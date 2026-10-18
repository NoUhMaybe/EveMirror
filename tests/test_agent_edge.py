import asyncio
import json
from uuid import uuid4

import httpx
import pytest

from apps.config import EdgeSettings
from apps.edge.hardware import SimulatedHardware
from apps.edge.runtime import EdgeRuntime
from tests.conftest import EDGE_TOKEN, OPERATOR_TOKEN
from tests.provider_fixtures import PROVIDERS, mock_provider, tool_results, wire_response
from tests.test_edge_integration import live_server


@pytest.mark.parametrize("name", PROVIDERS)
async def test_model_brightness_uses_authenticated_gateway_edge_journal_and_actual_results(
    settings, tmp_path, name
):
    settings.agent.allow_mutations = True

    def handler(request):
        body = json.loads(request.content)
        results = tool_results(name, body)
        if not results:
            return httpx.Response(
                200,
                json=wire_response(
                    name,
                    "",
                    [
                        ("before", "mirror.get_status", {}),
                        ("set", "mirror.set_brightness", {"percent": 35}),
                        ("repeat", "mirror.set_brightness", {"percent": 35}),
                        ("status", "mirror.get_status", {}),
                        ("time", "system.get_time", {}),
                    ],
                ),
            )
        assert all(r["status"] == "success" for r in results)
        assert results[0]["data"]["hardware"]["target_percent"] is None
        assert results[2]["replayed"] is True
        hardware = results[3]["data"]["hardware"]
        assert hardware["simulated"] and hardware["actual_percent"] is None
        assert hardware["fade_complete"] is None and hardware["target_percent"] == 35
        return httpx.Response(
            200,
            json=wire_response(
                name,
                f"Target {hardware['target_percent']}%; actual brightness unknown.",
            ),
        )

    async with live_server(settings, llm_provider=mock_provider(name, handler)) as (app, port):
        hardware = SimulatedHardware()
        runtime = EdgeRuntime(
            EdgeSettings(
                token=EDGE_TOKEN,
                server_url=f"ws://127.0.0.1:{port}",
                journal_path=tmp_path / "commands.sqlite3",
                heartbeat_interval=0.2,
            ),
            hardware=hardware,
        )
        edge_task = asyncio.create_task(runtime.run())
        try:
            await asyncio.wait_for(runtime.connected.wait(), 5)
            async with httpx.AsyncClient(
                base_url=f"http://127.0.0.1:{port}",
                headers={"Authorization": "Bearer " + OPERATOR_TOKEN},
            ) as client:
                body = {"request_id": str(uuid4()), "text": "Set 35%, then time and brightness?"}
                result = await client.post("/api/agent/turn", json=body)
                assert result.json()["response"] == "Target 35%; actual brightness unknown.", (
                    result.text
                )
                assert hardware.commands == [35]
                assert (await client.post("/api/agent/turn", json=body)).json() == result.json()
                assert hardware.commands == [35]
        finally:
            edge_task.cancel()
            await asyncio.gather(edge_task, return_exceptions=True)
