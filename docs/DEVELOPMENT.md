# Development and deployment examples

These configurations are prepared for review. No Docker daemon, systemd service,
homelab VM or hardware deployment was modified during development.

## Install and validate

Phase 7 validation also runs `python scripts/simulate_presence.py` and
`python scripts/simulate_voice.py`. Presence tests use fake monotonic clocks,
simulated readings and the real journal/transport, with no physical device access.
Use `python scripts/preflight.py --role edge` for read-only readiness reporting;
`--validate-config` verifies configured settings/assets without opening devices.
A nonzero result means required readiness gates failed, including on this Windows
development host. Do not install or change services to hide those findings.

See the [deployment plan](PHASE7_DEPLOYMENT_PLAN.md) for disposable container CI,
Linux speech-library installation checks and ARM64 wheel availability. Current
Linux voice-edge pins need Python 3.11; the TFLite ARM64 wheel needs glibc >=2.34.
Wheel downloads do not establish actual Pi compatibility. The
[acceptance guide](PHASE7_HARDWARE_ACCEPTANCE.md) includes read-only host sampling,
performance procedures and separately authorized physical stages.

Use a separate virtual environment, Python 3.11–3.12, and Node 24.4+. Linux:

```sh
python3.12 -m venv .venv-dev
.venv-dev/bin/python -m pip install -r requirements/dev.lock
.venv-dev/bin/python -m pip install --no-deps -e .
.venv-dev/bin/python -m ruff check apps packages scripts tests
.venv-dev/bin/python -m ruff format --check apps packages scripts tests
.venv-dev/bin/python -m pytest -q
.venv-dev/bin/python scripts/simulate.py
cd apps/dashboard
npm ci
npm test
npm run typecheck
npm run build
```

On Windows use `py -3.12 -m venv .venv-dev`, `.venv-dev\Scripts\python.exe`,
and `npm.cmd`. No activation or execution-policy modification is needed.

The `requirements/*.lock` files pin the tested foundation dependency versions.
`common` contains protocol/config/transport; `edge` adds pyserial; `server` adds
FastAPI/Uvicorn, HTTP, official OpenAI/Anthropic/MCP SDKs, IANA tzdata and JSON Schema validation;
`dev` adds test/lint/legacy-weather HTTP dependencies. Edge locks do not include
provider or MCP SDKs. Native audio, transcription and Piper packages are outside
the base roles. `audio.lock` adds NumPy/SoXR to development tests; `voice-edge.lock`
and `voice-server.lock` supply isolated optional runtime dependencies. Neither
voice role needs Torch or NVIDIA packages. Linux voice-edge requires Python 3.11
because openWakeWord's Linux dependency includes a Python-3.11 TFLite wheel;
our actual wake/VAD inference uses ONNX. Linux/Pi installation remains unverified.
The old unpinned `legacy/client/requirements.txt` and `legacy/agent/requirements.txt`
still describe the legacy environment, including its NVIDIA dependencies.

To update dependencies, resolve in a new environment, run all relevant checks,
and update the lockfiles deliberately. Keep lockfiles in Git; dependencies,
generated configs, build outputs, caches and recordings stay ignored.

## Run separate processes

Configuration is environment-only; the applications do not implicitly read a
working-directory `.env` file. systemd and Compose explicitly load their named
private files. Generate distinct 32+ character tokens, e.g. with
`python -c "import secrets; print(secrets.token_urlsafe(32))"`.

In the backend environment set `EVE_SERVER_OPERATOR_TOKEN` and
`EVE_SERVER_EDGE_TOKENS` (JSON object mapping device IDs to their tokens), then run:

```sh
uvicorn apps.server.main:create_app --factory --host 127.0.0.1 --port 8000 \
  --workers 1 --ws-max-size 24000 --ws-max-queue 8 --no-access-log
```

In another environment set `EVE_EDGE_DEVICE_ID`, matching `EVE_EDGE_TOKEN`, and
`EVE_EDGE_SERVER_URL=ws://127.0.0.1:8000` for development:

```sh
python -m apps.edge.runtime --simulate-hardware
```

With voice disabled, use `--upload-wav path/to/fixture.wav` to upload one existing 16 kHz PCM16 mono
fixture and exit. It does not transcribe the fixture. Normal runtime remains
connected and accepts typed hardware commands.

For a remotely hosted server, use a verified `wss://` origin, the same private
device token at both endpoints, and the real serial data-interface path. Never
use `--simulate-hardware` for hardware acceptance. Insecure LAN WebSockets require
`EVE_EDGE_ALLOW_INSECURE_LAN=true`; this is an explicit isolated-development option.

## Server container example

Copy `deploy/server/server.env.example` to `deploy/server/server.env`, replace the
invalid placeholders, and restrict file permissions. Then, when authorized to run
the development container, use `docker compose -f deploy/server/compose.yaml up --build`.
The example binds only loopback. A TLS reverse proxy must forward the WebSocket
upgrade and Authorization header, limit HTTP bodies (e.g. 32 KiB), avoid logging
headers, and expose only the intended LAN host. Do not disable certificate verification.

The default image installs only server dependencies and runs as an unprivileged
user with a read-only filesystem. It does not contain LLMs, microphone drivers,
speaker playback or the React application. Building/running this Docker example
was not validated in the Windows development session. The Compose example mounts
a named `eve-data` volume at `/var/lib/eve` and sets the SQLite path there. The
image prepares that directory for UID 10001. Preserve this volume and its WAL;
one process owns the database. Local runs default to `data/server.sqlite3`.

## Edge systemd example

After hardware deployment is separately authorized, install the package under
`/opt/evemirror` into `.venv` using `requirements/edge.lock` and `pip install --no-deps .`.
Create a dedicated `evemirror` service user, confirm the OS's serial/audio groups,
and review `deploy/edge/evemirror-edge.service`. Set matching credentials and the
verified data-interface path in `/etc/evemirror/edge.env` using the example.
Restrict credentials to the administrator/service user. The unit creates a private
state directory and restarts failures. Do not enable it alongside the old serial
controller. Kiosk and presence deployment remain later phases. Optional voice uses the same
single unit with `voice-edge.lock`; configure private manifests and audio devices
as described in [PHASE5_VOICE.md](PHASE5_VOICE.md). It defaults to muted.

## Model artifacts

The edge transport requires no model. The Phase 3 text agent needs an explicitly
configured tool-capable model endpoint; weights are not bundled or downloaded. Legacy voice operation still needs the
custom Hey Eve ONNX, openWakeWord melspectrogram/embedding models, and a Piper
ONNX voice plus its matching JSON config. Obtain the custom model from a trusted
training export/private backup; it is not reproducible from a fresh Git clone
without that artifact or a training run. Use documented upstream releases for
feature models and check the selected voice's license.

Copy trusted assets into an ignored `.assets/` directory and maintain a private
manifest containing the trusted SHA-256 for each file:

```json
{"hey_eve": {"path": "hey_eve.onnx", "sha256": "<64 hex digits from trusted release>"}}
```

Run `python scripts/verify_assets.py --manifest path/to/private-manifest.json --root .assets`.
Missing, empty, corrupted files and paths outside the artifact directory fail
verification. Hashing an untrusted download and then accepting that same hash is
not authenticity verification. Legacy scripts still use their historical model
paths under `training/wake_word/` and their existing download behavior. Phase 5's
new wake/VAD and STT/Piper paths require verified manifests and never implicitly
download weights. See [PHASE5_VOICE.md](PHASE5_VOICE.md) for role-specific manifests,
the complete Whisper local directory and explicit installation/smoke commands.
Do not commit models or training datasets during migration.

## Recovery and backup

- Backend restart: edge reconnects with backoff. Transport state/counters reset;
  conversation context/response text expire, but timers, alarms, native operation
  receipts, turn replay markers and semantic state survive. Overdue timers create
  one pending alarm on recovery, with their original deadline as expiry. In-flight
  external actions remain indeterminate; no automatic mutation replay occurs.
- Edge restart: command journal survives. A command interrupted before ACK
  persistence remains indeterminate and cannot be executed again under its ID.
- Serial disconnect: report unavailable/invalid/indeterminate acknowledgment;
  next explicit command attempts a new port open. No blind replay occurs.
- Audio failure/disconnect: discard the bounded buffer. The caller may submit
  a newly recorded utterance once reconnected, with a new session.
- Weather failure: bounded-age cached results identify stale status, source time
  and acquisition time; absent/too-old cache produces an error. Phase 4 raw HTTP
  caches are memory-only; selected weather presentation state survives restart.
- Database failure: persistent tools/snapshots become unavailable without resetting
  damaged storage. The gateway continues; the scheduler periodically retries open.
  Restore or repair explicitly. Unknown schema versions and failed migrations fail closed.

Back up private environment files securely and use SQLite's backup API for the
edge journal (or stop the edge before copying its database). Do not copy only a
live `.sqlite3` file and omit its WAL. Preserve permissions on restore. A restored
old journal may lack newer command IDs; expired deadlines prevent old requests
from executing, and operators must not blindly issue a fresh ID after an uncertain action.

Back up the server database with `python scripts/backup_database.py --source
data/server.sqlite3 --destination backups/server-2026-10-17.sqlite3` after creating
the destination directory. It uses SQLite's online backup API and requires a new
destination file. Stop the backend before restoring. Old backups can lack newer
turn/action identities, so restoration does not authorize replaying uncertain
requests. See [PHASE4_SERVICES.md](PHASE4_SERVICES.md) for storage, alarm and
receipt-capacity policies. Phase 5 adds a separate `edge-voice.sqlite3` journal for
mute, timer cache, alarm attempt receipts and offline dismissals. Back it up with
the same SQLite backup API. Preserve its device identity and replay records;
unknown attempts must not be replayed. Its default offline cache lease is 24 hours.

For Zabbix, monitor `/health/live` locally and authenticated `/api/health` for edge
online status, last heartbeat, serial metadata, error count and audio counters.
Provider configuration is visible at `/api/agent/status`; it is not a live
inference health probe. Service diagnostics also report database/weather/home/search
configuration and availability; they are not full upstream health probes. HA and
search default to unconfigured; STT/TTS are optional and disabled until configured.
Nested voice health includes local engine readiness/busy/errors and last edge
audio state. Voice captions use a separate scoped volatile API, not durable logs.
Latency histograms, resource
metrics and full readiness probes remain production-hardening work.

## Phase 3 text development

Use the same backend process. Set `EVE_SERVER_LLM_PROVIDER=ollama`, an explicit
`EVE_SERVER_OLLAMA_MODEL` and optional `EVE_SERVER_OLLAMA_BASE_URL`. Without a model
the transport still runs and the agent reports unconfigured. Cloud use requires
explicit `EVE_SERVER_ALLOW_CLOUD=true` and the chosen provider's backend-only
model/key. There is no automatic fallback or per-turn routing override. Do not
put an operator, edge or provider token into the frontend.

In a trusted terminal set `EVE_AGENT_TOKEN` to an optional scoped client credential
(or use the operator token for development), then run `python scripts/chat.py
--device mirror-1`. Commands are `/reset`, `/status`, `/quit`; Ctrl+C requests
cancellation. Sessions expire after 60 idle seconds. `/reset` clears model context,
retaining bounded retry receipts until expiry.

`python -m pytest -q` now exercises all three actual adapters with mocked HTTP, a
real isolated MCP stdio server, authenticated loopback MCP HTTP, the CLI and the
gateway/simulated edge hardware path. It needs no installed model, cloud key or
Home Assistant. `scripts/simulate.py` remains the independent Phase 2 transport
check. Hosted CI additionally runs that simulation and `pip check`.

[PHASE3_AGENT.md](PHASE3_AGENT.md) documents every setting and boundary, including
MCP process/remote configuration, tool approval, timeouts, context/receipt limits,
provider-specific capabilities and exactly what remains unverified live. MCP is
disabled by default. Enable brightness only deliberately via
`EVE_SERVER_AGENT__ALLOW_MUTATIONS=true`; live hardware acceptance remains a
separately authorized deployment task.

## Phase 4 service development

Use the same process and text API, with `EVE_SERVER_AGENT__ALLOW_MUTATIONS=true`
for timer creation and other approved changes. Scoped clients additionally need
their own mutation permission and explicit HA entity grants. Configure weather,
native HA/media and optional SearXNG using `deploy/server/server.env.example` and
[PHASE4_SERVICES.md](PHASE4_SERVICES.md). Missing optional integrations are not
advertised as working tools. Keep credentials in private backend configuration.

`GET /api/application/state` and `/api/application/events?after=0&limit=100` accept
the existing operator or scoped agent Bearer credentials and reject browser
Origins/device credentials. These remain trusted-service APIs alongside the new
paired browser API. Polling events uses durable revisions; reconnect from a
snapshot if the server reports `snapshot_required`.

Regenerate both contracts with `python scripts/export_protocol.py` and
`python scripts/export_application.py`. The full Python suite includes fake-clock
timer recovery/races, WAL backup/restore, weather/DST/stale cases, restricted HA/media,
search security, private snapshots/events and all three real provider adapters
using mocked HTTP. No live service is required. Retain `legacy/` until voice and
dashboard consumers and physical voice acceptance complete.


## Phase 5 voice development

Use [PHASE5_VOICE.md](PHASE5_VOICE.md) for isolated edge/server dependency locks,
private asset manifests, explicit speech/device permissions, capture/output devices,
mute controls, finite alarm tones and startup/recovery. `scripts/simulate_voice.py`
runs full authenticated loopback turns using fixture audio/models for all three
provider adapters, plus offline/restart and privacy failures. It needs no physical
audio device or model. `scripts/speech_smoke.py --help` describes explicit local
real-engine checks with trusted assets and existing fixtures; these were not run
against real models during implementation.

Server containers opt into speech with build argument `EVE_INSTALL_SPEECH=1` and
a reviewed read-only asset mount; no model is included in the image. Edge software
mute suppresses capture processing, not the operating system microphone device.
Programmatic voice stop and network loss preserve active alarms; explicit dismissal
is separate. Half-duplex suppression has no acoustic echo cancellation/barge-in.

## Phase 6 dashboard development

Use [PHASE6_DASHBOARD.md](PHASE6_DASHBOARD.md) for the paired cookie API, exact
loopback/TLS origins, grants, trusted administrator CLI, production static host,
Vite same-origin proxy, Chromium fixture and kiosk/recovery instructions. No
privileged credential belongs in a frontend environment variable. Browser captions
are an explicit delegation of the assigned mirror's voice principal.

After Python schema edits run both exporters, then `npm run contracts` from
`apps/dashboard`. Run `npm run contracts:check`, `npm run format:check`, `npm test`,
`npm run typecheck` and `npm run build`. Set `EVE_TEST_PYTHON` to your absolute dev
Python, install Chromium with `npx playwright install chromium`, then run
`npm run test:browser`. On Linux CI installation also uses `--with-deps`. The
opt-in loopback fixture binds 8766, requires a production build and uses temporary
data with simulated audio/models/services only. It must not run next to the old
relay on that port. Screenshots/traces in `test-results/` are ignored fixture
artifacts; inspect them when changing layout. No pixel-perfect golden baseline is
claimed. Keep test controls out of packaged production apps.

The server Dockerfile builds static assets in a Node stage. Browser enablement and
grants remain explicit. Examples do not enable a Pi unit, edit compositor/HDMI
rotation, contact live services or establish real GPU/audio performance.
