from fastapi import APIRouter, Depends, HTTPException, Query

from apps.server.auth import principal_dependency
from apps.server.services.common import ServiceError


def application_router(settings, hub):
    router = APIRouter(prefix="/api/application")

    principal = principal_dependency(settings)
    authentication = Depends(principal)

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
