import json
import os
import sys
from pathlib import Path
import re
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import requests

from backlight_control import get_last_known_brightness, set_backlight_brightness

DEFAULT_LOCATION = "Frisco, Texas"
BACKLIGHT_ADJUST_STEP = 20
DEFAULT_LAT = 33.1507
DEFAULT_LON = -96.8236
WEEKLY_REFRESH_SECONDS = 3 * 60 * 60
DAILY_REFRESH_SECONDS = 60 * 60
_WEATHER_LOCK = threading.RLock()
MAX_STALE_SECONDS = 24 * 60 * 60
CACHE_FILE_PATH = os.path.join(os.path.dirname(__file__), "weather_cache.json")

# In-process weather cache, keyed by location coordinates.
_WEATHER_CACHE: Dict[str, Dict[str, object]] = {}

# Share pure condition/nullable-column transformations; preserve the old relay contract.
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(_REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT))
from packages.weather import CONDITIONS as _WEATHER_CODE_MAP, column as _weather_column



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
        raise ValueError("Requested weather location was not found")

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

    out: List[Dict[str, object]] = []
    for i, ts in enumerate(hour_times):
        ts_text = str(ts)
        ts_date = ts_text.split("T")[0]
        if ts_date != today_date:
            continue
        out.append(
            {
                "time": ts_text,
                "temperature_f": _weather_column(hourly, "temperature_2m", i),
                "precipitation_probability_pct": _weather_column(hourly, "precipitation_probability", i),
                "precipitation_in": _weather_column(hourly, "precipitation", i),
                "relative_humidity_pct": _weather_column(hourly, "relative_humidity_2m", i),
            }
        )

    return today_date, out


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
    if not isinstance(data, dict) or not isinstance(data.get("current"), dict):
        raise ValueError("Invalid weather response")
    return data


def _build_weather_payload(
    resolved_location: str,
    daily_source: Dict[str, object],
    weekly_source: Dict[str, object],
    include_week: bool,
) -> Dict[str, object]:
    current = daily_source.get("current", {}) if isinstance(daily_source.get("current", {}), dict) else {}
    daily = daily_source.get("daily", {}) if isinstance(daily_source.get("daily", {}), dict) else {}

    code = current.get("weather_code")
    code = int(code) if isinstance(code, (int, float)) else -1
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

    _, hourly_today = _extract_today_hourly_rows(daily_source)

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
            "historical_backfill_available": False,
            "hourly_kind": "forecast",
        },
    }


def get_current_weather(location: str, include_week: bool = False, force_refresh: bool = False) -> Dict[str, object]:
    """Cached provider values only. Never synthesize observations or missing measurements."""
    with _WEATHER_LOCK:
        return _get_current_weather(location, include_week, force_refresh)


def _get_current_weather(location: str, include_week: bool, force_refresh: bool) -> Dict[str, object]:
    lat, lon, resolved = _resolve_location(location)
    key = _cache_key(lat, lon)
    now_ts = datetime.now().timestamp()
    cached = _WEATHER_CACHE.get(key, {})
    daily_source = cached.get("daily_source") if isinstance(cached.get("daily_source"), dict) else None
    weekly_source = cached.get("weekly_source") if isinstance(cached.get("weekly_source"), dict) else None
    daily_fetched_at = float(cached.get("daily_fetched_at", 0) or 0)
    weekly_fetched_at = float(cached.get("weekly_fetched_at", 0) or 0)
    daily_due = (force_refresh or not isinstance(daily_source, dict)
                 or not 0 <= now_ts - daily_fetched_at < DAILY_REFRESH_SECONDS)
    weekly_due = include_week and (force_refresh or not isinstance(weekly_source, dict)
                 or not 0 <= now_ts - weekly_fetched_at < WEEKLY_REFRESH_SECONDS)
    stale = False
    try:
        if weekly_due:
            weekly_source = _fetch_weather_snapshot(lat, lon, forecast_days=7)
            weekly_fetched_at = now_ts
            daily_source = weekly_source
            daily_fetched_at = now_ts
        elif daily_due:
            daily_source = _fetch_weather_snapshot(lat, lon, forecast_days=2)
            daily_fetched_at = now_ts
    except (requests.RequestException, ValueError):
        selected = weekly_source if include_week else daily_source
        acquired = weekly_fetched_at if include_week else daily_fetched_at
        if not isinstance(selected, dict) or not 0 <= now_ts - acquired <= MAX_STALE_SECONDS:
            raise
        stale = True

    # Do not reuse the legacy hourly cache: it may contain synthetic backfilled data.
    _WEATHER_CACHE[key] = {
        "weekly_source": weekly_source, "weekly_fetched_at": weekly_fetched_at,
        "daily_source": daily_source, "daily_fetched_at": daily_fetched_at,
    }
    _save_weather_cache(_WEATHER_CACHE)
    source = weekly_source if include_week else daily_source
    payload = _build_weather_payload(resolved, daily_source or source, source, include_week)
    payload.update({
        "source": "open-meteo", "source_timestamp": (daily_source or source).get("current", {}).get("time"),
        "acquired_at": datetime.fromtimestamp(daily_fetched_at, timezone.utc).isoformat(),
        "forecast_acquired_at": datetime.fromtimestamp(
            weekly_fetched_at if include_week else daily_fetched_at, timezone.utc).isoformat(),
        "stale": stale, "weather_error": "weather_source_unavailable" if stale else None,
        "units": {"temperature": "fahrenheit", "wind": "mph", "precipitation": "inch"},
    })
    return payload


def maybe_call_tools(user_text: str) -> Tuple[List[str], Dict[str, object]]:
    text = user_text.lower()
    notes: List[str] = []
    payload: Dict[str, object] = {}

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
