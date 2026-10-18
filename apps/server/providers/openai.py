"""Official Responses SDK; stateless storage with lossless private output-item replay."""

from __future__ import annotations

from openai import AsyncOpenAI

from apps.server.agent.messages import LLMMessage, LLMResponse, ToolCall
from apps.server.providers.base import ProviderError, ToolNames, provider_request, validate_response


class OpenAIProvider:
    name = "openai"

    def __init__(self, model: str, api_key: str, timeout: float = 45, client=None):
        self.model, self.timeout = model, timeout
        self.client = client or AsyncOpenAI(api_key=api_key, timeout=timeout, max_retries=0)

    async def generate(self, messages, tools, settings):
        if settings.think is not None:
            raise ProviderError("unsupported_setting")
        names = ToolNames(tools)
        wire = []
        for message in messages:
            if message.provider == self.name and message.provider_data is not None:
                # Includes reasoning/encrypted content and function_call IDs, unchanged.
                wire.extend(message.provider_data)
            elif message.role == "tool":
                wire.append(
                    {
                        "type": "function_call_output",
                        "call_id": message.call_id,
                        "output": message.content,
                    }
                )
            else:
                wire.append({"role": message.role, "content": message.content})
        kwargs = {
            "model": self.model,
            "input": wire,
            "store": False,
            "include": ["reasoning.encrypted_content"],
            "max_output_tokens": settings.max_output_tokens,
            "tools": [
                {
                    "type": "function",
                    "name": ToolNames.alias(t.name),
                    "description": t.description,
                    "parameters": t.parameters,
                    # Arbitrary approved MCP schemas need not meet the strict-mode subset.
                    # Eve validates every argument before any execution.
                    "strict": False,
                }
                for t in tools
            ],
        }
        if settings.temperature is not None:
            kwargs["temperature"] = settings.temperature
        if settings.reasoning_effort is not None:
            kwargs["reasoning"] = {"effort": settings.reasoning_effort}
        result = await provider_request(self.client.responses.create(**kwargs), self.timeout)
        try:
            data = result.model_dump(mode="json", exclude_none=True)
            native = data["output"]
            if not isinstance(native, list):
                raise ValueError("output type")
            text, calls, refused = [], [], False
            for item in native:
                if item["type"] == "function_call":
                    if item.get("status", "completed") != "completed":
                        raise ValueError("partial tool call")
                    calls.append(
                        ToolCall(
                            item["call_id"],
                            names.decode(item["name"]),
                            item["arguments"],
                        )
                    )
                elif item["type"] == "message":
                    for block in item["content"]:
                        if block["type"] == "output_text":
                            text.append(block["text"])
                        elif block["type"] == "refusal":
                            refused = True
                            text.append(block["refusal"])
                elif item["type"] != "reasoning":
                    raise ValueError("unsupported provider tool")
            if data["status"] not in {"completed", "incomplete"}:
                raise ValueError("response status")
            status = (
                "length"
                if data["status"] == "incomplete"
                else ("tool_calls" if calls else "refused" if refused else "complete")
            )
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
        except (ValueError, TypeError, KeyError, AttributeError):
            raise ProviderError("provider_invalid_response") from None

    async def close(self):
        await self.client.close()
