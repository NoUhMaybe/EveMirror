import validate from "../types/validate.mjs";
import type { BrowserFrame } from "../types/contracts";

export function parseFrame(value: unknown, sessionId?: string): BrowserFrame {
  if (!validate(value))
    throw Error("The server returned an invalid dashboard contract.");
  const frame = value as BrowserFrame;
  const device = frame.session.device_id;
  if (sessionId && frame.session.id !== sessionId)
    throw Error("Dashboard scope changed.");
  if (
    (frame.application.timers ?? []).some((x) => x.device_id !== device) ||
    (frame.application.alarms ?? []).some((x) => x.device_id !== device) ||
    frame.events.events.some(
      (x) => x.device_id !== null && x.device_id !== device,
    ) ||
    frame.events.events.some((x) => x.scope !== `voice:${device}`) ||
    frame.voice.devices.some((x) => x.device_id !== device) ||
    frame.voice.events.some((x) => x.device_id !== device) ||
    frame.home.some(
      (x) =>
        typeof x.entity_id !== "string" ||
        !frame.session.permissions.home_entities?.includes(x.entity_id),
    ) ||
    (frame.application.devices ?? []).some(
      (x) =>
        (typeof x.device_id === "string" && x.device_id !== device) ||
        (typeof x.entity_id === "string" &&
          !frame.session.permissions.home_entities?.includes(x.entity_id)),
    ) ||
    (frame.application.views ?? []).some(
      (x) => x.device_id && x.device_id !== device,
    )
  ) {
    throw Error("The server returned data outside this display's scope.");
  }
  return frame;
}
