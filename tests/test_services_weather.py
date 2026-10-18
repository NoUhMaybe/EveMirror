import asyncio
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import httpx
import pytest

from apps.config import WeatherSettings
from apps.server.services.common import ServiceError
from apps.server.services.weather import Location, WeatherService, normalize
from tests.service_fixtures import FakeClock, WeatherFixture, forecast_fixture


@pytest.mark.parametrize("mode,days", [("current", 1), ("daily", 1), ("weekly", 7)])
async def test_weather_modes_real_source_values_and_missing_data(mode, days):
    clock, fixture = FakeClock(), WeatherFixture()
    service = WeatherService(WeatherSettings(), clock, httpx.MockTransport(fixture.handler))
    await service.start()
    try:
        result = await service.get(mode)
        assert result["location"]["name"] == "Frisco, Texas, USA"
        assert len(result["daily"]) == days
        assert result["current"]["temperature"] == 72
        assert result["current"]["feels_like"] == 71
        assert result["daily"][0]["precipitation"] is None
        if mode == "daily":
            assert len(result["hourly"]) == 24
            assert result["hourly"][1]["temperature"] is None
            assert result["hourly"][0]["precipitation"] is None
            assert all(hour["kind"] == "forecast" for hour in result["hourly"])
            assert not any("backfilled" in hour for hour in result["hourly"])
        assert result["source"] == "open-meteo" and not result["stale"]
        assert result["source_timestamp"] != result["fetched_at"]
    finally:
        await service.close()


async def test_units_coalescing_independent_ttls_and_stale_bounds():
    clock, fixture = FakeClock(), WeatherFixture()
    settings = WeatherSettings(current_ttl=10, daily_ttl=20, weekly_ttl=30, max_stale=60)
    service = WeatherService(settings, clock, httpx.MockTransport(fixture.handler))
    await service.start()
    try:
        await asyncio.gather(*[service.get("weekly") for _ in range(8)])
        assert len(fixture.requests) == 1
        await service.get("current")
        clock.advance(11)
        await service.get("weekly")
        assert len(fixture.requests) == 1
        await service.get("current")
        assert len(fixture.requests) == 2
        metric = await service.get("daily", units="metric")
        assert (
            metric["current"]["temperature"] == 22
            and metric["measurement_units"]["temperature"] == "°C"
        )
        assert fixture.requests[-1].url.params["precipitation_unit"] == "mm"
        fixture.fail = True
        clock.advance(40)
        stale = await service.get("current")
        assert stale["stale"] and stale["cache_age_seconds"] == 40
        assert stale["fetched_at"] != clock().isoformat()
        clock.advance(30)
        with pytest.raises(ServiceError, match="weather_source_unavailable"):
            await service.get("current")
    finally:
        await service.close()


async def test_alternate_locations_and_ambiguity_never_fall_back_to_default():
    fixture = WeatherFixture()
    fixture.geocodes = [
        {
            "name": "Denver",
            "admin1": "Colorado",
            "country": "United States",
            "country_code": "US",
            "latitude": 39.7392,
            "longitude": -104.9903,
            "timezone": "America/Denver",
        }
    ]
    service = WeatherService(WeatherSettings(), FakeClock(), httpx.MockTransport(fixture.handler))
    await service.start()
    try:
        denver = await service.get("weekly", name="Denver", country_code="US")
        assert denver["location"]["timezone"] == "America/Denver"
        assert denver["location"]["name"].startswith("Denver")
        assert fixture.requests[-1].url.params["latitude"] == "39.7392"
        fixture.geocodes.append({**fixture.geocodes[0], "latitude": 40, "admin1": "Other"})
        with pytest.raises(ServiceError, match="location_ambiguous"):
            await service.get("current", name="Denver")
        fixture.geocodes = [{"name": "Missing timezone", "latitude": 40, "longitude": 0}]
        with pytest.raises(ServiceError, match="location_not_found"):
            await service.get("current", name="Unknown")
    finally:
        await service.close()


def test_dst_folds_are_distinct_instants_and_daily_dates_do_not_shift():
    start = datetime(2026, 11, 1, tzinfo=ZoneInfo("America/Chicago"))
    result = normalize(
        forecast_fixture(start),
        Location(name="Frisco", latitude=33, longitude=-96, timezone="America/Chicago"),
        "imperial",
        start.astimezone(UTC),
    )
    assert result.hourly[1].time.endswith("01:00:00-05:00")
    assert result.hourly[2].time.endswith("01:00:00-06:00")
    assert len({hour.time for hour in result.hourly}) == 168
    assert [day.date for day in result.daily] == [f"2026-11-{day:02}" for day in range(1, 8)]


@pytest.mark.parametrize(
    "mutator",
    [
        lambda raw: raw.update(hourly={}),
        lambda raw: raw.update(daily={}),
        lambda raw: raw["current_units"].update(temperature_2m="°C"),
    ],
)
async def test_invalid_weather_source_is_rejected(mutator):
    raw = forecast_fixture()
    mutator(raw)
    service = WeatherService(
        WeatherSettings(), FakeClock(), httpx.MockTransport(lambda r: httpx.Response(200, json=raw))
    )
    await service.start()
    try:
        with pytest.raises(ServiceError, match="weather_source_unavailable"):
            await service.get("current")
    finally:
        await service.close()
