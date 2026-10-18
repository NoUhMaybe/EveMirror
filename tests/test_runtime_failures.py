import asyncio
from threading import Event

import pytest

from apps.config import EdgeSettings
from apps.edge.hardware import FeatherService, HardwareError
from apps.edge.runtime import AudioUploadError, EdgeRuntime
from packages.protocol import AudioChunk, AudioEnd, Cancel
from tests.conftest import EDGE_TOKEN
from tests.test_hardware import FakeSerial


async def test_partial_serial_write_is_never_success():
    class PartialSerial(FakeSerial):
        def write(self, data):
            return 1

    serial = PartialSerial()
    hardware = FeatherService("fixture", serial_factory=lambda **_: serial)
    with pytest.raises(HardwareError, match="indeterminate"):
        await hardware.set_brightness(35)
    assert serial.closed and not hardware.status.connected


async def test_upload_cancellation_is_explicit_and_does_not_retain_pcm(tmp_path):
    runtime = EdgeRuntime(
        EdgeSettings(
            token=EDGE_TOKEN,
            simulate_hardware=True,
            journal_path=tmp_path / "journal.sqlite3",
        )
    )
    sent = []
    ended = asyncio.Event()

    class Socket:
        async def send(self, raw):
            from packages.protocol import parse_message

            event = parse_message(raw)
            sent.append(event)
            if isinstance(event, AudioEnd):
                ended.set()

    runtime._socket = Socket()
    runtime.connected.set()
    task = asyncio.create_task(runtime.upload_pcm(b"\0\0" * 200))
    await asyncio.wait_for(ended.wait(), 1)
    with pytest.raises(AudioUploadError, match="already active"):
        await runtime.upload_pcm(b"\0\0")
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert isinstance(sent[-1], Cancel)
    assert sum(isinstance(event, AudioChunk) for event in sent) == 1
    assert runtime._receipts == {}
    runtime.commands.close()
    await runtime.hardware.close()


async def test_serial_cancellation_keeps_lock_until_worker_finishes():
    started, release = Event(), Event()

    class BlockingSerial(FakeSerial):
        def write(self, data):
            self.writes.append(data)
            if len(self.writes) == 1:
                started.set()
                release.wait(2)
            return len(data)

    serial = BlockingSerial()
    hardware = FeatherService("fixture", serial_factory=lambda **_: serial)
    first = asyncio.create_task(hardware.set_brightness(35))
    assert await asyncio.to_thread(started.wait, 1)
    first.cancel()
    second = asyncio.create_task(hardware.set_brightness(35))
    await asyncio.sleep(0.01)
    assert serial.writes == [b"B35\n"]
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await first
    assert (await second).target_percent == 35
    assert serial.writes == [b"B35\n", b"B35\n"]
    await hardware.close()
