"""Versioned volatile voice state, separate from the existing application v1 contract."""

from typing import Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from apps.server.services.events import ApplicationSnapshot
from packages.protocol import DeviceId, EdgeVoicePayload


class VoiceEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1]
    event_id: UUID
    revision: int = Field(ge=1)
    timestamp: AwareDatetime
    device_id: DeviceId
    type: Literal[
        "assistant.transcribing",
        "assistant.thinking",
        "assistant.tool_executing",
        "assistant.synthesizing",
        "assistant.delivering",
        "assistant.speaking",
        "assistant.follow_up",
        "assistant.error",
        "assistant.edge_state",
        "assistant.playback",
    ]
    payload: dict[str, Any]


class VoiceDeviceState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device_id: DeviceId
    edge: EdgeVoicePayload | None = None
    connected: bool = False
    last_success: AwareDatetime | None = None
    application: ApplicationSnapshot | None = None


class AlarmDeliveryState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    alarm_id: UUID
    device_id: DeviceId
    delivery_status: Literal[
        "pending", "delivered", "started", "completed", "cancelled", "failed", "indeterminate"
    ]
    updated_at: AwareDatetime | None
    pending: bool


class AlarmDeliverySnapshot(BaseModel):
    available: bool = False
    alarms: list[AlarmDeliveryState] = Field(default_factory=list)


class VoiceSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = 1
    revision: int = Field(ge=0)
    volatile: Literal[True] = True
    expires_after_seconds: float = Field(gt=0)
    resync_required: bool = False
    events: list[VoiceEvent]
    devices: list[VoiceDeviceState]
    alarm_delivery: AlarmDeliverySnapshot = Field(default_factory=AlarmDeliverySnapshot)
