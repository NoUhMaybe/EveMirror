# Phase 7 physical acceptance and benchmarks

All physical stages below are **pending**. Repository simulations and hosted
software CI cannot mark them passed. Record operator, timestamp, app SHA, firmware
hashes, model hashes, OS/kernel, topology, device identifiers, observations and
failure/rollback results in a private acceptance record. Never publish credentials,
raw recordings, serial numbers or transcripts in CI artifacts.

## Stage A — read-only inventory

These commands inspect; they do not install, flash, capture audio or alter services:

```sh
uname -a
cat /etc/os-release
getconf GNU_LIBC_VERSION
free -h
df -h
lsusb
ls -l /dev/serial/by-id/
cat /proc/asound/cards
ls -l /sys/class/drm/
systemctl status evemirror-edge.service --no-pager
systemctl --user status evemirror-kiosk.service --no-pager
python scripts/preflight.py --role edge
# With reviewed private environment loaded:
python scripts/preflight.py --role edge --validate-config
```

Record actual Pi model/RAM/aarch64 OS and Python, mic/speaker identities and rates,
Feather data interface and current process owner. Read the actual Wayland output
status using that compositor's documented query command; do not guess compositor
names or run a mode-setting command. Confirm HDMI remains in its known-good mode,
actual portrait resolution and orientation. Query existing backend TLS health only
at the operator-supplied endpoint. Do not scan the network or invent SSH addresses.
Review current services and boot/profile backups before considering Stage C.

## Stage B — isolated backend and simulated edge

Use a disposable Docker test host/CI as described in
[deployment plan](PHASE7_DEPLOYMENT_PLAN.md), never an existing production instance.
Run all Python/frontend tests and the transport, voice and presence simulations.
Pair a test browser, verify cookies/Origin/CSRF and revoked grants, simulate
presence/unknown/manual off, disconnect backend and confirm local policy continues.
After separate model-host authorization, check a configured real model response
with harmless text before any device mutation. Record actual availability and
latency; mocked providers prove routing only.

## Stage C — authorized physical backlight and audio

Obtain approval naming the Pi, current owner, exact commands/targets, audio levels,
test duration and rollback. Preserve firmware and disable the old owner only in
that window. Start exactly one replacement owner. Use fresh authenticated operator
command UUIDs through the existing gateway; do not open a second serial diagnostic
client while the edge owns Feather.

1. Request a reviewed midrange brightness. Confirm the exact ACK, visible eased
   fade, correct scaling and unchanged HDMI image. Independently measure using the
   established safe method if voltage acceptance is authorized; software ACK alone
   proves no DAC voltage or physical illumination.
2. Request zero and confirm ENA true off after the fade, while HDMI and compositor
   output stay active. Explicit wake must restore the saved preferred value, e.g.
   65%, rather than overwrite it with 100%. Test intermediate targets and changes
   during a fade without altering the existing ~0–2 V scale, pins or polarity.
3. Review one missing/invalid ACK, unplug/reconnect and service restart. Confirm
   uncertain state inhibits automatic writes and duplicate IDs cause no second
   action. Inspect before authorizing a fresh request; never blindly retry.
4. Test actual mic/speaker enumeration, rates, gain/volume, local wake and chime,
   mute and echo suppression. Begin at approved low volume. Do not record or upload
   continuous audio. Verify capture runs while backlight is off and wakes locally
   during a backend outage. No AEC or voice barge-in capability is claimed.

## Stage D — real voice and safe tools

Validate trusted wake/VAD/STT/TTS models first. Start with a harmless time question,
then an explicitly approved timer. Verify actual utterance boundaries, transcription,
model response, speech, subtitles, follow-up, cancellation and a fresh wake after
cancel. Delayed status/playback must not resurrect the canceled turn. Check mute
and alarm behavior independently. HA actions require separate entity/action
approval; do not test with locks, security systems, power circuits or guessed IDs.
Cloud text routing requires explicit configuration/consent; local audio stays local.

## Stage E — chosen and installed presence sensor

This stage requires approved sensor selection, electrical design, wiring/install
and an exact implemented/tested driver. Current software supports simulation only.

Record model/firmware, supply/logic levels and adapter. Pi GPIO is 3.3 V logic.
Verify stable separate sensor/Feather paths and permissions; no two owners and no
sensor discovery of Feather. Test approaching, leaving, stationary/seated person,
edge of field, reflection/wall penetration and movement outside the intended room.
Tune confirmation and absence durations from measurements, not simulated accuracy.

Exercise PRESENT → ABSENT → PRESENT → ABSENT → UNKNOWN → PRESENT, false detections,
timeouts, malformed frames, disconnect/reconnect while awake/off and during an
alarm, backend/network outage, reboot, minimum awake/wake cooldown, night timezone
and DST, preferred restoration, manual override/release/expiry and active voice/
alarm protection. Manual off intentionally wins for its duration; audible alarms
continue. Test conservative awake versus explicitly selected hold-on-unknown.
Confirm bounded serial writes and no physical state claims beyond independent
observations. Never accept an undocumented sensor protocol based on similar names.

## Stage F — approved eight-hour soak and performance

This later stage needs separate authorization for real model/audio/display/sensor
operation and service restarts. It has **not** been run. Include quiet/occupied
periods, speech, alarms, outage/reconnect and thermal observation. Require no
unexpected wake/sleep loops, replay, memory growth, stuck capture, lost alarms or
unrecoverable browser/edge state. Define measurable thresholds before running;
derive them from the actual device and deployment rather than inventing results.

For already-running approved processes, the following utility only reads Linux
process and thermal counters and emits JSON Lines to stdout:

```sh
python scripts/benchmark_host.py --pid <edge-pid> --pid <chromium-browser-pid> --seconds 60 > <private-results.jsonl>
# Later approved soak, up to eight hours:
python scripts/benchmark_host.py --pid <edge-pid> --pid <chromium-browser-pid> --seconds 28800 > <private-soak.jsonl>
```

Sample all Chromium child PIDs as well as its browser process to calculate total
RSS. CPU percent is delta(user+system ticks)/`getconf CLK_TCK`/delta monotonic seconds
×100 (one CPU basis). Sample actual edge CPU/RSS, temperatures and `vcgencmd
get_throttled` only if that read-only tool is present. Record reconnect counts and
command receipts without secret bodies. Missing processes/counters are reported
as unavailable, not zero. The utility does not start audio, GPU work or models.

Use existing edge/voice diagnostics and correlated request/session UUIDs to record:

| Measure | Procedure/evidence |
| --- | --- |
| Wake false positives/latency | Count triggers over a defined quiet interval; timestamp approved wake stimulus and local WAKE_DETECTED. No accuracy claim from fixtures. |
| VAD/capture | Timestamp speech start/end, declared capture metrics and actual frame counts; check truncation/noise/rates. |
| Upload | Correlate AudioBegin/AudioReceived timestamps and utterance byte count. |
| STT / LLM / tools / TTS | Record existing per-stage voice metrics and correlated backend diagnostic timings with selected models, provider and tool. |
| Playback startup | Delivery/first driver-start acknowledgment; independently check sound. Started/drained does not measure acoustic output. |
| End-to-end | Human stimulus/speech end to audible response and visible state, with clock synchronization and repeated p50/p95 samples. |
| Rendering | Dashboard settings shows browser FPS; use Chromium Performance/Memory profiling at the actual portrait resolution. |
| Resources/recovery | JSONL host samples, thermal/throttle output, network conditions, restart/reconnect and replay receipts. |

Compare low/balanced/high graphics at the actual portrait resolution with identical
scene, duration and workloads; record active/idle FPS, renderer/browser RSS and
edge/Chromium CPU. Include reduced motion, fallback graphics and background-tab
behavior. Choose a default only from real-device measurements. Desktop software
rendering screenshots establish layout/behavior, not Pi FPS, GPU acceleration or
thermal headroom. Keep raw private traces local and publish only redacted aggregates.

Stop and use the reviewed rollback if capture, display, alarms, permissions or
hardware safety differs from expectations. Hardware acceptance remains incomplete
until the operator records every relevant stage and explicitly accepts limitations.
