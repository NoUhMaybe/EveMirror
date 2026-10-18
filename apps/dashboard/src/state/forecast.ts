import type { Forecast, Hour } from "../types/contracts";
import type { View } from "./dashboard";

export function forecastFor(
  application: Forecast[],
  ambient: Forecast | null | undefined,
  mode: View,
): Forecast | undefined {
  const selected = application.at(-1);
  if (mode === "weather_daily" && !selected?.hourly?.length)
    return ambient ?? selected;
  return mode === "weather_weekly" && (selected?.daily.length ?? 0) < 7
    ? (ambient ?? selected)
    : (selected ?? ambient ?? undefined);
}
export function graphSegments(
  hours: Hour[],
  width = 620,
  height = 150,
): string[] {
  const temperatures = hours
    .map((x) => x.temperature)
    .filter((x): x is number => x != null);
  if (!temperatures.length) return [];
  const min = Math.min(...temperatures) - 2,
    span = Math.max(...temperatures) - min + 2;
  const paths: string[] = [];
  let points = "";
  hours.forEach((hour, i) => {
    if (hour.temperature == null) {
      if (points) paths.push(points);
      points = "";
      return;
    }
    const x = (i / Math.max(1, hours.length - 1)) * width;
    const y = height - ((hour.temperature - min) / span) * height;
    points += `${points ? " L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`;
  });
  if (points) paths.push(points);
  return paths;
}

export const value = (number: number | null | undefined, unit = "") =>
  number == null ? "—" : `${Math.round(number)}${unit}`;
export const localTime = (iso: string | null, zone?: string) =>
  iso
    ? new Intl.DateTimeFormat(undefined, {
        hour: "numeric",
        minute: "2-digit",
        timeZone: zone,
      }).format(new Date(iso))
    : "—";
