import test from "node:test";
import assert from "node:assert/strict";
import {
  initialState,
  receive,
  countdown,
  duration,
  selectedView,
  visiblePhase,
} from "../src/state/dashboard.ts";
import { graphSegments, forecastFor } from "../src/state/forecast.ts";
import { parseFrame } from "../src/transport/contract.ts";
import { frame, event, timer, stamp, session } from "./fixtures.mjs";

const now = Date.parse(stamp);
test("presence contract accepts explicit simulated targets and rejects invalid sensor data", () => {
  const f = frame();
  f.presence = {
    simulated: true,
    confirmed: "UNKNOWN",
    reading: { state: "UNKNOWN", health: "unavailable" },
    target_percent: 0,
    acknowledged_percent: 0,
    display: "asleep",
  };
  assert.equal(parseFrame(f).presence.display, "asleep");
  for (const patch of [
    { target_percent: 101 },
    { confirmed: "MOTION" },
    { reading: { state: "UNKNOWN", health: "disconnected-maybe" } },
    { serial_port: "/dev/ttyUSB0" },
  ]) {
    const invalid = structuredClone(f);
    Object.assign(invalid.presence, patch);
    assert.throws(() => parseFrame(invalid));
  }
});
for (const error of [
  "provider_unavailable",
  "transcription_failed",
  "tool_permission_denied",
]) {
  test(`${error} has explicit error feedback without stale speaking`, () => {
    const f = frame();
    f.voice.revision = 1;
    f.voice.events = [event(1, "assistant.error", { state: "ERROR", error })];
    const s = receive(initialState(), f, now);
    assert.equal(visiblePhase(s), "ERROR");
    assert.equal(s.voice.error, error);
    assert.equal(s.voice.playing, false);
  });
}
test("failed playback and disconnected edge clear speaking captions", () => {
  const f = frame();
  f.voice.revision = 2;
  f.voice.events = [
    event(1, "assistant.delivering", {
      state: "DELIVERING",
      response: "private",
    }),
    event(2, "assistant.playback", { status: "started", request_id: "p" }),
  ];
  const speaking = receive(initialState(), f, now);
  f.reset = false;
  f.voice.revision = 3;
  f.voice.events = [
    event(3, "assistant.playback", { status: "failed", request_id: "p" }),
  ];
  const failed = receive(speaking, f, now);
  assert.equal(visiblePhase(failed), "ERROR");
  assert.equal(failed.voice.response, "");
  f.voice.events = [];
  f.voice.devices[0].connected = false;
  const offline = receive(speaking, f, now);
  assert.equal(visiblePhase(offline), "OFFLINE");
  assert.equal(offline.voice.response, "");
});
test("terminal edge state clears speaking when a cancellation receipt follows closed delivery tracking", () => {
  const f = frame();
  f.voice.revision = 2;
  f.voice.events = [
    event(1, "assistant.delivering", {
      state: "DELIVERING",
      response: "private reply",
    }),
    event(2, "assistant.playback", {
      status: "started",
      request_id: "playback-1",
    }),
  ];
  let s = receive(initialState(), f, now);
  assert.equal(s.voice.playing, true);
  f.reset = false;
  f.voice.revision = 3;
  f.voice.events = [event(3, "assistant.edge_state", { state: "IDLE" })];
  s = receive(s, f, now);
  assert.equal(s.voice.playing, false);
  assert.equal(s.voice.response, "");
});
test("generated runtime contract rejects invalid versions, scopes, identities, timer values and events", () => {
  assert.equal(parseFrame(frame()).session.id, session);
  for (const change of [
    (f) => (f.version = 2),
    (f) => (f.application.timers = [{ ...timer(), duration_ms: -1 }]),
    (f) =>
      (f.voice.events = [
        { ...event(1, "assistant.thinking", {}), device_id: "other" },
      ]),
    (f) => (f.session.id = "not-a-uuid"),
    (f) => (f.events.events = [{ type: "arbitrary.event" }]),
    (f) => (f.home = [{ entity_id: "light.private" }]),
    (f) => (f.voice.devices[0].device_id = "other"),
  ]) {
    const f = frame();
    change(f);
    assert.throws(() => parseFrame(f));
  }
  assert.throws(() => parseFrame(frame(), "another-session"));
});
for (const phase of [
  "WAKE_DETECTED",
  "LISTENING",
  "TRANSCRIBING",
  "THINKING",
  "TOOL_EXECUTING",
  "SYNTHESIZING",
  "DELIVERING",
  "FOLLOW_UP",
  "IDLE",
  "ERROR",
]) {
  test(`voice state ${phase} follows semantic events`, () => {
    const f = frame();
    f.voice.revision = 1;
    f.voice.events = [event(1, "assistant.edge_state", { state: phase })];
    assert.equal(visiblePhase(receive(initialState(), f, now)), phase);
  });
}
test("speaking follows actual playback and sample position, cancellation clears captions", () => {
  const f = frame();
  f.voice.revision = 4;
  f.voice.events = [
    event(1, "assistant.thinking", {
      state: "THINKING",
      transcript: "what is the weather",
    }),
    event(2, "assistant.delivering", {
      state: "DELIVERING",
      response: "A long response is ready.",
      metrics: { sample_count: 24000 },
    }),
    event(3, "assistant.playback", {
      status: "started",
      request_id: "playback-1",
      position_samples: 0,
    }),
    event(4, "assistant.playback", {
      status: "progress",
      request_id: "playback-1",
      position_samples: 12000,
    }),
  ];
  let s = receive(initialState(), f, now);
  assert.equal(s.voice.phase, "SPEAKING");
  assert.equal(s.voice.position / s.voice.samples, 0.5);
  assert.equal(s.voice.response, "A long response is ready.");
  assert.ok(s.voice.playing);
  const next = structuredClone(f);
  next.reset = false;
  next.voice.revision = 5;
  next.voice.events = [
    event(5, "assistant.playback", {
      status: "cancelled",
      request_id: "playback-1",
    }),
  ];
  s = receive(s, next, now);
  assert.equal(s.voice.response, "");
  assert.equal(s.voice.playing, false);
  assert.equal(s.voice.phase, "IDLE");
});
test("duplicate and out-of-order events never rewind playback or captions", () => {
  const f = frame();
  f.voice.revision = 3;
  f.voice.events = [
    event(3, "assistant.playback", {
      status: "progress",
      position_samples: 12000,
    }),
    event(1, "assistant.thinking", { transcript: "hello", state: "THINKING" }),
    event(2, "assistant.delivering", {
      state: "DELIVERING",
      response: "hello",
      metrics: { sample_count: 24000 },
    }),
  ];
  let s = receive(initialState(), f, now);
  const again = { ...f, reset: false };
  const count = s.eventIds.length;
  s = receive(s, again, now);
  assert.equal(s.eventIds.length, count);
  assert.equal(s.voice.phase, "SPEAKING");
  assert.equal(s.voice.position, 12000);
});
test("new epoch, cursor reset, scope change and expired captions recover cleanly", () => {
  const f = frame();
  f.voice.revision = 1;
  f.voice.events = [
    event(1, "assistant.thinking", {
      transcript: "private",
      state: "THINKING",
    }),
  ];
  let s = receive(initialState(), f, now);
  assert.equal(s.voice.transcript, "private");
  const empty = frame();
  empty.epoch = "55555555-5555-4555-8555-555555555555";
  s = receive(s, empty, now);
  assert.equal(s.voice.transcript, "");
  assert.equal(s.voiceCursor, 0);
  f.server_time = "2026-10-18T12:02:00Z";
  assert.equal(receive(initialState(), f, now).voice.transcript, "");
});
test("alarms override informational views and offline/mute indicators stay honest", () => {
  const f = frame();
  f.application.views = [{ view: "weather_weekly" }];
  let s = receive(initialState(), f, now);
  assert.equal(selectedView(s), "weather_weekly");
  f.application.alarms = [
    { alarm_id: "a", timer_id: "b", device_id: "mirror-1", expired_at: stamp },
  ];
  s = receive(s, f, now);
  assert.equal(selectedView(s), "timers");
  assert.equal(visiblePhase(s), "ALARM");
  f.application.alarms = [];
  f.voice.devices[0].edge.muted = true;
  s = receive(s, f, now);
  assert.equal(visiblePhase(s), "MUTED");
  assert.equal(visiblePhase({ ...s, network: "offline" }), "OFFLINE");
});
test("timer countdown uses synchronized UTC deadlines and never creates an alarm locally", () => {
  assert.equal(countdown(timer(), now + 61000), 539000);
  assert.equal(duration(539000), "08:59");
  assert.equal(countdown(timer(), now + 999999), 0);
  assert.equal(countdown(timer("PAUSED"), now + 999999), 600000);
  const f = frame();
  f.application.timers = [timer()];
  const s = receive(initialState(), f, now + 2000);
  assert.equal(s.offset, -2000);
  assert.equal(s.frame.application.alarms.length, 0);
});
test("hourly graphs preserve missing-value gaps and constant/null forecasts", () => {
  const hours = [10, 11, null, 13, 14].map((temperature) => ({ temperature }));
  assert.equal(graphSegments(hours).length, 2);
  assert.equal(graphSegments([{ temperature: null }]).length, 0);
  assert.ok(
    !graphSegments([{ temperature: 10 }, { temperature: 10 }])
      .join()
      .includes("NaN"),
  );
  const daily = { daily: [{}], hourly: [{ temperature: 14 }] },
    weekly = { daily: Array(7).fill({}), hourly: [] };
  assert.equal(forecastFor([daily], weekly, "weather_weekly"), weekly);
  assert.equal(forecastFor([daily], weekly, "weather_daily"), daily);
  assert.equal(forecastFor([weekly], daily, "weather_daily"), daily);
});
