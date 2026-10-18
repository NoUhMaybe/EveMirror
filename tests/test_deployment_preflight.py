"""Read-only readiness and benchmark probes against isolated host fixtures."""

import json
import platform
import subprocess

from scripts.benchmark_host import sample
from scripts.preflight import inspect, validate_config


def test_preflight_inventories_without_opening_devices_or_spawning_commands(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Preflight must not run commands or open devices")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(platform, "platform", lambda: "isolated Linux inventory fixture")
    monkeypatch.setattr(platform, "machine", lambda: "aarch64")
    monkeypatch.setattr(platform, "libc_ver", lambda: ("glibc", "2.36"))
    (tmp_path / "proc/asound").mkdir(parents=True)
    (tmp_path / "proc/asound/cards").write_text("isolated USB audio fixture")
    report = inspect("edge", root=tmp_path)
    assert report["read_only"]
    audio = next(c for c in report["checks"] if c["name"] == "alsa")
    assert audio["ok"] and "fixture" in audio["detail"]
    assert {c["name"] for c in report["checks"]} >= {
        "glibc",
        "portaudio",
        "onnxruntime",
        "wayland",
        "serial",
        "soxr",
    }
    assert not list(tmp_path.rglob("*.sqlite3"))


def test_config_preflight_redacts_failures_and_opens_no_database(monkeypatch, tmp_path):
    monkeypatch.setenv("EVE_EDGE_TOKEN", "private-invalid-token")
    monkeypatch.setenv("EVE_EDGE_JOURNAL_PATH", str(tmp_path / "never-created.sqlite3"))
    result = validate_config("edge")
    assert not result["ok"] and "private-invalid-token" not in json.dumps(result)
    assert not (tmp_path / "never-created.sqlite3").exists()
    monkeypatch.setenv("EVE_EDGE_TOKEN", "preflight-test-token-" + "a" * 32)
    monkeypatch.setenv("EVE_EDGE_SIMULATE_HARDWARE", "true")
    assert validate_config("edge")["ok"]
    assert not (tmp_path / "never-created.sqlite3").exists()
    monkeypatch.setenv("EVE_EDGE_JOURNAL_PATH", str(tmp_path / "missing/state.sqlite3"))
    assert not validate_config("edge")["ok"]
    assert not (tmp_path / "missing").exists()


def test_linux_counter_probe_handles_missing_process_and_temperature(tmp_path):
    process = tmp_path / "proc/123"
    process.mkdir(parents=True)
    (process / "status").write_text("Name:\tfixture\nVmRSS:\t1234 kB\n")
    fields = ["S"] + ["0"] * 22
    fields[11], fields[12] = "40", "5"
    (process / "stat").write_text("123 (name with spaces) " + " ".join(fields))
    temperature = tmp_path / "sys/class/thermal/thermal_zone0"
    temperature.mkdir(parents=True)
    (temperature / "temp").write_text("42000")
    report = sample([123, 999], tmp_path / "proc", tmp_path / "sys")
    assert report["processes"]["123"] == {"rss": "1234 kB", "user_ticks": 40, "system_ticks": 5}
    assert report["processes"]["999"] == {"unavailable": True}
    assert report["temperature_c"] == {"thermal_zone0": 42.0}
