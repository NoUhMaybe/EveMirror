# Repository baseline — 2026-10-17

Inspected clean `main` at `91e602c7d6c03583fef04c4ef5290848bd6ec3d0`.
Development branch: `codex/distributed-foundation`. No pre-existing edits.

Paths below describe the initial checkout. The subsequent cleanup moves source
into the [current repository layout](REPOSITORY_LAYOUT.md); keep this audit as a
record of the original baseline.

## Working source to retain

- `mirror_client/listen.py`: 16 kHz openWakeWord inference, custom ONNX asset,
  acknowledgment chime, Silero VAD, bounded utterance duration, microphone selection.
- `mirror_client/runtime.py`: subprocess supervision/restart; legacy entry point.
- `eve_agent`: working Ollama HTTP chat, faster-whisper with CPU fallback,
  Piper synthesis/playback, UDP-to-WebSocket dashboard events, Open-Meteo retrieval.
- `dashboard`: React/Three.js orb, subtitles/audio reactivity, portrait-oriented
  clock and weather graphics, explicit debug controls and local weather cache.
- Feather firmware: A0 DAC capped at nominal 2 V, D12 active-high ENA,
  1.5-second ease-out fade, true off, `B<pct>` / `OK <pct>` protocol.
  Firmware acknowledgment means fade initiated, not physically complete.
- Training and speaker-audition scripts remain useful development utilities.

These are source capabilities, not fresh hardware acceptance results. The prior
handoff reports working backlight hardware. Its HDMI diagnosis and older README
ThinkPad/Kokoro/phase descriptions are historical; current hardware state is unknown.

## Verified gaps and risks

| Area | Current evidence | Migration |
|---|---|---|
| Runtime | listener, event server and voice worker share host; worker waits for localhost Ollama | separate opt-in edge and backend applications |
| Voice | WAV directory polling; recordings retained; voice turns reset context | memory-only network audio, later shared sessions |
| Providers | Ollama only; no structured function definitions/results | normalized adapters and bounded tool loop in phase 3 |
| Tools/MCP | broad substring routing; `test_server.py` is ordinary Python, not MCP; HA stub | schema/permission registry, official MCP client, entity allowlists |
| Serial | agent owns cached port; loose `OK` parsing; no reconnect | sole edge owner, exact acknowledgment validation, reconnect on next explicit command |
| Weather | unconditional daily refresh and weekly `include_week` bypass TTL; invented missing hours; UI generates weekly drift | fix fabrication/cache regression now; backend weather service in phase 4 |
| Timers | debug inputs only; no scheduler/storage | authoritative SQLite service, later edge alarm reconciliation |
| Dashboard | 2,916-line App; hardcoded socket, no reconnect/snapshot; continuous vertex/SVG work | incremental extraction; provider-independent semantic state in phase 6 |
| Security | local unauthenticated UDP/WS; model instructed to trust tool content | new isolated authenticated gateway; legacy services stay loopback only |
| Dependencies | unpinned Python requirements include NVIDIA wheels; 7,393 generated files tracked | keep legacy environment; independent lightweight locked foundation |
| Assets | custom wake model absent from Git, feature downloads lack checksums; training paths machine-specific | explicit private artifact manifest/install verification |
| Deployment | no Compose/systemd/CI/health checks; endpoints hardcoded | portable examples and health diagnostics; hardware rollout remains manual |

## Baseline validation

- All 16 application/training Python files parsed successfully on Python 3.12.10.
- Existing `eve_agent/smoke_test.py` is a live prompt bank, including network calls
  even in routing-only mode. `test_wakeword.py` uses a real microphone. Neither
  is an isolated automated test suite. No measured coverage baseline exists.
- `npm.cmd run typecheck` failed: duplicate DOM declarations in the node project,
  missing Vite environment types, condition-icon union and tile-size inference.
- `npm.cmd run build` failed under this Windows sandbox while esbuild traversed
  an inaccessible ancestor to bundle the generated Vite config. Recheck using
  the source config and a clean dependency installation.
- System `python` is 3.9.13; repository `.venv` is 3.12.10. Use the latter explicitly.
  PowerShell blocks `npm.ps1`; `npm.cmd` works without changing execution policy.

## Constraints

No Pi, Feather, microphone, speakers, mmWave sensor, Proxmox, inference endpoint
or Home Assistant service was contacted. Do not infer addresses, VM IDs, GPU
support, Pi RAM/OS, serial interfaces or model performance from historical docs.
No firmware/electrical changes are necessary for the foundation. Keep legacy
code available until replacements pass their corresponding acceptance scenarios.

See [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) for actual results and
the next concrete steps; see [ARCHITECTURE.md](ARCHITECTURE.md) for boundaries.
