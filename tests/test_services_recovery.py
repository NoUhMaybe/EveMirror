import asyncio
import json
import sqlite3
import threading
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from apps.config import AgentClient
from apps.server.agent.messages import LLMMessage, LLMResponse, ToolCall
from apps.server.main import create_app
from apps.server.services.common import ServiceError
from apps.server.services.database import Database
from apps.server.services.events import EventStore
from scripts.backup_database import backup
from scripts.export_application import schema
from tests.conftest import EDGE_TOKEN
from tests.service_fixtures import FakeClock, principal
from tests.test_agent_api import FunctionProvider, final
from tests.test_services_timers import service


async def test_backup_captures_committed_wal_and_reopen_recovers(tmp_path):
    original, destination = tmp_path / "original.sqlite3", tmp_path / "backup.sqlite3"
    clock = FakeClock()
    timers = await service(original, clock)
    operation = uuid4()
    created, _ = await timers.mutate(
        principal(), "mirror-1", operation, "create", duration_seconds=100
    )
    await asyncio.to_thread(backup, original, destination)
    await timers.db.close()
    await timers.db.open()
    assert (await timers.list(principal()))["timers"][0]["id"] == created["data"]["timer"]["id"]
    await timers.db.close()
    restored = await service(destination, clock)
    try:
        replayed, duplicate = await restored.mutate(
            principal(), "mirror-1", operation, "create", duration_seconds=100
        )
        assert replayed == created and duplicate
    finally:
        await restored.db.close()
    with pytest.raises(ValueError):
        await asyncio.to_thread(backup, original, destination)


async def test_timer_pagination_and_explicit_operation_retry_through_registry(settings):
    settings.agent.allow_mutations = True
    operation = str(uuid4())
    phase = [0]

    async def model(messages, tools):
        if messages[-1].role == "tool":
            return final("done")
        phase[0] += 1
        return LLMResponse(
            LLMMessage(
                "assistant",
                tool_calls=(
                    ToolCall(
                        str(phase[0]),
                        "timer.create",
                        {
                            "operation_id": operation,
                            "duration_seconds": 60,
                        },
                    ),
                ),
            ),
            "test",
            "test-model",
            "tool_calls",
        )

    app = create_app(settings, llm_provider=FunctionProvider(model))
    async with app.router.lifespan_context(app):
        first = await app.state.agent.turn(principal(), "create", uuid4())
        second = await app.state.agent.turn(principal(), "retry operation", uuid4())
        assert first["status"] == second["status"] == "complete"
        assert second["tools"][0]["replayed"]
        for _ in range(4):
            await app.state.services.timers.mutate(
                principal(), "mirror-1", uuid4(), "create", duration_seconds=60
            )
        page = await app.state.services.timers.list(principal(), limit=2)
        assert len(page["timers"]) == 2 and page["total"] == 5 and page["next_offset"] == 2
        next_page = await app.state.services.timers.list(
            principal(), limit=2, offset=page["next_offset"]
        )
        assert not {timer["id"] for timer in page["timers"]} & {
            timer["id"] for timer in next_page["timers"]
        }


async def test_events_deduplicate_and_require_snapshot_for_old_cursor(tmp_path):
    db = Database(tmp_path / "events.sqlite3")
    await db.open()
    events = EventStore(db, retention=2)
    owner = principal()
    identity = uuid4()
    try:
        await db.run(
            lambda c: events.append(c, owner.id, "mirror-1", "timer.updated", {}, event_id=identity)
        )
        await db.run(
            lambda c: events.append(c, owner.id, "mirror-1", "timer.updated", {}, event_id=identity)
        )
        assert len((await events.read(owner))["events"]) == 1
        await events.publish(owner.id, "mirror-1", "timer.updated", {})
        await events.publish(owner.id, "mirror-1", "timer.updated", {})
        with pytest.raises(ServiceError, match="snapshot_required"):
            await events.read(owner, after=1)
        assert not (await events.read(principal("other")))["events"]
    finally:
        await db.close()


async def test_application_data_isolated_between_real_authenticated_clients(settings):
    alice, bob = "alice-" + "a" * 32, "bob-" + "b" * 32
    settings.agent.allow_mutations = True
    settings.edge_tokens["mirror-2"] = type(settings.operator_token)(EDGE_TOKEN + "other")
    settings.agent_clients = {
        "alice": AgentClient(token=alice, device_ids={"mirror-1"}, allow_mutations=True),
        "bob": AgentClient(token=bob, device_ids={"mirror-2"}, allow_mutations=True),
    }
    foreign_id = [None]

    async def model(messages, tools):
        if messages[-1].role == "tool":
            data = json.loads(messages[-1].content)
            return final(data["status"] if data["status"] == "success" else data["error"]["code"])
        if "steal" in messages[-1].content:
            name, arguments = "timer.cancel", {"timer_id": foreign_id[0]}
        else:
            name, arguments = "timer.create", {"duration_seconds": 60, "name": "private name"}
        return LLMResponse(
            LLMMessage("assistant", tool_calls=(ToolCall("one", name, arguments),)),
            "test",
            "test-model",
            "tool_calls",
        )

    app = create_app(settings, llm_provider=FunctionProvider(model))
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://test"
        ) as client:
            headers_a, headers_b = (
                {"Authorization": "Bearer " + alice},
                {"Authorization": "Bearer " + bob},
            )
            assert (
                await client.post("/api/agent/turn", headers=headers_a, json={"text": "create"})
            ).json()["response"] == "success"
            state = (await client.get("/api/application/state", headers=headers_a)).json()
            foreign_id[0] = state["timers"][0]["id"]
            assert (
                await client.post("/api/agent/turn", headers=headers_b, json={"text": "steal"})
            ).json()["response"] == "timer_not_found"
            foreign = (await client.get("/api/application/state", headers=headers_b)).json()
            assert not foreign["timers"] and not foreign["alarms"]
            assert "private name" not in json.dumps(foreign)
            assert (
                foreign_id[0]
                not in (await client.get("/api/application/events", headers=headers_b)).text
            )


def test_application_schema_matches_versioned_models():
    assert json.loads(Path("packages/application/schema.json").read_text()) == schema()


@pytest.mark.parametrize("damage", ["missing_tables", "missing_column"])
async def test_schema_marker_without_required_structure_is_unavailable(tmp_path, damage):
    path = tmp_path / "damaged-schema.sqlite3"
    if damage == "missing_column":
        original = Database(path)
        await original.open()
        await original.close()
        with sqlite3.connect(path) as connection:
            connection.execute("ALTER TABLE timers DROP COLUMN name")
    else:
        with sqlite3.connect(path) as connection:
            connection.execute("PRAGMA user_version=1")
    database = Database(path)
    await database.open()
    assert not database.available
    await database.close()


async def test_repeated_cancellation_keeps_transaction_ownership_until_worker_finishes(tmp_path):
    database = Database(tmp_path / "cancelled.sqlite3")
    await database.open()
    loop, entered, release = asyncio.get_running_loop(), asyncio.Event(), threading.Event()

    def blocked_write(connection):
        connection.execute("INSERT INTO views VALUES ('owner','mirror-1','timers','default')")
        loop.call_soon_threadsafe(entered.set)
        assert release.wait(5), "Test worker was not released"

    first = asyncio.create_task(database.run(blocked_write))
    second = None
    try:
        await asyncio.wait_for(entered.wait(), 2)
        first.cancel()
        await asyncio.sleep(0)
        first.cancel()
        await asyncio.sleep(0)
        second = asyncio.create_task(
            database.run(
                lambda connection: connection.execute("SELECT count(*) FROM views").fetchone()[0]
            )
        )
        await asyncio.sleep(0)
        assert database.lock.locked() and not first.done() and not second.done()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await first
        assert await second == 1
        assert database.available
    finally:
        release.set()
        await asyncio.gather(*[task for task in (first, second) if task], return_exceptions=True)
        await database.close()
