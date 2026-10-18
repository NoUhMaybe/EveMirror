/* Generated from packages/application/browser.schema.json. Run npm run contracts. */

export type CacheAgeSeconds = number;
export type Condition = string | null;
export type FeelsLike = number | null;
export type HumidityPct = number | null;
export type Kind = "model_estimate";
export type Precipitation = number | null;
export type Temperature = number | null;
export type Time = string | null;
export type WindSpeed = number | null;
export type Condition1 = string | null;
export type Date = string;
export type High = number | null;
export type Kind1 = "forecast";
export type Low = number | null;
export type Precipitation1 = number | null;
export type RainProbabilityPct = number | null;
export type Sunrise = string | null;
export type Sunset = string | null;
export type Daily = Day[];
export type FetchedAt = string;
export type FreshnessTtlSeconds = number;
export type HumidityPct1 = number | null;
export type Kind2 = "forecast";
export type Precipitation2 = number | null;
export type RainProbabilityPct1 = number | null;
export type Temperature1 = number | null;
export type Time1 = string;
export type Hourly = Hour[];
export type Latitude = number;
export type Longitude = number;
export type Name = string;
export type Timezone = string;
export type Source = "open-meteo";
export type SourceAgeSeconds = number | null;
export type SourceTimestamp = string | null;
export type Stale = boolean;
export type Units = "imperial" | "metric";
export type ValidFrom = string | null;
export type ValidUntil = string | null;
export type Version = 1;
export type AlarmId = string;
export type DeviceId = string;
export type ExpiredAt = string;
export type TimerId = string;
export type Alarms = AlarmRecord[];
export type Devices = {
  [k: string]: unknown;
}[];
export type Revision = number;
export type AcknowledgedAt = string | null;
export type CreatedAt = string;
export type Deadline = string | null;
export type DeviceId1 = string;
export type DurationMs = number;
export type ExpiredAt1 = string | null;
export type Id = string;
export type Name1 = string | null;
export type RemainingMs = number;
export type Status =
  | "RUNNING"
  | "PAUSED"
  | "EXPIRED"
  | "CANCELLED"
  | "ACKNOWLEDGED";
export type UpdatedAt = string;
export type Version1 = number;
export type Timers = TimerRecord[];
export type Timestamp = string;
export type Tools = {
  [k: string]: unknown;
}[];
export type Version2 = 1;
export type Views = {
  [k: string]: unknown;
}[];
export type Weather = Forecast[];
export type Epoch = string;
export type Cursor = number;
export type DeviceId2 = string | null;
export type EventId = string;
export type ResourceId = string | null;
export type Scope = string;
export type Sequence = number;
export type Timestamp1 = string;
export type Type =
  | "timer.created"
  | "timer.updated"
  | "timer.expired"
  | "timer.acknowledged"
  | "weather.updated"
  | "home.entity_changed"
  | "media.state_changed"
  | "dashboard.show_view"
  | "tool.execution_completed";
export type Version3 = 1;
export type Events = SemanticEvent[];
export type Version4 = 1;
export type Capabilities = string[];
export type EntityId = string;
export type LastUpdated = string | null;
export type Name2 = string;
export type ObservedAt = string;
export type PowerOff = boolean;
export type PowerOn = boolean;
export type RemoteCommands = string[];
export type Source1 = "home-assistant";
export type State = string;
export type Home = BrowserHome[];
export type Model = string | null;
export type Provider = string;
export type Reset = boolean;
export type ServerTime = string;
export type Csrf = string;
export type DeviceId3 = string;
export type ExpiresAt = string;
export type Id1 = string;
export type Name3 = string;
export type Captions = boolean;
export type Debug = boolean;
export type HomeControl = boolean;
export type HomeEntities = string[];
export type Timers1 = boolean;
export type VoiceControl = boolean;
export type Version5 = 1;
export type AlarmId1 = string;
export type DeliveryStatus =
  | "pending"
  | "delivered"
  | "started"
  | "completed"
  | "cancelled"
  | "failed"
  | "indeterminate";
export type DeviceId4 = string;
export type Pending = boolean;
export type UpdatedAt1 = string | null;
export type Alarms1 = AlarmDeliveryState[];
export type Available = boolean;
export type Connected = boolean;
export type DeviceId5 = string;
export type Error = string | null;
export type Errors = number;
export type InputLevelRms = number;
export type Microphone = boolean;
export type Muted = boolean;
export type Speaker = boolean;
export type State1 =
  | "STARTING"
  | "IDLE"
  | "WAKE_DETECTED"
  | "LISTENING"
  | "UPLOADING"
  | "TRANSCRIBING"
  | "THINKING"
  | "TOOL_EXECUTING"
  | "SYNTHESIZING"
  | "DELIVERING"
  | "SPEAKING"
  | "FOLLOW_UP"
  | "ERROR";
export type VadReady = boolean;
export type WakeReady = boolean;
export type LastSuccess = string | null;
export type Devices1 = VoiceDeviceState[];
export type DeviceId6 = string;
export type EventId1 = string;
export type Revision1 = number;
export type Timestamp2 = string;
export type Type1 =
  | "assistant.transcribing"
  | "assistant.thinking"
  | "assistant.tool_executing"
  | "assistant.synthesizing"
  | "assistant.delivering"
  | "assistant.speaking"
  | "assistant.follow_up"
  | "assistant.error"
  | "assistant.edge_state"
  | "assistant.playback";
export type Version6 = 1;
export type Events1 = VoiceEvent[];
export type ExpiresAfterSeconds = number;
export type ResyncRequired = boolean;
export type Revision2 = number;
export type Version7 = 1;
export type Volatile = true;

export interface BrowserFrame {
  ambient_weather?: Forecast | null;
  application: ApplicationSnapshot;
  epoch: Epoch;
  events: EventPage;
  home: Home;
  model: Model;
  provider: Provider;
  reset: Reset;
  server_time: ServerTime;
  session: BrowserSession;
  version?: Version5;
  voice: VoiceSnapshot;
}
export interface Forecast {
  cache_age_seconds?: CacheAgeSeconds;
  current: Current;
  daily: Daily;
  fetched_at: FetchedAt;
  freshness_ttl_seconds?: FreshnessTtlSeconds;
  hourly: Hourly;
  location: Location;
  measurement_units: MeasurementUnits;
  source?: Source;
  source_age_seconds?: SourceAgeSeconds;
  source_timestamp: SourceTimestamp;
  stale?: Stale;
  units: Units;
  valid_from: ValidFrom;
  valid_until: ValidUntil;
  version?: Version;
}
export interface Current {
  condition: Condition;
  feels_like: FeelsLike;
  humidity_pct: HumidityPct;
  kind?: Kind;
  precipitation: Precipitation;
  temperature: Temperature;
  time: Time;
  wind_speed: WindSpeed;
}
export interface Day {
  condition: Condition1;
  date: Date;
  high: High;
  kind?: Kind1;
  low: Low;
  precipitation: Precipitation1;
  rain_probability_pct: RainProbabilityPct;
  sunrise: Sunrise;
  sunset: Sunset;
}
export interface Hour {
  humidity_pct: HumidityPct1;
  kind?: Kind2;
  precipitation: Precipitation2;
  rain_probability_pct: RainProbabilityPct1;
  temperature: Temperature1;
  time: Time1;
}
export interface Location {
  latitude: Latitude;
  longitude: Longitude;
  name: Name;
  timezone: Timezone;
}
export interface MeasurementUnits {
  [k: string]: string;
}
export interface ApplicationSnapshot {
  alarms?: Alarms;
  availability?: Availability;
  devices?: Devices;
  revision: Revision;
  timers?: Timers;
  timestamp: Timestamp;
  tools?: Tools;
  version?: Version2;
  views?: Views;
  weather?: Weather;
}
export interface AlarmRecord {
  alarm_id: AlarmId;
  device_id: DeviceId;
  expired_at: ExpiredAt;
  timer_id: TimerId;
}
export interface Availability {
  [k: string]: unknown;
}
export interface TimerRecord {
  acknowledged_at: AcknowledgedAt;
  created_at: CreatedAt;
  deadline: Deadline;
  device_id: DeviceId1;
  duration_ms: DurationMs;
  expired_at: ExpiredAt1;
  id: Id;
  name: Name1;
  remaining_ms: RemainingMs;
  status: Status;
  updated_at: UpdatedAt;
  version: Version1;
}
export interface EventPage {
  cursor: Cursor;
  events: Events;
  version?: Version4;
}
export interface SemanticEvent {
  device_id: DeviceId2;
  event_id: EventId;
  payload: Payload;
  resource_id: ResourceId;
  scope: Scope;
  sequence: Sequence;
  timestamp: Timestamp1;
  type: Type;
  version?: Version3;
}
export interface Payload {
  [k: string]: unknown;
}
export interface BrowserHome {
  attributes: Attributes;
  capabilities: Capabilities;
  entity_id: EntityId;
  last_updated: LastUpdated;
  name: Name2;
  observed_at: ObservedAt;
  power_off: PowerOff;
  power_on: PowerOn;
  remote_commands: RemoteCommands;
  source: Source1;
  state: State;
}
export interface Attributes {
  [k: string]: unknown;
}
export interface BrowserSession {
  csrf: Csrf;
  device_id: DeviceId3;
  expires_at: ExpiresAt;
  id: Id1;
  name: Name3;
  permissions: BrowserGrant;
}
export interface BrowserGrant {
  captions?: Captions;
  debug?: Debug;
  home_control?: HomeControl;
  home_entities?: HomeEntities;
  timers?: Timers1;
  voice_control?: VoiceControl;
}
export interface VoiceSnapshot {
  alarm_delivery?: AlarmDeliverySnapshot;
  devices: Devices1;
  events: Events1;
  expires_after_seconds: ExpiresAfterSeconds;
  resync_required?: ResyncRequired;
  revision: Revision2;
  version?: Version7;
  volatile?: Volatile;
}
export interface AlarmDeliverySnapshot {
  alarms?: Alarms1;
  available?: Available;
}
export interface AlarmDeliveryState {
  alarm_id: AlarmId1;
  delivery_status: DeliveryStatus;
  device_id: DeviceId4;
  pending: Pending;
  updated_at: UpdatedAt1;
}
export interface VoiceDeviceState {
  application?: ApplicationSnapshot | null;
  connected?: Connected;
  device_id: DeviceId5;
  edge?: EdgeVoicePayload | null;
  last_success?: LastSuccess;
}
export interface EdgeVoicePayload {
  error?: Error;
  errors?: Errors;
  input_level_rms?: InputLevelRms;
  metrics?: Metrics;
  microphone?: Microphone;
  muted?: Muted;
  speaker?: Speaker;
  state: State1;
  vad_ready?: VadReady;
  wake_ready?: WakeReady;
}
export interface Metrics {
  [k: string]: number;
}
export interface VoiceEvent {
  device_id: DeviceId6;
  event_id: EventId1;
  payload: Payload1;
  revision: Revision1;
  timestamp: Timestamp2;
  type: Type1;
  version: Version6;
}
export interface Payload1 {
  [k: string]: unknown;
}
