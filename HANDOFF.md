# Handoff Notes — HDMI "No Signal" Debugging (read this first)

Written so a fresh Copilot Chat session (e.g. on another machine) can pick up
exactly where this left off. Pi is accessed via `ssh noah@192.168.0.40`
(ethernet) or `.41` (wifi, IP may vary by DHCP lease).

## Status summary

- **Backlight control (Feather + 24V driver board): COMPLETE, verified working.**
  0-2V DAC scaling, 1.5s ease-out fade, ENA true-off at 0% — all deployed and
  tested on real hardware. See `backlight Control/feather/code.py` and
  `eve_agent/backlight_control.py`. No further work needed unless a new issue
  comes up.
- **HDMI video (Pi 5 → DT-1920-HDMI controller → LVDS panel): UNRESOLVED.**
  This is the active problem. Backlight works, so the panel/backlight path is
  confirmed fine — the fault is specifically in the Pi's HDMI output not
  reaching/being recognized by the DT-1920-HDMI controller.

## The problem

Pi does not reliably get a picture onto the panel via the DT-1920-HDMI
controller. Originally intermittent after a full power-off/on (reseating the
HDMI cable "fixed" it temporarily), but currently it is not working at all,
through any method tried.

Key diagnostic fact: when the LCD assembly is power-cycled by itself, the
DT-1920-HDMI's own on-screen "No Signal" message appears, then goes black.
This proves the controller's internal pipeline (OSD render, LVDS output,
panel) is healthy — the problem is specifically "no video signal is reaching
the controller's HDMI input."

## What's been tried and ruled out (all remote, via SSH)

1. `hdmi_force_hotplug` / `hdmi_group` / `hdmi_mode` / `hdmi_drive` /
   `hdmi_ignore_edid` in `/boot/firmware/config.txt` — **inert**. These are
   legacy firmware/fkms-only options; this Pi uses full KMS
   (`dtoverlay=vc4-kms-v3d`), so firmware never touches HDMI setup at all
   (confirmed by `disable_fw_kms_setup=1` being the Bookworm default, which
   blocks exactly this). Reverted; config.txt is back to stock + that one line.
2. Kernel cmdline `video=HDMI-A-1:1920x1080@60e` (and later also forcing
   `HDMI-A-2`) in `/boot/firmware/cmdline.txt` — this **is** the real/working
   mechanism under full KMS. Successfully forces the DRM connector to
   `connected`/`enabled` (confirmed via `/sys/class/drm/card1-HDMI-A-1/status`
   and `enabled`), and `wlr-randr` confirms the compositor actively drives it
   at 1920x1080@59.99, portrait `Transform: 90`. **Despite this, no picture.**
   Forcing *both* HDMI-A-1 and HDMI-A-2 simultaneously (to rule out "wrong
   physical port" given the Pi 5 has two micro-HDMI ports) made no difference
   either — both report connected/enabled, still no picture. This rules out
   the port-mapping-ambiguity theory.
3. **Raw KMS test (the most conclusive test so far):** stopped `lightdm`
   (`sudo systemctl stop lightdm`) to free DRM master, then used
   `modetest -M vc4 -s 33:1920x1080@XR24 -v -F <n>` (connector id 33 =
   HDMI-A-1) to do a real atomic modeset + draw an actual test-pattern
   framebuffer, completely bypassing Wayland/labwc. This is the lowest-level
   thing the Pi can do short of writing raw TMDS. **Still no picture, and the
   controller still showed nothing.** (Remember to `sudo systemctl start
   lightdm` again afterward — already done.)
4. `dmesg | grep -iE 'vc4|hdmi|phy|tmds|i2c|drm'` after all of the above:
   completely clean, no PHY/TMDS/link/I2C errors of any kind logged.
   EDID read size is consistently 0 bytes
   (`wc -c < /sys/class/drm/card1-HDMI-A-1/edid`).

**Conclusion so far:** every software/kernel/compositor-level avenue has been
exhausted. The DT-1920-HDMI manual (see `backlight Control/` directory or ask
user — it was supplied as a PDF, confirms P3 is a plain standard HDMI Type-A
connector with totally standard VESA DDC/EDID/HPD wiring, nothing exotic) —
so there's no special EDID trick needed on the source side either. This
strongly points to a **physical/electrical fault**: cable, micro-HDMI
connector (on the Pi or the controller), or a damaged pin — not firmware,
not Wayland, not EDID negotiation logic.

## What's NOT yet been tried (needs physical access to the enclosure)

The user does not want to re-open the mirror enclosure except when
necessary, since reseating cables is what "fixes" it temporarily but isn't
viable once sealed long-term. Three tests are queued for next time it's open
(not yet scheduled as of this note):

1. **Check LED1A's color the instant power is applied.** LED1A is an
   on-board dual-color status LED on the DT-1920-HDMI controller itself.
   Per the manual: **RED** = no signal & backlight off, **GREEN** = signal
   present & backlight on, **ORANGE** = "Update EDID in progress or HDMI
   EDID is error". This alone narrows the fault category instantly. Not
   currently visible from outside the enclosure (confirmed with user).
2. **Swap in a different/known-good HDMI cable.** Single highest-value
   physical test remaining — reseating is literally what "fixes" it each
   time, consistent with a marginal cable or connector rather than firmware.
3. **Wire CN8 (RS-232/serial control header) to the Pi's own UART** to send
   the `0xC9` "query video input status" command directly to the controller
   (response digit `"0","0"` = invalid/no input, `"H","1"` = HDMI detected).
   This is an authoritative, controller-side answer independent of the OSD
   or any display. Also not currently wired/accessible (confirmed with user).

   Important wiring notes if/when this is done:
   - **Do NOT use a true RS-232 (DB9, ±12V) USB adapter** — CN8 is a bare
     6-pin, 1.25mm-pitch header with no RS-232 line-driver chip on board, so
     it's almost certainly 5V TTL logic despite the manual calling it
     "RS-232". A real RS-232-voltage adapter wired directly to it risks
     damaging the controller board. (User was about to buy a PL2303HX DB9
     adapter off Amazon for this — **don't use it for CN8.**)
   - Instead: use the **Pi's own built-in UART** (GPIO14/TXD, GPIO15/RXD) —
     requires `enable_uart=1` in `config.txt` + disabling the serial console
     login on that UART. Only 3 wires needed: Pi TXD → CN8 pin 6 (RXD),
     Pi RXD → CN8 pin 4 (TXD), shared GND → CN8 pin 5. **Skip CN8 pin 3
     (+5V)** — don't tie the two boards' 5V rails together, just share
     ground.
   - Pi GPIO is 3.3V logic and **not 5V-tolerant** on inputs. Before wiring
     directly, either (a) put a cheap bidirectional 3.3V↔5V logic-level
     shifter module between the two UARTs (safest, a few dollars), or
     (b) measure CN8 pin 4 (TXD) with a multimeter first — if it idles at
     ~3.3V, direct wiring is fine; if ~5V, use the level shifter.
   - RS-232 protocol details (baud 9600, 8N1, command bytes, full table)
     are in the DT-1920-HDMI manual the user supplied as a PDF during this
     conversation — ask the user for it again if needed, or they may have
     saved it in the repo already.

## Fallback if all three come back inconclusive

Physical cable/connector/port damage becomes the leading theory by
elimination. Next steps at that point: try a different HDMI cable/adapter
chain entirely, visually inspect the Pi's micro-HDMI ports and the
controller's P3 HDMI connector for bent/damaged pins, or consider the
controller board itself may have a failed HDMI receiver chip (least likely,
since "No Signal" OSD proves its internal pipeline works, but not impossible
if the receiver chip itself is the failure point).

## Useful facts for whoever picks this up

- Pi 5, Debian 12 Bookworm, labwc Wayland compositor, lightdm autologin as
  `noah` (uid 1000).
- SSH: passwordless key auth already set up to `noah@192.168.0.40`.
- Config files live at `/boot/firmware/config.txt` and
  `/boot/firmware/cmdline.txt` on the Pi — **not** in this git repo. Backups
  exist on the Pi itself (e.g. `config.txt.bak-*`, `cmdline.txt.bak-*`) from
  edits made during this debugging session.
- `wlr-randr` must be run as:
  `sudo -u noah XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0 wlr-randr`
- Backlight: `python eve_agent/backlight_control.py <0-100>` over SSH, uses
  the Feather over USB serial — independent of HDMI/Ollama/the agent, good
  for confirming the panel's backlight rail works while debugging video.
- A prior unrelated transient issue this session: after a `reboot`, the Pi
  occasionally came up with SD-card I/O errors (`Input/output error` on
  basic commands, SSH `Connection reset`) that a **full power cycle**
  (unplug/replug, not `sudo reboot`) resolved cleanly both times it happened.
  If SSH starts failing with connection resets rather than timeouts, this is
  likely what's happening again — try a full power cycle before assuming a
  new problem.
