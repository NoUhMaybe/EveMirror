import asyncio
import base64
import sqlite3
import sys
import threading
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4, uuid5

import numpy as np
import pytest

from apps.config import EdgeSettings, EdgeVoiceSettings
from apps.edge.voice.alarms import AlarmStore, TimerSynchronizer
from apps.edge.voice.controller import VoiceController
from apps.edge.voice.io import SoundOutput
from apps.edge.voice.playback import PlaybackManager, PlaybackReceiver
from packages.audio import SpeechAudio, SpeechError, notification
from packages.protocol import (
    AudioChunkPayload,
    AudioEndPayload,
    PlaybackBegin,
    PlaybackBeginPayload,
    PlaybackCancel,
    PlaybackChunk,
    PlaybackEnd,
    SyncedTimer,
    TimerSync,
    TimerSyncPayload,
)
from tests.test_edge_integration import until
from tests.voice_fixtures import Microphone, Speaker


def timer(now, status="RUNNING"):
    identity = uuid4()
    return SyncedTimer(
        timer_id=identity,
        alarm_id=uuid5(identity, "alarm"),
        deadline=now + timedelta(seconds=2),
        status=status,
        version=1,
    )


def synchronize(sync, rows, **kwargs):
    sync.accept(
        TimerSync(
            device_id=sync.store.device_id,
            payload=TimerSyncPayload(
                generation=uuid4(), sequence=0, final=True, timers=tuple(rows)
            ),
            **kwargs,
        )
    )


def test_offline_deadlines_pause_cancel_lease_clock_change_restart_and_dismiss(tmp_path):
    now = datetime(2026, 10, 18, tzinfo=UTC)
    store = AlarmStore(tmp_path / "voice.sqlite3", "mirror-1")
    store.open()
    sync = TimerSynchronizer(store, lambda: now)
    first, paused = timer(now), timer(now, "PAUSED")
    synchronize(sync, [first, paused])
    assert store.due(now, 86400) == []
    later = now + timedelta(seconds=3)
    assert [row["id"] for row in store.due(later, 86400)] == [str(first.timer_id)]
    assert store.due(now - timedelta(seconds=20), 86400) == []
    assert store.due(now + timedelta(days=2), 86400) == []
    assert store.reserve(first.alarm_id) is None
    store.mark(first.alarm_id, "started")
    store.close()
    store.open()
    assert store.reserve(first.alarm_id) == "indeterminate"
    assert len(store.due(later, 86400)) == 1
    store.dismiss(first.alarm_id)
    assert not store.due(later, 86400) and store.pending_dismissals() == [first.alarm_id]
    synchronize(sync, [paused])  # authoritative cancellation/ack removes old cache
    assert not store.pending_dismissals()
    store.set_muted(True)
    store.close()
    store.open()
    assert store.muted(False)
    store.close()


def test_timer_sync_is_device_bound_atomic_bounded_and_rejects_wrong_alarm_identity(tmp_path):
    now = datetime.now(UTC)
    store = AlarmStore(tmp_path / "voice.sqlite3", "mirror-1")
    store.open()
    sync = TimerSynchronizer(store, lambda: now)
    first = timer(now, "EXPIRED")
    synchronize(sync, [first])
    incomplete = TimerSync(
        device_id="mirror-1",
        payload=TimerSyncPayload(generation=uuid4(), sequence=0, final=False, timers=()),
    )
    sync.accept(incomplete)
    assert len(store.due(now, 86400)) == 1  # partial data never replaces authoritative cache
    with pytest.raises(SpeechError):
        synchronize(sync, [first.model_copy(update={"alarm_id": uuid4()})])
    with pytest.raises(SpeechError):
        sync.accept(incomplete.model_copy(update={"device_id": "other"}))
    with pytest.raises(SpeechError):
        sync.accept(
            TimerSync(
                device_id="mirror-1",
                payload=TimerSyncPayload(generation=uuid4(), sequence=1, final=True),
            )
        )
    store.close()
    wrong = AlarmStore(tmp_path / "voice.sqlite3", "other")
    with pytest.raises(SpeechError, match="voice_storage_unavailable"):
        wrong.open()


@pytest.mark.parametrize("damage", ["corrupt", "future"])
def test_voice_journal_fails_closed_without_removing_existing_data(tmp_path, damage):
    path = tmp_path / "voice.sqlite3"
    if damage == "corrupt":
        path.write_bytes(b"preserve corrupt data")
    else:
        with sqlite3.connect(path) as connection:
            connection.execute("PRAGMA user_version=999")
    original = path.read_bytes()
    with pytest.raises((SpeechError, sqlite3.Error)):
        AlarmStore(path, "mirror-1").open()
    assert path.read_bytes() == original


async def test_alarm_preempts_speech_once_and_pending_receipt_never_interrupts_later_speech(
    tmp_path,
):
    speaker, events = Speaker(), []
    store = AlarmStore(tmp_path / "voice.sqlite3", "mirror-1")
    store.open()

    async def send(event):
        events.append(event)

    player = PlaybackManager(speaker, send, "mirror-1", store)
    speaker.block = True
    speech = asyncio.create_task(player.play(notification(), uuid4(), uuid4()))
    await until(lambda: len(speaker.calls) == 1)
    identity = uuid4()
    alert = asyncio.create_task(
        player.play(notification(True), identity, identity, alarm_id=identity)
    )
    await until(lambda: len(speaker.calls) == 2)
    assert await speech == "cancelled"
    speaker.block = False
    assert await alert == "completed"
    speaker.block = True
    later = asyncio.create_task(player.play(notification(), uuid4(), uuid4()))
    await until(lambda: len(speaker.calls) == 3)
    assert (
        await player.play(notification(True), identity, identity, alarm_id=identity) == "completed"
    )
    assert not later.done() and len(speaker.calls) == 3
    speaker.block = False
    assert await later == "completed"
    assert [event.payload.status for event in events].count("cancelled") == 1
    store.close()


async def test_mute_disconnect_and_voice_stop_preserve_active_alarm_until_explicit_dismissal(
    tmp_path,
):
    runtime = SimpleNamespace(
        settings=EdgeSettings(
            device_id="mirror-1",
            token="x" * 40,
            voice=EdgeVoiceSettings(state_path=tmp_path / "voice.sqlite3"),
        ),
        connected=asyncio.Event(),
    )
    speaker = Speaker()
    speaker.block = True
    controller = VoiceController(runtime, source=Microphone(), speaker=speaker)
    controller.store.open()
    controller.storage_ready = True
    scheduled = timer(datetime.now(UTC), "EXPIRED")
    synchronize(controller.sync, [scheduled])
    identity = scheduled.alarm_id
    alert = asyncio.create_task(
        controller.player.play(notification(True), identity, identity, alarm_id=identity)
    )
    try:
        await until(lambda: controller.playing_alarm == identity)
        await controller.set_muted(True)
        await controller.cancel()
        await controller.disconnected()
        assert controller.muted and controller.player.busy and not alert.done()
        assert speaker.cancelled == []
        await controller.dismiss(identity)
        assert await alert == "cancelled"
        assert controller.store.pending_dismissals() == [identity]
    finally:
        await controller.close()
        await asyncio.gather(alert, return_exceptions=True)


async def test_failed_alarm_status_delivery_does_not_stop_local_output_or_replay(tmp_path):
    store = AlarmStore(tmp_path / "voice.sqlite3", "mirror-1")
    store.open()
    speaker = Speaker()

    async def disconnected_send(event):
        raise ConnectionError("socket failed before disconnected state arrived")

    player = PlaybackManager(speaker, disconnected_send, "mirror-1", store)
    identity = uuid4()
    try:
        assert (
            await player.play(notification(True), identity, identity, alarm_id=identity)
            == "completed"
        )
        assert store.receipt(identity) == "completed" and len(speaker.completed) == 1
        assert (
            await player.play(notification(True), identity, identity, alarm_id=identity)
            == "completed"
        )
        assert len(speaker.calls) == 1 and not speaker.cancelled
    finally:
        await player.cancel()
        store.close()


async def test_playback_receipts_chunk_integrity_cancel_correlation_failure_and_replay():
    speaker, events = Speaker(), []

    async def send(event):
        events.append(event)

    manager = PlaybackManager(speaker, send, "mirror-1")
    receiver = PlaybackReceiver(manager, send, "mirror-1")
    identity = {"device_id": "mirror-1", "request_id": uuid4(), "session_id": uuid4()}
    audio = SpeechAudio(b"\x01\x00" * 12000, 22050)
    begin = PlaybackBegin(
        **identity, payload=PlaybackBeginPayload(sample_rate=22050, total_bytes=len(audio.pcm))
    )
    await receiver.start(begin)
    assert events[-1].payload.status == "accepted" and not speaker.calls
    for sequence, offset in enumerate(range(0, len(audio.pcm), 16000)):
        await receiver.append(
            PlaybackChunk(
                **identity,
                payload=AudioChunkPayload(
                    sequence=sequence,
                    data=base64.b64encode(audio.pcm[offset : offset + 16000]).decode(),
                ),
            )
        )
        assert events[-1].payload.status == "buffered" and not speaker.calls
    speaker.block = True
    await receiver.finish(PlaybackEnd(**identity, payload=AudioEndPayload(chunks=2)))
    await until(lambda: manager.busy and len(speaker.calls) == 1)
    await receiver.cancel(
        PlaybackCancel(device_id="mirror-1", request_id=uuid4(), session_id=uuid4())
    )
    assert manager.busy
    await receiver.cancel(PlaybackCancel(**identity))
    assert not manager.busy and events[-1].payload.status == "cancelled"
    await receiver.start(begin)
    assert events[-1].payload.status == "failed" and len(speaker.calls) == 1
    speaker.fail = True
    assert await manager.play(audio, uuid4(), uuid4()) == "failed"
    assert events[-1].payload.status == "failed"


async def test_incomplete_invalid_and_expired_playback_discards_memory():
    now, events = [0.0], []

    async def send(event):
        events.append(event)

    manager = PlaybackManager(Speaker(), send, "mirror-1")
    receiver = PlaybackReceiver(manager, send, "mirror-1", timeout=1, clock=lambda: now[0])
    identity = {"device_id": "mirror-1", "request_id": uuid4(), "session_id": uuid4()}
    await receiver.start(
        PlaybackBegin(**identity, payload=PlaybackBeginPayload(sample_rate=16000, total_bytes=3200))
    )
    with pytest.raises(SpeechError):
        await receiver.append(
            PlaybackChunk(**identity, payload=AudioChunkPayload(sequence=1, data="AAAA"))
        )
    with pytest.raises(SpeechError):
        await receiver.finish(PlaybackEnd(**identity, payload=AudioEndPayload(chunks=1)))
    now[0] = 2
    await receiver.expire()
    assert (
        receiver.begin is None
        and not receiver.buffer
        and events[-1].payload.code == "playback_transfer_timeout"
    )


def test_real_output_adapter_resamples_to_selected_device_and_detects_underrun(monkeypatch):
    streams = []

    class Stream:
        def __init__(self, **kwargs):
            self.config, self.data, self.closed = kwargs, [], False
            self.fail = False
            streams.append(self)

        def start(self):
            pass

        def stop(self):
            pass

        def abort(self):
            pass

        def close(self):
            self.closed = True

        def write(self, data):
            self.data.append(data.copy())
            return self.fail

    monkeypatch.setitem(
        sys.modules,
        "sounddevice",
        SimpleNamespace(
            OutputStream=Stream, query_devices=lambda *args: {"default_samplerate": 48000}
        ),
    )
    output = SoundOutput(EdgeVoiceSettings(volume=0.5))
    stopped = threading.Event()
    observed = []
    output.play(
        SpeechAudio(b"\x00\x40" * 2400, 24000),
        stopped,
        lambda: observed.append("started"),
        lambda samples: observed.append(samples),
    )
    assert streams[0].config["samplerate"] == 48000
    assert sum(len(chunk) for chunk in streams[0].data) == 4800 and streams[0].closed
    assert observed[0] == "started" and observed[-1] == 2400
    assert np.isclose(np.concatenate(streams[0].data)[1000], 0.25, atol=0.01)
    monkeypatch.setattr(Stream, "write", lambda self, data: True)
    with pytest.raises(SpeechError, match="playback_underflow"):
        output.play(notification(), stopped, lambda: None, lambda _: None)
    assert streams[-1].closed
