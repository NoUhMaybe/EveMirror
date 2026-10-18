import asyncio
import sqlite3
from datetime import timedelta

import pytest

from apps.edge.commands import CommandProcessor
from apps.edge.hardware import FeatherService, HardwareError, SimulatedHardware, clamp_brightness
from packages.protocol import DeviceCommand, SetBrightness, SetDisplayMode, utc_now


class FakeSerial:
    def __init__(self, reply=b"OK 35\n", **kwargs):
        self.reply = reply
        self.writes = []
        self.closed = False

    def reset_input_buffer(self):
        pass

    def write(self, data):
        self.writes.append(data)
        return len(data)

    def readline(self, limit):
        return self.reply

    def close(self):
        self.closed = True


def command(percent=35):
    return DeviceCommand(
        device_id="mirror-1",
        payload=SetBrightness(action="set_brightness", percent=percent),
        expires_at=utc_now() + timedelta(seconds=10),
    )


def test_local_clamping_keeps_firmware_range():
    assert [clamp_brightness(x) for x in [-1, 0, 35, 100, 101]] == [0, 0, 35, 100, 100]
    with pytest.raises(ValueError):
        clamp_brightness(True)


async def test_exact_serial_ack_and_reuse():
    serial = FakeSerial()
    hardware = FeatherService("test", serial_factory=lambda **_: serial)
    result = await hardware.set_brightness(35)
    await hardware.set_brightness(35)
    assert serial.writes == [b"B35\n", b"B35\n"]
    assert result.target_percent == 35
    assert result.actual_percent is None and result.fade_complete is None
    await hardware.close()
    assert serial.closed


@pytest.mark.parametrize("reply", [b"OK\n", b"OK 34\n", b"OK 35junk\n", b"", b"ERR value\n"])
async def test_serial_error_and_reconnect_on_next_explicit_command(reply):
    serials = [FakeSerial(reply=reply), FakeSerial()]
    hardware = FeatherService("test", serial_factory=lambda **_: serials.pop(0))
    with pytest.raises(HardwareError, match="invalid_ack"):
        await hardware.set_brightness(35)
    assert not hardware.status.connected and hardware.status.target_percent is None
    assert (await hardware.set_brightness(35)).target_percent == 35
    await hardware.close()


async def test_replay_survives_restart_and_conflict_rejected(tmp_path):
    path = tmp_path / "journal.sqlite3"
    hardware = SimulatedHardware()
    processor = CommandProcessor("mirror-1", hardware, path)
    request = command()
    ack = await processor.execute(request)
    processor.close()
    processor = CommandProcessor("mirror-1", hardware, path)
    repeated = await processor.execute(request)
    assert repeated.payload.replayed is True
    assert repeated.payload.hardware == ack.payload.hardware
    assert repeated.request_id == ack.request_id and repeated.timestamp == ack.timestamp
    conflict = request.model_copy(
        update={"payload": SetBrightness(action="set_brightness", percent=50)}
    )
    assert (await processor.execute(conflict)).payload.code == "conflict"
    assert hardware.commands == [35]
    processor.close()


async def test_expired_and_wrong_device_commands_do_not_touch_hardware(tmp_path):
    hardware = SimulatedHardware()
    processor = CommandProcessor("mirror-1", hardware, tmp_path / "journal.sqlite3")
    expired = command().model_copy(update={"expires_at": utc_now() - timedelta(seconds=1)})
    assert (await processor.execute(expired)).payload.code == "expired"
    wrong = command().model_copy(update={"device_id": "another-mirror"})
    assert (await processor.execute(wrong)).payload.code == "conflict"
    assert hardware.commands == []
    processor.close()


async def test_interruption_stays_indeterminate_after_restart(tmp_path):
    class BlockingHardware(SimulatedHardware):
        async def set_brightness(self, percent):
            self.commands.append(percent)
            await asyncio.Event().wait()

    hardware = BlockingHardware()
    path = tmp_path / "journal.sqlite3"
    processor = CommandProcessor("mirror-1", hardware, path)
    request = command()
    task = asyncio.create_task(processor.execute(request))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    processor.close()
    processor = CommandProcessor("mirror-1", hardware, path)
    assert (await processor.execute(request)).payload.code == "indeterminate"
    assert hardware.commands == [35]
    processor.close()


async def test_explicit_sleep_uses_backlight_only(tmp_path):
    hardware = SimulatedHardware()
    processor = CommandProcessor("mirror-1", hardware, tmp_path / "journal.sqlite3")
    request = command().model_copy(
        update={
            "payload": SetDisplayMode(action="set_display_mode", mode="sleep"),
        }
    )
    assert (await processor.execute(request)).payload.status == "accepted"
    assert hardware.commands == [0]
    processor.close()


async def test_old_journal_tombstone_cannot_be_reexecuted_with_fresh_deadline(tmp_path):
    hardware = SimulatedHardware()
    processor = CommandProcessor("mirror-1", hardware, tmp_path / "journal.sqlite3")
    original = command()
    await processor.execute(original)
    with processor._db:
        processor._db.execute("UPDATE commands SET created=0")
    await processor.execute(command(50))  # prunes old ACKs, preserves IDs/fingerprints
    retry = original.model_copy(update={"expires_at": utc_now() + timedelta(seconds=5)})
    assert (await processor.execute(retry)).payload.code == "indeterminate"
    assert hardware.commands == [35, 50]
    processor.close()


def test_journal_schema_cannot_be_silently_downgraded(tmp_path):
    path = tmp_path / "future.sqlite3"
    with sqlite3.connect(path) as database:
        database.execute("PRAGMA user_version=2")
    with pytest.raises(RuntimeError, match="schema version"):
        CommandProcessor("mirror-1", SimulatedHardware(), path)
    with sqlite3.connect(path) as database:
        assert database.execute("PRAGMA user_version").fetchone()[0] == 2
