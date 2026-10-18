/** Legacy weather payload normalization. Missing values remain unavailable. */
export type WeatherHourPoint = {
  iso: string;
  hour: number;
  tempF: number;
  precipChancePct: number | null;
  humidityPct: number | null;
};

export type WeatherDayPoint = {
  date: string;
  highF: number | null;
  lowF: number | null;
  rainChancePct: number | null;
  condition: string;
};

export type WeatherTileData = {
  location: string;
  date: string;
  condition: string;
  hours: WeatherHourPoint[];
  week: WeatherDayPoint[];
  currentTempF: number | null;
  humidityPct: number | null;
  isMock: boolean;
  highIndex: number;
  lowIndex: number;
  sunriseHour: number | null;
  sunsetHour: number | null;
  currentHour: number;
  hasHistoricalBackfill: boolean;
  stale: boolean;
};

function record(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown> : null;
}

function number(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function percent(value: unknown): number | null {
  const n = number(value);
  return n !== null && n >= 0 && n <= 100 ? n : null;
}

function hour(value: unknown): number | null {
  if (typeof value !== "string") return null;
  // Open-Meteo timestamps carry location wall time; don't reinterpret in browser timezone.
  const match = /^\d{4}-\d{2}-\d{2}T([01]\d|2[0-3]):[0-5]\d/.exec(value);
  return match ? Number(match[1]) : null;
}

export function extractWeatherTileData(payload: Record<string, unknown>): WeatherTileData | null {
  const weather = record(record(payload.payload)?.weather);
  const today = record(weather?.today_detail);
  if (!weather || !today || typeof today.date !== "string") return null;
  const hours: WeatherHourPoint[] = [];
  for (const item of Array.isArray(today.hourly) ? today.hourly.slice(0, 25) : []) {
    const row = record(item);
    if (!row || row.backfilled === true || typeof row.time !== "string") continue;
    const h = hour(row.time);
    const temp = number(row.temperature_f);
    if (h === null || temp === null || !row.time.startsWith(today.date + "T")) continue;
    hours.push({ iso: row.time, hour: h, tempF: temp,
      precipChancePct: percent(row.precipitation_probability_pct),
      humidityPct: percent(row.relative_humidity_pct) });
  }
  hours.sort((a, b) => a.iso.localeCompare(b.iso));
  const week: WeatherDayPoint[] = [];
  for (const item of Array.isArray(weather.week_forecast) ? weather.week_forecast : []) {
    const row = record(item);
    if (!row || typeof row.date !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(row.date)) continue;
    week.push({ date: row.date, highF: number(row.high_f), lowF: number(row.low_f),
      rainChancePct: percent(row.rain_chance_pct),
      condition: typeof row.condition === "string" ? row.condition : "Unavailable" });
    if (week.length === 7) break;
  }
  let highIndex = 0, lowIndex = 0;
  hours.forEach((row, i) => {
    if (row.tempF > hours[highIndex].tempF) highIndex = i;
    if (row.tempF < hours[lowIndex].tempF) lowIndex = i;
  });
  return {
    location: typeof weather.location === "string" ? weather.location : "Unknown location",
    date: today.date, condition: typeof weather.condition === "string" ? weather.condition : "Unavailable",
    hours, week, currentTempF: number(weather.temperature_f), humidityPct: percent(weather.humidity_pct),
    isMock: false, highIndex, lowIndex, sunriseHour: hour(today.sunrise_iso), sunsetHour: hour(today.sunset_iso),
    currentHour: number(today.current_hour_local) ?? 0, hasHistoricalBackfill: false,
    stale: weather.stale === true,
  };
}

export function isValidWeatherTileData(value: unknown): value is WeatherTileData {
  const v = record(value);
  if (!v || typeof v.location !== "string" || typeof v.date !== "string" ||
      typeof v.condition !== "string" || !Array.isArray(v.hours) || !Array.isArray(v.week) ||
      v.hours.length > 25 || v.week.length > 7 || typeof v.isMock !== "boolean" ||
      typeof v.stale !== "boolean" || typeof v.hasHistoricalBackfill !== "boolean") return false;
  const nullableNumber = (n: unknown) => n === null || number(n) !== null;
  if (![v.currentTempF, v.humidityPct, v.sunriseHour, v.sunsetHour].every(nullableNumber) ||
      ![v.highIndex, v.lowIndex, v.currentHour].every(n => number(n) !== null)) return false;
  return v.hours.every(h => record(h) && typeof h.iso === "string" &&
      number(h.hour) !== null && number(h.tempF) !== null &&
      nullableNumber(h.precipChancePct) && nullableNumber(h.humidityPct)) &&
    v.week.every(d => record(d) && typeof d.date === "string" && typeof d.condition === "string" &&
      [d.highF, d.lowF, d.rainChancePct].every(nullableNumber));
}
