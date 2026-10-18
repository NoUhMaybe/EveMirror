import test from "node:test";
import assert from "node:assert/strict";
import { extractWeatherTileData, isValidWeatherTileData } from "../src/state/weather.ts";

function payload() {
  return {payload: {weather: {
    location: "Fixture city", temperature_f: 71, stale: false,
    today_detail: { date: "2026-10-17", current_hour_local: 16,
      hourly: [{time: "2026-10-17T16:00", temperature_f: 71},
        {time: "2026-10-17T17:00", temperature_f: null},
        {time: "2026-10-17T01:00", temperature_f: 70, backfilled: true}] },
    week_forecast: [{date: "2026-10-18", high_f: 79, low_f: 60, condition: "Rain"}],
  }}};
}

test("uses real weekly values without generating future measurements", () => {
  const result = extractWeatherTileData(payload());
  assert.equal(result.week.length, 1);
  assert.deepEqual(result.week[0], {date: "2026-10-18", highF: 79, lowF: 60,
    rainChancePct: null, condition: "Rain"});
  assert.ok(isValidWeatherTileData(result));
});

test("discards synthetic and missing temperatures, keeps absent percentages unavailable", () => {
  const result = extractWeatherTileData(payload());
  assert.equal(result.hours.length, 1);
  assert.equal(result.hours[0].tempF, 71);
  assert.equal(result.hours[0].hour, 16);
  assert.equal(result.hours[0].precipChancePct, null);
  assert.equal(result.hours[0].humidityPct, null);
});

test("invalid envelopes and old browser caches are rejected", () => {
  for (const value of [{}, {payload: null}, {payload: {weather: []}}]) {
    assert.equal(extractWeatherTileData(value), null);
  }
  assert.equal(isValidWeatherTileData({date: "2026-10-17", hours: []}), false);
  const good = extractWeatherTileData(payload());
  assert.equal(isValidWeatherTileData({...good, hours: [{tempF: Number.NaN}]}), false);
});

test("stale state and location wall time survive normalization", () => {
  const input = payload();
  input.payload.weather.stale = true;
  input.payload.weather.today_detail.hourly[0].time = "2026-10-17T16:00-05:00";
  const result = extractWeatherTileData(input);
  assert.equal(result.stale, true);
  assert.equal(result.hours[0].hour, 16);
});
