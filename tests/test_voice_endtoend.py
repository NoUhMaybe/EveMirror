"""Real authenticated loopback sockets, current agent/tools, simulated audio/model engines."""

import asyncio
import json
from uuid import UUID, uuid4

import httpx
import pytest

from apps.config import EdgeSettings, EdgeVoiceSettings, VoiceGrant
from apps.edge.hardware import SimulatedHardware
from apps.edge.runtime import EdgeRuntime
from tests.conftest import EDGE_TOKEN, OPERATOR_TOKEN
from tests.provider_fixtures import PROVIDERS, mock_provider, tool_results, wire_response
from tests.service_fixtures import FakeClock, HomeFixture, WeatherFixture
from tests.test_agent_api import FunctionProvider, final
from tests.test_edge_integration import live_server, until
from tests.voice_fixtures import STT, TTS, Detector, Microphone, Speaker, say


def edge_settings(tmp_path, port):
    return EdgeSettings(
        token=EDGE_TOKEN,
        server_url=f"ws://127.0.0.1:{port}",
        journal_path=tmp_path / "commands.sqlite3",
        heartbeat_interval=0.2,
        reconnect_min=0.1,
        reconnect_max=1,
        voice=EdgeVoiceSettings(
            enabled=True,
            muted_on_start=False,
            state_path=tmp_path / "voice.sqlite3",
            wake_hits=1,
            min_speech_ms=160,
            silence_ms=160,
            echo_cooldown=0.1,
        ),
    )


@pytest.mark.parametrize("provider_name", PROVIDERS)
async def test_voice_weather_playback_followup_brightness_and_timer_through_every_provider(
    settings, tmp_path, provider_name
):
    settings.speech.enabled = True
    settings.speech.alarm_poll_seconds = 0.05
    home = HomeFixture()
    settings.home = home.settings
    settings.voice_devices = {
        "mirror-1": VoiceGrant(allow_mutations=True, home_entities={"light.bedroom"})
    }
    settings.agent.allow_mutations = True
    clock = FakeClock()
    weather = WeatherFixture(clock)
    stt = STT(
        "turn bedroom lights off and weather today",
        "what about tomorrow",
        "dim mirror",
        "set timer",
    )
    tts, microphone, speaker, detector = TTS(), Microphone(), Speaker(), Detector()
    requests = []

    def model(request):
        body = json.loads(request.content)
        requests.append(body)
        index = len(stt.calls) - 1
        results = tool_results(provider_name, body)
        # Every new turn includes its own latest user message after older tool results.
        if len(requests) % 2:
            calls = [
                [
                    ("today", "weather.current", {}),
                    ("lights", "home.turn_off", {"target": "bedroom lights"}),
                ],
                ("tomorrow", "weather.daily", {"day_offset": 1}),
                ("brightness", "mirror.set_brightness", {"percent": 35}),
                ("timer", "timer.create", {"duration_seconds": 1}),
            ]
            return httpx.Response(
                200,
                json=wire_response(
                    provider_name, "", calls[index] if index == 0 else [calls[index]]
                ),
            )
        assert results[-1]["status"] == "success", results
        return httpx.Response(
            200,
            json=wire_response(
                provider_name,
                [
                    "Today forecast.",
                    "Tomorrow forecast.",
                    "Target is 35%; fade completion is unknown.",
                    "Timer created.",
                ][index],
            ),
        )

    async with live_server(
        settings,
        llm_provider=mock_provider(provider_name, model),
        service_clock=clock,
        speech_stt=stt,
        speech_tts=tts,
        service_transports={
            "weather": httpx.MockTransport(weather.handler),
            "home": httpx.MockTransport(home.handler),
        },
    ) as (app, port):
        hardware = SimulatedHardware()
        runtime = EdgeRuntime(
            edge_settings(tmp_path, port),
            hardware,
            audio_source=microphone,
            detector=detector,
            speaker=speaker,
            voice_utc_clock=clock,
        )
        task = asyncio.create_task(runtime.run())
        try:
            await asyncio.wait_for(runtime.connected.wait(), 5)
            for index in range(4):
                await say(runtime, microphone, wake=index == 0)
                await until(
                    lambda expected=index + 1: (
                        len(tts.calls) == expected and runtime.voice.state == "FOLLOW_UP"
                    )
                )
            assert hardware.status.target_percent == 35
            assert len([request for request in home.requests if request.method == "POST"]) == 1
            assert (
                len(stt.calls) == 4 and len(speaker.completed) >= 5
            )  # one chime + four speech responses
            assert all(audio.sample_rate == 16000 and audio.pcm for audio in stt.calls)
            assert len(app.state.agent.sessions.sessions) == 1
            session = next(iter(app.state.agent.sessions.sessions.values()))
            assert session.owner == "voice:mirror-1" and session.device_id == "mirror-1"
            clock.advance(2)
            await until(
                lambda: len(speaker.completed) == 6
            )  # timer tone, independently of another model turn
            assert len(requests) == 8
            pending = await app.state.services.timers.list(app.state.voice.principal("mirror-1"))
            assert len(pending["alarms"]) == 1
            identity = pending["alarms"][0]["alarm_id"]
            await runtime.voice.dismiss(UUID(identity))
            await until(lambda: app.state.voice.sync_sent.get("mirror-1") is not None)
            async with httpx.AsyncClient(
                base_url=f"http://127.0.0.1:{port}",
                headers={"Authorization": "Bearer " + OPERATOR_TOKEN},
            ) as client:
                response = await client.get("/api/application/voice")
                assert response.status_code == 200
                events = response.json()["events"]
                assert any(
                    event["type"] == "assistant.thinking"
                    and event["payload"].get("transcript") == "what about tomorrow"
                    for event in events
                )
                statuses = [
                    event["payload"]["status"]
                    for event in events
                    if event["type"] == "assistant.playback"
                ]
                assert "started" in statuses and "completed" in statuses
            assert not list(tmp_path.rglob("*.wav"))
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        assert microphone.closed == 1 and not runtime.voice.player.busy


async def test_slow_hardware_command_does_not_block_voice_frames_heartbeats_or_playback(
    settings, tmp_path
):
    settings.speech.enabled = True
    settings.command_timeout = 5
    settings.voice_devices = {"mirror-1": VoiceGrant()}
    stt, tts, microphone, speaker = STT("explain a neural network"), TTS(), Microphone(), Speaker()
    entered, release = asyncio.Event(), asyncio.Event()

    class Hardware(SimulatedHardware):
        async def set_brightness(self, percent):
            entered.set()
            await release.wait()
            return await super().set_brightness(percent)

    async def model(messages, tools):
        return final("A neural network learns patterns from data.")

    async with live_server(
        settings, llm_provider=FunctionProvider(model), speech_stt=stt, speech_tts=tts
    ) as (app, port):
        hardware = Hardware()
        runtime = EdgeRuntime(
            edge_settings(tmp_path, port),
            hardware,
            audio_source=microphone,
            detector=Detector(),
            speaker=speaker,
        )
        task = asyncio.create_task(runtime.run())
        try:
            await asyncio.wait_for(runtime.connected.wait(), 5)
            async with httpx.AsyncClient(
                base_url=f"http://127.0.0.1:{port}",
                headers={"Authorization": "Bearer " + OPERATOR_TOKEN},
            ) as client:
                body = {
                    "request_id": str(uuid4()),
                    "command": {"action": "set_brightness", "percent": 35},
                }
                command = asyncio.create_task(
                    client.post("/api/devices/mirror-1/commands", json=body)
                )
                await asyncio.wait_for(entered.wait(), 2)
                await say(runtime, microphone)
                await until(lambda: runtime.voice.state == "FOLLOW_UP")
                assert not command.done() and len(speaker.completed) == 2
                release.set()
                response = await command
                assert response.json()["payload"]["status"] == "accepted"
                replay = await client.post("/api/devices/mirror-1/commands", json=body)
                assert replay.json()["payload"]["replayed"] and hardware.commands == [35]
        finally:
            release.set()
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
