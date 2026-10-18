"""Disposable Linux Docker acceptance. Never targets existing containers or volumes."""

import argparse
import asyncio
import json
import os
import secrets
import ssl
import subprocess
import tempfile
import time
from pathlib import Path
from uuid import uuid4

import httpx
from websockets.asyncio.client import connect

from packages.protocol import EdgeHello, parse_message


def docker(*args, check=True):
    # Do not include Docker errors/logs containing runtime configuration in the report.
    result = subprocess.run(
        ["docker", *args], capture_output=True, text=True, timeout=180, check=False
    )
    if check and result.returncode:
        raise RuntimeError("Isolated Docker operation failed: " + args[0])
    return (result.stdout + (result.stderr if args[0] == "logs" else "")).strip()


async def verify_transport(origin, context, token):
    async with connect(
        origin.replace("https:", "wss:") + "/ws/edge/mirror-ci",
        ssl=context,
        proxy=None,
        additional_headers={"Authorization": "Bearer " + token},
    ) as socket:
        await socket.send(EdgeHello(device_id="mirror-ci").model_dump_json())
        event = parse_message(await asyncio.wait_for(socket.recv(), 5))
        assert event.type == "state.snapshot"


def acceptance(image):
    identity = "eve-acceptance-" + uuid4().hex[:12]
    backend, proxy = identity + "-backend", identity + "-proxy"
    ingress = identity + "-ingress"
    state, certificates = identity + "-state", identity + "-certs"
    report = []
    operator, edge = secrets.token_urlsafe(40), secrets.token_urlsafe(40)
    origin = "https://localhost:18443"
    with tempfile.TemporaryDirectory(prefix=identity) as directory:
        root = Path(directory)
        assets = root / "models"
        assets.mkdir()
        (assets / "probe.txt").write_text("read-only acceptance fixture", encoding="utf-8")
        env = root / "server.env"
        env.write_text(
            "EVE_SERVER_OPERATOR_TOKEN="
            + operator
            + "\n"
            + "EVE_SERVER_EDGE_TOKENS="
            + json.dumps({"mirror-ci": edge})
            + "\n"
            + "EVE_SERVER_DATABASE_PATH=/var/lib/eve/server.sqlite3\n"
            + "EVE_SERVER_WEATHER__ENABLED=false\n"
            + "EVE_SERVER_BROWSER__ENABLED=true\n"
            + "EVE_SERVER_BROWSER__ORIGINS="
            + json.dumps([origin])
            + "\n"
            + "EVE_SERVER_BROWSER__DEVICES="
            + json.dumps({"mirror-ci": {}})
            + "\n"
            + "\n",
            encoding="utf-8",
        )
        os.chmod(env, 0o600)
        caddyfile = root / "Caddyfile"
        caddyfile.write_text(
            "{\n auto_https disable_redirects\n}\n"
            "https://localhost:18443 {\n tls internal\n reverse_proxy " + backend + ":8000\n}\n",
            encoding="utf-8",
        )
        try:
            docker("network", "create", "--internal", identity)
            # Only the TLS proxy joins this host-facing bridge; the backend stays internal.
            docker("network", "create", ingress)
            subnet = docker(
                "network", "inspect", "-f", "{{(index .IPAM.Config 0).Subnet}}", identity
            )
            with env.open("a", encoding="utf-8") as output:
                output.write("FORWARDED_ALLOW_IPS=" + subnet + "\n")
            docker("volume", "create", state)
            docker("volume", "create", certificates)
            docker(
                "run",
                "-d",
                "--name",
                backend,
                "--network",
                identity,
                "--read-only",
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges",
                "--tmpfs",
                "/tmp:rw,noexec,nosuid,size=16m",
                "--env-file",
                str(env),
                "--mount",
                f"type=volume,source={state},target=/var/lib/eve",
                "--mount",
                f"type=bind,source={assets},target=/opt/eve/assets,readonly",
                image,
            )
            docker(
                "run",
                "-d",
                "--name",
                proxy,
                "--network",
                ingress,
                "-p",
                "127.0.0.1:18443:18443",
                "--mount",
                f"type=bind,source={caddyfile},target=/etc/caddy/Caddyfile,readonly",
                "--mount",
                f"type=volume,source={certificates},target=/data",
                "caddy:2",
            )
            docker("network", "connect", identity, proxy)
            deadline = time.monotonic() + 45
            cert = root / "root.crt"
            while time.monotonic() < deadline:
                docker(
                    "cp",
                    proxy + ":/data/caddy/pki/authorities/local/root.crt",
                    str(cert),
                    check=False,
                )
                if cert.exists():
                    break
                time.sleep(0.25)
            context = ssl.create_default_context(cafile=str(cert))
            with httpx.Client(
                base_url=origin, verify=context, trust_env=False, timeout=5
            ) as client:
                last_status = "no response"
                while time.monotonic() < deadline:
                    try:
                        response = client.get("/health/live")
                        last_status = str(response.status_code)
                        if response.status_code == 200:
                            break
                    except httpx.TransportError as exc:
                        last_status = type(exc).__name__ + ": " + str(exc)
                    time.sleep(0.25)
                else:
                    raise RuntimeError("Container readiness deadline exceeded: " + last_status)
                assert client.get("/").status_code == 200
                assert client.get("/settings").status_code == 200
                html = client.get("/").text
                asset = html.split('src="', 1)[1].split('"', 1)[0]
                assert client.get(asset).status_code == 200
                assert "default-src 'none'" in client.get("/").headers["content-security-policy"]
                report.append(
                    "Linux image, static assets, TLS verification and private reverse proxy"
                )
                asyncio.run(verify_transport(origin, context, edge))
                report.append("Authenticated WebSocket through TLS proxy")
                headers = {"Origin": origin}
                pairing = client.post(
                    "/api/browser/pairings", headers=headers, json={"name": "Container acceptance"}
                )
                code = pairing.json()["code"]
                admin = {"Authorization": "Bearer " + operator}
                assert (
                    client.post(
                        "/api/operator/browser/pairings/approve",
                        headers=admin,
                        json={"code": code, "device_id": "mirror-ci"},
                    ).status_code
                    == 200
                )
                claimed = client.get("/api/browser/pairings")
                session = claimed.json()["session"]
                cookie = claimed.headers["set-cookie"].lower()
                assert all(
                    value in cookie
                    for value in ["secure", "httponly", "samesite=strict", "__host-"]
                )
                assert client.post("/api/browser/session/renew", headers=headers).status_code == 403
                assert client.get("/api/browser/state").status_code == 200
                report.append("Migration, pairing, Secure cookie, CSRF and scoped state")
                probe = (
                    "from pathlib import Path; import os; assert os.getuid()==10001; "
                    "assert Path('/opt/eve/assets/probe.txt').read_text(); "
                    "assert not os.access('/opt/eve/assets',os.W_OK); "
                    "assert not os.access('/app',os.W_OK)"
                )
                docker("exec", backend, "python", "-c", probe)
                report.append("Nonroot, read-only root and model mount; writable SQLite volume")
                # SQLite online backup and restore in the isolated persistent volume.
                backup = (
                    "import sqlite3; a=sqlite3.connect('/var/lib/eve/server.sqlite3'); "
                    "b=sqlite3.connect('/var/lib/eve/backup.sqlite3'); a.backup(b); "
                    "c=sqlite3.connect('/var/lib/eve/restored.sqlite3'); b.backup(c); "
                    "assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'; "
                    "assert c.execute('SELECT count(*) FROM browser_sessions').fetchone()[0]==1; "
                    "a.close(); b.close(); c.close()"
                )
                docker("exec", backend, "python", "-c", backup)
                docker("stop", "--time", "15", backend)
                assert docker("inspect", "-f", "{{.State.ExitCode}}", backend) == "0"
                docker("start", backend)
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    try:
                        if client.get("/api/browser/session").status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(0.25)
                else:
                    raise RuntimeError("Persisted session failed after restart")
                assert client.get("/api/browser/session").json()["session"]["id"] == session["id"]
                report.append(
                    "Consistent backup, graceful shutdown, migration reopen and persistent session"
                )
                logs = docker("logs", backend)
                assert operator not in logs and edge not in logs
                assert docker("inspect", "-f", "{{json .HostConfig.PortBindings}}", backend) in {
                    "{}",
                    "null",
                }
            return report
        except Exception:
            for name in (backend, proxy):
                logs = docker("logs", "--tail", "60", name, check=False)
                logs = logs.replace(operator, "[redacted]").replace(edge, "[redacted]")
                status = docker("inspect", "-f", "{{.State.Status}}", name, check=False)
                print(json.dumps({"container": name, "status": status, "logs": logs}), flush=True)
            raise
        finally:
            # Only resources with this invocation's random identity are removed.
            for name in [proxy, backend]:
                docker("rm", "-f", name, check=False)
            docker("network", "rm", identity, check=False)
            docker("network", "rm", ingress, check=False)
            for name in [state, certificates]:
                docker("volume", "rm", name, check=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--allow-isolated-containers", action="store_true", required=True)
    args = parser.parse_args()
    print(json.dumps({"checks": acceptance(args.image), "physical_hardware": False}, indent=2))


if __name__ == "__main__":
    main()
