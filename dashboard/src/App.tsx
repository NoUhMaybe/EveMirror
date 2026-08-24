import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useCallback, useEffect, useId, useMemo, useRef, useState, type CSSProperties } from "react";
import * as THREE from "three";

type EventEnvelope = {
  type: string;
  payload: Record<string, unknown>;
};

type StageLayout = {
  x: number;
  y: number;
  sphereScale: number;
  logoScale: number;
  logoOpacity: number;
  clockX: number;
  clockY: number;
  clockScale: number;
};

type SubtitleState = {
  words: string[];
  activeWord: number;
  visible: boolean;
};

type WeatherRefreshPhase = "idle" | "queued" | "requested" | "loaded" | "error";

type TilePresetId = "none" | "animation-only" | "large-default" | "large-weather-daily" | "large-weather-weekly" | "large-timer" | "triple-blank" | "quad-blank" | "double-blank";
type TileSize = "large" | "medium" | "compact";
type TileVariant = "blank" | "weather" | "weather-weekly" | "timer";
type BlankTilePresetId = Exclude<TilePresetId, "none" | "animation-only">;

type ClockParts = {
  hour: string;
  minute: string;
  dayLabel: string;
  dateLabel: string;
};

type WeatherHourPoint = {
  iso: string;
  hour: number;
  tempF: number;
  precipChancePct: number;
  humidityPct: number | null;
};

type WeatherTileData = {
  location: string;
  date: string;
  condition: string;
  hours: WeatherHourPoint[];
  currentTempF: number | null;
  humidityPct: number | null;
  isMock: boolean;
  highIndex: number;
  lowIndex: number;
  sunriseHour: number | null;
  sunsetHour: number | null;
  currentHour: number;
  hasHistoricalBackfill: boolean;
};

type LayoutPreset = "center" | "top" | "bottom" | "left" | "right" | "upper-right" | "upper-left";

const LAYOUT_PRESETS: Record<LayoutPreset, StageLayout> = {
  center: { x: 0, y: -0.42, sphereScale: 1.14, logoScale: 1, logoOpacity: 1, clockX: 0, clockY: 0.34, clockScale: 1.18 },
  top: { x: 0, y: 0.65, sphereScale: 0.88, logoScale: 0.94, logoOpacity: 1, clockX: 0, clockY: 0.34, clockScale: 1.18 },
  bottom: { x: 0, y: -0.65, sphereScale: 0.88, logoScale: 0.94, logoOpacity: 1, clockX: 0, clockY: 0.34, clockScale: 1.18 },
  left: { x: -0.72, y: 0, sphereScale: 0.86, logoScale: 0.92, logoOpacity: 1, clockX: 0, clockY: 0.34, clockScale: 1.18 },
  right: { x: 0.72, y: 0, sphereScale: 0.86, logoScale: 0.92, logoOpacity: 1, clockX: 0, clockY: 0.34, clockScale: 1.18 },
  "upper-right": { x: 0.62, y: 0.55, sphereScale: 0.8, logoScale: 0.9, logoOpacity: 1, clockX: 0, clockY: 0.34, clockScale: 1.18 },
  "upper-left": { x: -0.62, y: 0.55, sphereScale: 0.8, logoScale: 0.9, logoOpacity: 1, clockX: 0, clockY: 0.34, clockScale: 1.18 },
};

const TOOLS_DISPLAY_LAYOUT: Partial<StageLayout> = {
  x: -0.42,
  y: 0.69,
  sphereScale: 0.74,
  logoOpacity: 0,
  clockX: 0.36,
  clockY: 0.34,
  clockScale: 1.18,
};

const NODE_COUNT = 360;
const NODE_RADIUS = 1.55;
const EDGE_DISTANCE_THRESHOLD = 0.235;
const VIEW_MARGIN = 0.78;
const EFFECT_HEADROOM = 1.25;
const LAYOUT_MOVE_X = 0.45;
const LAYOUT_MOVE_Y = 0.4;
const LAYOUT_OVERLAY_MOVE_X_PERCENT = 43;
const LAYOUT_OVERLAY_MOVE_Y_PERCENT = 40;
const LAYOUT_CLOCK_TOP_BASE_PERCENT = 5.5;
const TOOLS_LAYOUT_ANIMATION_MS = 1650;
const TILE_SWITCH_FADE_MS = 260;
const TILE_SWITCH_MOVE_MS = 1800;
const EARLY_RELEASE_MS = 80;
const WEATHER_CACHE_STORAGE_KEY = "eve.dashboard.lastRealWeather.v1";
const TEST_UI_ENABLED =
  (import.meta.env.VITE_SHOW_TTS_TEST_UI ?? "0") === "1" ||
  (typeof window !== "undefined" && new URLSearchParams(window.location.search).get("ttsTest") === "1");
const LAYOUT_DEBUG_UI_ENABLED =
  (import.meta.env.VITE_SHOW_LAYOUT_DEBUG_UI ?? "0") === "1" ||
  (typeof window !== "undefined" && new URLSearchParams(window.location.search).get("layoutDebug") === "1");

function toFiniteNumber(value: unknown): number | null {
  if (typeof value !== "number" || !Number.isFinite(value)) return null;
  return value;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function roundToNearestFive(value: number): number {
  return clamp(Math.round(value / 5) * 5, 0, 100);
}

function estimateSpeechDurationMs(text: string, rate = 1): number {
  const trimmed = text.trim();
  if (!trimmed) return 0;

  const words = trimmed.split(/\s+/).length;
  const punctuationPauses = (trimmed.match(/[.,!?;:]/g) ?? []).length;
  const baseWps = 2.7 * Math.max(0.65, rate);
  const speechMs = (words / baseWps) * 1000;
  const pauseMs = punctuationPauses * 120;
  return Math.max(450, speechMs + pauseMs);
}

function scheduleSpeechEnd(deadlineMs: number | null, earlyReleaseMs: number): number | null {
  if (deadlineMs === null) return null;
  return performance.now() + Math.max(0, deadlineMs - earlyReleaseMs);
}

function getClockParts(now: Date): ClockParts {
  const hour24 = now.getHours();
  const hour12 = hour24 % 12 === 0 ? 12 : hour24 % 12;
  const hour = hour12.toString().padStart(2, "0");
  const minute = now.getMinutes().toString().padStart(2, "0");
  const dayLabel = now
    .toLocaleDateString("en-US", { weekday: "short" })
    .toUpperCase();
  const month = (now.getMonth() + 1).toString().padStart(2, "0");
  const day = now.getDate().toString().padStart(2, "0");
  const year = now.getFullYear();
  return {
    hour,
    minute,
    dayLabel,
    dateLabel: `${month}/${day}/${year}`,
  };
}

function parseLayoutPayload(payload: Record<string, unknown>, current: StageLayout): StageLayout {
  const presetRaw = payload.preset;
  const preset = typeof presetRaw === "string" ? (presetRaw as LayoutPreset) : null;
  const base = preset && LAYOUT_PRESETS[preset] ? LAYOUT_PRESETS[preset] : current;

  const x = toFiniteNumber(payload.mainX ?? payload.x);
  const y = toFiniteNumber(payload.mainY ?? payload.y);
  const sphereScale = toFiniteNumber(payload.sphereScale ?? payload.scale);
  const logoScale = toFiniteNumber(payload.logoScale);
  const logoOpacity = toFiniteNumber(payload.logoOpacity);
  const clockX = toFiniteNumber(payload.clockX);
  const clockY = toFiniteNumber(payload.clockY);
  const clockScale = toFiniteNumber(payload.clockScale);

  return {
    x: x === null ? base.x : clamp(x, -1.6, 1.6),
    y: y === null ? base.y : clamp(y, -1.6, 1.6),
    sphereScale: sphereScale === null ? base.sphereScale : clamp(sphereScale, 0.2, 2.2),
    logoScale: logoScale === null ? base.logoScale : clamp(logoScale, 0.2, 2.4),
    logoOpacity: logoOpacity === null ? base.logoOpacity : clamp(logoOpacity, 0, 1),
    clockX: clockX === null ? base.clockX : clamp(clockX, -1.6, 1.6),
    clockY: clockY === null ? base.clockY : clamp(clockY, -1.6, 1.6),
    clockScale: clockScale === null ? base.clockScale : clamp(clockScale, 0.35, 2.8),
  };
}

function easeInOutCubic(t: number): number {
  if (t < 0.5) return 4 * t * t * t;
  return 1 - Math.pow(-2 * t + 2, 3) / 2;
}

function interpolateLayout(from: StageLayout, to: StageLayout, t: number): StageLayout {
  return {
    x: THREE.MathUtils.lerp(from.x, to.x, t),
    y: THREE.MathUtils.lerp(from.y, to.y, t),
    sphereScale: THREE.MathUtils.lerp(from.sphereScale, to.sphereScale, t),
    logoScale: THREE.MathUtils.lerp(from.logoScale, to.logoScale, t),
    logoOpacity: THREE.MathUtils.lerp(from.logoOpacity, to.logoOpacity, t),
    clockX: THREE.MathUtils.lerp(from.clockX, to.clockX, t),
    clockY: THREE.MathUtils.lerp(from.clockY, to.clockY, t),
    clockScale: THREE.MathUtils.lerp(from.clockScale, to.clockScale, t),
  };
}

function parseHourFromIso(iso: string): number | null {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d.getHours();
}

function toNumberOrDefault(value: unknown, fallback: number): number {
  const n = toFiniteNumber(value);
  return n === null ? fallback : n;
}

function extractWeatherTileData(payload: Record<string, unknown>): WeatherTileData | null {
  const toolPayload = payload.payload;
  if (!toolPayload || typeof toolPayload !== "object") return null;
  const weatherRaw = (toolPayload as Record<string, unknown>).weather;
  if (!weatherRaw || typeof weatherRaw !== "object") return null;
  const weather = weatherRaw as Record<string, unknown>;
  const todayRaw = weather.today_detail;
  if (!todayRaw || typeof todayRaw !== "object") return null;
  const today = todayRaw as Record<string, unknown>;

  const hourlyRaw = Array.isArray(today.hourly) ? today.hourly : [];
  const hours: WeatherHourPoint[] = hourlyRaw
    .map((item) => {
      if (!item || typeof item !== "object") return null;
      const row = item as Record<string, unknown>;
      const iso = String(row.time ?? "");
      const parsedHour = parseHourFromIso(iso);
      if (!iso || parsedHour === null) return null;
      return {
        iso,
        hour: parsedHour,
        tempF: toNumberOrDefault(row.temperature_f, 0),
        precipChancePct: toNumberOrDefault(row.precipitation_probability_pct, 0),
        humidityPct: toFiniteNumber(row.relative_humidity_pct),
      };
    })
    .filter((v): v is WeatherHourPoint => v !== null);

  if (hours.length === 0) return null;

  const sunriseHour = (() => {
    const iso = String(today.sunrise_iso ?? "");
    if (!iso) return null;
    return parseHourFromIso(iso);
  })();
  const sunsetHour = (() => {
    const iso = String(today.sunset_iso ?? "");
    if (!iso) return null;
    return parseHourFromIso(iso);
  })();

  return {
    location: String(weather.location ?? "Frisco, Texas"),
    date: String(today.date ?? ""),
    condition: String(weather.condition ?? "Clear"),
    hours,
    currentTempF: toFiniteNumber(weather.temperature_f),
    humidityPct: toFiniteNumber(weather.humidity_pct),
    isMock: false,
    highIndex: Math.max(0, Math.min(hours.length - 1, Math.floor(toNumberOrDefault(today.high_index, 0)))),
    lowIndex: Math.max(0, Math.min(hours.length - 1, Math.floor(toNumberOrDefault(today.low_index, 0)))),
    sunriseHour,
    sunsetHour,
    currentHour: Math.max(0, Math.min(23, Math.floor(toNumberOrDefault(today.current_hour_local, new Date().getHours())))),
    hasHistoricalBackfill: Boolean(today.historical_backfill_available),
  };
}

function makeMockWeatherTileData(): WeatherTileData {
  const now = new Date();
  const date = now.toISOString().slice(0, 10);
  const hours: WeatherHourPoint[] = Array.from({ length: 24 }, (_, h) => {
    const tempF = 84 + Math.sin((h - 6) / 24 * Math.PI * 2) * 14 + (h > 13 && h < 18 ? 7 : 0);
    const precip = h >= 14 && h <= 19 ? Math.max(0, 48 - Math.abs(17 - h) * 11) : Math.max(0, 8 - Math.abs(8 - h) * 2);
    return {
      iso: `${date}T${h.toString().padStart(2, "0")}:00:00`,
      hour: h,
      tempF,
      precipChancePct: precip,
      humidityPct: Math.round(clamp(58 + Math.sin((h - 3) / 24 * Math.PI * 2) * 18, 20, 95)),
    };
  });

  let highIndex = 0;
  let lowIndex = 0;
  for (let i = 1; i < hours.length; i += 1) {
    if (hours[i].tempF > hours[highIndex].tempF) highIndex = i;
    if (hours[i].tempF < hours[lowIndex].tempF) lowIndex = i;
  }

  return {
    location: "Frisco, Texas",
    date,
    condition: "Clear",
    hours,
    currentTempF: Math.round(hours[Math.max(0, Math.min(hours.length - 1, now.getHours()))].tempF),
    humidityPct: 42,
    isMock: true,
    highIndex,
    lowIndex,
    sunriseHour: 7,
    sunsetHour: 20,
    currentHour: now.getHours(),
    hasHistoricalBackfill: false,
  };
}

function isValidWeatherTileData(value: unknown): value is WeatherTileData {
  if (!value || typeof value !== "object") return false;
  const v = value as Record<string, unknown>;
  if (typeof v.location !== "string") return false;
  if (typeof v.date !== "string") return false;
  if (!(typeof v.condition === "string" || v.condition === undefined)) return false;
  if (!Array.isArray(v.hours)) return false;
  if (typeof v.highIndex !== "number" || typeof v.lowIndex !== "number") return false;
  if (typeof v.currentHour !== "number") return false;
  if (typeof v.hasHistoricalBackfill !== "boolean") return false;
  if (typeof v.isMock !== "boolean") return false;

  for (const item of v.hours) {
    if (!item || typeof item !== "object") return false;
    const h = item as Record<string, unknown>;
    if (typeof h.iso !== "string") return false;
    if (typeof h.hour !== "number") return false;
    if (typeof h.tempF !== "number") return false;
    if (typeof h.precipChancePct !== "number") return false;
    if (!(typeof h.humidityPct === "number" || h.humidityPct === null)) return false;
  }

  const currentTempF = v.currentTempF;
  if (!(typeof currentTempF === "number" || currentTempF === null)) return false;
  const humidityPct = v.humidityPct;
  if (!(typeof humidityPct === "number" || humidityPct === null)) return false;

  const sunriseHour = v.sunriseHour;
  if (!(typeof sunriseHour === "number" || sunriseHour === null)) return false;
  const sunsetHour = v.sunsetHour;
  if (!(typeof sunsetHour === "number" || sunsetHour === null)) return false;

  return true;
}

function smoothReactiveValue(current: number, target: number, attack: number, release: number, maxStep: number): number {
  const rate = target > current ? attack : release;
  const eased = THREE.MathUtils.lerp(current, target, rate);
  const delta = clamp(eased - current, -maxStep, maxStep);
  const next = current + delta;
  return Math.abs(next) < 0.003 ? 0 : next;
}

function makeSpherePoints(count: number): Float32Array {
  const arr = new Float32Array(count * 3);
  const offset = 2 / count;
  const increment = Math.PI * (3 - Math.sqrt(5));

  for (let i = 0; i < count; i += 1) {
    const y = i * offset - 1 + offset / 2;
    const r = Math.sqrt(1 - y * y);
    const phi = i * increment;
    arr[i * 3] = Math.cos(phi) * r;
    arr[i * 3 + 1] = y;
    arr[i * 3 + 2] = Math.sin(phi) * r;
  }
  return arr;
}

function makeEdges(points: Float32Array): Array<[number, number]> {
  const out: Array<[number, number]> = [];
  const total = points.length / 3;
  const threshold2 = EDGE_DISTANCE_THRESHOLD * EDGE_DISTANCE_THRESHOLD;

  for (let i = 0; i < total; i += 1) {
    const ax = points[i * 3];
    const ay = points[i * 3 + 1];
    const az = points[i * 3 + 2];

    for (let j = i + 1; j < total; j += 1) {
      const bx = points[j * 3];
      const by = points[j * 3 + 1];
      const bz = points[j * 3 + 2];
      const dx = ax - bx;
      const dy = ay - by;
      const dz = az - bz;
      const d2 = dx * dx + dy * dy + dz * dz;
      if (d2 <= threshold2) {
        out.push([i, j]);
      }
    }
  }

  return out;
}

function SphereGraph({
  activity,
  audioLevel,
  audioBands,
  speechActive,
  layout,
}: {
  activity: number;
  audioLevel: number;
  audioBands: { low: number; high: number };
  speechActive: boolean;
  layout: StageLayout;
}) {
  const groupRef = useRef<THREE.Group>(null);
  const pointsRef = useRef<THREE.Points>(null);
  const pointsGeometryRef = useRef<THREE.BufferGeometry>(null);
  const lineGeometryRef = useRef<THREE.BufferGeometry>(null);
  const viewport = useThree((state) => state.viewport);

  const pointsMaterial = useMemo(
    () =>
      new THREE.ShaderMaterial({
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
        uniforms: {
          uNearSize: { value: 11.5 },
          uFarSize: { value: 1.15 },
          uNearAlpha: { value: 1.0 },
          uFarAlpha: { value: 0.08 },
          uNearColor: { value: new THREE.Color("#ffffff") },
          uFarColor: { value: new THREE.Color("#b5b5b5") },
          uDepthMin: { value: 4.2 },
          uDepthMax: { value: 9.2 },
        },
        vertexShader: `
          uniform float uNearSize;
          uniform float uFarSize;
          uniform float uDepthMin;
          uniform float uDepthMax;
          varying float vDepth;
          void main() {
            vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
            float depth = clamp((-mvPosition.z - uDepthMin) / (uDepthMax - uDepthMin), 0.0, 1.0);
            vDepth = depth;
            gl_PointSize = mix(uNearSize, uFarSize, depth);
            gl_Position = projectionMatrix * mvPosition;
          }
        `,
        fragmentShader: `
          uniform float uNearAlpha;
          uniform float uFarAlpha;
          uniform vec3 uNearColor;
          uniform vec3 uFarColor;
          varying float vDepth;
          void main() {
            vec2 c = gl_PointCoord - vec2(0.5);
            float r = length(c);
            if (r > 0.5) discard;
            float edge = smoothstep(0.5, 0.1, r);
            float alpha = mix(uNearAlpha, uFarAlpha, vDepth) * edge;
            vec3 color = mix(uNearColor, uFarColor, vDepth);
            gl_FragColor = vec4(color, alpha);
          }
        `,
      }),
    []
  );

  const linesMaterial = useMemo(
    () =>
      new THREE.ShaderMaterial({
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
        uniforms: {
          uNearAlpha: { value: 0.95 },
          uFarAlpha: { value: 0.05 },
          uNearColor: { value: new THREE.Color("#ffffff") },
          uFarColor: { value: new THREE.Color("#8f8f8f") },
          uDepthMin: { value: 4.2 },
          uDepthMax: { value: 9.2 },
        },
        vertexShader: `
          uniform float uDepthMin;
          uniform float uDepthMax;
          varying float vDepth;
          void main() {
            vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
            float depth = clamp((-mvPosition.z - uDepthMin) / (uDepthMax - uDepthMin), 0.0, 1.0);
            vDepth = depth;
            gl_Position = projectionMatrix * mvPosition;
          }
        `,
        fragmentShader: `
          uniform float uNearAlpha;
          uniform float uFarAlpha;
          uniform vec3 uNearColor;
          uniform vec3 uFarColor;
          varying float vDepth;
          void main() {
            float nearFactor = 1.0 - vDepth;
            float alpha = mix(uNearAlpha, uFarAlpha, vDepth) * (0.65 + 0.35 * nearFactor);
            vec3 color = mix(uNearColor, uFarColor, vDepth) * (0.62 + 0.38 * nearFactor);
            gl_FragColor = vec4(color, alpha);
          }
        `,
      }),
    []
  );

  const basePoints = useMemo(() => makeSpherePoints(NODE_COUNT), []);
  const edges = useMemo(() => makeEdges(basePoints), [basePoints]);
  const pointPositions = useMemo(() => new Float32Array(basePoints.length), [basePoints]);
  const edgePositions = useMemo(() => new Float32Array(edges.length * 2 * 3), [edges.length]);

  useMemo(() => {
    pointPositions.set(basePoints);
    for (let e = 0; e < edges.length; e += 1) {
      const [a, b] = edges[e];
      const p = e * 6;
      edgePositions[p] = basePoints[a * 3];
      edgePositions[p + 1] = basePoints[a * 3 + 1];
      edgePositions[p + 2] = basePoints[a * 3 + 2];
      edgePositions[p + 3] = basePoints[b * 3];
      edgePositions[p + 4] = basePoints[b * 3 + 1];
      edgePositions[p + 5] = basePoints[b * 3 + 2];
    }
  }, [basePoints, edges, edgePositions, pointPositions]);

  useFrame(({ clock }, delta) => {
    if (!groupRef.current || !pointsGeometryRef.current || !lineGeometryRef.current || !pointsRef.current) return;

    const t = clock.getElapsedTime();
    const effectiveActivity = Math.min(1, Math.max(0, activity));
    const effectiveAudio = Math.min(1, Math.max(0, audioLevel));
    const stateInfluence = speechActive ? effectiveActivity * 0.58 : effectiveActivity * 0.12;
    const effective = Math.max(stateInfluence, effectiveAudio);

    groupRef.current.rotation.y += delta * (0.16 + effectiveAudio * 0.36);
    groupRef.current.rotation.x = Math.sin(t * 0.28) * (0.1 + effectiveAudio * 0.1);

    const targetX = layout.x * viewport.width * LAYOUT_MOVE_X;
    const targetY = layout.y * viewport.height * LAYOUT_MOVE_Y;
    groupRef.current.position.x = targetX;
    groupRef.current.position.y = targetY;

    const halfMinView = Math.min(viewport.width, viewport.height) * 0.5;
    const safeRadius = halfMinView * VIEW_MARGIN;
    const reactiveScaleBoost = 1 + effective * 0.2;
    const targetScale = (safeRadius / (NODE_RADIUS * EFFECT_HEADROOM)) * layout.sphereScale * reactiveScaleBoost;
    groupRef.current.scale.setScalar(targetScale);

    const pointsAttr = pointsGeometryRef.current.getAttribute("position") as THREE.BufferAttribute;
    const points = pointsAttr.array as Float32Array;
    const lowBand = clamp(audioBands.low, 0, 1);
    const highBand = clamp(audioBands.high, 0, 1);

    for (let i = 0; i < points.length; i += 3) {
      const index = i / 3;
      const bx = basePoints[i];
      const by = basePoints[i + 1];
      const bz = basePoints[i + 2];

      const topWeight = clamp((by + 1) * 0.5, 0, 1);
      const bottomWeight = 1 - topWeight;

      const pulse = Math.sin(t * 1.14 + index * 0.17) * (0.078 * effective);
      const shimmer = Math.sin(t * 0.84 + index * 0.11) * 0.02;
      const voiceMod = (0.026 + Math.sin(t * 8.9 + index * 0.21) * 0.018) * effectiveAudio;
      const pitchBandMod = lowBand * bottomWeight * 0.18 + highBand * topWeight * 0.18;
      const radius = NODE_RADIUS * (1 + pulse + shimmer + voiceMod + pitchBandMod);

      points[i] = bx * radius;
      points[i + 1] = by * radius;
      points[i + 2] = bz * radius;
    }

    pointsAttr.needsUpdate = true;

    const lineAttr = lineGeometryRef.current.getAttribute("position") as THREE.BufferAttribute;
    const lines = lineAttr.array as Float32Array;
    for (let e = 0; e < edges.length; e += 1) {
      const [a, b] = edges[e];
      const p = e * 6;
      lines[p] = points[a * 3];
      lines[p + 1] = points[a * 3 + 1];
      lines[p + 2] = points[a * 3 + 2];
      lines[p + 3] = points[b * 3];
      lines[p + 4] = points[b * 3 + 1];
      lines[p + 5] = points[b * 3 + 2];
    }
    lineAttr.needsUpdate = true;
  });

  return (
    <group ref={groupRef} position={[0, 0, 0]}>
      <lineSegments frustumCulled={false}>
        <bufferGeometry ref={lineGeometryRef}>
          <bufferAttribute attach="attributes-position" args={[edgePositions, 3]} />
        </bufferGeometry>
        <primitive object={linesMaterial} attach="material" />
      </lineSegments>

      <points ref={pointsRef} frustumCulled={false}>
        <bufferGeometry ref={pointsGeometryRef}>
          <bufferAttribute attach="attributes-position" args={[pointPositions, 3]} />
        </bufferGeometry>
        <primitive object={pointsMaterial} attach="material" />
      </points>
    </group>
  );
}

function gradientColorFromTemp(tempF: number, mode: "line" | "area" = "line") {
  const lineAnchors = [
    { t: 32, c: { r: 140, g: 205, b: 255, a: 1.0 } },
    { t: 65, c: { r: 102, g: 214, b: 122, a: 1.0 } },
    { t: 85, c: { r: 255, g: 216, b: 92, a: 1.0 } },
    { t: 95, c: { r: 255, g: 105, b: 96, a: 1.0 } },
  ];
  const areaAnchors = [
    { t: 32, c: { r: 124, g: 188, b: 245, a: 0.62 } },
    { t: 65, c: { r: 92, g: 194, b: 114, a: 0.62 } },
    { t: 85, c: { r: 243, g: 201, b: 84, a: 0.62 } },
    { t: 95, c: { r: 238, g: 96, b: 89, a: 0.62 } },
  ];
  const anchors = mode === "area" ? areaAnchors : lineAnchors;

  const lerpColor = (
    a: { r: number; g: number; b: number; a: number },
    b: { r: number; g: number; b: number; a: number },
    ratio: number,
  ) => ({
    r: Math.round(a.r + (b.r - a.r) * ratio),
    g: Math.round(a.g + (b.g - a.g) * ratio),
    b: Math.round(a.b + (b.b - a.b) * ratio),
    a: a.a + (b.a - a.a) * ratio,
  });

  if (tempF <= anchors[0].t) {
    const c = anchors[0].c;
    return `rgba(${c.r},${c.g},${c.b},${c.a.toFixed(3)})`;
  }
  if (tempF >= anchors[anchors.length - 1].t) {
    const c = anchors[anchors.length - 1].c;
    return `rgba(${c.r},${c.g},${c.b},${c.a.toFixed(3)})`;
  }
  for (let i = 0; i < anchors.length - 1; i += 1) {
    const a = anchors[i];
    const b = anchors[i + 1];
    if (tempF >= a.t && tempF <= b.t) {
      const ratio = (tempF - a.t) / Math.max(0.0001, b.t - a.t);
      const c = lerpColor(a.c, b.c, clamp(ratio, 0, 1));
      return `rgba(${c.r},${c.g},${c.b},${c.a.toFixed(3)})`;
    }
  }
  const fallback = anchors[anchors.length - 1].c;
  return `rgba(${fallback.r},${fallback.g},${fallback.b},${fallback.a.toFixed(3)})`;
}

function ConditionIconPaths({ kind }: { kind: "sunny" | "partly-cloudy" | "rain" | "snow" | "storm" | "fog" }) {
  if (kind === "sunny") {
    return (
      <g style={{ transformOrigin: "64px 64px", animation: "weather-sun-pulse 3.4s ease-in-out infinite", color: "#FFD55A" }}>
        <circle cx="64" cy="64" r="27" className="weather-condition-fill" />
        <g className="weather-condition-stroke">
          <line x1="64" y1="10" x2="64" y2="28" />
          <line x1="64" y1="100" x2="64" y2="118" />
          <line x1="10" y1="64" x2="28" y2="64" />
          <line x1="100" y1="64" x2="118" y2="64" />
          <line x1="26" y1="26" x2="39" y2="39" />
          <line x1="89" y1="89" x2="102" y2="102" />
          <line x1="26" y1="102" x2="39" y2="89" />
          <line x1="89" y1="39" x2="102" y2="26" />
        </g>
      </g>
    );
  }
  if (kind === "partly-cloudy") {
    return (
      <>
        <g style={{ transformOrigin: "44px 44px", animation: "weather-sun-pulse 3.4s ease-in-out infinite", color: "#FFD55A" }}>
          <circle cx="44" cy="44" r="19" className="weather-condition-fill" />
        </g>
        <g style={{ animation: "weather-cloud-drift 5.5s ease-in-out infinite" }}>
          <path d="M36 84c-9.8 0-17.6-7.7-17.6-17.2 0-8.6 6.6-15.9 15.2-17 3-10 12.3-17.1 22.9-17.1 11.6 0 21.6 8.1 23.8 19.3h1.1c11.7 0 21 9.1 21 20.3 0 11.6-9.8 20.7-21.1 20.7H36Z" className="weather-condition-fill" />
        </g>
      </>
    );
  }
  if (kind === "rain") {
    return (
      <>
        <g style={{ animation: "weather-cloud-drift 6s ease-in-out infinite", color: "rgba(155,180,205,0.95)" }}>
          <path d="M30 74c-10.1 0-18.2-7.9-18.2-17.7 0-8.8 6.9-16.2 15.8-17.4 3.2-10.3 12.7-17.5 23.5-17.5 11.8 0 21.8 8.2 24.1 19.6h1.1c11.9 0 21.4 9.3 21.4 20.8 0 11.9-10 21.2-21.5 21.2H30Z" className="weather-condition-fill" />
        </g>
        <line x1="42" y1="80" x2="35" y2="96" stroke="rgba(100,180,230,0.95)" strokeWidth="6.5" strokeLinecap="round">
          <animate attributeName="y1" values="80;108" dur="1.3s" begin="0s" repeatCount="indefinite" calcMode="spline" keySplines="0.25 0 0.75 1" />
          <animate attributeName="y2" values="96;124" dur="1.3s" begin="0s" repeatCount="indefinite" calcMode="spline" keySplines="0.25 0 0.75 1" />
          <animate attributeName="opacity" values="0.9;0" dur="1.3s" begin="0s" repeatCount="indefinite" calcMode="spline" keySplines="0.15 0 0.85 1" />
        </line>
        <line x1="64" y1="80" x2="57" y2="96" stroke="rgba(100,180,230,0.95)" strokeWidth="6.5" strokeLinecap="round">
          <animate attributeName="y1" values="80;108" dur="1.3s" begin="0.43s" repeatCount="indefinite" calcMode="spline" keySplines="0.25 0 0.75 1" />
          <animate attributeName="y2" values="96;124" dur="1.3s" begin="0.43s" repeatCount="indefinite" calcMode="spline" keySplines="0.25 0 0.75 1" />
          <animate attributeName="opacity" values="0.9;0" dur="1.3s" begin="0.43s" repeatCount="indefinite" calcMode="spline" keySplines="0.15 0 0.85 1" />
        </line>
        <line x1="86" y1="80" x2="79" y2="96" stroke="rgba(100,180,230,0.95)" strokeWidth="6.5" strokeLinecap="round">
          <animate attributeName="y1" values="80;108" dur="1.3s" begin="0.86s" repeatCount="indefinite" calcMode="spline" keySplines="0.25 0 0.75 1" />
          <animate attributeName="y2" values="96;124" dur="1.3s" begin="0.86s" repeatCount="indefinite" calcMode="spline" keySplines="0.25 0 0.75 1" />
          <animate attributeName="opacity" values="0.9;0" dur="1.3s" begin="0.86s" repeatCount="indefinite" calcMode="spline" keySplines="0.15 0 0.85 1" />
        </line>
      </>
    );
  }
  if (kind === "snow") {
    return (
      <>
        <g style={{ animation: "weather-cloud-drift 7s ease-in-out infinite", color: "rgba(185,210,235,0.95)" }}>
          <path d="M30 74c-10.1 0-18.2-7.9-18.2-17.7 0-8.8 6.9-16.2 15.8-17.4 3.2-10.3 12.7-17.5 23.5-17.5 11.8 0 21.8 8.2 24.1 19.6h1.1c11.9 0 21.4 9.3 21.4 20.8 0 11.9-10 21.2-21.5 21.2H30Z" className="weather-condition-fill" />
        </g>
        <g style={{ animation: "weather-snow-fall-1 1.9s ease-in infinite" }} fill="none" stroke="rgba(210,235,255,0.95)" strokeWidth="6.5" strokeLinecap="round">
          <line x1="42" y1="87" x2="42" y2="101" />
          <line x1="35" y1="94" x2="49" y2="94" />
        </g>
        <g style={{ animation: "weather-snow-fall-2 1.9s ease-in infinite 0.63s" }} fill="none" stroke="rgba(210,235,255,0.95)" strokeWidth="6.5" strokeLinecap="round">
          <line x1="64" y1="87" x2="64" y2="101" />
          <line x1="57" y1="94" x2="71" y2="94" />
        </g>
        <g style={{ animation: "weather-snow-fall-1 1.9s ease-in infinite 1.26s" }} fill="none" stroke="rgba(210,235,255,0.95)" strokeWidth="6.5" strokeLinecap="round">
          <line x1="86" y1="87" x2="86" y2="101" />
          <line x1="79" y1="94" x2="93" y2="94" />
        </g>
      </>
    );
  }
  if (kind === "storm") {
    return (
      <>
        <g style={{ animation: "weather-cloud-drift 5s ease-in-out infinite", color: "rgba(105,120,140,0.95)" }}>
          <path d="M30 74c-10.1 0-18.2-7.9-18.2-17.7 0-8.8 6.9-16.2 15.8-17.4 3.2-10.3 12.7-17.5 23.5-17.5 11.8 0 21.8 8.2 24.1 19.6h1.1c11.9 0 21.4 9.3 21.4 20.8 0 11.9-10 21.2-21.5 21.2H30Z" className="weather-condition-fill" />
        </g>
        <path d="M66 80l-12 23h12l-7 17 20-27H66l8-13Z" fill="#FFE44D">
          <animate
            attributeName="opacity"
            values="0.65;0.65;0.65;0.65;1;0.15;1;0.65;0.65;0.65;0.65"
            keyTimes="0;0.25;0.5;0.68;0.71;0.73;0.76;0.79;0.88;0.95;1"
            dur="4.6s"
            repeatCount="indefinite"
          />
        </path>
      </>
    );
  }
  return (
    <>
      <path d="M22 44h84" className="weather-condition-stroke" style={{ animation: "weather-fog-a 4.8s ease-in-out infinite" }} />
      <path d="M14 58h100" className="weather-condition-stroke" style={{ animation: "weather-fog-b 5.3s ease-in-out infinite" }} />
      <path d="M22 72h84" className="weather-condition-stroke" style={{ animation: "weather-fog-a 4.8s ease-in-out infinite 1.4s" }} />
      <path d="M14 86h100" className="weather-condition-stroke" style={{ animation: "weather-fog-b 5.3s ease-in-out infinite 0.7s" }} />
    </>
  );
}

function WeatherTile({
  visible,
  size = "large",
  variant = "blank",
  weatherData,
  debugMaxPrecipBars = false,
  debugMaxHumidityBars = false,
  debugIconOverride = "auto",
  debugTempOverride = null,
  timerHours = 0,
  timerMinutes = 0,
  timerSeconds = 0,
}: {
  visible: boolean;
  size?: TileSize;
  variant?: TileVariant;
  weatherData?: WeatherTileData | null;
  debugMaxPrecipBars?: boolean;
  debugMaxHumidityBars?: boolean;
  debugIconOverride?: "auto" | "sunny" | "partly-cloudy" | "rain" | "snow" | "storm" | "fog";
  debugTempOverride?: number | null;
  timerHours?: number;
  timerMinutes?: number;
  timerSeconds?: number;
}) {
  if (!visible) return null;

  const isDailyWeatherTile = variant === "weather";
  const isWeeklyWeatherTile = variant === "weather-weekly";
  const isWeatherTile = isDailyWeatherTile || isWeeklyWeatherTile;

  const weatherGradientId = useId();
  const weatherAreaGradientId = useId();
  const [phase, setPhase] = useState(0);
  const tileRef = useRef<HTMLElement | null>(null);
  const graphRef = useRef<HTMLDivElement | null>(null);
  const [canvasSize, setCanvasSize] = useState({ width: 560, height: 320 });
  const [graphSize, setGraphSize] = useState({ width: 1, height: 1 });

  useEffect(() => {
    let rafId = 0;
    let last = performance.now();

    const tick = (now: number) => {
      const dt = Math.min(48, now - last);
      last = now;

      setPhase((p) => p + dt * 0.000012);
      rafId = window.requestAnimationFrame(tick);
    };

    rafId = window.requestAnimationFrame(tick);
    return () => window.cancelAnimationFrame(rafId);
  }, []);

  useEffect(() => {
    const el = tileRef.current;
    if (!el) return;

    const updateSize = () => {
      const rect = el.getBoundingClientRect();
      const width = Math.max(320, Math.round(rect.width));
      const height = Math.max(180, Math.round(rect.height));
      setCanvasSize((prev) => {
        if (prev.width === width && prev.height === height) return prev;
        return { width, height };
      });
    };

    updateSize();

    const observer = new ResizeObserver(updateSize);
    observer.observe(el);

    return () => {
      observer.disconnect();
    };
  }, []);

  useEffect(() => {
    const el = graphRef.current;
    if (!el) return;

    const updateSize = () => {
      const rect = el.getBoundingClientRect();
      const width = Math.max(1, rect.width);
      const height = Math.max(1, rect.height);
      setGraphSize((prev) => {
        if (prev.width === width && prev.height === height) return prev;
        return { width, height };
      });
    };

    updateSize();

    const observer = new ResizeObserver(updateSize);
    observer.observe(el);

    return () => {
      observer.disconnect();
    };
  }, []);

  const width = canvasSize.width;
  const height = canvasSize.height;
  const weatherGraphMetrics = useMemo(() => {
    const tileHeight = Math.max(180, canvasSize.height);
    const baseBarHeight = 34;
    const barsGap = 8;
    const tileBottomMargin = 34;
    const debugMaxScale = 0.68;

    // Keep humidity graph anchored to its existing row near 75% of the tile.
    const humidityTopPx = tileHeight * 0.75 - baseBarHeight / 2;
    const humidityMaxHeightPx = Math.max(baseBarHeight, tileHeight - tileBottomMargin - humidityTopPx);
    const sharedBarsMaxHeightPx = Math.max(baseBarHeight, humidityMaxHeightPx * debugMaxScale);

    return {
      baseBarHeight,
      barsGap,
      humidityTopPx,
      humidityMaxHeightPx,
      sharedBarsMaxHeightPx,
    };
  }, [canvasSize.height]);

  const graphEnvelopeHeightPx = weatherGraphMetrics.sharedBarsMaxHeightPx;
  const activePrecipBarHeightPx = graphEnvelopeHeightPx;
  const activeHumidityBarHeightPx = graphEnvelopeHeightPx;
  const weatherBarOpacityScale = 0.82;
  const fixedLabelBarHeightPx = weatherGraphMetrics.sharedBarsMaxHeightPx;

  const currentTimeOverlayInsetPx = 56;
  const precipTopPx = Math.max(
    0,
    weatherGraphMetrics.humidityTopPx - weatherGraphMetrics.barsGap - activePrecipBarHeightPx,
  );
  const fixedPrecipLabelTopPx = Math.max(
    0,
    weatherGraphMetrics.humidityTopPx - weatherGraphMetrics.barsGap - fixedLabelBarHeightPx,
  );

  const precipGraphStyle = useMemo(
    () => ({
      top: `${precipTopPx.toFixed(2)}px`,
      height: `${activePrecipBarHeightPx.toFixed(2)}px`,
    }) satisfies CSSProperties,
    [activePrecipBarHeightPx, precipTopPx],
  );
  const humidityGraphStyle = useMemo(
    () => ({
      top: `${weatherGraphMetrics.humidityTopPx.toFixed(2)}px`,
      height: `${activeHumidityBarHeightPx.toFixed(2)}px`,
    }) satisfies CSSProperties,
    [activeHumidityBarHeightPx, weatherGraphMetrics.humidityTopPx],
  );
  const precipLabelStyle = useMemo(
    () => ({
      top: `${fixedPrecipLabelTopPx.toFixed(2)}px`,
      height: `${fixedLabelBarHeightPx.toFixed(2)}px`,
    }) satisfies CSSProperties,
    [fixedLabelBarHeightPx, fixedPrecipLabelTopPx],
  );
  const humidityLabelStyle = useMemo(
    () => ({
      top: `${weatherGraphMetrics.humidityTopPx.toFixed(2)}px`,
      height: `${fixedLabelBarHeightPx.toFixed(2)}px`,
    }) satisfies CSSProperties,
    [fixedLabelBarHeightPx, weatherGraphMetrics.humidityTopPx],
  );
  const currentTimeOverlayStyle = useMemo(
    () =>
      ({
        top: `${currentTimeOverlayInsetPx.toFixed(2)}px`,
        bottom: `${currentTimeOverlayInsetPx.toFixed(2)}px`,
      }) satisfies CSSProperties,
    [currentTimeOverlayInsetPx],
  );
  const currentTimeEchoes = useMemo(
    () => [
      { key: "1", drift: 0.75, begin: "-0.6s", dur: "10.5s" },
      { key: "2", drift: 1.5, begin: "-3.9s", dur: "10.5s" },
      { key: "3", drift: 2.25, begin: "-7.2s", dur: "10.5s" },
    ],
    [],
  );

  const inset = 10;
  const innerW = width - inset * 2;
  const innerH = height - inset * 2;
  const cornerRadius = Math.min(18, innerW * 0.16, innerH * 0.16);

  const straightW = Math.max(0, innerW - cornerRadius * 2);
  const straightH = Math.max(0, innerH - cornerRadius * 2);
  const arcLen = (Math.PI * cornerRadius) / 2;
  const perimeter = 2 * (straightW + straightH) + 4 * arcLen;
  const totalNodeCount = Math.max(40, Math.round(perimeter / 28));
  const nodeCount = Math.max(16, Math.round(totalNodeCount * 0.4375));
  const reverseNodeCount = Math.max(20, totalNodeCount - nodeCount);

  const pointAtPerimeter = (t: number) => {
    const tt = ((t % 1) + 1) % 1;
    const p = 2 * (straightW + straightH) + 4 * arcLen;
    const d = tt * p;
    const left = inset;
    const right = inset + innerW;
    const top = inset;
    const bottom = inset + innerH;

    if (d < straightW) {
      return { x: left + cornerRadius + d, y: top, nx: 0, ny: 1 };
    }

    if (d < straightW + arcLen) {
      const u = (d - straightW) / arcLen;
      const theta = -Math.PI / 2 + u * (Math.PI / 2);
      const cx = right - cornerRadius;
      const cy = top + cornerRadius;
      const cosT = Math.cos(theta);
      const sinT = Math.sin(theta);
      return {
        x: cx + cornerRadius * cosT,
        y: cy + cornerRadius * sinT,
        nx: -cosT,
        ny: -sinT,
      };
    }

    if (d < straightW + arcLen + straightH) {
      const offset = d - (straightW + arcLen);
      return { x: right, y: top + cornerRadius + offset, nx: -1, ny: 0 };
    }

    if (d < straightW + arcLen + straightH + arcLen) {
      const u = (d - (straightW + arcLen + straightH)) / arcLen;
      const theta = u * (Math.PI / 2);
      const cx = right - cornerRadius;
      const cy = bottom - cornerRadius;
      const cosT = Math.cos(theta);
      const sinT = Math.sin(theta);
      return {
        x: cx + cornerRadius * cosT,
        y: cy + cornerRadius * sinT,
        nx: -cosT,
        ny: -sinT,
      };
    }

    if (d < straightW + arcLen + straightH + arcLen + straightW) {
      const offset = d - (straightW + arcLen + straightH + arcLen);
      return { x: right - cornerRadius - offset, y: bottom, nx: 0, ny: -1 };
    }

    if (d < straightW + arcLen + straightH + arcLen + straightW + arcLen) {
      const u = (d - (straightW + arcLen + straightH + arcLen + straightW)) / arcLen;
      const theta = Math.PI / 2 + u * (Math.PI / 2);
      const cx = left + cornerRadius;
      const cy = bottom - cornerRadius;
      const cosT = Math.cos(theta);
      const sinT = Math.sin(theta);
      return {
        x: cx + cornerRadius * cosT,
        y: cy + cornerRadius * sinT,
        nx: -cosT,
        ny: -sinT,
      };
    }

    if (d < straightW + arcLen + straightH + arcLen + straightW + arcLen + straightH) {
      const offset = d - (straightW + arcLen + straightH + arcLen + straightW + arcLen);
      return { x: left, y: bottom - cornerRadius - offset, nx: 1, ny: 0 };
    }

    const u = (d - (straightW + arcLen + straightH + arcLen + straightW + arcLen + straightH)) / arcLen;
    const theta = Math.PI + u * (Math.PI / 2);
    const cx = left + cornerRadius;
    const cy = top + cornerRadius;
    const cosT = Math.cos(theta);
    const sinT = Math.sin(theta);
    return {
      x: cx + cornerRadius * cosT,
      y: cy + cornerRadius * sinT,
      nx: -cosT,
      ny: -sinT,
    };
  };

  const buildPerimeterPoints = (count: number, direction: 1 | -1, seed: number) => {
    return Array.from({ length: count }, (_, i) => {
      const idx = i + seed;
      const speedMod = 0.72 + (Math.sin(idx * 1.73) + 1) * 0.38;
      const localFreq = 0.55 + ((Math.sin(idx * 4.13) + 1) * 0.5) * 1.9;
      const localAmp = 0.03 + ((Math.sin(idx * 2.11 + 1.7) + 1) * 0.5) * 0.09;
      const localWarp = Math.sin(phase * Math.PI * 2 * localFreq + idx * 0.93) * localAmp;
      const homeT = i / count;
      const driftT = homeT + direction * (phase * speedMod + localWarp);

      // Each particle has its own staggered fade/respawn window so they never reset together.
      const life = (phase * 0.42 + idx * 0.037) % 1;
      const fadeOutStart = 0.78;
      const fadeOutEnd = 0.9;
      const hiddenEnd = 0.95;
      let alpha = 1;
      let t = driftT;

      if (life >= fadeOutStart && life < fadeOutEnd) {
        alpha = 1 - (life - fadeOutStart) / (fadeOutEnd - fadeOutStart);
      } else if (life >= fadeOutEnd && life < hiddenEnd) {
        alpha = 0;
        t = homeT;
      } else if (life >= hiddenEnd) {
        alpha = (life - hiddenEnd) / (1 - hiddenEnd);
        t = homeT;
      }

      const base = pointAtPerimeter(t);
      const wobblePrimary = Math.sin(direction * phase * Math.PI * 11.5 + idx * 1.91);
      const wobbleSecondary = Math.sin(direction * phase * Math.PI * 17.8 + idx * 0.73 + 0.8);
      const wobble = wobblePrimary * 0.72 + wobbleSecondary * 0.42;
      const amp = 3.2 + ((Math.sin(idx * 2.37) + 1) * 0.5) * 4.4;
      const offset = wobble * amp;
      return {
        x: base.x + base.nx * offset,
        y: base.y + base.ny * offset,
        alpha,
      };
    });
  };

  const points = useMemo(() => buildPerimeterPoints(nodeCount, 1, 0), [nodeCount, phase, width, height]);
  const reversePoints = useMemo(
    () => buildPerimeterPoints(reverseNodeCount, -1, 1000),
    [reverseNodeCount, phase, width, height]
  );
  const allPoints = useMemo(() => [...points, ...reversePoints], [points, reversePoints]);

  const buildNearestEdges = useCallback((sourcePoints: Array<{ x: number; y: number }>) => {
    const out: Array<{ a: number; b: number; dist2: number }> = [];
    const maxEdgeDist2 = 2700;
    for (let i = 0; i < sourcePoints.length; i += 1) {
      const ax = sourcePoints[i].x;
      const ay = sourcePoints[i].y;
      const nearest: Array<{ j: number; d2: number }> = [];
      for (let j = 0; j < sourcePoints.length; j += 1) {
        if (i === j) continue;
        const dx = ax - sourcePoints[j].x;
        const dy = ay - sourcePoints[j].y;
        const d2 = dx * dx + dy * dy;
        nearest.push({ j, d2 });
      }
      nearest.sort((l, r) => l.d2 - r.d2);
      for (let k = 0; k < 2 && k < nearest.length; k += 1) {
        const n = nearest[k];
        if (n.d2 > maxEdgeDist2) continue;
        const a = Math.min(i, n.j);
        const b = Math.max(i, n.j);
        if (!out.some((e) => e.a === a && e.b === b)) {
          out.push({ a, b, dist2: n.d2 });
        }
      }
    }
    return out;
  }, []);

  const nearestEdges = useMemo(() => buildNearestEdges(allPoints), [allPoints, buildNearestEdges]);

  const nearestHourPoint = useMemo(() => {
    if (!weatherData || weatherData.hours.length === 0) return null;
    let best = weatherData.hours[0];
    let bestDelta = Math.abs(best.hour - weatherData.currentHour);
    for (let i = 1; i < weatherData.hours.length; i += 1) {
      const candidate = weatherData.hours[i];
      const delta = Math.abs(candidate.hour - weatherData.currentHour);
      if (delta < bestDelta) {
        best = candidate;
        bestDelta = delta;
      }
    }
    return best;
  }, [weatherData]);

  const currentTempF = useMemo(() => {
    if (variant === "weather" && weatherData?.isMock) return null;
    if (typeof debugTempOverride === "number" && Number.isFinite(debugTempOverride)) {
      return Math.round(debugTempOverride);
    }
    if (weatherData?.currentTempF !== null && weatherData?.currentTempF !== undefined) {
      return Math.round(weatherData.currentTempF);
    }
    if (!nearestHourPoint) return null;
    return Math.round(nearestHourPoint.tempF);
  }, [debugTempOverride, nearestHourPoint, variant, weatherData]);

  const highTempF = useMemo(() => {
    if (variant === "weather" && weatherData?.isMock) return null;
    if (!weatherData || weatherData.hours.length === 0) return null;
    const idx = Math.max(0, Math.min(weatherData.hours.length - 1, weatherData.highIndex));
    return Math.round(weatherData.hours[idx].tempF);
  }, [variant, weatherData]);

  const lowTempF = useMemo(() => {
    if (variant === "weather" && weatherData?.isMock) return null;
    if (!weatherData || weatherData.hours.length === 0) return null;
    const idx = Math.max(0, Math.min(weatherData.hours.length - 1, weatherData.lowIndex));
    return Math.round(weatherData.hours[idx].tempF);
  }, [variant, weatherData]);

  const precipPct = useMemo(() => {
    if (variant === "weather" && weatherData?.isMock) return null;
    if (!nearestHourPoint) return null;
    return roundToNearestFive(nearestHourPoint.precipChancePct);
  }, [nearestHourPoint, variant, weatherData]);

  const humidityPct = useMemo(() => {
    if (variant === "weather" && weatherData?.isMock) return null;
    if (weatherData?.humidityPct === null || weatherData?.humidityPct === undefined) return null;
    return Math.round(weatherData.humidityPct);
  }, [variant, weatherData]);

  const weeklyForecastRows = useMemo(() => {
    if (!isWeeklyWeatherTile) {
      return [] as Array<{
        key: string;
        dayLabel: string;
        tempF: number | null;
        highF: number | null;
        lowF: number | null;
        precipPct: number | null;
        humidityPct: number | null;
      }>;
    }

    const baseTemp = currentTempF;
    const baseHigh = highTempF;
    const baseLow = lowTempF;
    const basePrecip = precipPct;
    const baseHumidity = humidityPct;
    const today = new Date();

    return Array.from({ length: 6 }, (_, idx) => {
      const dayOffset = idx + 1;
      const d = new Date(today);
      d.setDate(today.getDate() + dayOffset);

      const drift = Math.round(Math.sin(dayOffset * 1.37) * 4 + Math.cos(dayOffset * 0.73) * 2);
      const temp = baseTemp === null ? null : Math.round(baseTemp + drift);
      const highDelta = Math.max(2, Math.round(5 + Math.sin(dayOffset * 0.8) * 2));
      const lowDelta = Math.max(2, Math.round(6 + Math.cos(dayOffset * 0.9) * 2));
      const hi = temp === null ? baseHigh : temp + highDelta;
      const lo = temp === null ? baseLow : temp - lowDelta;

      const p = basePrecip === null
        ? null
        : roundToNearestFive(clamp(basePrecip + Math.round(Math.sin(dayOffset * 1.4) * 18), 0, 100));
      const h = baseHumidity === null
        ? null
        : clamp(Math.round(baseHumidity + Math.round(Math.cos(dayOffset * 1.1) * 12)), 0, 100);

      return {
        key: `weekly-${dayOffset}`,
        dayLabel: d.toLocaleDateString("en-US", { weekday: "short" }).toUpperCase(),
        tempF: temp,
        highF: hi,
        lowF: lo,
        precipPct: p,
        humidityPct: h,
      };
    });
  }, [currentTempF, highTempF, humidityPct, isWeeklyWeatherTile, lowTempF, precipPct]);

  const isTripleDigitTemp = useMemo(() => {
    if (currentTempF === null || currentTempF === undefined) return false;
    return Math.abs(currentTempF) >= 100;
  }, [currentTempF]);

  const conditionVisual = useMemo(() => {
    if (debugIconOverride !== "auto") {
      const labels: Record<"sunny" | "partly-cloudy" | "rain" | "snow" | "storm" | "fog", string> = {
        sunny: "Sunny",
        "partly-cloudy": "Partly Cloudy",
        rain: "Rain",
        snow: "Snow",
        storm: "Thunderstorm",
        fog: "Fog",
      };
      return {
        kind: debugIconOverride,
        label: labels[debugIconOverride],
      };
    }

    const raw = (weatherData?.condition ?? "").toLowerCase();
    const has = (terms: string[]) => terms.some((t) => raw.includes(t));

    if (has(["thunder", "storm", "lightning"])) return { kind: "storm", label: "Thunderstorm" };
    if (has(["snow", "sleet", "blizzard", "flurr", "ice"])) return { kind: "snow", label: "Snow" };
    if (has(["rain", "drizzle", "showers", "shower"])) return { kind: "rain", label: "Rain" };
    if (has(["fog", "mist", "haze", "smoke"])) return { kind: "fog", label: "Fog" };
    if (has(["partly", "mostly", "cloud"])) return { kind: "partly-cloudy", label: "Partly Cloudy" };
    if (has(["clear", "sun", "fair"])) return { kind: "sunny", label: "Sunny" };

    return { kind: "partly-cloudy", label: weatherData?.condition || "Clear" };
  }, [debugIconOverride, weatherData?.condition]);

  const markerAspectRatioComp = useMemo(() => {
    if (graphSize.width <= 0) return 1;
    return graphSize.height / graphSize.width;
  }, [graphSize.height, graphSize.width]);

  const weatherGraphData = useMemo(() => {
    if (!isDailyWeatherTile || !weatherData || weatherData.hours.length === 0) {
      return {
        areaPoints: "",
        linePoints: "",
        markers: [] as Array<Record<string, string | number>>,
        gradientStops: [] as Array<{ offset: number; color: string }>,
        areaGradientStops: [] as Array<{ offset: number; color: string }>,
        lineBasePoints: [] as Array<{ x: number; y: number; tempF: number }>,
      };
    }

    const graphW = 100;
    const graphH = 100;
    const topPad = 8;
    const bottomPad = 8;

    const sorted = [...weatherData.hours].sort((a, b) => a.hour - b.hour);
    const wrapped = [...sorted, { ...sorted[0], hour: 24 }];
    const hourToTemp = new Map<number, number>();
    for (const row of sorted) {
      hourToTemp.set(row.hour, row.tempF);
    }

    const temps = wrapped.map((h) => h.tempF);
    const minTemp = Math.min(...temps);
    const maxTemp = Math.max(...temps);
    const span = Math.max(1, maxTemp - minTemp);

    const toX = (hour: number) => (hour / 24) * graphW;
    const toY = (tempF: number) => {
      const normalized = (tempF - minTemp) / span;
      return graphH - bottomPad - normalized * (graphH - topPad - bottomPad);
    };

    const getTempAtHour = (hour: number) => {
      const clampedHour = clamp(hour, 0, 24);
      if (Math.abs(clampedHour - 24) < 0.0001) {
        return sorted[0].tempF;
      }

      const roundedHour = Math.round(clampedHour);
      if (Math.abs(clampedHour - roundedHour) < 0.0001 && hourToTemp.has(roundedHour)) {
        return hourToTemp.get(roundedHour) ?? sorted[0].tempF;
      }

      const lower = Math.floor(clampedHour);
      const upper = (lower + 1) % 24;
      const lowerTemp = hourToTemp.get(lower) ?? sorted[0].tempF;
      const upperTemp = hourToTemp.get(upper) ?? lowerTemp;
      const frac = clampedHour - lower;
      return lowerTemp + (upperTemp - lowerTemp) * frac;
    };

    const markers: Array<Record<string, string | number>> = [];

    const highHourPoint = weatherData.hours[Math.max(0, Math.min(weatherData.hours.length - 1, weatherData.highIndex))];
    const lowHourPoint = weatherData.hours[Math.max(0, Math.min(weatherData.hours.length - 1, weatherData.lowIndex))];

    if (highHourPoint) {
      markers.push({
        kind: "standard",
        key: "high",
        x: toX(highHourPoint.hour),
        y: toY(highHourPoint.tempF),
        fill: gradientColorFromTemp(highHourPoint.tempF),
        stroke: "rgba(255,255,255,0.9)",
        strokeWidth: 0.45,
        r: 2.1,
      });
    }

    if (lowHourPoint) {
      markers.push({
        kind: "standard",
        key: "low",
        x: toX(lowHourPoint.hour),
        y: toY(lowHourPoint.tempF),
        fill: gradientColorFromTemp(lowHourPoint.tempF),
        stroke: "rgba(255,255,255,0.9)",
        strokeWidth: 0.45,
        r: 2.1,
      });
    }

    if (weatherData.sunriseHour !== null && weatherData.sunriseHour !== undefined) {
      const sunriseTemp = getTempAtHour(weatherData.sunriseHour);
      markers.push({
        kind: "sunrise",
        key: "sunrise",
        x: toX(weatherData.sunriseHour),
        y: toY(sunriseTemp),
        fill: "rgba(255,255,255,1)",
        stroke: "rgba(255,255,255,0)",
        strokeWidth: 0,
        r: 1.85,
      });
    }

    if (weatherData.sunsetHour !== null && weatherData.sunsetHour !== undefined) {
      const sunsetTemp = getTempAtHour(weatherData.sunsetHour);
      markers.push({
        kind: "sunset",
        key: "sunset",
        x: toX(weatherData.sunsetHour),
        y: toY(sunsetTemp),
        fill: "rgba(0,0,0,1)",
        ring: "rgba(255,255,255,1)",
        ringR: 2.55,
        r: 1.85,
      });
    }

    const linePoints = wrapped
      .map((h) => {
        const x = toX(h.hour);
        const y = toY(h.tempF);
        return `${x.toFixed(2)},${y.toFixed(2)}`;
      })
      .join(" ");
    const lineBasePoints = wrapped.map((h) => ({ x: toX(h.hour), y: toY(h.tempF), tempF: h.tempF }));

    const sampleCount = 192;
    const gradientStops = Array.from({ length: sampleCount + 1 }, (_, i) => {
      const hour = (i / sampleCount) * 24;
      return {
        offset: clamp((hour / 24) * 100, 0, 100),
        color: gradientColorFromTemp(getTempAtHour(hour), "line"),
      };
    });
    const areaGradientStops = Array.from({ length: sampleCount + 1 }, (_, i) => {
      const hour = (i / sampleCount) * 24;
      return {
        offset: clamp((hour / 24) * 100, 0, 100),
        color: gradientColorFromTemp(getTempAtHour(hour), "area"),
      };
    });

    const areaPoints = `${linePoints} ${graphW.toFixed(2)},${graphH.toFixed(2)} 0.00,${graphH.toFixed(2)}`;

    return { areaPoints, linePoints, lineBasePoints, markers, gradientStops, areaGradientStops };
  }, [isDailyWeatherTile, weatherData]);

  const weatherPrecipBars = useMemo(() => {
    if (variant !== "weather" || !weatherData || weatherData.hours.length === 0) {
      return [] as Array<{ x: number; w: number; h: number; opacity: number }>;
    }

    const sorted = [...weatherData.hours].sort((a, b) => a.hour - b.hour);
    const values = sorted.map((h) => clamp(roundToNearestFive(Math.max(0, h.precipChancePct)), 0, 100));

    const slot = 100 / 24;
    const barW = slot * 0.58;
    const minBar = 0.65;
    const maxBar = activePrecipBarHeightPx;

    if (debugMaxPrecipBars) {
      return sorted.map((h) => {
        const centerX = (h.hour / 24) * 100;
        return {
          x: centerX - barW / 2,
          w: barW,
          h: maxBar,
          opacity: 0.9,
        };
      });
    }

    return sorted.map((h, i) => {
      const centerX = (h.hour / 24) * 100;
      const chance = values[i];
      const normalized = chance / 100;
      const hPx = minBar + normalized * (maxBar - minBar);
      return {
        x: centerX - barW / 2,
        w: barW,
        h: hPx,
        opacity: chance <= 0 ? 0.22 : 0.42 + normalized * 0.48,
      };
    });
  }, [activePrecipBarHeightPx, debugMaxPrecipBars, variant, weatherData]);

  const weatherHumidityBars = useMemo(() => {
    if (variant !== "weather" || !weatherData || weatherData.hours.length === 0) {
      return [] as Array<{ x: number; w: number; h: number; opacity: number }>;
    }

    const sorted = [...weatherData.hours].sort((a, b) => a.hour - b.hour);
    const values = sorted.map((h) => clamp(roundToNearestFive(Math.max(0, h.humidityPct ?? 0)), 0, 100));

    const slot = 100 / 24;
    const barW = slot * 0.58;
    const minBar = 0.65;
    const maxBar = activeHumidityBarHeightPx;

    if (debugMaxHumidityBars) {
      return sorted.map((h) => {
        const centerX = (h.hour / 24) * 100;
        return {
          x: centerX - barW / 2,
          w: barW,
          h: maxBar,
          opacity: 0.9,
        };
      });
    }

    return sorted.map((h, i) => {
      const centerX = (h.hour / 24) * 100;
      const humidity = values[i];
      const normalized = humidity / 100;
      const hPx = minBar + normalized * (maxBar - minBar);
      return {
        x: centerX - barW / 2,
        w: barW,
        h: hPx,
        opacity: humidity <= 0 ? 0.22 : 0.42 + normalized * 0.48,
      };
    });
  }, [activeHumidityBarHeightPx, debugMaxHumidityBars, variant, weatherData]);

  const currentDayProgressPct = useMemo(() => {
    if (variant !== "weather") return 0;
    const now = new Date();
    const hour = now.getHours() + now.getMinutes() / 60 + now.getSeconds() / 3600;
    return clamp((hour / 24) * 100, 0, 100);
  }, [variant]);

  const edgeFadePercent = 7;
  const getEdgeFadeOpacity = (offsetPct: number) => {
    const left = clamp(offsetPct / edgeFadePercent, 0, 1);
    const right = clamp((100 - offsetPct) / edgeFadePercent, 0, 1);
    const t = Math.min(left, right);
    // Smoothstep keeps the center fully visible while softening fade transitions at the edges.
    return t * t * (3 - 2 * t);
  };

  const getBarWaveShading = (barIndex: number, totalBars: number) => {
    const safeTotal = Math.max(1, totalBars);
    // Drive position directly from phase — no modulo so there is never a discontinuous wrap jump.
    const patternPos = barIndex / 24 - phase * 8.6;

    const primary = Math.sin(patternPos * Math.PI * 2 * 1.07 + 0.35);
    const secondary = Math.sin(patternPos * Math.PI * 2 * 2.73 + 1.12);
    const tertiary = Math.sin(patternPos * Math.PI * 2 * 4.91 + 2.4);
    const localJitter = Math.sin((barIndex / safeTotal) * Math.PI * 29 + 0.8) * 0.08;

    const wave = clamp(primary * 0.56 + secondary * 0.3 + tertiary * 0.14 + localJitter, -1, 1);

    return {
      darkOpacity: Math.pow(Math.max(0, -wave), 0.72) * 0.68,
      lightOpacity: Math.pow(Math.max(0, wave), 0.9) * 0.44,
    };
  };

  return (
    <section ref={tileRef} className={`weather-tile weather-tile-blank weather-tile-${size}`} aria-hidden={!visible}>
      {isWeatherTile && (
        <>
          <div className="weather-temp-corner" aria-hidden="true">
            <div className="weather-temp-main-row">
              <span className={`weather-temp-value${isTripleDigitTemp ? " weather-temp-value-3digit" : ""}`}>
                {currentTempF !== null ? currentTempF : "--"}
              </span>
              <span className="weather-temp-degree-stack">
                <span className="weather-temp-degree">&deg;</span>
                <span className="weather-temp-unit">F</span>
              </span>
            </div>
            <div className="weather-temp-stats" aria-hidden="true">
              <span style={{ color: "rgba(255,110,100,0.95)" }}>H {highTempF !== null ? `${highTempF}${String.fromCharCode(176)}` : "--"}</span>
              <span style={{ color: "rgba(100,180,255,0.95)" }}>L {lowTempF !== null ? `${lowTempF}${String.fromCharCode(176)}` : "--"}</span>
              <span>P {precipPct !== null ? `${precipPct}%` : "--"}</span>
              <span>HUM {humidityPct !== null ? `${humidityPct}%` : "--"}</span>
            </div>
          </div>

          <div className="weather-condition-axis-icon" aria-hidden="true">
            <svg viewBox="0 0 128 128" role="presentation" focusable="false" aria-hidden="true">
              <ConditionIconPaths kind={conditionVisual.kind} />
            </svg>
            <span>{conditionVisual.label}</span>
          </div>

          {isDailyWeatherTile && (
            <>
              <div ref={graphRef} className="weather-temp-graph" aria-hidden="true">
                <svg viewBox="0 0 100 100" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id={weatherGradientId} x1="0" y1="0" x2="100" y2="0" gradientUnits="userSpaceOnUse">
                      {weatherGraphData.gradientStops.map((stop, idx) => (
                        <stop
                          key={`temp-stop-${idx}-${stop.offset.toFixed(3)}`}
                          offset={`${stop.offset.toFixed(3)}%`}
                          stopColor={stop.color}
                          stopOpacity={getEdgeFadeOpacity(stop.offset)}
                        />
                      ))}
                    </linearGradient>
                    <linearGradient id={weatherAreaGradientId} x1="0" y1="0" x2="100" y2="0" gradientUnits="userSpaceOnUse">
                      {weatherGraphData.areaGradientStops.map((stop, idx) => (
                        <stop
                          key={`temp-area-stop-${idx}-${stop.offset.toFixed(3)}`}
                          offset={`${stop.offset.toFixed(3)}%`}
                          stopColor={stop.color}
                          stopOpacity={getEdgeFadeOpacity(stop.offset)}
                        />
                      ))}
                    </linearGradient>
                  </defs>
                  <polygon
                    points={weatherGraphData.areaPoints}
                    fill={`url(#${weatherAreaGradientId})`}
                    shapeRendering="geometricPrecision"
                  />
                  {weatherGraphData.lineBasePoints.length > 0 && (() => {
                    const mkPts = (phaseOff: number) =>
                      weatherGraphData.lineBasePoints.map((p) => {
                        const speed = 1 + Math.abs(p.tempF - 67.5) / 35;
                        const amp = 2.2 + Math.abs(p.tempF - 67.5) / 18;
                        return `${p.x.toFixed(2)},${clamp(p.y + Math.sin(phase * speed * 300 + p.x * 0.18 + phaseOff) * amp, 0, 100).toFixed(2)}`;
                      }).join(" ");
                    return (
                      <>
                        <polyline points={mkPts(0)} fill="none" stroke={`url(#${weatherGradientId})`} strokeWidth={1.1} strokeOpacity={0.3} strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" shapeRendering="geometricPrecision" />
                        <polyline points={mkPts(Math.PI * 0.65)} fill="none" stroke={`url(#${weatherGradientId})`} strokeWidth={1.1} strokeOpacity={0.6} strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" shapeRendering="geometricPrecision" />
                      </>
                    );
                  })()}
                  <polyline
                    points={weatherGraphData.linePoints}
                    fill="none"
                    stroke={`url(#${weatherGradientId})`}
                    strokeWidth={1.4}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    vectorEffect="non-scaling-stroke"
                    shapeRendering="geometricPrecision"
                  />
                  {weatherGraphData.markers.map((marker) => (
                    String(marker.kind) === "sunset" ? (
                      <g key={String(marker.key)}>
                        <ellipse
                          cx={Number(marker.x)}
                          cy={Number(marker.y)}
                          rx={Number(marker.ringR) * markerAspectRatioComp}
                          ry={Number(marker.ringR)}
                          fill={String(marker.ring)}
                        />
                        <ellipse
                          cx={Number(marker.x)}
                          cy={Number(marker.y)}
                          rx={Number(marker.r) * markerAspectRatioComp}
                          ry={Number(marker.r)}
                          fill={String(marker.fill)}
                        />
                      </g>
                    ) : (
                      <ellipse
                        key={String(marker.key)}
                        cx={Number(marker.x)}
                        cy={Number(marker.y)}
                        rx={Number(marker.r) * markerAspectRatioComp}
                        ry={Number(marker.r)}
                        fill={String(marker.fill)}
                        stroke={String(marker.stroke)}
                        strokeWidth={Number(marker.strokeWidth)}
                      />
                    )
                  ))}
                </svg>
              </div>

              <div className="weather-current-time-overlay" style={currentTimeOverlayStyle} aria-hidden="true">
                <svg viewBox="0 0 100 100" preserveAspectRatio="none">
                  {currentTimeEchoes.flatMap((echo) =>
                    [-1, 1].map((dir) => (
                      <line
                        key={`${echo.key}-${dir < 0 ? "l" : "r"}`}
                        x1={currentDayProgressPct}
                        y1={0}
                        x2={currentDayProgressPct}
                        y2={100}
                        className="weather-current-time-line-echo"
                      >
                        <animate
                          attributeName="x1"
                          values={`${currentDayProgressPct};${currentDayProgressPct + echo.drift * dir}`}
                          dur={echo.dur}
                          begin={echo.begin}
                          calcMode="spline"
                          keySplines="0.22 0.0 0.2 1"
                          repeatCount="indefinite"
                        />
                        <animate
                          attributeName="x2"
                          values={`${currentDayProgressPct};${currentDayProgressPct + echo.drift * dir}`}
                          dur={echo.dur}
                          begin={echo.begin}
                          calcMode="spline"
                          keySplines="0.22 0.0 0.2 1"
                          repeatCount="indefinite"
                        />
                        <animate
                          attributeName="y1"
                          values="0;10"
                          dur={echo.dur}
                          begin={echo.begin}
                          calcMode="spline"
                          keySplines="0.2 0.0 0.25 1"
                          repeatCount="indefinite"
                        />
                        <animate
                          attributeName="y2"
                          values="100;90"
                          dur={echo.dur}
                          begin={echo.begin}
                          calcMode="spline"
                          keySplines="0.2 0.0 0.25 1"
                          repeatCount="indefinite"
                        />
                        <animate
                          attributeName="stroke-opacity"
                          values="0;0;0.34;0"
                          keyTimes="0;0.14;0.34;1"
                          dur={echo.dur}
                          begin={echo.begin}
                          calcMode="spline"
                          keySplines="0.25 0 0.25 1;0.18 0 0.3 1;0.22 0 0.3 1"
                          repeatCount="indefinite"
                        />
                      </line>
                    )),
                  )}
                  <line
                    x1={currentDayProgressPct}
                    y1={0}
                    x2={currentDayProgressPct}
                    y2={100}
                    className="weather-current-time-line"
                  />
                </svg>
              </div>

              <div className="weather-bars-label-lane" style={precipLabelStyle} aria-hidden="true">
                <div className="weather-bars-row-icon weather-bars-row-icon-precip" aria-hidden="true">
                  <svg viewBox="0 0 24 24" role="presentation" focusable="false" aria-hidden="true">
                    <path d="M6.2 14.2c-2.2 0-4-1.8-4-4 0-2 1.5-3.7 3.4-3.9.7-2.3 2.9-3.9 5.3-3.9 2.7 0 5 1.9 5.5 4.5h.2c2.7 0 4.8 2.1 4.8 4.8 0 2.8-2.2 4.9-4.8 4.9H6.2Z" />
                    <path d="M8 17.2l-1.4 2.6M12 17.2l-1.4 2.6M16 17.2l-1.4 2.6" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" fill="none" />
                  </svg>
                </div>
                <div className="weather-bars-label weather-bars-label-precip">PRECIPITATION</div>
              </div>

              <div className="weather-precip-bars" style={precipGraphStyle} aria-hidden="true">
                <svg viewBox={`0 0 100 ${activePrecipBarHeightPx.toFixed(2)}`} preserveAspectRatio="none">
                  {weatherPrecipBars.map((bar, i) => {
                    const shading = getBarWaveShading(i, weatherPrecipBars.length);

                    return (
                      <g key={`precip-${i}`}>
                        <rect
                          x={bar.x}
                          y={Math.max(0, activePrecipBarHeightPx - bar.h)}
                          width={bar.w}
                          height={bar.h}
                          fill={`rgba(255,255,255,${(bar.opacity * weatherBarOpacityScale).toFixed(3)})`}
                          rx={0.3}
                          ry={0.3}
                        />
                        <rect
                          x={bar.x}
                          y={Math.max(0, activePrecipBarHeightPx - bar.h)}
                          width={bar.w}
                          height={bar.h}
                          fill="rgba(0,0,0,0.95)"
                          rx={0.3}
                          ry={0.3}
                          opacity={shading.darkOpacity}
                        />
                        <rect
                          x={bar.x}
                          y={Math.max(0, activePrecipBarHeightPx - bar.h)}
                          width={bar.w}
                          height={bar.h}
                          fill="rgba(255,255,255,0.9)"
                          rx={0.3}
                          ry={0.3}
                          style={{ mixBlendMode: "screen" }}
                          opacity={shading.lightOpacity}
                        />
                      </g>
                    );
                  })}
                </svg>
              </div>

              <div className="weather-time-axis" aria-hidden="true">
                <div className="weather-time-axis-line" />
                <div className="weather-time-axis-labels">
                  <span>12AM</span>
                  <span>6AM</span>
                  <span>12PM</span>
                  <span>6PM</span>
                </div>
              </div>

              <div className="weather-bars-label-lane" style={humidityLabelStyle} aria-hidden="true">
                <div className="weather-bars-row-icon weather-bars-row-icon-humidity" aria-hidden="true">
                  <svg viewBox="0 0 24 24" role="presentation" focusable="false" aria-hidden="true">
                    <path d="M12 2.4c-3.2 4-5.6 7.3-5.6 10.4 0 3.3 2.8 5.9 5.6 5.9s5.6-2.6 5.6-5.9c0-3.1-2.4-6.4-5.6-10.4Z" />
                    <path d="M15.3 13.1c0 1.8-1.2 3.2-2.8 3.7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" fill="none" opacity="0.72" />
                  </svg>
                </div>
                <div className="weather-bars-label weather-bars-label-humidity">HUMIDITY</div>
              </div>

              <div className="weather-humidity-bars" style={humidityGraphStyle} aria-hidden="true">
                <svg viewBox={`0 0 100 ${activeHumidityBarHeightPx.toFixed(2)}`} preserveAspectRatio="none">
                  {weatherHumidityBars.map((bar, i) => {
                    const shading = getBarWaveShading(i, weatherHumidityBars.length);

                    return (
                      <g key={`humidity-${i}`}>
                        <rect
                          x={bar.x}
                          y={0}
                          width={bar.w}
                          height={bar.h}
                          fill={`rgba(255,255,255,${(bar.opacity * weatherBarOpacityScale).toFixed(3)})`}
                          rx={0.3}
                          ry={0.3}
                        />
                        <rect
                          x={bar.x}
                          y={0}
                          width={bar.w}
                          height={bar.h}
                          fill="rgba(0,0,0,0.95)"
                          rx={0.3}
                          ry={0.3}
                          opacity={shading.darkOpacity}
                        />
                        <rect
                          x={bar.x}
                          y={0}
                          width={bar.w}
                          height={bar.h}
                          fill="rgba(255,255,255,0.9)"
                          rx={0.3}
                          ry={0.3}
                          style={{ mixBlendMode: "screen" }}
                          opacity={shading.lightOpacity}
                        />
                      </g>
                    );
                  })}
                </svg>
              </div>
            </>
          )}

          {isWeeklyWeatherTile && (
            <div className="weather-weekly-grid" aria-hidden="true">
              {weeklyForecastRows.map((row) => (
                <div key={row.key} className="weather-weekly-card">
                  <div className="weather-weekly-day">{row.dayLabel}</div>
                  <div className="weather-weekly-temp">{row.tempF !== null ? `${row.tempF}${String.fromCharCode(176)}` : "--"}</div>
                  <div className="weather-weekly-stats">
                    <div className="weather-weekly-stats-row">
                      <span style={{ color: "rgba(255,110,100,0.95)" }}>H {row.highF !== null ? `${row.highF}${String.fromCharCode(176)}` : "--"}</span>
                      <span style={{ color: "rgba(100,180,255,0.95)" }}>L {row.lowF !== null ? `${row.lowF}${String.fromCharCode(176)}` : "--"}</span>
                    </div>
                    <div className="weather-weekly-stats-row">
                      <span>P {row.precipPct !== null ? `${row.precipPct}%` : "--"}</span>
                      <span>HUM {row.humidityPct !== null ? `${row.humidityPct}%` : "--"}</span>
                    </div>
                  </div>
                  <div className="weather-weekly-mini-icon" aria-hidden="true">
                    <svg viewBox="0 0 128 128" role="presentation" focusable="false" aria-hidden="true">
                      <ConditionIconPaths kind={conditionVisual.kind} />
                    </svg>
                  </div>
                  <div className="weather-weekly-condition">{conditionVisual.label}</div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
      {variant === "timer" && (
        <div className="timer-tile-content">
          <div className="timer-tile-title">Timer</div>
          <div className="timer-tile-display">
            {timerHours > 0
              ? `${String(timerHours).padStart(2, "0")}:${String(timerMinutes).padStart(2, "0")}:${String(timerSeconds).padStart(2, "0")}`
              : `${String(timerMinutes).padStart(2, "0")}:${String(timerSeconds).padStart(2, "0")}`
            }
          </div>
        </div>
      )}
      <div className="weather-edge-orbit" aria-hidden="true">
        <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
          {nearestEdges.map((edge, i) => {
            const a = allPoints[edge.a];
            const b = allPoints[edge.b];
            const wave = (Math.sin((i / Math.max(1, nearestEdges.length)) * Math.PI * 2 + phase * Math.PI * 8) + 1) * 0.5;
            const distFade = clamp(1 - edge.dist2 / 2700, 0.12, 1);
            const opacity = (0.12 + wave * 0.56) * distFade;
            return (
              <line
                key={`edge-${i}`}
                x1={a.x}
                y1={a.y}
                x2={b.x}
                y2={b.y}
                stroke="rgba(255,255,255,1)"
                strokeOpacity={opacity}
                strokeWidth={0.9}
              />
            );
          })}

          {points.map((p, i) => {
            const wave = (Math.sin((i / nodeCount) * Math.PI * 2 + phase * Math.PI * 8 + 0.8) + 1) * 0.5;
            const r = 1.25 + wave * 0.95;
            return (
              <circle
                key={`node-${i}`}
                cx={p.x}
                cy={p.y}
                r={r}
                fill="rgba(255,255,255,0.95)"
                fillOpacity={p.alpha}
              />
            );
          })}

          {reversePoints.map((p, i) => {
            const wave = (Math.sin((i / reverseNodeCount) * Math.PI * 2 - phase * Math.PI * 8 + 0.8) + 1) * 0.5;
            const r = 1.05 + wave * 0.85;
            return (
              <circle
                key={`node-reverse-${i}`}
                cx={p.x}
                cy={p.y}
                r={r}
                fill="rgba(255,255,255,0.9)"
                fillOpacity={p.alpha}
              />
            );
          })}
        </svg>
      </div>
    </section>
  );
}

function useDraggable() {
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null);
  const dragging = useRef(false);
  const offset = useRef({ x: 0, y: 0 });
  const nodeRef = useRef<HTMLElement | null>(null);

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    if (!nodeRef.current) return;
    const rect = nodeRef.current.getBoundingClientRect();
    dragging.current = true;
    offset.current = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    e.preventDefault();
  }, []);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragging.current) return;
      setPos({ x: e.clientX - offset.current.x, y: e.clientY - offset.current.y });
    };
    const onUp = () => { dragging.current = false; };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, []);

  return { pos, onMouseDown, nodeRef };
}

function App() {
  const [activity, setActivity] = useState(0.06);
  const [audioLevel, setAudioLevel] = useState(0);
  const [audioBands, setAudioBands] = useState({ low: 0, high: 0 });
  const ttsDrag = useDraggable();
  const debugDrag = useDraggable();
  const audioLevelTargetRef = useRef(0);
  const audioBandsTargetRef = useRef({ low: 0, high: 0 });
  const speechActiveRef = useRef(false);
  const speechEndAtMsRef = useRef<number | null>(null);
  const [speechActive, setSpeechActive] = useState(false);
  const [layout, setLayout] = useState<StageLayout>(LAYOUT_PRESETS.center);
  const [subtitle, setSubtitle] = useState<SubtitleState>({ words: [], activeWord: -1, visible: false });
  const [testText, setTestText] = useState("Eve here. This is a subtitle and animation sync test.");
  const [testSpeaking, setTestSpeaking] = useState(false);
  const [clockNow, setClockNow] = useState(() => new Date());
  const [colonVisible, setColonVisible] = useState(() => new Date().getSeconds() % 2 === 0);
  const [toolsDisplayMode, setToolsDisplayMode] = useState(false);
  const [weatherTileData, setWeatherTileData] = useState<WeatherTileData | null>(null);
  const [selectedTilePreset, setSelectedTilePreset] = useState<TilePresetId>("none");
  const [activeTilePreset, setActiveTilePreset] = useState<BlankTilePresetId | null>(null);
  const [debugMaxPrecipBars, setDebugMaxPrecipBars] = useState(false);
  const [debugMaxHumidityBars, setDebugMaxHumidityBars] = useState(false);
  const [debugWeatherIcon, setDebugWeatherIcon] = useState<"auto" | "sunny" | "partly-cloudy" | "rain" | "snow" | "storm" | "fog">("auto");
  const [debugWeatherTempInput, setDebugWeatherTempInput] = useState("");
  const [timerHoursInput, setTimerHoursInput] = useState("0");
  const [timerMinutesInput, setTimerMinutesInput] = useState("0");
  const [timerSecondsInput, setTimerSecondsInput] = useState("0");
  const timerHours = Math.max(0, Math.min(99, parseInt(timerHoursInput, 10) || 0));
  const timerMinutes = Math.max(0, Math.min(59, parseInt(timerMinutesInput, 10) || 0));
  const timerSeconds = Math.max(0, Math.min(59, parseInt(timerSecondsInput, 10) || 0));
  const [weatherRefreshPhase, setWeatherRefreshPhase] = useState<WeatherRefreshPhase>("idle");
  const [weatherRefreshMessage, setWeatherRefreshMessage] = useState("Weather refresh idle.");
  const [tileVisible, setTileVisible] = useState(false);
  const [weatherTileOffsetVw, setWeatherTileOffsetVw] = useState(120);
  const preToolsLayoutRef = useRef<StageLayout | null>(null);
  const layoutRef = useRef<StageLayout>(LAYOUT_PRESETS.center);
  const layoutAnimationFrameRef = useRef<number | null>(null);
  const tileSwitchTimerRef = useRef<number | null>(null);
  const tileSwitchRafRef = useRef<number | null>(null);
  const tileTransitionTokenRef = useRef(0);
  const subtitleHideTimerRef = useRef<number | null>(null);
  const levelPulseTimerRef = useRef<number | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const pendingWeatherRefreshRef = useRef(false);
  const weatherRefreshInFlightRef = useRef(false);
  const weatherRefreshTimeoutRef = useRef<number | null>(null);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(WEATHER_CACHE_STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as unknown;
      if (isValidWeatherTileData(parsed) && !parsed.isMock) {
        setWeatherTileData(parsed);
      }
    } catch {
      // Ignore malformed storage data.
    }
  }, []);

  useEffect(() => {
    if (!weatherTileData || weatherTileData.isMock) return;
    try {
      window.localStorage.setItem(WEATHER_CACHE_STORAGE_KEY, JSON.stringify(weatherTileData));
    } catch {
      // Ignore storage failures.
    }
  }, [weatherTileData]);

  const stopLayoutAnimation = useCallback(() => {
    if (layoutAnimationFrameRef.current !== null) {
      window.cancelAnimationFrame(layoutAnimationFrameRef.current);
      layoutAnimationFrameRef.current = null;
    }
  }, []);

  const animateLayoutTo = useCallback(
    (nextLayout: StageLayout, durationMs = TOOLS_LAYOUT_ANIMATION_MS, onDone?: () => void) => {
      stopLayoutAnimation();
      const from = layoutRef.current;
      if (durationMs <= 0) {
        setLayout(nextLayout);
        layoutRef.current = nextLayout;
        onDone?.();
        return;
      }

      const startMs = performance.now();
      const tick = (nowMs: number) => {
        const raw = clamp((nowMs - startMs) / durationMs, 0, 1);
        const eased = easeInOutCubic(raw);
        const next = interpolateLayout(from, nextLayout, eased);
        setLayout(next);
        layoutRef.current = next;
        if (raw < 1) {
          layoutAnimationFrameRef.current = window.requestAnimationFrame(tick);
        } else {
          layoutAnimationFrameRef.current = null;
          onDone?.();
        }
      };

      layoutAnimationFrameRef.current = window.requestAnimationFrame(tick);
    },
    [stopLayoutAnimation]
  );

  const setToolsMode = (enabled: boolean) => {
    setToolsDisplayMode(enabled);
    const current = layoutRef.current;
    if (enabled) {
      preToolsLayoutRef.current = current;
      animateLayoutTo(
        {
          ...current,
          ...TOOLS_DISPLAY_LAYOUT,
        },
        TOOLS_LAYOUT_ANIMATION_MS
      );
      return;
    }

    if (preToolsLayoutRef.current) {
      const restored = preToolsLayoutRef.current;
      preToolsLayoutRef.current = null;
      animateLayoutTo(restored, TOOLS_LAYOUT_ANIMATION_MS);
      return;
    }

    animateLayoutTo(
      {
        ...current,
        logoOpacity: 1,
      },
      TOOLS_LAYOUT_ANIMATION_MS
    );
  };

  const setToolsModeAndWait = (enabled: boolean, onDone: () => void) => {
    setToolsDisplayMode(enabled);
    const current = layoutRef.current;
    if (enabled) {
      preToolsLayoutRef.current = current;
      animateLayoutTo(
        {
          ...current,
          ...TOOLS_DISPLAY_LAYOUT,
        },
        TOOLS_LAYOUT_ANIMATION_MS,
        onDone
      );
      return;
    }

    if (preToolsLayoutRef.current) {
      const restored = preToolsLayoutRef.current;
      preToolsLayoutRef.current = null;
      animateLayoutTo(restored, TOOLS_LAYOUT_ANIMATION_MS, onDone);
      return;
    }

    animateLayoutTo(
      {
        ...current,
        logoOpacity: 1,
      },
      TOOLS_LAYOUT_ANIMATION_MS,
      onDone
    );
  };

  const applyDefaultPlacementPreset = () => {
    setToolsDisplayMode(false);
    setSelectedTilePreset("none");
    runTileTransition(null);
    preToolsLayoutRef.current = null;
    animateLayoutTo(LAYOUT_PRESETS.center, TOOLS_LAYOUT_ANIMATION_MS);
  };

  const applyAnimationOnlyPreset = () => {
    setSelectedTilePreset("animation-only");
    setToolsMode(true);
  };

  const applyBlankTilePreset = (preset: BlankTilePresetId) => {
    const isWeatherPreset = preset === "large-weather-daily" || preset === "large-weather-weekly";
    if (isWeatherPreset && weatherTileData?.isMock) {
      setWeatherTileData(null);
    }
    if (!isWeatherPreset && !weatherTileData) {
      setWeatherTileData(makeMockWeatherTileData());
    }
    setSelectedTilePreset(preset);
  };

  const clearWeatherRefreshTimeout = () => {
    if (weatherRefreshTimeoutRef.current !== null) {
      window.clearTimeout(weatherRefreshTimeoutRef.current);
      weatherRefreshTimeoutRef.current = null;
    }
  };

  const requestWeatherTileRefresh = () => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      pendingWeatherRefreshRef.current = true;
      weatherRefreshInFlightRef.current = true;
      setWeatherRefreshPhase("queued");
      setWeatherRefreshMessage("Refresh queued: waiting for dashboard WebSocket.");
      return;
    }
    pendingWeatherRefreshRef.current = false;
    weatherRefreshInFlightRef.current = true;
    setWeatherRefreshPhase("requested");
    setWeatherRefreshMessage("Weather API refresh requested...");
    clearWeatherRefreshTimeout();
    weatherRefreshTimeoutRef.current = window.setTimeout(() => {
      if (!weatherRefreshInFlightRef.current) return;
      weatherRefreshInFlightRef.current = false;
      setWeatherRefreshPhase("error");
      setWeatherRefreshMessage("Refresh timed out waiting for new weather data.");
      weatherRefreshTimeoutRef.current = null;
    }, 12000);
    ws.send(
      JSON.stringify({
        type: "dashboard_refresh_weather",
        payload: { location: weatherTileData?.location || "Frisco, Texas" },
      })
    );
  };

  const clearTileTransitionHandles = () => {
    if (tileSwitchTimerRef.current !== null) {
      window.clearTimeout(tileSwitchTimerRef.current);
      tileSwitchTimerRef.current = null;
    }
    if (tileSwitchRafRef.current !== null) {
      window.cancelAnimationFrame(tileSwitchRafRef.current);
      tileSwitchRafRef.current = null;
    }
  };

  function runTileTransition(targetPreset: BlankTilePresetId | null) {
    tileTransitionTokenRef.current += 1;
    const token = tileTransitionTokenRef.current;
    clearTileTransitionHandles();

    const guarded = (fn: () => void) => {
      if (tileTransitionTokenRef.current !== token) return;
      fn();
    };

    const enterFromRight = (preset: BlankTilePresetId) => {
      guarded(() => {
        setWeatherTileOffsetVw(120);
        setActiveTilePreset(preset);
        setTileVisible(true);
        tileSwitchRafRef.current = window.requestAnimationFrame(() => {
          tileSwitchRafRef.current = window.requestAnimationFrame(() => {
            tileSwitchRafRef.current = null;
            guarded(() => {
              setWeatherTileOffsetVw(0);
            });
          });
        });
      });
    };

    const dismissToLeft = (onDone: () => void) => {
      if (activeTilePreset === null) {
        onDone();
        return;
      }
      guarded(() => {
        setTileVisible(true);
        setWeatherTileOffsetVw(-120);
        tileSwitchTimerRef.current = window.setTimeout(() => {
          tileSwitchTimerRef.current = null;
          guarded(() => {
            setTileVisible(false);
            setActiveTilePreset(null);
            setWeatherTileOffsetVw(120);
            tileSwitchRafRef.current = window.requestAnimationFrame(() => {
              tileSwitchRafRef.current = null;
              guarded(() => {
                onDone();
              });
            });
          });
        }, Math.max(TILE_SWITCH_FADE_MS, TILE_SWITCH_MOVE_MS));
      });
    };

    if (targetPreset === null) {
      dismissToLeft(() => {
        guarded(() => {
          setTileVisible(false);
          setActiveTilePreset(null);
          setWeatherTileOffsetVw(120);
        });
      });
      return;
    }

    if (activeTilePreset === null) {
      enterFromRight(targetPreset);
      return;
    }

    if (activeTilePreset === targetPreset) {
      guarded(() => {
        setTileVisible(true);
        setWeatherTileOffsetVw(0);
      });
      return;
    }

    dismissToLeft(() => {
      enterFromRight(targetPreset);
    });
  }

  const handleTilePresetChange = (preset: TilePresetId) => {
    if (preset === "none") {
      setSelectedTilePreset("none");
      runTileTransition(null);
    } else if (preset === "animation-only") {
      applyAnimationOnlyPreset();
      runTileTransition(null);
    } else {
      const isDefaultPlacementActive = !toolsDisplayMode;
      applyBlankTilePreset(preset);
      if (preset === "large-weather-daily" || preset === "large-weather-weekly") {
        requestWeatherTileRefresh();
      }
      if (isDefaultPlacementActive) {
        setToolsModeAndWait(true, () => {
          runTileTransition(preset);
        });
      } else {
        setToolsMode(true);
        runTileTransition(preset);
      }
    }
  };

  const showWeatherTile = activeTilePreset !== null;

  const tileSet = useMemo(() => {
    if (activeTilePreset === "large-default") {
      return {
        layoutClassName: "weather-tile-set-large-default",
        tiles: [{ size: "large", variant: "blank" as TileVariant }],
      };
    }

    if (activeTilePreset === "large-weather-daily") {
      return {
        layoutClassName: "weather-tile-set-large-default",
        tiles: [{ size: "large", variant: "weather" as TileVariant }],
      };
    }

    if (activeTilePreset === "large-weather-weekly") {
      return {
        layoutClassName: "weather-tile-set-large-default",
        tiles: [{ size: "large", variant: "weather-weekly" as TileVariant }],
      };
    }

    if (activeTilePreset === "large-timer") {
      return {
        layoutClassName: "weather-tile-set-large-default",
        tiles: [{ size: "large", variant: "timer" as TileVariant }],
      };
    }

    if (activeTilePreset === "triple-blank") {
      return {
        layoutClassName: "weather-tile-set-triple",
        tiles: [
          { size: "compact", variant: "blank" as TileVariant },
          { size: "compact", variant: "blank" as TileVariant },
          { size: "compact", variant: "blank" as TileVariant },
        ],
      };
    }

    if (activeTilePreset === "quad-blank") {
      return {
        layoutClassName: "weather-tile-set-quad",
        tiles: [
          { size: "compact", variant: "blank" as TileVariant },
          { size: "compact", variant: "blank" as TileVariant },
          { size: "compact", variant: "blank" as TileVariant },
          { size: "compact", variant: "blank" as TileVariant },
        ],
      };
    }

    if (activeTilePreset === "double-blank") {
      return {
        layoutClassName: "weather-tile-set-double",
        tiles: [
          { size: "medium", variant: "blank" as TileVariant },
          { size: "medium", variant: "blank" as TileVariant },
        ],
      };
    }

    return null;
  }, [activeTilePreset]);

  useEffect(() => {
    layoutRef.current = layout;
  }, [layout]);

  useEffect(() => {
    return () => {
      stopLayoutAnimation();
      if (tileSwitchTimerRef.current !== null) {
        window.clearTimeout(tileSwitchTimerRef.current);
        tileSwitchTimerRef.current = null;
      }
      if (tileSwitchRafRef.current !== null) {
        window.cancelAnimationFrame(tileSwitchRafRef.current);
        tileSwitchRafRef.current = null;
      }
    };
  }, [stopLayoutAnimation]);

  const endSpeechWindow = () => {
    speechActiveRef.current = false;
    speechEndAtMsRef.current = null;
    setSpeechActive(false);
    audioLevelTargetRef.current = 0;
    audioBandsTargetRef.current = { low: 0, high: 0 };
    // Keep current values and release quickly for a smoother settle.
    setActivity((prev) => Math.min(prev, 0.12));
  };

  const handleEvent = (evt: EventEnvelope) => {
    if (evt.type === "state_change") {
      const s = String(evt.payload.state ?? "IDLE");
      if (s === "THINKING") setActivity(0.95);
      else if (s === "TRANSCRIBING") setActivity(0.62);
      else if (s === "SPEAKING") {
        setActivity(0.68);
        speechActiveRef.current = true;
        setSpeechActive(true);
        const durationS = toFiniteNumber(evt.payload.duration_s);
        if (durationS !== null && durationS > 0) {
          speechEndAtMsRef.current = scheduleSpeechEnd(durationS * 1000, EARLY_RELEASE_MS);
        } else if (speechEndAtMsRef.current === null) {
          const textMaybe = String(evt.payload.text ?? "").trim();
          const est = estimateSpeechDurationMs(textMaybe);
          if (est > 0) {
            speechEndAtMsRef.current = scheduleSpeechEnd(est, EARLY_RELEASE_MS);
          }
        }
      }
      else {
        endSpeechWindow();
        setActivity(0.06);
      }
    }

    if (evt.type === "user_transcript") {
      setActivity(0.74);
    }

    if (evt.type === "assistant_response") {
      setActivity((prev) => Math.max(prev, 0.5));
    }

    if (evt.type === "subtitle_prepare") {
      speechActiveRef.current = true;
      setSpeechActive(true);
      const payloadWords = Array.isArray(evt.payload.words)
        ? evt.payload.words.map((w) => String(w))
        : [];
      const text = String(evt.payload.text ?? "").trim();
      const durationS = toFiniteNumber(evt.payload.duration_s);
      if (speechEndAtMsRef.current === null) {
        if (durationS !== null && durationS > 0) {
          speechEndAtMsRef.current = scheduleSpeechEnd(durationS * 1000, EARLY_RELEASE_MS);
        } else {
          const est = estimateSpeechDurationMs(text);
          if (est > 0) {
            speechEndAtMsRef.current = scheduleSpeechEnd(est, EARLY_RELEASE_MS);
          }
        }
      }
      const words = payloadWords.length > 0 ? payloadWords : text ? text.split(/\s+/) : [];
      if (subtitleHideTimerRef.current !== null) {
        window.clearTimeout(subtitleHideTimerRef.current);
        subtitleHideTimerRef.current = null;
      }
      setSubtitle({ words, activeWord: -1, visible: words.length > 0 });
    }

    if (evt.type === "subtitle_progress") {
      const idx = toFiniteNumber(evt.payload.word_index);
      if (idx !== null) {
        setSubtitle((prev) => ({
          ...prev,
          activeWord: Math.max(prev.activeWord, Math.floor(idx)),
          visible: prev.words.length > 0,
        }));
      }
    }

    if (evt.type === "subtitle_done") {
      endSpeechWindow();
      if (subtitleHideTimerRef.current !== null) {
        window.clearTimeout(subtitleHideTimerRef.current);
      }
      subtitleHideTimerRef.current = window.setTimeout(() => {
        setSubtitle({ words: [], activeWord: -1, visible: false });
        subtitleHideTimerRef.current = null;
      }, 1200);
    }

    if (evt.type === "tts_audio_level") {
      if (!speechActiveRef.current) return;
      const level = toFiniteNumber(evt.payload.level);
      if (level !== null) {
        const next = clamp(level, 0, 1);
        // Gate tiny values to reduce idle shimmer jitter.
        audioLevelTargetRef.current = next < 0.025 ? 0 : next;
        if (next > 0.01) {
          setActivity((prev) => Math.max(prev, 0.28 + next * 0.7));
        }
      }
    }

    if (evt.type === "tts_audio_bands") {
      if (!speechActiveRef.current) return;
      const low = toFiniteNumber(evt.payload.low);
      const high = toFiniteNumber(evt.payload.high);
      if (low !== null && high !== null) {
        const lowNext = clamp(low, 0, 1);
        const highNext = clamp(high, 0, 1);
        audioBandsTargetRef.current = {
          low: lowNext < 0.025 ? 0 : lowNext,
          high: highNext < 0.025 ? 0 : highNext,
        };
      }
    }

    if (evt.type === "ui_layout") {
      stopLayoutAnimation();
      setLayout((prev) => {
        const next = parseLayoutPayload(evt.payload, prev);
        layoutRef.current = next;
        return next;
      });
    }

    if (evt.type === "tool_context") {
      const maybeWeatherTile = extractWeatherTileData(evt.payload);
      if (maybeWeatherTile) {
        setWeatherTileData(maybeWeatherTile);
        if (weatherRefreshInFlightRef.current) {
          weatherRefreshInFlightRef.current = false;
          clearWeatherRefreshTimeout();
          setWeatherRefreshPhase("loaded");
          setWeatherRefreshMessage(`Weather refreshed at ${new Date().toLocaleTimeString()}.`);
        }
      }
    }
  };

  useEffect(() => {
    const ws = new WebSocket("ws://127.0.0.1:8765");
    wsRef.current = ws;

    ws.onopen = () => {
      setActivity(0.22);
      if (pendingWeatherRefreshRef.current) {
        requestWeatherTileRefresh();
      }
    };
    ws.onclose = () => {
      setActivity(0.12);
      if (weatherRefreshInFlightRef.current) {
        weatherRefreshInFlightRef.current = false;
        clearWeatherRefreshTimeout();
        setWeatherRefreshPhase("error");
        setWeatherRefreshMessage("Refresh failed: dashboard connection closed.");
      }
    };

    ws.onmessage = (msg) => {
      try {
        handleEvent(JSON.parse(msg.data) as EventEnvelope);
      } catch {
        // Ignore malformed events.
      }
    };

    return () => {
      wsRef.current = null;
      ws.close();
      clearWeatherRefreshTimeout();
      if (levelPulseTimerRef.current !== null) {
        window.clearInterval(levelPulseTimerRef.current);
        levelPulseTimerRef.current = null;
      }
      window.speechSynthesis?.cancel();
      if (subtitleHideTimerRef.current !== null) {
        window.clearTimeout(subtitleHideTimerRef.current);
        subtitleHideTimerRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (activeTilePreset !== "large-weather-daily" && activeTilePreset !== "large-weather-weekly") return;
    requestWeatherTileRefresh();
  }, [activeTilePreset]);

  useEffect(() => {
    const t = setInterval(() => {
      setActivity((v) => Math.max(0.06, v * 0.88));
    }, 120);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    const t = window.setInterval(() => {
      const next = new Date();
      setClockNow(next);
      setColonVisible(next.getSeconds() % 2 === 0);
    }, 250);
    return () => window.clearInterval(t);
  }, []);

  const clock = getClockParts(clockNow);

  useEffect(() => {
    const t = setInterval(() => {
      setAudioLevel((v) => {
        if (speechActiveRef.current) {
          return smoothReactiveValue(v, audioLevelTargetRef.current, 0.18, 0.09, 0.055);
        }
        return smoothReactiveValue(v, audioLevelTargetRef.current, 0.3, 0.22, 0.04);
      });
      setAudioBands((b) => ({
        low: (() => {
          if (speechActiveRef.current) {
            return smoothReactiveValue(b.low, audioBandsTargetRef.current.low, 0.14, 0.08, 0.045);
          }
          return smoothReactiveValue(b.low, audioBandsTargetRef.current.low, 0.24, 0.18, 0.035);
        })(),
        high: (() => {
          if (speechActiveRef.current) {
            return smoothReactiveValue(b.high, audioBandsTargetRef.current.high, 0.14, 0.08, 0.045);
          }
          return smoothReactiveValue(b.high, audioBandsTargetRef.current.high, 0.24, 0.18, 0.035);
        })(),
      }));

      // Deterministic fallback in case subtitle_done is delayed or dropped.
      if (speechActiveRef.current && speechEndAtMsRef.current !== null && performance.now() > speechEndAtMsRef.current + 120) {
        endSpeechWindow();
      }
    }, 33);
    return () => clearInterval(t);
  }, []);

  const stopTesterSpeech = () => {
    if (levelPulseTimerRef.current !== null) {
      window.clearInterval(levelPulseTimerRef.current);
      levelPulseTimerRef.current = null;
    }
    window.speechSynthesis?.cancel();
    handleEvent({ type: "tts_audio_level", payload: { level: 0 } });
    handleEvent({ type: "tts_audio_bands", payload: { low: 0, high: 0 } });
    handleEvent({ type: "subtitle_done", payload: {} });
    handleEvent({ type: "state_change", payload: { state: "IDLE" } });
    setTestSpeaking(false);
  };

  const startTesterSpeech = () => {
    const text = testText.trim();
    if (!text) return;
    if (!("speechSynthesis" in window)) return;

    stopTesterSpeech();

    const words = text.split(/\s+/);
    const estimatedDurationMs = estimateSpeechDurationMs(text, 0.97);
    handleEvent({ type: "subtitle_prepare", payload: { text, words, duration_s: estimatedDurationMs / 1000 } });
    handleEvent({ type: "state_change", payload: { state: "SPEAKING", duration_s: estimatedDurationMs / 1000, text } });

    const utter = new SpeechSynthesisUtterance(text);
    utter.rate = 0.97;
    utter.pitch = 1.1;
    utter.volume = 1.0;

    const voices = window.speechSynthesis.getVoices();
    const preferred =
      voices.find((v) => /female|woman|zira|aria|jenny|sara|susan/i.test(v.name)) ||
      voices.find((v) => /en[-_ ]?us|english/i.test(v.lang)) ||
      voices[0];
    if (preferred) utter.voice = preferred;

    utter.onstart = () => {
      setTestSpeaking(true);
      levelPulseTimerRef.current = window.setInterval(() => {
        const t = performance.now() * 0.001;
        const pulse = 0.2 + Math.abs(Math.sin(t * 12.5)) * 0.55;
        const low = 0.18 + Math.abs(Math.sin(t * 6.2 + 0.8)) * 0.62;
        const high = 0.16 + Math.abs(Math.sin(t * 9.8 + 2.1)) * 0.58;
        handleEvent({ type: "tts_audio_level", payload: { level: clamp(pulse, 0, 1) } });
        handleEvent({ type: "tts_audio_bands", payload: { low: clamp(low, 0, 1), high: clamp(high, 0, 1) } });
      }, 45);
    };

    utter.onboundary = (e) => {
      if (e.name !== "word") return;
      const leading = text.slice(0, e.charIndex).trim();
      const idx = leading.length === 0 ? 0 : leading.split(/\s+/).length;
      handleEvent({ type: "subtitle_progress", payload: { word_index: idx } });
    };

    utter.onend = () => {
      if (levelPulseTimerRef.current !== null) {
        window.clearInterval(levelPulseTimerRef.current);
        levelPulseTimerRef.current = null;
      }
      handleEvent({ type: "tts_audio_level", payload: { level: 0 } });
      handleEvent({ type: "tts_audio_bands", payload: { low: 0, high: 0 } });
      handleEvent({ type: "subtitle_done", payload: { text } });
      handleEvent({ type: "state_change", payload: { state: "IDLE" } });
      setTestSpeaking(false);
    };

    utter.onerror = () => {
      stopTesterSpeech();
    };

    window.speechSynthesis.speak(utter);
  };

  return (
    <div className="dash-root">
      <div
        className="clock-top"
        aria-live="off"
        style={{
          left: `${50 + layout.clockX * LAYOUT_OVERLAY_MOVE_X_PERCENT}%`,
          top: `${LAYOUT_CLOCK_TOP_BASE_PERCENT + layout.clockY * LAYOUT_OVERLAY_MOVE_Y_PERCENT}%`,
          transform: `translateX(-50%) scale(${layout.clockScale})`,
        }}
      >
        <div className="clock-time" role="timer" aria-label={`Current time ${clock.hour}:${clock.minute}`}>
          <span>{clock.hour}</span>
          <span className={`clock-colon ${colonVisible ? "visible" : "hidden"}`}>:</span>
          <span>{clock.minute}</span>
        </div>
        <div className="clock-date">{`${clock.dayLabel} ${clock.dateLabel}`}</div>
      </div>
      <Canvas camera={{ position: [0, 0, 6.6], fov: 36, near: 0.1, far: 60 }}>
        <color attach="background" args={["#000000"]} />
        <ambientLight intensity={0.5} />
        <pointLight position={[2.6, 2.3, 5]} intensity={1.6} color="#7ecbff" />
        <pointLight position={[-2.8, -2.1, 3]} intensity={0.8} color="#4d98d1" />
        <SphereGraph
          activity={activity}
          audioLevel={audioLevel}
          audioBands={audioBands}
          speechActive={speechActive}
          layout={layout}
        />
      </Canvas>
      <div
        className="logo-center"
        aria-hidden="true"
        style={{
          left: `${50 + layout.x * LAYOUT_OVERLAY_MOVE_X_PERCENT}%`,
          top: `${50 - layout.y * LAYOUT_OVERLAY_MOVE_Y_PERCENT}%`,
          transform: `translate(-50%, -50%) scale(${layout.logoScale})`,
          opacity: layout.logoOpacity,
        }}
      >
        <span className="logo-letter logo-letter-1">E</span>
        <span className="logo-letter logo-letter-2">V</span>
        <span className="logo-letter logo-letter-3">E</span>
      </div>

      {showWeatherTile && (
        <div className="weather-tile-lane" aria-hidden="true">
          <div
            className={`weather-tile-track ${tileVisible ? "visible" : "hidden"}`}
            style={{ transform: `translateX(${weatherTileOffsetVw}vw)` }}
          >
            {tileSet && (
              <div className={`weather-tile-set ${tileSet.layoutClassName}`}>
                {tileSet.tiles.map((tileSize, i) => (
                  <WeatherTile
                    key={`${tileSet.layoutClassName}-${i}`}
                    visible={showWeatherTile}
                    size={tileSize.size}
                    variant={tileSize.variant}
                    weatherData={weatherTileData}
                    debugMaxPrecipBars={debugMaxPrecipBars}
                    debugMaxHumidityBars={debugMaxHumidityBars}
                    debugIconOverride={debugWeatherIcon}
                    debugTempOverride={debugWeatherTempInput.trim() === "" ? null : Number(debugWeatherTempInput)}
                    timerHours={timerHours}
                    timerMinutes={timerMinutes}
                    timerSeconds={timerSeconds}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      <div className={`subtitle-track ${subtitle.visible ? "visible" : ""}`}>
        {subtitle.words.map((word, i) => (
          <span key={`${word}-${i}`} className={i <= subtitle.activeWord ? "done" : "pending"}>
            {word}
          </span>
        ))}
      </div>

      {TEST_UI_ENABLED && (
        <section
          ref={ttsDrag.nodeRef as React.RefObject<HTMLElement>}
          className="test-tts-panel"
          style={ttsDrag.pos ? { left: ttsDrag.pos.x, top: ttsDrag.pos.y, bottom: "auto", right: "auto" } : undefined}
        >
          <div className="test-tts-title" onMouseDown={ttsDrag.onMouseDown} style={{ cursor: "grab" }}>Animation TTS Test</div>
          <textarea
            value={testText}
            onChange={(e) => setTestText(e.target.value)}
            placeholder="Enter phrase to test speech + subtitle highlighting"
          />
          <div className="test-tts-actions">
            <button type="button" onClick={startTesterSpeech} disabled={testSpeaking || testText.trim().length === 0}>
              Speak Test
            </button>
            <button type="button" onClick={stopTesterSpeech} disabled={!testSpeaking}>
              Stop
            </button>
          </div>
          <div className="test-tts-note">Set VITE_SHOW_TTS_TEST_UI=0 to hide this panel.</div>
        </section>
      )}

      {LAYOUT_DEBUG_UI_ENABLED && (
        <section
          ref={debugDrag.nodeRef as React.RefObject<HTMLElement>}
          className="layout-debug-panel"
          style={debugDrag.pos ? { left: debugDrag.pos.x, top: debugDrag.pos.y, bottom: "auto", right: "auto" } : undefined}
        >
          <div className="layout-debug-title" onMouseDown={debugDrag.onMouseDown} style={{ cursor: "grab" }}>Layout Debug</div>
          <div className="layout-debug-row">
            <button
              type="button"
              onClick={applyDefaultPlacementPreset}
              disabled={!toolsDisplayMode && !showWeatherTile}
            >
              Default Placement
            </button>
            <select
              value={selectedTilePreset}
              onChange={(e) => handleTilePresetChange(e.target.value as TilePresetId)}
              aria-label="Tile Preset"
            >
              <option value="none">No Tile</option>
              <option value="animation-only">Animation Only</option>
              <option value="large-default">Large Default Tile</option>
              <option value="large-weather-daily">Large Daily Weather Tile</option>
              <option value="large-weather-weekly">Large Weekly Weather Tile</option>
              <option value="large-timer">Large Timer Tile</option>
              <option value="triple-blank">3 Blank Tiles (Side by Side)</option>
              <option value="quad-blank">4 Blank Tiles (2 x 2)</option>
              <option value="double-blank">2 Blank Tiles</option>
            </select>
          </div>
          {showWeatherTile && (selectedTilePreset === "large-weather-daily" || selectedTilePreset === "large-weather-weekly") && (
            <div className="layout-debug-row">
              <button
                type="button"
                onClick={requestWeatherTileRefresh}
                disabled={weatherRefreshPhase === "requested"}
              >
                {weatherRefreshPhase === "requested"
                  ? "Refreshing Weather..."
                  : weatherRefreshPhase === "queued"
                    ? "Refresh Queued"
                    : weatherRefreshPhase === "loaded"
                      ? "Refresh Weather API (Updated)"
                      : weatherRefreshPhase === "error"
                        ? "Retry Weather API Refresh"
                        : "Refresh Weather API"}
              </button>
              <button
                type="button"
                onClick={() => setDebugMaxPrecipBars((v) => !v)}
              >
                {debugMaxPrecipBars ? "Precip Graph: Max" : "Precip Graph: Normal"}
              </button>
              <button
                type="button"
                onClick={() => setDebugMaxHumidityBars((v) => !v)}
              >
                {debugMaxHumidityBars ? "Humidity Graph: Max" : "Humidity Graph: Normal"}
              </button>
            </div>
          )}
          {showWeatherTile && (selectedTilePreset === "large-weather-daily" || selectedTilePreset === "large-weather-weekly") && (
            <div className="layout-debug-note">{weatherRefreshMessage}</div>
          )}
          {showWeatherTile && (selectedTilePreset === "large-weather-daily" || selectedTilePreset === "large-weather-weekly") && (
            <div className="layout-debug-row">
              <select
                value={debugWeatherIcon}
                onChange={(e) => setDebugWeatherIcon(e.target.value as "auto" | "sunny" | "partly-cloudy" | "rain" | "snow" | "storm" | "fog")}
                aria-label="Weather Icon Override"
              >
                <option value="auto">Icon: Auto</option>
                <option value="sunny">Icon: Sunny</option>
                <option value="partly-cloudy">Icon: Partly Cloudy</option>
                <option value="rain">Icon: Rain</option>
                <option value="snow">Icon: Snow</option>
                <option value="storm">Icon: Thunderstorm</option>
                <option value="fog">Icon: Fog</option>
              </select>
              <input
                type="number"
                value={debugWeatherTempInput}
                onChange={(e) => setDebugWeatherTempInput(e.target.value)}
                placeholder="Temp override (F)"
                aria-label="Temperature Override"
              />
            </div>
          )}
          {activeTilePreset === "large-timer" && (
            <div className="layout-debug-row">
              <input type="number" value={timerHoursInput} onChange={(e) => setTimerHoursInput(e.target.value)} placeholder="Hours" min="0" max="99" aria-label="Timer hours" />
              <input type="number" value={timerMinutesInput} onChange={(e) => setTimerMinutesInput(e.target.value)} placeholder="Minutes" min="0" max="59" aria-label="Timer minutes" />
              <input type="number" value={timerSecondsInput} onChange={(e) => setTimerSecondsInput(e.target.value)} placeholder="Seconds" min="0" max="59" aria-label="Timer seconds" />
            </div>
          )}
          <div className="layout-debug-note">Enable with VITE_SHOW_LAYOUT_DEBUG_UI=1</div>
        </section>
      )}
    </div>
  );
}

export default App;
