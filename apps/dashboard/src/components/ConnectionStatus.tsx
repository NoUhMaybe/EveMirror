import { useDashboard } from "../app/AppProvider";

export function ConnectionStatus() {
  const { state } = useDashboard();
  const edge = state.frame?.voice.devices[0];
  const label =
    state.network === "online"
      ? edge?.connected
        ? "Connected"
        : "Mirror offline"
      : state.network === "unpaired"
        ? "Unpaired display"
        : state.network === "connecting"
          ? "Connecting"
          : "Reconnecting";
  return (
    <>
      <span
        className="connection"
        data-online={state.network === "online" && !!edge?.connected}
        role="status"
      >
        <i aria-hidden="true" />
        {label}
      </span>
      {state.network === "online" && state.frame?.presence && (
        <span className="presence-hint" data-testid="presence-status">
          {state.frame.presence.display === "asleep"
            ? "Backlight asleep"
            : state.frame.presence.display === "awake"
              ? "Backlight awake"
              : "Backlight unknown"}
          {state.frame.presence.reading?.health !== "healthy"
            ? " · sensor unknown"
            : ""}
        </span>
      )}
    </>
  );
}
