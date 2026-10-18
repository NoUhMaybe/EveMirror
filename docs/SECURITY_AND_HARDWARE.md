# Security boundaries and hardware verification

Phase 6 introduces a dedicated browser boundary described in
[PHASE6_DASHBOARD.md](PHASE6_DASHBOARD.md). Browser access defaults off; reviewed
HTTPS origins and explicit per-mirror grants are required. Short-lived pairing
approval needs the separate operator credential in a trusted terminal. Persistent
256-bit opaque credentials live in Secure/HttpOnly/SameSite=Strict host cookies,
with only hashes in SQLite, rotating renewal, expiration and revocation. Exact
Host/Origin/scheme, Fetch Metadata and CSRF protect browser APIs. No wildcard CORS,
privileged JS token, cookie query parameter, raw tool dispatch or provider setting
is added. Browser scope delegates one voice principal; captions and home controls
are separately opt-in. Physical kiosk profile theft still exposes that delegated
session: protect its user/profile and revoke it after loss. Rate-limit pairing at
the reviewed proxy if required; bounded local capacity is not distributed abuse
protection. Static CSP rejects runtime eval and third-party connections.

Trust proxy headers only from the actual reverse proxy, keep the backend port
private and retain TLS certificate verification. Browser mute requires the current
edge's persisted-state acknowledgment; Stop requests correlated session cancellation
and does not dismiss alarms. Neither constitutes hardware mic isolation or proof
of physical audio. Rendering uses capped shader/static presets but no Pi benchmark
or native mirror resolution has been verified. Kiosk examples do not change
Wayland/HDMI, boot configuration, rotation, display sleep/wake or hardware ownership.

## Implemented boundaries

Operator and per-device credentials are distinct, required, redacted in settings,
and never sent in browser bundles or URLs. The gateway exposes only typed
brightness/display/status commands. It has no shell, filesystem, arbitrary serial,
or raw-network action. The text registry separately exposes restricted native
Home Assistant/media actions only after configuration and explicit authorization.
The text agent supports explicitly selected
cloud inference only after a backend configuration opt-in. Device credentials cannot
call operator HTTP endpoints. Browser Origins cannot connect to the edge endpoint.
The tool executor additionally enforces argument schemas, device
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
and are isolated by authenticated principal/device. Phase 4 persists native action
receipts, hashed turn replay identities, timer names/alarms and scoped presentation
state/events in SQLite. It does not intentionally store full transcripts or model
response text. Treat the database and backups as private user data; replay records
are retained until reviewed maintenance and bounded capacity fails closed.
Phase 5's configurable voice path keeps input/output PCM, captions and context in
bounded memory. Captions have a short TTL and a separate non-durable API; device
voice grants create narrow `voice:<device>` principals through the existing tools.
Scoped clients need explicit `allow_voice_state` delegation to see a device's
captions and voice-owned widget state. That delegation is read-only and excludes
other principals' private data. Raw audio stays local to the STT/TTS hosts; an
explicitly selected cloud LLM still receives text/context/tool results.
The legacy voice path still records WAVs and logs transcripts; its separate
privacy behavior remains relevant when using the retained entry points.

Software mute drops microphone frames before copying/queuing/resampling and
suppresses inference/uploads; it does not disconnect the OS audio device. Capture
is half duplex during processing/output with bounded echo tails, without acoustic
echo cancellation or voice barge-in. Programmatic cancellation discards results
and cooperatively stops native work; it cannot undo an issued external action.
Asset manifests must contain independently trusted hashes and all runtime model
files. Models are not downloaded on demand. Keep inference/SDK debug logs disabled
when they could expose private text.

Protect private configuration files, journal directories and backups. Use TLS
outside loopback, restrict the homelab firewall and reverse proxy, keep access logs
from recording credentials, and use one backend process. Credential rotation,
revocation UI, browser sessions and comprehensive deployment security review remain
later work. There is no automatic provider fallback. Cloud inference requires
explicit selection and opt-in; prompts/context/tool results then go to that
provider. Ollama endpoints/models must actually use local inference when required.

Native HA requires exact approved entities/actions, per-client entity grants,
fresh capability discovery and the existing mutation opt-in. Arbitrary service
names, locks/alarms, scripts, shell commands and broad conversation-agent access
are not exposed. An action acknowledgment is distinguished from verified observed
state. Timeouts leave a durable unknown outcome; retries do not resend it. Do not
configure broad parallel HA MCP tools to bypass this boundary. Administrator-added
MCP tools retain their separately reviewed generic policy and are not covered by
the native HA journal. Use a dedicated least-privilege HA account/token, a verified
TLS proxy or explicit trusted-LAN HTTP opt-in; unrelated MCP TLS rules remain intact.

Weather and search use fixed administrator-configured endpoints, bounded requests,
no redirects and no environment proxy inheritance. Search is read-only and optional;
it filters unsafe result URLs and does not fetch result pages. Snippets are untrusted
data and cannot grant tool permission. Configured secrets are redacted from tool
results, final assistant text and application API output, including reflected
credentials. Do not put secrets into user timer names or trust upstream content.

Application snapshots/events enforce principal/device scopes and omit conversation
history. Events have durable bounded retention; alarms remain in authoritative
storage until acknowledged. The API rejects browser Origins and edge credentials;
it is not a browser session mechanism. Never ship its operator/service tokens in
React. Phase 5 implements independent audible-alarm scheduling and a durable edge
cache with a bounded offline lease; physical audio acceptance and browser transport
remain pending. Alarm attempt receipts reserve UUIDs before output, preventing
automatic replay after uncertain crashes. This can leave an unheard indeterminate
alarm; pending backend state persists until explicit dismissal. Offline caches may
miss remote cancellation until reconnect, and require sane synchronized UTC. Voice
mute, ordinary stop and network loss preserve an active alarm. See
[PHASE4_SERVICES.md](PHASE4_SERVICES.md) and [PHASE5_VOICE.md](PHASE5_VOICE.md).

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
7. For phase 5, validate microphone disconnect, wake false triggers/cooldown,
   chime echo suppression, VAD, mute, STT, Pi playback/cancellation and follow-up.
   Verify trusted real models, 44.1/48 kHz capture, truthful tool failures and actual
   speaker output. Test alarm priority, offline lease, reboot/receipt reconciliation
   and explicit dismissal. The phase-2 WAV upload test does not satisfy these scenarios.
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
