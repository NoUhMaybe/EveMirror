# Implementation status - 2026-10-18

Branch: `codex/distributed-foundation`; Phase 6 started clean at `8299989`, retaining
the Phase 5 CI synchronization repair. Browser pairing, typed polling/projections,
modular semantic widgets and portrait dashboard are implemented. Deployment, actual
Pi performance and live integration acceptance remain separate. Phase 5 started from clean
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
| 6 Dashboard | Scoped persistent browser cookies/pairing, CSRF/Origin, generated contracts, bounded polling/cursor recovery, modular React, playback subtitles/orb, backend weather/timers/alarms/home/media, portrait browser tests, shader/static quality presets, deployment examples | Physical native-resolution/standing-distance acceptance, Pi CPU/RSS/GPU/FPS/soak, live model/audio/HA, Linux/container/hosted CI run |
| 7 Presence | Typed local sensor interface/simulation, deterministic debounce/absence/unknown policy, centralized journaled brightness, saved preference/manual/night, offline wake/alarms, browser diagnostics/settings and deployment/preflight/acceptance utilities | Real sensor model/protocol/installation, Pi/model/audio/physical acceptance, production deployment and eight-hour soak |
| 8 Hardening | Compose/Dockerfile/systemd examples, health, security/privacy/recovery/backup/hardware docs | Linux/container deployment, actual recovery/security review, metrics and hardware benchmarks |

The text agent is functional through the common orchestration path. Defaults select
Ollama, but a model must be explicitly configured; otherwise text turns report 503
while the existing gateway still runs. Cloud requires explicit opt-in and there
is no provider fallback. HA/search and speech default to unconfigured/disabled.
Negotiated voice routes PCM to local STT and the same agent; old transport-only
peers keep their discard/injected consumer. React now uses the paired browser API;
the relay remains only in the coherent old-stack rollback set.

## Phase 7 software preparation

Started from `3538e829f64f0758bb8f4d871c8a315082b812d5` after its
[complete five-job CI matrix passed](https://github.com/NoUhMaybe/EveMirror/actions/runs/39157234157).
Before editing, both Windows Python 3.11.9 and 3.12.10 passed all 316 Python tests;
26 frontend tests, typecheck, build and nine Chromium scenarios passed.

See [PHASE7_PRESENCE.md](PHASE7_PRESENCE.md) for delivered behavior and exact sensor
limits; [deployment](PHASE7_DEPLOYMENT_PLAN.md) and
[acceptance](PHASE7_HARDWARE_ACCEPTANCE.md) distinguish software, isolated Linux
validation and pending real-device work. Existing cancellation/session regressions,
half duplex, alarm/audio attempt receipts and command replay semantics remain.
The complete regression suite includes an existing slow-serial test that caught
blocking activity notifications during development; notifications now record
protection immediately and a separate worker performs hardware writes.

New tests cover fake-clock policy transitions/failures, no replay after uncertain
ACK/cancellation/restart, settings/auth/CSRF, real loopback semantic events,
offline local wake and undismissed alarm protection after audio and sensor loss,
read-only preflight/counters, generated browser contracts and three new Chromium
presence/settings scenarios. No prior test was suppressed or weakened.

| Local check | Actual result |
| --- | --- |
| Complete Python suite, Windows 3.11.9 and 3.12.10 | **361 passed each**, including all 316 baseline cases and 45 new cases; existing upstream warning on 3.11 |
| Frontend tests / Chromium | **27 passed / 12 passed**, retaining all 26 / 9 baseline cases |
| Ruff lint/format, frontend format/typecheck/build, pip check and npm audit | Passed; 124 Python files; zero npm audit vulnerabilities |
| Four protocol/application schemas and browser TS/validator drift | Passed |
| Transport / voice / presence simulations | Passed using loopback and fake hardware/audio/models |
| Documentation / private artifacts | 60 local links resolve; wheel downloads/test artifacts ignored; firmware and legacy unchanged |

Cross-platform downloads verified 34 pinned ARM64 Python 3.11 wheels only after
including glibc 2.34 tags (TFLite runtime requires that baseline). No ARM code was
executed. Local preflight correctly reports this Windows host unsuitable for Pi
deployment. Docker/installed WSL are unavailable locally; new hosted CI jobs build
and exercise an isolated Linux container, install/import Linux voice libraries and
check ARM64 wheel availability. Final run results accompany the milestone commit.

No physical sensor protocol is claimed. Firmware and legacy rollback remain intact.
No physical/deployed endpoint, service, boot/display setting, wiring or production
database was modified. Actual model quality, Pi resource/FPS/thermal measurements,
sensor accuracy, HDMI/ENA/DAC behavior and the eight-hour soak remain unverified.

Linux CI exposed a real pre-existing offline ordering defect: each failed reconnect
called voice disconnect cleanup, even without an established socket. A local wake
chime could therefore be canceled by an unrelated retry. An event-controlled test
holds the chime while a failed connection completes, reproducing IDLE before the
fix. Cleanup now occurs only when an established socket is lost; repeated failed
attempts preserve local capture. Actual disconnect still cancels ordinary turns
and preserves alarms. Focused cancellation/presence/recovery tests passed on both
local Python versions before full 359-test validation.

A deliberately blocked presence-event write also reproduced an ACK timeout in
the original socket handler. Presence updates now change the gateway projection
immediately and enqueue bounded, coalesced notifications for one lifecycle-owned
worker in the existing services layer. No new ledger or database is added. The
regression holds event persistence blocked while a status ACK succeeds and floods
1,000 reports into the bounded queue. Existing command deadlines/assertions remain.
Policy preferences and uncertainty also share the original command reservation/
receipt transactions, avoiding extra disk commits on the ACK path. SQLite tracing
verifies exactly two commits and crash tests retain the uncertain-write latch.

Isolated Linux container acceptance passed in
[run 39163009792](https://github.com/NoUhMaybe/EveMirror/actions/runs/39163009792):
image/static hosting, TLS/WS, secure pairing/CSRF, nonroot/read-only root/model mount,
SQLite backup/restore integrity, graceful stop and persistent sessions after restart.
Linux Python 3.11 speech installation/imports and ARM64 wheel checks also passed.
This is a core backend image with speech disabled and fixture model files; actual
speech-model execution and ARM64 runtime/physical acceptance are still pending.

## Phase 6 cancellation ordering repair

The [Phase 6 Actions run](https://github.com/NoUhMaybe/EveMirror/actions/runs/39154983951)
for `ad900152d20191e14271ef9aead7ba55cd6bb97d` failed on Ubuntu/Python 3.11:
298 tests passed, while programmatic cancellation left the controller TRANSCRIBING
instead of IDLE. The other three foundation jobs and the dashboard job passed.
This is a production state-management defect, distinct from the earlier fixture
synchronization repair. The Starlette/httpx deprecation remains unrelated.

The server can have sent TRANSCRIBING before cancellation without the edge having
handled it yet. Waiting for STT entry or backend task cleanup does not drain that
incoming stream. `cancel()` previously retained `session_id`, and the status handler
accepted any message matching it, including FOLLOW_UP that could reopen capture.
An event-gated real-socket test reproduced the exact IDLE-to-TRANSCRIBING regression
three times on each available Windows Python 3.11.9 and 3.12.10 before the fix.

The edge now revokes its active identity before the first asynchronous cleanup wait,
retains local UUIDs for the outgoing cancellation, and checks session, upload or
playback request, terminal completion and generation. A handler blocked on capture
must recheck after acquiring that lock. Old playback frames cannot start sound or
clear newer transfers; queued ordinary output and late chime completion are stopped.
Capture remains suppressed during cleanup. Independent alarms and existing hardware
receipts/replay protection stay on their original paths. Valid follow-up speech
still uses fresh wire identities and the existing backend conversation.

`tests/test_voice_cancellation.py` deliberately releases delayed statuses during
cleanup, after cancellation and after a new turn, covers lock-waiting handlers,
request mismatch, terminal duplicates, stale/queued playback, queued alarms and
late chimes, then exercises a fresh wake and follow-up over authenticated sockets.
The original failing recovery assertion is retained. Timeouts were not increased,
and no test was skipped or marked flaky. Interruption tests also verify cleanup of
partial/playing speech before accepting a new turn, without waiting for a real timeout.

| Check for this repair | Result |
|---|---|
| Deterministic reproduction before the fix | 3/3 failures on each local Python version, exact delayed TRANSCRIBING regression |
| Final focused repetition (original failing test plus 17 regressions) | **20 consecutive runs on each Python version**, 360 executions each / **720 passed total** |
| Full Windows Python 3.11.9 / 3.12.10 suites | **316 passed on each**, including all original 299; existing Starlette/httpx warning on 3.11 only |
| Voice simulation / original transport simulation | **21 voice cases passed on each Python version**; transport accepted simulated 35% ACK and 16000 in-memory PCM bytes on each |
| Frontend unit / Chromium browser suites | **26 / 9 passed**; browser cases cover all three existing portrait/desktop projects |
| Lint, format, dependencies, generated contracts | Ruff passed, 112 Python files formatted; both pip checks passed; npm audit reported zero vulnerabilities; frontend format/typecheck/build and generated TypeScript/validator check passed |
| Protocol/application/voice/browser schemas | All four exports unchanged; no protocol or dependency changes |

Local Linux execution is unavailable (WSL and containers are not installed).
The pushed fix must pass all four Linux/Windows Python matrix jobs and the
dashboard job before Phase 7. Hosted results belong to the exact pushed SHA;
passing this Windows verification alone is not evidence that Linux CI passed.
Real models, sound devices, Pi/Feather hardware and deployed services were not used.

## Phase 6 delivery and validation (initial milestone)

See [PHASE6_DASHBOARD.md](PHASE6_DASHBOARD.md) for pairing, API/cursors, privacy,
component ownership, layout priorities, voice timing, kiosk/TLS, benchmarks and the
complete legacy disposition. Package version is 0.6.0. New SQLite migration 3 holds
only hashed browser credentials and pairing approvals in the existing database.
Existing application/voice contracts remain v1. Additive edge `voice.control` and
`voice.control_ack` confirm persisted software mute. Stop uses existing session
cancellation and clears follow-up eligibility; alarms/replay protection remain owned
by the existing runtime. An end-to-end long-response case found and fixed stuck
browser captions after cancelled delivery tracking closed.

The old React monolith/styles were replaced with transport/store/components/widgets,
shader animation and static fallback. Browser state never becomes an independent
timer/alarm database. Daily charts use actual hours from the shared weather cache;
weekly results alone deliberately contain none. Unavailable data stays unknown.
Automatic home/media confirmations expire while explicit views persist. The
standalone Piper speaker audition moved to `tools/audio/`; remaining legacy
runtime modules are retained because old supervisor/agent imports still use them.

Validation is recorded against this tree below; the previous phase tables are
historical. No deployment or physical acceptance is implied by simulations.

| Check | Phase 6 result |
|---|---|
| Full Python 3.11.9 / 3.12.10 on Windows | **299 passed on each**; all original 272 retained; existing Starlette/httpx warning on 3.11 only |
| Frontend unit/schema/state tests | **26 passed**, including original four weather cases |
| Chromium browser integration | **9 passed** across 1080x1920, 720x1280, 1440x900; complete voice/tools, reload, multi-timer pause/resume, both expiry paths, cancellation/revocation, mute and WebGL fallback |
| Ruff, format, schemas, typecheck/build, simulations | Passed: Ruff lint/111-file format, generated contracts/schema exports, frontend format/typecheck/build, transport and 21-case voice simulation, both pip checks and 0.6.0 editable installs, workflow/compose YAML |
| Bundle | About 778 kB JS / 196 kB gzip total; 292 kB / 72 kB gzip entry, lazy Three.js 470 kB / 117 kB gzip; prior 1026 / 284 kB |
| Visual review | Real fixture screenshots, bounded/nonoverlapping geometry checks, long captions, weather, countdown, alarm/offline/settings; reviewed fixture captures; reduced motion and actual WebGL context-loss fallback tested |
| Unavailable here | Linux/WSL, Docker/container build/run, real Pi/display/GPU/CPU/RSS/soak, trusted models, live weather/HA/cloud |

## CI recovery synchronization follow-up

The [Phase 5 Actions run](https://github.com/NoUhMaybe/EveMirror/actions/runs/39145728735)
failed on Ubuntu 24.04.5 / Python 3.11.17: 270 passed and the speaking-disconnect
case timed out waiting for playback. Matrix fail-fast cancelled the other three
foundation jobs. The separate Starlette/httpx warning did not cause the failure.

This was a test synchronization defect. The speaker fixture records completion
inside its driver thread, before the playback task sends its completed receipt,
the backend sends FOLLOW_UP, the edge finishes its old turn and the echo tail
expires. The test could inject follow-up PCM in that gap; half-duplex capture
correctly discarded it. A bare player-busy assertion could also observe the old
response instead of the intended second response.

Fixture input now waits for matching controller/capture states, a completed turn,
inactive output and the configured wake/echo deadlines. The disconnect test also
requires a second transcription and SPEAKING under a new playback request ID.
The busy-input test injects frames directly. A new event-gated socket regression
holds completion and FOLLOW_UP separately, verifies discarded premature frames,
then verifies a valid follow-up reuses the conversation without another chime.
Production runtime, echo/cancellation policy and hardware replay protection are
unchanged. Foundation matrix `fail-fast: false` preserves every platform's results.

Linux execution is unavailable locally: WSL is not installed and no Docker/Podman
runtime is present. The original timeout was reproduced with an event-controlled
FOLLOW_UP delay on Windows Python 3.11.9, where all 14 premature input frames were
discarded. Unmodified normal runs passed 10/10 on Python 3.11.9 and 20/20 on
Python 3.12.10; normal-run success alone did not establish correct synchronization.

Validation after the repair:

| Check | Actual result |
|---|---|
| Speaking-disconnect case plus event-gated regression | 20 consecutive runs of both tests on each Windows Python version: 80 test executions passed |
| Full Python 3.11.9 suite, fresh pinned development environment | **272 passed**, including all original 271; one existing Starlette/httpx deprecation |
| Full Python 3.12.10 suite, existing Phase 5 verification environment | **272 passed** |
| Ruff lint / format; pip check in both environments | Passed; 102 files consistently formatted, no broken requirements |
| Protocol/application/voice schema exports | Passed with no changes |
| Original real loopback transport simulation, Python 3.11 and 3.12 | Passed: simulated 35% ACK and 16000 in-memory PCM bytes |
| Frontend tests / typecheck / build | **4 passed** / passed / passed; existing 1.026 MB JS bundle warning |
| Workflow YAML / matrix / scope | Valid; all four foundation jobs retained; production code and hardware paths unchanged |

Updated Linux/hosted Actions results remain pending; no push or deployment was
performed during this repair. No test was skipped, suppressed or given a larger
timeout. The Starlette/httpx warning remains separate and unchanged.

## Phase 5 delivery and actual validation (initial milestone, 7c13390)

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

## Exact next steps: controlled deployment and physical acceptance

1. Inspect the milestone's Linux/Windows foundation, browser, container, Linux voice
   install and ARM64 wheel jobs. Keep production deployment separately authorized.
2. In a separately authorized deployment window, configure exact TLS origin, proxy
   trust, browser grants and pairing; retain database/build/profile rollback copies.
3. Run Phase 5 real-model/audio and Phase 6 native portrait, reboot, renewal,
   cancellation/mute, offline timer and actual HA acceptance. Measure Pi render,
   memory/CPU and eight-hour soak before selecting a quality default.
4. Retire old supervisor/relay/voice modules together only when hardware rollback is
   no longer needed. Preserve firmware and independent hardware/audio utilities.
5. Select the physical presence sensor and electrical design, implement its exact
   reviewed protocol driver, then request installation/physical acceptance approval.
   The implemented simulator and local policy do not establish sensor accuracy.
