import { useEffect, useState } from "react";
import { useDashboard } from "../app/AppProvider";
import type { PresenceOptions } from "../types/contracts";

export function PresenceSettings() {
  const { state, session, pending, display } = useDashboard();
  const status = state.frame?.presence;
  const [draft, setDraft] = useState<PresenceOptions | undefined>(
    status?.settings,
  );
  const settingsKey = JSON.stringify(status?.settings);
  useEffect(() => setDraft(status?.settings), [settingsKey]);
  const online = state.network === "online" && !!status;
  const allowed =
    online &&
    !!session?.permissions.display_control &&
    !!state.frame?.application.availability?.mutations_enabled;
  const change = (patch: Partial<PresenceOptions>) =>
    setDraft((p) => ({ ...p, ...patch }));
  return (
    <section aria-label="Presence and backlight" className="presence-settings">
      <h3>Presence and backlight</h3>
      <dl className="diagnostics">
        <div>
          <dt>Sensor</dt>
          <dd>
            {online
              ? `${status.reading?.health} · ${status.confirmed}${status.simulated ? " · simulated" : ""}`
              : "Unknown · mirror offline"}
          </dd>
        </div>
        <div>
          <dt>Backlight target</dt>
          <dd>
            {online
              ? `${status.target_percent ?? "Unknown"}% · ${status.reason}`
              : "Unknown"}
          </dd>
        </div>
        <div>
          <dt>Last acknowledged target</dt>
          <dd>
            {online && status.acknowledged_percent != null
              ? `${status.acknowledged_percent}%`
              : "Unknown"}
          </dd>
        </div>
        <div>
          <dt>Manual override</dt>
          <dd>{online && status.override_active ? "Active" : "Inactive"}</dd>
        </div>
        <div>
          <dt>Activity protection</dt>
          <dd>{online && status.activity_protected ? "Active" : "Inactive"}</dd>
        </div>
      </dl>
      <p className="settings-note">
        Targets describe commands. Physical brightness and fade completion are
        not measured.
      </p>
      {status?.uncertain && (
        <p role="status">
          The last hardware result is unknown. Automation is paused. Inspect the
          mirror before making a fresh manual request.
        </p>
      )}
      {draft && (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void display({ settings: draft });
          }}
        >
          <fieldset disabled={!allowed || pending}>
            <legend>Local display policy</legend>
            <label className="check">
              <input
                type="checkbox"
                checked={draft.enabled ?? false}
                onChange={(e) => change({ enabled: e.target.checked })}
              />
              Enable presence automation
            </label>
            <label>
              Preferred brightness (%)
              <input
                type="number"
                min="0"
                max="100"
                value={draft.preferred_percent ?? 65}
                onChange={(e) =>
                  change({ preferred_percent: Number(e.target.value) })
                }
              />
            </label>
            <label>
              Confirmed absence delay (seconds)
              <input
                type="number"
                min="0"
                max="86400"
                value={draft.absence_timeout ?? 120}
                onChange={(e) =>
                  change({ absence_timeout: Number(e.target.value) })
                }
              />
            </label>
            <label>
              Manual override duration (seconds)
              <input
                type="number"
                min="1"
                max="86400"
                value={draft.manual_override_seconds ?? 300}
                onChange={(e) =>
                  change({ manual_override_seconds: Number(e.target.value) })
                }
              />
            </label>
            <label>
              Unknown sensor policy
              <select
                value={draft.unknown_policy ?? "awake"}
                onChange={(e) =>
                  change({ unknown_policy: e.target.value as "awake" | "hold" })
                }
              >
                <option value="awake">Keep awake</option>
                <option value="hold">Hold last target</option>
              </select>
            </label>
            <label className="check">
              <input
                type="checkbox"
                checked={draft.night?.enabled ?? false}
                onChange={(e) =>
                  change({
                    night: { ...draft.night, enabled: e.target.checked },
                  })
                }
              />
              Scheduled night brightness
            </label>
            <label>
              Night timezone
              <input
                value={draft.night?.timezone ?? "UTC"}
                onChange={(e) =>
                  change({
                    night: { ...draft.night, timezone: e.target.value },
                  })
                }
              />
            </label>
            <label>
              Night starts
              <input
                type="time"
                value={draft.night?.start ?? "22:00"}
                onChange={(e) =>
                  change({ night: { ...draft.night, start: e.target.value } })
                }
              />
            </label>
            <label>
              Night ends
              <input
                type="time"
                value={draft.night?.end ?? "07:00"}
                onChange={(e) =>
                  change({ night: { ...draft.night, end: e.target.value } })
                }
              />
            </label>
            <label>
              Night brightness (%)
              <input
                type="number"
                min="0"
                max="100"
                value={draft.night?.percent ?? 25}
                onChange={(e) =>
                  change({
                    night: { ...draft.night, percent: Number(e.target.value) },
                  })
                }
              />
            </label>
            <button type="submit">Save display policy</button>
            <button
              type="button"
              onClick={() =>
                void display({
                  override_percent: draft.preferred_percent ?? 65,
                })
              }
            >
              Keep awake temporarily
            </button>
            <button
              type="button"
              onClick={() => void display({ override_percent: 0 })}
            >
              Backlight off temporarily
            </button>
            <button
              type="button"
              onClick={() => void display({ release_override: true })}
            >
              Resume automatic policy
            </button>
          </fieldset>
        </form>
      )}
      {!session?.permissions.display_control && (
        <p className="settings-note">
          An administrator must grant display control before these settings can
          be changed.
        </p>
      )}
    </section>
  );
}
