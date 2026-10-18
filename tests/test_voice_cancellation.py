"""Cancellation ordering regressions driven by events, without models or hardware."""

import asyncio
import base64
from types import SimpleNamespace
from uuid import uuid4

import pytest

from apps.config import VoiceGrant
from apps.edge.hardware import SimulatedHardware
from apps.edge.runtime import EdgeRuntime
from apps.edge.voice.capture import CaptureMachine
from apps.edge.voice.controller import VoiceController
from packages.protocol import (
    AudioChunkPayload,
    AudioEndPayload,
    Cancel,
    PlaybackBegin,
    PlaybackBeginPayload,
    PlaybackCancel,
    PlaybackChunk,
    PlaybackEnd,
    VoiceStatus,
    VoiceStatusPayload,
)
from tests.test_agent_api import FunctionProvider, final
from tests.test_edge_integration import live_server, until
from tests.test_voice_endtoend import edge_settings
from tests.voice_fixtures import (
    STT,
    TTS,
    WAKE_FRAME,
    Detector,
    Microphone,
    Speaker,
    capture_ready,
    say,
)


@pytest.fixture
async def voice(tmp_path):
    runtime = SimpleNamespace(
        settings=edge_settings(tmp_path, 0),
        connected=asyncio.Event(),
        uploads=asyncio.Queue(),
        upload_release=asyncio.Event(),
        sent=[],
    )
    runtime.connected.set()

    async def send(event):
        runtime.sent.append(event)

    async def upload(pcm, **identity):
        runtime.uploads.put_nowait(identity)
        await runtime.upload_release.wait()

    runtime._send, runtime.upload_pcm = send, upload
    controller = VoiceController(
        runtime, source=Microphone(), detector=Detector(), speaker=Speaker()
    )
    controller.machine = CaptureMachine(controller.settings, Detector(), controller.clock)
    try:
        yield controller
    finally:
        await controller.close()


async def start_turn(voice):
    voice.machine.state, voice.machine.busy = "UPLOADING", True
    voice.turn_task = asyncio.create_task(voice._turn(bytes(1024)))
    return await asyncio.wait_for(voice.runtime.uploads.get(), 5)


def status(identity, phase, **kwargs):
    return VoiceStatus(
        device_id="mirror-1", **identity, payload=VoiceStatusPayload(state=phase, **kwargs)
    )


def playback(identity):
    identity = {**identity, "device_id": "mirror-1"}
    pcm = bytes(1024)
    return (
        PlaybackBegin(
            **identity,
            payload=PlaybackBeginPayload(
                sample_rate=16000,
                total_bytes=len(pcm),
                sample_count=len(pcm) // 2,
                duration_seconds=len(pcm) / 32000,
            ),
        ),
        PlaybackChunk(
            **identity, payload=AudioChunkPayload(sequence=0, data=base64.b64encode(pcm).decode())
        ),
        PlaybackEnd(**identity, payload=AudioEndPayload(chunks=1)),
        PlaybackCancel(**identity),
    )


def observed(voice):
    return (
        voice.state,
        voice.machine.state,
        voice.machine.follow_until,
        voice.last_success,
        dict(voice.metrics),
        voice.errors,
        voice.session_id,
        voice.request_id,
    )


@pytest.mark.parametrize(
    "phase",
    [
        "TRANSCRIBING",
        "THINKING",
        "TOOL_EXECUTING",
        "SYNTHESIZING",
        "DELIVERING",
        "SPEAKING",
        "FOLLOW_UP",
        "ERROR",
    ],
)
async def test_cancel_revokes_statuses_before_cleanup_and_after_new_turn(voice, monkeypatch, phase):
    identity = await start_turn(voice)
    playback_id = uuid4()
    await voice.handle(playback({**identity, "request_id": playback_id})[0])
    stale = status(
        {**identity, "request_id": playback_id} if phase == "SPEAKING" else identity,
        phase,
        metrics={"stale_marker": 1},
    )
    cleanup, release = asyncio.Event(), asyncio.Event()
    send = voice.runtime._send

    async def hold_cancel(event):
        if isinstance(event, Cancel):
            assert event.session_id == identity["session_id"]
            assert event.request_id == identity["request_id"]
            cleanup.set()
            await release.wait()
        await send(event)

    monkeypatch.setattr(voice.runtime, "_send", hold_cancel)
    cancelling = asyncio.create_task(voice.cancel())
    try:
        await asyncio.wait_for(cleanup.wait(), 5)
        assert voice.session_id is None and voice.request_id is None
        assert not cancelling.done() and voice.cancelling
        before = observed(voice)
        await voice.handle(stale)
        assert observed(voice) == before
    finally:
        release.set()
        await asyncio.wait_for(cancelling, 5)
        monkeypatch.setattr(voice.runtime, "_send", send)
    assert voice.state == voice.machine.state == "IDLE"
    assert not voice.processing and not voice.player.busy and not voice.machine.busy
    before = observed(voice)
    await voice.handle(stale)
    assert observed(voice) == before
    fresh = await start_turn(voice)
    assert fresh["session_id"] != identity["session_id"]
    before = observed(voice)
    await voice.handle(stale)
    assert observed(voice) == before
    await voice.handle(status(fresh, "TRANSCRIBING"))
    assert voice.state == "TRANSCRIBING"


async def test_status_waiting_for_capture_lock_rechecks_cancelled_generation(voice, monkeypatch):
    class ObservedLock(asyncio.Lock):
        waiting = asyncio.Event()

        async def acquire(self):
            if self.locked():
                self.waiting.set()
            return await super().acquire()

    identity = await start_turn(voice)
    lock = voice.machine_lock = ObservedLock()
    await lock.acquire()
    handler = asyncio.create_task(voice.handle(status(identity, "FOLLOW_UP")))
    cleanup, release = asyncio.Event(), asyncio.Event()
    send = voice.runtime._send

    async def hold(event):
        if isinstance(event, Cancel):
            cleanup.set()
            await release.wait()
        await send(event)

    monkeypatch.setattr(voice.runtime, "_send", hold)
    cancelling = None
    try:
        await asyncio.wait_for(lock.waiting.wait(), 5)
        cancelling = asyncio.create_task(voice.cancel())
        await asyncio.wait_for(cleanup.wait(), 5)
        lock.release()
        await asyncio.wait_for(handler, 5)
        assert voice.state == "IDLE" and voice.machine.state != "FOLLOW_UP"
        assert voice.last_success is None and voice.machine.follow_until == 0
    finally:
        if lock.locked():
            lock.release()
        release.set()
        await asyncio.gather(handler, *([cancelling] if cancelling else []), return_exceptions=True)


async def test_upload_and_playback_request_ids_are_not_interchangeable(voice):
    identity = await start_turn(voice)
    before = observed(voice)
    await voice.handle(status({**identity, "request_id": uuid4()}, "FOLLOW_UP"))
    await voice.handle(status(identity, "SPEAKING"))
    assert observed(voice) == before
    await voice.handle(status(identity, "THINKING"))
    assert voice.state == "THINKING"
    voice.runtime.upload_release.set()
    await voice.handle(status(identity, "FOLLOW_UP", follow_up_seconds=5))
    await asyncio.wait_for(voice.turn_task, 5)
    before = observed(voice)
    await voice.handle(status(identity, "TRANSCRIBING"))
    await voice.handle(status(identity, "FOLLOW_UP", follow_up_seconds=60))
    assert observed(voice) == before and voice.state == "FOLLOW_UP"


async def test_stale_playback_does_not_play_or_clear_new_turn_assembly(voice):
    identity = await start_turn(voice)
    stale = playback({**identity, "request_id": uuid4()})
    await voice.cancel()
    for event in stale:
        await voice.handle(event)
    assert voice.receiver.begin is None and voice.receiver.task is None
    assert not voice.player.driver.calls
    fresh = await start_turn(voice)
    current = playback({**fresh, "request_id": uuid4()})
    await voice.handle(current[0])
    for event in stale:
        await voice.handle(event)
        assert voice.receiver.begin is current[0]
    # A mismatched request within the current session must not clear its assembly.
    await voice.handle(stale[1].model_copy(update={"session_id": fresh["session_id"]}))
    assert voice.receiver.begin is current[0]
    await voice.handle(current[1])
    await voice.handle(current[2])
    await asyncio.wait_for(voice.receiver.task, 5)
    assert len(voice.player.driver.calls) == 1


async def test_cancel_stops_output_queued_by_playback_end_before_driver_starts(voice):
    identity = await start_turn(voice)
    events = playback({**identity, "request_id": uuid4()})
    for event in events[:3]:
        await voice.handle(event)
    assert voice.receiver.task and not voice.player.busy
    await voice.cancel()
    assert voice.receiver.task.cancelled()
    assert not voice.player.driver.calls and not voice.player.busy


@pytest.mark.parametrize("stage", ["assembly", "playing"])
async def test_interrupted_turn_cleans_ordinary_playback_before_fresh_turn(voice, stage):
    failed = asyncio.Event()
    upload = voice.runtime.upload_pcm

    async def interrupted(pcm, **identity):
        voice.runtime.uploads.put_nowait(identity)
        await failed.wait()
        raise TimeoutError("event-controlled upload failure")

    voice.runtime.upload_pcm = interrupted
    identity = await start_turn(voice)
    events = playback({**identity, "request_id": uuid4()})
    await voice.handle(events[0])
    await voice.handle(events[1])
    if stage == "playing":
        voice.player.driver.block = True
        await voice.handle(events[2])
        await until(lambda: voice.player.busy and len(voice.player.driver.calls) == 1)
    failed.set()
    await asyncio.wait_for(voice.turn_task, 5)
    assert voice.state == voice.machine.state == "IDLE"
    assert voice.session_id is None and voice.request_id is None
    assert voice.receiver.begin is None and not voice.player.busy
    voice.runtime.upload_pcm = upload
    fresh = await start_turn(voice)
    await voice.handle(status(identity, "FOLLOW_UP"))
    await voice.handle(status(fresh, "TRANSCRIBING"))
    assert voice.state == "TRANSCRIBING"


async def test_cancel_preserves_queued_alarm_and_explicit_stop_can_end_it(voice):
    voice.store.open()
    voice.storage_ready = True
    voice.player.driver.block = True
    alarm_id = uuid4()
    events = playback({"session_id": alarm_id, "request_id": alarm_id})
    events = (
        events[0].model_copy(
            update={"payload": events[0].payload.model_copy(update={"alarm_id": alarm_id})}
        ),
        *events[1:],
    )
    for event in events[:3]:
        await voice.handle(event)
    await voice.cancel()
    await until(lambda: voice.player.busy and len(voice.player.driver.calls) == 1)
    assert not voice.receiver.task.cancelled() and voice.playing_alarm == alarm_id
    await voice.cancel(include_alarms=True)
    assert not voice.player.busy and len(voice.player.driver.cancelled) == 1
    assert voice.store.receipt(alarm_id) == "cancelled"


async def test_chime_completion_cannot_reopen_listening_after_cancel(voice, monkeypatch):
    finished = asyncio.Event()
    play = voice.player.play

    async def observe_play(*args, **kwargs):
        try:
            return await play(*args, **kwargs)
        finally:
            finished.set()

    monkeypatch.setattr(voice.player, "play", observe_play)
    voice.player.driver.block = True
    capture = asyncio.create_task(voice._capture())
    try:
        await until(lambda: voice.source.available)
        await voice.source.emit(WAKE_FRAME, 5)
        await until(lambda: len(voice.player.driver.calls) == 1)
        await voice.cancel()
        await asyncio.wait_for(finished.wait(), 5)
        assert voice.state == voice.machine.state == "IDLE"
        assert voice.session_id is None and voice.runtime.uploads.empty()
    finally:
        capture.cancel()
        await asyncio.gather(capture, return_exceptions=True)


async def test_delayed_transcription_cannot_resurrect_cancelled_turn(
    settings, tmp_path, monkeypatch
):
    settings.speech.enabled = True
    settings.voice_devices = {"mirror-1": VoiceGrant()}
    stt, microphone, speaker = STT("cancelled question"), Microphone(), Speaker()
    stt.wait = asyncio.Event()
    received, release, delivered = asyncio.Event(), asyncio.Event(), asyncio.Event()
    held = []

    async def model(messages, tools):
        return final("A response.")

    async with live_server(
        settings, llm_provider=FunctionProvider(model), speech_stt=stt, speech_tts=TTS()
    ) as (app, port):
        runtime = EdgeRuntime(
            edge_settings(tmp_path, port),
            SimulatedHardware(),
            audio_source=microphone,
            detector=Detector(),
            speaker=speaker,
        )
        handle = runtime.voice.handle

        async def delayed(event):
            if (
                isinstance(event, VoiceStatus)
                and event.payload.state == "TRANSCRIBING"
                and not held
            ):
                held.append(event)
                received.set()
                await release.wait()
                await handle(event)
                delivered.set()
            else:
                await handle(event)

        monkeypatch.setattr(runtime.voice, "handle", delayed)
        task = asyncio.create_task(runtime.run())
        try:
            await asyncio.wait_for(runtime.connected.wait(), 5)
            await say(runtime, microphone)
            await asyncio.wait_for(received.wait(), 5)
            await until(lambda: len(stt.calls) == 1)
            await runtime.voice.cancel()
            await until(lambda: not app.state.voice.tasks)
            assert runtime.voice.state == "IDLE"
            release.set()
            await asyncio.wait_for(delivered.wait(), 5)
            assert runtime.voice.state == "IDLE"
            assert runtime.voice.machine.state == "IDLE"
            assert not runtime.voice.processing and not runtime.voice.player.busy

            stt.wait = None
            stt.texts.clear()
            stt.texts.extend(["a fresh question", "a valid follow-up"])
            await say(runtime, microphone)
            await until(lambda: capture_ready(runtime, "FOLLOW_UP"))
            assert stt.calls[-1].session_id != held[0].session_id
            conversation = app.state.voice.sessions["mirror-1"]
            await say(runtime, microphone, wake=False)
            await until(lambda: len(stt.calls) == 3 and capture_ready(runtime, "FOLLOW_UP"))
            assert app.state.voice.sessions["mirror-1"] == conversation
            assert len(speaker.completed) == 4  # Two chimes, fresh reply and follow-up reply.
            assert not runtime._receipts and not app.state.voice.delivery.pending
        finally:
            release.set()
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
