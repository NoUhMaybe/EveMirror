# Development and deployment examples

These configurations are prepared for review. No Docker daemon, systemd service,
homelab VM or hardware deployment was modified during development.

## Install and validate

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
FastAPI/Uvicorn; `dev` adds test/lint/legacy-weather HTTP dependencies. Native
audio, Torch, transcription and Piper packages are deliberately outside these
foundation environments. Linux/Pi wheels and deployment remain CI/hardware checks.
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

Use `--upload-wav path/to/fixture.wav` to upload one existing 16 kHz PCM16 mono
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
was not validated in the Windows development session. Persistent backend timers,
settings storage, migrations and volumes will be added with the corresponding services.

## Edge systemd example

After hardware deployment is separately authorized, install the package under
`/opt/evemirror` into `.venv` using `requirements/edge.lock` and `pip install --no-deps .`.
Create a dedicated `evemirror` service user, confirm the OS's serial/audio groups,
and review `deploy/edge/evemirror-edge.service`. Set matching credentials and the
verified data-interface path in `/etc/evemirror/edge.env` using the example.
Restrict credentials to the administrator/service user. The unit creates a private
state directory and restarts failures. Do not enable it alongside the old serial
controller. Kiosk, wake capture and presence deployment are pending later phases.

## Model artifacts

The phase-2 runtime requires no model. Legacy voice operation still needs the
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
paths under `training/wake_word/` and their existing download behavior; wiring verified discovery into the new wake runtime is
an explicit phase-5 task. Do not commit models or training datasets during migration.

## Recovery and backup

- Backend restart: edge reconnects with backoff. Transport state/counters reset;
  no persistent backend assistant/timer state exists yet. In-flight commands
  become indeterminate; no automatic hardware retry occurs.
- Edge restart: command journal survives. A command interrupted before ACK
  persistence remains indeterminate and cannot be executed again under its ID.
- Serial disconnect: report unavailable/invalid/indeterminate acknowledgment;
  next explicit command attempts a new port open. No blind replay occurs.
- Audio failure/disconnect: discard the bounded buffer. The caller may submit
  a newly recorded utterance once reconnected, with a new session.
- Weather failure in legacy stack: bounded-age cached results carry `stale=true`
  and original acquisition timestamps; absent cache produces an error.

Back up private environment files securely and use SQLite's backup API for the
edge journal (or stop the edge before copying its database). Do not copy only a
live `.sqlite3` file and omit its WAL. Preserve permissions on restore. A restored
old journal may lack newer command IDs; expired deadlines prevent old requests
from executing, and operators must not blindly issue a fresh ID after an uncertain action.

For Zabbix, monitor `/health/live` locally and authenticated `/api/health` for edge
online status, last heartbeat, serial metadata, error count and audio counters.
Model/STT/TTS/HA are explicitly unconfigured; latency histograms, resource metrics,
alarms and full readiness probes remain production-hardening work.
