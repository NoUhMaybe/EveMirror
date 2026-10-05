"""Feather M4: drive a 0-2V analog dimming signal on A0 from Pi commands.

Protocol (newline-terminated ASCII over usb_cdc.data):
  Pi -> Feather: "B<0-100>\n"   set brightness percent (fades to it, see below)
  Feather -> Pi: "OK <pct>\n"   acknowledgement (sent as soon as the fade starts)
                 "ERR <msg>\n"  on bad input
"""
import time

import analogio
import board
import digitalio
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

# Every brightness change eases from the current DAC level to the new target
# over this many seconds, fast at first and slowing into the target (ease-out).
FADE_DURATION_S = 1.5

dac = analogio.AnalogOut(board.A0)

# A_DIM (board.A0) alone can't reach a true 0% on the backlight driver - it
# has a non-zero dimming floor. D12 drives the driver's ENA pin (measured
# idling ~3.3V when unconnected, i.e. active-high / pulled up by the board)
# to hard-disable the driver once a fade down to 0% finishes, and re-enable
# it before fading back up, for a genuine off instead of a dim floor.
ena = digitalio.DigitalInOut(board.D12)
ena.direction = digitalio.Direction.OUTPUT
ena.value = False

serial = usb_cdc.data
if serial is None:
    raise RuntimeError(
        "usb_cdc data serial is not enabled; check boot.py and power-cycle the board"
    )
serial.timeout = 0

_fade_start_value = 0.0
_fade_target_value = 0.0
_fade_start_time = 0.0
_fade_active = False
_pending_disable = False
_current_value = 0.0  # AnalogOut.value is write-only, so we track it ourselves


def _pct_to_dac_value(pct):
    return MAX_DAC_VALUE * (pct / 100)


def _set_dac(value):
    global _current_value
    _current_value = value
    dac.value = int(value)


def start_fade(pct):
    global _fade_start_value, _fade_target_value, _fade_start_time, _fade_active, _pending_disable
    pct = max(0, min(100, pct))
    _fade_start_value = _current_value
    _fade_target_value = _pct_to_dac_value(pct)
    _fade_start_time = time.monotonic()
    _fade_active = True
    if pct > 0:
        ena.value = True  # enable up front so the fade-up is visible from the start
        _pending_disable = False
    else:
        _pending_disable = True  # disable only once the fade-down finishes (no abrupt cut)
    return pct


def update_fade():
    global _fade_active
    if not _fade_active:
        return
    elapsed = time.monotonic() - _fade_start_time
    if elapsed >= FADE_DURATION_S:
        _set_dac(_fade_target_value)
        _fade_active = False
        if _pending_disable:
            ena.value = False
        return
    t = elapsed / FADE_DURATION_S
    eased = 1 - (1 - t) ** 3  # ease-out cubic: fast start, slow finish
    _set_dac(_fade_start_value + (_fade_target_value - _fade_start_value) * eased)


def handle_line(line):
    try:
        cmd = line[:1].upper()
        if cmd == b"B":
            pct = start_fade(int(line[1:]))
            serial.write("OK {}\n".format(pct).encode("utf-8"))
        else:
            serial.write(b"ERR unknown command\n")
    except ValueError:
        serial.write(b"ERR bad value\n")


# Start at 0% (backlight off) until the Pi sends a command.
_set_dac(0)
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
    update_fade()
    time.sleep(0.01)
