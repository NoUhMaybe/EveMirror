import { useEffect, useRef } from "react";
import { useDashboard } from "../app/AppProvider";
import { useClock } from "../hooks/useClock";

export function Subtitles() {
  const { state } = useDashboard();
  const now = useClock();
  const voice = state.voice;
  const visible =
    state.network === "online" && now + state.offset < voice.expires;
  const response = visible && voice.playing ? voice.response : "";
  const transcript =
    visible && !["IDLE", "FOLLOW_UP", "ERROR"].includes(voice.phase)
      ? voice.transcript
      : "";
  const words = response.split(/\s+/).filter(Boolean);
  const active =
    voice.samples > 0
      ? Math.min(
          words.length - 1,
          Math.floor((voice.position / voice.samples) * words.length),
        )
      : -1;
  const container = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const box = container.current;
    const word = box?.querySelectorAll("span")[Math.max(0, active)] as
      | HTMLElement
      | undefined;
    if (box && word)
      box.scrollTop = Math.max(
        0,
        word.offsetTop - box.offsetTop - box.clientHeight / 2,
      );
  }, [active, response]);
  return (
    <div
      ref={container}
      className="subtitles"
      data-testid="subtitles"
      aria-live="polite"
      aria-atomic="true"
    >
      {response ? (
        <p aria-label={response}>
          {words.map((word, i) => (
            <span key={i} className={i <= active ? "spoken" : ""}>
              {word}{" "}
            </span>
          ))}
        </p>
      ) : transcript ? (
        <p className="transcript">“{transcript}”</p>
      ) : (
        <p className="subtitle-placeholder">
          {state.network === "online" && voice.phase === "FOLLOW_UP"
            ? "You can keep talking. I'm listening."
            : ""}
        </p>
      )}
    </div>
  );
}
