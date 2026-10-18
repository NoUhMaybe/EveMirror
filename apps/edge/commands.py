"""Durable replay protection; network failures never automatically retry hardware."""

from __future__ import annotations

import asyncio
import hashlib
import sqlite3
from datetime import timedelta
from pathlib import Path

from apps.edge.hardware import FeatherService, HardwareError, SimulatedHardware
from packages.protocol import AckPayload, DeviceAck, DeviceCommand, utc_now


class CommandProcessor:
    def __init__(self, device_id: str, hardware: FeatherService | SimulatedHardware, path: Path):
        self.device_id = device_id
        self.hardware = hardware
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path)
        if self._db.execute("PRAGMA user_version").fetchone()[0] not in {0, 1}:
            self._db.close()
            raise RuntimeError(
                "Unsupported edge journal schema version; explicit migration required"
            )
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=FULL")
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS commands "
            "(id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, created REAL NOT NULL, ack TEXT)"
        )
        self._db.execute("PRAGMA user_version=1")
        self._lock = asyncio.Lock()

    def _ack(self, command: DeviceCommand, status: str, code: str = "ok") -> DeviceAck:
        return DeviceAck(
            device_id=self.device_id,
            request_id=command.request_id,
            session_id=command.session_id,
            payload=AckPayload(status=status, code=code, hardware=self.hardware.status),
        )

    async def execute(self, command: DeviceCommand) -> DeviceAck:
        async with self._lock:
            if command.device_id != self.device_id:
                return self._ack(command, "error", "conflict")
            fingerprint = hashlib.sha256(command.payload.model_dump_json().encode()).hexdigest()
            row = self._db.execute(
                "SELECT fingerprint, ack FROM commands WHERE id=?",
                (str(command.request_id),),
            ).fetchone()
            if row:
                if row[0] != fingerprint:
                    return self._ack(command, "error", "conflict")
                if row[1]:
                    original = DeviceAck.model_validate_json(row[1])
                    return original.model_copy(
                        update={
                            "payload": original.payload.model_copy(update={"replayed": True}),
                        }
                    )
                return self._ack(command, "error", "indeterminate")

            now = utc_now()
            if command.expires_at <= now or command.timestamp > now + timedelta(seconds=5):
                return self._ack(command, "error", "expired")
            with self._db:
                self._db.execute(
                    "UPDATE commands SET ack=NULL WHERE created < ? AND ack IS NOT NULL",
                    (now.timestamp() - 86400,),
                )
                self._db.execute(
                    "INSERT INTO commands VALUES (?, ?, ?, NULL)",
                    (str(command.request_id), fingerprint, now.timestamp()),
                )
            # An interrupted operation remains indeterminate across restart.
            try:
                action = command.payload.action
                if action == "get_status":
                    ack = self._ack(command, "completed")
                else:
                    percent = (
                        command.payload.percent
                        if action == "set_brightness"
                        else (0 if command.payload.mode == "sleep" else 100)
                    )
                    await self.hardware.set_brightness(percent)
                    ack = self._ack(command, "accepted")
            except HardwareError as exc:
                ack = self._ack(command, "error", exc.code)
            with self._db:
                self._db.execute(
                    "UPDATE commands SET ack=? WHERE id=?",
                    (ack.model_dump_json(), str(command.request_id)),
                )
            return ack

    def close(self):
        self._db.close()
