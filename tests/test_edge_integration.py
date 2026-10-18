"""Real loopback ASGI/WebSocket/HTTP, simulated hardware and in-memory audio."""

import asyncio
import socket
from contextlib import asynccontextmanager
from uuid import uuid4

import httpx
import pytest
import uvicorn

from apps.config import EdgeSettings
from apps.edge.hardware import SimulatedHardware
from apps.edge.runtime import EdgeOfflineError, EdgeRuntime, reconnect_delay
from apps.server.main import create_app
from tests.conftest import EDGE_TOKEN, OPERATOR_TOKEN


async def until(predicate):
    async with asyncio.timeout(5):
        while not predicate():  # noqa: ASYNC110 -- observe external uvicorn lifecycle in test
            await asyncio.sleep(0.01)


@asynccontextmanager
async def live_server(settings, consumer=None, **app_kwargs):
    app = create_app(settings, audio_consumer=consumer, **app_kwargs)
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            log_level="critical",
            ws_max_size=24_000,
        )
    )
    task = asyncio.create_task(server.serve(sockets=[listener]))
    try:
        await until(lambda: server.started or task.done())
        if task.done():
            task.result()
        yield app, port
    finally:
        server.should_exit = True
        try:
            await asyncio.wait_for(task, 5)
        finally:
            listener.close()


async def test_edge_audio_command_disconnect_reconnect_and_local_control(settings, tmp_path):
    received = []

    async def consume(audio):
        received.append(audio)

    async with live_server(settings, consume) as (app, port):
        hardware = SimulatedHardware()
        runtime = EdgeRuntime(
            EdgeSettings(
                token=EDGE_TOKEN,
                server_url=f"ws://127.0.0.1:{port}",
                journal_path=tmp_path / "commands.sqlite3",
                heartbeat_interval=0.2,
                reconnect_min=0.3,
                reconnect_max=1,
            ),
            hardware=hardware,
        )
        task = asyncio.create_task(runtime.run())
        try:
            await asyncio.wait_for(runtime.connected.wait(), 5)
            pcm = b"\x04\x01" * 18000  # multiple network frames
            receipt = await runtime.upload_pcm(pcm)
            assert receipt.payload.total_bytes == len(pcm)
            assert received[0].pcm == pcm
            assert received[0].device_id == "mirror-1"
            request_id = str(uuid4())
            async with httpx.AsyncClient(
                base_url=f"http://127.0.0.1:{port}",
                headers={
                    "Authorization": f"Bearer {OPERATOR_TOKEN}",
                },
            ) as client:
                payload = {
                    "request_id": request_id,
                    "command": {"action": "set_brightness", "percent": 35},
                }
                result = await client.post("/api/devices/mirror-1/commands", json=payload)
                assert result.status_code == 200, result.text
                assert result.json()["payload"]["hardware"]["simulated"] is True
                assert hardware.commands == [35]
                first = app.state.gateway.connections["mirror-1"]
                await first.socket.close(code=1012)
                await until(lambda: not runtime.connected.is_set())
                # The local owner survives network interruption and needs no LLM/backend.
                assert (await hardware.set_brightness(12)).target_percent == 12
                with pytest.raises(EdgeOfflineError):
                    await runtime.upload_pcm(b"\0\0")
                await asyncio.wait_for(runtime.connected.wait(), 5)
                await until(lambda: app.state.gateway.connections.get("mirror-1") is not first)
                await until(
                    lambda: app.state.gateway.states["mirror-1"].hardware.target_percent == 12
                )
                replay = await client.post("/api/devices/mirror-1/commands", json=payload)
                assert replay.status_code == 200
                assert replay.json()["request_id"] == request_id
                assert hardware.commands == [35, 12]
                state = (await client.get("/api/state")).json()
                assert state["payload"]["edges"][0]["online"] is True
                assert state["payload"]["edges"][0]["hardware"]["target_percent"] == 12
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


def test_reconnect_backoff_is_bounded():
    assert all(0 < reconnect_delay(attempt, 1, 30) <= 30 for attempt in range(100))
