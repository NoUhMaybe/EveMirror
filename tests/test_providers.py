import asyncio
import json

import httpx
import pytest

from apps.server.agent.messages import GenerationSettings, LLMMessage
from apps.server.providers.base import ProviderError, ToolNames
from apps.server.tools.base import ToolDefinition
from tests.provider_fixtures import (
    PRIVATE_REASONING,
    PROVIDERS,
    mock_provider,
    tool_results,
    wire_response,
)

TOOLS = [ToolDefinition("system.get_time", "Current time", {"type": "object", "properties": {}})]
MESSAGES = [LLMMessage("system", "You are Eve"), LLMMessage("user", "What time is it?")]


@pytest.mark.parametrize("name", PROVIDERS)
async def test_native_multiple_calls_results_private_state_and_usage(name):
    bodies = []

    def handler(request):
        body = json.loads(request.content)
        bodies.append(body)
        if len(bodies) == 1:
            return httpx.Response(
                200,
                json=wire_response(
                    name,
                    "",
                    [
                        ("one", "system.get_time", {}),
                        ("two", "system.get_time", {}),
                    ],
                ),
            )
        assert len(tool_results(name, body)) == 2
        assert PRIVATE_REASONING in json.dumps(body)
        if name == "anthropic":
            assert body["system"] == "You are Eve"
            assert [m["role"] for m in body["messages"]] == ["user", "assistant", "user"]
            assert len(body["messages"][-1]["content"]) == 2
            assert all(b["is_error"] for b in body["messages"][-1]["content"])
        if name == "openai":
            assert body["store"] is False
            assert body["include"] == ["reasoning.encrypted_content"]
        return httpx.Response(200, json=wire_response(name, "Time unavailable"))

    provider = mock_provider(name, handler)
    try:
        first = await provider.generate(MESSAGES, TOOLS, GenerationSettings())
        assert first.status == "tool_calls"
        assert [c.name for c in first.message.tool_calls] == ["system.get_time"] * 2
        history = [
            *MESSAGES,
            first.message,
            *[
                LLMMessage(
                    "tool", '{"status":"error"}', call_id=c.id, tool_name=c.name, is_error=True
                )
                for c in first.message.tool_calls
            ],
        ]
        final = await provider.generate(history, TOOLS, GenerationSettings(temperature=0.2))
        assert final.message.content == "Time unavailable"
        assert final.usage == {"input_tokens": 12, "output_tokens": 3}
        assert "temperature" in bodies[-1] or "temperature" in bodies[-1].get("options", {})
    finally:
        await provider.close()


@pytest.mark.parametrize("name", PROVIDERS)
async def test_ordinary_text_is_not_a_tool_request(name):
    provider = mock_provider(
        name,
        lambda r: httpx.Response(
            200,
            json=wire_response(name, "Call system.get_time({}) is ordinary text here."),
        ),
    )
    try:
        result = await provider.generate(MESSAGES, TOOLS, GenerationSettings())
        assert not result.message.tool_calls
        assert result.status == "complete"
    finally:
        await provider.close()


@pytest.mark.parametrize("name", PROVIDERS)
@pytest.mark.parametrize(
    "status,code",
    [
        (401, "provider_auth_failed"),
        (429, "provider_rate_limited"),
        (500, "provider_unavailable"),
        (400, "provider_request_rejected"),
    ],
)
async def test_provider_http_errors_are_redacted_without_retries(name, status, code):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(status, json={"error": {"message": "secret-token-and-prompt"}})

    provider = mock_provider(name, handler)
    try:
        with pytest.raises(ProviderError, match=code) as error:
            await provider.generate(MESSAGES, TOOLS, GenerationSettings())
        assert "secret" not in str(error.value)
        assert len(requests) == 1
    finally:
        await provider.close()


@pytest.mark.parametrize("name", PROVIDERS)
@pytest.mark.parametrize("mode", ["empty", "malformed", "duplicate", "timeout", "cancel"])
async def test_invalid_responses_timeout_and_cancellation(name, mode):
    started = asyncio.Event()

    async def handler(request):
        started.set()
        if mode == "timeout":
            raise httpx.ReadTimeout("secret-timeout", request=request)
        if mode == "cancel":
            await asyncio.Event().wait()
        data = wire_response(name, "") if mode == "empty" else {}
        if mode == "duplicate":
            data = wire_response(
                name,
                "",
                [
                    ("same", "system.get_time", {}),
                    ("same", "system.get_time", {}),
                ],
            )
        return httpx.Response(200, json=data)

    provider = mock_provider(name, handler)
    try:
        task = asyncio.create_task(provider.generate(MESSAGES, TOOLS, GenerationSettings()))
        if mode == "cancel":
            await asyncio.wait_for(started.wait(), 1)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            expected = (
                "provider_timeout"
                if mode == "timeout"
                else ("provider_empty_response" if mode == "empty" else "provider_invalid_response")
            )
            with pytest.raises(ProviderError, match=expected):
                await task
    finally:
        await provider.close()


@pytest.mark.parametrize("name", PROVIDERS)
async def test_generation_settings_are_explicit_and_provider_specific(name):
    bodies = []

    def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json=wire_response(name))

    provider = mock_provider(name, handler)
    try:
        valid = (
            GenerationSettings(think=True)
            if name == "ollama"
            else (
                GenerationSettings(reasoning_effort="low")
                if name == "openai"
                else GenerationSettings()
            )
        )
        await provider.generate(MESSAGES, TOOLS, valid)
        if name == "ollama":
            assert bodies[0]["think"] is True
        if name == "openai":
            assert bodies[0]["reasoning"] == {"effort": "low"}
        invalid = (
            GenerationSettings(reasoning_effort="low")
            if name == "ollama"
            else GenerationSettings(think=True)
        )
        with pytest.raises(ProviderError, match="unsupported_setting"):
            await provider.generate(MESSAGES, TOOLS, invalid)
        assert len(bodies) == 1
    finally:
        await provider.close()


def test_tool_aliases_are_safe_stable_and_do_not_collide():
    aliases = [
        ToolNames.alias(name) for name in ["home.turn_off", "home_turn_off", "home__turn_off"]
    ]
    assert len(set(aliases)) == 3
    assert all(len(alias) <= 64 and alias.replace("_", "").isalnum() for alias in aliases)
