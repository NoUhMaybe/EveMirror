"""Same-origin browser routes. Operator pairing approval remains a bearer-only API."""

import hmac
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from starlette.responses import JSONResponse

from apps.server.auth import authenticated
from apps.server.browser.models import (
    BrowserAction,
    DisplayRequest,
    MuteRequest,
    PairingApproval,
    PairingRequest,
)
from apps.server.browser.sessions import csrf


def cookie_name(request, purpose="session"):
    return ("__Host-" if request.url.scheme == "https" else "") + "eve_browser_" + purpose


def set_cookie(response, request, token, duration, purpose="session"):
    response.set_cookie(
        cookie_name(request, purpose),
        token,
        max_age=duration,
        secure=request.url.scheme == "https",
        httponly=True,
        samesite="strict",
        path="/",
    )


class BrowserSecurity:
    def __init__(self, app, settings):
        self.app, self.config = app, settings

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith("/api/browser"):
            return await self.app(scope, receive, send)
        request = Request(scope)
        origin = request.headers.get("origin")
        allowed = self.config.origins
        host = request.headers.get("host", "")
        good = (
            self.config.enabled
            and any(
                urlsplit(value).netloc == host and urlsplit(value).scheme == request.url.scheme
                for value in allowed
            )
            and (origin is None or origin in allowed)
            and request.headers.get("sec-fetch-site") not in {"cross-site", "same-site"}
            and not request.headers.get("authorization")
            and (request.method in {"GET", "HEAD"} or origin in allowed)
        )
        if not good:
            return await JSONResponse({"detail": "browser_origin_not_allowed"}, 403)(
                scope, receive, send
            )

        async def secure_send(message):
            if message["type"] == "http.response.start":
                message["headers"] = list(message.get("headers", [])) + [
                    (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"x-frame-options", b"DENY"),
                ]
            await send(message)

        return await self.app(scope, receive, secure_send)


def browser_router(settings, service):
    router = APIRouter()
    sessions, config = service.sessions, settings.browser

    async def identity(request: Request):
        token = request.cookies.get(cookie_name(request))
        row = await sessions.authenticate(token)
        if request.method not in {"GET", "HEAD"} and not hmac.compare_digest(
            request.headers.get("x-eve-csrf", ""), csrf(token)
        ):
            raise HTTPException(403, "csrf_required")
        return row, token

    async def operator(request: Request):
        if request.headers.get("origin") or not authenticated(
            request.headers.get("authorization"), settings.operator_token.get_secret_value()
        ):
            raise HTTPException(401, "operator_required")
        if not config.enabled:
            raise HTTPException(404, "browser_disabled")

    authentication = Depends(identity)

    @router.post("/api/browser/pairings")
    async def pairing(body: PairingRequest, request: Request, response: Response):
        token, code = await sessions.begin(
            body.name, request.cookies.get(cookie_name(request, "pairing"))
        )
        set_cookie(response, request, token, config.pairing_seconds, "pairing")
        return {"status": "pending", "code": code, "expires_in": config.pairing_seconds}

    @router.get("/api/browser/pairings")
    async def pairing_status(request: Request, response: Response):
        result = await sessions.claim(request.cookies.get(cookie_name(request, "pairing")))
        if result is None:
            return {"status": "pending"}
        row, token = result
        set_cookie(response, request, token, config.session_seconds)
        response.delete_cookie(
            cookie_name(request, "pairing"),
            path="/",
            secure=request.url.scheme == "https",
            httponly=True,
            samesite="strict",
        )
        return {"status": "paired", "session": sessions.public(row, token)}

    @router.post("/api/operator/browser/pairings/approve", dependencies=[Depends(operator)])
    async def approve(body: PairingApproval):
        await sessions.approve(body.code, body.device_id)
        return {"status": "approved", "device_id": body.device_id}

    @router.get("/api/operator/browser/sessions", dependencies=[Depends(operator)])
    async def list_sessions():
        return {"sessions": await sessions.list()}

    @router.post(
        "/api/operator/browser/sessions/{session_id}/revoke", dependencies=[Depends(operator)]
    )
    async def revoke(session_id: UUID):
        await sessions.revoke(session_id)
        return {"status": "revoked"}

    @router.get("/api/browser/session")
    async def session(auth=authentication):
        row, token = auth
        return {"session": sessions.public(row, token)}

    @router.post("/api/browser/session/renew")
    async def renew(request: Request, response: Response, auth=authentication):
        row, token = await sessions.renew(*auth)
        set_cookie(response, request, token, config.session_seconds)
        return {"session": sessions.public(row, token)}

    @router.post("/api/browser/session/logout")
    async def logout(request: Request, response: Response, auth=authentication):
        await sessions.revoke(auth[0]["id"])
        response.delete_cookie(
            cookie_name(request),
            path="/",
            secure=request.url.scheme == "https",
            httponly=True,
            samesite="strict",
        )
        return {"status": "revoked"}

    @router.get("/api/browser/state")
    async def state(
        after: int | None = Query(default=None, ge=0),
        voice_after: int = Query(default=0, ge=0),
        epoch: UUID | None = None,
        auth=authentication,
    ):
        return await service.frame(*auth, after, voice_after, str(epoch) if epoch else None)

    @router.post("/api/browser/actions")
    async def action(body: BrowserAction, auth=authentication):
        return await service.action(auth[0], body)

    @router.post("/api/browser/voice/mute")
    async def mute(body: MuteRequest, auth=authentication):
        return await service.mute(auth[0], body.muted)

    @router.post("/api/browser/voice/cancel")
    async def cancel(auth=authentication):
        return await service.cancel(auth[0])

    @router.post("/api/browser/display")
    async def display(body: DisplayRequest, auth=authentication):
        return await service.display(auth[0], body)

    return router
