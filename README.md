# EveMirror

Local-first smart mirror modernization, developed on `codex/distributed-foundation`.
The **phase 1–6 runtime** separates a lightweight Pi edge runtime from an
authenticated FastAPI gateway and provider-independent text agent. The existing
voice application remains available under `legacy/`.

The new runtime transfers PCM audio and validated Feather commands. Text turns
support native Ollama/OpenAI/Anthropic tool calling, permission checks, approved
MCP tools and temporary conversations. Persistent timers/alarms, Open-Meteo weather,
restricted Home Assistant/media controls, optional SearXNG search and scoped
semantic state/events use that same agent. HA and search require configuration;
mutations require explicit permission. Optional distributed voice adds local Pi
wake/VAD capture, server CPU INT8 faster-whisper and Piper, bounded Pi playback,
follow-up listening and durable offline alarm scheduling. Voice requires separately
installed dependencies, trusted model assets and explicit configuration; physical
audio and real inference acceptance remain pending.
Follow [implementation status](docs/IMPLEMENTATION_STATUS.md)
for completed work, validation evidence and exact next steps.

## Development

Use Python 3.11 or 3.12 and Node 24.4+. On Windows, use `npm.cmd` to avoid changing
PowerShell execution policy. Preserve the existing `.venv` for the legacy voice stack.
The optional Linux voice-edge dependency set requires Python 3.11; see the
[Phase 5 setup guide](docs/PHASE5_VOICE.md) for isolated role environments.

```powershell
py -3.12 -m venv .venv-dev
.\.venv-dev\Scripts\python.exe -m pip install -r requirements/dev.lock
.\.venv-dev\Scripts\python.exe -m pip install --no-deps -e .
.\.venv-dev\Scripts\python.exe -m pytest -q
.\.venv-dev\Scripts\python.exe scripts/simulate.py
```

The simulation starts an ephemeral loopback server, generates temporary scoped
credentials, connects a simulated Feather, sends a brightness command and uploads
an in-memory audio fixture. It requires no hardware, models or live services.

```powershell
cd apps/dashboard
npm.cmd ci
npm.cmd test
npm.cmd run typecheck
npm.cmd run build
```

The modular React dashboard pairs with Eve Server using its own scoped HttpOnly
cookie. It reads authoritative state/events for voice, subtitles, weather, timers,
alarms and approved home/media controls. It no longer connects to the legacy relay.
Browser access defaults to disabled; use the [Phase 6 guide](docs/PHASE6_DASHBOARD.md)
for TLS, exact origins/grants, administrator pairing, recovery and kiosk examples.
Operator, provider and edge tokens stay outside JavaScript. A successful build and
desktop browser tests do not establish Pi FPS or live hardware acceptance.

For browser integration tests, set `EVE_TEST_PYTHON` to the absolute path of the
development Python executable, then run `npx playwright install chromium` and
`npm run test:browser` after building. The isolated loopback fixture runs real
edge/server/tools with fake audio/models/services. No live device is contacted.

## Text agent

Configure the existing backend credentials and an installed, tool-capable local
model with `EVE_SERVER_OLLAMA_MODEL`. Ollama is the default provider; cloud use
requires explicit configuration and there is no automatic fallback. Missing model
configuration leaves the gateway running and the text API reports a clear error.

Start the backend as described in [DEVELOPMENT.md](docs/DEVELOPMENT.md), then use
a trusted terminal with `EVE_AGENT_TOKEN` set to a scoped agent-client token (or
`EVE_SERVER_OPERATOR_TOKEN` for operator development):

```powershell
.\.venv-dev\Scripts\python.exe scripts/chat.py --device mirror-1
```

Use `/reset` to clear context and `/quit` to exit. Sessions expire after 60 idle
seconds. Time and mirror status are read-only; brightness requires an explicit
backend mutation permission and always uses the existing edge gateway.
See [the Phase 3 guide](docs/PHASE3_AGENT.md) for the agent API and provider setup,
and [the Phase 4 guide](docs/PHASE4_SERVICES.md) for tools, database backup,
HA/media/search configuration, permissions and recovery. Automated service tests
use fixtures; live integrations and audible alarms remain unverified.

## Distributed voice

Follow [PHASE5_VOICE.md](docs/PHASE5_VOICE.md) to install `voice-edge.lock` on the
Pi and `voice-server.lock` on the server, verify private model manifests, configure
device-specific voice grants and select audio devices. Voice defaults to disabled
and the edge defaults to muted. The production path uses the same authenticated
socket, agent, permissions and tools as text; audio stays in memory. Independent
alarms use a durable edge cache and generated local tones without inference.

`python scripts/simulate_voice.py` exercises the complete socket path with fixture
models and speakers. Real-engine smoke commands and the pending Pi acceptance
checklist are in the guide. No real microphone, speaker or model was exercised by
those simulated scenarios. Keep the legacy relay until the dashboard migrates.

## Further documentation

- [Audit and retained interfaces](docs/BASELINE.md)
- [Architecture and phased migration](docs/ARCHITECTURE.md)
- [Protocol and failure semantics](docs/PROTOCOL.md)
- [Setup, recovery and configuration](docs/DEVELOPMENT.md)
- [Persistent timers, weather, home/media, search and semantic state](docs/PHASE4_SERVICES.md)
- [Distributed voice, local models, playback and offline alarms](docs/PHASE5_VOICE.md)
- [Security, privacy and hardware verification](docs/SECURITY_AND_HARDWARE.md)
- [Repository layout and moved paths](docs/REPOSITORY_LAYOUT.md)
- [Legacy voice startup](legacy/README.md)
- [Historical design](docs/archive/LEGACY_STACK.md)

Do not run the legacy serial controller and new edge controller simultaneously.
The known-working Feather firmware is unchanged. Nothing in this branch deploys,
flashes or changes connected devices automatically.

## Repository layout

```text
apps/                Edge runtime, backend and React dashboard
packages/            Schemas, audio/asset helpers and shared weather normalization
firmware/feather_m4/  Preserved CircuitPython firmware
legacy/              Working older voice agent and microphone client
training/wake_word/   Wake-word training tools and ignored local assets
tools/hardware/      Standalone hardware diagnostic client
deploy/              Server and edge deployment examples
requirements/        Pinned foundation dependencies
scripts/             Schema, asset verification and development simulation
tests/               Backend and integration tests
docs/                Current documentation and historical archives
```
