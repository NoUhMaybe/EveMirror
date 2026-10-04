"""Feather M4: drive a 0-2V analog dimming signal on A0 from Pi commands.

Protocol (newline-terminated ASCII over usb_cdc.data):
  Pi -> Feather: "B<0-100>\n"   set brightness percent
  Feather -> Pi: "OK <pct>\n"   acknowledgement
                 "ERR <msg>\n"  on bad input
"""
import time

import analogio
import board
import usb_cdc

# The SAMD51 DAC output is referenced to VDDANA (~3.3V on the Feather M4).
# AnalogOut takes a 16-bit value (0-65535) scaled internally to the board's
# 12-bit DAC. Capping MAX_DAC_VALUE below TARGET_MAX_VOLTS keeps A0 from ever
# exceeding the panel's 0-2V dimming input, regardless of commanded percent.
# Measure the actual A0 voltage at 100% with a multimeter and adjust
# DAC_FULL_SCALE_VOLTS if it doesn't match your board.
DAC_FULL_SCALE_VOLTS = 3.3
TARGET_MAX_VOLTS = 2.0
MAX_DAC_VALUE = int(65535 * (TARGET_MAX_VOLTS / DAC_FULL_SCALE_VOLTS))

dac = analogio.AnalogOut(board.A0)

serial = usb_cdc.data
if serial is None:
    raise RuntimeError(
        "usb_cdc data serial is not enabled; check boot.py and power-cycle the board"
    )
serial.timeout = 0


def set_brightness_percent(pct):
    pct = max(0, min(100, pct))
    dac.value = int(MAX_DAC_VALUE * (pct / 100))
    return pct


def handle_line(line):
    try:
        cmd = line[:1].upper()
        if cmd == b"B":
            pct = set_brightness_percent(int(line[1:]))
            serial.write("OK {}\n".format(pct).encode("utf-8"))
        else:
            serial.write(b"ERR unknown command\n")
    except ValueError:
        serial.write(b"ERR bad value\n")


# Start at 0% (backlight off) until the Pi sends a command.
set_brightness_percent(0)
buffer = bytearray()

while True:
    n = serial.in_waiting
    if n:
        buffer.extend(serial.read(n))
    idx = buffer.find(b"\n")
    while idx != -1:
        line = bytes(buffer[:idx]).strip()
        buffer = buffer[idx + 1 :]
        if line:
            handle_line(line)
        idx = buffer.find(b"\n")
    time.sleep(0.01)
