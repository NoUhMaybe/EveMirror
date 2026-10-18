# EveMirror

Local-first smart mirror modernization, developed on `codex/distributed-foundation`.
The new **phase 1–2 foundation** separates a lightweight Pi edge runtime from an
authenticated FastAPI gateway. The existing voice application remains available.

The new runtime currently transfers PCM audio and validated Feather commands.
It does **not yet** transcribe, call LLM tools, synthesize/play speech, schedule
timers, or control Home Assistant. Follow [implementation status](docs/IMPLEMENTATION_STATUS.md)
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
cd dashboard
npm.cmd ci
npm.cmd test
npm.cmd run typecheck
npm.cmd run build
```

The React dashboard currently uses the legacy event server. The authenticated
gateway's snapshots are available to operators and edges; browser session and
dashboard integration are still pending. A successful build is not a Pi FPS test.

## Further documentation

- [Audit and retained interfaces](docs/BASELINE.md)
- [Architecture and phased migration](docs/ARCHITECTURE.md)
- [Protocol and failure semantics](docs/PROTOCOL.md)
- [Setup, recovery and configuration](docs/DEVELOPMENT.md)
- [Security, privacy and hardware verification](docs/SECURITY_AND_HARDWARE.md)
- [Legacy voice startup and historical design](README)

Do not run the legacy serial controller and new edge controller simultaneously.
The known-working Feather firmware is unchanged. Nothing in this branch deploys,
flashes or changes connected devices automatically.
