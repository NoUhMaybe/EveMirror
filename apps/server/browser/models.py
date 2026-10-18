from typing import Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from apps.config import BrowserGrant
from apps.server.services.events import ApplicationSnapshot, SemanticEvent
from apps.server.services.weather import Forecast
from apps.server.speech.state import VoiceSnapshot
from packages.protocol import DeviceId


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PairingRequest(Strict):
    name: str = Field(min_length=1, max_length=80, pattern=r"^[^\x00-\x1f]+$")


class PairingApproval(Strict):
    code: str = Field(pattern=r"^[A-Z2-9]{8}$")
    device_id: DeviceId


class BrowserSession(Strict):
    id: UUID
    device_id: DeviceId
    name: str
    expires_at: str
    csrf: str
    permissions: BrowserGrant


class EventPage(Strict):
    version: Literal[1] = 1
    cursor: int = Field(ge=0)
    events: list[SemanticEvent]


class BrowserHome(Strict):
    entity_id: str
    name: str = Field(max_length=160)
    state: str = Field(max_length=160)
    source: Literal["home-assistant"]
    observed_at: AwareDatetime
    last_updated: str | None
    attributes: dict[str, Any]
    capabilities: list[str]
    remote_commands: list[str]
    power_on: bool
    power_off: bool


class BrowserFrame(Strict):
    version: Literal[1] = 1
    epoch: UUID
    reset: bool
    server_time: str
    session: BrowserSession
    application: ApplicationSnapshot
    events: EventPage
    voice: VoiceSnapshot
    ambient_weather: Forecast | None = None
    home: list[BrowserHome]
    provider: str
    model: str | None


BrowserTool = Literal[
    "weather.current",
    "weather.daily",
    "weather.weekly",
    "home.list_entities",
    "home.get_state",
    "media.get_state",
    "home.turn_on",
    "home.turn_off",
    "home.set_level",
    "home.activate_scene",
    "media.power",
    "media.play",
    "media.pause",
    "media.stop",
    "media.set_volume",
    "media.volume_up",
    "media.volume_down",
    "media.select_source",
    "media.send_remote_command",
    "timer.create",
    "timer.pause",
    "timer.resume",
    "timer.cancel",
    "timer.acknowledge",
    "dashboard.show_view",
    "dashboard.dismiss_view",
    "dashboard.set_layout",
]


class BrowserAction(Strict):
    request_id: UUID
    name: BrowserTool
    arguments: dict[str, Any] = Field(default_factory=dict, max_length=8)


class MuteRequest(Strict):
    muted: bool = Field(strict=True)
