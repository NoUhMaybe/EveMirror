import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests

from backlight_control import get_last_known_brightness, set_backlight_brightness

DEFAULT_LOCATION = "Frisco, Texas"
BACKLIGHT_ADJUST_STEP = 20
DEFAULT_LAT = 33.1507
DEFAULT_LON = -96.8236
WEEKLY_REFRESH_SECONDS = 3 * 60 * 60
DAILY_REFRESH_SECONDS = 60 * 60
CACHE_FILE_PATH = os.path.join(os.path.dirname(__file__), "weather_cache.json")

# In-process weather cache, keyed by location coordinates.
_WEATHER_CACHE: Dict[str, Dict[str, object]] = {}

_WEATHER_CODE_MAP = {
    0: "clear",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "rime fog",
    51: "light drizzle",
    53: "drizzle",
    55: "heavy drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    80: "rain showers",
    81: "heavy rain showers",
    82: "violent rain showers",
    95: "thunderstorm",
}


def should_enable_thinking(user_text: str) -> bool:
    text = user_text.lower().strip()
    complex_markers = [
        "plan",
        "compare",
        "tradeoff",
        "pros and cons",
        "step by step",
        "strategy",
        "reason through",
        "analyze",
        "if i",
        "should i",
    ]
    long_prompt = len(text.split()) >= 24
    multi_question = text.count("?") >= 2
    conditional = " if " in f" {text} " and (" then " in f" {text} " or " should " in f" {text} ")
    return (long_prompt and any(m in text for m in complex_markers)) or multi_question or conditional


def extract_requested_location(user_text: str) -> str:
    # Supports prompts like "weather in Denver" or "temperature for Austin, TX"
    match = re.search(r"\b(?:in|for|at)\s+([a-zA-Z][a-zA-Z\s,.-]{2,})$", user_text.strip())
    if match:
        location = match.group(1).strip(" .?!")
        if location:
            return location
    return DEFAULT_LOCATION


def wants_weekly_weather(user_text: str) -> bool:
    text = user_text.lower()
    weekly_markers = [
        "week",
        "this week",
        "weekly",
        "7 day",
        "seven day",
        "next few days",
        "forecast",
        "tomorrow",
    ]
    return any(m in text for m in weekly_markers)


def is_weather_request(user_text: str) -> bool:
    text = user_text.lower()
    weather_markers = [
        "weather",
        "temperature",
        "forecast",
        "rain",
        "raining",
        "shower",
        "showers",
        "storm",
        "snow",
        "sunny",
        "cloudy",
        "humid",
        "humidity",
        "wind",
        "windy",
        "today",
        "tomorrow",
        "tonight",
    ]
    return any(m in text for m in weather_markers)


def is_backlight_request(user_text: str) -> bool:
    text = user_text.lower()
    markers = ["backlight", "screen brightness", "display brightness", "mirror brightness"]
    return any(m in text for m in markers)


def resolve_backlight_target_percent(user_text: str, current_percent: Optional[int]) -> Optional[int]:
    """Return the target brightness 0-100, or None if the request has no actionable target."""
    text = user_text.lower()

    match = re.search(r"(\d{1,3})\s*%", text) or re.search(r"\b(\d{1,3})\b", text)
    if match:
        return max(0, min(100, int(match.group(1))))

    if re.search(r"\boff\b", text):
        return 0
    if any(k in text for k in ["full", "max", "maximum", "brightest"]) or re.search(r"\bon\b", text):
        return 100
    if re.search(r"\bhalf\b", text):
        return 50

    base = current_percent if current_percent is not None else 50
    if any(k in text for k in ["dim", "darker", "lower", "down"]):
        return max(0, base - BACKLIGHT_ADJUST_STEP)
    if any(k in text for k in ["brighten", "brighter", "raise", "up"]):
        return min(100, base + BACKLIGHT_ADJUST_STEP)

    return None


def get_current_time() -> Dict[str, str]:
    now = datetime.now().astimezone()
    return {
        "iso": now.isoformat(timespec="seconds"),
        "readable": now.strftime("%A, %B %d at %I:%M %p %Z"),
    }


def _resolve_location(location: str) -> Tuple[float, float, str]:
    if location.lower() == DEFAULT_LOCATION.lower():
        return DEFAULT_LAT, DEFAULT_LON, DEFAULT_LOCATION

    resp = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": location, "count": 1, "language": "en", "format": "json"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    results = data.get("results") or []
    if not results:
        return DEFAULT_LAT, DEFAULT_LON, DEFAULT_LOCATION

    top = results[0]
    label = ", ".join(p for p in [top.get("name"), top.get("admin1"), top.get("country")] if p)
    return float(top["latitude"]), float(top["longitude"]), label


def _cache_key(lat: float, lon: float) -> str:
    return f"{lat:.4f},{lon:.4f}"


def _load_weather_cache() -> Dict[str, Dict[str, object]]:
    if not os.path.exists(CACHE_FILE_PATH):
        return {}
    try:
        with open(CACHE_FILE_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError):
        return {}

    if not isinstance(raw, dict):
        return {}

    out: Dict[str, Dict[str, object]] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            continue
        out[key] = value
    return out


def _save_weather_cache(cache: Dict[str, Dict[str, object]]) -> None:
    parent_dir = os.path.dirname(CACHE_FILE_PATH)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    tmp_path = CACHE_FILE_PATH + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=True, separators=(",", ":"))
        os.replace(tmp_path, CACHE_FILE_PATH)
    except OSError:
        # Non-fatal: keep in-memory cache even if persistence fails.
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass


def _parse_iso_local(iso_text: object) -> Optional[datetime]:
    if not iso_text:
        return None
    try:
        return datetime.fromisoformat(str(iso_text))
    except ValueError:
        return None


def _extract_today_hourly_rows(source: Dict[str, object]) -> Tuple[Optional[str], List[Dict[str, object]]]:
    current = source.get("current", {}) if isinstance(source.get("current", {}), dict) else {}
    daily = source.get("daily", {}) if isinstance(source.get("daily", {}), dict) else {}
    hourly = source.get("hourly", {}) if isinstance(source.get("hourly", {}), dict) else {}

    current_time_iso = current.get("time")
    current_dt = _parse_iso_local(current_time_iso)
    day_list = daily.get("time", []) if isinstance(daily.get("time", []), list) else []

    today_date: Optional[str] = None
    if current_dt:
        today_date = current_dt.date().isoformat()
    elif current_time_iso:
        today_date = str(current_time_iso).split("T")[0]
    elif day_list:
        today_date = str(day_list[0])

    if not today_date:
        return None, []

    hour_times = hourly.get("time", []) if isinstance(hourly.get("time", []), list) else []
    hour_temps = hourly.get("temperature_2m", []) if isinstance(hourly.get("temperature_2m", []), list) else []
    hour_pop = hourly.get("precipitation_probability", []) if isinstance(hourly.get("precipitation_probability", []), list) else []
    hour_precip = hourly.get("precipitation", []) if isinstance(hourly.get("precipitation", []), list) else []
    hour_humidity = hourly.get("relative_humidity_2m", []) if isinstance(hourly.get("relative_humidity_2m", []), list) else []

    out: List[Dict[str, object]] = []
    for i, ts in enumerate(hour_times):
        ts_text = str(ts)
        ts_date = ts_text.split("T")[0]
        if ts_date != today_date:
            continue
        out.append(
            {
                "time": ts_text,
                "temperature_f": hour_temps[i] if i < len(hour_temps) else None,
                "precipitation_probability_pct": hour_pop[i] if i < len(hour_pop) else 0,
                "precipitation_in": hour_precip[i] if i < len(hour_precip) else 0,
                "relative_humidity_pct": hour_humidity[i] if i < len(hour_humidity) else None,
            }
        )

    return today_date, out


def _merge_hourly_rows(
    existing_rows: List[Dict[str, object]],
    fresh_rows: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    by_time: Dict[str, Dict[str, object]] = {}

    for row in existing_rows:
        ts = str(row.get("time", ""))
        if not ts:
            continue
        by_time[ts] = {
            "time": ts,
            "temperature_f": row.get("temperature_f"),
            "precipitation_probability_pct": row.get("precipitation_probability_pct", 0),
            "precipitation_in": row.get("precipitation_in", 0),
            "relative_humidity_pct": row.get("relative_humidity_pct"),
        }

    for row in fresh_rows:
        ts = str(row.get("time", ""))
        if not ts:
            continue
        prior = by_time.get(ts, {"time": ts})
        temp = row.get("temperature_f")
        pop = row.get("precipitation_probability_pct")
        precip = row.get("precipitation_in")
        humidity = row.get("relative_humidity_pct")

        prior["temperature_f"] = temp if temp is not None else prior.get("temperature_f")
        prior["precipitation_probability_pct"] = pop if pop is not None else prior.get("precipitation_probability_pct", 0)
        prior["precipitation_in"] = precip if precip is not None else prior.get("precipitation_in", 0)
        prior["relative_humidity_pct"] = humidity if humidity is not None else prior.get("relative_humidity_pct")
        by_time[ts] = prior

    merged = list(by_time.values())
    merged.sort(key=lambda r: str(r.get("time", "")))
    return merged


def _backfill_today_missing_hours(
    date_iso: str,
    current_hour_local: int,
    rows: List[Dict[str, object]],
    current_temp_f: Optional[float],
) -> List[Dict[str, object]]:
    # Keep original observations and only synthesize missing earlier hours for the same day.
    by_hour: Dict[int, Dict[str, object]] = {}
    for row in rows:
        ts = str(row.get("time", ""))
        if not ts:
            continue
        ts_hour = _parse_iso_local(ts)
        if not ts_hour:
            continue
        by_hour[ts_hour.hour] = {
            "time": ts,
            "temperature_f": row.get("temperature_f"),
            "precipitation_probability_pct": row.get("precipitation_probability_pct", 0),
            "precipitation_in": row.get("precipitation_in", 0),
            "relative_humidity_pct": row.get("relative_humidity_pct"),
            "backfilled": bool(row.get("backfilled", False)),
        }

    anchor_temp: Optional[float] = None
    if current_temp_f is not None:
        anchor_temp = float(current_temp_f)
    else:
        temps = [r.get("temperature_f") for r in rows if r.get("temperature_f") is not None]
        if temps:
            anchor_temp = float(temps[-1])

    for hour in range(max(0, min(23, current_hour_local)) + 1):
        if hour in by_hour:
            continue
        temp = anchor_temp
        if temp is None:
            temp = 70.0

        by_hour[hour] = {
            "time": f"{date_iso}T{hour:02d}:00:00",
            "temperature_f": temp,
            "precipitation_probability_pct": 0,
            "precipitation_in": 0,
            "relative_humidity_pct": None,
            "backfilled": True,
        }

    merged = list(by_hour.values())
    merged.sort(key=lambda r: str(r.get("time", "")))
    return merged


_WEATHER_CACHE = _load_weather_cache()


def _fetch_weather_snapshot(lat: float, lon: float, forecast_days: int) -> Dict[str, object]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m,relative_humidity_2m",
        "hourly": "temperature_2m,precipitation_probability,precipitation,relative_humidity_2m",
        "daily": "sunrise,sunset,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,weather_code",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "auto",
        "forecast_days": forecast_days,
    }

    resp = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params=params,
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, dict) else {}


def _refresh_weekly_cache_if_due(location: str = DEFAULT_LOCATION) -> Optional[str]:
    lat, lon, resolved = _resolve_location(location)
    key = _cache_key(lat, lon)
    now_ts = datetime.now().timestamp()

    cached = _WEATHER_CACHE.get(key, {})
    weekly_fetched_at = float(cached.get("weekly_fetched_at", 0.0) or 0.0)
    weekly_source = cached.get("weekly_source") if isinstance(cached.get("weekly_source"), dict) else None

    if weekly_source is not None and (now_ts - weekly_fetched_at) < WEEKLY_REFRESH_SECONDS:
        return None

    refreshed_weekly = _fetch_weather_snapshot(lat, lon, forecast_days=7)
    next_cached = dict(cached)
    next_cached["weekly_source"] = refreshed_weekly
    next_cached["weekly_fetched_at"] = now_ts

    # Seed daily cache only if it doesn't exist yet.
    if not isinstance(next_cached.get("daily_source"), dict):
        next_cached["daily_source"] = refreshed_weekly
        next_cached["daily_fetched_at"] = now_ts

    _WEATHER_CACHE[key] = next_cached
    _save_weather_cache(_WEATHER_CACHE)
    return resolved


def _build_weather_payload(
    resolved_location: str,
    daily_source: Dict[str, object],
    weekly_source: Dict[str, object],
    include_week: bool,
    cached_today_hourly: Optional[List[Dict[str, object]]] = None,
) -> Dict[str, object]:
    current = daily_source.get("current", {}) if isinstance(daily_source.get("current", {}), dict) else {}
    daily = daily_source.get("daily", {}) if isinstance(daily_source.get("daily", {}), dict) else {}
    hourly = daily_source.get("hourly", {}) if isinstance(daily_source.get("hourly", {}), dict) else {}

    code = int(current.get("weather_code", -1))
    condition = _WEATHER_CODE_MAP.get(code, f"weather code {code}")

    current_time_iso = current.get("time")
    current_dt = _parse_iso_local(current_time_iso)

    week_daily = weekly_source.get("daily", {}) if isinstance(weekly_source.get("daily", {}), dict) else {}
    date_list = week_daily.get("time", []) if isinstance(week_daily.get("time", []), list) else []
    max_list = week_daily.get("temperature_2m_max", []) if isinstance(week_daily.get("temperature_2m_max", []), list) else []
    min_list = week_daily.get("temperature_2m_min", []) if isinstance(week_daily.get("temperature_2m_min", []), list) else []
    pop_list = week_daily.get("precipitation_probability_max", []) if isinstance(week_daily.get("precipitation_probability_max", []), list) else []
    rain_list = week_daily.get("precipitation_sum", []) if isinstance(week_daily.get("precipitation_sum", []), list) else []
    code_list = week_daily.get("weather_code", []) if isinstance(week_daily.get("weather_code", []), list) else []

    today_date = None
    if current_dt:
        today_date = current_dt.date().isoformat()
    elif current_time_iso:
        today_date = str(current_time_iso).split("T")[0]
    elif date_list:
        today_date = str(date_list[0])

    days: List[Dict[str, object]] = []
    for i, day in enumerate(date_list):
        day_str = str(day)
        # Drop historical daily entries once their date has passed.
        if today_date and day_str < today_date:
            continue
        day_code = int(code_list[i]) if i < len(code_list) and code_list[i] is not None else -1
        day_condition = _WEATHER_CODE_MAP.get(day_code, f"weather code {day_code}")
        days.append(
            {
                "date": day_str,
                "high_f": max_list[i] if i < len(max_list) else None,
                "low_f": min_list[i] if i < len(min_list) else None,
                "rain_chance_pct": pop_list[i] if i < len(pop_list) else None,
                "rain_estimate_in": rain_list[i] if i < len(rain_list) else None,
                "condition": day_condition,
            }
        )
        if len(days) >= (7 if include_week else 2):
            break

    hour_times = hourly.get("time", []) if isinstance(hourly.get("time", []), list) else []
    hour_temps = hourly.get("temperature_2m", []) if isinstance(hourly.get("temperature_2m", []), list) else []
    hour_pop = hourly.get("precipitation_probability", []) if isinstance(hourly.get("precipitation_probability", []), list) else []
    hour_precip = hourly.get("precipitation", []) if isinstance(hourly.get("precipitation", []), list) else []
    hour_humidity = hourly.get("relative_humidity_2m", []) if isinstance(hourly.get("relative_humidity_2m", []), list) else []

    hourly_today: List[Dict[str, object]] = []
    current_hour_floor = None
    if current_dt:
        current_hour_floor = current_dt.replace(minute=0, second=0, microsecond=0)

    if cached_today_hourly:
        hourly_today = list(cached_today_hourly)
    else:
        for i, ts in enumerate(hour_times):
            ts_text = str(ts)
            ts_date = ts_text.split("T")[0]
            if today_date and ts_date != today_date:
                continue

            hourly_today.append(
                {
                    "time": ts_text,
                    "temperature_f": hour_temps[i] if i < len(hour_temps) else None,
                    "precipitation_probability_pct": hour_pop[i] if i < len(hour_pop) else 0,
                    "precipitation_in": hour_precip[i] if i < len(hour_precip) else 0,
                    "relative_humidity_pct": hour_humidity[i] if i < len(hour_humidity) else None,
                }
            )

    hourly_today.sort(key=lambda h: str(h.get("time", "")))

    temp_values = [float(h["temperature_f"]) for h in hourly_today if h.get("temperature_f") is not None]
    high_index = 0
    low_index = 0
    if temp_values and hourly_today:
        high_temp = max(temp_values)
        low_temp = min(temp_values)
        high_index = next(
            (idx for idx, h in enumerate(hourly_today) if h.get("temperature_f") is not None and float(h["temperature_f"]) == high_temp),
            0,
        )
        low_index = next(
            (idx for idx, h in enumerate(hourly_today) if h.get("temperature_f") is not None and float(h["temperature_f"]) == low_temp),
            0,
        )

    sunrise_iso = daily.get("sunrise", [None])[0] if daily.get("sunrise") else None
    sunset_iso = daily.get("sunset", [None])[0] if daily.get("sunset") else None

    current_hour_local = datetime.now().astimezone().hour
    if current_dt:
        current_hour_local = current_dt.hour

    historical_backfill_available = False
    if current_hour_floor:
        for row in hourly_today:
            ts_dt = _parse_iso_local(row.get("time"))
            if ts_dt and ts_dt < current_hour_floor:
                historical_backfill_available = True
                break

    return {
        "location": resolved_location,
        "temperature_f": current.get("temperature_2m"),
        "feels_like_f": current.get("apparent_temperature"),
        "humidity_pct": current.get("relative_humidity_2m"),
        "wind_mph": current.get("wind_speed_10m"),
        "condition": condition,
        "week_forecast": days,
        "includes_week_forecast": include_week,
        "today_detail": {
            "date": today_date,
            "hourly": hourly_today,
            "high_index": high_index,
            "low_index": low_index,
            "sunrise_iso": sunrise_iso,
            "sunset_iso": sunset_iso,
            "current_hour_local": current_hour_local,
            "historical_backfill_available": historical_backfill_available,
        },
    }


def get_current_weather(location: str, include_week: bool = False, force_refresh: bool = False) -> Dict[str, object]:
    lat, lon, resolved = _resolve_location(location)
    key = _cache_key(lat, lon)
    now_ts = datetime.now().timestamp()
    cached = _WEATHER_CACHE.get(key, {})

    weekly_source = cached.get("weekly_source") if isinstance(cached.get("weekly_source"), dict) else None
    daily_source = cached.get("daily_source") if isinstance(cached.get("daily_source"), dict) else None
    weekly_fetched_at = float(cached.get("weekly_fetched_at", 0.0) or 0.0)
    daily_fetched_at = float(cached.get("daily_fetched_at", 0.0) or 0.0)

    # Weekly stockpile: refresh every 6h, and on weekly-style requests.
    needs_weekly_refresh = (
        force_refresh
        or
        weekly_source is None
        or (now_ts - weekly_fetched_at) >= WEEKLY_REFRESH_SECONDS
        or include_week
    )

    # Daily/current view: refresh every hour and whenever weather is requested.
    # Requests are weather-related by caller contract, so this keeps current conditions fresh.
    needs_daily_refresh = (
        force_refresh
        or
        daily_source is None
        or (now_ts - daily_fetched_at) >= DAILY_REFRESH_SECONDS
        or True
    )

    if needs_weekly_refresh:
        weekly_source = _fetch_weather_snapshot(lat, lon, forecast_days=7)
        weekly_fetched_at = now_ts

    # Reuse the 7-day fetch for daily if we already made one this request.
    if needs_daily_refresh:
        if needs_weekly_refresh and weekly_source is not None:
            daily_source = weekly_source
        else:
            daily_source = _fetch_weather_snapshot(lat, lon, forecast_days=2)
        daily_fetched_at = now_ts

    if weekly_source is None or daily_source is None:
        # Defensive fallback if an unexpected path skipped fetches.
        snapshot = _fetch_weather_snapshot(lat, lon, forecast_days=7)
        weekly_source = snapshot
        daily_source = snapshot
        weekly_fetched_at = now_ts
        daily_fetched_at = now_ts

    cached_daily_hourly = cached.get("daily_hourly_cache") if isinstance(cached.get("daily_hourly_cache"), dict) else {}
    today_date, fresh_rows = _extract_today_hourly_rows(daily_source)
    next_daily_hourly_cache: Dict[str, List[Dict[str, object]]] = {}
    current = daily_source.get("current", {}) if isinstance(daily_source.get("current", {}), dict) else {}
    current_dt = _parse_iso_local(current.get("time"))
    current_hour_local = datetime.now().astimezone().hour
    if current_dt:
        current_hour_local = current_dt.hour
    current_temp_f = current.get("temperature_2m") if isinstance(current.get("temperature_2m"), (int, float)) else None

    if today_date:
        # Keep only current/future day buckets; drop fully elapsed days.
        for date_key, rows in cached_daily_hourly.items():
            if not isinstance(date_key, str) or date_key < today_date:
                continue
            if isinstance(rows, list):
                normalized_rows = [r for r in rows if isinstance(r, dict)]
                next_daily_hourly_cache[date_key] = normalized_rows

        existing_rows = next_daily_hourly_cache.get(today_date, [])
        merged_rows = _merge_hourly_rows(existing_rows, fresh_rows)
        backfilled_rows = _backfill_today_missing_hours(
            date_iso=today_date,
            current_hour_local=current_hour_local,
            rows=merged_rows,
            current_temp_f=float(current_temp_f) if current_temp_f is not None else None,
        )
        next_daily_hourly_cache[today_date] = backfilled_rows

    cached_today_hourly = next_daily_hourly_cache.get(today_date, []) if today_date else []

    _WEATHER_CACHE[key] = {
        "weekly_source": weekly_source,
        "daily_source": daily_source,
        "weekly_fetched_at": weekly_fetched_at,
        "daily_fetched_at": daily_fetched_at,
        "daily_hourly_cache": next_daily_hourly_cache,
    }
    _save_weather_cache(_WEATHER_CACHE)

    return _build_weather_payload(
        resolved_location=resolved,
        daily_source=daily_source,
        weekly_source=weekly_source,
        include_week=include_week,
        cached_today_hourly=cached_today_hourly,
    )


def maybe_call_tools(user_text: str) -> Tuple[List[str], Dict[str, object]]:
    text = user_text.lower()
    notes: List[str] = []
    payload: Dict[str, object] = {}

    # Autonomous cache refresh: keep weekly stockpile current every 3 hours.
    try:
        refreshed_location = _refresh_weekly_cache_if_due(DEFAULT_LOCATION)
        if refreshed_location:
            notes.append(f"weather weekly cache auto-refreshed (location={refreshed_location})")
    except Exception as exc:
        notes.append(f"weather weekly cache auto-refresh failed ({exc})")

    if is_weather_request(user_text):
        requested_location = extract_requested_location(user_text)
        include_week = wants_weekly_weather(user_text)
        try:
            weather = get_current_weather(requested_location, include_week=include_week)
            payload["weather"] = weather
            notes.append(
                "weather tool used"
                f" (location={weather['location']}, temp_f={weather['temperature_f']},"
                f" feels_like_f={weather['feels_like_f']}, condition={weather['condition']},"
                f" week={weather['includes_week_forecast']})"
            )
        except Exception as exc:
            payload["weather_error"] = str(exc)
            payload["weather_unavailable"] = True
            notes.append(f"weather tool failed ({exc}); model must avoid guessing weather details")

    if any(k in text for k in ["time", "clock", "what day", "date"]):
        now = get_current_time()
        payload["time"] = now
        notes.append(f"time tool used (local={now['readable']})")

    if is_backlight_request(user_text):
        current = get_last_known_brightness()
        target = resolve_backlight_target_percent(user_text, current)
        if target is None:
            if current is None:
                payload["backlight"] = {"status": "unknown", "detail": "No brightness has been set yet this session."}
                notes.append("backlight status requested; no brightness set yet")
            else:
                payload["backlight"] = {"status": "ok", "brightness_percent": current}
                notes.append(f"backlight status requested (current={current}%)")
        else:
            result = set_backlight_brightness(target)
            payload["backlight"] = result
            if result.get("status") == "ok":
                notes.append(f"backlight tool used (brightness_percent={result['brightness_percent']})")
            else:
                notes.append(f"backlight tool failed ({result.get('error')})")
    elif any(k in text for k in ["light", "lights", "thermostat", "garage", "alarm", "switch", "home assistant"]):
        payload["smart_home_attempt"] = {
            "status": "attempted_not_executed",
            "details": "Smart-home execution is intentionally stubbed in this phase.",
        }
        notes.append("smart-home action attempt recorded (not executed in this phase)")

    return notes, payload
