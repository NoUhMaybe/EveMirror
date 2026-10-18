export const device = "mirror-1";
export const session = "11111111-1111-4111-8111-111111111111";
export const stamp = "2026-10-18T12:00:00Z";
export function frame() {
  return {
    version: 1,
    epoch: "22222222-2222-4222-8222-222222222222",
    reset: true,
    server_time: stamp,
    session: {
      id: session,
      device_id: device,
      name: "Fixture mirror",
      expires_at: "2026-11-18T12:00:00Z",
      csrf: "fixture-csrf",
      permissions: {
        captions: true,
        timers: true,
        home_control: false,
        voice_control: true,
        debug: true,
        home_entities: [],
      },
    },
    application: {
      version: 1,
      timestamp: stamp,
      revision: 0,
      timers: [],
      alarms: [],
      weather: [],
      devices: [],
      views: [],
      tools: [],
      availability: { mutations_enabled: true },
    },
    events: { version: 1, cursor: 0, events: [] },
    voice: {
      version: 1,
      revision: 0,
      volatile: true,
      expires_after_seconds: 60,
      resync_required: false,
      events: [],
      devices: [
        {
          device_id: device,
          connected: true,
          edge: {
            state: "IDLE",
            muted: false,
            microphone: true,
            wake_ready: true,
            vad_ready: true,
            speaker: true,
            errors: 0,
            error: null,
            input_level_rms: 0,
            metrics: {},
          },
          last_success: null,
          application: null,
        },
      ],
      alarm_delivery: { available: true, alarms: [] },
    },
    ambient_weather: null,
    home: [],
    provider: "ollama",
    model: "fixture-model",
  };
}
export function event(revision, type, payload) {
  return {
    version: 1,
    event_id: `00000000-0000-4000-8000-${revision.toString().padStart(12, "0")}`,
    revision,
    timestamp: stamp,
    device_id: device,
    type,
    payload: { session_id: "33333333-3333-4333-8333-333333333333", ...payload },
  };
}
export function timer(status = "RUNNING") {
  return {
    id: "44444444-4444-4444-8444-444444444444",
    device_id: device,
    name: "Tea",
    duration_ms: 600000,
    remaining_ms: 600000,
    status,
    created_at: stamp,
    deadline: "2026-10-18T12:10:00Z",
    expired_at: null,
    acknowledged_at: null,
    updated_at: stamp,
    version: 1,
  };
}
