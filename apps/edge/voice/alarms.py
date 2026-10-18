"""Device-bound durable timer cache and at-most-once alarm playback attempts."""

import sqlite3
import threading
import time
from datetime import UTC, datetime
from uuid import UUID, uuid5

from packages.audio import SpeechError


class AlarmStore:
    def __init__(self, path, device_id, limit=10000):
        self.path, self.device_id, self.limit = path, device_id, limit
        self.connection = None
        self.lock = threading.Lock()

    def open(self):
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.path, check_same_thread=False, timeout=5)
            try:
                connection.row_factory = sqlite3.Row
                if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise ValueError("Invalid voice journal")
                version = connection.execute("PRAGMA user_version").fetchone()[0]
                if version not in (0, 1):
                    raise ValueError("Unsupported voice journal")
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute("PRAGMA synchronous=FULL")
                if version == 0:
                    connection.executescript("""BEGIN IMMEDIATE;
CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE timers(id TEXT PRIMARY KEY,alarm_id TEXT UNIQUE,
deadline TEXT,status TEXT,version INTEGER);
CREATE TABLE playbacks(id TEXT PRIMARY KEY,status TEXT NOT NULL);
CREATE TABLE dismissals(id TEXT PRIMARY KEY);
PRAGMA user_version=1; COMMIT;""")
                row = connection.execute("SELECT value FROM metadata WHERE key='device'").fetchone()
                if row and row[0] != self.device_id:
                    raise ValueError("Voice journal belongs to another device")
                connection.execute(
                    "INSERT OR IGNORE INTO metadata VALUES ('device',?)", (self.device_id,)
                )
                connection.execute(
                    "UPDATE playbacks SET status='indeterminate' "
                    "WHERE status IN ('reserved','started')"
                )
                connection.commit()
                self.connection = connection
            except Exception:
                connection.close()
                raise SpeechError("voice_storage_unavailable") from None

    def muted(self, default):
        with self.lock:
            row = self.connection.execute("SELECT value FROM metadata WHERE key='muted'").fetchone()
            return default or (row is not None and row[0] == "true")

    def set_muted(self, muted):
        with self.lock, self.connection:
            self.connection.execute(
                "INSERT OR REPLACE INTO metadata VALUES ('muted',?)",
                ("true" if muted else "false",),
            )

    def replace(self, timers, now):
        with self.lock, self.connection:
            self.connection.execute("DELETE FROM timers")
            self.connection.executemany(
                "INSERT INTO timers VALUES (?,?,?,?,?)",
                [
                    (
                        str(row.timer_id),
                        str(row.alarm_id),
                        row.deadline.isoformat() if row.deadline else None,
                        row.status,
                        row.version,
                    )
                    for row in timers
                ],
            )
            self.connection.execute(
                "INSERT OR REPLACE INTO metadata VALUES ('synced_at',?)", (now.isoformat(),)
            )
            self.connection.execute(
                "DELETE FROM dismissals WHERE id NOT IN (SELECT alarm_id FROM timers)"
            )

    def due(self, now, lease):
        with self.lock:
            synced = self.connection.execute(
                "SELECT value FROM metadata WHERE key='synced_at'"
            ).fetchone()
            if (
                not synced
                or not -5 <= (now - datetime.fromisoformat(synced[0])).total_seconds() <= lease
            ):
                return []
            return [
                dict(row)
                for row in self.connection.execute(
                    "SELECT * FROM timers WHERE status!='PAUSED' "
                    "AND alarm_id NOT IN (SELECT id FROM dismissals)"
                ).fetchall()
                if row["status"] == "EXPIRED"
                or (row["deadline"] and datetime.fromisoformat(row["deadline"]) <= now)
            ]

    def reserve(self, alarm_id):
        with self.lock, self.connection:
            row = self.connection.execute(
                "SELECT status FROM playbacks WHERE id=?", (str(alarm_id),)
            ).fetchone()
            if row:
                return row[0]
            if (
                self.connection.execute("SELECT count(*) FROM playbacks").fetchone()[0]
                >= self.limit
            ):
                raise SpeechError("alarm_receipt_capacity")
            self.connection.execute("INSERT INTO playbacks VALUES (?,'reserved')", (str(alarm_id),))
            return None

    def receipt(self, alarm_id):
        with self.lock:
            row = self.connection.execute(
                "SELECT status FROM playbacks WHERE id=?", (str(alarm_id),)
            ).fetchone()
            return row[0] if row else None

    def mark(self, alarm_id, status):
        with self.lock, self.connection:
            self.connection.execute(
                "UPDATE playbacks SET status=? WHERE id=?", (status, str(alarm_id))
            )

    def dismiss(self, alarm_id):
        with self.lock, self.connection:
            if not self.connection.execute(
                "SELECT 1 FROM timers WHERE alarm_id=?", (str(alarm_id),)
            ).fetchone():
                raise SpeechError("alarm_not_found")
            self.connection.execute("INSERT OR IGNORE INTO dismissals VALUES (?)", (str(alarm_id),))

    def pending_dismissals(self):
        with self.lock:
            return [UUID(row[0]) for row in self.connection.execute("SELECT id FROM dismissals")]

    def close(self):
        with self.lock:
            if self.connection:
                self.connection.close()
                self.connection = None


class TimerSynchronizer:
    def __init__(self, store, clock=lambda: datetime.now(UTC), monotonic=time.monotonic):
        self.store, self.clock, self.monotonic = store, clock, monotonic
        self.clear()

    def clear(self):
        self.generation, self.sequence, self.rows, self.started = None, 0, [], 0

    def accept(self, event):
        if event.device_id != self.store.device_id:
            raise SpeechError("timer_device_mismatch")
        payload = event.payload
        if payload.sequence == 0:
            self.clear()
            self.generation, self.started = payload.generation, self.monotonic()
        if (
            payload.generation != self.generation
            or payload.sequence != self.sequence
            or self.monotonic() - self.started > 10
        ):
            self.clear()
            raise SpeechError("invalid_timer_sync")
        for row in payload.timers:
            if row.alarm_id != uuid5(row.timer_id, "alarm") or (
                row.status == "RUNNING" and row.deadline is None
            ):
                self.clear()
                raise SpeechError("invalid_timer_sync")
        self.rows.extend(payload.timers)
        self.sequence += 1
        if len(self.rows) > 1024 or len({row.timer_id for row in self.rows}) != len(self.rows):
            self.clear()
            raise SpeechError("invalid_timer_sync")
        if payload.final:
            self.store.replace(self.rows, self.clock())
            self.clear()
            return True
        return False
