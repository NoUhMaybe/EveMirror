# Protocol v1

Python definitions: `packages/protocol/__init__.py`; portable discriminated JSON
Schema: `packages/protocol/schema.json`. Regenerate with
`python scripts/export_protocol.py`. The schema consistency test prevents drift.
Browser TypeScript and CSP-safe validation are generated from the additive browser
projection; see [Phase 6](PHASE6_DASHBOARD.md). Existing wire contracts stay version 1.

Phase 6 adds `voice.control` (`action: set_muted`, strict boolean `muted`) and
`voice.control_ack` (`status: completed|error`, actual `muted`, bounded optional
error). They use the existing authenticated edge connection and request UUID;
only an acknowledgment from that live connection/request completes browser mute.
There is no browser bearer or browser-to-Feather path. Mute is sent only when the
edge advertises `voice_control`; old edges stay connected without this action.
Upgrade the backend before a new edge because old strict servers reject unknown
capabilities. Existing session cancellation is
reused for Stop Eve, including follow-up; alarm acknowledgment remains separate.

The separate generated `packages/application/browser.schema.json` wraps the
unchanged application and voice snapshots in `BrowserFrame` v1. Cookie-authenticated
`GET /api/browser/state?after=N&voice_after=V&epoch=UUID` returns full scope-filtered
state and bounded existing durable/volatile events. New/invalid/expired cursors or
new process epochs request a reset. Notifications precede a transactional full
snapshot; retain the notification cursor so a concurrent mutation cannot be lost.
No notification patches a newer projection. Browser POSTs require exact Origin and
CSRF, and finite actions are checked against existing tool schemas/permissions.
See the [browser protocol and pairing guide](PHASE6_DASHBOARD.md) for all routes,
credential boundaries, recovery, deduplication and generated TypeScript checks.

Each envelope contains `version: 1`, `type`, `device_id`, `request_id` (UUID),
`timestamp` (timezone-aware), optional `session_id`, and a typed `payload`.
Unknown fields, actions, versions, invalid ranges and invalid audio encodings are rejected.
Maximum JSON text frame size: 24,000 bytes. Uvicorn must also enforce this limit
before allocating incoming frames (see deployment commands).

## Connection and authentication

`/ws/edge/{device_id}` accepts the device's `Authorization: Bearer ...` header.
Tokens are not URL parameters. Each device has a different token. Browser Origin
headers are rejected on this device-only endpoint. First message must be
`edge.hello` within five seconds, with the same device ID as the authenticated path.
The server sends `state.snapshot`, then accepts periodic `heartbeat` messages
and echoes them. Missing traffic closes the connection after the configured timeout.
Only one live connection per device is accepted.

Edges reconnect with exponential jittered backoff. They do not replay audio or
pending hardware commands automatically. The gateway is single-process for now;
do not configure multiple Uvicorn workers or independent replicas.

## Hardware command example

```json
{
  "version": 1,
  "type": "device.command",
  "device_id": "mirror-1",
  "request_id": "604e7a77-79a3-4c0f-b6de-e37ec85becdc",
  "timestamp": "2026-10-17T17:00:00Z",
  "expires_at": "2026-10-17T17:00:07Z",
  "payload": {"action": "set_brightness", "percent": 35}
}
```

This uses a discriminated payload instead of the historical untyped `arguments`
example. Supported actions are `set_brightness`, `get_status`, and
`set_display_mode` (`awake` / `sleep`). Sleep sends `B0`; awake currently sends
`B100`. Presence overrides/restoration policy is a later phase.

The edge sends `device.ack` with the original request ID and `payload.status`:

- `accepted`: firmware returned the exact `OK <target>` acknowledgment.
- `completed`: a local status query completed.
- `error`: deadline expired, conflict, unavailable device, invalid acknowledgment
  or indeterminate execution. Neither invalid nor missing ACK proves no action occurred.

`hardware.target_percent` is last acknowledged target, not a measurement.
`actual_percent` and `fade_complete` are always null with the original firmware.
`simulated: true` explicitly marks the test implementation.

The edge journals a request before executing it. The same ID/payload returns the
original result with `payload.replayed=true`; a different payload is rejected.
An interrupted request remains indeterminate after restart. Full acknowledgments
are retained for 24 hours and pruned on subsequent commands. Minimal request-ID /
fingerprint tombstones persist to reject older ID reuse. Commands live at most
60 seconds; expired envelopes cannot execute. This assumes synchronized UTC
clocks; configure NTP before hardware validation. Future timestamps tolerate five
seconds of skew. A timeout or dropped connection returns an indeterminate error
to the operator and is never automatically retried.

## Audio upload

1. `audio.begin`: unique session ID, shared request ID, `pcm_s16le`, mono,
   16 kHz, declared positive even byte count (maximum 960,000 / 30 seconds).
2. `audio.chunk`: same IDs, sequence starting at zero, validated base64 PCM;
   at most 16,000 decoded bytes, aligned to 16-bit samples.
3. `audio.end`: exact chunk count. Received bytes must equal the declaration.
4. `audio.received`: exact received byte count. This confirms receipt only.

Base64 is a transitional transport: it adds overhead but keeps framing explicit.
The interfaces allow later binary streaming and partial transcripts without
filesystem polling. Current transmission is whole-utterance input, sent in
bounded frames. One upload per edge and two audio consumers server-wide are
allowed by default. Idle, total-duration and consumer deadlines are enforced.
Invalid/incomplete buffers are discarded; disconnect clears them. Reused audio
session IDs on a connection are rejected. A bounded replay window forces a clean
reconnect after 1,024 sessions. `session.cancel` discards an upload or cancels its
consumer; cancelled sessions do not produce successful receipts.

Peers without negotiated voice retain the original discard/injected consumer.
Voice peers receive transport receipt before asynchronous STT/agent/TTS work;
completion of that work uses separate voice/playback messages below. Disabled or
unauthorized speech returns an explicit voice error. Receipt is never proof of
transcription, a tool action, synthesis or playback.

## Operator endpoints

Existing operator endpoints require the separate operator Bearer token. Agent
endpoints additionally accept explicitly configured scoped backend clients. Device
tokens cannot issue these HTTP requests. Do not distribute privileged tokens to browsers.

- `GET /api/state`: current snapshot, including offline configured devices.
- `GET /api/health`: readiness, edge heartbeats/status, errors and audio counters.
- `POST /api/devices/{id}/commands`: `{request_id: UUID, command: typed payload}`.
  The server creates the envelope/deadline and waits for a correlated ACK.
  HTTP 200 confirms delivery of the ACK; inspect `payload.status` for device success
  or failure. A device error must never become a successful tool result.
- `GET /health/live`: unauthenticated status only, suitable for loopback/container checks.

These existing snapshots restore transport/hardware metadata. Phase 4 application
snapshots/events below separately restore timers, alarms and weather; device/audio
v1 stays unchanged. Temporary conversation context remains private and memory-only.
Browser authentication remains pending.

Phase 5 adds `POST /api/devices/{id}/voice/cancel` for operators. It cancels voice
processing and ordinary playback; it cannot undo a hardware/HA action already issued.

## Text agent HTTP API (Phase 3)

`POST /api/agent/turn` accepts `text`, optional `session_id`, optional `device_id`,
and optional `request_id` UUID (send an explicit UUID to recognize retries). It
returns session/request IDs, final `response`, `provider`, `model`, `status`, stable
`error` code, `tools` summaries, summed token `usage` and `latency_ms`. Accepted
turns use HTTP 200; inspect `complete` / `error` / `cancelled` status and each tool
summary. A final response can describe a failed tool. Tool arguments, raw outputs
and private reasoning blocks are not returned in summaries. Reused tool receipts
are marked `replayed=true`; they describe earlier execution, not new observations.

`POST /api/agent/sessions` creates context; `POST /api/agent/sessions/{id}/reset`
clears it; `/cancel` cancels its active task. `GET /api/agent/status` returns only
non-secret configuration/policy/availability. Origin headers and edge credentials
are rejected. Separate agent-client tokens are optional, with device allowlists
and mutation policy; they grant no access to existing operator endpoints. Foreign
or expired sessions return 404. Active-session/request conflicts return 409,
unconfigured providers/capacity return 503, invalid input 422, and bodies over
32 KiB 413. Sessions expire after 60 idle seconds by default.

Turn UUIDs reuse bounded in-memory receipts until session expiry. Context reset
retains retry receipts. Evicted response text leaves a tombstone that returns
409 `retry_result_expired`, never re-execution. Phase 4 adds a durable hashed turn
claim: after cache loss, a reused UUID returns `turn_already_processed`,
`turn_indeterminate`, or `request_conflict`, instead of regenerating actions.
Old supplied session IDs still follow the existing 404 expiry behavior. This does
not persist conversation text or provide generic durable MCP transactions.
Hardware mutations derive stable UUIDs from the turn,
principal/device and typed command, and use the same gateway deadline, ACK/error
and durable edge journal as existing operator commands. No alternate wire route
was added. Phase 5 subsequently adds negotiated voice messages to that v1 schema.

The API cannot override provider/model, permissions or confirmation through input.
For full schemas, configuration, privacy and examples see
[PHASE3_AGENT.md](PHASE3_AGENT.md).

## Application HTTP state/events (Phase 4, schema version 1)

`GET /api/application/state` returns `version`, aware `timestamp`, database
`revision`, private timers/alarms, freshness-labeled weather, approved cached device
observations, semantic views/layouts, recent tool summaries and availability.
The state and event revision are read in one SQLite transaction. Only resources
belonging to the authenticated principal and permitted device IDs are included;
no conversation history is returned.

`GET /api/application/events?after=<sequence>&limit=<1..200>` returns `version`,
`cursor` and scoped `events`. Each event has `event_id`, aware `timestamp`,
`sequence`, `scope`, optional `device_id`/`resource_id`, `type`, `payload`, and
`version: 1`. Consumers start with a snapshot, resume after its revision and
deduplicate by event UUID. A truncated page advances only to its last event;
an exhausted page can advance past other scopes without revealing their payloads.
Retained history defaults to 10000 events. Too-old or incompatible cursors return
409 `snapshot_required`; fetch a new snapshot. Timer/alarm state survives event
retention independently, and pending alarms remain until explicit acknowledgment.

These routes reuse operator/scoped agent Bearer credentials, reject browser
Origins and edge tokens, and report 503 if persistent storage is unavailable.
They add durable polling, not a browser session or WebSocket event stream.
Semantic commands accept finite views/layouts, never CSS/HTML/JavaScript. A pending
alarm protects the timer view. See [PHASE4_SERVICES.md](PHASE4_SERVICES.md) for
event types, permission policy, operation UUIDs and reconnect/recovery details.

Python models live in `apps/server/services/events.py`, `models.py` and
`weather.py`. Regenerate the separate portable contract with
`python scripts/export_application.py` into `packages/application/schema.json`.
The original `packages/protocol/schema.json` remains the device/audio contract.

## Negotiated distributed voice (Phase 5, additive v1)

`edge.hello.payload.capabilities` advertises `voice`, `playback` and `timer_sync`.
Defaults preserve old peers; original command/upload forms remain valid. All new
messages retain authenticated device/session/request correlation and the 24,000
byte JSON limit. Cross-device, wrong-direction and foreign-session messages fail.

- `voice.status`: server phases, bounded captions, conversation ID, transcript
  language/model/final metadata, tool state and stage metrics. `DELIVERING` precedes
  output; `SPEAKING` follows the edge's actual software started receipt.
- `voice.edge_state`: mute, capture/wake/VAD/output readiness, RMS, errors and
  timings. Availability is last reported software state, not a hardware probe.
- `playback.begin`: declared PCM16 mono format, rate, bytes, source sample count,
  duration and optional alarm UUID. Only bounded, consistent metadata is accepted.
- `playback.chunk` / `playback.end`: ordered base64 PCM (at most 16,000 decoded
  bytes per frame) and exact final byte/chunk counts. The edge buffers one bounded
  response and starts output only after validation of the complete transfer.
- `playback.status`: accepted/buffered flow control, then software started,
  progress, completed, cancelled, failed or indeterminate. `position_samples`
  counts **source-rate** samples; `started_at` is aware software UTC. Sending bytes
  never marks completion. The server waits for each transfer receipt with bounds.
- `playback.cancel`: correlated cancellation of assembly or output. Native work
  cancellation is cooperative; completion is never fabricated after cancellation.
- `timer.sync` / `timer.sync_received`: complete paginated snapshots, generation
  UUID and durable-cache storage receipt. Maximum 16 records/frame and 1024 total;
  partial generations cannot replace prior schedules. Reconnect replays historical
  alarm receipts, never the sound; `replayed_receipt` identifies reconciliation.
- `alarm.dismiss`: explicit device-scoped alarm UUID acknowledgment, queued
  durably offline. Alarm playback and backend pending/acknowledged state are separate.

`session.cancel` also cancels an accepted voice consumer by its upload IDs.
Disconnect discards utterances/responses and preserves independent cached alarms.
No automatic audio/turn replay occurs. Legacy transport snapshot `stt`/`tts`
placeholders remain compatible; `/api/health` contains current nested speech status.

`GET /api/application/voice?after=<revision>` returns the separately generated
`packages/application/voice.schema.json` contract: scoped current voice state,
bounded volatile events/captions, `resync_required`, voice-owned widget snapshots
and durable alarm-delivery metadata. Operators qualify; scoped agent clients need
`allow_voice_state=true` plus device grants. This delegates voice-owned widget
visibility only, excluding other principals' private state. Origins/device tokens
are rejected. Caption TTL defaults to 60 seconds and history to 128 events/device;
restart/retention requires resync. The existing application v1 schema is unchanged.

See [PHASE5_VOICE.md](PHASE5_VOICE.md) for exact state transitions, offline lease,
at-most-once attempt limitations, privacy and failure recovery.
