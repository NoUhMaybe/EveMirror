from fastapi import APIRouter, Depends, HTTPException, Query

from apps.server.auth import principal_dependency
from apps.server.services.common import ServiceError
from apps.server.speech.state import VoiceSnapshot


def application_router(settings, hub, voice=None):
    router = APIRouter(prefix="/api/application")

    principal = principal_dependency(settings)
    authentication = Depends(principal)

    @router.get("/voice")
    async def voice_state(after: int = Query(default=0, ge=0), identity=authentication):
        if not identity.allow_voice_state:
            raise HTTPException(403, "voice_state_not_authorized")
        if voice is None:
            return {"version": 1, "events": []}
        snapshot = voice.snapshot(identity, after)
        for device in snapshot["devices"]:
            try:
                application = await voice.device_application(identity, device["device_id"])
                device["application"] = application.model_dump(mode="json") if application else None
            except ServiceError:
                device["application"] = None
        try:
            snapshot["alarm_delivery"] = await voice.alarm_snapshot(identity)
        except ServiceError:
            snapshot["alarm_delivery"] = {"available": False, "alarms": []}
        return hub.redact(VoiceSnapshot.model_validate(snapshot).model_dump(mode="json"))

    @router.get("/state")
    async def state(identity=authentication):
        try:
            return hub.redact((await hub.snapshot(identity)).model_dump(mode="json"))
        except ServiceError as exc:
            raise HTTPException(503, exc.code) from None

    @router.get("/events")
    async def events(
        after: int = Query(default=0, ge=0),
        limit: int = Query(default=100, ge=1, le=200),
        identity=authentication,
    ):
        try:
            return hub.redact(await hub.events.read(identity, after, limit))
        except ServiceError as exc:
            raise HTTPException(409 if exc.code == "snapshot_required" else 503, exc.code) from None

    return router
