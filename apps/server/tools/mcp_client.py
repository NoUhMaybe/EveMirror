"""Official MCP client with one task owning each transport/session lifecycle.

No sampling, elicitation, roots, prompts, resources, or server instructions are
accepted. Only explicitly allowlisted tools enter Eve's executor. Reconnect is
allowed before a future turn, never as a retry of a failed tool execution.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
from contextlib import AsyncExitStack
from datetime import timedelta

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

from apps.config import MCPServer
from apps.server.tools.base import Tool, ToolDefinition, ToolResult
from apps.server.tools.registry import ToolRegistry


def canonical_name(server: str, tool: str) -> str:
    safe = re.sub(r"[^a-z0-9_]", "_", tool.lower())[:64]
    return f"mcp.{server}.{safe}_{hashlib.sha256(tool.encode()).hexdigest()[:8]}"


async def discard_log(_):
    pass


class MCPConnection:
    def __init__(self, config: MCPServer, registry: ToolRegistry):
        self.config, self.registry = config, registry
        self.task: asyncio.Task | None = None
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=16)
        self.ready: asyncio.Future | None = None
        self.live = False
        self.error: str | None = None
        self.names: set[str] = set()
        self.connect_lock = asyncio.Lock()

    async def start(self):
        async with self.connect_lock:
            if self.task and not self.task.done():
                return
            self.ready = asyncio.get_running_loop().create_future()
            self.task = asyncio.create_task(self._run())
            try:
                async with asyncio.timeout(self.config.connect_timeout):
                    await asyncio.shield(self.ready)
            except asyncio.CancelledError:
                await self.close()
                raise
            except Exception:
                self.error = "mcp_unavailable"
                await self.close()

    async def _run(self):
        active = None
        try:
            async with AsyncExitStack() as stack:
                if self.config.transport == "stdio":
                    # SDK inherits only its safe OS environment; never pass the backend env.
                    errlog = stack.enter_context(open(os.devnull, "w"))  # noqa: ASYNC230 -- OS sink
                    streams = await stack.enter_async_context(
                        stdio_client(
                            StdioServerParameters(
                                command=self.config.command,
                                args=self.config.args,
                                env={k: v.get_secret_value() for k, v in self.config.env.items()},
                            ),
                            errlog=errlog,
                        )
                    )
                else:
                    headers = {}
                    if self.config.bearer_token:
                        headers["Authorization"] = (
                            "Bearer " + self.config.bearer_token.get_secret_value()
                        )
                    http = await stack.enter_async_context(
                        httpx.AsyncClient(
                            headers=headers,
                            timeout=self.config.connect_timeout,
                            follow_redirects=False,
                            trust_env=False,
                        )
                    )
                    streams = await stack.enter_async_context(
                        streamable_http_client(
                            self.config.url,
                            http_client=http,
                        )
                    )
                session = await stack.enter_async_context(
                    ClientSession(
                        streams[0],
                        streams[1],
                        read_timeout_seconds=timedelta(seconds=self.config.connect_timeout),
                        logging_callback=discard_log,
                    )
                )
                await session.initialize()
                discovered, cursor = {}, None
                for _ in range(8):
                    page = await session.list_tools(cursor=cursor)
                    for tool in page.tools:
                        if tool.name in discovered or len(discovered) >= 256:
                            raise ValueError("Invalid discovery")
                        discovered[tool.name] = tool
                    cursor = page.nextCursor
                    if not cursor:
                        break
                else:
                    raise ValueError("Discovery pagination limit")
                # Construct and validate all tools before publishing the new registry entries.
                approved = ToolRegistry()
                for remote_name, policy in self.config.allowed_tools.items():
                    if remote_name not in discovered:
                        continue
                    name = canonical_name(self.config.name, remote_name)

                    async def handler(
                        arguments, context, remote=remote_name, duration=policy.timeout
                    ):
                        return await self.call(remote, arguments, duration)

                    approved.register(
                        Tool(
                            ToolDefinition(
                                name, policy.description, discovered[remote_name].inputSchema
                            ),
                            handler,
                            permission=policy.permission,
                            mutates=policy.mutates,
                            requires_confirmation=policy.requires_confirmation,
                            timeout=policy.timeout,
                            available=lambda: self.live,
                        )
                    )
                for name in self.names:
                    self.registry.tools.pop(name, None)
                self.names = set(approved.tools)
                self.registry.tools.update(approved.tools)
                self.live, self.error = True, None
                if not self.ready.done():
                    self.ready.set_result(None)
                while True:
                    remote, arguments, timeout, active = await self.queue.get()
                    try:
                        result = await session.call_tool(
                            remote,
                            arguments,
                            read_timeout_seconds=timedelta(seconds=timeout),
                        )
                        if result.isError:
                            normalized = ToolResult.error(
                                "mcp_tool_error", "The MCP tool reported failure."
                            )
                        elif result.structuredContent is not None:
                            normalized = ToolResult("success", result.structuredContent)
                        elif any(block.type != "text" for block in result.content):
                            normalized = ToolResult.error(
                                "unsupported_mcp_content",
                                "Only structured or text MCP results are supported.",
                            )
                        else:
                            # No resource dereference or binary expansion; external text stays data.
                            normalized = ToolResult(
                                "success",
                                {
                                    "content": [
                                        block.text
                                        for block in result.content
                                        if block.type == "text"
                                    ]
                                },
                            )
                        if not active.done():
                            active.set_result(normalized)
                        active = None
                    except Exception:
                        if not active.done():
                            active.set_exception(RuntimeError("mcp_execution_failed"))
                        active = None
                        raise
        except asyncio.CancelledError:
            raise
        except Exception:
            self.error = "mcp_unavailable"
        finally:
            self.live = False
            if self.ready and not self.ready.done():
                self.ready.set_result(None)
            if active is not None and not active.done():
                active.set_exception(RuntimeError("mcp_disconnected"))
            while not self.queue.empty():
                *_, pending = self.queue.get_nowait()
                if not pending.done():
                    pending.set_exception(RuntimeError("mcp_disconnected"))

    async def call(self, name, arguments, duration):
        if not self.live:
            return ToolResult.error("mcp_unavailable", "The MCP server is unavailable.")
        future = asyncio.get_running_loop().create_future()
        try:
            self.queue.put_nowait((name, arguments, duration, future))
        except asyncio.QueueFull:
            return ToolResult.error("mcp_busy", "The MCP server is busy.")
        try:
            return await future
        except asyncio.CancelledError:
            # Close the connection instead of leaving a cancelled mutation in a reusable session.
            self.live = False
            if self.task:
                self.task.cancel()
            raise

    async def close(self):
        self.live = False
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)


class MCPManager:
    def __init__(self, definitions: list[MCPServer], registry: ToolRegistry):
        self.connections = [MCPConnection(definition, registry) for definition in definitions]

    async def refresh(self):
        await asyncio.gather(*(connection.start() for connection in self.connections))

    async def close(self):
        await asyncio.gather(*(connection.close() for connection in self.connections))

    def status(self):
        return [
            {
                "name": c.config.name,
                "available": c.live,
                "error": c.error,
                "approved_tools": sorted(c.names),
            }
            for c in self.connections
        ]
