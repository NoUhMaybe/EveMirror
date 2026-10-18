"""Run: uvicorn apps.server.main:create_app --factory --host 127.0.0.1."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager, suppress
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from pydantic import Field, ValidationError
from starlette.responses import JSONResponse

from apps.config import ServerSettings
from apps.server.agent.api import agent_router
from apps.server.agent.body_limit import AgentBodyLimit
from apps.server.agent.orchestrator import Orchestrator
from apps.server.agent.sessions import SessionStore
from apps.server.audio import AudioAssembler, AudioError, CompletedAudio
from apps.server.auth import authenticated
from apps.server.gateway import Gateway, GatewayError
from apps.server.providers.base import LLMProvider
from apps.server.providers.factory import create_provider
from apps.server.services.api import application_router
from apps.server.services.common import utc_now as service_now
from apps.server.services.hub import Services
from apps.server.tools.mcp_client import MCPManager
from apps.server.tools.native import register_native
from apps.server.tools.registry import ToolRegistry
from apps.server.tools.services import register_services
from packages.protocol import (
    AudioBegin,
    AudioChunk,
    AudioEnd,
    AudioReceived,
    AudioReceivedPayload,
    Cancel,
    Command,
    DeviceAck,
    EdgeHello,
    ErrorEvent,
    ErrorPayload,
    Heartbeat,
    Model,
    parse_message,
    utc_now,
)

logger = logging.getLogger("eve.server")
AudioConsumer = Callable[[CompletedAudio], Awaitable[None]]


async def receive_text(socket: WebSocket) -> str:
    frame = await socket.receive()
    if frame["type"] == "websocket.disconnect":
        raise WebSocketDisconnect(frame.get("code", 1000))
    if frame.get("text") is None:
        raise ValueError("Only JSON text frames are supported in protocol v1")
    return frame["text"]


class CommandSubmission(Model):
    request_id: UUID = Field(strict=False)
    command: Command


def create_app(
    settings: ServerSettings | None = None,
    audio_consumer: AudioConsumer | None = None,
    llm_provider: LLMProvider | None = None,
    native_clock=None,
    service_clock=None,
    service_transports=None,
) -> FastAPI:
    settings = settings or ServerSettings()
    gateway = Gateway(settings)
    consumers: set[asyncio.Task] = set()
    registry = ToolRegistry()
    register_native(registry, gateway, clock=native_clock)
    services = Services(
        settings, gateway, clock=service_clock or service_now, transports=service_transports
    )
    register_services(registry, services)
    provider, configuration_error = (
        (llm_provider, None) if llm_provider else create_provider(settings)
    )
    sessions = SessionStore(settings.agent)
    mcp = MCPManager(settings.mcp_servers, registry)
    agent = Orchestrator(settings, provider, registry, sessions, mcp, services)

    async def expire_sessions():
        while True:
            await asyncio.sleep(min(5, settings.agent.session_idle_seconds / 2))
            sessions.expire()

    @asynccontextmanager
    async def lifespan(app):
        reaper = None
        try:
            await services.start()
            await mcp.refresh()
            reaper = asyncio.create_task(expire_sessions())
            yield
        finally:
            if reaper:
                reaper.cancel()
                await asyncio.gather(reaper, return_exceptions=True)
            await sessions.close()
            await services.close()
            await mcp.close()
            if provider:
                await provider.close()
            for connection in list(gateway.connections.values()):
                await connection.socket.close(code=1012)
            for task in list(consumers):
                task.cancel()
            await asyncio.gather(*consumers, return_exceptions=True)

    app = FastAPI(
        title="Eve Server",
        version="0.4.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.gateway = gateway
    app.state.agent = agent
    app.state.services = services
    app.include_router(agent_router(settings, agent, mcp, configuration_error))
    app.include_router(application_router(settings, services))
    app.add_middleware(AgentBodyLimit)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, error):
        if request.url.path.startswith(("/api/agent", "/api/application")):
            return JSONResponse({"detail": "invalid_request"}, status_code=422)
        return await request_validation_exception_handler(request, error)

    async def operator(authorization: str | None = Header(default=None)):
        if not authenticated(authorization, settings.operator_token.get_secret_value()):
            raise HTTPException(status_code=401, detail="unauthorized")

    @app.get("/health/live")
    async def liveness():
        return {"status": "ok"}

    @app.get("/api/state", dependencies=[Depends(operator)])
    async def state():
        return gateway.snapshot()

    @app.get("/api/health", dependencies=[Depends(operator)])
    async def diagnostics():
        return {
            "backend": "online",
            "edges": list(gateway.states.values()),
            "audio_received": gateway.audio_received,
            "active_audio_consumers": len(consumers),
            "errors": gateway.errors,
            "provider": settings.llm_provider if provider else "unconfigured",
            "stt": "unconfigured",
            "tts": "unconfigured",
            "home_assistant": "configured" if services.home.configured else "unconfigured",
            "services": services.availability(),
        }

    @app.post("/api/devices/{device_id}/commands", dependencies=[Depends(operator)])
    async def command(device_id: str, submission: CommandSubmission):
        if device_id not in settings.edge_tokens:
            raise HTTPException(status_code=404, detail="unknown_device")
        try:
            return await gateway.command(device_id, submission.request_id, submission.command)
        except GatewayError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.code) from None

    @app.websocket("/ws/edge/{device_id}")
    async def edge(socket: WebSocket, device_id: str):
        credential = settings.edge_tokens.get(device_id)
        # Browser clients cannot use device credentials as their dashboard session.
        if (
            socket.headers.get("origin")
            or credential is None
            or not authenticated(
                socket.headers.get("authorization"),
                credential.get_secret_value(),
            )
        ):
            await socket.close(code=1008)
            return
        await socket.accept()
        connection = None
        audio = AudioAssembler(settings.audio_timeout, settings.audio_max_seconds)
        owned_tasks: dict[UUID, asyncio.Task] = {}
        recent_sessions: set[UUID] = set()

        async def error(code: str, message: str, event=None):
            gateway.errors += 1
            await connection.send(
                ErrorEvent(
                    device_id=device_id,
                    **(
                        {"request_id": event.request_id, "session_id": event.session_id}
                        if event
                        else {}
                    ),
                    payload=ErrorPayload(code=code, message=message),
                )
            )

        async def consume(completed: CompletedAudio):
            try:
                if audio_consumer:
                    async with asyncio.timeout(60):
                        await audio_consumer(completed)
                gateway.audio_received += 1
                await connection.send(
                    AudioReceived(
                        device_id=device_id,
                        request_id=completed.request_id,
                        session_id=completed.session_id,
                        payload=AudioReceivedPayload(total_bytes=len(completed.pcm)),
                    )
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                # Never log provider exception bodies, tokens, transcripts or audio.
                logger.warning(
                    "audio_consumer_failed device_id=%s request_id=%s",
                    device_id,
                    completed.request_id,
                )
                try:
                    await error("consumer_failed", "Audio consumer failed", completed)
                except (OSError, RuntimeError):
                    pass

        try:
            hello = parse_message(await asyncio.wait_for(receive_text(socket), 5))
            if not isinstance(hello, EdgeHello) or hello.device_id != device_id:
                await socket.close(code=1008)
                return
            try:
                connection = gateway.attach(device_id, socket)
            except GatewayError:
                await socket.close(code=1008)
                return
            await connection.send(gateway.snapshot(device_id))
            last_received = time.monotonic()
            invalid_count = 0
            while True:
                try:
                    raw = await asyncio.wait_for(receive_text(socket), 0.5)
                except TimeoutError:
                    if time.monotonic() - last_received > settings.heartbeat_timeout:
                        await socket.close(code=1001)
                        return
                    expired = audio.begin
                    if audio.expire():
                        await error("audio_timeout", "Incomplete audio upload discarded", expired)
                    continue
                try:
                    event = parse_message(raw)
                    if event.device_id != device_id:
                        raise ValueError("Device identity mismatch")
                except (ValueError, ValidationError):
                    invalid_count += 1
                    await error("invalid_message", "Invalid protocol message")
                    if invalid_count >= 3:
                        await socket.close(code=1008)
                        return
                    continue
                last_received = time.monotonic()
                try:
                    if isinstance(event, Heartbeat):
                        connection.last_hardware_reported_at = event.timestamp
                        connection.state = connection.state.model_copy(
                            update={
                                "last_heartbeat": utc_now(),
                                "hardware": event.payload,
                            }
                        )
                        gateway.states[device_id] = connection.state
                        await connection.send(event.model_copy(update={"timestamp": utc_now()}))
                    elif isinstance(event, DeviceAck):
                        gateway.acknowledge(connection, event)
                    elif isinstance(event, AudioBegin):
                        if event.session_id in recent_sessions:
                            raise AudioError("Audio session already used on this connection")
                        if len(recent_sessions) >= 1024:
                            # Reconnect to start a new bounded replay window.
                            await socket.close(code=1012)
                            return
                        audio.start(event)
                        recent_sessions.add(event.session_id)
                    elif isinstance(event, AudioChunk):
                        audio.append(event)
                    elif isinstance(event, AudioEnd):
                        completed = audio.finish(event)
                        if len(consumers) >= settings.max_audio_consumers:
                            await error("busy", "Audio consumer is busy", event)
                            continue
                        task = asyncio.create_task(consume(completed))
                        consumers.add(task)
                        owned_tasks[event.session_id] = task
                        task.add_done_callback(consumers.discard)
                        task.add_done_callback(
                            lambda _, sid=event.session_id: owned_tasks.pop(sid, None)
                        )
                    elif isinstance(event, Cancel):
                        if audio.begin and audio.begin.session_id == event.session_id:
                            audio.clear()
                        task = owned_tasks.get(event.session_id)
                        if task:
                            task.cancel()
                    else:
                        await error("invalid_message", "Message direction is not permitted", event)
                except AudioError:
                    audio.clear()
                    await error(
                        "invalid_audio", "Invalid or incomplete audio upload discarded", event
                    )
        except WebSocketDisconnect:
            pass
        except (TimeoutError, ValueError, RuntimeError, OSError):
            with suppress(RuntimeError, OSError):
                await socket.close(code=1008)
        finally:
            audio.clear()
            tasks = list(owned_tasks.values())
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            if connection:
                gateway.detach(device_id, connection)

    return app
