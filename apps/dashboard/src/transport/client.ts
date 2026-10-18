import type { BrowserFrame, BrowserSession } from "../types/contracts";
import { parseFrame } from "./contract";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
export async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`/api/browser${path}`, {
    credentials: "same-origin",
    cache: "no-store",
    ...options,
    signal: options.signal
      ? AbortSignal.any([options.signal, AbortSignal.timeout(12000)])
      : AbortSignal.timeout(12000),
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(
      response.status,
      typeof body.detail === "string" ? body.detail : "Request unavailable",
    );
  }
  return response.json() as Promise<T>;
}
export function backoff(attempt: number, random = Math.random()): number {
  return Math.min(
    30000,
    500 * 2 ** Math.min(attempt, 6) * (0.8 + random * 0.4),
  );
}

/** One request at a time, full projection plus durable/volatile cursors. No mutation retries. */
export class DashboardClient {
  private timer: ReturnType<typeof setTimeout> | undefined;
  private controller: AbortController | undefined;
  private stopped = false;
  private attempt = 0;
  private epoch: string | undefined;
  private cursor = 0;
  private voiceCursor = 0;
  private renewalWindow: number;
  constructor(
    private session: BrowserSession,
    private frame: (frame: BrowserFrame) => void,
    private failure: (error: Error, unauthorized: boolean) => void,
  ) {
    this.renewalWindow = Math.min(
      24 * 60 * 60 * 1000,
      Math.max(1000, (Date.parse(session.expires_at) - Date.now()) / 2),
    );
  }
  start() {
    this.stopped = false;
    void this.poll();
  }
  stop() {
    this.stopped = true;
    clearTimeout(this.timer);
    this.controller?.abort();
  }
  private async poll() {
    this.controller = new AbortController();
    const timeout = setTimeout(() => this.controller?.abort(), 12000);
    let delay = 500;
    try {
      if (
        Date.parse(this.session.expires_at) - Date.now() <
        this.renewalWindow
      ) {
        const value = await request<{ session: BrowserSession }>(
          "/session/renew",
          {
            method: "POST",
            headers: { "X-Eve-CSRF": this.session.csrf },
            signal: this.controller.signal,
          },
        );
        this.session = value.session;
      }
      const query = this.epoch
        ? `?after=${this.cursor}&voice_after=${this.voiceCursor}&epoch=${this.epoch}`
        : "";
      const value = parseFrame(
        await request<unknown>(`/state${query}`, {
          signal: this.controller.signal,
        }),
        this.session.id,
      );
      if (!this.stopped) {
        this.epoch = value.epoch;
        this.cursor = value.events.cursor;
        this.voiceCursor = value.voice.revision;
        this.session = value.session;
        this.attempt = 0;
        this.frame(value);
      }
    } catch (error) {
      if (this.stopped) return;
      const unauthorized =
        error instanceof ApiError && [401, 403].includes(error.status);
      this.failure(
        error instanceof Error ? error : Error("Connection interrupted"),
        unauthorized,
      );
      if (unauthorized) {
        this.stop();
        return;
      }
      delay = backoff(this.attempt++);
    } finally {
      clearTimeout(timeout);
      if (!this.stopped) this.timer = setTimeout(() => void this.poll(), delay);
    }
  }
}
