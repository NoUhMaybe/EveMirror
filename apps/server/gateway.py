"""Connection ownership and correlated command delivery; no hardware imports."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import WebSocket

from apps.config import ServerSettings
from packages.protocol import (
    Command,
    DeviceAck,
    DeviceCommand,
    EdgeState,
    Message,
    SnapshotPayload,
    StateSnapshot,
    utc_now,
)


class GatewayError(Exception):
    def __init__(self, code: str, status_code: int):
        self.code = code
        self.status_code = status_code
        super().__init__(code)


@dataclass
class Connection:
    socket: WebSocket
    state: EdgeState
    pending: dict[UUID, tuple[Command, asyncio.Future]] = field(default_factory=dict)
    send_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    last_hardware_reported_at: datetime | None = None
    capabilities: frozenset[str] = field(default_factory=frozenset)

    async def send(self, message: Message):
        async with self.send_lock:
            async with asyncio.timeout(5):
                exclude = (
                    {"payload": {"edges": {"__all__": {"presence"}}}}
                    if isinstance(message, StateSnapshot) and "presence" not in self.capabilities
                    else None
                )
                await self.socket.send_text(message.model_dump_json(exclude=exclude))


class Gateway:
    def __init__(self, settings: ServerSettings):
        self.settings = settings
        self.connections: dict[str, Connection] = {}
        self.states = {key: EdgeState(device_id=key, online=False) for key in settings.edge_tokens}
        self.audio_received = 0
        self.errors = 0

    def attach(self, device_id: str, socket: WebSocket) -> Connection:
        if device_id in self.connections:
            raise GatewayError("already_connected", 409)
        state = EdgeState(device_id=device_id, online=True, last_heartbeat=utc_now())
        connection = Connection(socket=socket, state=state)
        self.connections[device_id] = connection
        self.states[device_id] = state
        return connection

    def detach(self, device_id: str, connection: Connection):
        if self.connections.get(device_id) is not connection:
            return
        del self.connections[device_id]
        self.states[device_id] = connection.state.model_copy(update={"online": False})
        for _, future in connection.pending.values():
            if not future.done():
                future.set_exception(GatewayError("indeterminate", 502))

    def snapshot(self, device_id: str = "server") -> StateSnapshot:
        return StateSnapshot(
            device_id=device_id,
            payload=SnapshotPayload(
                edges=tuple(self.states.values()),
                audio_received=self.audio_received,
            ),
        )

    def acknowledge(self, connection: Connection, ack: DeviceAck):
        pending = connection.pending.get(ack.request_id)
        if pending and not pending[1].done():
            # A replayed acknowledgment describes a past command, not current hardware state.
            if not ack.payload.replayed and (
                connection.last_hardware_reported_at is None
                or ack.timestamp >= connection.last_hardware_reported_at
            ):
                connection.last_hardware_reported_at = ack.timestamp
                connection.state = connection.state.model_copy(
                    update={"hardware": ack.payload.hardware}
                )
                self.states[ack.device_id] = connection.state
            pending[1].set_result(ack)

    async def command(self, device_id: str, request_id: UUID, payload: Command) -> DeviceAck:
        connection = self.connections.get(device_id)
        if connection is None:
            raise GatewayError("device_offline", 503)
        if payload.action == "set_display_policy" and "presence" not in connection.capabilities:
            raise GatewayError("presence_not_supported", 409)
        pending = connection.pending.get(request_id)
        if pending:
            if pending[0] != payload:
                raise GatewayError("request_conflict", 409)
            return await asyncio.shield(pending[1])
        if len(connection.pending) >= 16:
            raise GatewayError("device_busy", 429)
        future = asyncio.get_running_loop().create_future()
        connection.pending[request_id] = (payload, future)
        now = utc_now()
        message = DeviceCommand(
            device_id=device_id,
            request_id=request_id,
            timestamp=now,
            expires_at=now + timedelta(seconds=self.settings.command_timeout + 2),
            payload=payload,
        )
        try:
            await connection.send(message)
            return await asyncio.wait_for(asyncio.shield(future), self.settings.command_timeout)
        except GatewayError:
            raise
        except (TimeoutError, OSError, RuntimeError):
            self.errors += 1
            raise GatewayError("indeterminate", 504) from None
        finally:
            connection.pending.pop(request_id, None)
            if not future.done():
                future.set_exception(GatewayError("indeterminate", 504))
            # Also consume the error if the original HTTP caller was cancelled.
            if not future.cancelled():
                future.exception()
