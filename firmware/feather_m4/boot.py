import usb_cdc

# Expose a second CDC serial ("data") separate from the REPL console, so the
# Pi can talk to code.py without interfering with the CircuitPython console.
# NOTE: boot.py only runs on a hard reset/power-cycle, not on a code.py save.
usb_cdc.enable(console=True, data=True)
