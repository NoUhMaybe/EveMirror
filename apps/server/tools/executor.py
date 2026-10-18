"""Central enforcement, serialized side effects, and a per-turn execution receipt ledger."""

import asyncio
import hashlib
import json
from dataclasses import dataclass, field, replace

from apps.config import AgentLimits
from apps.server.agent.messages import ToolCall
from apps.server.providers.base import json_text
from apps.server.tools.base import ToolContext, ToolResult
from apps.server.tools.permissions import denied
from apps.server.tools.registry import ToolRegistry


@dataclass
class ExecutionLedger:
    calls: dict[str, tuple[str, ToolResult]] = field(default_factory=dict)
    mutations: dict[str, ToolResult] = field(default_factory=dict)


class ToolExecutor:
    def __init__(self, registry: ToolRegistry, limits: AgentLimits):
        self.registry, self.limits = registry, limits

    async def execute(self, call: ToolCall, context: ToolContext, ledger: ExecutionLedger):
        tool = self.registry.tools.get(call.name)
        if tool is None:
            return ToolResult.error("unknown_tool", "Requested tool is not registered.")
        policy = denied(tool, context.principal, self.limits)
        if policy:
            return ToolResult.error(policy, "Backend policy does not permit this action.")
        if not tool.available():
            return ToolResult.error("tool_unavailable", "The configured tool is unavailable.")
        try:
            raw = call.arguments if isinstance(call.arguments, str) else json_text(call.arguments)
            if len(raw.encode()) > self.limits.max_argument_bytes:
                return ToolResult.error("arguments_too_large", "Tool arguments exceed the limit.")
            arguments = json.loads(raw)
            if not isinstance(arguments, dict):
                raise ValueError("object required")
            arguments = self.registry.validate(tool, arguments)
            encoded = json.dumps(arguments, sort_keys=True, allow_nan=False, separators=(",", ":"))
        except Exception:
            # Validation errors can contain supplied secrets; only this code crosses the boundary.
            return ToolResult.error("invalid_arguments", "Arguments do not match the tool schema.")
        fingerprint = hashlib.sha256((call.name + ":" + encoded).encode()).hexdigest()
        previous = ledger.calls.get(call.id)
        if previous:
            if previous[0] != fingerprint:
                return ToolResult.error("call_id_conflict", "Tool call ID was already used.")
            return replace(previous[1], replayed=True)
        if tool.mutates and fingerprint in ledger.mutations:
            result = ledger.mutations[fingerprint]
            ledger.calls[call.id] = (fingerprint, result)
            return replace(result, replayed=True)
        uncertain = ToolResult.error(
            "indeterminate" if tool.mutates else "tool_cancelled",
            "Execution was interrupted; do not retry a state change automatically.",
        )
        ledger.calls[call.id] = (fingerprint, uncertain)
        if tool.mutates:
            ledger.mutations[fingerprint] = uncertain
        try:
            async with asyncio.timeout(min(tool.timeout, self.limits.tool_timeout)):
                result = await tool.handler(arguments, context)
            if not isinstance(result, ToolResult):
                raise ValueError("invalid handler result")
            if len(json_text(result.payload()).encode()) > self.limits.max_result_bytes:
                result = ToolResult.error(
                    "result_too_large",
                    "Result exceeded the limit; a state change may have occurred.",
                )
        except TimeoutError:
            result = ToolResult.error(
                "indeterminate" if tool.mutates else "tool_timeout",
                "Tool timed out. State-changing operations are never retried automatically.",
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            result = ToolResult.error(
                "indeterminate" if tool.mutates else "tool_failed",
                "Tool execution failed. A state-changing outcome may be unknown.",
            )
        ledger.calls[call.id] = (fingerprint, result)
        if tool.mutates:
            ledger.mutations[fingerprint] = result
        return result
