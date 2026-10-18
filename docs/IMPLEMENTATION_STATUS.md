# Implementation status - 2026-10-18

Branch: `codex/distributed-foundation`; Phase 5 started from clean
`1a50bc3fc3499ad196e5f4422763935c4cc366a5` (Phase 4).
Distributed voice now extends the existing authenticated edge socket, common
three-provider agent/tools and persistent timers. Voice is optional and requires
trusted local assets, role-specific dependencies and explicit grants. Physical
Pi audio and real-model inference acceptance remain pending. No live hardware,
infrastructure, firmware or deployed service was changed.

## Phase results

| Phase | Implemented | Remaining / acceptance limits |
|---|---|---|
| 1 Audit/foundation | Audit, architecture, branch, protocol/JSON Schema, redacted settings, pinned dependencies, CI, asset verifier, generated-file cleanup | Hosted CI matrix unrun; verified model discovery not wired into old listener |
| 2 Edge/server | FastAPI gateway, scoped auth, outbound edge socket, heartbeats/reconnect, snapshots, correlated commands, exact Feather ACKs, durable replay journal, cancellable PCM upload | Mock/real-loopback validation passed; physical Pi/Feather acceptance pending |
| 3 Providers/registry | Native Ollama, official OpenAI Responses and Anthropic Messages adapters; bounded structured tool loop; typed registry/permissions; real MCP stdio/HTTP; temporary isolated sessions; authenticated text API/CLI | Non-streaming; live model/API quality and deployed endpoints unverified; sensitive confirmation flow and generic durable MCP action journal deferred |
| 4 Core tools | SQLite timers/alarms and durable native receipts; Open-Meteo service; restricted native HA/media; optional SearXNG; semantic views, scoped snapshots and durable event polling | Live endpoint/device acceptance and generic MCP durable transactions; Phase 5 adds alarm output/cache |
| 5 Voice | Native-rate Pi capture/resampling, local Hey Eve/Silero; CPU INT8 faster-whisper; Piper; bounded acknowledged Pi output; half duplex/mute/stop/follow-up; durable independent offline alarms; scoped volatile voice state | Trusted deployment models and real inference/audio quality; physical Pi acceptance; Linux optional-role install; no AEC/barge-in or GPU claims |
| 6 Dashboard | Extracted weather normalization, actual weekly/daily values, null/stale handling, cache invalidation, repaired TypeScript/build, pure tests | Componentization, browser auth/transport, state machine, reconnect/snapshots, real timer/home/media widgets, portrait/performance checks |
| 7 Presence | Local hardware module survives network loss in simulation | Sensor interface/driver, debounce, absence/override/protected-activity policy, offline automatic dim/wake |
| 8 Hardening | Compose/Dockerfile/systemd examples, health, security/privacy/recovery/backup/hardware docs | Linux/container deployment, actual recovery/security review, browser sessions, metrics and hardware benchmarks |

The text agent is functional through the common orchestration path. Defaults select
Ollama, but a model must be explicitly configured; otherwise text turns report 503
while the existing gateway still runs. Cloud requires explicit opt-in and there
is no provider fallback. HA/search and speech default to unconfigured/disabled.
Negotiated voice routes PCM to local STT and the same agent; old transport-only
peers keep their discard/injected consumer. React still uses the legacy relay.

## Phase 5 delivery and actual validation

See [PHASE5_VOICE.md](PHASE5_VOICE.md) for setup, complete model manifests, voice
identity/permissions, audio framing, state/caption contracts, offline policy,
recovery, manual acceptance and legacy inventory.

- `apps/edge/voice/`: lazy ONNX openWakeWord/Silero, continuous native-rate capture,
  real stateful SoXR conversion, bounded VAD recording; one prioritized speaker
  manager, software receipts, half duplex, mute, explicit stop and follow-up.
- `apps/server/speech/`: reusable local CPU INT8 faster-whisper and Piper workers,
  cancellation/busy ownership, bounded output delivery, scoped common-agent turns,
  safe tool-failure wording, metrics and volatile caption snapshots.
- Backend migration 2 and a separate device-bound edge voice journal implement
  independent local alarm tones, complete timer-cache sync/storage ACKs, offline
  lease, durable attempt deduplication, receipt reconciliation and explicit dismissal.
  Sound output never implicitly acknowledges the authoritative pending timer.
- Shared asset verification and PCM/metadata helpers; additive negotiated v1 voice
  messages; separate generated voice HTTP schema. Original application v1 is
  unchanged. Optional role locks, deployment examples and real-engine smoke CLI
  are included; package version is 0.5.0. Firmware/hardware logic and legacy runtime
  modules are preserved. The dashboard relay remains necessary until Phase 6.

Fresh ignored `.venv-phase5-verify`, Windows Python 3.12.10: installed the pinned
`dev.lock`, `voice-edge.lock` and `voice-server.lock`, then editable package 0.5.0.

| Check | Actual result |
|---|---|
| Full Python suite | **271 passed**, including all 218 Phase 4 tests and 53 new voice cases |
| Complete voice path, three provider adapters | Passed over real authenticated loopback HTTP/WS with fixture mic/wake/VAD/STT/TTS/speaker and mocked Ollama/OpenAI/Anthropic HTTP: HA off + tomorrow weather, follow-up daily view, 35% brightness and timer |
| Recovery, privacy and independent output | Passed: missing speech/grant, blank speech, tool/provider/STT/TTS/output failure, cancellation/disconnect/reconnect, no overlap, follow-up expiry, delegated caption isolation/TTL, two-device grants, slow hardware responsiveness, mute/stop preserving alarms |
| Durable alarm delivery | Passed with fake clocks and fixture output: offline timers, pause/cancel, priority, failed status sends, lost receipts, edge/backend reboot, deduplication, unknown attempts and explicit dismissal |
| DSP and adapter binding | Real NumPy/SoXR rate/duration/anti-alias checks; fixture ONNX/PortAudio/model bindings validate local-only CPU INT8, assets, metadata, model reuse and timeout worker ownership |
| Ruff check / format; pinned install / pip check | Passed; 102 Python files; no broken requirements |
| Schemas | Device/audio/voice and separate voice HTTP generated consistently; original application v1 unchanged |
| Original loopback transport simulation | Passed: simulated 35% ACK and 16000 in-memory PCM bytes |
| Frontend tests / typecheck / production build | **4 passed** / passed / passed; existing 1.026 MB JS / 284 KB gzip bundle warning |
| Examples / CLI / links / ignores | YAML, active env samples, optional grants, diagnostic help, local documentation links and private/runtime ignore rules checked without live connections |

No model inference, physical microphone/speaker, Pi, HA/weather/search/cloud endpoint,
Linux/Python 3.11, container/systemd deployment, hosted CI or GPU benchmark ran.
Real local speech implementations are present; trusted deployment assets and manual
acceptance are required. Simulation engine timings are fixture timings and provide
no real STT/TTS/acoustic or Pi performance measurement. The core-only environment
can still emit the known upstream Starlette/httpx TestClient deprecation.

Software started/completed reports describe driver calls/drain, not measured sound.
Native cancellation is cooperative and holds the worker slot until it exits. Input
is half duplex without AEC/voice barge-in. Offline alarms use the last synchronized
snapshot for at most 24 hours by default and may miss a remote cancel during outage.
Durable at-most-once attempts can leave an unheard indeterminate alarm after a crash;
backend pending state persists until explicit dismissal. See the guide's recovery
and acceptance policy. Browser credentials/transport and generic durable MCP writes
remain later work.

## Phase 4 delivery and actual validation (historical)

See [PHASE4_SERVICES.md](PHASE4_SERVICES.md) for configuration, every tool,
SQLite schema/migrations/backup, recovery, permissions and event contracts.

- `apps/server/services/`: lifecycle-owned SQLite connection and transactions,
  persistent timer state machine/reconciliation and unique pending alarms; durable
  native operation/turn identities; Open-Meteo/geocoding with TTLs, coalescing,
  DST, null and bounded stale handling; native restricted HA/media and optional
  read-only SearXNG clients; scoped presentation state and durable event revisions.
- `apps/server/tools/services.py`, executor/registry/orchestrator: all new tools
  use the existing three-provider path, typed arguments, principal/device grants,
  bounded execution and explicit mutation policy. Distinct timer call identities
  allow intentional identical timers; retries return receipts without replay.
  Unknown external writes stay indeterminate across restart.
- `/api/application/state` and `/events`: typed version-1 private snapshots,
  selected views/layouts, protected alarm presentation and cursor recovery. These
  use trusted backend-client credentials, not browser authentication. React keeps
  its old relay. `packages/application/schema.json` is a separate generated schema;
  existing device/audio v1 is unchanged.
- `packages/weather/` shares pure nullable-column/condition normalization with
  legacy weather; its callers, voice stack, firmware and hardware path are retained.
  Compose now prepares a writable persistent volume; backup/export scripts, env
  examples, documentation, package version 0.4.0 and CI schema checks are updated.

Fresh ignored `.venv-phase4`, Python 3.12.10 on Windows, installed from updated
`requirements/dev.lock`, then `pip install --no-deps -e .`:

| Check | Actual result |
|---|---|
| Full Python suite | **218 passed**, including the 145-test Phase 3 baseline; one existing Starlette/httpx deprecation warning |
| All three provider SDK/native adapters through new tools | Passed with mocked HTTP: two identical timers, weather, HA light, media pause, search and semantic view in the common agent loop |
| Persistence/recovery/failures | Passed: deadlines, races, repeated cancellation/transaction ownership, offline expiry/restart, unique alarms, ownership/device isolation, corrupt/missing/future schema, migration failure, WAL backup/restore, receipt replay and event cursors |
| Weather/HA/media/search security | Passed using isolated fixtures; includes DST, units, coalescing/stale/nulls, capabilities, unknown outcomes, unsafe URL rejection, untrusted snippets and reflected-credential redaction |
| Ruff check / format; clean lock install / pip check | Passed; 79 Python files formatted consistently, package 0.4.0 |
| Device/audio and application JSON Schemas | Regenerated without drift |
| Existing real loopback simulation | Passed: simulated 35% ACK and 16,000 in-memory PCM bytes |
| Frontend tests / typecheck / production build | **4 passed** / passed / passed; existing 1.026 MB JS / 284 KB gzip bundle warning |
| Configuration / documentation / ignore rules | Active and optional env examples validated without connections; 35 local links resolved; database/WAL/SHM/backups and verification environments ignored |

No live model, cloud, weather/search, Home Assistant or physical device endpoint
was tested. Production adapters make actual configured requests; fixtures are
injected only by tests. HA/search are unavailable until configured, weather is
requested on demand, and mutations remain disabled by default. No Pi audio,
audible alarm, offline edge fallback, Linux/Python 3.11, Docker/systemd, hosted CI,
GPU or physical performance acceptance is claimed.

Conversation context/response text remain memory-only. Durable replay markers
retain identities/hashes, not full conversations; timer names and scoped state
are private persistent data. Native receipt tables fail closed at bounded capacity
and need reviewed maintenance. Restoring an older backup can lose newer identities.
Browser sessions/streaming, generic durable MCP transactions and sensitive action
confirmation remain deferred. Keep `legacy/` until its consumers migrate.

## Phase 3 delivery and actual validation (historical)

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

At the Phase 3 milestone, context, request receipts and sessions were memory-only and expired;
MCP mutations have no generic durable transaction journal. Never blindly retry an
uncertain turn after restart/expiry. Whole old turns are discarded under bounds,
without LLM summaries. Optional model-specific reasoning/temperature settings need
live compatibility checks. Phase 4 subsequently implemented timer/weather/HA backend services and durable
turn/native-action records; streaming, speech processing and dashboard migration remain later work. `legacy/` is retained.

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

## Exact next steps: Phase 6

1. Implement browser sessions with explicit device/voice scopes and CSRF/Origin
   policy; keep operator, provider and edge credentials out of React.
2. Generate TypeScript contracts for application and voice snapshots. Replace the
   legacy relay with authenticated snapshot/event transport, durable revision and
   volatile caption-cursor recovery; test expiry, reconnect and offline states.
3. Split semantic timer/alarm, weather, home/media and voice widgets. Use real
   software playback timing for captions, null/stale/unknown states and explicit
   alarm acknowledgment. Do not equate delivery with physical action/sound.
4. Add state-machine/component and auth/recovery tests, portrait/accessibility
   checks, then measure bundle/render/CPU/RSS/FPS on the actual Pi. Optimize from
   measurements while preserving visual and hardware behavior.
5. Run the Phase 5 real-model and Pi manual checklist in a separately authorized
   window. Retire legacy relay/voice consumers only after replacements and physical
   acceptance pass; preserve utilities and firmware rollback.
