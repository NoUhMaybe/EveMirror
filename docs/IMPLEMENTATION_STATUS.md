# Implementation status — 2026-10-17

Branch: `codex/distributed-foundation`; clean starting baseline: `91e602c`.
This session delivers a working **phase 1–2 development foundation** and focused
legacy weather/frontend repairs. It does not complete the full assistant redesign.
No live hardware, infrastructure, firmware or service credentials were changed.

## Phase results

| Phase | Implemented | Remaining / acceptance limits |
|---|---|---|
| 1 Audit/foundation | Audit, architecture, branch, protocol/JSON Schema, redacted settings, pinned dependencies, CI, asset verifier, generated-file cleanup | Hosted CI matrix unrun; verified model discovery not wired into old listener |
| 2 Edge/server | FastAPI gateway, scoped auth, outbound edge socket, heartbeats/reconnect, snapshots, correlated commands, exact Feather ACKs, durable replay journal, cancellable PCM upload | Mock/real-loopback validation passed; physical Pi/Feather acceptance pending |
| 3 Providers/registry | Pending in new server | Ollama/OpenAI/Anthropic adapters, structured tool loop, permissions, MCP, temporary sessions |
| 4 Core tools | Legacy weather repairs only | Configured backend weather; persistent timers/alarms; HA/media/search and hardware/UI tool namespaces |
| 5 Voice | Audio transport and injected consumer interface only | Wake/VAD capture integration, STT, synthesis, Pi playback/cancellation, mute/echo suppression and follow-up |
| 6 Dashboard | Extracted weather normalization, actual weekly/daily values, null/stale handling, cache invalidation, repaired TypeScript/build, pure tests | Componentization, browser auth/transport, state machine, reconnect/snapshots, real timer/home/media widgets, portrait/performance checks |
| 7 Presence | Local hardware module survives network loss in simulation | Sensor interface/driver, debounce, absence/override/protected-activity policy, offline automatic dim/wake |
| 8 Hardening | Compose/Dockerfile/systemd examples, health, security/privacy/recovery/backup/hardware docs | Linux/container deployment, actual recovery/security review, browser sessions, metrics and hardware benchmarks |

The new server explicitly reports provider, STT, TTS and HA as unconfigured.
Its default audio consumer discards PCM after receipt; upload success is not a
voice interaction. The browser still uses the legacy loopback event server and
does not consume the new gateway's snapshot.

## Changed files and ownership

- `apps/config.py`: backend/edge settings, distinct credentials, TLS-origin
  validation, bounds and redaction. `packages/protocol/`: strict versioned commands,
  ACK/state/audio schemas, generated JSON Schema and drift test.
- `apps/edge/`: sole serial owner, exact protocol parsing, lazy reopen, serialized
  cancellation-safe operations, SQLite journal v1 with interrupted-command and
  old-ID tombstones, outbound runtime. ACKs represent targets, never measurements.
- `apps/server/`: auth, correlation/deadlines, duplicate connection rejection,
  bounded audio assembler/consumers, health and snapshots.
- `scripts/`: schema export, trusted-manifest SHA-256 verifier and standalone
  loopback simulation. `requirements/*.lock`, `pyproject.toml` and CI define the
  isolated foundation environment. `deploy/` contains examples with invalid token
  placeholders; `README.md` and `docs/` describe setup and actual capabilities.
- `eve_agent/tooling.py`, `dashboard_event_server.py`: retained weather API with
  separate daily/weekly TTLs, no unconditional unrelated-chat fetch, no invented
  hours, null measurements, bounded stale fallback and acquisition/source metadata.
- `dashboard/src/state/weather.ts`, `App.tsx`, `styles.css`, package/TypeScript
  config and `dashboard/tests/`: actual forecasts/highs/lows, missing-data handling,
  labeled cached/demo values, source-local hours and repaired typecheck/build.
- `backlight Control/README.md`: corrects the direction-of-calibration explanation.
  Firmware, voltage scaling, pins, ENA and fades are unchanged.
- Generated dependencies/builds/configs/bytecode and local env/weather cache were
  removed **from the index only**, retained locally and ignored. No history rewrite.

## Validation actually executed

Windows; Python 3.12.10; Node 24.11.1. The old `.venv` was retained; new
`.venv-dev` / `.venv-verify` environments are ignored.

| Check | Result |
|---|---|
| Fresh `requirements/dev.lock` installation, then `pip install --no-deps -e .` | Passed in `.venv-verify` |
| `python -m pip check` | Passed |
| `python -m pytest -q` | **64 passed** |
| Ruff check and format check for apps/packages/scripts/tests | Passed |
| `python scripts/simulate.py` | Passed: simulated 35% ACK and 16,000 PCM bytes over real loopback HTTP/WS |
| `npm.cmd ci --offline --ignore-scripts` | Clean reinstall passed |
| `npm.cmd test` | **4 passed** |
| `npm.cmd run typecheck` | Passed; failed at baseline |
| `npm.cmd run build` | Passed with source Vite config/runner loader |
| Compose and CI YAML parsing | Passed; no services started |
| `git diff --check` | Passed |
| Original Feather firmware/client and wake/supervisor source comparison | Unchanged |

Tests cover strict protocol/config, token isolation/redaction, auth failures,
command/ACK correlation/timeouts, exact/partial/malformed serial writes and ACKs,
cancellation serialization, durable replay/conflicts/interruption/schema recovery,
audio order/size/count/expiry/cancellation, consumer failure redaction/recovery,
edge reconnect and local hardware calls during disconnection, asset hashes,
weather cache/stale/missing-data behavior and frontend normalization.

No numerical coverage percentage is claimed. One upstream Starlette TestClient
deprecation references httpx 0.28.1. Vite reports the existing large bundle:
roughly 1.026 MB JavaScript / 284 KB gzip. Clean npm reinstall reports the existing
Drei mesh-BVH dependency deprecation; Drei appears unused in application imports.
Resolve the dependency and measure rendering in phase 6. No visual/FPS test ran.

Docker CLI/systemd are unavailable here. Linux/Pi installation, Python 3.11 and
hosted Actions remain unverified. CI targets Windows/Linux Python 3.11/3.12 and
a Node 24 dashboard build.

## Untested hardware assumptions

The prior source/handoff reports a working Feather with nominal 0–2 V A0 DAC,
active-high D12 ENA, 1.5-second fade and USB CDC data interface. These were not
remeasured. ACK means fade initiation; actual brightness/completion stay unknown.
Verify serial interface, Pi RAM/OS, HDMI state, microphone/speaker IDs, mmWave
hardware and service/network addresses during deployment. No Intel Arc acceleration,
live inference/weather/HA or physical device test ran. Follow
[SECURITY_AND_HARDWARE.md](SECURITY_AND_HARDWARE.md) for manual acceptance.

## Next actionable steps — do not repeat the audit

1. Read `BASELINE.md`, `ARCHITECTURE.md`, `PROTOCOL.md` and the checks in `README.md`.
   Reuse the opt-in new apps; keep legacy voice and firmware available.
2. Implement phase 3 under `apps/server/providers/`, `agent/`, `tools/`: typed
   normalized messages/tool calls/results and separate Ollama/OpenAI/Anthropic
   adapters using current official SDK/API docs. Handle native roles/result grouping,
   multiple calls, reasoning settings, usage, timeouts, rate limits, streaming and
   cancellation. Use mocked APIs; no live credentials are needed for this step.
3. Add the permission-aware registry, call-depth/count bounds, execution deadlines,
   durable action deduplication and provider-safe aliases for canonical namespaces.
   Treat tool/MCP results as external data. Test identical tools through all adapters.
4. Add bounded ephemeral context/reset/cancellation, explicit provider/model settings
   and local-only privacy. Never silently fall back to cloud. Wire a text-turn API
   before attaching STT to the audio consumer.
5. Implement authoritative SQLite timers with migrations, expiry/pause/resume/cancel/
   acknowledgment and restart tests; then timer snapshots and a durable edge alarm
   fallback/reconciliation. Do not claim offline alarms before these pass.
6. Extract repaired Open-Meteo logic into a configured backend service; implement
   approved-entity HA/MCP/media and configured search. Replace broad keyword routing;
   do not expose arbitrary HA services, network, filesystem, serial or shell tools.
7. Implement server CPU INT8 STT and synthesis-only Piper, verified wake/VAD assets
   and Pi capture/playback. Use actual playback ACKs for state. Benchmark Intel GPU
   alternatives only when hardware is available.
8. Migrate browser auth/shared schemas/snapshot/reconnect/semantic state, split orb
   and widgets and optimize portrait rendering. Add local presence policy independently
   of backend/LLM availability.
9. Validate Compose/systemd on Linux and hardware procedures only after deployment
   authorization. Keep simulated results separate from actual acceptance.
