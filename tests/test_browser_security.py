from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apps.config import BrowserGrant, BrowserSettings, VoiceGrant
from apps.server.browser.models import BrowserFrame
from apps.server.main import create_app
from tests.conftest import EDGE_TOKEN, OPERATOR_TOKEN

ORIGIN = "https://mirror.test"
WRITE = {"Origin": ORIGIN}
ADMIN = {"Authorization": "Bearer " + OPERATOR_TOKEN}


def configure(settings):
    settings.weather.enabled = False
    settings.voice_devices = {"mirror-1": VoiceGrant()}
    settings.browser = BrowserSettings(
        enabled=True, origins=[ORIGIN], devices={"mirror-1": BrowserGrant()}
    )
    return settings


def pair(client, device="mirror-1", name="Hall mirror"):
    response = client.post("/api/browser/pairings", json={"name": name}, headers=WRITE)
    assert response.status_code == 200
    code = response.json()["code"]
    assert client.get("/api/browser/pairings").json() == {"status": "pending"}
    assert (
        client.post(
            "/api/operator/browser/pairings/approve",
            json={"code": code, "device_id": device},
            headers=ADMIN,
        ).status_code
        == 200
    )
    response = client.get("/api/browser/pairings")
    assert response.status_code == 200
    return response.json()["session"]


def test_pairing_requires_approval_and_uses_opaque_secure_cookies(settings):
    app = create_app(configure(settings))
    with TestClient(app, base_url=ORIGIN) as client:
        assert client.get("/api/browser/state").status_code == 401
        assert client.post("/api/browser/pairings", json={"name": "Mirror"}).status_code == 403
        session = pair(client)
        token = client.cookies.get("__Host-eve_browser_session")
        cookie = client.cookies.jar._cookies["mirror.test"]["/"]["__Host-eve_browser_session"]
        assert cookie.secure and "HttpOnly" in cookie._rest and cookie._rest["SameSite"] == "strict"
        assert token not in str(session) and OPERATOR_TOKEN not in str(session)
        rows = client.portal.call(
            app.state.services.db.run,
            lambda c: [dict(r) for r in c.execute("SELECT * FROM browser_sessions")],
        )
        assert token not in str(rows) and session["csrf"] not in str(rows)
        frame = client.get("/api/browser/state")
        assert frame.status_code == 200 and frame.headers["cache-control"] == "no-store"
        BrowserFrame.model_validate(frame.json())
        assert frame.json()["session"]["device_id"] == "mirror-1"
        assert client.get("/api/state").status_code == 401
        assert client.post("/api/agent/turn", json={"text": "hi"}).status_code == 401


@pytest.mark.parametrize(
    "headers",
    [
        {"Origin": "https://evil.test"},
        {"Origin": "null"},
        {"Sec-Fetch-Site": "cross-site"},
        {"Sec-Fetch-Site": "same-site"},
        {"Host": "evil.test"},
        {"Authorization": "Bearer " + EDGE_TOKEN},
        {"Authorization": "Bearer " + OPERATOR_TOKEN},
    ],
)
def test_browser_origin_and_credentials_are_independent(settings, headers):
    with TestClient(create_app(configure(settings)), base_url=ORIGIN) as client:
        pair(client)
        assert client.get("/api/browser/state", headers=headers).status_code == 403


def test_renewal_rotation_csrf_logout_and_revocation(settings):
    app = create_app(configure(settings))
    with TestClient(app, base_url=ORIGIN) as client:
        session = pair(client)
        old = client.cookies.get("__Host-eve_browser_session")
        assert client.post("/api/browser/session/renew", headers=WRITE).status_code == 403
        renewed = client.post(
            "/api/browser/session/renew", headers={**WRITE, "X-Eve-CSRF": session["csrf"]}
        )
        assert renewed.status_code == 200
        assert client.cookies.get("__Host-eve_browser_session") != old
        assert renewed.json()["session"]["id"] == session["id"]
        assert (
            client.get(
                "/api/browser/session", headers={"Cookie": "__Host-eve_browser_session=" + old}
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/api/browser/session/logout",
                headers={**WRITE, "X-Eve-CSRF": renewed.json()["session"]["csrf"]},
            ).status_code
            == 200
        )
        assert client.get("/api/browser/session").status_code == 401
        session = pair(client)
        assert (
            client.post(
                f"/api/operator/browser/sessions/{session['id']}/revoke", headers=ADMIN
            ).status_code
            == 200
        )
        assert client.get("/api/browser/state").status_code == 401


def test_pairing_expiry_invalid_code_unapproved_device_and_cookie_binding(settings):
    app = create_app(configure(settings))
    with TestClient(app, base_url=ORIGIN) as client:
        response = client.post("/api/browser/pairings", json={"name": "Mirror"}, headers=WRITE)
        code = response.json()["code"]
        for supplied, device, expected in [("ZZZZZZZZ", "mirror-1", 404), (code, "other", 401)]:
            assert (
                client.post(
                    "/api/operator/browser/pairings/approve",
                    json={"code": supplied, "device_id": device},
                    headers=ADMIN,
                ).status_code
                == expected
            )
        client.portal.call(
            app.state.services.db.run,
            lambda c: c.execute("UPDATE browser_pairings SET expires_ms=0"),
        )
        assert (
            client.post(
                "/api/operator/browser/pairings/approve",
                json={"code": code, "device_id": "mirror-1"},
                headers=ADMIN,
            ).status_code
            == 404
        )
        assert client.get("/api/browser/pairings").status_code == 401
        session = pair(client)
        assert (
            client.get(
                "/api/browser/session",
                headers={"Cookie": "__Host-eve_browser_session=" + str(uuid4())},
            ).status_code
            == 401
        )
        client.portal.call(
            app.state.services.db.run,
            lambda c: c.execute(
                "UPDATE browser_sessions SET expires_ms=0 WHERE id=?", (session["id"],)
            ),
        )
        assert client.get("/api/browser/session").status_code == 401


def test_persistent_session_restart_and_immediate_scope_change(settings):
    configure(settings)
    with TestClient(create_app(settings), base_url=ORIGIN) as client:
        pair(client)
        token = client.cookies.get("__Host-eve_browser_session")
    with TestClient(create_app(settings), base_url=ORIGIN) as client:
        client.cookies.set("__Host-eve_browser_session", token, domain="mirror.test", path="/")
        assert client.get("/api/browser/state").status_code == 200
        settings.browser.devices["mirror-1"].captions = True
        assert client.get("/api/browser/state").status_code == 401


def test_timer_actions_are_scoped_durable_and_browser_permissions_enforced(settings):
    configure(settings)
    settings.agent.allow_mutations = True
    app = create_app(settings)
    with TestClient(app, base_url=ORIGIN) as client:
        session = pair(client)
        headers = {**WRITE, "X-Eve-CSRF": session["csrf"]}
        body = {
            "request_id": str(uuid4()),
            "name": "timer.create",
            "arguments": {"duration_seconds": 600, "name": "Tea"},
        }
        assert client.post("/api/browser/actions", json=body, headers=headers).status_code == 403
        settings.browser.devices["mirror-1"].timers = True
        session = pair(client)
        headers["X-Eve-CSRF"] = session["csrf"]
        first = client.post("/api/browser/actions", json=body, headers=headers)
        assert first.status_code == 200 and first.json()["status"] == "success"
        assert client.post("/api/browser/actions", json=body, headers=headers).json()["replayed"]
        frame = client.get("/api/browser/state").json()
        assert len(frame["application"]["timers"]) == 1
        assert frame["application"]["timers"][0]["name"] == "Tea"
        for name, args, status in [
            ("mirror.set_brightness", {"percent": 35}, 422),
            ("timer.create", {"duration_seconds": 1, "device_id": "other"}, 422),
            ("timer.create", {"duration_seconds": 1, "operation_id": str(uuid4())}, 422),
            ("home.turn_off", {"target": "light.other"}, 403),
        ]:
            assert (
                client.post(
                    "/api/browser/actions",
                    json={**body, "name": name, "arguments": args},
                    headers=headers,
                ).status_code
                == status
            )


def test_private_scope_captions_cursors_and_backend_epoch(settings):
    configure(settings)
    app = create_app(settings)
    with TestClient(app, base_url=ORIGIN) as client:
        pair(client)
        voice = app.state.voice
        voice.observe(
            "mirror-1", "assistant.thinking", {"state": "THINKING", "transcript": "private phrase"}
        )
        client.portal.call(
            app.state.services.events.publish,
            "other",
            "mirror-1",
            "weather.updated",
            {"secret": "unrelated"},
        )
        frame = client.get("/api/browser/state").json()
        assert "private phrase" not in str(frame) and "unrelated" not in str(frame)
        assert frame["reset"]
        cursor = frame["events"]["cursor"]
        client.portal.call(
            app.state.services.events.publish,
            "voice:mirror-1",
            "mirror-1",
            "weather.updated",
            {"updated": True},
        )
        next_frame = client.get(f"/api/browser/state?after={cursor}&epoch={frame['epoch']}").json()
        assert not next_frame["reset"] and len(next_frame["events"]["events"]) == 1
        assert next_frame["application"]["revision"] >= next_frame["events"]["cursor"]
        assert client.get(f"/api/browser/state?after=999999&epoch={frame['epoch']}").json()["reset"]
        assert client.get(f"/api/browser/state?after={cursor}&epoch={uuid4()}").json()["reset"]


@pytest.mark.parametrize(
    "origin",
    [
        "http://lan.example",
        "https://mirror.test/path",
        "https://mirror.test/",
        "https://user@mirror.test",
        "*",
    ],
)
def test_browser_requires_explicit_secure_origins(origin):
    with pytest.raises(ValueError):
        BrowserSettings(enabled=True, origins=[origin], devices={"mirror-1": BrowserGrant()})


def test_browser_device_and_caption_scopes_never_cross(settings):
    from pydantic import SecretStr

    configure(settings)
    settings.edge_tokens["mirror-2"] = SecretStr("another-device-token-" + "c" * 32)
    settings.voice_devices["mirror-2"] = VoiceGrant()
    settings.browser.devices["mirror-1"].captions = True
    settings.browser.devices["mirror-2"] = BrowserGrant()
    app = create_app(settings)
    with TestClient(app, base_url=ORIGIN) as client:
        pair(client)
        app.state.voice.observe(
            "mirror-1", "assistant.thinking", {"state": "THINKING", "transcript": "allowed caption"}
        )
        app.state.voice.observe(
            "mirror-2",
            "assistant.thinking",
            {"state": "THINKING", "transcript": "other mirror secret"},
        )
        client.portal.call(
            app.state.services.events.publish,
            "voice:mirror-2",
            "mirror-2",
            "weather.updated",
            {"private": "other mirror weather"},
        )
        first = client.get("/api/browser/state").json()
        assert "allowed caption" in str(first)
        assert "other mirror" not in str(first)
        assert [d["device_id"] for d in first["voice"]["devices"]] == ["mirror-1"]
        pair(client, "mirror-2")
        second = client.get("/api/browser/state").json()
        assert "allowed caption" not in str(second) and "other mirror secret" not in str(second)
        assert second["session"]["device_id"] == "mirror-2"


def test_snapshot_event_race_and_retention_have_authoritative_recovery(settings, monkeypatch):
    app = create_app(configure(settings))
    with TestClient(app, base_url=ORIGIN) as client:
        pair(client)
        first = client.get("/api/browser/state").json()
        hub = app.state.services
        original = hub.snapshot

        async def racing_snapshot(principal):
            await hub.events.publish(principal.id, "mirror-1", "weather.updated", {"raced": True})
            return await original(principal)

        monkeypatch.setattr(hub, "snapshot", racing_snapshot)
        query = f"/api/browser/state?after={first['events']['cursor']}&epoch={first['epoch']}"
        raced = client.get(query).json()
        assert raced["application"]["revision"] > raced["events"]["cursor"]
        monkeypatch.setattr(hub, "snapshot", original)
        recovered = client.get(query).json()
        assert recovered["events"]["events"][0]["payload"] == {"raced": True}
        old_cursor = recovered["events"]["cursor"]
        hub.events.retention = 2
        for _ in range(4):
            client.portal.call(
                hub.events.publish, "voice:mirror-1", "mirror-1", "weather.updated", {}
            )
        reset = client.get(f"/api/browser/state?after={old_cursor}&epoch={first['epoch']}").json()
        assert reset["reset"] and not reset["events"]["events"]
        assert reset["events"]["cursor"] == reset["application"]["revision"]


def test_browser_mutations_require_csrf_and_do_not_expand_operator_access(settings):
    app = create_app(configure(settings))
    with TestClient(app, base_url=ORIGIN) as client:
        session = pair(client)
        for path, body in [
            ("/voice/mute", {"muted": True}),
            ("/voice/cancel", {}),
            ("/session/logout", {}),
            ("/actions", {"name": "timer.create", "request_id": str(uuid4())}),
        ]:
            assert client.post("/api/browser" + path, json=body, headers=WRITE).status_code == 403
        headers = {**WRITE, "X-Eve-CSRF": session["csrf"]}
        assert (
            client.post(
                "/api/browser/voice/mute", json={"muted": True}, headers=headers
            ).status_code
            == 403
        )
        assert client.post("/api/browser/voice/cancel", headers=headers).status_code == 403
        assert client.get("/api/operator/browser/sessions").status_code == 401
        listing = client.get("/api/operator/browser/sessions", headers=ADMIN).json()
        assert listing["sessions"][0]["id"] == session["id"]
        assert "token_hash" not in str(listing) and "csrf" not in str(listing)
        response = client.post(
            "/api/browser/pairings", headers=WRITE, content='{"name":"' + "x" * 40000 + '"}'
        )
        assert response.status_code == 413


def test_mute_ack_must_match_live_connection_and_request(settings):
    from types import SimpleNamespace

    from packages.protocol import VoiceControlAck, VoiceControlAckPayload

    configure(settings)
    settings.browser.devices["mirror-1"].voice_control = True
    app = create_app(settings)
    with TestClient(app, base_url=ORIGIN) as client:
        session = pair(client)
        browser = app.state.browser

        async def verify():
            connection = SimpleNamespace(capabilities={"voice", "voice_control"})

            async def send(message):
                event = VoiceControlAck(
                    device_id="mirror-1",
                    request_id=message.request_id,
                    payload=VoiceControlAckPayload(status="completed", muted=True),
                )
                browser.acknowledge(object(), event)
                assert not browser.controls["mirror-1"][2].done()
                browser.acknowledge(connection, event.model_copy(update={"request_id": uuid4()}))
                assert not browser.controls["mirror-1"][2].done()
                browser.acknowledge(connection, event)

            connection.send = send
            app.state.gateway.connections["mirror-1"] = connection
            result = await browser.mute({"device_id": "mirror-1"}, True)
            assert result == {"status": "completed", "muted": True}
            assert not browser.controls
            app.state.gateway.connections.pop("mirror-1")

        client.portal.call(verify)
        headers = {**WRITE, "X-Eve-CSRF": session["csrf"]}
        assert (
            client.post(
                "/api/browser/voice/mute", headers=headers, json={"muted": "true"}
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/api/browser/voice/mute", headers=headers, json={"muted": True}
            ).status_code
            == 503
        )


def test_static_host_preserves_csp_and_does_not_catch_api_routes(settings, tmp_path):
    configure(settings)
    static = tmp_path / "web"
    (static / "assets").mkdir(parents=True)
    (static / "index.html").write_text("<!doctype html><title>Eve</title>")
    settings.browser.static_root = static
    with TestClient(create_app(settings), base_url=ORIGIN) as client:
        for path in ("/", "/settings"):
            response = client.get(path)
            assert response.status_code == 200
            csp = response.headers["content-security-policy"]
            assert "script-src 'self'" in csp and "unsafe-eval" not in csp
            assert "frame-ancestors 'none'" in csp
        assert client.get("/api/browser/state").status_code == 401
        assert client.get("/api/does-not-exist").status_code == 404


def test_ambient_weather_uses_one_cache_and_includes_real_daily_hours(settings):
    import httpx

    from tests.service_fixtures import FakeClock, WeatherFixture

    configure(settings)
    settings.weather.enabled = True
    clock = FakeClock()
    weather = WeatherFixture(clock)
    app = create_app(
        settings,
        service_clock=clock,
        service_transports={"weather": httpx.MockTransport(weather.handler)},
    )
    with TestClient(app, base_url=ORIGIN) as client:
        pair(client)
        client.get("/api/browser/state")

        async def refreshed():
            task = app.state.browser.refresh_tasks.get("mirror-1")
            if task:
                await task

        client.portal.call(refreshed)
        ambient = client.get("/api/browser/state").json()["ambient_weather"]
        assert len(weather.requests) == 1
        assert len(ambient["daily"]) == 7 and len(ambient["hourly"]) == 24
        assert ambient["hourly"][1]["temperature"] is None
        clock.advance(settings.weather.max_stale + 1)
        assert client.get("/api/browser/state").json()["ambient_weather"] is None


def test_cancel_closes_follow_up_using_existing_edge_session(settings):
    from types import SimpleNamespace

    configure(settings)
    settings.browser.devices["mirror-1"].voice_control = True
    app = create_app(settings)
    with TestClient(app, base_url=ORIGIN) as client:
        session = pair(client)
        voice, gateway = app.state.voice, app.state.gateway
        sid = uuid4()
        voice.observe(
            "mirror-1", "assistant.edge_state", {"state": "FOLLOW_UP", "session_id": str(sid)}
        )
        voice.follow_until["mirror-1"] = 999999999999
        messages = []

        async def send(event):
            messages.append(event)

        gateway.connections["mirror-1"] = SimpleNamespace(send=send)
        try:
            response = client.post(
                "/api/browser/voice/cancel",
                json={},
                headers={**WRITE, "X-Eve-CSRF": session["csrf"]},
            )
        finally:
            gateway.connections.pop("mirror-1")
        assert response.json() == {"status": "cancel_requested"}
        assert messages[0].type == "session.cancel" and messages[0].session_id == sid
        assert "mirror-1" not in voice.follow_until


def test_browser_without_speech_reports_edge_scope_and_older_edge_mute_is_safe(settings):
    from types import SimpleNamespace

    configure(settings)
    settings.voice_devices = {}
    settings.browser.devices["mirror-1"].voice_control = True
    app = create_app(settings)
    with TestClient(app, base_url=ORIGIN) as client:
        session = pair(client)
        state = client.get("/api/browser/state").json()
        assert state["voice"]["devices"][0]["device_id"] == "mirror-1"
        assert not state["voice"]["devices"][0]["connected"]
        app.state.gateway.connections["mirror-1"] = SimpleNamespace(capabilities={"voice"})
        try:
            response = client.post(
                "/api/browser/voice/mute",
                json={"muted": True},
                headers={**WRITE, "X-Eve-CSRF": session["csrf"]},
            )
            assert response.status_code == 503
            assert response.json()["detail"] == "edge_voice_unavailable"
        finally:
            app.state.gateway.connections.pop("mirror-1")


def test_automatic_home_confirmation_expires_but_explicit_view_persists(settings):
    from apps.server.agent.messages import ToolCall
    from apps.server.tools.base import Principal, ToolContext, ToolResult
    from tests.service_fixtures import FakeClock

    configure(settings)
    clock = FakeClock()
    app = create_app(settings, service_clock=clock)
    with TestClient(app, base_url=ORIGIN) as client:
        session = pair(client)
        hub = app.state.services
        principal = Principal("voice:mirror-1", frozenset({"mirror-1"}))
        context = ToolContext(principal, uuid4(), uuid4(), "mirror-1")
        client.portal.call(
            hub.observe,
            ToolCall("home", "home.turn_off", {}),
            ToolResult("success", {"acknowledged": True, "state": None}),
            context,
        )
        assert (
            client.get("/api/browser/state").json()["application"]["views"][0]["view"]
            == "smart_home"
        )
        clock.advance(13)
        assert (
            client.get("/api/browser/state").json()["application"]["views"][0]["view"] == "default"
        )
        response = client.post(
            "/api/browser/actions",
            json={
                "request_id": str(uuid4()),
                "name": "dashboard.show_view",
                "arguments": {"view": "smart_home"},
            },
            headers={**WRITE, "X-Eve-CSRF": session["csrf"]},
        )
        assert response.status_code == 200
        clock.advance(60)
        assert (
            client.get("/api/browser/state").json()["application"]["views"][0]["view"]
            == "smart_home"
        )
