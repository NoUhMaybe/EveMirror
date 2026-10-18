"""Official Messages SDK with separate system text and grouped user tool results."""

from __future__ import annotations

from anthropic import AsyncAnthropic

from apps.server.agent.messages import LLMMessage, LLMResponse, ToolCall
from apps.server.providers.base import ProviderError, ToolNames, provider_request, validate_response


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, model: str, api_key: str, timeout: float = 45, client=None):
        self.model, self.timeout = model, timeout
        self.client = client or AsyncAnthropic(api_key=api_key, timeout=timeout, max_retries=0)

    async def generate(self, messages, tools, settings):
        if settings.think is not None or settings.reasoning_effort is not None:
            raise ProviderError("unsupported_setting")
        names = ToolNames(tools)
        system, wire = [], []
        for message in messages:
            if message.role == "system":
                system.append(message.content)
                continue
            if message.role == "tool":
                block = {
                    "type": "tool_result",
                    "tool_use_id": message.call_id,
                    "content": message.content,
                    "is_error": message.is_error,
                }
                if wire and wire[-1]["role"] == "user" and isinstance(wire[-1]["content"], list):
                    wire[-1]["content"].append(block)
                else:
                    wire.append({"role": "user", "content": [block]})
            elif message.provider == self.name and message.provider_data is not None:
                wire.append({"role": "assistant", "content": message.provider_data})
            else:
                wire.append({"role": message.role, "content": message.content})
        kwargs = {
            "model": self.model,
            "system": "\n\n".join(system),
            "messages": wire,
            "max_tokens": settings.max_output_tokens,
            "tools": [
                {
                    "name": ToolNames.alias(t.name),
                    "description": t.description,
                    "input_schema": t.parameters,
                }
                for t in tools
            ],
        }
        if settings.temperature is not None:
            kwargs["temperature"] = settings.temperature
        response = await provider_request(self.client.messages.create(**kwargs), self.timeout)
        try:
            data = response.model_dump(mode="json", exclude_none=True)
            native, calls, text = data["content"], [], []
            for block in native:
                if block["type"] == "tool_use":
                    if not isinstance(block["input"], dict):
                        raise ValueError("arguments type")
                    calls.append(ToolCall(block["id"], names.decode(block["name"]), block["input"]))
                elif block["type"] == "text":
                    text.append(block["text"])
                elif block["type"] not in {"thinking", "redacted_thinking"}:
                    raise ValueError("unsupported provider tool")
            reason = data["stop_reason"]
            if reason not in {"end_turn", "stop_sequence", "tool_use", "max_tokens", "refusal"}:
                raise ValueError("response status")
            status = (
                "length"
                if reason == "max_tokens"
                else "tool_calls"
                if reason == "tool_use"
                else "refused"
                if reason == "refusal"
                else "complete"
            )
            if (status == "tool_calls") != bool(calls):
                raise ValueError("tool status mismatch")
            usage = data.get("usage") or {}
            return validate_response(
                LLMResponse(
                    message=LLMMessage(
                        "assistant",
                        "".join(text),
                        tuple(calls),
                        provider=self.name,
                        provider_data=native,
                    ),
                    provider=self.name,
                    model=data["model"],
                    status=status,
                    usage={
                        key: int(usage.get(key, 0)) for key in ("input_tokens", "output_tokens")
                    },
                )
            )
        except (ValueError, KeyError, TypeError, AttributeError):
            raise ProviderError("provider_invalid_response") from None

    async def close(self):
        await self.client.close()
