"""Read-only host inventory. Does not open audio/serial, install, or change services."""

import argparse
import ctypes.util
import importlib.metadata
import importlib.util
import json
import os
import platform
import shutil
import sys
from pathlib import Path


def inspect(role="edge", *, root=Path("/")):
    checks = []

    def add(name, ok, detail, required=True):
        checks.append({"name": name, "ok": bool(ok), "detail": detail, "required": required})

    add("linux", platform.system() == "Linux", platform.platform())
    add("python", (3, 11) <= sys.version_info[:2] <= (3, 12), platform.python_version())
    add(
        "architecture",
        platform.machine().lower() in {"aarch64", "arm64"} if role == "edge" else True,
        platform.machine(),
    )
    modules = ["pydantic", "websockets"]
    modules += (
        ["serial", "numpy", "soxr", "sounddevice", "onnxruntime", "openwakeword"]
        if role == "edge"
        else ["fastapi", "uvicorn", "httpx"]
    )
    for module in modules:
        found = importlib.util.find_spec(module) is not None
        distribution = {"serial": "pyserial"}.get(module, module)
        try:
            version = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            version = "not installed"
        add(module, found, version)
    if role == "edge":
        libc, version = platform.libc_ver()
        try:
            compatible_libc = libc == "glibc" and tuple(map(int, version.split(".")[:2])) >= (2, 34)
        except ValueError:
            compatible_libc = False
        add("glibc", compatible_libc, f"{libc} {version}; ARM64 TFLite wheel needs glibc >=2.34")
        add(
            "portaudio",
            ctypes.util.find_library("portaudio") is not None,
            "OS shared library lookup",
        )
        add("systemd", shutil.which("systemctl") is not None, "No units changed")
        add(
            "chromium",
            bool(shutil.which("chromium") or shutil.which("chromium-browser")),
            "Binary discovery only",
        )
        add("wayland", bool(os.environ.get("WAYLAND_DISPLAY")), "Run as the intended kiosk user")
        add(
            "voice-python",
            sys.version_info[:2] == (3, 11) if platform.system() == "Linux" else False,
            "voice-edge.lock includes Linux tflite-runtime 2.14.0; use Python 3.11",
        )
        for name, relative in [
            ("usb", "dev/serial/by-id"),
            ("alsa", "proc/asound/cards"),
            ("drm", "sys/class/drm"),
        ]:
            path = root / relative
            add(
                name,
                path.exists(),
                sorted(p.name for p in path.iterdir())
                if path.is_dir()
                else path.read_text()[:2000]
                if path.is_file()
                else "unavailable",
                False,
            )
    else:
        add(
            "docker",
            shutil.which("docker") is not None,
            "CLI discovery; daemon not contacted",
            False,
        )
    for name, relative in [("memory", "proc/meminfo"), ("os", "etc/os-release")]:
        path = root / relative
        add(
            name,
            path.is_file(),
            path.read_text()[:2000] if path.is_file() else "unavailable",
            False,
        )
    disk = shutil.disk_usage(Path.cwd())
    add("workspace-free-bytes", disk.free > 2 * 1024**3, disk.free, False)
    return {
        "role": role,
        "read_only": True,
        "ready": all(c["ok"] for c in checks if c["required"]),
        "checks": checks,
    }


def validate_config(role):
    from apps.config import EdgeSettings, ServerSettings
    from packages.assets import AssetCatalog

    try:
        config = EdgeSettings() if role == "edge" else ServerSettings()
        databases = [config.journal_path] if role == "edge" else [config.database_path]
        if role == "edge" and config.voice.enabled:
            databases.append(config.voice.state_path)
        for path in databases:
            if not path.parent.is_dir() or not os.access(path.parent, os.W_OK):
                raise ValueError("State directory missing or not writable")
            if path.exists() and not os.access(path, os.R_OK | os.W_OK):
                raise ValueError("Database permissions missing")
        if role == "edge" and not config.simulate_hardware:
            if not config.serial_port or not Path(config.serial_port).exists():
                raise ValueError("Explicit stable Feather port missing")
            if not os.access(config.serial_port, os.R_OK | os.W_OK):
                raise ValueError("Feather permissions missing")
        manifests = []
        if role == "edge" and config.voice.enabled:
            if config.voice.asset_manifest is None:
                raise ValueError("Voice manifest missing")
            manifests.append((config.voice.asset_manifest, config.voice.asset_root))
        if role == "server" and config.speech.enabled:
            if config.speech.asset_manifest is None:
                raise ValueError("Speech manifest missing")
            manifests.append((config.speech.asset_manifest, config.speech.asset_root))
        for manifest, assets in manifests:
            catalog = AssetCatalog(manifest, assets)
            for name in catalog.assets:
                catalog.path(name)
        return {
            "ok": True,
            "detail": "Settings and configured model hashes validated; devices remain unopened",
        }
    except Exception:
        return {
            "ok": False,
            "detail": "Configuration or assets invalid; inspect locally without sharing secrets",
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", choices=["edge", "server"], default="edge")
    parser.add_argument("--validate-config", action="store_true")
    args = parser.parse_args()
    report = inspect(args.role)
    if args.validate_config:
        report["configuration"] = validate_config(args.role)
        report["ready"] &= report["configuration"]["ok"]
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["ready"] else 1)


if __name__ == "__main__":
    main()
