# Feather Backlight Control

Adafruit Feather M4 Express (CircuitPython) generates a 0-2V analog dimming
signal on pin **A0** to control an LCD panel's backlight, driven by brightness
commands sent from a Raspberry Pi over USB serial.

Status: verified working — CircuitPython 10.3.1 flashed, `boot.py`/`code.py`
deployed, and brightness commands confirmed round-tripping (`B50` -> `OK 50`)
over the data serial port.

## Repository layout

```
feather/
  boot.py               # enables the second ("data") USB CDC serial port
  code.py                # reads brightness commands, drives the A0 DAC
pi/
  feather_backlight.py   # Pi-side client: FeatherBacklight class + CLI
```

## Hardware

- Feather M4 Express plugged into the Raspberry Pi via USB.
- Feather **A0** -> LCD backlight controller's analog dimming input.
- Feather **GND** -> LCD backlight controller's GND (shared reference, required
  for an accurate analog signal even though USB already grounds the Pi/Feather).
- The SAMD51's DAC on A0 outputs a clean DC level (not PWM), so no external
  filtering is required. A small decoupling cap (e.g. 0.1uF) at the panel's
  input is optional if you see noise over long wire runs.

## Feather setup

### 1. Flash CircuitPython (skip if already installed)

1. Double-click the Feather's reset button to enter the UF2 bootloader; a
   `FEATHERBOOT` drive appears.
2. Download and drag on the `.uf2` for this board:
   [CircuitPython 10.3.1 for Feather M4 Express](https://downloads.circuitpython.org/bin/feather_m4_express/en_US/adafruit-circuitpython-feather_m4_express-en_US-10.3.1.uf2)
3. The board reboots automatically and a `CIRCUITPY` drive appears.

### 2. Deploy the firmware files

1. Copy [feather/boot.py](feather/boot.py) and [feather/code.py](feather/code.py)
   to the root of the `CIRCUITPY` drive.
2. Power-cycle the board (unplug/replug, or a single press of reset) —
   `boot.py` only runs on a hard boot, not on a `code.py` save/auto-reload.
3. This creates a second USB serial interface ("data") separate from the
   console/REPL, so the Pi can send commands without colliding with the REPL.
   The board will enumerate as two serial ports (e.g. two `/dev/ttyACM*` on
   the Pi, or two `COM*` ports on Windows) — the second one is the data port.

### Calibrating the 2V max

`code.py` assumes `VDDANA` is 3.3V and scales the DAC so 100% maps to 2.0V.
Set brightness to 100% and measure the actual voltage at A0 with a multimeter;
if it's off, adjust `DAC_FULL_SCALE_VOLTS` in [feather/code.py](feather/code.py)
to match (e.g. if you measure 2.1V at 100%, scale down VDDANA accordingly).

## Raspberry Pi setup

```bash
pip install pyserial
```

Use [pi/feather_backlight.py](pi/feather_backlight.py) directly:

```bash
python3 pi/feather_backlight.py 75   # 75% brightness
python3 pi/feather_backlight.py 0    # backlight off
```

Or import it in your own code:

```python
from feather_backlight import FeatherBacklight

with FeatherBacklight() as backlight:
    backlight.set_brightness(50)
```

The port is auto-detected by matching Adafruit's USB vendor ID (0x239A) and
picking the second (data) CDC interface. Pass `port="/dev/ttyACM1"` explicitly
if auto-detection picks the wrong interface on your system.

### Integrating into another program

`FeatherBacklight` is the only public surface needed:

- `FeatherBacklight(port=None, baudrate=115200, timeout=1.0)` — opens the
  connection; raises `RuntimeError` if no Feather is found and no `port` was
  given.
- `set_brightness(percent)` — clamps to 0-100, sends the command, waits for
  `OK`/`ERR`, returns the applied percent. Raises `RuntimeError` on `ERR` or a
  missing/garbled reply.
- `close()` / context manager (`with FeatherBacklight() as backlight:`).

Reuse a single `FeatherBacklight` instance for the lifetime of your program
rather than reconnecting per call — opening the serial port has a brief
settle delay (~0.2s).

## Protocol

Newline-terminated ASCII commands over the data serial port:

| Direction | Message | Meaning |
|---|---|---|
| Pi -> Feather | `B75\n` | Set brightness to 75% (maps to 0-2V) |
| Feather -> Pi | `OK 75\n` | Acknowledges the new brightness (sent as soon as the fade starts, not when it finishes) |
| Feather -> Pi | `ERR <msg>\n` | Bad command or value |

On the Feather, each `B<pct>` command eases the DAC from its current level to
the new target over 1.5s (ease-out: fast at first, slowing into the target)
instead of snapping instantly — see `FADE_DURATION_S`/`update_fade()` in
[feather/code.py](feather/code.py). Sending a new `B<pct>` mid-fade smoothly
retargets from the DAC's current in-flight value, no jump.

## Troubleshooting

- **Data port doesn't respond at all**: make sure `boot.py` actually ran (hard
  reset required after copying it) and that your serial client asserts
  DTR/RTS when opening the port. CircuitPython's USB CDC stack (TinyUSB) will
  not flush writes to a client that hasn't raised DTR — pyserial on Linux does
  this automatically, but Windows tools like .NET's `SerialPort` default to
  `DtrEnable = false` and need it set explicitly.
- **`TypeError` mentioning `bytearray` in the console**: CircuitPython's
  `bytearray` doesn't support `del buf[:n]` slice deletion like CPython does;
  `code.py` already works around this by reassigning
  `buffer = buffer[idx + 1:]` instead.
- **Check for tracebacks**: connect to the console (first) serial port, press
  Ctrl-C then Ctrl-D to soft-reload, and read back any traceback printed
  before "Code done running."
