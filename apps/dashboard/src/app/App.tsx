import { useCallback, useState } from "react";
import { AppProvider, useDashboard } from "./AppProvider";
import { AssistantOrb } from "../components/AssistantOrb";
import { Clock } from "../components/Clock";
import { ConnectionStatus } from "../components/ConnectionStatus";
import { LayoutManager } from "../components/LayoutManager";
import { Subtitles } from "../components/Subtitles";
import { Settings, type Preferences } from "../components/Settings";
import { AmbientWeather } from "../components/AmbientWeather";
import { useReducedMotion } from "../hooks/useClock";
import {
  labels,
  selectedView,
  visiblePhase,
  type View,
} from "../state/dashboard";

const views: [View, string][] = [
  ["default", "Home"],
  ["weather_current", "Weather"],
  ["weather_daily", "Today"],
  ["weather_weekly", "This week"],
  ["timers", "Timers"],
  ["smart_home", "My space"],
  ["media", "Media"],
];
function preferences(): Preferences {
  try {
    const p = JSON.parse(
      localStorage.getItem("eve.display.preferences.v1") ?? "{}",
    );
    return {
      quality: ["low", "balanced", "high"].includes(p.quality)
        ? p.quality
        : "balanced",
      intensity:
        typeof p.intensity === "number"
          ? Math.max(0, Math.min(1, p.intensity))
          : 0.7,
      reduced: p.reduced === true,
    };
  } catch {
    return { quality: "balanced", intensity: 0.7, reduced: false };
  }
}
function Display() {
  const {
    state,
    session,
    code,
    pair,
    pairingError,
    view,
    mute,
    cancel,
    pending,
    notice,
    dismissNotice,
  } = useDashboard();
  const [settings, setSettings] = useState(location.pathname === "/settings");
  const [prefs, setPrefs] = useState(preferences);
  const [fps, setFps] = useState(0);
  const reduced = useReducedMotion();
  const recordFps = useCallback((rate: number) => setFps(rate), []);
  const change = (p: Preferences) => {
    setPrefs(p);
    try {
      localStorage.setItem("eve.display.preferences.v1", JSON.stringify(p));
    } catch {
      /* Preferences are optional; no backend state is cached. */
    }
  };
  const phase = visiblePhase(state);
  const selected = selectedView(state);
  const paired = !!session;
  const online = state.network === "online";
  const edge = state.frame?.voice.devices[0];
  return (
    <div
      className="dashboard"
      data-testid="dashboard"
      data-contextual={
        selected !== "default" || !!state.frame?.application.timers?.length
      }
      data-reduced={reduced || prefs.reduced}
      data-layout={state.frame?.application.views?.at(-1)?.layout ?? "default"}
    >
      <header className="masthead">
        <a className="wordmark" href="/" aria-label="Eve home">
          eve
          <span className="brand-dot" />
        </a>
        <div className="header-controls">
          <ConnectionStatus />
          {paired && (
            <button
              className="icon-button"
              onClick={() => setSettings(true)}
              aria-label="Display settings"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 7h16M4 17h16M8 4v6m8 4v6" />
              </svg>
            </button>
          )}
        </div>
      </header>
      <section className="day-header">
        <Clock />
        {paired && <AmbientWeather />}
      </section>
      {!paired ? (
        <main className="pairing-screen">
          <AssistantOrb
            phase="IDLE"
            level={0}
            progress={0}
            quality={prefs.quality}
            reduced={reduced || prefs.reduced}
            intensity={prefs.intensity}
          />
          <div className="pairing-copy">
            <p className="eyebrow">Welcome to your everyday</p>
            <h1>A little more connected.</h1>
            <p>Pair this display with your Eve mirror to get started.</p>
            {code ? (
              <>
                <output data-testid="pair-code" className="pair-code">
                  {code}
                </output>
                <p className="settings-note">
                  Have your administrator approve this code for your mirror.
                  This code expires shortly.
                </p>
              </>
            ) : (
              <button className="accent" onClick={() => void pair()}>
                Pair this display
              </button>
            )}
            {pairingError && (
              <p className="error-copy" role="alert">
                {pairingError}
              </p>
            )}
            {state.error && <p role="status">{state.error}</p>}
          </div>
        </main>
      ) : (
        <>
          <main className="stage">
            <section className="assistant-space" data-testid="assistant">
              <AssistantOrb
                phase={phase}
                level={edge?.edge?.input_level_rms ?? 0}
                progress={
                  state.voice.samples
                    ? state.voice.position / state.voice.samples
                    : 0
                }
                quality={prefs.quality}
                reduced={reduced || prefs.reduced}
                intensity={prefs.intensity}
                metrics={recordFps}
              />
              <p
                className="assistant-label"
                data-testid="voice-label"
                role="status"
              >
                {labels[phase]}
              </p>
              <Subtitles />
            </section>
            <LayoutManager />
          </main>
          {(notice || pending) && (
            <div className="notice" role="status">
              <span>{pending ? "Waiting for confirmation…" : notice}</span>
              <button
                className="quiet"
                onClick={dismissNotice}
                aria-label="Dismiss notice"
              >
                Close
              </button>
            </div>
          )}
          <footer className="footer">
            <nav aria-label="Dashboard views">
              {views.map(([key, label]) => (
                <button
                  key={key}
                  aria-current={selected === key ? "page" : undefined}
                  disabled={
                    !online ||
                    pending ||
                    (!!state.frame?.application.alarms?.length &&
                      key !== "timers")
                  }
                  onClick={() => void view(key)}
                >
                  {label}
                </button>
              ))}
            </nav>
            <div className="voice-controls">
              <button
                disabled={
                  !online ||
                  !edge?.connected ||
                  !session.permissions.voice_control ||
                  state.frame?.application.availability?.voice_control !==
                    true ||
                  pending
                }
                onClick={() => void mute(!edge?.edge?.muted)}
              >
                {edge?.edge?.muted ? "Unmute mic" : "Mute mic"}
              </button>
              <button
                disabled={
                  !online ||
                  !edge?.connected ||
                  !session.permissions.voice_control ||
                  pending
                }
                onClick={() => void cancel()}
              >
                Stop Eve
              </button>
            </div>
          </footer>
        </>
      )}
      {settings && paired && (
        <div className="settings-scrim">
          <Settings
            preferences={prefs}
            change={change}
            close={() => {
              setSettings(false);
              if (location.pathname === "/settings")
                history.replaceState({}, "", "/");
            }}
            fps={fps}
          />
        </div>
      )}
    </div>
  );
}
export default function App() {
  return (
    <AppProvider>
      <Display />
    </AppProvider>
  );
}
