"""Expose the Feather backlight dimmer to the Eve agent's tool layer.

The firmware (see "backlight Control/feather/code.py") already scales the
0-100% command range onto a 0-2V DAC output, so this module only needs to
forward brightness commands over serial and remember the last value sent
(the wire protocol has no "read current brightness" command).
"""
import importlib.util
import threading
from pathlib import Path
from typing import Dict, Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent
_FEATHER_MODULE_PATH = _REPO_ROOT / "backlight Control" / "pi" / "feather_backlight.py"

_lock = threading.Lock()
_backlight = None
_last_percent: Optional[int] = None


def _load_feather_backlight_class():
    spec = importlib.util.spec_from_file_location("feather_backlight", _FEATHER_MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.FeatherBacklight


def _get_backlight():
    global _backlight
    if _backlight is None:
        feather_backlight_cls = _load_feather_backlight_class()
        _backlight = feather_backlight_cls()
    return _backlight


def set_backlight_brightness(percent: int) -> Dict[str, object]:
    """Set brightness 0-100% (maps to 0-2V on the Feather DAC); returns a result dict."""
    global _last_percent
    percent = max(0, min(100, int(percent)))
    with _lock:
        try:
            backlight = _get_backlight()
            applied = backlight.set_brightness(percent)
            _last_percent = applied
            return {"status": "ok", "brightness_percent": applied}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}


def get_last_known_brightness() -> Optional[int]:
    return _last_percent
