# Legacy voice application

This working voice stack remains available while the distributed runtime is
implemented. It still uses local recordings, Ollama, faster-whisper, Piper playback
and the loopback dashboard event relay. It is separate from `apps/edge` and
`apps/server`; see [current status](../docs/IMPLEMENTATION_STATUS.md).

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

For the browser, run `npm.cmd run dev` from `apps/dashboard/`. The old relay binds
loopback; remote browser/gateway migration is still pending. For manual serial
diagnostics use `python tools/hardware/feather_backlight.py --help`.

Only one runtime may own the Feather port. Stop legacy controllers before starting
the new edge hardware owner. The archived [design notes](../docs/archive/LEGACY_STACK.md)
and [HDMI handoff](../docs/archive/HDMI_DEBUGGING.md) retain their historical paths.
