"""One connection/transaction owner, WAL, schema migrations and durable action receipts."""

import asyncio
import hashlib
import json
import sqlite3
from contextlib import suppress
from pathlib import Path
from uuid import UUID

from apps.server.providers.base import json_text
from apps.server.services.common import ServiceError

MIGRATIONS = [
    """
CREATE TABLE timers (
 id TEXT PRIMARY KEY, owner TEXT NOT NULL, device_id TEXT NOT NULL, name TEXT,
 duration_ms INTEGER NOT NULL CHECK(duration_ms > 0),
 remaining_ms INTEGER NOT NULL CHECK(remaining_ms >= 0),
 created_ms INTEGER NOT NULL, deadline_ms INTEGER,
 status TEXT NOT NULL CHECK(status IN ('RUNNING','PAUSED','EXPIRED','CANCELLED','ACKNOWLEDGED')),
 expired_ms INTEGER, acknowledged_ms INTEGER, updated_ms INTEGER NOT NULL, version INTEGER NOT NULL,
 CHECK((status='RUNNING' AND deadline_ms IS NOT NULL) OR status!='RUNNING')
);
CREATE INDEX timers_deadlines ON timers(status,deadline_ms);
CREATE TABLE alarms (
 id TEXT PRIMARY KEY, timer_id TEXT NOT NULL UNIQUE REFERENCES timers(id),
 owner TEXT NOT NULL, device_id TEXT NOT NULL, created_ms INTEGER NOT NULL, acknowledged_ms INTEGER
);
CREATE TABLE operations (
 owner TEXT NOT NULL, id TEXT NOT NULL, fingerprint TEXT NOT NULL, result TEXT,
 PRIMARY KEY(owner,id)
);
CREATE TABLE turns (
 owner TEXT NOT NULL, id TEXT NOT NULL, fingerprint TEXT NOT NULL, status TEXT NOT NULL,
 PRIMARY KEY(owner,id)
);
CREATE TABLE events (
 sequence INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE,
 timestamp TEXT NOT NULL, owner TEXT NOT NULL, device_id TEXT, type TEXT NOT NULL,
 resource_id TEXT, payload TEXT NOT NULL
);
CREATE INDEX events_scope ON events(owner,device_id,sequence);
CREATE TABLE views (
 owner TEXT NOT NULL, device_id TEXT NOT NULL, view TEXT NOT NULL, layout TEXT NOT NULL,
 PRIMARY KEY(owner,device_id)
);
CREATE TABLE resources (
 owner TEXT NOT NULL, device_id TEXT NOT NULL, kind TEXT NOT NULL,
 id TEXT NOT NULL, payload TEXT NOT NULL,
 PRIMARY KEY(owner,device_id,kind,id)
);
""",
    """
CREATE TABLE alarm_delivery (
 alarm_id TEXT PRIMARY KEY REFERENCES alarms(id), device_id TEXT NOT NULL,
 status TEXT NOT NULL, updated_at TEXT NOT NULL
);
""",
    """
CREATE TABLE browser_pairings (
 token_hash TEXT PRIMARY KEY, code_hash TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
 expires_ms INTEGER NOT NULL, device_id TEXT
);
CREATE TABLE browser_sessions (
 id TEXT PRIMARY KEY, token_hash TEXT NOT NULL UNIQUE, device_id TEXT NOT NULL,
 name TEXT NOT NULL, created_ms INTEGER NOT NULL, expires_ms INTEGER NOT NULL,
 policy_hash TEXT NOT NULL, revoked INTEGER NOT NULL DEFAULT 0
);
""",
]


class Database:
    def __init__(self, path: Path, busy_ms=5000, max_operations=100000):
        self.path, self.busy_ms, self.max_operations = path, busy_ms, max_operations
        self.connection = None
        self.lock = asyncio.Lock()
        self.error = None

    @property
    def available(self):
        return self.connection is not None and self.error is None

    async def _owned(self, function):
        async with self.lock:
            task = asyncio.create_task(asyncio.to_thread(function))
            try:
                return await asyncio.shield(task)
            except asyncio.CancelledError:
                # Keep ownership until the SQLite transaction actually ends.
                # Repeated cancellation must not cancel the thread's wrapper task
                # and release this lock while the underlying thread still runs.
                while not task.done():
                    try:
                        await asyncio.shield(task)
                    except asyncio.CancelledError:
                        continue
                    except Exception:
                        break
                if not task.cancelled():
                    task.exception()
                raise

    async def open(self):
        def initialize():
            if self.connection is not None:
                return
            connection = None
            try:
                if str(self.path) != ":memory:":
                    self.path.parent.mkdir(parents=True, exist_ok=True)
                connection = sqlite3.connect(
                    str(self.path), timeout=self.busy_ms / 1000, check_same_thread=False
                )
                connection.row_factory = sqlite3.Row
                connection.execute("PRAGMA foreign_keys=ON")
                connection.execute(f"PRAGMA busy_timeout={self.busy_ms}")
                if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise ValueError("Integrity check failed")
                version = connection.execute("PRAGMA user_version").fetchone()[0]
                if version > len(MIGRATIONS):
                    raise ValueError("Unknown database version")
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute("PRAGMA synchronous=FULL")
                for number in range(version, len(MIGRATIONS)):
                    # executescript controls its transaction; migration/version change are atomic.
                    connection.executescript(
                        "BEGIN IMMEDIATE;\n"
                        + MIGRATIONS[number]
                        + f"\nPRAGMA user_version={number + 1};\nCOMMIT;"
                    )
                # An existing version marker is insufficient if a table/column was damaged.
                for query in (
                    "SELECT id,owner,device_id,name,duration_ms,remaining_ms,created_ms,"
                    "deadline_ms,status,expired_ms,acknowledged_ms,updated_ms,version "
                    "FROM timers LIMIT 0",
                    "SELECT id,timer_id,owner,device_id,created_ms,acknowledged_ms "
                    "FROM alarms LIMIT 0",
                    "SELECT owner,id,fingerprint,result FROM operations LIMIT 0",
                    "SELECT owner,id,fingerprint,status FROM turns LIMIT 0",
                    "SELECT sequence,id,timestamp,owner,device_id,type,resource_id,payload "
                    "FROM events LIMIT 0",
                    "SELECT owner,device_id,view,layout FROM views LIMIT 0",
                    "SELECT owner,device_id,kind,id,payload FROM resources LIMIT 0",
                    "SELECT alarm_id,device_id,status,updated_at FROM alarm_delivery LIMIT 0",
                    "SELECT token_hash,code_hash,name,expires_ms,device_id "
                    "FROM browser_pairings LIMIT 0",
                    "SELECT id,token_hash,device_id,name,created_ms,expires_ms,policy_hash,revoked "
                    "FROM browser_sessions LIMIT 0",
                ):
                    connection.execute(query)
                self.connection, self.error = connection, None
            except Exception:
                if connection:
                    connection.close()
                self.error = "database_unavailable"

        await self._owned(initialize)

    async def run(self, function):
        def transaction():
            if self.connection is None:
                raise ServiceError("database_unavailable", "Persistent service is unavailable.")
            try:
                self.connection.execute("BEGIN IMMEDIATE")
                result = function(self.connection)
                self.connection.commit()
                return result
            except sqlite3.Error:
                with suppress(sqlite3.Error):
                    self.connection.rollback()
                with suppress(sqlite3.Error):
                    self.connection.close()
                self.connection = None
                self.error = "database_unavailable"
                raise ServiceError("database_unavailable", "Database transaction failed.") from None
            except Exception:
                self.connection.rollback()
                raise

        return await self._owned(transaction)

    def reserve(self, connection, owner, operation_id, action, arguments):
        try:
            operation_id = str(UUID(str(operation_id)))
        except ValueError:
            raise ServiceError("invalid_operation", "A valid operation UUID is required.") from None
        fingerprint = hashlib.sha256(json_text([action, arguments]).encode()).hexdigest()
        previous = connection.execute(
            "SELECT fingerprint,result FROM operations WHERE owner=? AND id=?",
            (owner, str(operation_id)),
        ).fetchone()
        if previous:
            if previous["fingerprint"] != fingerprint:
                raise ServiceError(
                    "operation_conflict", "Operation ID refers to different arguments."
                )
            return True, (
                json.loads(previous["result"])
                if previous["result"]
                else {
                    "status": "error",
                    "error": {
                        "code": "indeterminate",
                        "message": "Earlier execution may have occurred; it will not be retried.",
                    },
                }
            )
        if (
            connection.execute("SELECT count(*) FROM operations").fetchone()[0]
            >= self.max_operations
        ):
            raise ServiceError(
                "operation_capacity", "Operation journal requires administrator maintenance."
            )
        connection.execute(
            "INSERT INTO operations VALUES (?,?,?,NULL)", (owner, str(operation_id), fingerprint)
        )
        return False, None

    @staticmethod
    def complete(connection, owner, operation_id, result):
        connection.execute(
            "UPDATE operations SET result=? WHERE owner=? AND id=?",
            (
                json_text(result),
                owner,
                str(UUID(str(operation_id))),
            ),
        )

    async def begin_turn(self, owner, request_id, fingerprint):
        def claim(connection):
            previous = connection.execute(
                "SELECT * FROM turns WHERE owner=? AND id=?", (owner, str(request_id))
            ).fetchone()
            if previous:
                if previous["fingerprint"] != fingerprint:
                    return "request_conflict"
                return (
                    "turn_already_processed"
                    if previous["status"] == "DONE"
                    else "turn_indeterminate"
                )
            if (
                connection.execute("SELECT count(*) FROM turns").fetchone()[0]
                >= self.max_operations
            ):
                return "operation_capacity"
            connection.execute(
                "INSERT INTO turns VALUES (?,?,?,'STARTED')", (owner, str(request_id), fingerprint)
            )
            return None

        return await self.run(claim)

    async def finish_turn(self, owner, request_id, indeterminate=False):
        await self.run(
            lambda c: c.execute(
                "UPDATE turns SET status=? WHERE owner=? AND id=?",
                ("UNKNOWN" if indeterminate else "DONE", owner, str(request_id)),
            )
        )

    async def close(self):
        def shutdown():
            if self.connection:
                self.connection.close()
                self.connection = None

        await self._owned(shutdown)
