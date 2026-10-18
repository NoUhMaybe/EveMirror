"""Legacy API repairs use provider fixtures; no weather/LLM/hardware calls."""

import importlib
from copy import deepcopy
from pathlib import Path

import pytest
import requests


@pytest.fixture
def weather(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(Path("legacy/agent").resolve()))
    module = importlib.import_module("tooling")
    monkeypatch.setattr(module, "_WEATHER_CACHE", {})
    monkeypatch.setattr(module, "CACHE_FILE_PATH", str(tmp_path / "weather.json"))
    return module


@pytest.fixture
def snapshot():
    return {
        "current": {"time": "2026-10-17T16:00", "temperature_2m": 71, "weather_code": 0},
        "hourly": {"time": ["2026-10-17T16:00", "2026-10-17T17:00"], "temperature_2m": [71, None]},
        "daily": {
            "time": ["2026-10-17", "2026-10-18"],
            "temperature_2m_max": [75, 79],
            "temperature_2m_min": [60, 61],
        },
    }


def test_current_and_weekly_requests_respect_separate_ttls(weather, snapshot, monkeypatch):
    calls = []

    def fetch(lat, lon, forecast_days):
        calls.append(forecast_days)
        return deepcopy(snapshot)

    monkeypatch.setattr(weather, "_fetch_weather_snapshot", fetch)
    weather.get_current_weather(weather.DEFAULT_LOCATION)
    weather.get_current_weather(weather.DEFAULT_LOCATION)
    assert calls == [2]
    weather.get_current_weather(weather.DEFAULT_LOCATION, include_week=True)
    weather.get_current_weather(weather.DEFAULT_LOCATION, include_week=True)
    weather.get_current_weather(weather.DEFAULT_LOCATION)
    assert calls == [2, 7]
    weather.get_current_weather(weather.DEFAULT_LOCATION, force_refresh=True)
    assert calls == [2, 7, 2]


def test_missing_hours_and_measurements_are_not_fabricated(weather, snapshot, monkeypatch):
    monkeypatch.setattr(weather, "_fetch_weather_snapshot", lambda *a, **k: deepcopy(snapshot))
    result = weather.get_current_weather(weather.DEFAULT_LOCATION)
    hourly = result["today_detail"]["hourly"]
    assert len(hourly) == 2
    assert hourly[1]["temperature_f"] is None
    assert hourly[0]["precipitation_probability_pct"] is None
    assert hourly[0]["precipitation_in"] is None
    assert result["today_detail"]["hourly_kind"] == "forecast"
    assert result["today_detail"]["historical_backfill_available"] is False
    assert result["source"] == "open-meteo" and result["stale"] is False


def test_legacy_synthetic_hourly_cache_is_discarded(weather, snapshot, monkeypatch):
    monkeypatch.setattr(weather, "_fetch_weather_snapshot", lambda *a, **k: deepcopy(snapshot))
    weather.get_current_weather(weather.DEFAULT_LOCATION)
    entry = next(iter(weather._WEATHER_CACHE.values()))
    entry["daily_hourly_cache"] = {
        "2026-10-17": [{"time": "2026-10-17T01:00", "temperature_f": 70, "backfilled": True}]
    }
    result = weather.get_current_weather(weather.DEFAULT_LOCATION)
    assert len(result["today_detail"]["hourly"]) == 2
    assert "daily_hourly_cache" not in next(iter(weather._WEATHER_CACHE.values()))


def test_unavailable_source_returns_labeled_cache_only(weather, snapshot, monkeypatch):
    monkeypatch.setattr(weather, "_fetch_weather_snapshot", lambda *a, **k: deepcopy(snapshot))
    original = weather.get_current_weather(weather.DEFAULT_LOCATION)

    def unavailable(*args, **kwargs):
        raise requests.ConnectionError("weather unavailable")

    monkeypatch.setattr(weather, "_fetch_weather_snapshot", unavailable)
    stale = weather.get_current_weather(weather.DEFAULT_LOCATION, force_refresh=True)
    assert stale["stale"] is True
    assert stale["acquired_at"] == original["acquired_at"]
    assert stale["weather_error"] == "weather_source_unavailable"
    weather._WEATHER_CACHE.clear()
    with pytest.raises(requests.ConnectionError):
        weather.get_current_weather(weather.DEFAULT_LOCATION)


def test_ordinary_chat_does_not_fetch_weather(weather, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Unrelated request triggered a weather fetch")

    monkeypatch.setattr(weather, "_fetch_weather_snapshot", forbidden)
    assert weather.maybe_call_tools("Explain transformers")[1] == {}
