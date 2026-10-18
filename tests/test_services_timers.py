import asyncio
import sqlite3
from uuid import uuid4

import pytest

from apps.config import TimerSettings
from apps.server.services.common import ServiceError
from apps.server.services.database import Database
from apps.server.services.events import EventStore
from apps.server.services.timers import TimerService
from tests.service_fixtures import FakeClock, principal


async def service(path, clock):
    db = Database(path)
    await db.open()
    assert db.available
    return TimerService(db, EventStore(db, clock=clock), TimerSettings(), clock)


async def test_create_identical_timers_retries_conflicts_pause_resume_cancel_and_ack(tmp_path):
    clock = FakeClock()
    timers = await service(tmp_path / "timers.sqlite3", clock)
    owner = principal()
    first_op = uuid4()
    try:
        first, replayed = await timers.mutate(
            owner, "mirror-1", first_op, "create", name="laundry", duration_seconds=10
        )
        first_id = first["data"]["timer"]["id"]
        assert not replayed
        repeat, replayed = await timers.mutate(
            owner, "mirror-1", first_op, "create", name="laundry", duration_seconds=10
        )
        assert repeat == first and replayed
        with pytest.raises(ServiceError, match="operation_conflict"):
            await timers.mutate(
                owner, "mirror-1", first_op, "create", name="other", duration_seconds=10
            )
        second, _ = await timers.mutate(
            owner, "mirror-1", uuid4(), "create", name="laundry", duration_seconds=10
        )
        second_id = second["data"]["timer"]["id"]
        assert second_id != first_id
        clock.advance(2.5)
        paused, _ = await timers.mutate(owner, "mirror-1", uuid4(), "pause", timer_id=first_id)
        assert paused["data"]["timer"]["remaining_ms"] == 7500
        clock.advance(20)
        assert (await timers.list(owner, "mirror-1", first_id))["timers"][0]["status"] == "PAUSED"
        resumed, _ = await timers.mutate(owner, "mirror-1", uuid4(), "resume", timer_id=first_id)
        assert resumed["data"]["timer"]["remaining_ms"] == 7500
        cancelled, _ = await timers.mutate(owner, "mirror-1", uuid4(), "cancel", timer_id=first_id)
        assert cancelled["data"]["timer"]["status"] == "CANCELLED"
        expired = await timers.list(owner, "mirror-1", second_id)
        assert expired["timers"][0]["status"] == "EXPIRED" and len(expired["alarms"]) == 1
        ack, _ = await timers.mutate(owner, "mirror-1", uuid4(), "acknowledge", timer_id=second_id)
        assert ack["data"]["timer"]["status"] == "ACKNOWLEDGED"
        assert not (await timers.list(owner))["alarms"]
    finally:
        await timers.db.close()


async def test_restart_offline_expiry_unique_alarm_and_durable_receipts(tmp_path):
    clock, path = FakeClock(), tmp_path / "durable.sqlite3"
    timers = await service(path, clock)
    owner, operation = principal(), uuid4()
    created, _ = await timers.mutate(owner, "mirror-1", operation, "create", duration_seconds=2)
    await timers.db.close()
    clock.advance(60)
    recovered = await service(path, clock)
    try:
        await recovered.reconcile()
        first = await recovered.list(owner)
        assert first["timers"][0]["status"] == "EXPIRED"
        assert len(first["alarms"]) == 1
        alarm_id = first["alarms"][0]["alarm_id"]
        for _ in range(3):
            await recovered.reconcile()
        repeated, replayed = await recovered.mutate(
            owner, "mirror-1", operation, "create", duration_seconds=2
        )
        assert repeated == created and replayed
        events = (await recovered.events.read(owner))["events"]
        assert [e["event_id"] for e in events if e["type"] == "timer.expired"] == [alarm_id]
    finally:
        await recovered.db.close()


@pytest.mark.parametrize("action", ["pause", "cancel"])
async def test_expiration_wins_at_deadline_and_failure_receipt_is_durable(tmp_path, action):
    clock = FakeClock()
    timers = await service(tmp_path / "race.sqlite3", clock)
    try:
        created, _ = await timers.mutate(
            principal(), "mirror-1", uuid4(), "create", duration_seconds=1
        )
        clock.advance(1)
        operation = uuid4()
        failure, _ = await timers.mutate(
            principal(), "mirror-1", operation, action, timer_id=created["data"]["timer"]["id"]
        )
        assert failure["error"]["code"] == "invalid_transition"
        assert len((await timers.list(principal()))["alarms"]) == 1
        repeated, replayed = await timers.mutate(
            principal(), "mirror-1", operation, action, timer_id=created["data"]["timer"]["id"]
        )
        assert repeated == failure and replayed
    finally:
        await timers.db.close()


async def test_owner_device_isolation_and_concurrent_idempotency(tmp_path):
    timers = await service(tmp_path / "concurrent.sqlite3", FakeClock())
    operation = uuid4()
    try:
        results = await asyncio.gather(
            *[
                timers.mutate(
                    principal(), "mirror-1", operation, "create", name="same", duration_seconds=10
                )
                for _ in range(8)
            ]
        )
        assert len({result[0]["data"]["timer"]["id"] for result in results}) == 1
        assert sum(not result[1] for result in results) == 1
        assert not (await timers.list(principal("other")))["timers"]
        assert not (await timers.list(principal(devices=("mirror-2",))))["timers"]
        with pytest.raises(ServiceError, match="device_not_authorized"):
            await timers.mutate(
                principal(devices=("mirror-2",)), "mirror-1", uuid4(), "create", duration_seconds=10
            )
        result, _ = await timers.mutate(
            principal("other"),
            "mirror-1",
            uuid4(),
            "cancel",
            timer_id=results[0][0]["data"]["timer"]["id"],
        )
        assert result["error"]["code"] == "timer_not_found"
    finally:
        await timers.db.close()


async def test_scheduler_reconciles_clock_jumps_and_shuts_down(tmp_path):
    clock = FakeClock()
    timers = await service(tmp_path / "schedule.sqlite3", clock)
    timers.settings.reconcile_seconds = 0.02
    await timers.start()
    try:
        await timers.mutate(principal(), "mirror-1", uuid4(), "create", duration_seconds=100)
        clock.advance(200)
        await asyncio.sleep(0.06)
        assert (await timers.list(principal()))["timers"][0]["status"] == "EXPIRED"
        clock.advance(-400)
        assert (await timers.list(principal()))["timers"][0]["status"] == "EXPIRED"
    finally:
        await timers.close()
        assert timers.task.done()
        await timers.db.close()


async def test_expiration_uses_transaction_time_when_an_operation_was_queued(tmp_path):
    clock = FakeClock()
    timers = await service(tmp_path / "queued.sqlite3", clock)
    try:
        created, _ = await timers.mutate(
            principal(), "mirror-1", uuid4(), "create", duration_seconds=1
        )
        async with timers.db.lock:
            task = asyncio.create_task(
                timers.mutate(
                    principal(),
                    "mirror-1",
                    uuid4(),
                    "pause",
                    timer_id=created["data"]["timer"]["id"],
                )
            )
            await asyncio.sleep(0)
            clock.advance(2)
        result, _ = await task
        assert result["error"]["code"] == "invalid_transition"
        assert len((await timers.list(principal()))["alarms"]) == 1
    finally:
        await timers.db.close()


@pytest.mark.parametrize("mode", ["corruption", "future_schema", "migration_failure"])
async def test_database_fails_closed_without_resetting_data(tmp_path, monkeypatch, mode):
    path = tmp_path / "bad.sqlite3"
    if mode == "corruption":
        path.write_bytes(b"preserve-this-corrupt-database")
    elif mode == "future_schema":
        with sqlite3.connect(path) as connection:
            connection.execute("PRAGMA user_version=999")
    else:
        import apps.server.services.database as module

        monkeypatch.setattr(module, "MIGRATIONS", ["CREATE TABLE incomplete(id); INVALID SQL;"])
    before = path.read_bytes() if path.exists() else None
    db = Database(path)
    await db.open()
    assert not db.available and db.error == "database_unavailable"
    if before:
        assert path.read_bytes() == before
    else:
        with sqlite3.connect(path) as connection:
            assert connection.execute("PRAGMA user_version").fetchone()[0] == 0
            assert not connection.execute(
                "SELECT name FROM sqlite_master WHERE name='incomplete'"
            ).fetchall()
    await db.close()
