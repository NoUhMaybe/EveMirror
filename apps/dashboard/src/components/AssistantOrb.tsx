import { lazy, Suspense } from "react";
import { ErrorBoundary } from "./ErrorBoundary";

export type OrbProps = {
  phase: string;
  level: number;
  progress: number;
  quality: "low" | "balanced" | "high";
  reduced: boolean;
  intensity: number;
  metrics?: (fps: number) => void;
};
const OrbGL = lazy(() => import("../animations/OrbGL"));
export function StaticOrb({ phase }: { phase: string }) {
  return (
    <div className="static-orb" data-phase={phase} aria-hidden="true">
      <div />
      <div />
      <div />
      <i />
    </div>
  );
}
export function AssistantOrb(props: OrbProps) {
  const fallback = <StaticOrb phase={props.phase} />;
  return (
    <div
      className="orb-container"
      data-testid="orb"
      data-phase={props.phase}
      role="img"
      aria-label={`Eve: ${props.phase.toLowerCase().replaceAll("_", " ")}`}
    >
      {props.reduced ? (
        fallback
      ) : (
        <ErrorBoundary fallback={fallback}>
          <Suspense fallback={fallback}>
            <OrbGL {...props} />
          </Suspense>
        </ErrorBoundary>
      )}
    </div>
  );
}
