import asyncio
import os
import sys

from tests.conftest import OPERATOR_TOKEN
from tests.test_agent_api import FunctionProvider, final
from tests.test_edge_integration import live_server


async def test_interactive_cli_uses_backend_sessions_and_reset(settings):
    seen = []

    async def model(messages, tools):
        seen.append([m.content for m in messages if m.role == "user"])
        return final("Backend answer")

    async with live_server(settings, llm_provider=FunctionProvider(model)) as (app, port):
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "scripts/chat.py",
            "--url",
            f"http://127.0.0.1:{port}",
            env={**os.environ, "EVE_AGENT_TOKEN": OPERATOR_TOKEN},
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(
                    b"first\nfollow-up\n/reset\nfresh\n/quit\n",
                ),
                10,
            )
            assert process.returncode == 0, stderr.decode()
            assert stdout.count(b"Backend answer") == 3
            assert OPERATOR_TOKEN.encode() not in stdout + stderr
            assert seen == [["first"], ["first", "follow-up"], ["fresh"]]
        finally:
            if process.returncode is None:
                process.kill()
                await process.wait()
