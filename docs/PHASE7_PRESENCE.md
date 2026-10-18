# Phase 7 local presence and brightness policy

Software and simulated acceptance are separate from physical acceptance. This
phase changes no firmware, wiring, production unit, display output or deployed
service. The previous cancellation repair at `3538e82` is retained.

## Supported sensors and unresolved selection

`PresenceSensor` in `apps/edge/presence/sensors.py` defines asynchronous initialize,
typed read and close operations. `PresenceReading` contains PRESENT, ABSENT or
UNKNOWN and healthy, timeout, unavailable, malformed or disabled health. A driver
must honor cancellation; the supervisor bounds initialization/read time, closes
failed sources and retries initialization after the configured reconnect interval.
Unhealthy observations cannot claim presence or absence. A bounded latest-value
queue carries diagnostics; raw radar measurements are neither uploaded nor stored.

Only `none` (unavailable) and explicitly `simulated` drivers ship. **No physical
sensor protocol is supported yet.** Simulation health/targets are visibly labeled.
The interface can accept a future USB serial/UART driver; sensor ownership is
separate from Feather ownership and must reject the same resolved device path.
No driver may enumerate/open Feather ports or write configuration to them.

The HLK-LD2410 family is a practical candidate because it has vendor UART protocol
documentation, including separate variants in the [vendor product catalog](https://www.hlktech.com/en/Goods-238.html).
This is an evaluation, not a purchase or installation recommendation. Model,
firmware, frame format, baud rate, adapter and supply/logic levels remain unknown.
LD2410/B/C/S/AA reports must not be treated as interchangeable. A real parser needs
an exact independently reviewed vendor specification, captured frame fixtures,
length/framing/checksum rules, fragmented/malformed/stale-frame tests and an
approved device path before integration. No speculative UART parser was added.

Pi GPIO is 3.3 V logic, not 5 V tolerant. Establish actual sensor supply voltage,
logic levels, current and level shifting before wiring; a sensor supply rating
does not establish UART voltage. Confirm stable USB paths, exclusive permissions,
UART framing and whether opening the adapter toggles reset lines. Radar placement
must account for mirror materials, walls, reflections, movement outside the room,
interference and seated/stationary occupants. Physical installation is pending.

## State and time

`PresenceMachine` is deterministic. Separate present/absent confirmation requires
continuous readings of that candidate state. UNKNOWN immediately breaks both
confirmation histories and clears the absence deadline. Confirmed absence starts
the additional absence timeout; the minimum awake interval must also finish before
sleep. A wake cooldown bounds subsequent presence wakes. An opposite unconfirmed
candidate retains the last confirmed state until debounce completes.

All durations use monotonic time. Only the night schedule uses timezone-aware
wall time with an IANA zone; wraparound intervals and repeated DST hours are tested.
An equal start/end is rejected. Night brightness caps preferred brightness while
the display is otherwise awake. Confirmed absence still sleeps at night.

UNKNOWN defaults to `awake`: wake/retain preferred brightness, including a sensor
failure while asleep or immediately after reboot. `hold` retains the selected
target, including zero, until confirmed presence or protected/manual activity.
This optional policy can leave the display dark after a sensor failure. Neither
policy converts unknown input into absence. Healthy input must reconfirm after a
fault/reconnect. Initial state is UNKNOWN; no boot-time absence is invented.

## Arbitration and acknowledgment

Every runtime network command and local automatic target goes through
`DisplayController`, the existing `CommandProcessor` SQLite journal and the single
`FeatherService`. All physical calls remain serialized. Decisions during the
firmware's existing 1.5-second eased fade can select a new target after its ACK;
the firmware owns the fade. There is no guessed fade-completion event.

Precedence is:

1. Validated 0–100% range and hardware availability/uncertainty latch.
2. Explicit, time-bounded manual override, including off.
3. Voice, playback, undismissed valid cached alarms and the post-activity grace.
4. Confirmed presence/absence and conservative unknown policy.
5. Timezone-aware night cap.
6. Preferred/default brightness.

**Manual off wins over an active alarm's backlight protection** until expiry or
explicit release. Audio/alarm receipts are unaffected. This is a deliberate user
override; neither stale presence nor activity immediately reverses it. A new
explicit manual wake supersedes it. A wake word restores a presence-slept display
locally, subject to this manual override and a hardware uncertainty latch.

Nonzero `set_brightness` updates the preferred value and starts a manual override;
zero starts an override without losing the preference. `set_display_mode: awake`
restores preferred brightness, sleep selects zero. Automatic sleep never replaces
the preference: 65 → 0 → 65 is preserved. LLM brightness uses the same gateway
command and receives no alternative hardware path.

Desired target, preferred setting, manual override, night target and last hardware
ACK are separate. `display: awake|asleep` describes the selected backlight target,
not observed physical state. `actual_percent` and `fade_complete` remain null.
HDMI stays active: there are no compositor, hotplug, DPMS or HDMI output commands.

Unchanged reads/targets cause no new serial calls. Before a write, uncertainty is
persisted in `display_preferences` inside the existing command database, with no
new database or event ledger. An invalid/missing ACK or interrupted write latches
automation off, including after restart. Only a fresh authorized manual request
can resolve it. Reusing an old ID returns its receipt and cannot renew an override,
reapply old settings or initiate a second fade. Never delete the journal to retry.

Saved settings are authoritative after restart; environment settings seed a new
journal. Saved overrides restore only their bounded remaining UTC expiry, then use
monotonic time. Sane UTC/NTP is required across restarts. Corrupt saved settings
fail startup rather than silently enabling an alternative policy. Policy reads do
not measure hardware or automatically replay an indeterminate request.

## Voice, alarms and offline behavior

Wake, listening, upload, STT, thinking, tools, synthesis, delivery, speaking and
follow-up protect the display. Cancellation retires turn identity before cleanup,
as in Phase 6; display integration does not change event acceptance or source
suppression. Activity notifications record protection without awaiting serial
locks. A separate policy worker handles hardware, so slow ACKs cannot block
microphone frames, playback or heartbeats. Sensor reads have a separate worker.

Playback protection is independent of voice state. Cached due alarms remain
protected after their one audio attempt until dismissal, synchronization removes
them, or the existing offline lease expires. Ordinary cancellation, mute and
sensor failure preserve alarms. This adds no playback retry or alarm journal.
After activity ends, the configured grace keeps important results visible before
presence policy resumes. Manual policy controls supply authorized manual activity.

Sensor/policy workers remain local when backend, network, LLM, Home Assistant or
Chromium is unavailable. Wake processing keeps running while the backlight is off.
This feature uploads no continuous audio, changes no cloud selection and does not
alter half-duplex echo suppression, mute or hardware receipts.
Connection loss still cancels ordinary network voice turns. A failed reconnect
without an established socket does not repeat that cleanup or cancel a new local
wake chime; this ordering is covered by a deterministic event-controlled test.

## Configuration and browser boundary

See `deploy/edge/edge.env.example`. Defaults disable automation. Set
`EVE_EDGE_PRESENCE` to a JSON object with strict numbers/booleans; defaults include
65% preferred, 1 s present/5 s absent confirmation, 120 s absence delay, 15 s minimum
awake and activity grace, 2 s wake cooldown and 300 s manual override. Poll/read/
reconnect defaults are 0.2/1/5 seconds. `presence_driver=none` reports unavailable,
so enabling automation alone does not fabricate a sensor.

`edge.presence_state` uses the existing authenticated transport and `presence`
capability. BrowserFrame exposes typed optional `presence`; minimal semantic
notifications use the existing scoped event store. Identical reports are deduped.
The dashboard shows sensor health, simulation, target/ACK, override and protection,
with subtle sleep/wake status and no routine popups. Disconnected status is unknown.

`POST /api/browser/display` requires paired cookie, exact Origin/CSRF, the explicit
per-device `display_control` grant, backend mutation opt-in and a capable connected
edge. Its finite payload is request UUID plus settings, override_percent or
release_override. Browser request IDs are session-namespaced before existing edge
journaling. No serial path, shell, GPIO, arbitrary device or provider settings can
be supplied. Settings apply only after an authenticated command; ACKs still do not
verify physical output. Grant changes invalidate old browser sessions.

## Reproducible software validation

```sh
python scripts/simulate_presence.py
python scripts/simulate_voice.py
python scripts/simulate.py
python -m pytest -q
```

Fake clocks cover debounce, noise, absent/unknown, minimum awake/cooldown, schedules,
preferences, override expiry/reboot, concurrent/uncertain writes and no replay.
Real loopback tests cover typed status/events, auth/CSRF, browser command receipts,
offline local wake and cached alarms. Browser tests exercise configured simulated
sleep/wake and manual off across three viewport sizes. These do not establish real
radar accuracy, acoustic behavior, DAC voltage, HDMI stability or Pi performance.
