import json
from typing import Any, Literal
from uuid import uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from apps.server.providers.base import json_text
from apps.server.services.common import ServiceError, utc_now
from apps.server.services.models import AlarmRecord, TimerRecord
from apps.server.services.weather import Forecast

View = Literal[
    "default", "weather_current", "weather_daily", "weather_weekly", "timers", "smart_home", "media"
]
Layout = Literal["default", "compact", "focus"]


class SemanticEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = 1
    event_id: str
    timestamp: AwareDatetime
    sequence: int = Field(ge=1)
    scope: str
    device_id: str | None
    type: Literal[
        "timer.created",
        "timer.updated",
        "timer.expired",
        "timer.acknowledged",
        "weather.updated",
        "home.entity_changed",
        "media.state_changed",
        "dashboard.show_view",
        "tool.execution_completed",
        "presence.detected",
        "presence.lost",
        "presence.unknown",
        "presence.unavailable",
        "display.awake",
        "display.asleep",
        "display.brightness_changed",
    ]
    resource_id: str | None
    payload: dict[str, Any]


class ApplicationSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = 1
    timestamp: AwareDatetime
    revision: int = Field(ge=0)
    timers: list[TimerRecord] = Field(default_factory=list)
    alarms: list[AlarmRecord] = Field(default_factory=list)
    weather: list[Forecast] = Field(default_factory=list)
    devices: list[dict] = Field(default_factory=list)
    views: list[dict] = Field(default_factory=list)
    tools: list[dict] = Field(default_factory=list)
    availability: dict[str, Any] = Field(default_factory=dict)


class EventStore:
    def __init__(self, database, retention=10000, clock=utc_now):
        self.db, self.retention, self.clock = database, retention, clock

    def append(self, connection, owner, device_id, type, payload, resource_id=None, event_id=None):
        identity = str(event_id or uuid4())
        connection.execute(
            (
                "INSERT OR IGNORE INTO events(id,timestamp,owner,device_id,type,"
                "resource_id,payload) VALUES (?,?,?,?,?,?,?)"
            ),
            (
                identity,
                self.clock().isoformat(),
                owner,
                device_id,
                type,
                resource_id,
                json_text(payload),
            ),
        )
        # Alarm records are independent of event-log retention and survive until acknowledgment.
        connection.execute(
            "DELETE FROM events WHERE sequence <= (SELECT max(sequence)-? FROM events)",
            (self.retention,),
        )
        return identity

    async def publish(self, owner, device_id, type, payload, resource_id=None):
        return await self.db.run(
            lambda c: self.append(c, owner, device_id, type, payload, resource_id)
        )

    async def read(self, principal, after=0, limit=100):
        def query(connection):
            minimum, maximum = connection.execute(
                "SELECT min(sequence),max(sequence) FROM events"
            ).fetchone()
            if after and minimum and after < minimum - 1:
                raise ServiceError(
                    "snapshot_required", "Event cursor is older than retained history."
                )
            if after > (maximum or 0):
                raise ServiceError(
                    "snapshot_required", "Event cursor belongs to another database generation."
                )
            devices = list(principal.device_ids)
            placeholders = ",".join("?" for _ in devices)
            scope = (
                f"(device_id IS NULL OR device_id IN ({placeholders}))"
                if devices
                else "device_id IS NULL"
            )
            rows = connection.execute(
                f"SELECT * FROM events WHERE owner=? AND sequence>? AND {scope} "
                "ORDER BY sequence LIMIT ?",
                (
                    principal.id,
                    after,
                    *devices,
                    limit,
                ),
            ).fetchall()
            return {
                "version": 1,
                "cursor": maximum or 0,
                "events": [
                    SemanticEvent(
                        event_id=row["id"],
                        timestamp=row["timestamp"],
                        sequence=row["sequence"],
                        scope=row["owner"],
                        device_id=row["device_id"],
                        type=row["type"],
                        resource_id=row["resource_id"],
                        payload=json.loads(row["payload"]),
                    ).model_dump(mode="json")
                    for row in rows
                ],
            }

        result = await self.db.run(query)
        # A truncated page must not skip the rest of this principal's events.
        if len(result["events"]) == limit:
            result["cursor"] = result["events"][-1]["sequence"]
        return result
