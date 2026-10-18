"""Approve or revoke a kiosk from a trusted terminal. Never paste this token into React."""

import argparse
import os
from urllib.parse import urlsplit

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    commands = parser.add_subparsers(dest="command", required=True)
    approval = commands.add_parser("approve")
    approval.add_argument("code")
    approval.add_argument("--device", required=True)
    commands.add_parser("list")
    revoke = commands.add_parser("revoke")
    revoke.add_argument("session_id")
    args = parser.parse_args()
    url = args.url.rstrip("/")
    parsed = urlsplit(url)
    if parsed.scheme != "https" and not (
        parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    ):
        parser.error("Use HTTPS outside loopback")
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path:
        parser.error("Use a plain server origin")
    token = os.environ.get("EVE_SERVER_OPERATOR_TOKEN")
    if not token:
        parser.error("Set EVE_SERVER_OPERATOR_TOKEN in this trusted terminal")
    with httpx.Client(
        base_url=url,
        headers={"Authorization": "Bearer " + token},
        timeout=10,
        trust_env=False,
        follow_redirects=False,
    ) as client:
        if args.command == "approve":
            response = client.post(
                "/api/operator/browser/pairings/approve",
                json={"code": args.code.upper().replace("-", ""), "device_id": args.device},
            )
        elif args.command == "revoke":
            from uuid import UUID

            identity = UUID(args.session_id)
            response = client.post(f"/api/operator/browser/sessions/{identity}/revoke")
        else:
            response = client.get("/api/operator/browser/sessions")
        if response.status_code != 200:
            print(f"Browser administration failed (HTTP {response.status_code}).")
            raise SystemExit(1)
        print(response.json())


if __name__ == "__main__":
    main()
