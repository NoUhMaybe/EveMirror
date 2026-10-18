from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from apps.server.main import create_app
from packages.protocol import (
    AckPayload,
    Cancel,
    DeviceAck,
    EdgeHello,
    HardwareStatus,
    parse_message,
)
from tests.conftest import EDGE_TOKEN, OPERATOR_TOKEN
from tests.test_audio import utterance

OPERATOR = {"Authorization": f"Bearer {OPERATOR_TOKEN}"}
EDGE = {"Authorization": f"Bearer {EDGE_TOKEN}"}


def test_http_auth_scoping_and_invalid_commands(settings):
    with TestClient(create_app(settings)) as client:
        assert client.get("/health/live").json() == {"status": "ok"}
        assert client.get("/api/state").status_code == 401
        assert client.get("/api/state", headers=EDGE).status_code == 401
        state = client.get("/api/state", headers=OPERATOR)
        assert state.status_code == 200
        assert state.json()["payload"]["edges"][0]["online"] is False
        assert EDGE_TOKEN not in state.text and OPERATOR_TOKEN not in state.text
        body = {"request_id": str(uuid4()), "command": {"action": "set_brightness", "percent": 101}}
        assert (
            client.post(
                "/api/devices/mirror-1/commands",
                headers=OPERATOR,
                json=body,
            ).status_code
            == 422
        )
        body["command"]["percent"] = 35
        assert (
            client.post(
                "/api/devices/mirror-1/commands",
                headers=OPERATOR,
                json=body,
            ).status_code
            == 503
        )
        assert (
            client.post(
                "/api/devices/mirror-1/commands",
                headers=EDGE,
                json=body,
            ).status_code
            == 401
        )


@pytest.mark.parametrize(
    "path,headers",
    [
        ("/ws/edge/mirror-1", {}),
        ("/ws/edge/mirror-1", OPERATOR),
        ("/ws/edge/unknown-device", EDGE),
        ("/ws/edge/mirror-1", {**EDGE, "Origin": "https://untrusted.example"}),
    ],
)
def test_websocket_auth_scoping(settings, path, headers):
    with TestClient(create_app(settings)) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(path, headers=headers):
                pytest.fail("Unauthorized socket accepted")


def test_command_ack_correlation_and_snapshot(settings):
    settings = settings.model_copy(update={"command_timeout": 2})
    with TestClient(create_app(settings)) as client:
        with client.websocket_connect("/ws/edge/mirror-1", headers=EDGE) as socket:
            socket.send_text(EdgeHello(device_id="mirror-1").model_dump_json())
            assert socket.receive_json()["type"] == "state.snapshot"
            request_id = uuid4()
            with ThreadPoolExecutor(max_workers=1) as executor:
                response = executor.submit(
                    client.post,
                    "/api/devices/mirror-1/commands",
                    headers=OPERATOR,
                    json={
                        "request_id": str(request_id),
                        "command": {"action": "set_brightness", "percent": 35},
                    },
                )
                command = parse_message(socket.receive_text())
                assert command.request_id == request_id
                assert command.payload.percent == 35
                wrong = DeviceAck(device_id="mirror-1", payload=AckPayload(status="accepted"))
                socket.send_text(wrong.model_dump_json())
                socket.send_text(
                    DeviceAck(
                        device_id="mirror-1",
                        request_id=command.request_id,
                        payload=AckPayload(
                            status="accepted",
                            hardware=HardwareStatus(
                                connected=True,
                                target_percent=35,
                            ),
                        ),
                    ).model_dump_json()
                )
                result = response.result(timeout=5)
                assert result.status_code == 200
                assert result.json()["payload"]["status"] == "accepted"
            snapshot = client.get("/api/state", headers=OPERATOR).json()
            assert snapshot["payload"]["edges"][0]["hardware"]["target_percent"] == 35


def test_command_timeout_reports_indeterminate(settings):
    with TestClient(create_app(settings)) as client:
        with client.websocket_connect("/ws/edge/mirror-1", headers=EDGE) as socket:
            socket.send_text(EdgeHello(device_id="mirror-1").model_dump_json())
            socket.receive_json()
            response = client.post(
                "/api/devices/mirror-1/commands",
                headers=OPERATOR,
                json={
                    "request_id": str(uuid4()),
                    "command": {"action": "get_status"},
                },
            )
            assert response.status_code == 504
            assert response.json()["detail"] == "indeterminate"


def test_audio_receipt_and_duplicate_connection(settings):
    received = []

    async def consume(audio):
        received.append(audio.pcm)

    with TestClient(create_app(settings, audio_consumer=consume)) as client:
        with client.websocket_connect("/ws/edge/mirror-1", headers=EDGE) as socket:
            socket.send_text(EdgeHello(device_id="mirror-1").model_dump_json())
            socket.receive_json()
            for message in utterance():
                socket.send_text(message.model_dump_json())
            assert socket.receive_json()["payload"]["total_bytes"] == 400
            assert received == [b"\x00\x01" * 200]
            with pytest.raises(WebSocketDisconnect):
                with client.websocket_connect("/ws/edge/mirror-1", headers=EDGE) as duplicate:
                    duplicate.send_text(EdgeHello(device_id="mirror-1").model_dump_json())
                    duplicate.receive_json()


def test_audio_idle_timeout_and_invalid_event_recovery(settings):
    with TestClient(create_app(settings)) as client:
        with client.websocket_connect("/ws/edge/mirror-1", headers=EDGE) as socket:
            socket.send_text(EdgeHello(device_id="mirror-1").model_dump_json())
            socket.receive_json()
            socket.send_text(utterance()[0].model_dump_json())
            assert socket.receive_json()["payload"]["code"] == "audio_timeout"
            socket.send_text('{"version":999,"type":"shell"}')
            assert socket.receive_json()["payload"]["code"] == "invalid_message"
            for message in utterance():
                socket.send_text(message.model_dump_json())
            assert socket.receive_json()["type"] == "audio.received"


def test_cancel_discards_upload_and_binary_frames_close_cleanly(settings):
    with TestClient(create_app(settings)) as client:
        with client.websocket_connect("/ws/edge/mirror-1", headers=EDGE) as socket:
            socket.send_text(EdgeHello(device_id="mirror-1").model_dump_json())
            socket.receive_json()
            begin, _, end = utterance()
            socket.send_text(begin.model_dump_json())
            socket.send_text(
                Cancel(
                    device_id="mirror-1",
                    request_id=begin.request_id,
                    session_id=begin.session_id,
                ).model_dump_json()
            )
            socket.send_text(end.model_dump_json())
            assert socket.receive_json()["payload"]["code"] == "invalid_audio"
            socket.send_bytes(b"unsupported binary frame")
            with pytest.raises(WebSocketDisconnect):
                socket.receive_json()


def test_consumer_failure_does_not_leak_details_and_next_turn_recovers(settings, caplog):
    calls = []

    async def consumer(audio):
        calls.append(audio.session_id)
        if len(calls) == 1:
            raise RuntimeError("sensitive provider credential in exception")

    with TestClient(create_app(settings, consumer)) as client:
        with client.websocket_connect("/ws/edge/mirror-1", headers=EDGE) as socket:
            socket.send_text(EdgeHello(device_id="mirror-1").model_dump_json())
            socket.receive_json()
            for message in utterance():
                socket.send_text(message.model_dump_json())
            error = socket.receive_json()
            assert error["payload"]["code"] == "consumer_failed"
            assert "sensitive provider credential" not in str(error) + caplog.text
            for message in utterance():
                socket.send_text(message.model_dump_json())
            assert socket.receive_json()["type"] == "audio.received"
