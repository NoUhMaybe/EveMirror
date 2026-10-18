# Phase 4 backend services

The Phase 6 [paired dashboard](PHASE6_DASHBOARD.md) now consumes these same services,
receipts, timers and semantic events through a separate scoped cookie boundary.
The trusted bearer APIs documented here retain their existing authorization rules.

Phase 4 extends the existing FastAPI application, tool registry, provider adapters
and scoped text API. Production implementations perform SQLite, Open-Meteo,
restricted Home Assistant REST and optional SearXNG requests. Automated tests inject
HTTP fixtures; production code does not substitute fabricated device/weather data.
No live Home Assistant, inference, weather, search or physical-device acceptance
was performed. `legacy/` and the old dashboard relay remain available.

Phase 5 subsequently adds local speech, Pi playback and durable offline alarm
caching through these same services. Database migration 2 adds alarm-delivery
receipts; playback is separate from timer acknowledgment. See
[PHASE5_VOICE.md](PHASE5_VOICE.md) for current audio behavior and acceptance limits.
This guide retains the Phase 4 service contracts and validation history.

## Start and configure

Install the updated `requirements/dev.lock` and `pip install --no-deps -e .` in the
development environment. Server-only installations use `requirements/server.lock`.
`tzdata` supplies IANA zones on Windows; edge/common dependency locks are unchanged.
Run the same backend and `scripts/chat.py` described in [DEVELOPMENT.md](DEVELOPMENT.md).
All settings extend `apps/config.py`, without implicit `.env` discovery. Full
examples are in [server.env.example](../deploy/server/server.env.example).

For timer creation and other low-risk mutations, explicitly set
`EVE_SERVER_AGENT__ALLOW_MUTATIONS=true`. Operators then qualify for those tools;
scoped clients also need their own `allow_mutations=true`. Read-only tools retain
their existing permission class. Sensitive/confirmation-required actions remain
blocked. LLM inference defaults to Ollama, cloud requires explicit opt-in, and
there is no automatic provider fallback. Configuring public weather or search is
separate from choosing a local LLM: requested tool data goes to that selected LLM.

The Compose example uses a named `eve-data` volume at `/var/lib/eve`, owned by the
image's service UID 10001. It overrides the database path to
`/var/lib/eve/server.sqlite3` while keeping the root filesystem read-only. Docker
and Linux execution remain unverified; the configuration was prepared and reviewed,
not deployed. Do not run multiple Uvicorn workers or gateway replicas.

## Timer storage, time and recovery

`apps/server/services/database.py` owns one SQLite connection, serializes complete
transactions, and runs blocking work outside the event loop. Cancellation waits
for an already-started transaction to finish before ownership is released. WAL,
`synchronous=FULL`, foreign keys, and a default 5000 ms busy timeout are enabled.
Database files and WAL/SHM companions are ignored by Git.

Schema migrations use `PRAGMA user_version`; each migration and its version change
commit atomically. Version 1 defines:

- `timers`: UUID, owner, device, optional name, original duration, paused remainder,
  UTC creation/deadline/expiry/acknowledgment/update instants and resource version.
- `alarms`: unique alarm UUID and unique timer reference, owner/device, expiry
  instant and acknowledgment instant.
- `operations`: owner/operation UUID, argument fingerprint and structured receipt;
  an unfinished external action remains indeterminate.
- `turns`: owner/request UUID, input fingerprint and completion marker, without
  conversation text or model response storage.
- `events`, `views`, `resources`: scoped semantic event revisions, selected layouts
  and last weather/device/tool presentation state.

Integrity checks, unsupported schema versions, missing tables/columns or migration
failure make persistent services unavailable. Existing files are never silently
reset. The transport gateway remains usable; application snapshots report 503 and
diagnostics identify the database failure. The scheduler attempts bounded-frequency
reopen/reconciliation, with at least one second between failed attempts; default
reconciliation is 30 seconds. Repair/restore a damaged database explicitly.

Timer tools are `timer.create`, `timer.list`, `timer.get`, `timer.pause`,
`timer.resume`, `timer.cancel`, and `timer.acknowledge`. Creation takes integer
`duration_seconds` and optional `name`; changes use an exact `timer_id`. Names may
repeat. List by name to resolve duplicates instead of guessing. Lists default to
active/paused/expired timers, paginate with `limit` (1–20), `offset`, `total` and
`next_offset`, and optionally include cancelled/acknowledged records. Exact-ID
lookup can retrieve terminal records. Each result reports remaining milliseconds,
status and UTC timestamps. Owners cannot read or mutate another principal's timers,
and all timer operations enforce authorized devices.

Statuses are `RUNNING`, `PAUSED`, `EXPIRED`, `CANCELLED`, `ACKNOWLEDGED`. Pausing
stores the remainder; resuming creates a new UTC deadline from that remainder.
The scheduler sleeps monotonically toward the nearest persisted deadline and
reconciles wall time periodically. It never decrements a browser/session counter.
UTC deadlines are authoritative: forward clock jumps may expire timers immediately;
backward jumps can extend remaining wall time. UTC/NTP correctness is operationally
important. Expiration uses transaction execution time, including after lock waits.
At or after the deadline, expiration wins over pause/cancel; acknowledge that alarm.
Overdue timers are reconciled on startup, snapshots, timer queries and relevant
presentation operations. Late processing preserves the original deadline as expiry.

Transitions, expiry and alarm creation commit before readers observe their events.
Alarm IDs derive from timer UUIDs and are unique across restarts. Pending alarms
remain authoritative until acknowledged, independently of LLM/session lifetimes.
Expiry selects a protected timer view; weather or dismiss commands cannot hide an
unacknowledged alarm. No physical sound playback is claimed.

Settings: `EVE_SERVER_DATABASE_PATH` (default `data/server.sqlite3`),
`EVE_SERVER_DATABASE_BUSY_MS` (5000), `EVE_SERVER_MAX_OPERATIONS` (100000), and
`EVE_SERVER_TIMERS__MAX_ACTIVE` (128 per owner/device, including pending alarms),
`MAX_DURATION_SECONDS` (604800), `RECONCILE_SECONDS` (30). The latter three use
the `EVE_SERVER_TIMERS__` prefix.

## Operation identity and uncertain outcomes

Phase 3 argument-based mutation deduplication remains for existing hardware and
generic tools. Timer and HA mutations use distinct call identities for new actions;
two identical `timer.create` calls create two timers. Repeating a call ID reuses its
receipt. An optional `operation_id` UUID can explicitly retrieve a prior operation
across turns/restarts; changing its arguments is a conflict. Omitted IDs derive
from authenticated principal, turn UUID, canonical tool and call ID. Returned
receipts identify the operation, and reused receipts are marked `replayed=true`.
They describe historical execution, not fresh state. Query status for current state.

Send an explicit `request_id` UUID with text requests. During a live session,
Phase 3's bounded response cache still returns duplicate results. After cache loss,
expiry or restart, the durable turn journal prevents regenerating the same request's
actions: `turn_already_processed`, `turn_indeterminate`, or `request_conflict` is
returned instead of rerunning the model. A stale supplied session ID still returns
404 under the existing session rules. Inspect authoritative timers/device state
instead of automatically creating a new request UUID after an uncertain action.

SQLite timer mutations and their receipts commit atomically. External HA mutations
reserve an operation before sending HTTP. Timeout, cancellation or process loss
after that reservation cannot cause an automatic replay; a pending receipt is
indeterminate after restart. Cancellation cannot undo an external action. This is
bounded native-action journaling, not a generic unrestricted MCP transaction system.
Native Feather command correlation, deadlines and durable edge replay semantics
are unchanged. No second hardware route was introduced.

Minimal turn/operation identities and receipts are retained without automatic
pruning; capacity is bounded by `MAX_OPERATIONS` per journal table. At capacity,
new operations fail closed. Raise the configured limit or perform reviewed
maintenance that preserves replay tombstones. Resetting sessions does not clear
durable action records. Database removal/old-backup restoration can lose newer
receipts; do not blindly replay uncertain requests afterward.

For a consistent online backup, including committed WAL contents:

```powershell
.\.venv-dev\Scripts\python.exe scripts/backup_database.py --source data/server.sqlite3 --destination backups/server-2026-10-17.sqlite3
```

Create the destination directory first. The utility requires a new destination
file and opens its source read-only. Protect backups as private application state.
For restore, stop the backend and restore a verified complete backup; do not copy
only a live database while omitting WAL contents. Record which newer operation IDs
may be missing. No credentials or full conversation transcripts are intentionally
stored; timer names, scoped state and operation metadata are persistent user data.

## Weather

`weather.current`, `weather.daily` and `weather.weekly` call the dedicated Open-Meteo
service, without importing legacy keyword routing. Defaults are Frisco, Texas,
coordinates 33.1507/-96.8236, `America/Chicago`, imperial units. Configure the
`EVE_SERVER_WEATHER__` fields `ENABLED`, `LOCATION`, `LATITUDE`, `LONGITUDE`,
`TIMEZONE`, `UNITS`, `FORECAST_URL`, `GEOCODING_URL`, `TIMEOUT`, `MAX_LOCATIONS`.
Endpoints are fixed backend configuration, not arbitrary user URLs. TLS is required
outside loopback for these endpoints.

Tools accept `location_name`, optional `country_code`/`admin1`, or structured
`coordinates` containing name/latitude/longitude/timezone, plus optional units.
Alternate cities resolve through bounded geocoding results. Ambiguous/invalid
locations return candidates/errors and never silently substitute Frisco.
Daily `day_offset` ranges from 0 (today) to 6. Unit settings are sent to Open-Meteo,
validated against returned unit labels, and represented explicitly in results.

Normalized results include current temperature, apparent temperature, humidity,
wind, condition, precipitation, daily high/low/rain probability/precipitation,
sunrise/sunset and hourly temperatures/probability/humidity/precipitation. Missing
measurements remain null. Hourly/daily values are marked forecasts; current values
are model estimates, not claimed physical observations. Unix timestamps are
converted with IANA timezone rules, preserving repeated DST hours. Daily calendar
labels preserve Open-Meteo's documented fixed-offset aggregate dates. No earlier
hours, temperatures or precipitation values are synthesized.

Current/daily/weekly freshness defaults are 600/3600/10800 seconds. A bounded
location/unit cache and per-key locks coalesce concurrent requests, sharing a
seven-day acquisition across projections. A new weekly date window or unavailable
requested daily date requires refresh. Weekly results discard past calendar days.
Source failure permits explicitly stale fallback up to `MAX_STALE` (86400 seconds),
preserving acquisition/source timestamps; a 15-second retry cooldown limits
outage bursts. Beyond the bound the tool fails honestly. There is no startup or
unrelated-chat weather fetch. Source timestamps, source age, forecast validity,
cache age and applicable freshness TTL remain distinct metadata.

The old relay's API/cache remain intact. Both consumers share pure condition and
nullable-column transformations in `packages/weather`; their temporary transport
adapters differ. Migrate the remaining dashboard/voice consumers before retiring
legacy weather. Do not maintain a second permanent keyword router.

## Home Assistant and media

The chosen integration is native REST, not HA's conversation agent or a broad MCP
natural-language command. HA credentials stay in the backend; cloud LLMs receive
only authorized normalized results. Configure `EVE_SERVER_HOME__URL`, `TOKEN`,
`ENTITIES`, `TIMEOUT` (5), `DISCOVERY_TTL` (10), and optionally
`ALLOW_INSECURE_LAN=true` for an explicitly trusted native HTTP LAN connection.
This flag does not weaken MCP TLS validation. No HA endpoint/entity is assumed.

`ENTITIES` maps exact IDs to aliases and allowed actions. Supported domains are
limited to light, switch, scene, media_player, sensor and binary_sensor. Locks,
garage/cover, alarms, scripts and administrative domains cannot be configured.
Scoped clients additionally need explicit `home_entities`; operators receive the
configured approved set. Discovery filters outputs to those identities and returns
minimal state metadata. Unique aliases resolve to exact approved IDs; ambiguous
aliases return approved candidates. It never guesses an unauthorized entity.

Tools: `home.list_entities`, `home.get_state`, `home.turn_on`, `home.turn_off`,
`home.set_level`, `home.activate_scene`, and `media.get_state`, `media.power`,
`media.play`, `media.pause`, `media.stop`, `media.set_volume`, `media.volume_up`,
`media.volume_down`, `media.select_source`, `media.send_remote_command`.

Before presenting mutation tools to a model, bounded discovery reads states and
registered services. Advertised actions require configured approvals and known
supported features/capabilities. Execution validates again using fresh state.
Light level control requires an advertised brightness-capable color mode. Media
operations check HA feature bits and registered service names. Unknown capabilities
fail closed. Source selection is restricted to the device's advertised source list.
Remote buttons use a fixed per-device mapping from HOME/BACK/UP/DOWN/LEFT/RIGHT/
SELECT/PLAY/PAUSE to administrator-approved button identifiers and an exact paired
`remote_entity`. No model-generated arbitrary service name or JSON payload is sent.

Successful service HTTP acknowledgment returns `acknowledged=true`; subsequent
state verification determines `verified` and `outcome`. Scenes, remote buttons,
stop/relative-volume actions and delayed/unavailable state may be acknowledged
without verified completion. Eve must say so. Authentication, unavailability,
unsupported capabilities and uncertain writes produce structured errors; writes
are never blindly retried. Hardware/network quality and live capability flags
remain unverified here.

Generic MCP support remains available for other approved tools. Do not configure
broad HA conversation/HassTurnOn tools as a parallel bypass around these entity
and action policies. Use a least-privilege HA account and reviewed exposure; an
Eve allowlist does not reduce the privileges of a stolen HA token itself.

## Search

`search.web` is disabled until `EVE_SERVER_SEARCH__URL` points to a fixed SearXNG
endpoint such as `https://search.example.invalid/search`. Enable JSON format in
that service's configuration separately. Optional `TOKEN` is a backend bearer
credential for an authenticated endpoint/proxy. `TIMEOUT` defaults to 8 seconds,
`MAX_RESULTS` to 5 (maximum 10), and insecure trusted-LAN HTTP requires its own
`ALLOW_INSECURE_LAN=true`. No search configuration is inferred from the homelab.

Queries are bounded to 256 characters. Responses are bounded to 256 KiB, snippets
and result counts are limited, and redirects/proxy environment forwarding are
disabled. Search results carry title, validated public HTTP(S) URL, plain-text
snippet, optional actual publication timestamp, retrieval timestamp and engine/
provider metadata. Missing/invalid publication dates remain null. Private/local/
metadata URLs, embedded credentials and unusual ports are rejected for results.
Eve never fetches result URLs or accepts arbitrary backend fetch targets. Snippets
remain untrusted tool data and cannot grant permissions or trigger actions.
Search occurs only when selected by the model, not for every factual question.

## Application state and semantic events

`GET /api/application/state` returns typed, version-1 scoped timers, pending alarms,
cached weather with current age/freshness, approved observed device state, semantic
views/layouts, recent non-sensitive tool summaries and service configuration/error
status. Device observations remain marked cached; configuration is not a live
health guarantee. Selected weather/home/view state persists, while weather HTTP
acquisition caches and HA discovery caches restart empty. Over-age weather is
omitted rather than presented as current. No conversation history or credentials
are included. Existing `/api/state` and device/audio v1 are unchanged.

`dashboard.show_view`, `dashboard.dismiss_view`, `dashboard.set_layout` accept only
supported semantic views and layouts (`default`, `compact`, `focus`). Successful
weather/timer/home/media tools deterministically update presentation without an
extra model call. Explicit view commands override automatic presentation within
that turn. Pending alarms protect the timer view, including after restart.

`GET /api/application/events?after=<sequence>&limit=<1..200>` polls a scoped durable
event log. Events include version, UUID, UTC timestamp, owner/device scope,
monotonic database sequence, resource reference and semantic payload. Types include
timer created/updated/expired/acknowledged, weather updated, home/media state changed,
dashboard view and tool execution completed. Event IDs deduplicate delivery;
consumers resume using the returned cursor. Fetch a snapshot first, then events
after its revision. Snapshot database state/revision are captured in one transaction.

`EVE_SERVER_EVENT_RETENTION` defaults to the last 10000 events. An older or
incompatible cursor returns 409 `snapshot_required`. Full historical event delivery
is not promised after retention or database replacement. Pending alarm identities
remain recoverable independently from authoritative alarm storage until acknowledged.
The tests include a simulated deduplicating alarm consumer; Pi speaker playback
and durable edge fallback are deferred. A future fallback must synchronize timer
UUID/version/deadline and alarm UUID, persist playback/ack state, and reconcile
cancel/pause/ack changes on reconnect before deciding which alarm to play.

Both routes use the existing operator/scoped backend credentials and reject
browser Origins and edge credentials. Different tokens are required for different
principals; sharing an operator token shares its private scope. Browser sessions,
event streaming and React migration remain Phase 6 work. Portable application JSON
Schema is in `packages/application/schema.json`; regenerate using
`python scripts/export_application.py`.

## Validation and Phase 5

Run the existing lint/format, full pytest suite, `pip check`, both schema exporters,
transport simulation and frontend tests/typecheck/build. CI checks both schemas.
Tests exercise real provider SDK serialization with mocked HTTP, real MCP fixtures,
timer databases/restarts/races/backup, scoped snapshots/events, simulated Feather
hardware and isolated HA/weather/search fixtures. No physical sound, Pi/Feather,
live provider, HA, weather/search endpoint, Docker/Linux or hosted-CI result is
claimed without a separate actual run.

Phase 5 should connect verified edge wake/VAD capture to the existing bounded PCM
transport; inject local server STT into the audio consumer and this same agent;
implement server-only Piper synthesis with bounded output and explicit edge
playback start/finish/cancel acknowledgments. Bind voice sessions to trusted
device/client principals, preserving permissions and cloud routing. Add mute,
echo/chime suppression, interruption and follow-up tests. Implement durable alarm
playback/dedup/reconnect reconciliation and explicitly test any offline edge
fallback before claiming it. Keep legacy voice/relay and firmware until their
remaining consumers are migrated and physical deployment is separately authorized.

Official implementation references:
[Open-Meteo forecast and timestamp semantics](https://open-meteo.com/en/docs),
[geocoding](https://open-meteo.com/en/docs/geocoding-api),
[HA REST](https://developers.home-assistant.io/docs/api/rest/),
[HA media features](https://github.com/home-assistant/core/blob/dev/homeassistant/components/media_player/const.py),
[HA remote](https://www.home-assistant.io/integrations/remote/),
[SearXNG search API](https://docs.searxng.org/dev/search_api.html).
