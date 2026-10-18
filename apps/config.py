"""Environment-only runtime configuration. No implicit .env reads."""

from pathlib import Path
from typing import Annotated
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from packages.protocol import DeviceId


def validate_secret(secret: SecretStr) -> SecretStr:
    value = secret.get_secret_value()
    if len(value) < 32 or not value.isascii() or any(char.isspace() for char in value):
        raise ValueError("Tokens must contain at least 32 ASCII characters without whitespace")
    return secret


Token = Annotated[SecretStr, Field(repr=False)]


class ServerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EVE_SERVER_",
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

    @model_validator(mode="after")
    def credentials(self):
        values = [validate_secret(self.operator_token).get_secret_value()]
        if not self.edge_tokens or len(self.edge_tokens) > 32:
            raise ValueError("Configure between 1 and 32 edge devices")
        values.extend(
            validate_secret(secret).get_secret_value() for secret in self.edge_tokens.values()
        )
        if len(set(values)) != len(values):
            raise ValueError("Operator and device credentials must all be different")
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
