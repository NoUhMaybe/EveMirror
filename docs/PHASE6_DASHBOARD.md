# Phase 6: paired production dashboard

The React application now uses Eve Server's browser API. It has no connection to
the legacy `:8765` WebSocket. Development started at `8299989` on
`codex/distributed-foundation`, preserving the CI recovery fix atop Phase 5.
No Pi, physical device, live integration or production infrastructure was changed.

## Browser identity and pairing

Browser access defaults to disabled. Configure `BROWSER__ENABLED`, exact
`BROWSER__ORIGINS` and explicit `BROWSER__DEVICES` under the `EVE_SERVER_` prefix.
Origins require HTTPS; HTTP is permitted only with `ALLOW_HTTP_LOOPBACK=true`
and a literal loopback/localhost origin for development. Keep production on TLS.
The edge token map must already contain each assigned mirror. A browser grant
does not copy operator, edge, agent-client or provider credentials.

Each browser is delegated the existing `voice:<device>` principal for exactly
one mirror. It sees that mirror's voice-owned timers, alarms, presentation and
approved home entities. Timers created by unrelated text principals stay private.
Optional `captions`, `timers`, `home_control`, `voice_control` and `debug` grants
default to false. Home IDs must also be approved in backend configuration.
Timer/home mutations additionally require the existing global agent mutation flag.
Finite view navigation is independently permitted: it validates the existing
dashboard tool schema and calls the existing presentation service without granting
LLM hardware or home mutation rights. No arbitrary tool names are accepted.

1. Open the HTTPS dashboard and choose **Pair this display**.
2. Verify the displayed code and mirror identity in person. A LAN source address
   alone grants nothing. Codes expire after five minutes by default and are bound
   to the initiating browser's HttpOnly pairing cookie.
3. In a trusted administrator terminal with `EVE_SERVER_OPERATOR_TOKEN` already set:

   ```sh
   python scripts/pair_browser.py --url https://mirror.example.invalid approve ABCDE234 --device mirror-1
   python scripts/pair_browser.py --url https://mirror.example.invalid list
   python scripts/pair_browser.py --url https://mirror.example.invalid revoke SESSION_UUID
   ```

4. The initiating browser claims a single-use approval and receives its own opaque
   256-bit credential. Keep Chromium's private profile across reboots.

Production cookies use `__Host-eve_browser_session`, Secure, HttpOnly, Path=/ and
SameSite=Strict. Only SHA-256 credential/code hashes are stored in the existing
SQLite database (migration 3); tokens never enter responses, URLs or JavaScript.
The JSON session includes an HMAC CSRF proof, required as `X-Eve-CSRF` on every
authenticated POST. Renewal rotates the cookie and CSRF proof, invalidating the
old credential. Default session lifetime is 30 days; the client renews before
expiry, with a shorter renewal window for configured short sessions. Logout or
operator revocation invalidates it. Grant changes require pairing again, including
after a server restart. Expired/revoked sessions are pruned at pairing; capacity
is bounded (128 sessions, 100 pending approvals by default). Keep the API behind
your normal request limits; this does not implement a distributed abuse limiter.

Browser APIs validate the exact Host, scheme and Origin, reject cross-site/same-site
Fetch Metadata requests and reject Authorization headers. Mutations require Origin
as well as CSRF. No wildcard CORS or query-string credentials are used. Operator
approval/list/revoke is a separate bearer-only boundary and rejects browser Origins.
API responses are no-store. Static hosting sets CSP with no runtime eval, frame
embedding denied, no referrer and microphone/camera/geolocation disabled. The
browser never captures audio. Local display preferences are the only localStorage
value; captions, cookies, timers and backend state are not cached there.

## State transport and reconciliation

| Route | Purpose |
|---|---|
| POST /api/browser/pairings; GET /api/browser/pairings | Start approval / poll and claim |
| GET /api/browser/session | Recover existing session after browser restart |
| POST /api/browser/session/renew; /session/logout | Rotate / revoke cookie |
| GET /api/browser/state | Full authorized projection and bounded events |
| POST /api/browser/actions | Finite schema-checked weather, timer, view, home/media tools |
| POST /api/browser/voice/mute; /voice/cancel | Scoped edge controls |
| /api/operator/browser/pairings/approve; /sessions; /sessions/{id}/revoke | Administrator boundary |

The client polls every 500 ms after the previous request finishes. Failures use
exponential backoff with jitter, capped at 30 seconds; requests have a 12-second
deadline and abort on teardown. Mutations are never automatically retried.
Unknown command outcomes are labeled and require checking real state.

`BrowserFrame` v1 is generated from Python into
`packages/application/browser.schema.json`, TypeScript declarations and a CSP-safe
precompiled runtime validator. AJV runs at build time. Invalid versions, malformed
state and data outside the assigned mirror/entity/session scope are rejected.
Regenerate with `python scripts/export_application.py` then `npm run contracts`;
CI checks both generated outputs, including the standalone validator.

After initial synchronization, send `after`, `voice_after` and `epoch`. Durable
notifications reuse the Phase 4 event store, 200 per page. Volatile captions use
the existing Phase 5 bounded TTL stream; they are never made durable. The server
reads the event page **before** taking a full transactional application snapshot.
Events notify; they never patch that newer snapshot. A mutation between those two
reads is already reflected by the snapshot and remains eligible for the next
event page because the page cursor is retained. On first connection, invalid or
retention-expired cursors, or a new process epoch, return `reset=true` with a full
snapshot and its revision. The browser deduplicates bounded IDs and orders events;
older projections cannot roll state backward. Volatile resync/expiry clears old
captions. Polling avoids a separate subscribe/snapshot handoff race.

Ambient weather refreshes through the existing WeatherService TTL cache, never a
browser-to-provider call. Home discovery reuses HomeService; refreshes are bounded
to ten seconds per mirror and command completion fetches state evidence. Forecasts
beyond `weather.max_stale` disappear. Backend restart rotates the epoch, while
cookies and authoritative timers remain in SQLite. A disconnected browser keeps
its local clock and labeled last-known forecast, disables mutations and clears
captions. Reconnect restores current alarms without replaying browser audio.

## Frontend ownership and presentation

| Module | Responsibility |
|---|---|
| app/AppProvider | Single transport/store, pairing, bounded pending actions and notices |
| transport | Same-origin cookies/CSRF, deadlines, reconnect, contract/scope validation |
| state/dashboard | Voice reducer, cursors, priorities, UTC countdown math |
| state/forecast | Real hourly segments, nullable gaps, forecast choice and formatting |
| components | Clock/status, subtitles, layout, settings, errors, static/WebGL orb boundary |
| widgets | Lazy current/daily/weekly weather, timers/alarms, authorized home/media |
| animations/OrbGL | Reused GPU geometry/materials and shader deformation |
| styles | Central black/white/cyan/violet tokens and constrained responsive layout |

The default display stays quiet: large clock/date, orb, ambient weather and status.
An alarm takes contextual priority until acknowledged. Voice feedback remains
visible alongside the requested semantic view. Ordinary tool results/presentation
follow, then ambient content. Weather refreshes cannot dismiss an alarm. The
assistant requests finite views, never coordinates. Automatic successful home/media
action confirmations expire after 12 seconds using presentation metadata in the
existing resource store; a full snapshot resolves the expired view back to default.
Explicit views clear that expiry and persist. This does not create another timer
service or change alarm priority. Portrait layouts stack the
assistant and context; desktop places forecast and compact countdown side by side.
Lists paginate; long subtitles scroll internally to the active word. Settings use
a separate overlay; only the debug grant exposes event metadata, without captions.
Provider/model and assigned mirror are read-only. Preview real weather/timers with
the view navigation; synthetic development state belongs in the isolated fixture.

Voice labels cover wake, listening, upload, transcription, thinking, tool execution,
synthesis, delivery, actual speaking, follow-up, idle, mute, offline and error.
Speaking begins with actual software playback receipts. Sample positions drive
subtitle highlighting and orb activity; input RMS drives listening. Word progress
is proportional to sample progress, not phoneme/word alignment or an acoustic
loudness measurement. It does not prove sound came from a physical speaker.
Completion, failure, cancellation, terminal edge state, expiry and loss of
authorization clear speaking/captions. Stop uses a correlated existing Cancel
message; it also closes follow-up eligibility and preserves independent alarms.
Mute waits for an acknowledgment from the current connection/request after edge
persistence. It suppresses capture processing, not the OS microphone hardware.
Mute requires the new negotiated `voice_control` capability; older edges remain
connected and return unavailable for this action. Upgrade the backend before a
new edge that advertises this additive capability; old strict servers reject
unknown capabilities.

Weather uses real backend current/daily/hourly/weekly measurements and source time,
timezone, units and stale flags. Missing temperatures leave chart gaps. Timer
countdowns use server deadlines and clock offset; reaching zero locally says
"Waiting for server confirmation". Expiration, software audio delivery and user
acknowledgment are separate. Browser refresh never creates or plays an alarm.
Home/media controls require current observations, browser/global permissions and
actual discovered/configured capabilities. A service acknowledgment does not
become an optimistic physical-state claim. Unsupported power directions, remote
commands and media controls are omitted. Unavailable/unknown state disables actions.

## Graphics and measurements

The old application updated geometry on the CPU. The new renderer deforms reused
geometry in shaders, with no post-processing stack or React updates per frame.
Three.js remains a lazy separate chunk; React Three Fiber was removed because the
renderer no longer uses it. Nonessential widgets are lazy chunks too. System or
local reduced motion uses a static CSS orb without loading Three.js; WebGL failure
or context loss also falls back. Hidden pages cancel rendering, and teardown
disposes geometry/materials/renderer, listeners, timers and animation frames.

| Quality | Geometry subdivision | DPR cap | Active render cap |
|---|---|---|---|
| Low | 2 | 1 | 15 fps |
| Balanced | 3 | 1.25 | 30 fps |
| High | 4 | 1.5 | 45 fps |

Idle rendering is capped at 12 fps. The settings render-rate value counts actual
renders over two seconds; it is a diagnostic, not a guaranteed frame rate. There
is no unmeasured automatic quality governor. Choose low if the deployment needs it.

The Phase 5 baseline was 1025.71 kB JS / 283.72 kB gzip. The Phase 6 build is about
778 kB total JS / 196 kB gzip across lazy chunks, with a 292 kB / 72 kB gzip entry
and a 470 kB / 117 kB gzip Three.js chunk. These are build measurements on Windows,
not Pi startup, memory, CPU or FPS measurements. No real Pi benchmark was run.

For a later authorized Pi acceptance run, record OS/kernel/Chromium versions,
verified active resolution/rotation, renderer from `chrome://gpu`, quality/DPR and
edge model versions. Use Chromium Task Manager/performance tools for browser RSS,
CPU, heap and frame times, and `pidstat`/`ps` for edge RSS/CPU. Use available platform
GPU counters only if supported, otherwise record GPU utilization as unavailable.
Measure cold/warm startup and server-event timestamp to displayed-frame latency
(synchronized clocks), idle/listening/speaking/chart/alarm FPS for 60 seconds each,
then an eight-hour soak including reload, disconnect, renewal and alarm recovery.
Record median/p95, maxima and dropped frames with edge capture enabled. Repeat low
and balanced quality, reduced motion, display sleep/wake and WebGL failure. Compare
capture continuity and memory growth. Desktop software-GPU tests prove no Pi target.

## Development and browser tests

Use the pinned Python dev environment and Node 24.4+. In `apps/dashboard`:

```sh
npm ci
npm run contracts:check
npm run format:check
npm test
npm run typecheck
npm run build
npx playwright install chromium
npm run test:browser
```

Set `EVE_TEST_PYTHON` to the absolute dev Python executable. The test runner uses
`tests/browser_fixture_app.py`, requires its explicit simulation flag, binds only
loopback, creates temporary SQLite/edge journals and serves the real production
build. Mock STT/TTS/provider/HA/weather and simulated hardware feed the actual
authenticated edge, agent tools, timers and browser API. No models or live devices
are contacted. Startup/shutdown belongs to Playwright; fixture controls never ship
in production packages. Screenshots/traces contain fixture data and are ignored.

Three scenarios run at 1080x1920, 720x1280 and 1440x900: complete voice weekly
forecast plus Tea timer, follow-up/reload/offline expiration/reconnect/alarm/dismiss;
long playback with actual fixture sample progress, cancellation, two timers with
pause/resume, connected expiration and admin revocation;
and current/daily weather, scoped home/media, confirmed mute, settings and reduced
motion. The voice scenario also deliberately loses WebGL context and verifies
that the static fallback preserves the interface. Test-only GPU rasterization is
disabled to avoid missing glyphs in Windows software-renderer captures. Geometry assertions check viewport bounds, primary-region overlap, final
forecast row and compact timer visibility. Screenshots capture settled finite
transitions; tests synchronize to states/events, not arbitrary waits. Inspect
artifacts when changing layout. They are review captures, not cross-platform
pixel-perfect golden baselines. Hardware-native resolution remains unverified.

For hot reload, run Vite on its fixed loopback port and configure the backend's
browser origin to exactly `http://127.0.0.1:5173`, explicitly allow loopback HTTP,
and set `EVE_DASHBOARD_DEV_BACKEND` if needed. The proxy preserves Host/Origin.
Use the trusted CLI directly against the private backend for approval. Never add
a privileged VITE token. `vite preview` alone does not provide the backend API;
prefer static serving for production-like integration.

## Deployment, kiosk and rollback

Examples under `deploy/dashboard/` are preparation only. Build the frontend and
set `EVE_SERVER_BROWSER__STATIC_ROOT` to its absolute dist directory, or build the
multi-stage server Dockerfile. The image includes reviewed static assets but
browser access remains disabled until configured. Keep backend port private,
one server worker, persistent SQLite and existing model mounts. Docker/container
startup has not been executed in this Windows environment.

The Caddy example terminates TLS on the reviewed hostname and preserves Host.
Set DNS/TLS first; use no certificate bypass. Trust forwarded headers only from
the actual reverse-proxy IP (`FORWARDED_ALLOW_IPS`, compose's
`EVE_TRUSTED_PROXY_IPS`), never `*`. Browser HTTPS scheme validation fails closed
if proxy trust is wrong. Do not expose a bare backend port to the LAN. Keep edge
WebSocket forwarding and existing authentication intact.

For Raspberry Pi OS, install the example `eve-kiosk` as `~/.local/bin/eve-kiosk`
with executable mode, the user unit under `~/.config/systemd/user/`, and a private
`~/.config/eve/kiosk.env`. Set the reviewed HTTPS origin and Chromium binary.
Enable the unit only during authorized deployment with a working graphical user
session and imported compositor environment. It restarts Chromium and preserves
the private cookie profile; one process owns that profile. Normal GPU acceleration
is retained; do not copy software-test or sandbox-disabling flags to production.
Review Wayland/HDMI portrait rotation on the physical mirror separately; these
examples change no boot, compositor, DPMS, wake/sleep or display rotation settings.

If pairing fails, check exact Origin/Host/forwarded scheme and code expiry. A 401
requires pairing again; a 403 may be origin, CSRF or grant policy. After profile
loss revoke its old session and pair a new one. After a network outage retain the
profile and wait for bounded reconnect. If graphics fail, use reduced motion/low
quality and inspect `chrome://gpu` in an authorized maintenance session. Avoid
production caption/cookie traces and uncontrolled request-header logging.

Before updating, back up SQLite through the existing backup procedure and retain
the server image, frontend build and private Chromium profile. Update backend and
edge together for the new mute control, then validate TLS, cookies, complete voice
turn, reboot/reconnect and disconnected timer expiry. To roll back, stop the new
kiosk/runtime, restore the prior image/static build and compatible database backup
as a unit. Older migrations reject a newer database version; do not hand-edit it.
Browser display rollback does not authorize replaying commands or restoring stale
physical state. Keep Feather ownership exclusive throughout.

## Legacy disposition

No legacy runtime files were deleted in Phase 6. None are imported or launched by
the new dashboard, server or edge. Their remaining callers form the hardware
rollback stack; keep that set together until physical acceptance is complete.

| Files under legacy/ | Disposition / remaining caller |
|---|---|
| client/runtime.py, client/listen.py, client/requirements.txt | Required for old supervisor/wake capture rollback; supervisor still launches relay |
| agent/agent.py, voice_loop.py, transcribe.py, tts_local.py, requirements.txt | Required for old inference/audio rollback and its explicit environment |
| agent/tooling.py, backlight_control.py | Required by agent and relay; tooling still calls the hardware bridge |
| agent/dashboard_events.py | Required by agent.py and voice_loop.py imports |
| agent/dashboard_event_server.py | Unused by new dashboard; still launched/probed by old supervisor, required for coherent old-dashboard rollback |
| agent/smoke_test.py | Standalone old-agent diagnostic; safe to archive with rollback set, not a new-runtime dependency |
| agent/audition_tts_voices.py | Standalone utility moved to tools/audio/ in this phase; no runtime caller |
| README.md | Retain migration/rollback instructions |

Safe to delete now: no remaining tracked legacy dependency. The old React source
and styles were replaced; their rollback version remains in Git at `8299989`.
After physical acceptance and an explicit end to old-stack rollback, archive the
above runtime set together, remove old supervisor launches/imports/probes, then
delete the relay/events/tooling with their callers. Keep `tools/hardware/` and
firmware sources independently. Do not infer deletion safety from the new browser
passing simulated tests.
