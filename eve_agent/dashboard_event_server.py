"""
Local dashboard event server.

- WebSocket clients connect to ws://127.0.0.1:8765
- Runtime components emit JSON events via UDP to 127.0.0.1:8766
- Server broadcasts each event to all connected websocket clients
"""

import asyncio
import json
from typing import Set

import websockets
from tooling import DEFAULT_LOCATION, get_current_weather

WS_HOST = "127.0.0.1"
WS_PORT = 8765
UDP_HOST = "127.0.0.1"
UDP_PORT = 8766

CLIENTS: Set[websockets.WebSocketServerProtocol] = set()


async def ws_handler(websocket: websockets.WebSocketServerProtocol) -> None:
    CLIENTS.add(websocket)
    try:
        async for message in websocket:
            try:
                evt = json.loads(message)
            except Exception:
                continue

            if not isinstance(evt, dict):
                continue

            evt_type = str(evt.get("type", ""))
            if evt_type != "dashboard_refresh_weather":
                continue

            payload = evt.get("payload", {})
            location = DEFAULT_LOCATION
            if isinstance(payload, dict):
                location_raw = payload.get("location")
                if isinstance(location_raw, str) and location_raw.strip():
                    location = location_raw.strip()

            async def refresh_weather() -> None:
                try:
                    weather = await asyncio.to_thread(get_current_weather, location, False, True)
                    envelope = {
                        "type": "tool_context",
                        "payload": {
                            "notes": [f"weather tile manual refresh (location={weather.get('location', location)})"],
                            "payload": {"weather": weather},
                        },
                    }
                    await broadcast(json.dumps(envelope))
                except Exception as exc:
                    err = {
                        "type": "tool_context",
                        "payload": {
                            "notes": [f"weather tile manual refresh failed ({exc})"],
                            "payload": {"weather_error": str(exc), "weather_unavailable": True},
                        },
                    }
                    await broadcast(json.dumps(err))

            asyncio.create_task(refresh_weather())
    finally:
        CLIENTS.discard(websocket)


async def broadcast(message: str) -> None:
    if not CLIENTS:
        return
    dead = []
    for client in CLIENTS:
        try:
            await client.send(message)
        except Exception:
            dead.append(client)
    for client in dead:
        CLIENTS.discard(client)


class UdpProtocol(asyncio.DatagramProtocol):
    def datagram_received(self, data: bytes, addr) -> None:
        try:
            decoded = data.decode("utf-8")
            json.loads(decoded)
        except Exception:
            return
        asyncio.create_task(broadcast(decoded))


async def main() -> None:
    ws_server = await websockets.serve(ws_handler, WS_HOST, WS_PORT)
    loop = asyncio.get_running_loop()
    await loop.create_datagram_endpoint(lambda: UdpProtocol(), local_addr=(UDP_HOST, UDP_PORT))

    print(f"[events] websocket server: ws://{WS_HOST}:{WS_PORT}")
    print(f"[events] udp ingest: {UDP_HOST}:{UDP_PORT}")

    await ws_server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
