#!/usr/bin/env python3
"""Control the Feather M4 backlight dimmer from a Raspberry Pi.

Requires pyserial: pip install pyserial

Usage:
    python3 feather_backlight.py 75          # set brightness to 75%
    python3 feather_backlight.py 0           # backlight off
    python3 feather_backlight.py 100 --port /dev/ttyACM1
"""
import argparse
import time

import serial
from serial.tools import list_ports

FEATHER_VID = 0x239A  # Adafruit


def find_data_port():
    """Pick the Feather's second (data) CDC interface, if present."""
    candidates = sorted(
        (p for p in list_ports.comports() if p.vid == FEATHER_VID),
        key=lambda p: p.device,
    )
    if not candidates:
        return None
    # Console enumerates first, data second.
    return candidates[-1].device


class FeatherBacklight:
    def __init__(self, port=None, baudrate=115200, timeout=1.0):
        port = port or find_data_port()
        if port is None:
            raise RuntimeError(
                "Could not find Feather M4 serial port; pass port= explicitly"
            )
        self._ser = serial.Serial(port, baudrate=baudrate, timeout=timeout)
        time.sleep(0.2)  # let the port settle before writing

    def set_brightness(self, percent):
        percent = max(0, min(100, int(percent)))
        self._ser.reset_input_buffer()
        self._ser.write("B{}\n".format(percent).encode("utf-8"))
        reply = self._ser.readline().decode("utf-8", errors="replace").strip()
        if not reply.startswith("OK"):
            raise RuntimeError("Feather reported error: {}".format(reply or "<no response>"))
        return percent

    def close(self):
        self._ser.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("percent", type=int, help="Backlight brightness 0-100")
    parser.add_argument("--port", default=None, help="Serial port (default: auto-detect)")
    args = parser.parse_args()

    with FeatherBacklight(port=args.port) as backlight:
        actual = backlight.set_brightness(args.percent)
        print("Backlight set to {}%".format(actual))


if __name__ == "__main__":
    main()
