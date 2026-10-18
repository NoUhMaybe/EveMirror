import { useState } from "react";
import { useDashboard } from "../app/AppProvider";
import { useClock } from "../hooks/useClock";
import { countdown, duration } from "../state/dashboard";

export default function Timers({ compact = false }: { compact?: boolean }) {
  const { state, action, pending, session } = useDashboard();
  const now = useClock() + state.offset;
  const [requestedPage, setPage] = useState(0);
  const timers = state.frame?.application.timers ?? [];
  const alarms = state.frame?.application.alarms ?? [];
  const entries = [...timers].sort(
    (a, b) => Number(b.status === "EXPIRED") - Number(a.status === "EXPIRED"),
  );
  const size = compact ? 2 : 3;
  const page = Math.min(
    requestedPage,
    Math.max(0, Math.ceil(entries.length / size) - 1),
  );
  const allowed =
    !!session?.permissions.timers &&
    state.frame?.application.availability?.mutations_enabled === true &&
    state.network === "online" &&
    !pending;
  return (
    <section
      className={`widget timers ${compact ? "compact-timers" : ""}`}
      data-testid="timers"
      data-alarm={alarms.length > 0}
    >
      <div className="widget-heading">
        <div>
          <p className="eyebrow">
            {alarms.length ? "Time for a moment" : "Make time"}
          </p>
          <h2>
            {alarms.length
              ? "Your timer is ready"
              : compact
                ? "On your time"
                : "Timers"}
          </h2>
        </div>
        <span className="count-label">
          {timers.length ? `${timers.length} active` : "All clear"}
        </span>
      </div>
      {!timers.length && (
        <p className="empty-copy">
          Ask Eve to set a timer, or create one below.
        </p>
      )}
      {entries.slice(page * size, page * size + size).map((timer) => {
        const alarm = alarms.find((x) => x.timer_id === timer.id);
        const delivery = state.frame?.voice.alarm_delivery?.alarms?.find(
          (x) => x.alarm_id === alarm?.alarm_id,
        );
        const remaining = countdown(timer, now);
        return (
          <div className="timer-row" key={timer.id} data-testid="timer-row">
            <div className="timer-copy">
              <h3>{timer.name || "Timer"}</h3>
              <span>
                {alarm
                  ? `Pending acknowledgment · sound ${delivery?.delivery_status ?? "pending"}`
                  : timer.status === "PAUSED"
                    ? "Paused"
                    : remaining === 0
                      ? "Waiting for server confirmation"
                      : "Counting down"}
              </span>
            </div>
            <strong className="timer-value">
              {alarm ? "Ready" : duration(remaining)}
            </strong>
            <div className="timer-actions">
              {alarm ? (
                <button
                  className="accent"
                  disabled={!allowed}
                  onClick={() =>
                    void action("timer.acknowledge", { timer_id: timer.id })
                  }
                >
                  Dismiss alarm
                </button>
              ) : (
                <>
                  <button
                    disabled={!allowed}
                    onClick={() =>
                      void action(
                        timer.status === "PAUSED"
                          ? "timer.resume"
                          : "timer.pause",
                        { timer_id: timer.id },
                      )
                    }
                  >
                    {timer.status === "PAUSED" ? "Resume" : "Pause"}
                  </button>
                  <button
                    className="quiet"
                    disabled={!allowed}
                    onClick={() =>
                      void action("timer.cancel", { timer_id: timer.id })
                    }
                  >
                    Cancel
                  </button>
                </>
              )}
            </div>
          </div>
        );
      })}
      {entries.length > size && (
        <div className="pagination">
          <button disabled={page === 0} onClick={() => setPage(page - 1)}>
            Previous
          </button>
          <span>
            {page + 1} / {Math.ceil(entries.length / size)}
          </span>
          <button
            disabled={(page + 1) * size >= entries.length}
            onClick={() => setPage(page + 1)}
          >
            Next
          </button>
        </div>
      )}
      {!compact && !!session?.permissions.timers && (
        <form
          className="timer-form"
          onSubmit={(event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            void action("timer.create", {
              name: String(form.get("name") || "Timer"),
              duration_seconds: Number(form.get("minutes")) * 60,
            });
          }}
        >
          <label>
            Timer name
            <input
              name="name"
              placeholder="A moment for tea"
              maxLength={120}
              disabled={!allowed}
            />
          </label>
          <label>
            Minutes
            <input
              name="minutes"
              type="number"
              min="1"
              max="10080"
              defaultValue="10"
              required
              disabled={!allowed}
            />
          </label>
          <button type="submit" disabled={!allowed}>
            Start timer
          </button>
        </form>
      )}
    </section>
  );
}
