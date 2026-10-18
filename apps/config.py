"""Environment-only runtime configuration. No implicit .env reads."""

from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

from packages.protocol import DeviceId


def validate_secret(secret: SecretStr) -> SecretStr:
    value = secret.get_secret_value()
    if len(value) < 32 or not value.isascii() or any(char.isspace() for char in value):
        raise ValueError("Tokens must contain at least 32 ASCII characters without whitespace")
    return secret


Token = Annotated[SecretStr, Field(repr=False)]


def http_endpoint(value: str, *, remote_tls: bool = False) -> str:
    if "\\" in value or any(char.isspace() or ord(char) < 32 for char in value):
        raise ValueError("Endpoint URLs must not contain whitespace or backslashes")
    AnyHttpUrl(value)
    parsed = urlsplit(value)
    try:
        port = parsed.port
    except ValueError:
        raise ValueError("Invalid endpoint port") from None
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or port == 0
    ):
        raise ValueError("Use an HTTP(S) endpoint without credentials, query or fragment")
    if (
        remote_tls
        and parsed.scheme != "https"
        and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
    ):
        raise ValueError("Remote MCP endpoints require HTTPS")
    return value.rstrip("/")


class PrivateConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class AgentLimits(PrivateConfig):
    max_tool_calls: int = Field(default=8, ge=1, le=32)
    max_tool_rounds: int = Field(default=4, ge=1, le=8)
    tool_timeout: float = Field(default=10, ge=0.01, le=60)
    turn_timeout: float = Field(default=90, ge=0.05, le=300)
    max_argument_bytes: int = Field(default=8192, ge=128, le=32768)
    max_result_bytes: int = Field(default=16384, ge=256, le=65536)
    max_context_bytes: int = Field(default=131072, ge=4096, le=1048576)
    max_context_messages: int = Field(default=64, ge=4, le=256)
    session_idle_seconds: float = Field(default=60, ge=0.05, le=3600)
    max_sessions: int = Field(default=128, ge=1, le=1024)
    max_turns_per_session: int = Field(default=64, ge=1, le=256)
    allow_mutations: bool = False


class AgentClient(PrivateConfig):
    token: Token
    device_ids: set[DeviceId] = Field(default_factory=set)
    allow_mutations: bool = False
    home_entities: set[str] = Field(default_factory=set)


class TimerSettings(PrivateConfig):
    max_active: int = Field(default=128, ge=1, le=1024)
    max_duration_seconds: int = Field(default=604800, ge=1, le=31536000)
    reconcile_seconds: float = Field(default=30, ge=0.01, le=60)


class WeatherSettings(PrivateConfig):
    enabled: bool = True
    location: str = Field(default="Frisco, Texas, USA", min_length=1, max_length=160)
    latitude: float = Field(default=33.1507, ge=-90, le=90)
    longitude: float = Field(default=-96.8236, ge=-180, le=180)
    timezone: str = "America/Chicago"
    units: Literal["imperial", "metric"] = "imperial"
    forecast_url: str = "https://api.open-meteo.com/v1/forecast"
    geocoding_url: str = "https://geocoding-api.open-meteo.com/v1/search"
    current_ttl: float = Field(default=600, ge=1, le=3600)
    daily_ttl: float = Field(default=3600, ge=1, le=10800)
    weekly_ttl: float = Field(default=10800, ge=1, le=21600)
    max_stale: float = Field(default=86400, ge=1, le=172800)
    max_locations: int = Field(default=32, ge=1, le=128)
    timeout: float = Field(default=8, ge=0.05, le=30)

    @field_validator("timezone")
    @classmethod
    def zone(cls, value):
        try:
            ZoneInfo(value)
        except (KeyError, ValueError):
            raise ValueError("Unknown IANA timezone") from None
        return value

    @field_validator("forecast_url", "geocoding_url")
    @classmethod
    def endpoint(cls, value):
        return http_endpoint(value, remote_tls=True)


HomeAction = Literal[
    "turn_on",
    "turn_off",
    "set_level",
    "activate_scene",
    "power",
    "play",
    "pause",
    "stop",
    "set_volume",
    "volume_up",
    "volume_down",
    "select_source",
    "send_remote_command",
]


class HomeEntity(PrivateConfig):
    aliases: list[str] = Field(default_factory=list, max_length=32)
    actions: set[HomeAction] = Field(default_factory=set)
    remote_entity: str | None = Field(default=None, pattern=r"^remote\.[a-z0-9_]+$")
    remote_commands: dict[
        Literal["HOME", "BACK", "UP", "DOWN", "LEFT", "RIGHT", "SELECT", "PLAY", "PAUSE"], str
    ] = Field(default_factory=dict)

    @field_validator("remote_commands")
    @classmethod
    def commands(cls, value):
        if any(
            not command or len(command) > 64 or any(c.isspace() for c in command)
            for command in value.values()
        ):
            raise ValueError("Remote commands must be fixed single button identifiers")
        return value


class HomeSettings(PrivateConfig):
    url: str | None = Field(default=None, repr=False)
    token: SecretStr | None = Field(default=None, repr=False)
    allow_insecure_lan: bool = False
    entities: dict[str, HomeEntity] = Field(default_factory=dict)
    timeout: float = Field(default=5, ge=0.05, le=30)
    discovery_ttl: float = Field(default=10, ge=0.01, le=300)

    @model_validator(mode="after")
    def policy(self):
        import re

        if self.url:
            self.url = http_endpoint(self.url, remote_tls=not self.allow_insecure_lan)
        if bool(self.url) != bool(self.token):
            raise ValueError("Home Assistant requires both endpoint and token")
        if len(self.entities) > 128 or any(
            not re.fullmatch(
                r"(?:light|switch|scene|media_player|sensor|binary_sensor)\.[a-z0-9_]+", entity
            )
            for entity in self.entities
        ):
            raise ValueError("Only explicitly approved non-sensitive entity domains are supported")
        return self


class SearchSettings(PrivateConfig):
    url: str | None = Field(default=None, repr=False)
    token: SecretStr | None = Field(default=None, repr=False)
    allow_insecure_lan: bool = False
    timeout: float = Field(default=8, ge=0.05, le=30)
    max_results: int = Field(default=5, ge=1, le=10)

    @model_validator(mode="after")
    def endpoint(self):
        if self.url:
            self.url = http_endpoint(self.url, remote_tls=not self.allow_insecure_lan)
        return self


class MCPToolPolicy(PrivateConfig):
    # Trusted administrator policy; server-supplied annotations never grant permissions.
    description: str = Field(min_length=1, max_length=1024)
    permission: Literal["read_only", "low_risk", "sensitive"] = "read_only"
    mutates: bool = False
    requires_confirmation: bool = False
    timeout: float = Field(default=10, ge=0.05, le=60)

    @model_validator(mode="after")
    def category(self):
        if self.mutates and self.permission == "read_only":
            raise ValueError("Mutating MCP tools cannot be classified read_only")
        return self


class MCPServer(PrivateConfig):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,23}$")
    transport: Literal["stdio", "streamable_http"]
    command: str | None = Field(default=None, repr=False)
    args: list[str] = Field(default_factory=list, repr=False)
    env: dict[str, SecretStr] = Field(default_factory=dict, repr=False)
    url: str | None = Field(default=None, repr=False)
    bearer_token: SecretStr | None = Field(default=None, repr=False)
    allowed_tools: dict[str, MCPToolPolicy] = Field(default_factory=dict)
    connect_timeout: float = Field(default=10, ge=0.1, le=60)

    @model_validator(mode="after")
    def endpoint(self):
        if not self.allowed_tools or len(self.allowed_tools) > 32:
            raise ValueError("MCP requires an explicit allowlist of 1 to 32 tools")
        if any(len(name) > 128 for name in self.allowed_tools):
            raise ValueError("MCP tool name is too long")
        if self.transport == "stdio":
            if not self.command or self.url or self.bearer_token:
                raise ValueError("stdio requires command, without URL or bearer token")
        elif not self.url or self.command or self.args or self.env:
            raise ValueError("streamable_http requires URL, without process configuration")
        else:
            self.url = http_endpoint(self.url, remote_tls=True)
        return self


class ServerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EVE_SERVER_",
        env_nested_delimiter="__",
        extra="forbid",
        hide_input_in_errors=True,
    )

    operator_token: Token
    edge_tokens: dict[DeviceId, SecretStr] = Field(repr=False)
    command_timeout: float = Field(default=5, ge=0.1, le=30)
    heartbeat_timeout: float = Field(default=45, ge=1, le=300)
    audio_timeout: float = Field(default=10, ge=0.1, le=60)
    audio_max_seconds: int = Field(default=30, ge=1, le=30)
    max_audio_consumers: int = Field(default=2, ge=1, le=16)
    llm_provider: Literal["ollama", "openai", "anthropic"] = "ollama"
    ollama_base_url: str = Field(default="http://127.0.0.1:11434", repr=False)
    ollama_model: str | None = None
    openai_model: str | None = None
    anthropic_model: str | None = None
    openai_api_key: SecretStr | None = Field(default=None, repr=False)
    anthropic_api_key: SecretStr | None = Field(default=None, repr=False)
    allow_cloud: bool = False
    llm_timeout: float = Field(default=45, ge=0.05, le=180)
    llm_max_output_tokens: int = Field(default=1024, ge=64, le=16384)
    llm_temperature: float | None = Field(default=None, ge=0, le=1)
    ollama_think: bool | None = None
    openai_reasoning_effort: Literal["none", "minimal", "low", "medium", "high", "xhigh"] | None = (
        None
    )
    agent: AgentLimits = Field(default_factory=AgentLimits)
    agent_clients: dict[DeviceId, AgentClient] = Field(default_factory=dict, repr=False)
    mcp_servers: list[MCPServer] = Field(default_factory=list, repr=False)
    agent_prompt_suffix: str = Field(default="", max_length=4096, repr=False)
    database_path: Path = Path("data/server.sqlite3")
    database_busy_ms: int = Field(default=5000, ge=100, le=10000)
    max_operations: int = Field(default=100000, ge=100, le=10000000)
    event_retention: int = Field(default=10000, ge=100, le=100000)
    timers: TimerSettings = Field(default_factory=TimerSettings)
    weather: WeatherSettings = Field(default_factory=WeatherSettings)
    home: HomeSettings = Field(default_factory=HomeSettings)
    search: SearchSettings = Field(default_factory=SearchSettings)

    _ollama_endpoint = field_validator("ollama_base_url")(http_endpoint)

    @field_validator("ollama_model", "openai_model", "anthropic_model")
    @classmethod
    def model_name(cls, value):
        if value is not None and (not value.strip() or len(value) > 200):
            raise ValueError("Model names must contain 1 to 200 characters")
        return value

    @model_validator(mode="after")
    def credentials(self):
        values = [validate_secret(self.operator_token).get_secret_value()]
        if len(self.agent_clients) > 32:
            raise ValueError("Configure at most 32 agent clients")
        if not self.edge_tokens or len(self.edge_tokens) > 32:
            raise ValueError("Configure between 1 and 32 edge devices")
        values.extend(
            validate_secret(secret).get_secret_value() for secret in self.edge_tokens.values()
        )
        for client in self.agent_clients.values():
            values.append(validate_secret(client.token).get_secret_value())
            if not client.device_ids <= self.edge_tokens.keys():
                raise ValueError("Agent client refers to an unknown device")
            if not client.home_entities <= self.home.entities.keys():
                raise ValueError("Agent client refers to an unapproved Home Assistant entity")
        if len(set(values)) != len(values):
            raise ValueError("Operator, device and agent-client credentials must all be different")
        if self.llm_provider != "ollama" and not self.allow_cloud:
            raise ValueError("Cloud inference requires explicit allow_cloud=true")
        if len(self.mcp_servers) > 8 or len({s.name for s in self.mcp_servers}) != len(
            self.mcp_servers
        ):
            raise ValueError("Configure at most eight uniquely named MCP servers")
        return self


class EdgeSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EVE_EDGE_",
        extra="forbid",
        hide_input_in_errors=True,
    )

    device_id: DeviceId = "mirror-1"
    server_url: str = "ws://127.0.0.1:8000"
    token: Token
    allow_insecure_lan: bool = False
    serial_port: str | None = None
    serial_timeout: float = Field(default=1, ge=0.1, le=3)
    simulate_hardware: bool = False
    journal_path: Path = Path("data/edge-commands.sqlite3")
    heartbeat_interval: float = Field(default=10, ge=0.2, le=30)
    reconnect_min: float = Field(default=1, ge=0.1, le=30)
    reconnect_max: float = Field(default=30, ge=1, le=300)

    _token_valid = field_validator("token")(validate_secret)

    @model_validator(mode="after")
    def endpoint(self):
        parsed = urlsplit(self.server_url)
        if (
            parsed.scheme not in {"ws", "wss"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise ValueError("server_url must be a ws(s) origin without credentials, query or path")
        if parsed.scheme == "ws" and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            if not self.allow_insecure_lan:
                raise ValueError(
                    "Use wss for LAN connections or explicitly allow an isolated test LAN"
                )
        if self.reconnect_max < self.reconnect_min:
            raise ValueError("reconnect_max must be at least reconnect_min")
        return self
