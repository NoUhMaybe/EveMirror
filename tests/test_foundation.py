import json
from datetime import timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from apps.config import EdgeSettings, ServerSettings
from packages.protocol import (
    MESSAGE_ADAPTER,
    DeviceCommand,
    SetBrightness,
    parse_message,
    utc_now,
)
from tests.conftest import EDGE_TOKEN, OPERATOR_TOKEN


def test_protocol_round_trip_and_generated_schema():
    command = DeviceCommand(
        device_id="mirror-1",
        payload=SetBrightness(action="set_brightness", percent=35),
        expires_at=utc_now() + timedelta(seconds=10),
    )
    assert parse_message(command.model_dump_json()) == command
    assert json.loads(Path("packages/protocol/schema.json").read_text()) == (
        MESSAGE_ADAPTER.json_schema()
    )


@pytest.mark.parametrize("percent", [-1, 101, 1.2, "35", True])
def test_brightness_wire_validation(percent):
    with pytest.raises(ValidationError):
        SetBrightness(action="set_brightness", percent=percent)


@pytest.mark.parametrize(
    "patch",
    [
        {"version": 2},
        {"device_id": "../../etc"},
        {"arbitrary": "shell"},
        {"payload": {"action": "shell", "command": "shutdown"}},
        {"timestamp": "2026-10-17T12:00:00"},
    ],
)
def test_reject_invalid_protocol(patch):
    command = DeviceCommand(
        device_id="mirror-1",
        payload=SetBrightness(action="set_brightness", percent=30),
        expires_at=utc_now() + timedelta(seconds=10),
    ).model_dump(mode="json")
    command.update(patch)
    with pytest.raises(ValueError):
        parse_message(json.dumps(command))


def test_limits_and_deadlines():
    with pytest.raises(ValueError, match="size"):
        parse_message(" " * 24_001)
    with pytest.raises(ValueError, match="lifetime"):
        DeviceCommand(
            device_id="mirror-1",
            payload=SetBrightness(action="set_brightness", percent=1),
            expires_at=utc_now() + timedelta(seconds=90),
        )


def test_environment_configuration_and_redaction(monkeypatch):
    monkeypatch.setenv("EVE_SERVER_OPERATOR_TOKEN", OPERATOR_TOKEN)
    monkeypatch.setenv("EVE_SERVER_EDGE_TOKENS", json.dumps({"mirror-1": EDGE_TOKEN}))
    config = ServerSettings()
    assert config.edge_tokens["mirror-1"].get_secret_value() == EDGE_TOKEN
    for rendered in [str(config), repr(config), config.model_dump_json()]:
        assert EDGE_TOKEN not in rendered
        assert OPERATOR_TOKEN not in rendered


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost",
        "ws://192.168.1.10",
        "wss://eve.local/path",
        "wss://eve.local?token=secret",
        "wss://user:secret@eve.local",
        "wss://eve.local/#frag",
    ],
)
def test_edge_rejects_unsafe_endpoint(url):
    with pytest.raises(ValueError):
        EdgeSettings(token=EDGE_TOKEN, server_url=url)


def test_explicit_isolated_lan_and_production_tls():
    assert EdgeSettings(token=EDGE_TOKEN, server_url="wss://eve.local").server_url
    assert EdgeSettings(
        token=EDGE_TOKEN,
        server_url="ws://192.168.1.10",
        allow_insecure_lan=True,
    ).allow_insecure_lan


def test_scoped_secrets_required():
    with pytest.raises(ValueError):
        ServerSettings(operator_token=EDGE_TOKEN, edge_tokens={"mirror-1": EDGE_TOKEN})
    with pytest.raises(ValueError):
        EdgeSettings(token="short")
