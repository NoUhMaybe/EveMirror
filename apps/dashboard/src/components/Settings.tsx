import { useDashboard } from "../app/AppProvider";
import type { OrbProps } from "./AssistantOrb";

export type Preferences = {
  quality: OrbProps["quality"];
  intensity: number;
  reduced: boolean;
};
export function Settings({
  preferences,
  change,
  close,
  fps,
}: {
  preferences: Preferences;
  change: (p: Preferences) => void;
  close: () => void;
  fps: number;
}) {
  const { state, session, logout, pending } = useDashboard();
  return (
    <aside
      className="settings"
      role="dialog"
      aria-modal="true"
      aria-label="Display settings"
    >
      <div className="settings-heading">
        <p className="eyebrow">Make yourself at home</p>
        <button className="quiet" onClick={close}>
          Close
        </button>
      </div>
      <h2>Display settings</h2>
      <label>
        Animation quality
        <select
          value={preferences.quality}
          onChange={(event) =>
            change({
              ...preferences,
              quality: event.target.value as OrbProps["quality"],
            })
          }
        >
          <option value="low">Low · lighter on resources</option>
          <option value="balanced">Balanced</option>
          <option value="high">High detail</option>
        </select>
      </label>
      <label>
        Animation intensity
        <input
          type="range"
          min="0"
          max="1"
          step="0.1"
          value={preferences.intensity}
          onChange={(event) =>
            change({ ...preferences, intensity: Number(event.target.value) })
          }
        />
      </label>
      <label className="check">
        <input
          type="checkbox"
          checked={preferences.reduced}
          onChange={(event) =>
            change({ ...preferences, reduced: event.target.checked })
          }
        />
        Reduce motion
      </label>
      <p className="settings-note">
        System reduced-motion preferences always apply. The clock and widgets
        keep working if graphics are unavailable.
      </p>
      <dl className="diagnostics">
        <div>
          <dt>Assigned mirror</dt>
          <dd>{session?.device_id}</dd>
        </div>
        <div>
          <dt>Display session</dt>
          <dd>{session?.name}</dd>
        </div>
        <div>
          <dt>Connection</dt>
          <dd>{state.network}</dd>
        </div>
        <div>
          <dt>Microphone</dt>
          <dd>
            {state.frame?.voice.devices[0]?.edge?.muted
              ? "Muted"
              : state.frame?.voice.devices[0]?.edge?.microphone
                ? "Available"
                : "Unavailable"}
          </dd>
        </div>
        <div>
          <dt>Render rate</dt>
          <dd>
            {fps ? `${fps.toFixed(1)} fps · this browser` : "Not measured"}
          </dd>
        </div>
        <div>
          <dt>Provider / model</dt>
          <dd>
            {state.frame?.provider} / {state.frame?.model ?? "Unconfigured"}
          </dd>
        </div>
      </dl>
      {session?.permissions.debug && (
        <details>
          <summary>Event diagnostics</summary>
          <p className="settings-note">
            Current session metadata. Captions and credentials are omitted.
          </p>
          <ol className="event-list">
            {state.frame?.voice.events
              .slice(-12)
              .reverse()
              .map((event) => (
                <li key={event.event_id}>
                  <strong>{event.type}</strong>
                  <time>{new Date(event.timestamp).toLocaleTimeString()}</time>
                </li>
              ))}
          </ol>
          <p className="settings-note">
            Application cursor {state.cursor} · voice {state.voiceCursor}
          </p>
        </details>
      )}
      <button
        className="logout"
        disabled={pending || state.network !== "online"}
        onClick={() => void logout()}
      >
        Unpair this display
      </button>
    </aside>
  );
}
