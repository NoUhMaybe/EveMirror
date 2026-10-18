from __future__ import annotations

import asyncio
import hashlib
import time
from contextlib import suppress
from uuid import UUID

from apps.config import ServerSettings
from apps.server.agent.messages import LLMMessage
from apps.server.agent.prompts import system_prompt
from apps.server.agent.sessions import SessionError, SessionStore, context_size
from apps.server.providers.base import LLMProvider, ProviderError, json_text
from apps.server.providers.factory import generation_settings
from apps.server.redaction import secret_redactor
from apps.server.services.common import ServiceError
from apps.server.tools.base import Principal, ToolContext
from apps.server.tools.executor import ExecutionLedger, ToolExecutor
from apps.server.tools.registry import ToolRegistry


class Orchestrator:
    def __init__(
        self,
        settings: ServerSettings,
        provider: LLMProvider | None,
        registry: ToolRegistry,
        sessions: SessionStore,
        mcp=None,
        services=None,
    ):
        self.settings, self.provider = settings, provider
        self.registry, self.sessions, self.mcp = registry, sessions, mcp
        self.services = services
        self.redact = secret_redactor(settings)
        self.executor = ToolExecutor(registry, settings.agent, self.redact)

    async def turn(
        self,
        principal: Principal,
        text: str,
        request_id: UUID,
        session_id: UUID | None = None,
        device_id: str | None = None,
    ) -> dict:
        if self.provider is None:
            raise SessionError("provider_not_configured", 503)
        fingerprint = hashlib.sha256(json_text([text, device_id]).encode()).hexdigest()
        session, cached = self.sessions.turn(
            principal,
            request_id,
            session_id,
            device_id,
            fingerprint,
        )
        if cached is not None:
            return cached
        started = time.monotonic()
        user = LLMMessage("user", text)
        summaries, usage = [], {}
        claim = [False]
        task = asyncio.create_task(
            self._generate(
                session, principal, user, request_id, summaries, usage, fingerprint, claim
            )
        )
        session.task = task
        result = {
            "session_id": str(session.id),
            "request_id": str(request_id),
            "provider": self.provider.name,
            "model": self.provider.model,
            "status": "error",
            "response": None,
            "error": None,
            "tools": summaries,
            "usage": usage,
        }
        try:
            response, turn_messages = await task
            result.update(
                status="complete", response=response.message.content, model=response.model
            )
            self.sessions.remember(session, turn_messages)
        except asyncio.CancelledError:
            result.update(status="cancelled", error={"code": "turn_cancelled"})
        except TimeoutError:
            result["error"] = {"code": "turn_timeout"}
        except ProviderError as exc:
            result["error"] = {"code": exc.code}
        except Exception:
            result["error"] = {"code": "turn_failed"}
        finally:
            if claim[0]:
                with suppress(ServiceError):
                    await self.services.db.finish_turn(
                        principal.id, request_id, result["status"] != "complete"
                    )
            if result["status"] != "complete":
                # Do not retain a broken provider tool sequence; record outcome uncertainty.
                self.sessions.remember(
                    session,
                    [
                        user,
                        LLMMessage(
                            "assistant",
                            "The previous turn did not complete. Any interrupted action "
                            "may have an unknown outcome; do not retry automatically.",
                        ),
                    ],
                )
            result["latency_ms"] = round((time.monotonic() - started) * 1000)
            self.sessions.finish(session, request_id, fingerprint, result)
            session.task = None
        return result

    async def _generate(
        self, session, principal, user, request_id, summaries, usage, fingerprint, claim
    ):
        limits = self.settings.agent
        async with asyncio.timeout(limits.turn_timeout):
            if self.services and self.services.started:
                if self.services.db.available:
                    previous = await self.services.db.begin_turn(
                        principal.id, request_id, fingerprint
                    )
                    if previous:
                        raise ProviderError(previous)
                    claim[0] = True
                await self.services.prepare()
            if self.mcp:
                await self.mcp.refresh()
            tools = self.registry.definitions(principal, limits)
            tool_bytes = len(json_text([t.__dict__ for t in tools]).encode())
            prefix = LLMMessage("system", system_prompt(self.settings.agent_prompt_suffix))
            messages = [prefix, *session.messages(), user]
            start = len(messages) - 1
            ledger = ExecutionLedger()
            rounds, count = 0, 0
            context = ToolContext(principal, session.id, request_id, session.device_id)
            while True:
                if (
                    context_size(messages) + tool_bytes > limits.max_context_bytes
                    or len(messages) > limits.max_context_messages
                ):
                    raise ProviderError("context_limit")
                response = await self.provider.generate(
                    messages, tools, generation_settings(self.settings)
                )
                response.message.content = self.redact(response.message.content)
                for key, value in response.usage.items():
                    usage[key] = usage.get(key, 0) + value
                if response.status == "length":
                    raise ProviderError("provider_output_limit")
                messages.append(response.message)
                if context_size(messages) + tool_bytes > limits.max_context_bytes:
                    raise ProviderError("context_limit")
                calls = response.message.tool_calls
                if not calls:
                    return response, messages[start:]
                rounds += 1
                count += len(calls)
                if rounds > limits.max_tool_rounds or count > limits.max_tool_calls:
                    raise ProviderError("tool_limit")
                # Preserve model order. Mutations are never speculatively parallelized.
                for call in calls:
                    result = await self.executor.execute(call, context, ledger)
                    if self.services:
                        await self.services.observe(call, result, context)
                    summaries.append(
                        {
                            "name": call.name,
                            "call_id": call.id,
                            "status": result.status,
                            "error_code": result.code,
                            "replayed": result.replayed,
                        }
                    )
                    messages.append(
                        LLMMessage(
                            "tool",
                            json_text(result.payload()),
                            call_id=call.id,
                            tool_name=call.name,
                            is_error=result.status == "error",
                        )
                    )
