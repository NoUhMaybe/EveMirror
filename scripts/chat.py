"""Trusted terminal client for the backend, never a separate agent implementation."""

import argparse
import asyncio
import os
from contextlib import suppress
from uuid import uuid4

import httpx

from apps.config import http_endpoint


async def chat(args):
    token = os.environ.get("EVE_AGENT_TOKEN") or os.environ.get("EVE_SERVER_OPERATOR_TOKEN")
    if not token:
        raise SystemExit("Set EVE_AGENT_TOKEN (scoped client) or EVE_SERVER_OPERATOR_TOKEN.")
    url = http_endpoint(args.url, remote_tls=True)
    session_id = None
    async with httpx.AsyncClient(
        base_url=url,
        headers={"Authorization": "Bearer " + token},
        timeout=310,
        follow_redirects=False,
        trust_env=False,
    ) as client:
        status = await client.get("/api/agent/status")
        status.raise_for_status()
        state = status.json()
        if not state["configured"]:
            raise SystemExit("Backend provider is unconfigured: " + state["configuration_error"])
        print(
            f"{state['provider']} / {state['model']}. "
            "/reset, /status, /quit; Ctrl+C cancels a turn."
        )
        try:
            while True:
                text = await asyncio.to_thread(input, "You: ")
                if text in {"/quit", "/exit"}:
                    break
                if text == "/status":
                    print((await client.get("/api/agent/status")).json())
                    continue
                if text == "/reset":
                    if session_id:
                        reset = await client.post(f"/api/agent/sessions/{session_id}/reset")
                        reset.raise_for_status()
                    print("Context reset.")
                    continue
                if not text.strip():
                    continue
                if session_id is None:
                    created = await client.post(
                        "/api/agent/sessions", json={"device_id": args.device}
                    )
                    created.raise_for_status()
                    session_id = created.json()["session_id"]
                response = await client.post(
                    "/api/agent/turn",
                    json={
                        "request_id": str(uuid4()),
                        "session_id": session_id,
                        "text": text,
                    },
                )
                if response.status_code == 404:
                    print("Session expired. Submit your next message to start fresh.")
                    session_id = None
                    continue
                if response.status_code == 409:
                    print("Session limit or conflict; start a new CLI session.")
                    continue
                response.raise_for_status()
                result = response.json()
                print("Eve:", result["response"] or result["error"]["code"])
                for tool in result["tools"]:
                    print(f"  {tool['name']}: {tool['status']} ({tool['error_code'] or 'ok'})")
        finally:
            if session_id:
                # Also runs when asyncio.run handles Ctrl+C by cancelling the active client turn.
                with suppress(httpx.HTTPError):
                    await client.post(f"/api/agent/sessions/{session_id}/cancel", timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--device", default=None)
    args = parser.parse_args()
    try:
        asyncio.run(chat(args))
    except KeyboardInterrupt:
        pass
    except httpx.HTTPError:
        raise SystemExit(
            "Backend request failed; check availability and credentials. No turn was retried."
        ) from None


if __name__ == "__main__":
    main()
