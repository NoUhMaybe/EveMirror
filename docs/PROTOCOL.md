# Protocol v1

Python definitions: `packages/protocol/__init__.py`; portable discriminated JSON
Schema: `packages/protocol/schema.json`. Regenerate with
`python scripts/export_protocol.py`. The schema consistency test prevents drift.
TypeScript generation/browser integration follows in the dashboard phase.

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

The default consumer discards PCM after receipt. Tests inject a fake speech
consumer. A future STT/agent service must implement the consumer contract; no
STT/TTS readiness is inferred from this transport test.

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

Current snapshots restore transport/hardware metadata, not timers, weather or
conversations. Temporary agent context is private to its authenticated principal;
its API is separate from device protocol v1. Timers/weather and browser
authentication remain pending.

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
409 `retry_result_expired`, never re-execution. These are not a persistent agent
transaction journal. Hardware mutations derive stable UUIDs from the turn,
principal/device and typed command, and use the same gateway deadline, ACK/error
and durable edge journal as existing operator commands. No alternate wire route
was added, and the v1 device/audio JSON Schema is unchanged.

The API cannot override provider/model, permissions or confirmation through input.
For full schemas, configuration, privacy and examples see
[PHASE3_AGENT.md](PHASE3_AGENT.md).
