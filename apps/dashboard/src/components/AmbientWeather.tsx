import { useDashboard } from "../app/AppProvider";
import { value } from "../state/forecast";
import { WeatherIcon } from "./WeatherIcon";
export function AmbientWeather() {
  const { state } = useDashboard();
  const forecast = state.frame?.ambient_weather;
  if (!forecast)
    return (
      <div className="ambient empty">Weather available when connected</div>
    );
  return (
    <div className="ambient" data-testid="ambient-weather">
      <WeatherIcon condition={forecast.current.condition} />
      <div>
        <strong>{value(forecast.current.temperature, "°")}</strong>
        <span>{forecast.location.name.split(",")[0]}</span>
        <small>
          {state.network !== "online" || forecast.stale
            ? "Last known"
            : (forecast.current.condition ?? "Conditions unavailable")}
        </small>
      </div>
    </div>
  );
}
