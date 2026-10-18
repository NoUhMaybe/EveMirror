# Phase 7 deployment and rollback plan

This is a reviewable plan, not authorization to deploy. No production VM, Pi,
network, firmware or live integration was changed. Replace placeholders from an
operator-approved inventory; no VM ID, address, domain, HA entity or GPU is assumed.
Keep the existing Ollama VM independent and preserve all legacy rollback files.

## Inventory and approval record

Record these before selecting installation commands:

| Item | Value to establish |
| --- | --- |
| Backend host | `<approved Proxmox guest/VM ID, OS, address, CPU/RAM/storage>` |
| Proxy/TLS | `<existing proxy, DNS name, certificate chain, exact trusted proxy IPs>` |
| Ollama | `<existing private verified endpoint and installed model>` |
| Pi | `<model/RAM, OS/kernel, aarch64 architecture, glibc, Python version>` |
| Display | `<actual portrait pixel resolution, orientation, compositor/session>` |
| Audio | `<unique USB input/output names, rates, PortAudio configuration>` |
| Feather | `<stable data-interface path, firmware hashes, permissions/current owner>` |
| Sensor | `<selected model/firmware, approved protocol driver, power/logic/adapter>` |
| Storage | `<private model root, server volume, edge journals, kiosk profile, backup destination>` |
| Integrations | `<approved provider/model, HA entity/action grants, browser origin/grants>` |

Read-only inspection is Stage A of [hardware acceptance](PHASE7_HARDWARE_ACCEPTANCE.md).
`python scripts/preflight.py --role edge` inventories OS/Python, architecture,
glibc, package metadata, PortAudio library, systemd/Chromium/Wayland, audio/serial
paths, RAM and free storage. It does not open serial/audio or install anything.
Run as the intended kiosk/service user to get meaningful session/permissions data.
`--validate-config` additionally validates environment configuration and model
hashes without initializing inference. Load secrets through a trusted environment;
the script does not read env files implicitly and redacts validation failures.

## Compatibility gates

Core edge/backend target Python 3.11/3.12. The pinned Linux voice-edge set requires
Python 3.11 due to TFLite runtime 2.14.0. A cross-platform wheel download verified
34 pinned Python 3.11 ARM64 distributions, including ONNX Runtime, SoXR, NumPy,
SciPy, sounddevice and pyserial. The TFLite ARM64 wheel is tagged
`manylinux_2_34_aarch64`; a check limited to older glibc tags failed. Require glibc
2.34 or newer for this set. See [PyPI package metadata](https://pypi.org/pypi/tflite-runtime/2.14.0/json).
The ONNX wake path does not intentionally run TFLite inference.

Wheel availability does not establish ABI compatibility, PortAudio linkage,
model support, USB audio stability or ARM execution. The real Pi OS is unknown.
Do not replace its Python/OS or add unreviewed package repositories to satisfy this
plan. Select an approved isolated Python 3.11 installation and test actual imports,
ONNX wake/VAD assets and audio after installation approval. Python 3.12 remains a
core test target, not a claim of Linux voice-edge installation support.

## Isolated Linux/container validation

The Windows workspace has no Docker daemon or installed WSL Linux distribution.
The repository supplies a repeatable Ubuntu CI container job and a separate Linux
speech-install/import job. Neither connects to production or physical devices.

On an **approved disposable Docker test host**, these commands create new isolated
containers, a private network and new volumes with random `eve-acceptance-*` names:

```sh
docker build -f deploy/server/Dockerfile -t evemirror-test:<reviewed-sha> .
python scripts/container_acceptance.py --image evemirror-test:<reviewed-sha> --allow-isolated-containers
```

Acceptance builds the frontend into the image; starts nonroot/read-only FastAPI
with a writable SQLite volume and read-only fixture model mount; verifies migration,
health/static assets, CSP, real TLS validation through Caddy's private test CA,
authenticated edge WebSockets, pairing, Secure/HttpOnly/SameSite cookies, CSRF,
SQLite online backup/restore integrity, graceful shutdown and persisted sessions
after restart. The bare backend has no published port on its internal network.
Only the TLS proxy joins a separate bridge with loopback-only host ingress.
Test proxy trust uses the
actual isolated network's inspected subnet, not a production wildcard. Test
credentials exist only in a private temporary env file and logs are checked for
them. The script removes only resources created by that invocation. This validates
container software, not production routing, DNS, certificate renewal or real models.

ARM64 CI only downloads wheels without executing them. The Linux voice job installs
the pinned voice-edge set and imports libraries without audio/model initialization.
Real ARM64 execution, model warmup and Pi performance still require device acceptance.

## Backend installation, after separate approval

1. Save the prior application SHA/image digest, deployment files, private env,
   dashboard build and compatible SQLite online backup. Record restore instructions
   and access paths before changing anything. Preserve the existing Ollama guest.
2. Review `deploy/server/Dockerfile`, `compose.yaml` and `server.env.example`.
   Create a protected `server.env` outside version control with distinct high-entropy
   operator/device credentials. Use one backend process; no replica shares its DB.
3. Configure the actual private Ollama endpoint/model. Speech is optional; for local
   STT/TTS build with `EVE_INSTALL_SPEECH=1`, install verified private models into the
   reviewed asset mount, and enable speech only with a trusted manifest. No models
   or credentials go in the image or repository. CPU INT8 is the documented starting
   configuration; no Intel Arc/GPU acceleration is assumed.
4. Provision the persistent volume with UID/GID 10001 access and mount private model
   assets read-only. Keep the root filesystem read-only, capability drop,
   no-new-privileges, bounded tmpfs and graceful stop timeout. Do not mount Docker
   sockets or host device trees into the backend. Base health is `/health/live`;
   authenticated `/api/health` reports database/model/config availability separately.
5. Bind bare backend only to reviewed loopback/private routing. Configure actual TLS
   origin and exact proxy trust, WebSocket upgrades, firewall and backup access.
   Review `deploy/dashboard/Caddyfile.example`; do not invent Cloudflare/DNS changes.
   Verify cert trust and Secure cookies in the real browser before pairing.
6. Enable browser only for exact origins/device grants; physical `display_control`,
   voice control, captions, timers and HA grants default false. Mutation controls
   additionally require the backend mutation opt-in. Pair through the operator CLI
   from a trusted terminal. Never put operator/device/provider secrets in Chromium.
7. Once the deployment window is approved, example commands are:

```sh
docker compose --env-file <private-compose-env> -f deploy/server/compose.yaml build
docker compose --env-file <private-compose-env> -f deploy/server/compose.yaml up -d
curl --fail https://<approved-origin>/health/live
```

These commands have **not** been run against a deployed service. Validate the
actual Compose model locally before execution and review rendered output privately.

## Pi installation, after separate approval

Prepare a dedicated `evemirror` user, protected env file and writable state directory,
with only required audio/dialout membership and verified stable device paths. Stop
the legacy serial owner before starting the replacement; never run two owners.
Record current units/processes, display/HDMI settings, profile and SSH recovery path.

The following are installation examples requiring approval, not commands to run
as part of read-only preflight:

```sh
<approved-python3.11> -m venv /opt/evemirror/.venv
/opt/evemirror/.venv/bin/python -m pip install -r requirements/voice-edge.lock
/opt/evemirror/.venv/bin/python -m pip install --no-deps .
/opt/evemirror/.venv/bin/python -m pip check
# Install reviewed edge.env/unit files and enable/start only in the agreed window.
sudo systemctl daemon-reload
sudo systemctl enable --now evemirror-edge.service
```

OS PortAudio/USB support must be checked and installed only after the actual OS is
known. Configure unique audio names, stable Feather data path, trusted edge model
manifest and writable command/voice journal paths. Verify model storage capacity
and that the service user can read assets and access its devices. Run asset
validation without audio first; real capture/playback requires Stage C approval.

Review the kiosk launcher/user service with the actual Wayland session and Chromium
binary. Use a separate persistent private browser profile and explicit pairing.
Retain Chromium's sandbox. Do not copy Playwright's software-rendering flags into
production. Select actual portrait resolution/orientation without changing HDMI,
compositor output or boot configuration during this milestone. Kiosk restart must
recover the paired session and truthful offline state. Reboot/rotation changes need
their own approved test window. Keep SSH available and preserve a known-good boot.

Presence defaults disabled. There is no real sensor driver to install yet. Complete
sensor selection, electrical review, protocol implementation and its tests before
enabling physical automatic presence. Simulator use must remain visibly marked.

## Upgrade and rollback

Use SQLite online backup for each server/edge DB rather than copying a live WAL DB:

```sh
python scripts/backup_database.py --source <existing-db> --destination <new-private-backup>
```

The script refuses an existing destination. Record schema versions, application
SHA, model manifest/hash and backup timestamps. Protect backups like credentials
and timer names. A backup older than issued actions loses newer replay identities:
do not replay uncertain commands or restore brightness automatically from that gap.

Upgrade the backend before the new capability-advertising edge. The backend omits
new presence snapshot fields for old edges. Upgrade the browser build/contracts
together; old generated validators can reject new event types until reloaded.
The new default-false display grant participates in the browser policy hash, so
existing Phase 6 sessions need fresh operator pairing after this upgrade. Back up
the private profile, and plan pairing access before changing the deployed build.
Keep prior image/source/venv, env, browser build and a compatible DB backup. The
new `display_preferences` table is additive within edge journal v1; never delete
the command rows/tombstones to revert policy.

For rollback in an approved window: stop the replacement edge, verify the serial
handle is released, restore the previous compatible application and private config,
then restore DB/profile only if required by schema compatibility. Preserve the
newer journals for reconciliation. Restart exactly one selected owner and verify
health, mute, browser session, timers and receipts before any explicit brightness
command. Explicitly authorize a target if hardware state is uncertain. Do not
restore firmware or boot files unless separately approved; none changed here.

Do not delete `legacy/` until live acceptance and the rollback retention period
are complete. Save kiosk profile backup before session/permission changes and
revoke credentials when profile trust is lost. Run the physical acceptance plan
and performance/soak gates before calling the deployment production-ready.
