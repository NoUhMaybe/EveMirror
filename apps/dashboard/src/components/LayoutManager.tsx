import { lazy, Suspense } from "react";
import { useDashboard } from "../app/AppProvider";
import { selectedView } from "../state/dashboard";

const Weather = lazy(() => import("../widgets/Weather"));
const Timers = lazy(() => import("../widgets/Timers"));
const Home = lazy(() => import("../widgets/Home"));
export function LayoutManager() {
  const { state } = useDashboard();
  const view = selectedView(state);
  const hasTimers = !!state.frame?.application.timers?.length;
  return (
    <section
      className={`context-space ${view === "default" && !hasTimers ? "ambient-only" : ""}`}
      data-testid="context"
      data-view={view}
    >
      <Suspense
        fallback={
          <p className="loading" role="status">
            Getting things ready…
          </p>
        }
      >
        {view.startsWith("weather_") && <Weather view={view} />}
        {view === "timers" && <Timers />}
        {view === "smart_home" && <Home />}
        {view === "media" && <Home media />}
        {view !== "timers" && hasTimers && <Timers compact />}
        {view === "default" && !hasTimers && (
          <p className="ambient-prompt">
            A quieter kind of connected.<span>Say “Hey Eve” to begin.</span>
          </p>
        )}
      </Suspense>
    </section>
  );
}
