"""Native /api/chat with native tool messages, including optional thinking state."""

from __future__ import annotations

from uuid import uuid4

import httpx

from apps.server.agent.messages import LLMMessage, LLMResponse, ToolCall
from apps.server.providers.base import (
    ProviderError,
    ToolNames,
    provider_request,
    validate_response,
)
from apps.server.tools.base import ToolDefinition


class OllamaProvider:
    name = "ollama"

    def __init__(self, model: str, base_url: str, timeout: float = 45, client=None):
        self.model, self.timeout = model, timeout
        self.client = client or httpx.AsyncClient(
            base_url=base_url.rstrip("/") + "/",
            timeout=timeout,
            trust_env=False,
            follow_redirects=False,
        )

    async def generate(self, messages, tools, settings):
        if settings.reasoning_effort is not None:
            raise ProviderError("unsupported_setting")
        names = ToolNames(tools)
        wire = []
        for message in messages:
            if message.provider == self.name and message.provider_data is not None:
                wire.append(message.provider_data)
            elif message.role == "tool":
                wire.append(
                    {
                        "role": "tool",
                        "tool_name": ToolNames.alias(message.tool_name),
                        "content": message.content,
                    }
                )
            else:
                wire.append({"role": message.role, "content": message.content})
        options = {"num_predict": settings.max_output_tokens}
        if settings.temperature is not None:
            options["temperature"] = settings.temperature
        body = {
            "model": self.model,
            "messages": wire,
            "stream": False,
            "options": options,
            "tools": [self._tool(t) for t in tools],
        }
        if settings.think is not None:
            body["think"] = settings.think

        async def request():
            response = await self.client.post("api/chat", json=body)
            response.raise_for_status()
            return response

        response = await provider_request(request(), self.timeout)
        try:
            if len(response.content) > 1_048_576:
                raise ValueError("response size")
            data = response.json()
            native = data["message"]
            if native["role"] != "assistant" or data.get("done") is not True:
                raise ValueError("incomplete response")
            content = native.get("content", "")
            if not isinstance(content, str):
                raise ValueError("content type")
            calls = tuple(
                ToolCall(
                    id=call.get("id") or str(uuid4()),
                    name=names.decode(call["function"]["name"]),
                    arguments=call["function"]["arguments"],
                )
                for call in native.get("tool_calls", [])
            )
            if any(not isinstance(c.arguments, dict | str) for c in calls):
                raise ValueError("arguments type")
            status = (
                "length"
                if data.get("done_reason") == "length"
                else ("tool_calls" if calls else "complete")
            )
            return validate_response(
                LLMResponse(
                    message=LLMMessage(
                        "assistant",
                        content,
                        calls,
                        provider=self.name,
                        provider_data=native,
                    ),
                    provider=self.name,
                    model=data.get("model", self.model),
                    status=status,
                    usage={
                        "input_tokens": int(data.get("prompt_eval_count", 0)),
                        "output_tokens": int(data.get("eval_count", 0)),
                    },
                )
            )
        except (KeyError, TypeError, ValueError, AttributeError):
            raise ProviderError("provider_invalid_response") from None

    @staticmethod
    def _tool(tool: ToolDefinition):
        return {
            "type": "function",
            "function": {
                "name": ToolNames.alias(tool.name),
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }

    async def close(self):
        await self.client.aclose()
