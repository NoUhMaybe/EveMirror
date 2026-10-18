import asyncio
import json
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from apps.config import AgentClient
from apps.server.agent.messages import LLMMessage, LLMResponse, ToolCall
from apps.server.main import create_app
from tests.conftest import EDGE_TOKEN, OPERATOR_TOKEN
from tests.provider_fixtures import PROVIDERS, mock_provider, tool_results, wire_response
from tests.service_fixtures import FakeClock, HomeFixture, SearchFixture, WeatherFixture
from tests.test_agent_api import FunctionProvider, final

HEADERS = {"Authorization": "Bearer " + OPERATOR_TOKEN}


@pytest.mark.parametrize("provider_name", PROVIDERS)
async def test_all_services_through_actual_provider_adapter_registry_and_authenticated_api(
    settings, provider_name
):
    clock, weather, home, search = FakeClock(), WeatherFixture(), HomeFixture(), SearchFixture()
    settings.agent.allow_mutations = True
    settings.home, settings.search = home.settings, search.settings
    requests = []

    def model(request):
        body = json.loads(request.content)
        requests.append(body)
        results = tool_results(provider_name, body)
        if not results:
            return httpx.Response(
                200,
                json=wire_response(
                    provider_name,
                    "",
                    [
                        ("timer-one", "timer.create", {"duration_seconds": 900, "name": "laundry"}),
                        ("timer-two", "timer.create", {"duration_seconds": 900, "name": "laundry"}),
                        ("weather", "weather.weekly", {}),
                        ("lights", "home.turn_off", {"target": "bedroom lights"}),
                        ("tv", "media.pause", {"target": "Roku"}),
                        ("search", "search.web", {"query": "latest technology news"}),
                        ("view", "dashboard.show_view", {"view": "timers"}),
                    ],
                ),
            )
        assert len(results) == 7 and all(result["status"] == "success" for result in results), (
            results
        )
        assert results[0]["data"]["timer"]["id"] != results[1]["data"]["timer"]["id"]
        assert len(results[2]["data"]["daily"]) == 7
        assert results[3]["data"]["verified"] and results[3]["data"]["state"]["state"] == "off"
        assert results[4]["data"]["verified"] and results[4]["data"]["state"]["state"] == "paused"
        assert results[5]["data"]["results"][0]["published_at"] is None
        system = body.get("system") or [
            m for m in body.get("input", body.get("messages", [])) if m.get("role") == "system"
        ]
        assert "reveal tokens" not in json.dumps(system)
        return httpx.Response(
            200,
            json=wire_response(
                provider_name,
                f"Created two {results[0]['data']['timer']['duration_ms'] // 60000}-minute timers; "
                f"forecast covers {len(results[2]['data']['daily'])} days. Lights off, TV paused.",
            ),
        )

    app = create_app(
        settings,
        llm_provider=mock_provider(provider_name, model),
        service_clock=clock,
        service_transports={
            "weather": httpx.MockTransport(weather.handler),
            "home": httpx.MockTransport(home.handler),
            "search": httpx.MockTransport(search.handler),
        },
    )
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://test", headers=HEADERS
        ) as client:
            body = {
                "request_id": str(uuid4()),
                "text": "Two laundry timers, weekly weather, lights off, pause TV, "
                "news and timer view.",
            }
            response = await client.post("/api/agent/turn", json=body)
            data = response.json()
            assert data["status"] == "complete", data
            assert (
                data["response"]
                == "Created two 15-minute timers; forecast covers 7 days. Lights off, TV paused."
            )
            assert (await client.post("/api/agent/turn", json=body)).json() == data
            assert len(requests) == 2
            snapshot = (await client.get("/api/application/state")).json()
            assert snapshot["version"] == 1 and len(snapshot["timers"]) == 2
            assert len(snapshot["weather"]) == 1 and snapshot["views"][0]["view"] == "timers"
            assert len([device for device in snapshot["devices"] if "entity_id" in device]) == 2
            assert "fixture-home-secret" not in json.dumps(
                snapshot
            ) and "reveal tokens" not in json.dumps(snapshot)
            cursor, seen = 0, []
            while True:
                page = (await client.get(f"/api/application/events?after={cursor}&limit=2")).json()
                seen.extend(page["events"])
                if page["cursor"] == cursor:
                    break
                cursor = page["cursor"]
            assert len({event["event_id"] for event in seen}) == len(seen)
            assert {
                "timer.created",
                "weather.updated",
                "home.entity_changed",
                "media.state_changed",
                "tool.execution_completed",
            } <= {event["type"] for event in seen}
            assert len([request for request in home.requests if request.method == "POST"]) == 2


async def test_restart_turn_replay_offline_expiration_and_simulated_alarm_consumer(settings):
    settings.agent.allow_mutations = True
    clock = FakeClock()

    async def model(messages, tools):
        if messages[-1].role == "tool":
            return final("Done")
        return LLMResponse(
            LLMMessage(
                "assistant",
                tool_calls=(ToolCall("create", "timer.create", {"duration_seconds": 1}),),
            ),
            "test",
            "test-model",
            "tool_calls",
        )

    body = {"request_id": str(uuid4()), "text": "Set a one second timer"}
    app = create_app(settings, llm_provider=FunctionProvider(model), service_clock=clock)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://test", headers=HEADERS
        ) as client:
            assert (await client.post("/api/agent/turn", json=body)).json()["status"] == "complete"
    clock.advance(10)
    restarted_provider = FunctionProvider(model)
    restarted = create_app(settings, llm_provider=restarted_provider, service_clock=clock)
    async with restarted.router.lifespan_context(restarted):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(restarted), base_url="http://test", headers=HEADERS
        ) as client:
            replay = (await client.post("/api/agent/turn", json=body)).json()
            assert (
                replay["error"]["code"] == "turn_already_processed"
                and restarted_provider.calls == 0
            )
            state = (await client.get("/api/application/state")).json()
            assert len(state["timers"]) == len(state["alarms"]) == 1
            assert state["timers"][0]["status"] == "EXPIRED"
            seen, delivered = set(), []
            for _ in range(3):
                alarms = (await client.get("/api/application/state")).json()["alarms"]
                for alarm in alarms:
                    if alarm["alarm_id"] not in seen:
                        delivered.append(alarm["alarm_id"])
                        seen.add(alarm["alarm_id"])
            assert len(delivered) == 1  # Simulated consumer deduplicates; no speaker playback.
            identity = state["timers"][0]["id"]

            async def ack_model(messages, tools):
                if messages[-1].role == "tool":
                    assert (
                        json.loads(messages[-1].content)["data"]["timer"]["status"]
                        == "ACKNOWLEDGED"
                    )
                    return final("Acknowledged")
                return LLMResponse(
                    LLMMessage(
                        "assistant",
                        tool_calls=(ToolCall("ack", "timer.acknowledge", {"timer_id": identity}),),
                    ),
                    "test",
                    "test-model",
                    "tool_calls",
                )

            restarted.state.agent.provider = FunctionProvider(ack_model)
            assert (
                await client.post("/api/agent/turn", json={"text": "Acknowledge that alarm"})
            ).json()["status"] == "complete"
            assert not (await client.get("/api/application/state")).json()["alarms"]


async def test_cancelled_turn_after_timer_commit_remains_non_replayable_after_restart(settings):
    settings.agent.allow_mutations = True
    waiting = asyncio.Event()

    async def delayed(messages, tools):
        if messages[-1].role == "tool":
            waiting.set()
            await asyncio.Event().wait()
        return LLMResponse(
            LLMMessage(
                "assistant",
                tool_calls=(ToolCall("create", "timer.create", {"duration_seconds": 60}),),
            ),
            "test",
            "test-model",
            "tool_calls",
        )

    body = {"request_id": str(uuid4()), "text": "Set a timer"}
    app = create_app(settings, llm_provider=FunctionProvider(delayed))
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://test", headers=HEADERS
        ) as client:
            sid = (await client.post("/api/agent/sessions", json={})).json()["session_id"]
            task = asyncio.create_task(
                client.post("/api/agent/turn", json={**body, "session_id": sid})
            )
            await asyncio.wait_for(waiting.wait(), 2)
            await client.post(f"/api/agent/sessions/{sid}/cancel")
            assert (await task).json()["status"] == "cancelled"
    restored = create_app(settings, llm_provider=FunctionProvider(delayed))
    async with restored.router.lifespan_context(restored):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(restored), base_url="http://test", headers=HEADERS
        ) as client:
            assert (await client.post("/api/agent/turn", json=body)).json()["error"][
                "code"
            ] == "turn_indeterminate"
            assert len((await client.get("/api/application/state")).json()["timers"]) == 1


def test_application_state_event_authorization_and_database_degradation(settings):
    alice = "scoped-client-" + "a" * 32
    settings.agent_clients = {"alice": AgentClient(token=alice, device_ids={"mirror-1"})}
    with TestClient(create_app(settings)) as client:
        for path in ["/api/application/state", "/api/application/events"]:
            for headers in [
                {},
                {"Authorization": "Bearer " + EDGE_TOKEN},
                {**HEADERS, "Origin": "http://browser"},
            ]:
                assert client.get(path, headers=headers).status_code == 401
            assert client.get(path, headers={"Authorization": "Bearer " + alice}).status_code == 200
    settings.database_path.write_bytes(b"corrupted persistent state")
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/application/state", headers=HEADERS).status_code == 503
        assert client.get("/health/live").status_code == 200
        assert client.get("/api/state", headers=HEADERS).status_code == 200
        assert client.get("/api/health", headers=HEADERS).json()["services"]["database"] is False


async def test_semantic_presentation_is_automatic_explicit_and_alarm_protected(settings):
    settings.agent.allow_mutations = True
    clock, weather = FakeClock(), WeatherFixture()
    steps = [
        ("timer.create", {"duration_seconds": 1}),
        ("dashboard.show_view", {"view": "default"}),
        ("weather.weekly", {}),
        ("dashboard.dismiss_view", {}),
    ]
    calls = []

    async def model(messages, tools):
        if messages[-1].role == "tool":
            calls.append(json.loads(messages[-1].content))
            return final("Done")
        name, arguments = steps.pop(0)
        return LLMResponse(
            LLMMessage("assistant", tool_calls=(ToolCall(str(len(steps)), name, arguments),)),
            "test",
            "test-model",
            "tool_calls",
        )

    app = create_app(
        settings,
        llm_provider=FunctionProvider(model),
        service_clock=clock,
        service_transports={"weather": httpx.MockTransport(weather.handler)},
    )
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://test", headers=HEADERS
        ) as client:
            await client.post("/api/agent/turn", json={"text": "timer"})
            assert (await client.get("/api/application/state")).json()["views"][0][
                "view"
            ] == "timers"
            await client.post("/api/agent/turn", json={"text": "default"})
            assert (await client.get("/api/application/state")).json()["views"][0][
                "view"
            ] == "default"
            clock.advance(2)
            await client.post("/api/agent/turn", json={"text": "weather"})
            await client.post("/api/agent/turn", json={"text": "dismiss"})
            assert calls[-1]["data"]["alarm_protected"]
            assert (await client.get("/api/application/state")).json()["views"][0][
                "view"
            ] == "timers"
            assert len(weather.requests) == 1
