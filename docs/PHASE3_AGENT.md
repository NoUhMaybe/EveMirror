# Phase 3 text agent

The text agent is part of `apps/server/main.py`, using the same gateway and
credential boundary as the Phase 2 transport. It does not attach the audio
consumer to STT or TTS. `legacy/` and the dashboard's old relay remain necessary
for the retained voice/weather experience.

## Implemented pipeline

`POST /api/agent/turn` sends normalized messages and tool definitions to one
configured provider. Native structured calls pass through a single registry,
JSON Schema validation, strict native argument models, backend policy and a
bounded executor. Structured success/error results return to that same provider
until it produces a final response or a limit/error ends the turn. Calls execute
in model order; mutations are not parallelized or automatically retried.

There is no keyword routing and no production canned model or tool response.
Tests inject provider HTTP transports and simulated hardware explicitly.

| Provider | Production API | Native tools / multiple calls | Private context handling | Generation settings |
|---|---|---|---|---|
| Ollama | Native non-streaming `/api/chat` via httpx | Function definitions, parsed calls, ordered `tool_name` results | Original assistant message, including optional thinking, is replayed | Output limit, optional temperature and boolean `think` |
| OpenAI | Official `AsyncOpenAI.responses.create` | Function items and correlated `function_call_output` items | All output items, including reasoning/encrypted state, replayed; `store=false`, no remote conversation ID | Output limit, optional temperature and reasoning effort |
| Anthropic | Official `AsyncAnthropic.messages.create` | Tool-use blocks and grouped user tool-result blocks with `is_error` | Separate system instructions; original assistant blocks replayed | Output limit and optional temperature; extended/adaptive thinking is not configurable yet |

Provider-safe aliases use canonical names plus a digest; the executor always
uses canonical Eve identities. Plain assistant text never becomes a tool call.
Incomplete tool responses cannot execute. Unsupported settings fail explicitly;
model-specific support is left to the provider's documented validation, without
model-name heuristics. SDK automatic retries are disabled. HTTP/SDK failures are
converted to stable codes without returning their exception bodies.

Generation is non-streaming in this milestone. `AgentStreamEvent` defines the
future internal event boundary; no streaming endpoint or working stream adapter
is claimed. MCP resources/prompts, provider-hosted tools, multimodal input/output,
arbitrary generation kwargs, model downloads and cross-provider fallback are
unsupported.

## Configuration and routing

All settings extend `apps/config.py`; there is no implicit `.env` discovery.
Compose explicitly loads `deploy/server/server.env`. Complete examples are in
[server.env.example](../deploy/server/server.env.example).

For local development, alongside the existing distinct operator/edge tokens:

```powershell
$env:EVE_SERVER_LLM_PROVIDER = 'ollama'
$env:EVE_SERVER_OLLAMA_BASE_URL = 'http://127.0.0.1:11434'
$env:EVE_SERVER_OLLAMA_MODEL = '<installed-tool-capable-model>'
$env:EVE_SERVER_ALLOW_CLOUD = 'false'
.\.venv-dev\Scripts\python.exe -m uvicorn apps.server.main:create_app --factory --host 127.0.0.1 --port 8000 --workers 1 --ws-max-size 24000 --ws-max-queue 8 --no-access-log
```

No inference request occurs at startup. An absent model or active cloud key is
reported as unconfigured by `/api/agent/status`; turns receive HTTP 503 while
edge/audio/health operations continue working. The default is Ollama with no
model assumed. An inactive cloud provider needs no key. To select OpenAI or
Anthropic, set `EVE_SERVER_ALLOW_CLOUD=true`, `EVE_SERVER_LLM_PROVIDER`, and the
matching `EVE_SERVER_OPENAI_MODEL` / `EVE_SERVER_OPENAI_API_KEY` or
`EVE_SERVER_ANTHROPIC_MODEL` / `EVE_SERVER_ANTHROPIC_API_KEY`.

Eve never silently reroutes a turn. Even enabling cloud access does not enable
fallback. Cloud selection sends user context and permitted tool definitions /
results to the selected provider. Keys stay in the server environment; they are
neither API output nor edge/dashboard configuration. OpenAI `store=false` avoids
Eve requesting stored Responses; it is not a guarantee about all provider-side
retention policies. Local-only routing assumes the administrator's Ollama endpoint
and chosen model actually perform local inference; do not configure a cloud-backed
Ollama model or proxy when local-only inference is required. Endpoint URLs cannot
contain embedded credentials, query parameters or fragments. HTTP is permitted
for administrator-configured local/LAN Ollama services; protect that network path.

Optional generation settings are `EVE_SERVER_LLM_TIMEOUT` (45 seconds),
`EVE_SERVER_LLM_MAX_OUTPUT_TOKENS` (1024), `EVE_SERVER_LLM_TEMPERATURE` (unset),
`EVE_SERVER_OLLAMA_THINK` (unset) and `EVE_SERVER_OPENAI_REASONING_EFFORT` (unset).
`EVE_SERVER_AGENT_PROMPT_SUFFIX` adds trusted administrator instructions to the
central voice-friendly prompt. It does not grant tool permissions.

## Tools, permissions and limits

| Canonical tool | Availability / behavior | Permission |
|---|---|---|
| `system.get_time` | Real UTC date/time, no external service; accepts `{}` | Read-only |
| `mirror.get_status` | Correlated gateway `get_status`; returns actual edge ACK/state or an honest failure | Read-only, authorized device only |
| `mirror.set_brightness` | Correlated gateway command through the existing edge journal and Feather service | Low-risk mutation, disabled by default |
| Approved `mcp.<server>.<tool>_<digest>` | Discovered schema with administrator description and policy; unavailable if disconnected/missing | Explicit administrator category |
| Weather, timers, HA, media, search, dashboard | Added in [Phase 4](PHASE4_SERVICES.md), using this same registry | Read-only or explicitly approved low-risk mutation; availability depends on service/configuration |

Mirror tools accept optional `device_id`, defaulting to the session's bound
device or a principal's sole device. Brightness also requires integer `percent`
in 0–100. Extra native arguments and unauthorized devices are rejected. Brightness
requires `EVE_SERVER_AGENT__ALLOW_MUTATIONS=true` and a principal that permits
mutations. Operators qualify for the latter; scoped clients default to read-only.
Sensitive and confirmation-required tools cannot execute in Phase 3; no model
argument or prompt can provide confirmation or override backend policy.

The new agent never imports serial or firmware code. Hardware request IDs derive
from principal, turn UUID, device and normalized command, preserving edge replay
semantics across repeated delivery. Read-only status calls get fresh correlation
IDs so a status query after a mutation cannot replay an older observation.
Device-error ACKs become tool errors. An accepted target is not actual brightness
or fade completion; both remain unknown with existing firmware.

Duplicate call IDs reuse their receipt; conflicting arguments are rejected.
Identical existing hardware/generic mutations in one turn execute once even if
the provider supplies new call IDs. Phase 4 timer/HA tools instead use call identities
or explicit operation UUIDs, allowing intentional identical actions. Reused execution receipts carry `replayed=true` and describe historical
execution, never a fresh reading or new state change. Timeout/cancellation after a
mutation starts is indeterminate. There is no automatic retry. Durable replay
protection is provided by the edge for native hardware actions, not by a generic
durable MCP transaction journal. Inspect uncertain outcomes before issuing a new turn.

Limits use `EVE_SERVER_AGENT__<NAME>` (or the equivalent nested JSON `EVE_SERVER_AGENT`):

| Name | Default |
|---|---|
| `MAX_TOOL_CALLS` / `MAX_TOOL_ROUNDS` | 8 calls / 4 rounds per turn |
| `TOOL_TIMEOUT` / `TURN_TIMEOUT` | 10 / 90 seconds |
| `MAX_ARGUMENT_BYTES` / `MAX_RESULT_BYTES` | 8192 / 16384 UTF-8 bytes |
| `MAX_CONTEXT_BYTES` / `MAX_CONTEXT_MESSAGES` | 131072 bytes / 64 messages for generation |
| `SESSION_IDLE_SECONDS` / `MAX_SESSIONS` | 60 seconds / 128 sessions |
| `MAX_TURNS_PER_SESSION` | 64 receipts, then start a new session |
| `ALLOW_MUTATIONS` | false |

Each tool can have a smaller timeout. Oversized results become errors, never
fabricated success. Whole completed turns are pruned to half the context budget
to leave room for the next turn; tool request/result groups and private provider
state are never split. In-flight context includes the system prompt and tools.
There is no summarizing LLM call, persistent transcript store, audio retention or
cross-session global conversation history.

## MCP approval and lifecycle

`EVE_SERVER_MCP_SERVERS` is a JSON list, empty by default. Each definition names
`stdio` with an administrator-chosen executable/args and optional explicit secret
environment, or `streamable_http` with a fixed URL and optional backend-only bearer
token. Remote HTTP requires HTTPS; unencrypted loopback is allowed for tests.
The SDK restricts redirects to prevent cross-origin credential forwarding.

Each server requires an `allowed_tools` mapping from exact remote name to trusted
`description`, `permission`, `mutates`, `requires_confirmation`, and `timeout`.
Missing fields use read-only/non-mutating defaults; classify actual state changes
accurately. Treat this file as privileged configuration. Never approve unrestricted
shell, filesystem, arbitrary-network or broad Home Assistant service tools.
Stdio launches a trusted executable; it is not a sandbox for hostile server code.
Run external servers with least-privilege accounts and restricted credentials.

Only discovered, explicitly approved tools enter the registry. Server annotations
never grant permission, and server instructions/descriptions are not promoted into
the system prompt. Schemas must be bounded object schemas with local-only
references; external file/network references and base URI overrides are rejected.
Structured results or text are supported; other content returns a clear error.
Results stay in tool messages as untrusted data. Root enumeration, sampling,
elicitation, resources, prompts and server log forwarding are not enabled.

One task owns each SDK session/transport from initialization through shutdown.
Discovery is paginated and bounded. Startup errors leave the application available
with an unavailable MCP status. A later new turn may reconnect and rediscover;
failed execution is never replayed during reconnect. Cancelling an active MCP
call closes that session. Server shutdown cancels active turns and closes clients
and child processes. This connection closure cannot roll back an external action.

## Authentication, sessions and API

All agent routes require an operator credential or an optional scoped backend
client credential, never an edge credential. Browser Origin headers are rejected;
do not put these credentials in React. Configure optional independent clients:

```text
EVE_SERVER_AGENT_CLIENTS={"terminal":{"token":"<distinct-32+-character-token>","device_ids":["mirror-1"],"allow_mutations":false}}
```

Sessions belong to the authenticated principal, not a supplied client name. Two
callers sharing one token are the same principal; use distinct configured tokens
for isolation. Scoped clients cannot use existing operator endpoints or read other
clients' sessions, and their device allowlists are enforced by native tools.
Sessions bind to a device where supplied (or the principal's sole device).

| Method / route | Request / result |
|---|---|
| `POST /api/agent/sessions` | `{device_id?: string}` → `session_id`, idle lifetime |
| `POST /api/agent/turn` | `{text, request_id?: UUID, session_id?: UUID, device_id?: string}` → final text, session/request IDs, provider/model, status/error, tool summaries, usage, latency |
| `POST /api/agent/sessions/{id}/reset` | Clear context; refuses an active session |
| `POST /api/agent/sessions/{id}/cancel` | Cancel the active task; returns whether requested |
| `GET /api/agent/status` | Non-secret configuration, tool policy/availability and MCP connection state |

Example body:

```json
{"request_id":"744d0841-62ec-48f3-8ce4-19dab6d6c17d","text":"What time is it, and what is the mirror's current brightness?","device_id":"mirror-1"}
```

Reuse the returned `session_id` for follow-up text. A single session has one
active turn; conflicts return 409. Foreign or expired session references return
404 without revealing ownership. A background reaper removes inactive sessions;
reset removes generation context but retains bounded retry receipts until expiry.
Completed request UUIDs reuse their result without running the model/tools again,
even if the original request omitted a session ID. A UUID with different input
returns 409. Under the response-cache byte limit, older result text is discarded
while ID/fingerprint tombstones remain; retrying such a request returns 409
`retry_result_expired`, without re-execution. Response text disappears on session expiry/server restart. Phase 4 additionally
persists hashed turn claims and native operation receipts: reusing an old request
UUID after cache loss returns a processed/indeterminate/conflict error instead of
regenerating actions. Inspect authoritative state before any new uncertain action.

Requests are bounded to 32 KiB before parsing (413 on overflow); text is limited
to 8192 characters / 16384 UTF-8 bytes. Malformed input returns 422; missing
configuration/capacity returns 503. Accepted turns return HTTP 200 with status
`complete`, `error` or `cancelled`; inspect status and error code. A completed
assistant response can still contain failed tool summaries. Those summaries expose
tool identity/status/receipt flags, not arguments, raw results or private reasoning.

The development CLI calls these routes, supports repeated text, `/reset`, `/status`,
`/quit`, and requests cancellation on Ctrl+C. Provider selection is deliberately
server configuration, not a per-request/CLI override that could change privacy routing.

## Verification boundaries and subsequent work

Tests use the real OpenAI/Anthropic SDKs with mocked HTTP and the native Ollama
adapter with mocked HTTP. All three follow the same time/status and simulated
brightness loops. A real isolated MCP subprocess and authenticated loopback MCP
HTTP server test discovery, allowlists, structured/text results, errors,
disconnect/reconnect, timeouts and cleanup. The CLI subprocess talks to a real
loopback backend. No live inference, cloud keys, Home Assistant or physical devices
are required or claimed. A tool-capable installed model and its live endpoint
remain deployment verification tasks; deterministic tests cannot establish model
quality or whether a chosen model supports particular reasoning settings.

Phase 4 implemented SQLite timer/alarms, durable native receipts and turn replay
markers, backend weather, restricted native HA/media, optional search and semantic
state/events. See [PHASE4_SERVICES.md](PHASE4_SERVICES.md) and the current
[implementation status](IMPLEMENTATION_STATUS.md) for configuration and actual
validation. Voice integration is Phase 5; browser authentication/React migration
and legacy retirement remain later milestones.

Official implementation references:
[Ollama tools](https://docs.ollama.com/capabilities/tool-calling),
[OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling),
[OpenAI Responses](https://developers.openai.com/api/reference/python/resources/responses/methods/create),
[Anthropic tool results](https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls),
[MCP Python SDK clients](https://github.com/modelcontextprotocol/python-sdk/blob/v1.x/docs/client.md).
