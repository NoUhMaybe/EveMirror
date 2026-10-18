import asyncio
from datetime import UTC, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator

from apps.server.services.common import ServiceError, utc_now
from apps.server.services.http import http_client, request_json
from packages.weather import column, condition, number


class Location(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=240)
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    timezone: str

    @field_validator("timezone")
    @classmethod
    def valid_zone(cls, value):
        try:
            ZoneInfo(value)
        except (KeyError, ValueError):
            raise ValueError("Unknown IANA timezone") from None
        return value


class Current(BaseModel):
    kind: Literal["model_estimate"] = "model_estimate"
    time: str | None
    temperature: float | None
    feels_like: float | None
    humidity_pct: float | None = Field(ge=0, le=100)
    wind_speed: float | None
    condition: str | None
    precipitation: float | None


class Hour(BaseModel):
    kind: Literal["forecast"] = "forecast"
    time: str
    temperature: float | None
    humidity_pct: float | None = Field(ge=0, le=100)
    rain_probability_pct: float | None = Field(ge=0, le=100)
    precipitation: float | None


class Day(BaseModel):
    date: str
    kind: Literal["forecast"] = "forecast"
    high: float | None
    low: float | None
    rain_probability_pct: float | None = Field(ge=0, le=100)
    precipitation: float | None
    condition: str | None
    sunrise: str | None
    sunset: str | None


class Forecast(BaseModel):
    version: Literal[1] = 1
    location: Location
    units: Literal["imperial", "metric"]
    measurement_units: dict[str, str]
    current: Current
    hourly: list[Hour]
    daily: list[Day]
    fetched_at: str
    source_timestamp: str | None
    valid_from: str | None
    valid_until: str | None
    source: Literal["open-meteo"] = "open-meteo"
    stale: bool = False
    cache_age_seconds: float = 0
    freshness_ttl_seconds: float = Field(default=600, gt=0)
    source_age_seconds: float | None = Field(default=None, ge=0)


def normalize(data, location, units, acquired):
    if not isinstance(data, dict):
        raise ValueError("Invalid forecast response")
    zone = ZoneInfo(location.timezone)

    def stamp(value):
        epoch = number(value)
        return datetime.fromtimestamp(epoch, zone).isoformat() if epoch is not None else None

    current, hourly, daily = (data.get(key, {}) for key in ("current", "hourly", "daily"))
    if not all(isinstance(value, dict) for value in (current, hourly, daily)):
        raise ValueError("Invalid forecast sections")
    hours = [
        Hour(
            time=stamp(epoch),
            temperature=column(hourly, "temperature_2m", i),
            humidity_pct=column(hourly, "relative_humidity_2m", i),
            rain_probability_pct=column(hourly, "precipitation_probability", i),
            precipitation=column(hourly, "precipitation", i),
        )
        for i, epoch in enumerate(hourly.get("time", [])[:200])
        if stamp(epoch) is not None
    ]
    offset = number(data.get("utc_offset_seconds")) or 0
    days = [
        Day(
            # Daily values are labelled calendar aggregates from the API's fixed-offset boundary.
            date=datetime.fromtimestamp(epoch + offset, UTC).date().isoformat(),
            high=column(daily, "temperature_2m_max", i),
            low=column(daily, "temperature_2m_min", i),
            rain_probability_pct=column(daily, "precipitation_probability_max", i),
            precipitation=column(daily, "precipitation_sum", i),
            condition=condition(column(daily, "weather_code", i)),
            sunrise=stamp(column(daily, "sunrise", i)),
            sunset=stamp(column(daily, "sunset", i)),
        )
        for i, epoch in enumerate(daily.get("time", [])[:7])
        if number(epoch) is not None
    ]
    if not hours or not days:
        raise ValueError("Forecast has no valid time range")
    source_time = stamp(current.get("time"))
    if source_time is None and number(current.get("temperature_2m")) is not None:
        raise ValueError("Current conditions lack a source timestamp")
    expected = {
        "temperature": "°F" if units == "imperial" else "°C",
        "wind_speed": "mph" if units == "imperial" else "km/h",
        "precipitation": "inch" if units == "imperial" else "mm",
    }
    # Prevent accidental unit mislabelling when upstream ignores query parameters.
    actual = data.get("current_units", {})
    for key, label in [
        ("temperature_2m", expected["temperature"]),
        ("wind_speed_10m", expected["wind_speed"]),
        ("precipitation", expected["precipitation"]),
    ]:
        actual_label = actual.get(key)
        if label == "mph" and actual_label == "mp/h":
            actual_label = "mph"
        if actual_label not in {None, label}:
            raise ValueError("Unexpected source units")
    return Forecast(
        location=location,
        units=units,
        measurement_units=expected,
        current=Current(
            time=source_time,
            temperature=number(current.get("temperature_2m")),
            feels_like=number(current.get("apparent_temperature")),
            humidity_pct=number(current.get("relative_humidity_2m")),
            wind_speed=number(current.get("wind_speed_10m")),
            condition=condition(current.get("weather_code")),
            precipitation=number(current.get("precipitation")),
        ),
        hourly=hours,
        daily=days,
        fetched_at=acquired.isoformat(),
        source_timestamp=source_time,
        valid_from=hours[0].time,
        valid_until=(
            datetime.fromisoformat(hours[-1].time).astimezone(UTC) + timedelta(hours=1)
        ).isoformat(),
    )


class WeatherService:
    def __init__(self, settings, clock=utc_now, transport=None):
        self.settings, self.clock, self.transport = settings, clock, transport
        self.client = None
        self.cache = {}
        self.locks = {}
        self.locations = {}
        self.resolve_lock = asyncio.Lock()
        self.last_error = None
        self.failed_at = {}

    async def start(self):
        self.client = http_client(self.settings.timeout, transport=self.transport)

    async def resolve(self, name=None, coordinates=None, country_code=None, admin1=None):
        if coordinates:
            location = Location(**coordinates)
            ZoneInfo(location.timezone)
            return location
        if name is None or name.casefold() == self.settings.location.casefold():
            return Location(
                name=self.settings.location,
                latitude=self.settings.latitude,
                longitude=self.settings.longitude,
                timezone=self.settings.timezone,
            )
        key = (name.casefold(), country_code, admin1)
        async with self.resolve_lock:
            if key in self.locations:
                return self.locations[key]
            if len(self.locations) >= self.settings.max_locations:
                raise ServiceError("location_capacity", "Location cache limit reached.")
            data = await request_json(
                self.client,
                "GET",
                self.settings.geocoding_url,
                params={"name": name, "count": 10, "language": "en", "format": "json"},
            )
            if not isinstance(data, dict) or not isinstance(data.get("results", []), list):
                raise ServiceError("location_not_found", "Geocoding returned an invalid result.")
            matches = []
            for row in data.get("results", [])[:10]:
                if (
                    not isinstance(row, dict)
                    or str(row.get("name", "")).casefold() != name.casefold()
                ):
                    continue
                if country_code and row.get("country_code") != country_code:
                    continue
                if admin1 and str(row.get("admin1", "")).casefold() != admin1.casefold():
                    continue
                try:
                    zone = row["timezone"]
                    ZoneInfo(zone)
                    candidate = Location(
                        name=", ".join(
                            str(row[k]) for k in ("name", "admin1", "country") if row.get(k)
                        ),
                        latitude=row["latitude"],
                        longitude=row["longitude"],
                        timezone=zone,
                    )
                    if candidate not in matches:
                        matches.append(candidate)
                except (ValueError, KeyError, TypeError):
                    continue
            if len(matches) != 1:
                raise ServiceError(
                    "location_ambiguous" if matches else "location_not_found",
                    (
                        "Supply coordinates, country_code or admin1 to identify the "
                        "requested location."
                    ),
                    {"candidates": [m.model_dump() for m in matches]},
                )
            self.locations[key] = matches[0]
            return matches[0]

    async def get(
        self,
        mode,
        *,
        name=None,
        coordinates=None,
        units=None,
        country_code=None,
        admin1=None,
        day_offset=0,
    ):
        if not self.settings.enabled or self.client is None:
            raise ServiceError("weather_unavailable", "Weather is disabled or not started.")
        location = await self.resolve(name, coordinates, country_code, admin1)
        units = units or self.settings.units
        key = (location.latitude, location.longitude, location.timezone, units)
        if key not in self.locks:
            if len(self.locks) >= self.settings.max_locations:
                raise ServiceError("location_capacity", "Forecast cache limit reached.")
            self.locks[key] = asyncio.Lock()
        async with self.locks[key]:
            cached = self.cache.get(key)
            age = (
                max(0, (self.clock() - datetime.fromisoformat(cached.fetched_at)).total_seconds())
                if cached
                else float("inf")
            )
            ttl = getattr(self.settings, mode + "_ttl")
            stale = False
            today = self.clock().astimezone(ZoneInfo(location.timezone)).date()
            cached_date = (
                datetime.fromisoformat(cached.fetched_at)
                .astimezone(ZoneInfo(location.timezone))
                .date()
                if cached
                else None
            )
            needs_new_window = mode == "weekly" and cached_date != today
            if mode == "daily" and cached:
                wanted_date = (today + timedelta(days=day_offset)).isoformat()
                needs_new_window = wanted_date not in {day.date for day in cached.daily}
            if age >= ttl or needs_new_window:
                params = {
                    "latitude": location.latitude,
                    "longitude": location.longitude,
                    "timezone": location.timezone,
                    "timeformat": "unixtime",
                    "forecast_days": 7,
                    "temperature_unit": "fahrenheit" if units == "imperial" else "celsius",
                    "wind_speed_unit": "mph" if units == "imperial" else "kmh",
                    "precipitation_unit": "inch" if units == "imperial" else "mm",
                    "current": (
                        "temperature_2m,apparent_temperature,relative_humidity_2m,"
                        "wind_speed_10m,weather_code,precipitation"
                    ),
                    "hourly": (
                        "temperature_2m,relative_humidity_2m,precipitation_probability,"
                        "precipitation"
                    ),
                    "daily": (
                        "weather_code,temperature_2m_max,temperature_2m_min,"
                        "precipitation_probability_max,precipitation_sum,sunrise,sunset"
                    ),
                }
                try:
                    if (
                        key in self.failed_at
                        and (self.clock() - self.failed_at[key]).total_seconds() < 15
                    ):
                        raise ServiceError(
                            "weather_source_unavailable", "Weather retry is cooling down."
                        )
                    self.failed_at[key] = self.clock()
                    data = await request_json(
                        self.client, "GET", self.settings.forecast_url, params=params
                    )
                    cached = normalize(data, location, units, self.clock())
                    self.cache[key] = cached
                    self.failed_at.pop(key, None)
                    age, self.last_error = 0, None
                except (ServiceError, ValueError, TypeError, KeyError, OverflowError, OSError):
                    self.failed_at.setdefault(key, self.clock())
                    self.last_error = "weather_source_unavailable"
                    if cached is None or age > self.settings.max_stale:
                        raise ServiceError(
                            "weather_source_unavailable",
                            "No sufficiently recent weather is available.",
                        ) from None
                    stale = True
            result = cached.model_dump()
            result.update(
                stale=stale,
                cache_age_seconds=age,
                freshness_ttl_seconds=ttl,
                source_age_seconds=max(
                    0,
                    (
                        self.clock() - datetime.fromisoformat(cached.source_timestamp)
                    ).total_seconds(),
                )
                if cached.source_timestamp
                else None,
            )
            if mode == "daily":
                wanted = (
                    self.clock().astimezone(ZoneInfo(location.timezone)).date()
                    + timedelta(days=day_offset)
                ).isoformat()
                result["daily"] = [day for day in result["daily"] if day["date"] == wanted]
                result["hourly"] = [
                    hour for hour in result["hourly"] if hour["time"].startswith(wanted + "T")
                ]
                if not result["daily"]:
                    raise ServiceError(
                        "forecast_date_unavailable",
                        "Requested date is absent from the available forecast.",
                    )
            else:
                result["hourly"] = []
                result["daily"] = [
                    day for day in result["daily"] if day["date"] >= today.isoformat()
                ]
                if mode == "current":
                    today = self.clock().astimezone(ZoneInfo(location.timezone)).date().isoformat()
                    result["daily"] = [day for day in result["daily"] if day["date"] == today]
            return result

    async def close(self):
        if self.client:
            await self.client.aclose()
