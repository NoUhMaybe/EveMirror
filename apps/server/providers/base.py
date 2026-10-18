from __future__ import annotations

import asyncio
import hashlib
import json
import re
from collections.abc import Awaitable
from typing import Protocol, TypeVar

import httpx

from apps.server.agent.messages import GenerationSettings, LLMMessage, LLMResponse
from apps.server.tools.base import ToolDefinition


class ProviderError(Exception):
    """Only stable codes leave this boundary, never SDK exception bodies."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class LLMProvider(Protocol):
    name: str
    model: str

    async def generate(
        self, messages: list[LLMMessage], tools: list[ToolDefinition], settings: GenerationSettings
    ) -> LLMResponse: ...

    async def close(self) -> None: ...


class ToolNames:
    def __init__(self, tools: list[ToolDefinition]):
        self.forward = {t.name: self.alias(t.name) for t in tools}
        self.reverse = {v: k for k, v in self.forward.items()}

    @staticmethod
    def alias(name: str) -> str:
        readable = re.sub(r"[^a-zA-Z0-9_]", "_", name)[:38]
        return "eve_" + readable + "_" + hashlib.sha256(name.encode()).hexdigest()[:12]

    def decode(self, name: str) -> str:
        return self.reverse.get(name, "unknown." + hashlib.sha256(name.encode()).hexdigest()[:12])


def json_text(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


T = TypeVar("T")


async def provider_request(request: Awaitable[T], deadline_seconds: float) -> T:
    try:
        async with asyncio.timeout(deadline_seconds):
            return await request
    except (TimeoutError, httpx.TimeoutException):
        raise ProviderError("provider_timeout") from None
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        if type(exc).__name__ == "APITimeoutError":
            raise ProviderError("provider_timeout") from None
        status = getattr(exc, "status_code", None)
        if status is None and isinstance(exc, httpx.HTTPStatusError):
            status = exc.response.status_code
        code = {
            429: "provider_rate_limited",
            401: "provider_auth_failed",
            403: "provider_auth_failed",
            400: "provider_request_rejected",
            404: "provider_model_unavailable",
        }.get(status, "provider_unavailable")
        raise ProviderError(code) from None


def validate_response(response: LLMResponse) -> LLMResponse:
    calls = response.message.tool_calls
    if len(calls) > 32 or len({c.id for c in calls}) != len(calls):
        raise ProviderError("provider_invalid_response")
    if any(not c.id or len(c.id) > 256 for c in calls):
        raise ProviderError("provider_invalid_response")
    if not calls and not response.message.content.strip():
        raise ProviderError("provider_empty_response")
    if calls and response.status != "tool_calls":
        raise ProviderError("provider_invalid_response")
    return response
