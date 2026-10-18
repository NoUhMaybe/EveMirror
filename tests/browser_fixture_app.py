"""Opt-in loopback-only Playwright fixture. Never packaged or used by production."""

import asyncio
import os
import tempfile
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx
from fastapi import HTTPException, Request

from apps.config import BrowserGrant, BrowserSettings, ServerSettings, VoiceGrant
from apps.edge.hardware import SimulatedHardware
from apps.edge.runtime import EdgeRuntime
from apps.server.agent.messages import LLMMessage, LLMResponse, ToolCall
from apps.server.main import create_app
from tests.conftest import EDGE_TOKEN, OPERATOR_TOKEN
from tests.service_fixtures import FakeClock, HomeFixture, forecast_fixture
from tests.test_agent_api import FunctionProvider, final
from tests.test_edge_integration import until
from tests.test_voice_endtoend import edge_settings
from tests.voice_fixtures import STT, TTS, Detector, Microphone, Speaker, capture_ready, say

TEST_TOKEN = "loopback-dashboard-fixture-" + "x" * 32


def create_fixture_app():
    if os.environ.get("EVE_DASHBOARD_SIMULATION") != "1":
        raise RuntimeError("This fixture requires explicit EVE_DASHBOARD_SIMULATION=1")
    origin = os.environ.get("EVE_DASHBOARD_TEST_ORIGIN", "http://127.0.0.1:8766")
    from urllib.parse import urlsplit

    if urlsplit(origin).hostname != "127.0.0.1":
        raise ValueError("Fixture accepts loopback only")
    port = urlsplit(origin).port
    directory = tempfile.TemporaryDirectory(prefix="eve-dashboard-test-")
    root = Path(directory.name).resolve()
    if not root.is_relative_to(Path(tempfile.gettempdir()).resolve()):
        raise ValueError("Fixture directory outside the OS temporary root")
    clock, home = FakeClock(datetime.now(UTC)), HomeFixture()
    settings = ServerSettings(
        operator_token=OPERATOR_TOKEN,
        edge_tokens={"mirror-1": EDGE_TOKEN},
        database_path=root / "server.sqlite3",
        home=home.settings,
        browser=BrowserSettings(
            enabled=True,
            origins=[origin],
            allow_http_loopback=True,
            static_root=Path("apps/dashboard/dist"),
            devices={
                "mirror-1": BrowserGrant(
                    captions=True,
                    timers=True,
                    home_control=True,
                    voice_control=True,
                    debug=True,
                    home_entities={"light.bedroom", "media_player.tv"},
                )
            },
        ),
        voice_devices={
            "mirror-1": VoiceGrant(
                allow_mutations=True, home_entities={"light.bedroom", "media_player.tv"}
            )
        },
    )
    settings.agent.allow_mutations = settings.speech.enabled = True
    settings.speech.alarm_poll_seconds = 0.05
    stt, microphone, speaker = STT(), Microphone(), Speaker()
    long_reply = False

    original_play = speaker.play

    def play(audio, stop, started, progress):
        def begin():
            started()
            if speaker.block:
                progress(audio.sample_count // 2)

        return original_play(audio, stop, begin, progress)

    speaker.play = play

    class Synthesis(TTS):
        async def synthesize(self, text):
            speaker.block = True  # Only speech is held; the wake chime already completed.
            return await super().synthesize(text)

    tts = Synthesis()

    async def model(messages, tools):
        if messages[-1].role == "tool":
            if long_reply:
                return final("A little more detail for your day. " * 35)
            return final("Here's your week ahead. Your ten-minute tea timer is running.")
        return LLMResponse(
            LLMMessage(
                "assistant",
                tool_calls=(
                    ToolCall("weather", "weather.weekly", {}),
                    ToolCall("timer", "timer.create", {"duration_seconds": 600, "name": "Tea"}),
                    ToolCall("view", "dashboard.show_view", {"view": "weather_weekly"}),
                ),
            ),
            "fixture",
            "fixture-model",
            "tool_calls",
        )

    async def weather(request):
        day = (
            clock()
            .astimezone(ZoneInfo("America/Chicago"))
            .replace(hour=0, minute=0, second=0, microsecond=0)
        )
        return httpx.Response(200, json=forecast_fixture(day))

    app = create_app(
        settings,
        llm_provider=FunctionProvider(model),
        service_clock=clock,
        speech_stt=stt,
        speech_tts=tts,
        service_transports={
            "weather": httpx.MockTransport(weather),
            "home": httpx.MockTransport(home.handler),
        },
    )
    runtime = EdgeRuntime(
        edge_settings(root, port),
        SimulatedHardware(),
        audio_source=microphone,
        detector=Detector(),
        speaker=speaker,
        voice_utc_clock=clock,
    )
    original_lifespan = app.router.lifespan_context
    runtime_task = None

    @asynccontextmanager
    async def lifespan(application):
        nonlocal runtime_task
        async with original_lifespan(application):
            task = asyncio.create_task(runtime.run())
            runtime_task = task
            try:
                yield
            finally:
                speaker.block = False
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
        directory.cleanup()

    app.router.lifespan_context = lifespan

    @app.post("/__test__/{action}")
    async def control(action: str, request: Request):
        nonlocal long_reply
        if (
            request.client.host not in {"127.0.0.1", "::1"}
            or request.headers.get("authorization") != "Bearer " + TEST_TOKEN
        ):
            raise HTTPException(403)
        if action != "shutdown":
            await asyncio.wait_for(runtime.connected.wait(), 5)
        if action == "reset":
            long_reply = False
            speaker.block = False
            await runtime.voice.cancel()
            await app.state.voice.cancel("mirror-1")

            def reset(c):
                for table in ("alarm_delivery", "alarms", "timers", "views", "resources", "events"):
                    c.execute("DELETE FROM " + table)

            await app.state.services.db.run(reset)
            app.state.browser.epoch = uuid4()
            app.state.voice.events["mirror-1"].clear()
            app.state.voice.sessions.clear()
            app.state.voice.follow_until.clear()
            app.state.voice.capture_until.clear()
            stt.texts.clear()
            clock.value = datetime.now(UTC)
            await runtime.voice.set_muted(False)
            return {"status": "reset"}
        if action == "shutdown":
            speaker.block = False
            runtime_task.cancel()
            await asyncio.gather(runtime_task, return_exceptions=True)
            app.state.stop_server()
            return {"status": "stopped"}
        if action in {"speak", "long-speak"}:
            long_reply = action == "long-speak"
            stt.texts.append("Show me the weather this week and set a timer for ten minutes.")
            await say(runtime, microphone)
            await until(lambda: runtime.voice.state == "SPEAKING" and runtime.voice.player.busy)
            return {"status": "speaking", "stt_calls": len(stt.calls), "tts_calls": len(tts.calls)}
        if action == "finish":
            speaker.block = False
            await until(lambda: capture_ready(runtime, "FOLLOW_UP"))
            return {"status": "follow_up"}
        if action == "expire":
            clock.advance(601)
            await app.state.services.timers.reconcile()
            return {"status": "expired"}
        raise HTTPException(404)

    return app


if __name__ == "__main__":
    from urllib.parse import urlsplit

    import uvicorn

    application = create_fixture_app()
    fixture_port = urlsplit(
        os.environ.get("EVE_DASHBOARD_TEST_ORIGIN", "http://127.0.0.1:8766")
    ).port
    server = uvicorn.Server(
        uvicorn.Config(
            application,
            host="127.0.0.1",
            port=fixture_port,
            access_log=False,
            log_level="warning",
            ws_max_size=24000,
        )
    )
    application.state.stop_server = lambda: setattr(server, "should_exit", True)
    server.run()
