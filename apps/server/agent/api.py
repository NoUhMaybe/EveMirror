from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from apps.server.agent.sessions import SessionError
from apps.server.auth import principal_dependency
from packages.protocol import DeviceId


class SessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    device_id: DeviceId | None = None


class TurnRequest(SessionRequest):
    text: str = Field(min_length=1, max_length=8192)
    request_id: UUID = Field(default_factory=uuid4, strict=False)
    session_id: UUID | None = Field(default=None, strict=False)

    @field_validator("text")
    @classmethod
    def nonblank(cls, value):
        if not value.strip() or len(value.encode()) > 16384:
            raise ValueError("Text is empty or too large")
        return value


def agent_router(settings, orchestrator, mcp, configuration_error):
    router = APIRouter(prefix="/api/agent")

    principal = principal_dependency(settings)

    def translate(operation):
        try:
            return operation()
        except SessionError as exc:
            raise HTTPException(exc.status, exc.code) from None

    identity_dependency = Depends(principal)

    @router.post("/sessions")
    async def create(body: SessionRequest, identity=identity_dependency):
        session = translate(lambda: orchestrator.sessions.create(identity, body.device_id))
        return {"session_id": session.id, "idle_seconds": settings.agent.session_idle_seconds}

    @router.post("/sessions/{session_id}/reset")
    async def reset(session_id: UUID, identity=identity_dependency):
        translate(lambda: orchestrator.sessions.reset(session_id, identity))
        return {"status": "reset"}

    @router.post("/sessions/{session_id}/cancel")
    async def cancel(session_id: UUID, identity=identity_dependency):
        requested = translate(lambda: orchestrator.sessions.cancel(session_id, identity))
        return {"cancel_requested": requested}

    @router.post("/turn")
    async def turn(body: TurnRequest, identity=identity_dependency):
        try:
            return await orchestrator.turn(
                identity,
                body.text,
                body.request_id,
                body.session_id,
                body.device_id,
            )
        except SessionError as exc:
            raise HTTPException(exc.status, exc.code) from None

    @router.get("/status")
    async def status(identity=identity_dependency):
        return {
            "provider": settings.llm_provider,
            "model": orchestrator.provider.model if orchestrator.provider else None,
            "configured": orchestrator.provider is not None,
            "configuration_error": configuration_error,
            "cloud_allowed": settings.allow_cloud,
            "fallback": "disabled",
            "streaming": False,
            "session_idle_seconds": settings.agent.session_idle_seconds,
            "tools": orchestrator.registry.status(identity, settings.agent),
            "mcp": mcp.status(),
        }

    return router
