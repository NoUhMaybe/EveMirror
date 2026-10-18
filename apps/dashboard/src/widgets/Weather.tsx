import { WeatherIcon } from "../components/WeatherIcon";
import { useDashboard } from "../app/AppProvider";
import {
  forecastFor,
  graphSegments,
  value,
  localTime,
} from "../state/forecast";
import type { View } from "../state/dashboard";

export default function Weather({ view }: { view: View }) {
  const { state, action, pending } = useDashboard();
  const forecast = forecastFor(
    state.frame?.application.weather ?? [],
    state.frame?.ambient_weather,
    view,
  );
  if (!forecast)
    return (
      <section className="widget empty-state" data-testid="weather">
        <p className="eyebrow">Weather</p>
        <h2>A clearer outlook, soon.</h2>
        <p>No forecast is available yet.</p>
        <button
          disabled={pending || state.network !== "online"}
          onClick={() => void action("weather.weekly")}
        >
          Get forecast
        </button>
      </section>
    );
  const unit =
    forecast.measurement_units.temperature ??
    (forecast.units === "imperial" ? "°F" : "°C");
  const daily = forecast.daily[0];
  const hours = forecast.hourly.filter((x) =>
    x.time.startsWith(daily?.date + "T"),
  );
  const paths = graphSegments(hours);
  const stale = forecast.stale || state.network !== "online";
  const today = new Intl.DateTimeFormat("en-CA", {
    timeZone: forecast.location.timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(Date.now() + state.offset));
  const currentIndex = hours.findIndex(
    (hour, i) =>
      Date.parse(hour.time) <= Date.now() + state.offset &&
      (i === hours.length - 1 ||
        Date.parse(hours[i + 1].time) > Date.now() + state.offset),
  );
  return (
    <section className="widget weather" data-testid="weather" data-view={view}>
      <div className="widget-heading">
        <div>
          <p className="eyebrow">{forecast.location.name}</p>
          <h2>
            {view === "weather_weekly"
              ? "The week ahead"
              : view === "weather_daily"
                ? "A day in detail"
                : "Right now"}
          </h2>
        </div>
        <span className={`source-badge ${stale ? "stale" : ""}`}>
          {stale ? "Last known" : "Forecast"}
        </span>
      </div>
      {view === "weather_weekly" ? (
        <div className="week-list">
          {forecast.daily.map((day, i) => (
            <div className="forecast-day" key={day.date}>
              <span className="day-name">
                {i === 0 && day.date === today
                  ? "Today"
                  : new Intl.DateTimeFormat(undefined, {
                      weekday: "short",
                      timeZone: "UTC",
                    }).format(new Date(day.date + "T12:00:00Z"))}
                <small>
                  {new Intl.DateTimeFormat(undefined, {
                    month: "short",
                    day: "numeric",
                    timeZone: "UTC",
                  }).format(new Date(day.date + "T12:00:00Z"))}
                </small>
              </span>
              <WeatherIcon condition={day.condition} />
              <span className="day-condition">
                {day.condition ?? "Unavailable"}
              </span>
              <span className="rain">
                {value(day.rain_probability_pct, "%")}
              </span>
              <span className="high-low">
                {value(day.high, "°")} <em>{value(day.low, "°")}</em>
              </span>
            </div>
          ))}
        </div>
      ) : (
        <>
          <div className="current-weather">
            <WeatherIcon condition={forecast.current.condition} />
            <strong>
              {view === "weather_daily"
                ? value(daily?.high, "°")
                : value(forecast.current.temperature, "°")}
              <small>{unit.slice(1)}</small>
            </strong>
            <div>
              <h3>
                {view === "weather_daily"
                  ? (daily?.condition ?? "Daily forecast")
                  : (forecast.current.condition ?? "Unavailable")}
              </h3>
              <p>
                High {value(daily?.high, "°")}{" "}
                <span>Low {value(daily?.low, "°")}</span>
              </p>
            </div>
          </div>
          {view === "weather_current" && (
            <dl className="weather-facts">
              <div>
                <dt>Feels like</dt>
                <dd>{value(forecast.current.feels_like, "°")}</dd>
              </div>
              <div>
                <dt>Humidity</dt>
                <dd>{value(forecast.current.humidity_pct, "%")}</dd>
              </div>
              <div>
                <dt>Wind</dt>
                <dd>
                  {value(forecast.current.wind_speed)}{" "}
                  <small>{forecast.measurement_units.wind_speed}</small>
                </dd>
              </div>
            </dl>
          )}
          {view === "weather_daily" && (
            <>
              <div className="hourly-chart">
                <svg
                  viewBox="-8 -10 636 178"
                  role="img"
                  aria-label="Hourly temperature forecast. Gaps indicate unavailable readings."
                >
                  {[0, 50, 100, 150].map((y) => (
                    <line
                      key={y}
                      x1="0"
                      x2="620"
                      y1={y}
                      y2={y}
                      className="chart-grid"
                    />
                  ))}
                  {paths.map((d, i) => (
                    <path key={i} d={d} className="chart-line" />
                  ))}
                  {currentIndex >= 0 && daily?.date === today && (
                    <line
                      x1={(currentIndex / Math.max(1, hours.length - 1)) * 620}
                      x2={(currentIndex / Math.max(1, hours.length - 1)) * 620}
                      y1="0"
                      y2="150"
                      className="chart-now"
                    />
                  )}
                </svg>
              </div>
              <div className="hour-labels">
                {hours
                  .filter(
                    (_, i) =>
                      i % Math.max(1, Math.floor(hours.length / 5)) === 0,
                  )
                  .slice(0, 6)
                  .map((hour) => (
                    <span key={hour.time}>
                      {localTime(hour.time, forecast.location.timezone)}
                      <small>
                        {value(hour.rain_probability_pct, "% rain")} ·{" "}
                        {value(hour.humidity_pct, "% RH")}
                      </small>
                    </span>
                  ))}
              </div>
              <dl className="weather-facts">
                <div>
                  <dt>Sunrise</dt>
                  <dd>
                    {localTime(
                      daily?.sunrise ?? null,
                      forecast.location.timezone,
                    )}
                  </dd>
                </div>
                <div>
                  <dt>Sunset</dt>
                  <dd>
                    {localTime(
                      daily?.sunset ?? null,
                      forecast.location.timezone,
                    )}
                  </dd>
                </div>
                <div>
                  <dt>Rain chance</dt>
                  <dd>{value(daily?.rain_probability_pct, "%")}</dd>
                </div>
              </dl>
            </>
          )}
        </>
      )}
      <p className="provenance">
        Open-Meteo · {unit} · Updated{" "}
        {localTime(forecast.fetched_at, forecast.location.timezone)}
        {stale ? " · Cached forecast" : ""}
      </p>
    </section>
  );
}
