"""Persistent opaque cookies; pairing approval requires a separate operator credential."""

import hashlib
import hmac
import json
import re
import secrets
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException

from apps.server.browser.models import BrowserSession
from apps.server.services.common import millis


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def csrf(token):
    return hmac.new(token.encode(), b"evemirror-browser-csrf-v1", hashlib.sha256).hexdigest()


class BrowserSessions:
    def __init__(self, settings, database, clock):
        self.settings, self.db, self.clock = settings, database, clock

    def policy_hash(self, device):
        grant = self.settings.devices.get(device)
        if grant is None:
            raise HTTPException(401, "browser_scope_revoked")
        policy = grant.model_dump(mode="json")
        policy["home_entities"] = sorted(policy["home_entities"])
        return digest(json.dumps(policy, sort_keys=True))

    async def begin(self, name, previous=None):
        token = secrets.token_urlsafe(32)
        code = "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(8))
        now = millis(self.clock())

        def create(c):
            c.execute("DELETE FROM browser_pairings WHERE expires_ms<=?", (now,))
            if previous:
                c.execute("DELETE FROM browser_pairings WHERE token_hash=?", (digest(previous),))
            if c.execute("SELECT count(*) FROM browser_pairings").fetchone()[0] >= 100:
                raise HTTPException(429, "pairing_capacity")
            c.execute(
                "INSERT INTO browser_pairings VALUES (?,?,?,?,NULL)",
                (
                    digest(token),
                    digest(code),
                    name,
                    now + self.settings.pairing_seconds * 1000,
                ),
            )

        await self.db.run(create)
        return token, code

    async def approve(self, code, device):
        self.policy_hash(device)

        def approve(c):
            result = c.execute(
                "UPDATE browser_pairings SET device_id=? WHERE code_hash=? "
                "AND device_id IS NULL AND expires_ms>?",
                (device, digest(code), millis(self.clock())),
            )
            if result.rowcount != 1:
                raise HTTPException(404, "pairing_invalid_or_expired")

        await self.db.run(approve)

    async def claim(self, token):
        if not token or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
            raise HTTPException(401, "pairing_required")
        secret, identity, now = secrets.token_urlsafe(32), str(uuid4()), millis(self.clock())

        def claim(c):
            row = c.execute(
                "SELECT * FROM browser_pairings WHERE token_hash=?", (digest(token),)
            ).fetchone()
            if row is None or row["expires_ms"] <= now:
                raise HTTPException(401, "pairing_invalid_or_expired")
            if row["device_id"] is None:
                return None
            policy = self.policy_hash(row["device_id"])
            c.execute("DELETE FROM browser_sessions WHERE expires_ms<=? OR revoked=1", (now,))
            if (
                c.execute("SELECT count(*) FROM browser_sessions").fetchone()[0]
                >= self.settings.max_sessions
            ):
                raise HTTPException(429, "browser_session_capacity")
            c.execute(
                "INSERT INTO browser_sessions VALUES (?,?,?,?,?,?,?,0)",
                (
                    identity,
                    digest(secret),
                    row["device_id"],
                    row["name"],
                    now,
                    now + self.settings.session_seconds * 1000,
                    policy,
                ),
            )
            c.execute("DELETE FROM browser_pairings WHERE token_hash=?", (digest(token),))
            return dict(
                c.execute("SELECT * FROM browser_sessions WHERE id=?", (identity,)).fetchone()
            )

        row = await self.db.run(claim)
        return (row, secret) if row else None

    async def authenticate(self, token):
        if not token or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
            raise HTTPException(401, "browser_session_required")
        row = await self.db.run(
            lambda c: c.execute(
                "SELECT * FROM browser_sessions WHERE token_hash=?", (digest(token),)
            ).fetchone()
        )
        if row is None or row["revoked"] or row["expires_ms"] <= millis(self.clock()):
            raise HTTPException(401, "browser_session_expired_or_revoked")
        if row["policy_hash"] != self.policy_hash(row["device_id"]):
            raise HTTPException(401, "browser_scope_changed")
        return dict(row)

    def public(self, row, token):
        return BrowserSession(
            id=row["id"],
            device_id=row["device_id"],
            name=row["name"],
            expires_at=datetime.fromtimestamp(row["expires_ms"] / 1000, UTC).isoformat(),
            csrf=csrf(token),
            permissions=self.settings.devices[row["device_id"]],
        )

    async def renew(self, row, token):
        new = secrets.token_urlsafe(32)
        expires = millis(self.clock()) + self.settings.session_seconds * 1000

        def rotate(c):
            result = c.execute(
                "UPDATE browser_sessions SET token_hash=?,expires_ms=? "
                "WHERE id=? AND token_hash=? AND revoked=0 AND expires_ms>?",
                (digest(new), expires, row["id"], digest(token), millis(self.clock())),
            )
            if result.rowcount != 1:
                raise HTTPException(401, "browser_session_changed")

        await self.db.run(rotate)
        return {**row, "expires_ms": expires}, new

    async def revoke(self, identity):
        await self.db.run(
            lambda c: c.execute(
                "UPDATE browser_sessions SET revoked=1 WHERE id=?", (str(identity),)
            )
        )

    async def list(self):
        return await self.db.run(
            lambda c: [
                dict(row)
                for row in c.execute(
                    "SELECT id,device_id,name,created_ms,expires_ms,revoked "
                    "FROM browser_sessions ORDER BY created_ms DESC LIMIT 1024"
                ).fetchall()
            ]
        )
