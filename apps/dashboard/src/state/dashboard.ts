import type { BrowserFrame, TimerRecord, VoiceEvent } from "../types/contracts";

export type View =
  | "default"
  | "weather_current"
  | "weather_daily"
  | "weather_weekly"
  | "timers"
  | "smart_home"
  | "media";
export type Phase =
  | "STARTING"
  | "IDLE"
  | "WAKE_DETECTED"
  | "LISTENING"
  | "UPLOADING"
  | "TRANSCRIBING"
  | "THINKING"
  | "TOOL_EXECUTING"
  | "SYNTHESIZING"
  | "DELIVERING"
  | "SPEAKING"
  | "FOLLOW_UP"
  | "ERROR";
export const phases: Phase[] = [
  "STARTING",
  "IDLE",
  "WAKE_DETECTED",
  "LISTENING",
  "UPLOADING",
  "TRANSCRIBING",
  "THINKING",
  "TOOL_EXECUTING",
  "SYNTHESIZING",
  "DELIVERING",
  "SPEAKING",
  "FOLLOW_UP",
  "ERROR",
];
export const labels: Record<Phase | "OFFLINE" | "MUTED" | "ALARM", string> = {
  STARTING: "Getting ready",
  IDLE: "Here when you need me",
  WAKE_DETECTED: "Hello, I'm listening",
  LISTENING: "Listening",
  UPLOADING: "Heard you",
  TRANSCRIBING: "Finding your words",
  THINKING: "Thinking",
  TOOL_EXECUTING: "Taking care of it",
  SYNTHESIZING: "Preparing a reply",
  DELIVERING: "Getting your reply ready",
  SPEAKING: "Speaking",
  FOLLOW_UP: "Anything else?",
  ERROR: "Something needs attention",
  OFFLINE: "Connection interrupted",
  MUTED: "Microphone muted",
  ALARM: "Your timer is ready",
};

export type Voice = {
  phase: Phase;
  session: string | null;
  transcript: string;
  response: string;
  error: string;
  playing: boolean;
  position: number;
  samples: number;
  expires: number;
  playback: string | null;
};
export const emptyVoice = (): Voice => ({
  phase: "IDLE",
  session: null,
  transcript: "",
  response: "",
  error: "",
  playing: false,
  position: 0,
  samples: 0,
  expires: 0,
  playback: null,
});
export type DashboardState = {
  frame: BrowserFrame | null;
  voice: Voice;
  cursor: number;
  voiceCursor: number;
  eventIds: string[];
  notices: string[];
  network: "connecting" | "online" | "offline" | "unpaired";
  offset: number;
  receivedAt: number;
  error: string;
};
export const initialState = (): DashboardState => ({
  frame: null,
  voice: emptyVoice(),
  cursor: 0,
  voiceCursor: 0,
  eventIds: [],
  notices: [],
  network: "connecting",
  offset: 0,
  receivedAt: 0,
  error: "",
});

function applyVoice(previous: Voice, event: VoiceEvent, ttl: number): Voice {
  const p = event.payload;
  const session =
    typeof p.session_id === "string" ? p.session_id : previous.session;
  const fresh =
    session &&
    session !== previous.session &&
    event.type !== "assistant.edge_state";
  const next = { ...(fresh ? emptyVoice() : previous), session };
  if (typeof p.state === "string" && phases.includes(p.state as Phase))
    next.phase = p.state as Phase;
  if (["IDLE", "FOLLOW_UP", "ERROR"].includes(next.phase)) {
    next.playing = false;
    next.transcript = "";
    next.response = "";
  }
  if (typeof p.transcript === "string" && p.transcript)
    next.transcript = p.transcript;
  if (typeof p.response === "string" && p.response) next.response = p.response;
  if (typeof p.error === "string") next.error = p.error;
  const metrics = p.metrics as Record<string, unknown> | undefined;
  if (typeof metrics?.sample_count === "number" && metrics.sample_count > 0)
    next.samples = metrics.sample_count;
  if (event.type === "assistant.playback" && !p.alarm_id) {
    const request = typeof p.request_id === "string" ? p.request_id : null;
    if (p.status === "started" || p.status === "progress") {
      next.playing = true;
      next.phase = "SPEAKING";
      next.playback = request;
      if (typeof p.position_samples === "number")
        next.position = Math.max(next.position, p.position_samples);
    } else if (
      ["completed", "cancelled", "failed", "indeterminate"].includes(
        String(p.status),
      )
    ) {
      if (!next.playback || next.playback === request) {
        next.playing = false;
        next.phase =
          p.status === "completed"
            ? "FOLLOW_UP"
            : p.status === "cancelled"
              ? "IDLE"
              : "ERROR";
        if (p.status !== "completed") next.response = "";
      }
    }
  }
  next.expires = Date.parse(event.timestamp) + ttl * 1000;
  return next;
}

export function receive(
  state: DashboardState,
  frame: BrowserFrame,
  now = Date.now(),
): DashboardState {
  const reset =
    frame.reset ||
    frame.epoch !== state.frame?.epoch ||
    frame.session.id !== state.frame?.session.id;
  if (
    !reset &&
    (frame.application.revision < (state.frame?.application.revision ?? 0) ||
      frame.events.cursor < state.cursor)
  )
    return state;
  let voice =
    reset || frame.voice.resync_required ? emptyVoice() : { ...state.voice };
  let revision = reset || frame.voice.resync_required ? 0 : state.voiceCursor;
  const ids = new Set(reset ? [] : state.eventIds);
  const notices = reset ? [] : [...state.notices];
  for (const event of [...frame.voice.events].sort(
    (a, b) => a.revision - b.revision,
  )) {
    if (event.revision <= revision || ids.has(event.event_id)) continue;
    voice = applyVoice(voice, event, frame.voice.expires_after_seconds);
    revision = event.revision;
    ids.add(event.event_id);
  }
  for (const event of [...frame.events.events].sort(
    (a, b) => a.sequence - b.sequence,
  )) {
    if (event.sequence <= (reset ? 0 : state.cursor) || ids.has(event.event_id))
      continue;
    ids.add(event.event_id);
    if (
      event.type === "tool.execution_completed" &&
      event.payload.status === "error"
    )
      notices.push("A requested action could not be confirmed.");
  }
  const offset = Date.parse(frame.server_time) - now;
  if (now + offset > voice.expires) voice = emptyVoice();
  const edge = frame.voice.devices[0]?.edge;
  if (!frame.voice.devices[0]?.connected || edge?.muted) voice = emptyVoice();
  if (
    !frame.voice.events.length &&
    !voice.expires &&
    edge &&
    phases.includes(edge.state)
  )
    voice.phase = edge.state;
  if (!frame.session.permissions.captions) {
    voice.transcript = "";
    voice.response = "";
  }
  return {
    ...state,
    frame,
    voice,
    cursor: Math.max(reset ? 0 : state.cursor, frame.events.cursor),
    voiceCursor: frame.voice.revision,
    eventIds: [...ids].slice(-512),
    notices: notices.slice(-3),
    network: "online",
    offset,
    receivedAt: now,
    error: "",
  };
}

export function countdown(timer: TimerRecord, now: number): number {
  return timer.status === "RUNNING" && timer.deadline
    ? Math.min(timer.duration_ms, Math.max(0, Date.parse(timer.deadline) - now))
    : timer.remaining_ms;
}
export function duration(ms: number): string {
  const seconds = Math.ceil(Math.max(0, ms) / 1000);
  return `${Math.floor(seconds / 60)
    .toString()
    .padStart(2, "0")}:${(seconds % 60).toString().padStart(2, "0")}`;
}
export function selectedView(state: DashboardState): View {
  if (state.frame?.application.alarms?.length) return "timers";
  const view = state.frame?.application.views?.at(-1)?.view;
  return [
    "default",
    "weather_current",
    "weather_daily",
    "weather_weekly",
    "timers",
    "smart_home",
    "media",
  ].includes(String(view))
    ? (view as View)
    : "default";
}
export function visiblePhase(
  state: DashboardState,
): Phase | "OFFLINE" | "MUTED" | "ALARM" {
  if (state.frame?.application.alarms?.length) return "ALARM";
  if (state.network !== "online" || !state.frame?.voice.devices[0]?.connected)
    return "OFFLINE";
  if (state.frame.voice.devices[0]?.edge?.muted) return "MUTED";
  return state.voice.phase;
}
