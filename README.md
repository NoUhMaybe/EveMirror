# EveMirror

Local-first smart mirror modernization, developed on `codex/distributed-foundation`.
The **phase 1–3 backend** separates a lightweight Pi edge runtime from an
authenticated FastAPI gateway and provider-independent text agent. The existing
voice application remains available under `legacy/`.

The new runtime transfers PCM audio and validated Feather commands. Text turns
support native Ollama/OpenAI/Anthropic tool calling, permission checks, approved
MCP tools and temporary conversations. It does **not yet** transcribe audio,
synthesize/play speech, schedule timers, or control Home Assistant.
Follow [implementation status](docs/IMPLEMENTATION_STATUS.md)
for completed work, validation evidence and exact next steps.

## Development

Use Python 3.11 or 3.12 and Node 24.4+. On Windows, use `npm.cmd` to avoid changing
PowerShell execution policy. Preserve the existing `.venv` for the legacy voice stack.

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

The React dashboard currently uses the legacy event server. The authenticated
gateway's snapshots are available to operators and edges; browser session and
dashboard integration are still pending. A successful build is not a Pi FPS test.

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
See [the Phase 3 guide](docs/PHASE3_AGENT.md) for configuration, API examples,
provider support, MCP approval, limits, privacy and verification boundaries.

## Further documentation

- [Audit and retained interfaces](docs/BASELINE.md)
- [Architecture and phased migration](docs/ARCHITECTURE.md)
- [Protocol and failure semantics](docs/PROTOCOL.md)
- [Setup, recovery and configuration](docs/DEVELOPMENT.md)
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
packages/            Shared protocol
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
