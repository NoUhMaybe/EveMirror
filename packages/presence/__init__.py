"""Portable presence configuration and minimal diagnostic state; no hardware imports."""

from datetime import datetime
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, model_validator

Percent = Annotated[int, Field(ge=0, le=100)]
Presence = Literal["PRESENT", "ABSENT", "UNKNOWN"]
Health = Literal["healthy", "timeout", "unavailable", "malformed", "disabled"]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class NightSchedule(Model):
    enabled: bool = False
    timezone: str = "UTC"
    start: str = Field(default="22:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    end: str = Field(default="07:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    percent: Percent = 25

    @model_validator(mode="after")
    def valid_zone(self):
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Unknown IANA timezone") from None
        if self.start == self.end:
            raise ValueError("Night schedule start and end must differ")
        return self

    def active(self, now: datetime) -> bool:
        if now.tzinfo is None:
            raise ValueError("Schedule requires timezone-aware time")
        current = now.astimezone(ZoneInfo(self.timezone)).strftime("%H:%M")
        return self.enabled and (
            self.start <= current < self.end
            if self.start < self.end
            else current >= self.start or current < self.end
        )


class PresenceOptions(Model):
    enabled: bool = False
    present_confirm: float = Field(default=1.0, ge=0, le=60)
    absent_confirm: float = Field(default=5.0, ge=0, le=300)
    absence_timeout: float = Field(default=120.0, ge=0, le=86400)
    minimum_awake: float = Field(default=15.0, ge=0, le=3600)
    wake_cooldown: float = Field(default=2.0, ge=0, le=60)
    activity_grace: float = Field(default=15.0, ge=0, le=3600)
    manual_override_seconds: float = Field(default=300.0, ge=1, le=86400)
    preferred_percent: Percent = 65
    unknown_policy: Literal["awake", "hold"] = "awake"
    night: NightSchedule = Field(default_factory=NightSchedule)


class PresenceReading(Model):
    state: Presence = "UNKNOWN"
    health: Health = "unavailable"

    @model_validator(mode="after")
    def unhealthy_is_unknown(self):
        if self.health != "healthy" and self.state != "UNKNOWN":
            raise ValueError("Unhealthy input cannot confirm presence or absence")
        return self


class DisplayPolicyUpdate(Model):
    settings: PresenceOptions | None = None
    override_percent: Percent | None = None
    release_override: bool = False

    @model_validator(mode="after")
    def meaningful(self):
        if self.settings is None and self.override_percent is None and not self.release_override:
            raise ValueError("A settings change or manual override is required")
        if self.release_override and self.override_percent is not None:
            raise ValueError("Cannot set and release an override together")
        return self


class PresenceStatus(Model):
    settings: PresenceOptions = Field(default_factory=PresenceOptions)
    reading: PresenceReading = Field(default_factory=PresenceReading)
    confirmed: Presence = "UNKNOWN"
    driver: Literal["none", "simulated"] = "none"
    simulated: bool = False
    target_percent: Percent | None = None
    acknowledged_percent: Percent | None = None
    display: Literal["awake", "asleep", "unknown"] = "unknown"
    reason: Literal["manual", "activity", "presence", "night", "default", "unknown"] = "default"
    override_active: bool = False
    activity_protected: bool = False
    uncertain: bool = False
