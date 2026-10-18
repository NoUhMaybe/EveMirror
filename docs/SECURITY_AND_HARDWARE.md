# Security boundaries and hardware verification

## Implemented boundaries

Operator and per-device credentials are distinct, required, redacted in settings,
and never sent in browser bundles or URLs. The gateway exposes only typed
brightness/display/status commands. It has no shell, filesystem, arbitrary serial,
raw-network, Home Assistant or cloud-inference action. Device credentials cannot
call operator HTTP endpoints. Browser Origins cannot connect to the edge endpoint.
This is device/operator authorization; the LLM tool permission registry comes later.

The edge alone owns serial. Use a stable, verified data interface. Auto-discovery
only accepts one Adafruit port explicitly identified as a data interface; ambiguous
ports fail closed. Linux opens the port exclusively. Existing firmware behavior,
pin assignments, DAC scaling and ENA polarity are unchanged. No firmware status
query is invented; unknown physical state is represented by null fields.

Raw audio is bounded and memory-only in the new transport. Uploads are not retried
or written to disk. The SQLite edge journal retains request IDs, action fingerprints,
timestamps and full acknowledgments for 24 hours (pruned on new commands). Minimal
ID/fingerprint tombstones persist until the journal is removed, preventing older
IDs from executing again with a newly issued deadline. No tokens, recordings or
transcripts are stored. No conversations are retained by this milestone.
The legacy voice path still records WAVs and logs transcripts; use its privacy
behavior knowingly until the new voice pipeline replaces it.

Protect private configuration files, journal directories and backups. Use TLS
outside loopback, restrict the homelab firewall and reverse proxy, keep access logs
from recording credentials, and use one backend process. Credential rotation,
revocation UI, browser sessions and comprehensive deployment security review remain
later work. No cloud fallback or implicit cloud request is implemented.

## Manual hardware acceptance (all pending)

Record actual results, timestamps, firmware hash and operator before marking passed.
These procedures were not performed in this development session.

1. Confirm Pi model/RAM, OS release, audio device names, serial permissions and
   stable Feather data port. Confirm HDMI image/orientation independently of the
   [historical HDMI diagnosis](archive/HDMI_DEBUGGING.md); preserve a working HDMI configuration.
2. Back up deployed `boot.py` and `code.py`; compare them to repository sources.
   Do not flash anything for this milestone. The new bridge uses the existing protocol.
3. Stop the legacy runtime/controller before starting the new serial owner. Use
   an authenticated operator command with a fresh request UUID to request 35%.
   Verify `B35` / exact `OK 35`, visual fade and stable display signal. ACK alone
   does not verify voltage, physical brightness or fade completion.
4. Under an authorized test window, request zero and verify true backlight off
   after the fade while HDMI stays active; request awake and verify the documented
   current 100% wake target. Confirm electrical behavior using the established
   safe measurement procedure; do not alter pins, voltage scaling or ENA polarity.
5. Unplug Feather and confirm an honest error; reconnect it, then issue a new
   explicit command. Test an invalid/missing ACK and confirm no reported success.
6. Disconnect/restart the backend and verify edge reconnection. Confirm a
   duplicate request ID returns the original result and creates no second fade.
   Review indeterminate results manually before issuing any fresh action.
7. After phase 5, validate microphone disconnect, wake false triggers/cooldown,
   chime echo suppression, VAD, mute, STT, Pi playback/cancellation and follow-up.
   The phase-2 WAV upload test does not satisfy these scenarios.
8. After phase 7, validate actual sensor presence/absence, debounce, unknown state,
   manual override expiry, protected conversations/alarms and offline sleep/wake.

## Firmware evaluation and rollback

Read-target, fade status, protocol version and stable firmware identity would be
useful backward-compatible additions, but they are deferred until a hardware
verification window. Changing deployed firmware is unnecessary for transport
acceptance. Maintain the original `B<pct>` / `OK <pct>` contract.

If a later firmware change is authorized, save the deployed files and hashes,
record the board/CircuitPython version, retain a known-working firmware copy, and
test commands, true off and voltage limits before acceptance. Roll back by restoring
the saved `boot.py`/`code.py` and performing the hardware-approved reset procedure.
Do not infer a CircuitPython version from the old README or flash a suggested UF2
without verifying the connected board and rollback requirements.

## Performance acceptance (pending)

On the real Pi, record edge and Chromium RSS/CPU, GPU/idle load, active FPS,
temperature/throttling, capture/upload/STT/LLM/tool/TTS/playback latency and sustained
behavior. Record selected models, hardware, quality settings and network conditions.
Remote hosting still renders React/Three.js on the Pi. The existing large bundle
and per-frame CPU geometry/SVG work require measurement and phase-6 optimization;
no Pi performance or Intel Arc inference acceleration is claimed here.
