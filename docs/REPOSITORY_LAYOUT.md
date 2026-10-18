# Repository layout

Application code belongs in `apps/`, shared wire contracts in `packages/`, physical
firmware in `firmware/`, training tools in `training/`, and standalone diagnostics
in `tools/`. The earlier voice stack stays under `legacy/` until its replacements
are validated. No firmware logic or electrical parameters were changed.

Backend services live in `apps/server/services/` and register tools through
`apps/server/tools/services.py`. `packages/protocol/` owns the device/audio schema;
`packages/application/` contains the separate generated semantic state/event
schema; `packages/weather/` shares pure normalization with legacy weather.
Database backup and both schema exporters belong in `scripts/`. Runtime SQLite
files, WAL/SHM companions and local verification environments stay ignored.

| Previous path | Current path |
|---|---|
| `dashboard/` | `apps/dashboard/` |
| `eve_agent/` | `legacy/agent/` |
| `mirror_client/` | `legacy/client/` |
| `wake_word_training/` | `training/wake_word/` |
| `backlight Control/feather/` | `firmware/feather_m4/` |
| `backlight Control/pi/feather_backlight.py` | `tools/hardware/feather_backlight.py` |
| `backlight Control/README.md` | `firmware/feather_m4/README.md` |
| root `README` | `docs/archive/LEGACY_STACK.md` |
| root `HANDOFF.md` | `docs/archive/HDMI_DEBUGGING.md` |

Use [README.md](../README.md) for current startup and [legacy/README.md](../legacy/README.md)
for the retained voice pipeline. Update shell shortcuts, IDE run configurations and
bookmarks that still use the old paths. Historical documents and the baseline audit
deliberately retain old paths; they are labeled as archives.

Removed confirmed leftovers: `.gitkeep` files in populated directories, the unused
non-MCP `mcp_servers/test_server.py` scaffold, the generated machine-specific
`my_model.yaml`, old compiled Vite configuration and hardware bytecode caches.
The unused `@react-three/drei` dependency was removed from the dashboard manifest
and lockfile. Working voice, audition, smoke-test and training tools remain.

Local models, datasets, recordings, private environment files and dependency
directories were preserved during the moves. They stay ignored. Root virtual
environments were retained. Like other Python virtual environments, a relocated
`training/wake_word/piper_venv` may need recreation before reusing its console
scripts; the training source does not depend on that environment path.

The training tool defaults to its own directory. Set `EVE_TRAINING_WORK_DIR` to
reuse an external dataset workspace and `EVE_WAKE_MODEL_DIR` for an explicit model
export directory. The clip generator is resolved beside the script, independently
of the data workspace. Training was not launched during cleanup.

`.gitignore` excludes dependencies/builds, Python/Node/test caches, private env
files/keys, runtime databases/audio, local training assets and OS/editor leftovers.
Dependency locks, source configs, protocol schemas and `*.env.example` templates
remain versioned. The backend Docker context excludes the frontend, legacy stack,
firmware and training data. Python package discovery excludes the React app.
