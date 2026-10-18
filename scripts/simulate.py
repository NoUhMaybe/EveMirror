"""Run real loopback HTTP/WS and explicitly simulated hardware, without live services."""

from __future__ import annotations

import asyncio
import secrets
import socket
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import httpx
import uvicorn

from apps.config import EdgeSettings, ServerSettings
from apps.edge.runtime import EdgeRuntime
from apps.server.main import create_app


async def main():
    operator_token, device_token = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    settings = ServerSettings(
        operator_token=operator_token,
        edge_tokens={"simulation": device_token},
    )
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(create_app(settings), log_level="critical"))
    server_task = asyncio.create_task(server.serve(sockets=[listener]))
    try:
        async with asyncio.timeout(5):
            while not server.started:  # noqa: ASYNC110 -- external server readiness
                if server_task.done():
                    server_task.result()
                await asyncio.sleep(0.01)
        with TemporaryDirectory(prefix="eve-simulation-") as temporary:
            edge = EdgeRuntime(
                EdgeSettings(
                    device_id="simulation",
                    token=device_token,
                    server_url=f"ws://127.0.0.1:{port}",
                    simulate_hardware=True,
                    journal_path=Path(temporary) / "commands.sqlite3",
                )
            )
            edge_task = asyncio.create_task(edge.run())
            try:
                await asyncio.wait_for(edge.connected.wait(), 5)
                async with httpx.AsyncClient(
                    base_url=f"http://127.0.0.1:{port}",
                    headers={"Authorization": f"Bearer {operator_token}"},
                ) as client:
                    result = await client.post(
                        "/api/devices/simulation/commands",
                        json={
                            "request_id": str(uuid4()),
                            "command": {"action": "set_brightness", "percent": 35},
                        },
                    )
                    result.raise_for_status()
                    ack = result.json()["payload"]
                    if ack["status"] != "accepted" or not ack["hardware"]["simulated"]:
                        raise RuntimeError("Simulation did not return the expected acknowledgment")
                receipt = await edge.upload_pcm(b"\x01\x00" * 8_000)
                print("Simulated Feather accepted 35%; physical fade completion is unknown.")
                print(f"Gateway received {receipt.payload.total_bytes} in-memory PCM bytes.")
                print("Simulation passed. STT, tools, TTS and physical hardware were not tested.")
            finally:
                edge_task.cancel()
                await asyncio.gather(edge_task, return_exceptions=True)
    finally:
        server.should_exit = True
        await asyncio.wait_for(server_task, 5)
        listener.close()


if __name__ == "__main__":
    asyncio.run(main())
