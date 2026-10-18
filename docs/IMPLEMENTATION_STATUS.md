# Implementation status

Started 2026-10-17 from `91e602c` on `codex/distributed-foundation`.
Scope of this session: a coherent, mock-validated phase 1–2 foundation, followed
by repairs to the specific baseline weather and frontend defects. This is not
completion of the eight-phase redesign.

| Phase | Status | Next acceptance boundary |
|---|---|---|
| 1 Audit/foundation | In progress | schemas/configuration/CI and clean checks |
| 2 Edge/server | In progress | authenticated audio and command round trips with mocks |
| 3 Providers/registry | Pending | three mocked adapters execute identical validated tools |
| 4 Core tools | Pending | SQLite timer restart, real cached weather, HA allowlists |
| 5 Distributed voice | Pending | wake → STT → tools → synthesis → Pi playback |
| 6 Dashboard | Pending | real semantic widgets, snapshot restore and portrait checks |
| 7 Presence | Pending | offline local dim/wake simulation and hardware driver |
| 8 Hardening | Pending | live deployment, recovery, security and performance validation |

## Baseline and plan

See [BASELINE.md](BASELINE.md) and [ARCHITECTURE.md](ARCHITECTURE.md). Existing
legacy entry points and firmware will remain available. Generated dependencies
will be removed from the index only, preserving the local installation.

## Validation record

Before changes: 16 legacy Python files parse; frontend typecheck fails; Vite build
blocked by config-bundling ancestor access. No hardware acceptance has been run.

This file will be updated with changed files, exact checks and outstanding work
before the milestone is committed.
