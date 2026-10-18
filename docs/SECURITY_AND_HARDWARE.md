# Security boundaries and hardware verification

## Implemented boundaries

Operator and per-device credentials are distinct, required, redacted in settings,
and never sent in browser bundles or URLs. The gateway exposes only typed
brightness/display/status commands. It has no shell, filesystem, arbitrary serial,
raw-network or Home Assistant action. The text agent supports explicitly selected
cloud inference only after a backend configuration opt-in. Device credentials cannot
call operator HTTP endpoints. Browser Origins cannot connect to the edge endpoint.
The Phase 3 tool executor additionally enforces argument schemas, device
allowlists, mutation permissions, confirmation blocks and execution bounds.

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
transcripts are stored by the edge. Text conversations and bounded response
receipts are memory-only on the backend, expire after 60 idle seconds by default,
and are isolated by authenticated principal/device. No transcript persistence was added.
The legacy voice path still records WAVs and logs transcripts; use its privacy
behavior knowingly until the new voice pipeline replaces it.

Protect private configuration files, journal directories and backups. Use TLS
outside loopback, restrict the homelab firewall and reverse proxy, keep access logs
from recording credentials, and use one backend process. Credential rotation,
revocation UI, browser sessions and comprehensive deployment security review remain
later work. There is no automatic provider fallback. Cloud inference requires
explicit selection and opt-in; prompts/context/tool results then go to that
provider. Ollama endpoints/models must actually use local inference when required.

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

## Phase 3 agent trust boundary

Optional scoped backend clients use distinct tokens and per-client device allowlists;
they cannot use operator routes. Origin headers are rejected on agent routes.
Callers sharing one token share a principal, so use separate credentials when
session isolation is required. Guessed foreign session IDs return 404. Context is
bounded, resettable and periodically expired. API summaries exclude raw arguments,
raw results and private provider reasoning. Validation/provider/handler failures
are redacted to stable codes; secret values are redacted in settings serialization.

The model cannot grant itself permission or supply confirmation. Sensitive and
confirmation-required tools are blocked; ordinary mutations require both backend
and principal permission. Native mirror tools use the existing correlated gateway
and edge journal. Timeout/cancellation can leave an external mutation indeterminate;
connection closure is not rollback. There is no generic durable MCP action journal.

MCP servers and their schema/content are untrusted. Only exact administrator
allowlists, trusted descriptions and explicit permission metadata enter the tool
registry; external schema references are forbidden. Sampling, roots, elicitation,
resources, prompts and external log forwarding are not enabled. Stdio processes
receive the SDK's restricted OS environment plus explicitly configured variables,
not the whole backend environment. Stdio is not a hostile-code sandbox; approved
executables and remote accounts must themselves have minimal privileges. Remote
MCP requires TLS except isolated loopback tests and fixed, validated endpoints.
Never allowlist arbitrary shell/filesystem/network or unrestricted HA services.

See [PHASE3_AGENT.md](PHASE3_AGENT.md) for retention, retry tombstones and routing
limitations. No hardware procedures above were executed during Phase 3.
