"""Real SDK deserialization and HTTP request serialization, entirely isolated from live APIs."""

import json

import httpx
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from apps.server.providers.anthropic import AnthropicProvider
from apps.server.providers.base import ToolNames
from apps.server.providers.ollama import OllamaProvider
from apps.server.providers.openai import OpenAIProvider

PROVIDERS = ["ollama", "openai", "anthropic"]
PRIVATE_REASONING = "private-state-do-not-expose"


def wire_response(provider, text="done", calls=()):
    if provider == "ollama":
        return {
            "model": "test-model",
            "done": True,
            "done_reason": "stop",
            "message": {
                "role": "assistant",
                "content": text,
                "thinking": PRIVATE_REASONING,
                "tool_calls": [
                    {
                        "id": id,
                        "function": {
                            "name": ToolNames.alias(name),
                            "arguments": arguments,
                        },
                    }
                    for id, name, arguments in calls
                ],
            },
            "prompt_eval_count": 12,
            "eval_count": 3,
        }
    if provider == "openai":
        output = [
            {
                "type": "reasoning",
                "id": "rs_1",
                "summary": [],
                "encrypted_content": PRIVATE_REASONING,
            }
        ]
        if text:
            output.append(
                {
                    "id": "msg_1",
                    "type": "message",
                    "role": "assistant",
                    "status": "completed",
                    "content": [{"type": "output_text", "text": text, "annotations": []}],
                }
            )
        output.extend(
            {
                "type": "function_call",
                "id": "fc_" + id,
                "call_id": id,
                "name": ToolNames.alias(name),
                "arguments": json.dumps(arguments),
                "status": "completed",
            }
            for id, name, arguments in calls
        )
        return {
            "id": "resp_1",
            "object": "response",
            "created_at": 1,
            "status": "completed",
            "model": "test-model",
            "output": output,
            "usage": {"input_tokens": 12, "output_tokens": 3, "total_tokens": 15},
        }
    content = [{"type": "thinking", "thinking": PRIVATE_REASONING, "signature": "signature"}]
    if text:
        content.append({"type": "text", "text": text})
    content.extend(
        {
            "type": "tool_use",
            "id": id,
            "name": ToolNames.alias(name),
            "input": arguments,
        }
        for id, name, arguments in calls
    )
    return {
        "id": "msg_1",
        "type": "message",
        "role": "assistant",
        "model": "test-model",
        "content": content,
        "stop_reason": "tool_use" if calls else "end_turn",
        "usage": {"input_tokens": 12, "output_tokens": 3},
    }


def tool_results(provider, body):
    if provider == "ollama":
        return [json.loads(m["content"]) for m in body["messages"] if m["role"] == "tool"]
    if provider == "openai":
        return [
            json.loads(m["output"])
            for m in body["input"]
            if m.get("type") == "function_call_output"
        ]
    return [
        json.loads(block["content"])
        for message in body["messages"]
        if isinstance(message["content"], list)
        for block in message["content"]
        if block["type"] == "tool_result"
    ]


def mock_provider(name, handler):
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://test/")
    if name == "ollama":
        return OllamaProvider("test-model", "http://test", client=http)
    if name == "openai":
        sdk = AsyncOpenAI(api_key="test-key", http_client=http, max_retries=0)
        return OpenAIProvider("test-model", "test-key", client=sdk)
    sdk = AsyncAnthropic(api_key="test-key", http_client=http, max_retries=0)
    return AnthropicProvider("test-model", "test-key", client=sdk)
