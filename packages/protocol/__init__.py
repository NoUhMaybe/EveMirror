"""Versioned, validated wire contract. No hardware or server imports."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    model_validator,
)

DeviceId = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")]
MAX_FRAME_BYTES = 16_000
MAX_MESSAGE_BYTES = 24_000
MAX_AUDIO_SECONDS = 30
SAMPLE_RATE = 16_000


def utc_now() -> datetime:
    return datetime.now(UTC)


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class Envelope(Model):
    version: Literal[1] = 1
    device_id: DeviceId
    request_id: UUID = Field(default_factory=uuid4)
    session_id: UUID | None = None
    timestamp: AwareDatetime = Field(default_factory=utc_now)


class SetBrightness(Model):
    action: Literal["set_brightness"]
    percent: Annotated[int, Field(ge=0, le=100)]


class GetStatus(Model):
    action: Literal["get_status"]


class SetDisplayMode(Model):
    action: Literal["set_display_mode"]
    mode: Literal["awake", "sleep"]


Command = Annotated[SetBrightness | GetStatus | SetDisplayMode, Field(discriminator="action")]


class DeviceCommand(Envelope):
    type: Literal["device.command"] = "device.command"
    payload: Command
    expires_at: AwareDatetime

    @model_validator(mode="after")
    def bounded_deadline(self):
        duration = (self.expires_at - self.timestamp).total_seconds()
        if not 0 < duration <= 60:
            raise ValueError("Command lifetime must be greater than zero and at most 60 seconds")
        return self


class HardwareStatus(Model):
    connected: bool = False
    target_percent: Annotated[int, Field(ge=0, le=100)] | None = None
    # Original firmware cannot measure/report actual brightness or fade completion.
    actual_percent: None = None
    fade_complete: None = None
    simulated: bool = False


class AckPayload(Model):
    status: Literal["accepted", "completed", "error"]
    replayed: bool = False
    code: Literal[
        "ok", "unavailable", "invalid_ack", "indeterminate", "expired", "conflict", "busy"
    ] = "ok"
    hardware: HardwareStatus = Field(default_factory=HardwareStatus)


class DeviceAck(Envelope):
    type: Literal["device.ack"] = "device.ack"
    payload: AckPayload


class HelloPayload(Model):
    capabilities: tuple[
        Literal["brightness", "pcm_upload", "voice", "playback", "timer_sync", "voice_control"], ...
    ] = ("brightness", "pcm_upload")


class EdgeHello(Envelope):
    type: Literal["edge.hello"] = "edge.hello"
    payload: HelloPayload = Field(default_factory=HelloPayload)


class Heartbeat(Envelope):
    type: Literal["heartbeat"] = "heartbeat"
    payload: HardwareStatus = Field(default_factory=HardwareStatus)


class EdgeState(Model):
    device_id: DeviceId
    online: bool
    last_heartbeat: AwareDatetime | None = None
    hardware: HardwareStatus = Field(default_factory=HardwareStatus)


class SnapshotPayload(Model):
    edges: tuple[EdgeState, ...] = ()
    audio_received: Annotated[int, Field(ge=0)] = 0
    # Explicit until provider/speech services are implemented.
    assistant_state: Literal["UNCONFIGURED"] = "UNCONFIGURED"


class StateSnapshot(Envelope):
    type: Literal["state.snapshot"] = "state.snapshot"
    payload: SnapshotPayload


class AudioBeginPayload(Model):
    encoding: Literal["pcm_s16le"] = "pcm_s16le"
    sample_rate: Literal[16000] = SAMPLE_RATE
    channels: Literal[1] = 1
    total_bytes: Annotated[int, Field(gt=0, le=SAMPLE_RATE * 2 * MAX_AUDIO_SECONDS, multiple_of=2)]


class AudioBegin(Envelope):
    type: Literal["audio.begin"] = "audio.begin"
    session_id: UUID
    payload: AudioBeginPayload


class AudioChunkPayload(Model):
    sequence: Annotated[int, Field(ge=0, le=10_000)]
    # Validated base64 is decoded only by the bounded audio assembler.
    data: Annotated[str, Field(min_length=4, max_length=21_336)]


class AudioChunk(Envelope):
    type: Literal["audio.chunk"] = "audio.chunk"
    session_id: UUID
    payload: AudioChunkPayload


class AudioEndPayload(Model):
    chunks: Annotated[int, Field(gt=0, le=10_000)]


class AudioEnd(Envelope):
    type: Literal["audio.end"] = "audio.end"
    session_id: UUID
    payload: AudioEndPayload


class AudioReceivedPayload(Model):
    total_bytes: int
    status: Literal["received"] = "received"


class AudioReceived(Envelope):
    type: Literal["audio.received"] = "audio.received"
    session_id: UUID
    payload: AudioReceivedPayload


class Cancel(Envelope):
    type: Literal["session.cancel"] = "session.cancel"
    session_id: UUID


class ErrorPayload(Model):
    code: Literal["invalid_message", "invalid_audio", "audio_timeout", "busy", "consumer_failed"]
    message: Annotated[str, Field(max_length=160)]


class ErrorEvent(Envelope):
    type: Literal["error"] = "error"
    payload: ErrorPayload


class PlaybackBeginPayload(Model):
    encoding: Literal["pcm_s16le"] = "pcm_s16le"
    sample_rate: Annotated[int, Field(ge=8000, le=48000)]
    channels: Literal[1] = 1
    total_bytes: Annotated[int, Field(gt=0, le=5_760_000, multiple_of=2)]
    purpose: Literal["speech", "alarm"] = "speech"
    alarm_id: UUID | None = None
    sample_count: Annotated[int | None, Field(gt=0, le=2880000)] = None
    duration_seconds: Annotated[float | None, Field(gt=0, le=60)] = None

    @model_validator(mode="after")
    def valid_audio(self):
        if self.total_bytes > self.sample_rate * 2 * 60:
            raise ValueError("Playback exceeds sixty seconds")
        if (self.purpose == "alarm") != (self.alarm_id is not None):
            raise ValueError("Alarm identity is required only for alarms")
        if self.sample_count is not None and self.sample_count != self.total_bytes // 2:
            raise ValueError("Playback sample count mismatch")
        if (
            self.duration_seconds is not None
            and abs(self.duration_seconds - self.total_bytes / (self.sample_rate * 2))
            > 1 / self.sample_rate
        ):
            raise ValueError("Playback duration mismatch")
        return self


class PlaybackBegin(Envelope):
    type: Literal["playback.begin"] = "playback.begin"
    session_id: UUID
    payload: PlaybackBeginPayload


class PlaybackChunk(Envelope):
    type: Literal["playback.chunk"] = "playback.chunk"
    session_id: UUID
    payload: AudioChunkPayload


class PlaybackEnd(Envelope):
    type: Literal["playback.end"] = "playback.end"
    session_id: UUID
    payload: AudioEndPayload


class PlaybackCancel(Envelope):
    type: Literal["playback.cancel"] = "playback.cancel"
    session_id: UUID


class PlaybackStatusPayload(Model):
    status: Literal[
        "accepted",
        "buffered",
        "started",
        "progress",
        "completed",
        "cancelled",
        "failed",
        "indeterminate",
    ]
    next_sequence: Annotated[int, Field(ge=0, le=10000)] = 0
    position_samples: Annotated[int, Field(ge=0, le=2880000)] = 0
    code: Annotated[str | None, Field(max_length=64)] = None
    alarm_id: UUID | None = None
    started_at: AwareDatetime | None = None


class PlaybackStatus(Envelope):
    type: Literal["playback.status"] = "playback.status"
    session_id: UUID
    payload: PlaybackStatusPayload


VoicePhase = Literal[
    "STARTING",
    "IDLE",
    "WAKE_DETECTED",
    "LISTENING",
    "UPLOADING",
    "TRANSCRIBING",
    "THINKING",
    "TOOL_EXECUTING",
    "SYNTHESIZING",
    "DELIVERING",
    "SPEAKING",
    "FOLLOW_UP",
    "ERROR",
]


class VoiceStatusPayload(Model):
    state: VoicePhase
    conversation_id: UUID | None = None
    transcript: Annotated[str | None, Field(max_length=8192)] = None
    response: Annotated[str | None, Field(max_length=8192)] = None
    language: Annotated[str | None, Field(max_length=32)] = None
    stt_model: Annotated[str | None, Field(max_length=160)] = None
    transcript_final: bool = True
    tool: Annotated[str | None, Field(max_length=160)] = None
    tool_status: Literal["success", "error"] | None = None
    error: Annotated[str | None, Field(max_length=64)] = None
    follow_up_seconds: Annotated[float, Field(ge=0, le=60)] = 0
    metrics: Annotated[dict[str, float], Field(max_length=16)] = Field(default_factory=dict)


class VoiceStatus(Envelope):
    type: Literal["voice.status"] = "voice.status"
    session_id: UUID
    payload: VoiceStatusPayload


class EdgeVoicePayload(Model):
    state: VoicePhase
    muted: bool = True
    microphone: bool = False
    wake_ready: bool = False
    vad_ready: bool = False
    speaker: bool = False
    errors: Annotated[int, Field(ge=0)] = 0
    error: Annotated[str | None, Field(max_length=64)] = None
    input_level_rms: Annotated[float, Field(ge=0, le=1)] = 0
    metrics: Annotated[dict[str, float], Field(max_length=16)] = Field(default_factory=dict)


class EdgeVoiceState(Envelope):
    type: Literal["voice.edge_state"] = "voice.edge_state"
    payload: EdgeVoicePayload


class VoiceControlPayload(Model):
    action: Literal["set_muted"] = "set_muted"
    muted: bool


class VoiceControl(Envelope):
    type: Literal["voice.control"] = "voice.control"
    payload: VoiceControlPayload


class VoiceControlAckPayload(Model):
    status: Literal["completed", "error"]
    muted: bool
    error: Annotated[str | None, Field(max_length=64)] = None


class VoiceControlAck(Envelope):
    type: Literal["voice.control_ack"] = "voice.control_ack"
    payload: VoiceControlAckPayload


class SyncedTimer(Model):
    timer_id: UUID
    alarm_id: UUID
    status: Literal["RUNNING", "PAUSED", "EXPIRED"]
    deadline: AwareDatetime | None
    version: Annotated[int, Field(ge=1)]


class TimerSyncPayload(Model):
    generation: UUID
    sequence: Annotated[int, Field(ge=0, le=63)]
    final: bool
    timers: Annotated[tuple[SyncedTimer, ...], Field(max_length=16)] = ()


class TimerSync(Envelope):
    type: Literal["timer.sync"] = "timer.sync"
    payload: TimerSyncPayload


class TimerSyncReceiptPayload(Model):
    generation: UUID
    status: Literal["stored"] = "stored"


class TimerSyncReceipt(Envelope):
    type: Literal["timer.sync_received"] = "timer.sync_received"
    payload: TimerSyncReceiptPayload


class AlarmDismiss(Envelope):
    type: Literal["alarm.dismiss"] = "alarm.dismiss"
    payload: Annotated[
        UUID, Field(description="Explicitly dismiss an alarm on this authenticated device")
    ]


Message = Annotated[
    DeviceCommand
    | DeviceAck
    | EdgeHello
    | Heartbeat
    | StateSnapshot
    | AudioBegin
    | AudioChunk
    | AudioEnd
    | AudioReceived
    | Cancel
    | ErrorEvent
    | PlaybackBegin
    | PlaybackChunk
    | PlaybackEnd
    | PlaybackCancel
    | PlaybackStatus
    | VoiceStatus
    | EdgeVoiceState
    | VoiceControl
    | VoiceControlAck
    | TimerSync
    | TimerSyncReceipt
    | AlarmDismiss,
    Field(discriminator="type"),
]
MESSAGE_ADAPTER = TypeAdapter(Message)


def parse_message(raw: str | bytes) -> Message:
    if len(raw.encode("utf-8") if isinstance(raw, str) else raw) > MAX_MESSAGE_BYTES:
        raise ValueError("Message size limit exceeded")
    return MESSAGE_ADAPTER.validate_json(raw)
