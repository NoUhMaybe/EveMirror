"""Presence acceptance uses monotonic fake clocks and journaled simulated hardware."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from apps.config import EdgeSettings
from apps.edge.commands import CommandProcessor
from apps.edge.hardware import HardwareError, SimulatedHardware
from apps.edge.presence.controller import DisplayController
from apps.edge.presence.policy import PresenceMachine
from apps.edge.presence.sensors import SimulatedSensor
from packages.presence import NightSchedule, PresenceOptions, PresenceReading
from packages.protocol import (
    DeviceCommand,
    EdgePresenceState,
    SetBrightness,
    SetDisplayPolicy,
    parse_message,
)


class Clock:
    def __init__(self):
        self.now = 0.0
        self.wall = datetime(2026, 10, 18, 12, tzinfo=UTC)

    def advance(self, seconds):
        self.now += seconds
        self.wall += timedelta(seconds=seconds)


def reading(state, health="healthy"):
    return PresenceReading(state=state, health=health)


@pytest.fixture
def display(tmp_path):
    clock = Clock()
    hardware = SimulatedHardware()
    settings = EdgeSettings(
        token="presence-device-token-12345678901234567890",
        journal_path=tmp_path / "edge.sqlite3",
        simulate_hardware=True,
        presence_driver="simulated",
        presence=PresenceOptions(
            enabled=True,
            present_confirm=1.0,
            absent_confirm=2.0,
            absence_timeout=3.0,
            minimum_awake=4.0,
            activity_grace=5.0,
            manual_override_seconds=10.0,
        ),
    )
    commands = CommandProcessor(
        settings.device_id, hardware, settings.journal_path, clock=lambda: clock.wall
    )
    controller = DisplayController(
        settings, commands, clock=lambda: clock.now, wall=lambda: clock.wall
    )
    yield controller, hardware, clock, commands, settings
    commands.close()


def command(display, payload):
    controller, _, clock, _, settings = display
    return DeviceCommand(
        device_id=settings.device_id,
        timestamp=clock.wall,
        expires_at=clock.wall + timedelta(seconds=5),
        payload=payload,
    )


async def asleep(display):
    controller, hardware, clock, *_ = display
    await controller.tick(reading("ABSENT"))
    clock.advance(2)
    await controller.tick(reading("ABSENT"))
    clock.advance(3)
    await controller.tick(reading("ABSENT"))
    assert hardware.commands == [65, 0]


def test_debounce_requires_continuous_input_and_unknown_breaks_absence():
    m = PresenceMachine(PresenceOptions(present_confirm=2.0, absent_confirm=3.0), 0)
    m.observe(reading("PRESENT"), 0)
    m.observe(reading("ABSENT"), 1)
    m.observe(reading("PRESENT"), 2)
    assert m.confirmed == "UNKNOWN"
    m.observe(reading("PRESENT"), 4)
    assert m.confirmed == "PRESENT"
    m.observe(reading("ABSENT"), 5)
    m.observe(reading("ABSENT"), 8)
    assert m.confirmed == "ABSENT" and m.absent_since == 8
    m.observe(PresenceReading(health="timeout"), 9)
    assert m.confirmed == "UNKNOWN" and m.absent_since is None
    m.observe(reading("ABSENT"), 20)
    assert m.confirmed == "UNKNOWN"


async def test_sleep_and_confirmed_wake_restore_preference_without_read_flood(display):
    controller, hardware, clock, *_ = display
    await asleep(display)
    await controller.tick(reading("PRESENT"))
    assert hardware.commands == [65, 0]
    clock.advance(1)
    await controller.tick(reading("PRESENT"))
    for _ in range(100):
        await controller.tick(reading("PRESENT"))
    assert hardware.commands == [65, 0, 65]
    assert controller.status.acknowledged_percent == 65
    assert hardware.status.actual_percent is None and hardware.status.fade_complete is None


@pytest.mark.parametrize("health", ["timeout", "unavailable", "malformed"])
async def test_sensor_failure_while_off_wakes_conservatively_and_reconfirms_absence(
    display, health
):
    controller, hardware, clock, *_ = display
    await asleep(display)
    await controller.tick(PresenceReading(health=health))
    assert hardware.commands == [65, 0, 65]
    clock.advance(100)
    await controller.tick(reading("ABSENT"))
    assert controller.status.confirmed == "UNKNOWN"
    assert hardware.commands == [65, 0, 65]


async def test_unknown_hold_can_keep_off_but_never_counts_as_absence(display):
    controller, hardware, clock, *_ = display
    controller.machine.settings = controller.machine.settings.model_copy(
        update={"unknown_policy": "hold"}
    )
    await asleep(display)
    await controller.tick(PresenceReading())
    clock.advance(100)
    await controller.tick(PresenceReading())
    assert hardware.commands == [65, 0]
    assert controller.machine.absent_since is None
    await controller.activity("voice", True)
    await controller.tick()
    assert hardware.commands == [65, 0, 65]


async def test_minimum_awake_and_wake_cooldown_bound_fades(display):
    controller, hardware, clock, *_ = display
    m = controller.machine
    m.settings = m.settings.model_copy(update={"absent_confirm": 0.0, "absence_timeout": 0.0})
    await controller.tick(reading("PRESENT"))
    await controller.tick(reading("ABSENT"))
    assert hardware.commands == [65]
    clock.advance(4)
    await controller.tick(reading("ABSENT"))
    m.settings = m.settings.model_copy(update={"present_confirm": 0.0, "wake_cooldown": 10.0})
    await controller.tick(reading("PRESENT"))
    assert hardware.commands == [65, 0]
    clock.advance(6)
    await controller.tick(reading("PRESENT"))
    assert hardware.commands == [65, 0, 65]


async def test_rapid_noisy_sequence_has_bounded_hardware_writes(display):
    controller, hardware, *_ = display
    for state in ["PRESENT", "ABSENT", "PRESENT", "ABSENT", "UNKNOWN", "PRESENT"] * 100:
        await controller.tick(reading(state))
    assert hardware.commands == [65]
    assert controller.updates.qsize() == 1


@pytest.mark.parametrize("activity", ["voice", "playback", "alarm", "manual_interaction"])
async def test_local_activity_wakes_offline_and_grace_protects_results(display, activity):
    controller, hardware, clock, *_ = display
    await asleep(display)
    await controller.activity(activity, True)
    await controller.tick()
    clock.advance(100)
    await controller.tick(reading("ABSENT"))
    await controller.tick(PresenceReading())
    assert hardware.commands == [65, 0, 65]
    await controller.activity(activity, False)
    await controller.tick(reading("ABSENT"))
    clock.advance(2)
    await controller.tick(reading("ABSENT"))
    clock.advance(2.9)
    await controller.tick(reading("ABSENT"))
    assert hardware.commands[-1] == 65
    clock.advance(0.1)
    await controller.tick(reading("ABSENT"))
    assert hardware.commands[-1] == 0


async def test_manual_off_survives_presence_and_alarm_until_expiry(display):
    controller, hardware, clock, *_ = display
    request = command(display, SetBrightness(action="set_brightness", percent=0))
    ack = await controller.execute(request)
    await controller.activity("alarm", True)
    await controller.tick(reading("PRESENT"))
    clock.advance(9)
    await controller.tick(reading("PRESENT"))
    assert ack.payload.status == "accepted" and hardware.commands == [0]
    clock.advance(1)
    await controller.tick(reading("PRESENT"))
    assert hardware.commands == [0, 65]


async def test_manual_preference_duplicate_does_not_extend_override_and_reboot_restores(display):
    controller, hardware, clock, commands, settings = display
    request = command(display, SetBrightness(action="set_brightness", percent=42))
    await controller.execute(request)
    clock.advance(5)
    assert (await controller.execute(request)).payload.replayed
    assert controller.machine.manual_until == 10
    replacement = DisplayController(
        settings, commands, clock=lambda: clock.now, wall=lambda: clock.wall
    )
    assert replacement.machine.settings.preferred_percent == 42
    assert replacement.machine.manual_until == 10
    assert hardware.commands == [42]
    clock.advance(6)
    await replacement.tick(reading("PRESENT"))
    assert hardware.commands == [42]
    assert not replacement.status.override_active


def test_night_schedule_uses_zone_and_dst_and_not_runtime_durations():
    schedule = NightSchedule(enabled=True, timezone="America/Chicago", start="22:00", end="07:00")
    assert schedule.active(datetime(2026, 11, 1, 6, 30, tzinfo=UTC))
    assert schedule.active(datetime(2026, 11, 1, 7, 30, tzinfo=UTC))
    assert not schedule.active(datetime(2026, 11, 1, 13, 0, tzinfo=UTC))
    with pytest.raises(ValueError):
        schedule.active(datetime(2026, 1, 1))


async def test_night_manual_and_voice_precedence(display):
    controller, hardware, clock, *_ = display
    controller.machine.settings = controller.machine.settings.model_copy(
        update={"night": NightSchedule(enabled=True, start="11:00", end="13:00", percent=20)}
    )
    await controller.tick(reading("PRESENT"))
    clock.advance(1)
    await controller.tick(reading("PRESENT"))
    assert hardware.commands == [65, 20]  # Unknown first follows the conservative policy.
    await controller.activity("voice", True)
    await controller.tick()
    assert hardware.commands[-1] == 65
    await controller.execute(command(display, SetBrightness(action="set_brightness", percent=30)))
    assert hardware.commands[-1] == 30
    await controller.activity("voice", False)
    clock.advance(11)
    await controller.tick(reading("PRESENT"))
    assert hardware.commands[-1] == 20 and controller.machine.settings.preferred_percent == 30


async def test_wall_clock_jump_does_not_expire_manual_override(display):
    controller, hardware, clock, *_ = display
    await controller.execute(command(display, SetBrightness(action="set_brightness", percent=0)))
    clock.wall += timedelta(days=10)
    await controller.activity("voice", True)
    assert hardware.commands == [0] and controller.status.override_active


async def test_invalid_ack_latches_automation_across_restart_until_new_explicit_request(display):
    controller, hardware, clock, commands, settings = display
    original = hardware.set_brightness
    attempts = []

    async def fail(percent):
        attempts.append(percent)
        raise HardwareError("invalid_ack")

    hardware.set_brightness = fail
    await controller.tick(reading("PRESENT"))
    for _ in range(20):
        await controller.tick(reading("ABSENT"))
        clock.advance(10)
    replacement = DisplayController(
        settings, commands, clock=lambda: clock.now, wall=lambda: clock.wall
    )
    await replacement.tick(reading("PRESENT"))
    assert attempts == [65] and replacement.status.uncertain
    hardware.set_brightness = original
    ack = await replacement.execute(
        command(display, SetBrightness(action="set_brightness", percent=40))
    )
    assert ack.payload.status == "accepted" and not replacement.status.uncertain
    assert hardware.commands == [40]


async def test_cancelled_hardware_write_is_not_replayed_on_restart(display):
    controller, hardware, clock, commands, settings = display
    entered, release = asyncio.Event(), asyncio.Event()

    async def blocked(percent):
        hardware.commands.append(percent)
        entered.set()
        await release.wait()

    hardware.set_brightness = blocked
    task = asyncio.create_task(controller.tick(reading("PRESENT")))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    replacement = DisplayController(
        settings, commands, clock=lambda: clock.now, wall=lambda: clock.wall
    )
    await replacement.tick(reading("ABSENT"))
    assert hardware.commands == [65] and replacement.status.uncertain


async def test_crash_after_driver_ack_before_journal_receipt_keeps_uncertainty(display):
    controller, hardware, clock, commands, settings = display
    original = commands._ack

    def crash(command, status, code="ok"):
        if status == "accepted":
            raise RuntimeError("Injected crash before durable receipt")
        return original(command, status, code)

    commands._ack = crash
    with pytest.raises(RuntimeError, match="Injected crash"):
        await controller.execute(
            command(display, SetBrightness(action="set_brightness", percent=40))
        )
    commands._ack = original
    replacement = DisplayController(
        settings, commands, clock=lambda: clock.now, wall=lambda: clock.wall
    )
    await replacement.tick(reading("PRESENT"))
    assert hardware.commands == [40] and replacement.status.uncertain


async def test_concurrent_presence_and_manual_commands_serialize_with_fade_ack(display):
    controller, hardware, clock, *_ = display
    entered, release = asyncio.Event(), asyncio.Event()
    original = hardware.set_brightness

    async def blocked(percent):
        entered.set()
        await release.wait()
        return await original(percent)

    hardware.set_brightness = blocked
    automatic = asyncio.create_task(controller.tick(reading("PRESENT")))
    await entered.wait()
    manual = asyncio.create_task(
        controller.execute(command(display, SetBrightness(action="set_brightness", percent=0)))
    )
    release.set()
    await asyncio.gather(automatic, manual)
    assert hardware.commands == [65, 0]
    await controller.tick(reading("PRESENT"))
    assert hardware.commands == [65, 0]


async def test_activity_notification_never_waits_for_serial_ack(display):
    controller, hardware, *_ = display
    entered, release = asyncio.Event(), asyncio.Event()
    original = hardware.set_brightness

    async def blocked(percent):
        entered.set()
        await release.wait()
        return await original(percent)

    hardware.set_brightness = blocked
    task = asyncio.create_task(controller.tick(reading("PRESENT")))
    try:
        await asyncio.wait_for(entered.wait(), 1)
        await asyncio.wait_for(controller.activity("voice", True), 1)
        assert controller.lock.locked() and controller.status.activity_protected
    finally:
        release.set()
        await task
    await controller.tick(reading("PRESENT"))
    assert hardware.commands == [65]


async def test_policy_configuration_and_override_use_same_journal(display):
    controller, hardware, clock, *_ = display
    payload = SetDisplayPolicy(
        action="set_display_policy",
        settings=PresenceOptions(enabled=False, preferred_percent=55),
        override_percent=0,
    )
    request = command(display, payload)
    await controller.execute(request)
    assert controller.machine.settings.preferred_percent == 55 and hardware.commands == [0]
    release = command(display, SetDisplayPolicy(action="set_display_policy", release_override=True))
    await controller.execute(release)
    assert hardware.commands == [0, 55]
    assert (await controller.execute(request)).payload.replayed
    assert hardware.commands == [0, 55] and controller.machine.manual is None


async def test_sensor_supervisor_times_out_closes_and_recovers_without_absence(display):
    controller, hardware, clock, *_ = display
    entered, closed = asyncio.Event(), asyncio.Event()

    class StuckSensor(SimulatedSensor):
        async def read(self):
            entered.set()
            await asyncio.Event().wait()

        async def close(self):
            closed.set()
            await super().close()

    controller.sensor = StuckSensor()
    controller.edge.presence_read_timeout = 0.02
    controller.edge.presence_poll_interval = 0.02
    task = asyncio.create_task(controller.run())
    try:
        await asyncio.wait_for(entered.wait(), 1)
        await asyncio.wait_for(closed.wait(), 1)
        # Wait for the timeout report, not an arbitrary duration.
        while not controller.status.reading.health == "timeout":
            await asyncio.wait_for(controller.updates.get(), 1)
        assert controller.status.confirmed == "UNKNOWN"
        assert hardware.commands == [65]
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


async def test_malformed_sensor_closes_reconnects_and_requires_fresh_confirmation(display):
    controller, hardware, clock, *_ = display
    reopened = asyncio.Event()

    class RecoveringSensor(SimulatedSensor):
        opens = 0
        closes = 0

        async def initialize(self):
            await super().initialize()
            self.opens += 1
            if self.opens == 2:
                reopened.set()

        async def read(self):
            return b"malformed" if self.opens == 1 else reading("PRESENT")

        async def close(self):
            self.closes += 1
            await super().close()

    sensor = RecoveringSensor()
    controller.sensor = sensor
    controller.edge.presence_poll_interval = 0.02
    task = asyncio.create_task(controller.run())
    try:
        async with asyncio.timeout(1):
            while controller.status.reading.health != "malformed":
                await controller.updates.get()
        assert controller.status.confirmed == "UNKNOWN" and sensor.closes == 1
        clock.advance(5)
        await asyncio.wait_for(reopened.wait(), 1)
        async with asyncio.timeout(1):
            while controller.status.reading.state != "PRESENT":
                await controller.updates.get()
        assert controller.status.confirmed == "UNKNOWN"
        clock.advance(1)
        controller.wake.set()
        async with asyncio.timeout(1):
            while controller.status.confirmed != "PRESENT":
                await controller.updates.get()
        assert hardware.commands == [65] and controller.status.reading.health == "healthy"
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.parametrize(
    "value",
    [
        {"preferred_percent": 101},
        {"absence_timeout": -1},
        {"enabled": "true"},
        {"night": {"timezone": "Nowhere/Invalid"}},
        {"night": {"start": "25:00"}},
    ],
)
def test_invalid_policy_configuration_rejected(value):
    with pytest.raises(ValidationError):
        PresenceOptions.model_validate(value)


def test_typed_status_wire_roundtrip_and_unhealthy_absence_rejected(display):
    controller, *_ = display
    event = EdgePresenceState(device_id="mirror-1", payload=controller.status)
    assert parse_message(event.model_dump_json()) == event
    with pytest.raises(ValidationError):
        PresenceReading(state="ABSENT", health="timeout")
