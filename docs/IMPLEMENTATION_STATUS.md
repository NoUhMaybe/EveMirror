# Implementation status — 2026-10-17

Branch: `codex/distributed-foundation`; clean starting baseline: `91e602c`.
Phase 3 is implemented on top of the reviewed `d35b5e9` Phase 1-2 baseline: a
provider-independent text agent with structured tools, MCP and temporary sessions.
This does not complete the full voice/dashboard/Phase 4 redesign.
No live hardware, infrastructure, firmware or service credentials were changed.

## Phase results

| Phase | Implemented | Remaining / acceptance limits |
|---|---|---|
| 1 Audit/foundation | Audit, architecture, branch, protocol/JSON Schema, redacted settings, pinned dependencies, CI, asset verifier, generated-file cleanup | Hosted CI matrix unrun; verified model discovery not wired into old listener |
| 2 Edge/server | FastAPI gateway, scoped auth, outbound edge socket, heartbeats/reconnect, snapshots, correlated commands, exact Feather ACKs, durable replay journal, cancellable PCM upload | Mock/real-loopback validation passed; physical Pi/Feather acceptance pending |
| 3 Providers/registry | Native Ollama, official OpenAI Responses and Anthropic Messages adapters; bounded structured tool loop; typed registry/permissions; real MCP stdio/HTTP; temporary isolated sessions; authenticated text API/CLI | Non-streaming; live model/API quality and deployed endpoints unverified; sensitive confirmation flow and generic durable MCP action journal deferred |
| 4 Core tools | Legacy weather repairs only | Configured backend weather; persistent timers/alarms; HA/media/search and hardware/UI tool namespaces |
| 5 Voice | Audio transport and injected consumer interface only | Wake/VAD capture integration, STT, synthesis, Pi playback/cancellation, mute/echo suppression and follow-up |
| 6 Dashboard | Extracted weather normalization, actual weekly/daily values, null/stale handling, cache invalidation, repaired TypeScript/build, pure tests | Componentization, browser auth/transport, state machine, reconnect/snapshots, real timer/home/media widgets, portrait/performance checks |
| 7 Presence | Local hardware module survives network loss in simulation | Sensor interface/driver, debounce, absence/override/protected-activity policy, offline automatic dim/wake |
| 8 Hardening | Compose/Dockerfile/systemd examples, health, security/privacy/recovery/backup/hardware docs | Linux/container deployment, actual recovery/security review, browser sessions, metrics and hardware benchmarks |

The text agent is functional through the common orchestration path. Defaults select
Ollama, but a model must be explicitly configured; otherwise text turns report 503
while the existing gateway still runs. Cloud requires explicit opt-in and there
is no provider fallback. STT/TTS/HA remain unconfigured, the default audio consumer
discards PCM after receipt, and the browser still uses the legacy relay.

## Phase 3 delivery and actual validation

See [PHASE3_AGENT.md](PHASE3_AGENT.md) for the provider matrix, configuration/API,
permissions, MCP lifecycle, retention, retry behavior and exact limitations.

- `apps/server/providers/`: native Ollama chat and official OpenAI/Anthropic SDKs;
  canonical tool aliases, multiple calls/results, usage, redacted failures,
  timeouts/cancellation, private reasoning/context preservation. OpenAI uses
  `store=false`; streaming is a reserved internal event contract only.
- `apps/server/tools/`: strict native arguments and bounded JSON Schema registry,
  backend permissions, confirmations/sensitive actions blocked, ordered executor,
  duplicate receipt handling, time/result/argument bounds. Real UTC and correlated
  mirror status; brightness is opt-in and uses the unchanged gateway/edge journal.
- `apps/server/tools/mcp_client.py`: official SDK initialization, bounded paginated
  discovery, exact allowlists, trusted administrator descriptions/policy, stdio and
  authenticated Streamable HTTP, structured/text results, timeout/disconnect,
  reconnect before a future turn and clean lifecycle ownership. No resources,
  prompts, sampling, roots, arbitrary shell/network/filesystem tools or HA service
  integration. Remote servers and stdio executables require administrator review.
- `apps/server/agent/`: central prompt, non-streaming bounded execution loop,
  principal/device-bound in-memory sessions, multi-turn context, reset/expiry,
  concurrency rejection, cancellation and bounded retry receipts/tombstones.
  `apps/server/auth.py` reuses shared credential comparison; optional scoped
  terminal/service clients cannot access operator endpoints. No browser auth added.
- Existing FastAPI app hosts the authenticated agent routes, bounds request bodies
  before parsing and redacts validation errors. `scripts/chat.py` calls that API
  with repeated turns/reset/status and cancellation. Config, pinned server locks,
  examples, docs and CI were updated. Edge/common locks, firmware, dashboard and
  legacy implementation code remain unchanged.

Fresh ignored `.venv-phase3`, Python 3.12.10 on Windows, installed from the updated
`requirements/dev.lock`, then `pip install --no-deps -e .` (package 0.3.0):

| Check | Actual result |
|---|---|
| Full Python suite | **145 passed**, including all prior 64; one existing Starlette/httpx deprecation warning |
| Ruff check / format | Passed across apps/packages/scripts/tests |
| Clean lock installation and `pip check` | Passed |
| Existing real loopback transport simulation | Passed: simulated 35% ACK and 16,000 PCM bytes |
| All three adapters through text API/native tools | Passed with actual SDK/API serialization and mocked HTTP, no live keys |
| All three adapters through simulated gateway/edge brightness/status | Passed; duplicate action/API retries cause one hardware mutation; status after mutation is fresh |
| All three adapters through real isolated MCP subprocess | Passed: discovery, schema validation, execution, result to model, final response |
| Authenticated loopback MCP HTTP; disconnect/reconnect/cleanup | Passed |
| Interactive CLI subprocess against loopback backend | Passed: repeated context, reset, response and credential non-disclosure |
| Existing device protocol JSON Schema | Regenerated without drift |
| Frontend tests / typecheck / build | **4 passed** / passed / passed; unchanged 1.026 MB JS / 284 KB gzip bundle warning |

Hosted CI has not been run here; its matrix still targets Windows/Linux Python
3.11/3.12 and now also runs `pip check` and the transport simulation. Linux,
Python 3.11, Docker/systemd, live Ollama/cloud API requests, Home Assistant and
physical hardware remain unverified. No production services were contacted.
The Windows `py -3.12` launcher did not resolve an installed runtime; invoking
the existing Python 3.12 environment directly successfully created the clean
verification environment. All listed acceptance checks then passed locally.

Known limits: context, request receipts and sessions are memory-only and expire;
MCP mutations have no generic durable transaction journal. Never blindly retry an
uncertain turn after restart/expiry. Whole old turns are discarded under bounds,
without LLM summaries. Optional model-specific reasoning/temperature settings need
live compatibility checks. Streaming, speech processing, timers/weather/HA backend
services and dashboard migration remain later work. `legacy/` is retained.

## Repository cleanup follow-up

Source now follows [REPOSITORY_LAYOUT.md](REPOSITORY_LAYOUT.md). The dashboard is
under `apps/dashboard`, firmware under `firmware/feather_m4`, old voice components
under `legacy/`, and training tools/assets under `training/wake_word`. CI, runtime
paths, package discovery and documentation were updated. Historical docs moved to
`docs/archive/`. The unused MCP scaffold, `.gitkeep` markers and generated training
config were deleted; Drei was removed from the frontend dependencies. Existing local
models, datasets, private env files, recordings and root virtual environments were
preserved. Firmware and standalone serial-client bytes remain unchanged.

Cleanup validation passed: 64 Python tests, four frontend tests, lint/format,
clean frontend reinstall/typecheck/build and the loopback simulation. Legacy CLI
help/import checks, 16 relocated Python parses, package discovery and current
documentation links passed. Ignore checks confirmed 22 generated/private paths
are excluded and nine source/lock/template paths remain trackable. Firmware and
standalone serial-client SHA-256 values match their pre-move values. Training,
microphone capture and physical hardware control were not launched.

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
- `legacy/agent/tooling.py`, `dashboard_event_server.py`: retained weather API with
  separate daily/weekly TTLs, no unconditional unrelated-chat fetch, no invented
  hours, null measurements, bounded stale fallback and acquisition/source metadata.
- `apps/dashboard/src/state/weather.ts`, `App.tsx`, `styles.css`, package/TypeScript
  config and `apps/dashboard/tests/`: actual forecasts/highs/lows, missing-data handling,
  labeled cached/demo values, source-local hours and repaired typecheck/build.
- `firmware/feather_m4/README.md`: corrects the direction-of-calibration explanation.
  Firmware, voltage scaling, pins, ENA and fades are unchanged.
- Generated dependencies/builds/configs/bytecode and local env/weather cache were
  removed **from the index only**, retained locally and ignored. No history rewrite.

## Prior Phase 1-2 validation (historical)

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
| Feather firmware and standalone serial-client bytes | Unchanged; legacy runtime path references updated |

Tests cover strict protocol/config, token isolation/redaction, auth failures,
command/ACK correlation/timeouts, exact/partial/malformed serial writes and ACKs,
cancellation serialization, durable replay/conflicts/interruption/schema recovery,
audio order/size/count/expiry/cancellation, consumer failure redaction/recovery,
edge reconnect and local hardware calls during disconnection, asset hashes,
weather cache/stale/missing-data behavior and frontend normalization.

No numerical coverage percentage is claimed. One upstream Starlette TestClient
deprecation references httpx 0.28.1. Vite reports the existing large bundle:
roughly 1.026 MB JavaScript / 284 KB gzip. The unused Drei dependency and its mesh-BVH deprecation were removed during
cleanup; the frontend lock now resolves 48 packages instead of 102. Measure
rendering in phase 6. No visual/FPS test ran.

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

## Exact next steps: Phase 4

1. Implement authoritative SQLite timer storage/migrations and deterministic
   restart/expiry/pause/resume/cancel/acknowledgment tests; register real timer tools
   through the existing executor. Plan durable edge fallback/reconciliation without
   claiming offline alarms until tested.
2. Extract the repaired legacy Open-Meteo service into the backend with explicit
   location, acquisition/source timestamps, daily/weekly TTLs, bounded stale/null
   behavior and regression tests. Register real weather tools; retain legacy until
   dashboard/voice replacements consume the migrated service.
3. Configure least-privilege HA credentials and explicit approved entities/services.
   Use this MCP client or a native service behind the registry; sensitive actions
   stay unavailable until a trusted confirmation mechanism exists. No broad HA
   service/shell/network exposure.
4. Add timer/weather snapshots and approved media/search/UI interfaces, with
   integration tests for actual success/failure and permission checks. Preserve
   gateway command correlation, deadlines and edge replay behavior.
5. Verify the chosen live model's tool and reasoning support in a separately
   authorized environment. Keep browser auth/dashboard and distributed STT/Piper/
   playback for their later phases; do not delete `legacy/` in Phase 4 prematurely.
