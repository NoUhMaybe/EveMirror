from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from packages.protocol import DeviceId


class TimerRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    device_id: DeviceId
    name: str | None
    duration_ms: int = Field(gt=0)
    remaining_ms: int = Field(ge=0)
    status: Literal["RUNNING", "PAUSED", "EXPIRED", "CANCELLED", "ACKNOWLEDGED"]
    created_at: AwareDatetime
    deadline: AwareDatetime | None
    expired_at: AwareDatetime | None
    acknowledged_at: AwareDatetime | None
    updated_at: AwareDatetime
    version: int = Field(ge=1)


class AlarmRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    alarm_id: UUID
    timer_id: UUID
    device_id: DeviceId
    expired_at: AwareDatetime
