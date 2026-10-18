import asyncio
import json

import httpx
import pytest
from pydantic import SecretStr

from apps.config import AgentClient, VoiceGrant
from apps.edge.hardware import HardwareError, SimulatedHardware
from apps.edge.runtime import EdgeRuntime
from apps.server.agent.messages import LLMMessage, LLMResponse, ToolCall
from apps.server.providers.base import ProviderError
from packages.audio import SpeechError
from packages.protocol import PlaybackStatus, VoiceStatus
from tests.conftest import EDGE_TOKEN, OPERATOR_TOKEN
from tests.service_fixtures import HomeFixture
from tests.test_agent_api import FunctionProvider, final
from tests.test_edge_integration import live_server, until
from tests.test_voice_endtoend import edge_settings
from tests.voice_fixtures import (
    SILENCE_FRAME,
    SPEECH_FRAME,
    STT,
    TTS,
    Detector,
    Microphone,
    Speaker,
    capture_ready,
    say,
)


@pytest.mark.parametrize(
    "mode",
    [
        "denied",
        "unavailable",
        "indeterminate",
        "provider_timeout",
        "blank",
        "unconfigured",
        "no_grant",
        "tts_failed",
    ],
)
async def test_voice_failures_are_truthful_and_return_to_a_usable_state(settings, tmp_path, mode):
    settings.speech.enabled = True
    settings.agent.allow_mutations = True
    settings.voice_devices = (
        {} if mode == "no_grant" else {"mirror-1": VoiceGrant(allow_mutations=mode != "denied")}
    )
    stt, tts = STT("" if mode == "blank" else "dim my mirror"), TTS()
    microphone, speaker = Microphone(), Speaker()

    async def model(messages, tools):
        if mode == "provider_timeout":
            raise ProviderError("provider_timeout")
        if messages[-1].role == "tool":
            return final(
                "Everything succeeded."
            )  # Pipeline must not speak this over a failed tool.
        return LLMResponse(
            LLMMessage(
                "assistant", tool_calls=(ToolCall("dim", "mirror.set_brightness", {"percent": 35}),)
            ),
            "test",
            "test-model",
            "tool_calls",
        )

    class Hardware(SimulatedHardware):
        async def set_brightness(self, percent):
            if mode in {"unavailable", "indeterminate"}:
                self.commands.append(percent)
                raise HardwareError(mode)
            return await super().set_brightness(percent)

    if mode == "tts_failed":

        async def broken(text):
            tts.calls.append(text)
            raise SpeechError("synthesis_failed")

        tts.synthesize = broken
    provider = None if mode == "unconfigured" else FunctionProvider(model)
    async with live_server(settings, llm_provider=provider, speech_stt=stt, speech_tts=tts) as (
        app,
        port,
    ):
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
            await say(runtime, microphone)
            await until(
                lambda: runtime.voice.turn_task is not None and runtime.voice.turn_task.done()
            )
            assert runtime.voice.state in {"IDLE", "FOLLOW_UP"} and not runtime.voice.player.busy
            if mode in {"denied", "unavailable", "indeterminate"}:
                assert tts.calls == [
                    (
                        "One or more actions failed or have an unknown outcome. "
                        "Please check their state before trying again."
                    )
                ]
                assert "Everything succeeded." not in tts.calls
            elif mode in {"provider_timeout", "unconfigured"}:
                assert len(tts.calls) == 1 and "assistant" in tts.calls[0].lower()
            elif mode != "tts_failed":
                assert not tts.calls
            if mode == "denied":
                assert not hardware.commands
            assert not app.state.voice.tasks
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


@pytest.mark.parametrize("stage", ["transcribing", "speaking"])
async def test_disconnect_recovers_without_replaying_actions(settings, tmp_path, stage):
    settings.speech.enabled = True
    settings.agent.allow_mutations = True
    settings.voice_devices = {"mirror-1": VoiceGrant(allow_mutations=True)}
    stt, tts = STT("dim mirror", "tell me a fact"), TTS()
    microphone, speaker, hardware = Microphone(), Speaker(), SimulatedHardware()
    if stage == "transcribing":
        stt.wait = asyncio.Event()
    else:
        speaker.block = False

    async def model(messages, tools):
        if messages[-1].role == "tool":
            return final("Target acknowledged.")
        if messages[-1].content == "dim mirror":
            return LLMResponse(
                LLMMessage(
                    "assistant",
                    tool_calls=(ToolCall("dim", "mirror.set_brightness", {"percent": 35}),),
                ),
                "test",
                "test-model",
                "tool_calls",
            )
        return final("A safe new response.")

    async with live_server(
        settings, llm_provider=FunctionProvider(model), speech_stt=stt, speech_tts=tts
    ) as (app, port):
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
            await say(runtime, microphone)
            await until(lambda: len(stt.calls) == 1)
            if stage == "speaking":
                # Driver completion precedes playback ACKs, turn cleanup and echo expiry.
                await until(lambda: capture_ready(runtime, "FOLLOW_UP"))
                assert len(speaker.completed) == 2 and hardware.commands == [35]
                previous_playback = runtime.voice.player.active_request
                speaker.block = True
                # Disconnect during the second response, not the first one's cleanup.
                await say(runtime, microphone, wake=False)
                await until(
                    lambda: (
                        len(stt.calls) == 2
                        and runtime.voice.state == "SPEAKING"
                        and runtime.voice.player.busy
                        and runtime.voice.player.active_request != previous_playback
                    )
                )
            connection = app.state.gateway.connections["mirror-1"]
            await connection.socket.close(code=1012)
            await until(
                lambda: (
                    app.state.gateway.connections.get("mirror-1") is not None
                    and app.state.gateway.connections["mirror-1"] is not connection
                )
            )
            await until(
                lambda: (
                    not runtime.voice.player.busy
                    and not runtime.voice.processing
                    and not app.state.voice.tasks
                )
            )
            assert not runtime.voice.player.busy and not app.state.voice.tasks
            before = list(hardware.commands)
            if stt.wait:
                stt.wait.set()
            stt.wait = None
            # A cancelled STT call may not consume its fixture transcript.
            stt.texts.clear()
            stt.texts.append("tell me a fact")
            speaker.block = False
            await say(runtime, microphone)
            await until(lambda: runtime.voice.state == "FOLLOW_UP")
            assert hardware.commands == before
            assert not runtime._receipts and not app.state.voice.delivery.pending
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


async def test_followup_after_delayed_playback_receipt_and_status(settings, tmp_path, monkeypatch):
    settings.speech.enabled = True
    settings.voice_devices = {"mirror-1": VoiceGrant()}
    stt, tts, microphone, speaker = (
        STT("first question", "follow-up"),
        TTS(),
        Microphone(),
        Speaker(),
    )
    completion, release_completion = asyncio.Event(), asyncio.Event()
    followup, release_followup = asyncio.Event(), asyncio.Event()

    async def model(messages, tools):
        return final("A safe response.")

    async with live_server(
        settings,
        llm_provider=FunctionProvider(model),
        speech_stt=stt,
        speech_tts=tts,
    ) as (app, port):
        runtime = EdgeRuntime(
            edge_settings(tmp_path, port),
            SimulatedHardware(),
            audio_source=microphone,
            detector=Detector(),
            speaker=speaker,
        )
        send, handle = runtime._send, runtime.voice.handle

        async def hold_completion(event):
            if (
                isinstance(event, PlaybackStatus)
                and event.payload.status == "completed"
                and not completion.is_set()
            ):
                completion.set()
                await release_completion.wait()
            await send(event)

        async def hold_followup(event):
            if (
                isinstance(event, VoiceStatus)
                and event.payload.state == "FOLLOW_UP"
                and not followup.is_set()
            ):
                await until(lambda: not runtime.voice.player.busy)
                followup.set()
                await release_followup.wait()
            await handle(event)

        monkeypatch.setattr(runtime, "_send", hold_completion)
        monkeypatch.setattr(runtime.voice, "handle", hold_followup)
        task = asyncio.create_task(runtime.run())
        try:
            await asyncio.wait_for(runtime.connected.wait(), 5)
            await say(runtime, microphone)
            await asyncio.wait_for(completion.wait(), 5)
            assert len(speaker.completed) == 2  # Chime and driver output, before its ACK.
            assert runtime.voice.player.busy and runtime.voice.processing
            assert not capture_ready(runtime, "FOLLOW_UP")
            release_completion.set()
            await asyncio.wait_for(followup.wait(), 5)
            assert not runtime.voice.player.busy and runtime.voice.processing
            assert not runtime.voice.turn_task.done()
            assert not capture_ready(runtime, "FOLLOW_UP")

            # Force the CI ordering: all audio arrives after driver completion but
            # before FOLLOW_UP. Half-duplex capture must discard it, not upload it.
            consumed, frames = asyncio.Event(), []
            loop = asyncio.get_running_loop()
            feed = runtime.voice.machine.feed

            def observe_feed(pcm):
                events = feed(pcm)
                frames.append(events)
                if len(frames) == 14:
                    loop.call_soon_threadsafe(consumed.set)
                return events

            monkeypatch.setattr(runtime.voice.machine, "feed", observe_feed)
            await microphone.emit(SPEECH_FRAME, 8)
            await microphone.emit(SILENCE_FRAME, 6)
            await asyncio.wait_for(consumed.wait(), 5)
            assert frames == [[]] * 14 and len(stt.calls) == 1
            release_followup.set()
            await until(lambda: capture_ready(runtime, "FOLLOW_UP"))
            conversation = app.state.voice.sessions["mirror-1"]
            await say(runtime, microphone, wake=False)
            await until(lambda: len(stt.calls) == 2 and capture_ready(runtime, "FOLLOW_UP"))
            assert app.state.voice.sessions["mirror-1"] == conversation
            assert len(speaker.completed) == 3  # Follow-up needs no second wake/chime.
            assert not runtime._receipts and not app.state.voice.delivery.pending
        finally:
            release_completion.set()
            release_followup.set()
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


async def test_software_mute_busy_wakes_programmatic_stop_and_followup_timeout(settings, tmp_path):
    settings.speech.enabled = True
    settings.voice_devices = {"mirror-1": VoiceGrant()}
    stt, tts, microphone, speaker, detector = (
        STT("a question", "a new question"),
        TTS(),
        Microphone(),
        Speaker(),
        Detector(),
    )
    stt.wait = asyncio.Event()

    async def model(messages, tools):
        return final("A response.")

    async with live_server(
        settings, llm_provider=FunctionProvider(model), speech_stt=stt, speech_tts=tts
    ) as (app, port):
        runtime = EdgeRuntime(
            edge_settings(tmp_path, port),
            SimulatedHardware(),
            audio_source=microphone,
            detector=detector,
            speaker=speaker,
        )
        task = asyncio.create_task(runtime.run())
        try:
            await asyncio.wait_for(runtime.connected.wait(), 5)
            await runtime.voice.set_muted(True)
            await microphone.emit(SPEECH_FRAME, 8)
            await microphone.emit(SILENCE_FRAME, 6)
            await asyncio.sleep(0.05)
            assert not stt.calls and detector.wakes == 0
            await runtime.voice.set_muted(False)
            await say(runtime, microphone)
            await until(lambda: len(stt.calls) == 1)
            # Deliberately inject while busy; say() models a user waiting to speak.
            await microphone.emit(SPEECH_FRAME, 8)
            await microphone.emit(SILENCE_FRAME, 6)
            await until(microphone.queue.empty)
            assert len(stt.calls) == 1  # busy frames cannot start another voice interaction
            await runtime.voice.cancel()
            await until(lambda: not app.state.voice.tasks)
            assert runtime.voice.state == "IDLE"
            stt.wait = None
            stt.texts.clear()
            stt.texts.append("a new question")
            await say(runtime, microphone)
            await until(lambda: runtime.voice.state == "FOLLOW_UP")
            runtime.voice.machine.follow_until = runtime.voice.clock() - 1
            await microphone.emit(SILENCE_FRAME, 1)
            await until(lambda: runtime.voice.state == "IDLE")
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


async def test_voice_caption_permission_scope_ttl_and_no_sqlite_transcript_persistence(
    settings, tmp_path
):
    settings.speech.enabled = True
    settings.voice_devices = {"mirror-1": VoiceGrant()}
    settings.agent_clients = {
        "reader": AgentClient(
            token="caption-reader-" + ("r" * 32), device_ids={"mirror-1"}, allow_voice_state=True
        ),
        "other": AgentClient(token="other-client-" + ("x" * 32), device_ids={"mirror-1"}),
    }
    stt, tts, microphone, speaker = STT("private spoken sentence"), TTS(), Microphone(), Speaker()

    async def model(messages, tools):
        return final("Private response.")

    async with live_server(
        settings, llm_provider=FunctionProvider(model), speech_stt=stt, speech_tts=tts
    ) as (app, port):
        runtime = EdgeRuntime(
            edge_settings(tmp_path, port),
            SimulatedHardware(),
            audio_source=microphone,
            detector=Detector(),
            speaker=speaker,
        )
        task = asyncio.create_task(runtime.run())
        try:
            await asyncio.wait_for(runtime.connected.wait(), 5)
            await say(runtime, microphone)
            await until(lambda: runtime.voice.state == "FOLLOW_UP")
            async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}") as client:
                url = "/api/application/voice"
                assert (
                    await client.get(url, headers={"Authorization": "Bearer " + EDGE_TOKEN})
                ).status_code == 401
                assert (
                    await client.get(
                        url,
                        headers={
                            "Authorization": "Bearer " + OPERATOR_TOKEN,
                            "Origin": "http://browser",
                        },
                    )
                ).status_code == 401
                assert (
                    await client.get(
                        url,
                        headers={
                            "Authorization": "Bearer "
                            + settings.agent_clients["other"].token.get_secret_value()
                        },
                    )
                ).status_code == 403
                response = await client.get(
                    url,
                    headers={
                        "Authorization": "Bearer "
                        + settings.agent_clients["reader"].token.get_secret_value()
                    },
                )
                assert "private spoken sentence" in response.text
                app.state.voice.observe(
                    "unapproved-device", "assistant.thinking", {"transcript": "must not leak"}
                )
                assert "must not leak" not in response.text
            saved = await app.state.services.db.run(
                lambda c: [
                    row[0]
                    for row in c.execute(
                        "SELECT payload FROM events UNION ALL SELECT payload FROM resources"
                    )
                ]
            )
            assert "private spoken sentence" not in json.dumps(
                saved
            ) and "Private response." not in json.dumps(saved)
            app.state.voice.clock = lambda: 1e20
            assert not app.state.voice.snapshot(app.state.voice.principal("mirror-1"))["events"]
            assert not app.state.voice.events["mirror-1"]
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


async def test_two_voice_devices_keep_sessions_home_grants_and_caption_readers_isolated(
    settings, tmp_path
):
    settings.speech.enabled = True
    settings.agent.allow_mutations = True
    home = HomeFixture()
    settings.home = home.settings
    token = "other-edge-" + ("z" * 32)
    settings.edge_tokens["mirror-2"] = SecretStr(token)
    settings.voice_devices = {
        "mirror-1": VoiceGrant(allow_mutations=True, home_entities={"light.bedroom"}),
        "mirror-2": VoiceGrant(allow_mutations=True),
    }
    settings.agent_clients = {
        "reader": AgentClient(
            token="reader-" + ("r" * 40), device_ids={"mirror-1"}, allow_voice_state=True
        )
    }
    stt, tts = STT("first private voice sentence", "second private voice sentence"), TTS()

    async def model(messages, tools):
        if messages[-1].role == "tool":
            return final("The approved light is off.")
        return LLMResponse(
            LLMMessage(
                "assistant",
                tool_calls=(ToolCall("light", "home.turn_off", {"target": "bedroom lights"}),),
            ),
            "test",
            "test-model",
            "tool_calls",
        )

    async with live_server(
        settings,
        llm_provider=FunctionProvider(model),
        speech_stt=stt,
        speech_tts=tts,
        service_transports={"home": httpx.MockTransport(home.handler)},
    ) as (app, port):
        runtimes, tasks, microphones = [], [], []
        try:
            for device in ("mirror-1", "mirror-2"):
                microphone = Microphone()
                config = edge_settings(tmp_path / device, port).model_copy(
                    update={
                        "device_id": device,
                        "token": SecretStr(EDGE_TOKEN if device == "mirror-1" else token),
                    }
                )
                runtime = EdgeRuntime(
                    config,
                    SimulatedHardware(),
                    audio_source=microphone,
                    detector=Detector(),
                    speaker=Speaker(),
                )
                runtimes.append(runtime)
                microphones.append(microphone)
                tasks.append(asyncio.create_task(runtime.run()))
                await asyncio.wait_for(runtime.connected.wait(), 5)
                await say(runtime, microphone)
                await until(lambda current=runtime: current.voice.state == "FOLLOW_UP")
            sessions = list(app.state.agent.sessions.sessions.values())
            assert {session.owner for session in sessions} == {"voice:mirror-1", "voice:mirror-2"}
            assert len({session.id for session in sessions}) == 2
            assert all(
                (
                    "second private"
                    not in json.dumps([message.content for message in session.messages()])
                )
                for session in sessions
                if session.device_id == "mirror-1"
            )
            assert len([request for request in home.requests if request.method == "POST"]) == 1
            assert tts.calls[1].startswith("One or more actions failed")
            async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}") as client:
                response = await client.get(
                    "/api/application/voice",
                    headers={
                        "Authorization": "Bearer "
                        + settings.agent_clients["reader"].token.get_secret_value()
                    },
                )
                assert response.status_code == 200
                assert (
                    "first private voice sentence" in response.text
                    and "second private voice sentence" not in response.text
                )
                data = response.json()
                assert [device["device_id"] for device in data["devices"]] == ["mirror-1"]
                assert (
                    data["devices"][0]["application"]["devices"][0]["entity_id"] == "light.bedroom"
                )
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)


async def test_operator_voice_cancel_covers_pending_synthesis_and_preserves_hardware_receipts(
    settings, tmp_path
):
    settings.speech.enabled = True
    settings.agent.allow_mutations = True
    settings.voice_devices = {"mirror-1": VoiceGrant(allow_mutations=True)}
    stt, tts, microphone, speaker = STT("dim the mirror"), TTS(), Microphone(), Speaker()
    waiting = asyncio.Event()

    async def blocked(text):
        tts.calls.append(text)
        await waiting.wait()
        raise AssertionError("Cancelled synthesis must never produce playback")

    tts.synthesize = blocked

    async def model(messages, tools):
        if messages[-1].role == "tool":
            return final("Target acknowledged.")
        return LLMResponse(
            LLMMessage(
                "assistant", tool_calls=(ToolCall("dim", "mirror.set_brightness", {"percent": 35}),)
            ),
            "test",
            "test-model",
            "tool_calls",
        )

    async with live_server(
        settings, llm_provider=FunctionProvider(model), speech_stt=stt, speech_tts=tts
    ) as (app, port):
        hardware = SimulatedHardware()
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
            await say(runtime, microphone)
            await until(lambda: bool(tts.calls))
            async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}") as client:
                path = "/api/devices/mirror-1/voice/cancel"
                assert (
                    await client.post(path, headers={"Authorization": "Bearer " + EDGE_TOKEN})
                ).status_code == 401
                response = await client.post(
                    path, headers={"Authorization": "Bearer " + OPERATOR_TOKEN}
                )
                assert response.json()["status"] == "cancel_requested"
            await until(lambda: runtime.voice.turn_task.done() and not app.state.voice.tasks)
            assert hardware.commands == [35] and len(speaker.calls) == 1  # chime only
            assert not runtime.voice.player.busy and not app.state.voice.delivery.pending
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


async def test_unverified_home_acknowledgment_is_not_spoken_as_observed_success(settings, tmp_path):
    settings.speech.enabled = True
    settings.agent.allow_mutations = True
    home = HomeFixture()
    home.verify = False
    settings.home = home.settings
    settings.voice_devices = {
        "mirror-1": VoiceGrant(allow_mutations=True, home_entities={"light.bedroom"})
    }
    stt, tts, microphone = STT("turn off bedroom lights"), TTS(), Microphone()

    async def model(messages, tools):
        if messages[-1].role == "tool":
            return final("The light is definitely off.")
        return LLMResponse(
            LLMMessage(
                "assistant",
                tool_calls=(ToolCall("light", "home.turn_off", {"target": "bedroom lights"}),),
            ),
            "test",
            "test-model",
            "tool_calls",
        )

    async with live_server(
        settings,
        llm_provider=FunctionProvider(model),
        speech_stt=stt,
        speech_tts=tts,
        service_transports={"home": httpx.MockTransport(home.handler)},
    ) as (app, port):
        runtime = EdgeRuntime(
            edge_settings(tmp_path, port),
            SimulatedHardware(),
            audio_source=microphone,
            detector=Detector(),
            speaker=Speaker(),
        )
        task = asyncio.create_task(runtime.run())
        try:
            await asyncio.wait_for(runtime.connected.wait(), 5)
            await say(runtime, microphone)
            await until(lambda: runtime.voice.state == "FOLLOW_UP")
            assert tts.calls == [
                "The approved command was acknowledged, but I haven't confirmed "
                "the device's state. Please check it before trying again."
            ]
            assert len([request for request in home.requests if request.method == "POST"]) == 1
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
