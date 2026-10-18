"""Existing transport, browser security, tool routing and offline voice integration."""

import asyncio
from uuid import uuid4, uuid5

import httpx
import pytest
from fastapi.testclient import TestClient

from apps.edge.hardware import SimulatedHardware
from apps.edge.presence.sensors import SimulatedSensor
from apps.edge.runtime import EdgeRuntime
from apps.server.agent.messages import LLMMessage, LLMResponse, ToolCall
from apps.server.main import create_app
from packages.presence import PresenceOptions, PresenceReading
from packages.protocol import SyncedTimer
from tests.conftest import OPERATOR_TOKEN
from tests.test_agent_api import FunctionProvider, final
from tests.test_browser_security import ORIGIN, WRITE, configure, pair
from tests.test_edge_integration import live_server, until
from tests.test_presence import Clock
from tests.test_voice_endtoend import edge_settings
from tests.voice_fixtures import WAKE_FRAME, Detector, Microphone, Speaker


async def test_presence_transport_events_and_browser_settings_receipts(settings, tmp_path):
    configure(settings)
    settings.browser.allow_http_loopback = True
    settings.browser.origins = ["http://127.0.0.1"]  # Replaced after binding below.
    settings.browser.devices["mirror-1"].display_control = True
    settings.agent.allow_mutations = True
    clock, sensor, hardware = Clock(), SimulatedSensor(), SimulatedHardware()
    sensor.feed("PRESENT")
    async with live_server(settings) as (app, port):
        origin = f"http://127.0.0.1:{port}"
        settings.browser.origins = [origin]
        edge = edge_settings(tmp_path, port)
        edge.voice.enabled = False
        edge.presence = PresenceOptions(
            enabled=True,
            present_confirm=0.0,
            absent_confirm=0.0,
            absence_timeout=2.0,
            minimum_awake=0.0,
        )
        edge.presence_driver = "simulated"
        runtime = EdgeRuntime(
            edge, hardware, presence_sensor=sensor, presence_clock=lambda: clock.now
        )
        task = asyncio.create_task(runtime.run())
        try:
            await asyncio.wait_for(runtime.connected.wait(), 5)
            sensor.feed("PRESENT")
            await until(
                lambda: (
                    app.state.gateway.states["mirror-1"].presence is not None
                    and app.state.gateway.states["mirror-1"].presence.confirmed == "PRESENT"
                )
            )
            async with httpx.AsyncClient(base_url=origin) as client:
                begun = await client.post(
                    "/api/browser/pairings",
                    json={"name": "Presence test"},
                    headers={"Origin": origin},
                )
                await client.post(
                    "/api/operator/browser/pairings/approve",
                    json={"code": begun.json()["code"], "device_id": "mirror-1"},
                    headers={"Authorization": "Bearer " + OPERATOR_TOKEN},
                )
                session = (await client.get("/api/browser/pairings")).json()["session"]
                headers = {"Origin": origin, "X-Eve-CSRF": session["csrf"]}
                body = {"request_id": str(uuid4()), "override_percent": 0}
                assert (
                    await client.post("/api/browser/display", json=body, headers={"Origin": origin})
                ).status_code == 403
                first = await client.post("/api/browser/display", json=body, headers=headers)
                assert first.status_code == 200 and first.json()["status"] == "accepted"
                again = await client.post("/api/browser/display", json=body, headers=headers)
                assert again.json()["replayed"]
                assert hardware.commands == [65, 0]
                await until(
                    lambda: app.state.gateway.states["mirror-1"].presence.display == "asleep"
                )
                frame = (await client.get("/api/browser/state")).json()
                assert frame["presence"]["simulated"] and frame["presence"]["target_percent"] == 0
                events = await app.state.services.events.read(
                    app.state.browser.principal({"device_id": "mirror-1"})
                )
                assert {e["type"] for e in events["events"]} >= {
                    "presence.detected",
                    "display.awake",
                    "display.asleep",
                }
                # Identical readings do not append an unbounded stream of events.
                count = events["cursor"]
                current = app.state.gateway.states["mirror-1"].presence
                await app.state.services.presence_update("mirror-1", current, current)
                assert (
                    await app.state.services.events.read(
                        app.state.browser.principal({"device_id": "mirror-1"})
                    )
                )["cursor"] == count
                clock.advance(2)
                await client.post(
                    "/api/browser/display",
                    json={"request_id": str(uuid4()), "release_override": True},
                    headers=headers,
                )
                assert hardware.commands[-1] == 65
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


@pytest.mark.parametrize("grant,mutations", [(False, False), (False, True), (True, False)])
def test_browser_physical_settings_require_explicit_grant_and_mutation_permission(
    settings, grant, mutations
):
    configure(settings)
    settings.browser.devices["mirror-1"].display_control = grant
    settings.agent.allow_mutations = mutations
    with TestClient(create_app(settings), base_url=ORIGIN) as client:
        session = pair(client)
        response = client.post(
            "/api/browser/display",
            json={"request_id": str(uuid4()), "override_percent": 0},
            headers={**WRITE, "X-Eve-CSRF": session["csrf"]},
        )
        assert response.status_code == 403


def test_browser_cannot_configure_serial_gpio_or_another_device(settings):
    configure(settings)
    with TestClient(create_app(settings), base_url=ORIGIN) as client:
        session = pair(client)
        for extra in [{"port": "/dev/ttyACM0"}, {"device_id": "other"}, {"shell": "anything"}]:
            response = client.post(
                "/api/browser/display",
                json={"request_id": str(uuid4()), "override_percent": 0, **extra},
                headers={**WRITE, "X-Eve-CSRF": session["csrf"]},
            )
            assert response.status_code == 422


async def test_local_wake_and_alarm_protection_while_backend_unreachable(tmp_path):
    edge = edge_settings(tmp_path, 1)
    edge.presence = PresenceOptions(
        enabled=True,
        present_confirm=0.0,
        absent_confirm=0.0,
        absence_timeout=0.0,
        minimum_awake=0.0,
    )
    edge.presence_driver = "simulated"
    sensor, hardware, mic, speaker = SimulatedSensor(), SimulatedHardware(), Microphone(), Speaker()
    sensor.feed("ABSENT")
    runtime = EdgeRuntime(
        edge,
        hardware,
        presence_sensor=sensor,
        audio_source=mic,
        detector=Detector(),
        speaker=speaker,
    )
    task = asyncio.create_task(runtime.run())
    try:
        await until(lambda: runtime.voice.ready and hardware.commands == [65, 0])
        assert not runtime.connected.is_set()
        await mic.emit(WAKE_FRAME, 5)
        await until(lambda: runtime.voice.state == "LISTENING")
        assert hardware.commands == [65, 0, 65]
        await runtime.voice.set_muted(True)
        # Independent alarm playback still protects backlight when voice is muted/offline.
        await runtime.voice._playback_activity(True, uuid4())
        await runtime.display.tick(PresenceReading())
        assert runtime.display.status.activity_protected and hardware.commands[-1] == 65
        await runtime.voice.cancel()
        assert runtime.display.status.activity_protected
        await runtime.voice._playback_activity(False, None)
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


async def test_llm_brightness_path_is_arbitrated_by_local_manual_policy(settings, tmp_path):
    settings.agent.allow_mutations = True

    async def model(messages, tools):
        if messages[-1].role == "tool":
            return final("Target accepted; physical brightness is unmeasured.")
        return LLMResponse(
            LLMMessage(
                "assistant",
                tool_calls=(ToolCall("brightness", "mirror.set_brightness", {"percent": 42}),),
            ),
            "fixture",
            "fixture-model",
        )

    async with live_server(settings, llm_provider=FunctionProvider(model)) as (app, port):
        edge = edge_settings(tmp_path, port)
        edge.voice.enabled = False
        edge.presence = PresenceOptions(
            enabled=True,
            present_confirm=0.0,
            absent_confirm=0.0,
            absence_timeout=0.0,
            minimum_awake=0.0,
        )
        sensor, hardware = SimulatedSensor(), SimulatedHardware()
        sensor.feed("ABSENT")
        runtime = EdgeRuntime(edge, hardware, presence_sensor=sensor)
        task = asyncio.create_task(runtime.run())
        try:
            await asyncio.wait_for(runtime.connected.wait(), 5)
            await until(lambda: hardware.commands == [65, 0])
            async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}") as client:
                response = await client.post(
                    "/api/agent/turn",
                    headers={"Authorization": "Bearer " + OPERATOR_TOKEN},
                    json={
                        "request_id": str(uuid4()),
                        "text": "Set the mirror brightness to 42 percent.",
                    },
                )
                assert (
                    response.status_code == 200 and "Target accepted" in response.json()["response"]
                )
            assert runtime.display.status.settings.preferred_percent == 42
            assert runtime.display.status.override_active and hardware.commands == [65, 0, 42]
            await runtime.display.tick(PresenceReading(state="ABSENT", health="healthy"))
            assert hardware.commands == [65, 0, 42]
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


async def test_undismissed_offline_alarm_protects_after_audio_and_sensor_failure(tmp_path):
    edge = edge_settings(tmp_path, 1)
    edge.presence = PresenceOptions(
        enabled=True, absent_confirm=0.0, absence_timeout=0.0, minimum_awake=0.0, activity_grace=0.0
    )
    edge.presence_driver = "simulated"
    sensor, hardware, speaker = SimulatedSensor(), SimulatedHardware(), Speaker()
    sensor.feed("ABSENT")
    runtime = EdgeRuntime(
        edge,
        hardware,
        presence_sensor=sensor,
        audio_source=Microphone(),
        detector=Detector(),
        speaker=speaker,
    )
    task = asyncio.create_task(runtime.run())
    try:
        await asyncio.wait_for(runtime.voice.started.wait(), 5)
        timer_id = uuid4()
        alarm_id = uuid5(timer_id, "alarm")
        row = SyncedTimer(
            timer_id=timer_id, alarm_id=alarm_id, status="EXPIRED", version=1, deadline=None
        )
        await asyncio.to_thread(runtime.voice.store.replace, [row], runtime.voice.utc_clock())
        await until(lambda: runtime.voice.store.receipt(alarm_id) == "completed")
        assert "alarms" in runtime.display.machine.activity
        sensor.feed("UNKNOWN", "unavailable")
        await runtime.display.tick(PresenceReading())
        assert runtime.display.status.activity_protected and hardware.commands[-1] == 65
        # Completed audio must not release an undismissed alarm or replay it.
        count = len(speaker.completed)
        await until(lambda: not runtime.voice.player.busy)
        await runtime.voice.set_muted(True)
        await runtime.voice.cancel()
        assert "alarms" in runtime.display.machine.activity and len(speaker.completed) == count
        await runtime.voice.dismiss(alarm_id)
        await until(lambda: "alarms" not in runtime.display.machine.activity)
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
