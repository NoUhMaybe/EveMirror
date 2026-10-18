import pytest

from apps.config import ServerSettings

EDGE_TOKEN = "edge-test-token-" + "a" * 32
OPERATOR_TOKEN = "operator-test-token-" + "b" * 32


@pytest.fixture
def settings():
    return ServerSettings(
        operator_token=OPERATOR_TOKEN,
        edge_tokens={"mirror-1": EDGE_TOKEN},
        command_timeout=0.2,
        heartbeat_timeout=2,
        audio_timeout=0.2,
    )
