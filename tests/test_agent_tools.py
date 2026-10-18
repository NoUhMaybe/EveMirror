import asyncio
from uuid import uuid4

import pytest

from apps.config import AgentLimits
from apps.server.agent.messages import ToolCall
from apps.server.tools.base import Principal, Tool, ToolContext, ToolDefinition, ToolResult
from apps.server.tools.executor import ExecutionLedger, ToolExecutor
from apps.server.tools.registry import ToolRegistry

PRINCIPAL = Principal("test", frozenset({"mirror-1"}), True)
CONTEXT = ToolContext(PRINCIPAL, uuid4(), uuid4(), "mirror-1")
SCHEMA = {
    "type": "object",
    "properties": {"value": {"type": "integer", "minimum": 0}},
    "required": ["value"],
    "additionalProperties": False,
}


def registry_with(handler, **kwargs):
    registry = ToolRegistry()
    registry.register(
        Tool(ToolDefinition("test.action", "Test-only action", SCHEMA), handler, **kwargs)
    )
    return registry


@pytest.mark.parametrize(
    "arguments,code",
    [
        ({"value": -1}, "invalid_arguments"),
        ({"value": "1"}, "invalid_arguments"),
        ({"value": 1, "shell": "secret"}, "invalid_arguments"),
        ("{", "invalid_arguments"),
        ("[]", "invalid_arguments"),
        ('{"value":' + '"a"' * 9000 + "}", "arguments_too_large"),
    ],
)
async def test_arguments_validated_before_handler(arguments, code):
    calls = []

    async def handler(args, context):
        calls.append(args)
        return ToolResult("success", args)

    executor = ToolExecutor(registry_with(handler), AgentLimits())
    result = await executor.execute(
        ToolCall("one", "test.action", arguments), CONTEXT, ExecutionLedger()
    )
    assert result.code == code and not calls


@pytest.mark.parametrize(
    "policy,code",
    [
        ({"permission": "sensitive", "mutates": True}, "permission_denied"),
        ({"requires_confirmation": True}, "confirmation_required"),
        ({"permission": "low_risk", "mutates": True}, "permission_denied"),
        ({"available": lambda: False}, "tool_unavailable"),
    ],
)
async def test_backend_policy_cannot_be_overridden_by_tool_arguments(policy, code):
    async def forbidden(args, context):
        pytest.fail("Unauthorized handler ran")

    executor = ToolExecutor(registry_with(forbidden, **policy), AgentLimits())
    result = await executor.execute(
        ToolCall("id", "test.action", {"value": 1}), CONTEXT, ExecutionLedger()
    )
    assert result.code == code
    assert not executor.registry.definitions(PRINCIPAL, AgentLimits())


async def test_mutation_receipts_deduplicate_ids_and_identical_actions_and_reject_conflicts():
    calls = []

    async def handler(args, context):
        calls.append(args)
        return ToolResult("success", args)

    executor = ToolExecutor(
        registry_with(handler, permission="low_risk", mutates=True),
        AgentLimits(allow_mutations=True),
    )
    ledger = ExecutionLedger()
    for id in ["one", "one", "different-id"]:
        result = await executor.execute(ToolCall(id, "test.action", {"value": 1}), CONTEXT, ledger)
        assert result.status == "success"
    conflict = await executor.execute(ToolCall("one", "test.action", {"value": 2}), CONTEXT, ledger)
    assert conflict.code == "call_id_conflict" and len(calls) == 1
    unknown = await executor.execute(ToolCall("bad", "shell.run", {}), CONTEXT, ledger)
    assert unknown.code == "unknown_tool"


@pytest.mark.parametrize("mutates", [False, True])
async def test_timeout_does_not_retry_and_reports_uncertain_mutations(mutates):
    calls = []

    async def handler(args, context):
        calls.append(args)
        await asyncio.Event().wait()

    executor = ToolExecutor(
        registry_with(
            handler,
            permission="low_risk" if mutates else "read_only",
            mutates=mutates,
        ),
        AgentLimits(allow_mutations=True, tool_timeout=0.02),
    )
    ledger = ExecutionLedger()
    call = ToolCall("one", "test.action", {"value": 1})
    result = await executor.execute(call, CONTEXT, ledger)
    assert result.code == ("indeterminate" if mutates else "tool_timeout")
    assert (await executor.execute(call, CONTEXT, ledger)).code == result.code
    assert len(calls) == 1


async def test_handler_failures_and_result_size_are_honest_and_redacted():
    async def failed(args, context):
        raise RuntimeError("secret-provider-key")

    async def oversized(args, context):
        return ToolResult("success", "x" * 17000)

    for handler, code in [(failed, "tool_failed"), (oversized, "result_too_large")]:
        executor = ToolExecutor(registry_with(handler), AgentLimits())
        result = await executor.execute(
            ToolCall("id", "test.action", {"value": 1}), CONTEXT, ExecutionLedger()
        )
        assert result.code == code
        assert "secret" not in str(result.payload())


async def test_cancellation_keeps_mutation_uncertain_and_never_reexecutes_it():
    entered = asyncio.Event()
    executions = []

    async def handler(arguments, context):
        executions.append(arguments)
        entered.set()
        await asyncio.Event().wait()

    executor = ToolExecutor(
        registry_with(handler, mutates=True, permission="low_risk"),
        AgentLimits(allow_mutations=True),
    )
    ledger = ExecutionLedger()
    call = ToolCall("one", "test.action", {"value": 1})
    task = asyncio.create_task(executor.execute(call, CONTEXT, ledger))
    await asyncio.wait_for(entered.wait(), 1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    result = await executor.execute(ToolCall("two", "test.action", {"value": 1}), CONTEXT, ledger)
    assert result.code == "indeterminate" and len(executions) == 1


async def test_client_permissions_and_device_permissions_are_enforced(settings):
    from apps.server.gateway import Gateway
    from apps.server.tools.native import register_native

    registry = ToolRegistry()
    register_native(registry, Gateway(settings))
    executor = ToolExecutor(registry, AgentLimits(allow_mutations=True))
    identity = Principal("read-only", frozenset({"mirror-1"}), False)
    context = ToolContext(identity, uuid4(), uuid4())
    denied = await executor.execute(
        ToolCall("one", "mirror.set_brightness", {"percent": 10}),
        context,
        ExecutionLedger(),
    )
    assert denied.code == "permission_denied"
    other_device = await executor.execute(
        ToolCall("two", "mirror.get_status", {"device_id": "not-my-device"}),
        context,
        ExecutionLedger(),
    )
    assert other_device.code == "device_not_authorized"


@pytest.mark.parametrize("ref", ["https://attacker/schema", "file:///secret", "other.json"])
def test_external_schema_references_never_trigger_network_or_file_reads(ref):
    async def handler(args, context):
        pass

    registry = ToolRegistry()
    with pytest.raises(ValueError, match="External"):
        registry.register(
            Tool(ToolDefinition("bad.tool", "Bad", {"type": "object", "$ref": ref}), handler)
        )
