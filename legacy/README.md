# Legacy voice application

This working voice stack remains available while the distributed runtime is
implemented. It still uses local recordings, Ollama, faster-whisper, Piper playback
and the loopback dashboard event relay. It is separate from `apps/edge` and
`apps/server`; see [current status](../docs/IMPLEMENTATION_STATUS.md).

Phase 5 now implements the replacement distributed voice path; see its
[setup and acceptance guide](../docs/PHASE5_VOICE.md). This directory remains for
rollback and physical voice acceptance. Its dashboard relay/event/weather modules
remain dependencies of this old supervisor/agent; the Phase 6 React application
uses the authenticated server instead. Do not delete the legacy
entry points or utilities solely because the new pipeline exists.

Run commands from the repository root using the existing voice `.venv` or an
environment installed from `legacy/client/requirements.txt` and
`legacy/agent/requirements.txt`. Keep it separate from `.venv-dev`.

```powershell
.\.venv\Scripts\python.exe legacy/client/runtime.py --help
.\.venv\Scripts\python.exe legacy/client/runtime.py
.\.venv\Scripts\python.exe legacy/agent/agent.py --text "What's the weather?" --no-tts
.\.venv\Scripts\python.exe legacy/agent/voice_loop.py --watch
```

The supervisor starts `legacy/client/listen.py`, `legacy/agent/voice_loop.py` and
`legacy/agent/dashboard_event_server.py`. Microphone recordings remain in the
ignored `legacy/client/recordings/` directory. Wake and voice models now reside
under ignored `training/wake_word/my_custom_model/` and `training/wake_word/models/`.
Existing local assets were moved with their directories.

For old dashboard rollback, restore the React build from `8299989` together with
this old stack. Current React uses the [Phase 6 paired API](../docs/PHASE6_DASHBOARD.md).
The old relay binds loopback. Piper speaker audition is a standalone utility at
`tools/audio/audition_tts_voices.py` and writes ignored `data/voice_auditions/`.
For manual serial
diagnostics use `python tools/hardware/feather_backlight.py --help`.

Only one runtime may own the Feather port. Stop legacy controllers before starting
the new edge hardware owner. The archived [design notes](../docs/archive/LEGACY_STACK.md)
and [HDMI handoff](../docs/archive/HDMI_DEBUGGING.md) retain their historical paths.
