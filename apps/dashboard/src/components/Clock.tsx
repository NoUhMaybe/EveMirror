import { memo } from "react";
import { useClock } from "../hooks/useClock";

export const Clock = memo(function Clock() {
  const now = new Date(useClock());
  const time = new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(now);
  return (
    <div className="clock" data-testid="clock">
      <p className="eyebrow">
        {new Intl.DateTimeFormat(undefined, {
          weekday: "long",
          month: "long",
          day: "numeric",
        }).format(now)}
      </p>
      <time dateTime={now.toISOString()}>{time}</time>
      <span className="clock-caption">A little clarity for your day.</span>
    </div>
  );
});
