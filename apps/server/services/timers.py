"""UTC deadlines are authoritative. Sleeping is monotonic and periodically reconciled."""

import asyncio
from uuid import UUID, uuid4, uuid5

from apps.server.services.common import ServiceError, iso, millis, utc_now


class TimerService:
    def __init__(self, database, events, settings, clock=utc_now):
        self.db, self.events, self.settings, self.clock = database, events, settings, clock
        self.changed = asyncio.Event()
        self.task = None

    @staticmethod
    def _device(principal, device_id):
        if device_id not in principal.device_ids:
            raise ServiceError("device_not_authorized", "Select an authorized timer device.")

    @staticmethod
    def _record(row, now):
        return {
            "id": row["id"],
            "device_id": row["device_id"],
            "name": row["name"],
            "duration_ms": row["duration_ms"],
            "status": row["status"],
            "version": row["version"],
            "remaining_ms": max(0, row["deadline_ms"] - now)
            if row["status"] == "RUNNING"
            else row["remaining_ms"],
            "created_at": iso(row["created_ms"]),
            "deadline": iso(row["deadline_ms"]),
            "expired_at": iso(row["expired_ms"]),
            "acknowledged_at": iso(row["acknowledged_ms"]),
            "updated_at": iso(row["updated_ms"]),
        }

    def _expire(self, connection, now):
        rows = connection.execute(
            "SELECT * FROM timers WHERE status='RUNNING' AND deadline_ms<=?", (now,)
        ).fetchall()
        for row in rows:
            alarm_id = str(uuid5(UUID(row["id"]), "alarm"))
            connection.execute(
                (
                    "UPDATE timers SET status='EXPIRED',remaining_ms=0,"
                    "expired_ms=deadline_ms,updated_ms=?,version=version+1 WHERE "
                    "id=? AND status='RUNNING'"
                ),
                (now, row["id"]),
            )
            connection.execute(
                "INSERT INTO alarms VALUES (?,?,?,?,?,NULL)",
                (
                    alarm_id,
                    row["id"],
                    row["owner"],
                    row["device_id"],
                    row["deadline_ms"],
                ),
            )
            self.events.append(
                connection,
                row["owner"],
                row["device_id"],
                "timer.expired",
                {
                    "timer_id": row["id"],
                    "alarm_id": alarm_id,
                    "expired_at": iso(row["deadline_ms"]),
                },
                row["id"],
                alarm_id,
            )
            connection.execute(
                (
                    "INSERT INTO views VALUES (?,?,'timers','default') ON "
                    "CONFLICT(owner,device_id) DO UPDATE SET view='timers'"
                ),
                (row["owner"], row["device_id"]),
            )

    async def reconcile(self):
        def reconcile(connection):
            now = millis(self.clock())
            self._expire(connection, now)
            row = connection.execute(
                "SELECT min(deadline_ms) FROM timers WHERE status='RUNNING'"
            ).fetchone()
            return row[0]

        return await self.db.run(reconcile)

    async def start(self):
        if self.db.available:
            await self.reconcile()
        self.task = asyncio.create_task(self._schedule())

    async def _schedule(self):
        while True:
            self.changed.clear()
            try:
                if not self.db.available:
                    await self.db.open()
                deadline = await self.reconcile()
                wait = (
                    self.settings.reconcile_seconds
                    if deadline is None
                    else min(
                        self.settings.reconcile_seconds,
                        max(0.001, (deadline - millis(self.clock())) / 1000),
                    )
                )
            except ServiceError:
                wait = max(1, self.settings.reconcile_seconds)
            try:
                await asyncio.wait_for(self.changed.wait(), wait)
            except TimeoutError:
                pass

    async def mutate(
        self,
        principal,
        device_id,
        operation_id,
        action,
        *,
        timer_id=None,
        name=None,
        duration_seconds=None,
    ):
        self._device(principal, device_id)
        arguments = [
            device_id,
            str(timer_id) if timer_id is not None else None,
            name,
            duration_seconds,
        ]

        def apply(connection, now):
            if action == "create":
                if (
                    not isinstance(duration_seconds, int)
                    or not 1 <= duration_seconds <= self.settings.max_duration_seconds
                ):
                    raise ServiceError(
                        "invalid_duration", "Timer duration is outside configured limits."
                    )
                if name is not None and (not isinstance(name, str) or len(name) > 120):
                    raise ServiceError("invalid_name", "Timer name is too long.")
                count = connection.execute(
                    (
                        "SELECT count(*) FROM timers WHERE owner=? AND device_id=? AND "
                        "status IN ('RUNNING','PAUSED','EXPIRED')"
                    ),
                    (principal.id, device_id),
                ).fetchone()[0]
                if count >= self.settings.max_active:
                    raise ServiceError(
                        "timer_capacity", "Too many active or unacknowledged timers."
                    )
                identity = str(uuid4())
                duration = duration_seconds * 1000
                connection.execute(
                    "INSERT INTO timers VALUES (?,?,?,?,?,?,?,?,'RUNNING',NULL,NULL,?,1)",
                    (
                        identity,
                        principal.id,
                        device_id,
                        name,
                        duration,
                        duration,
                        now,
                        now + duration,
                        now,
                    ),
                )
                event_type = "timer.created"
            else:
                row = connection.execute(
                    "SELECT * FROM timers WHERE id=? AND owner=? AND device_id=?",
                    (str(timer_id), principal.id, device_id),
                ).fetchone()
                if row is None:
                    raise ServiceError("timer_not_found", "Timer is unavailable in this scope.")
                identity, status = row["id"], row["status"]
                if action == "pause" and status == "RUNNING":
                    connection.execute(
                        (
                            "UPDATE timers SET status='PAUSED',remaining_ms=?,"
                            "deadline_ms=NULL,updated_ms=?,version=version+1 WHERE id=?"
                        ),
                        (max(0, row["deadline_ms"] - now), now, identity),
                    )
                elif action == "resume" and status == "PAUSED":
                    connection.execute(
                        (
                            "UPDATE timers SET status='RUNNING',deadline_ms=?,updated_ms=?,"
                            "version=version+1 WHERE id=?"
                        ),
                        (now + row["remaining_ms"], now, identity),
                    )
                elif action == "cancel" and status in {"RUNNING", "PAUSED"}:
                    connection.execute(
                        (
                            "UPDATE timers SET status='CANCELLED',remaining_ms=0,"
                            "deadline_ms=NULL,updated_ms=?,version=version+1 WHERE id=?"
                        ),
                        (now, identity),
                    )
                elif action == "acknowledge" and status == "EXPIRED":
                    connection.execute(
                        (
                            "UPDATE timers SET status='ACKNOWLEDGED',acknowledged_ms=?,"
                            "updated_ms=?,version=version+1 WHERE id=?"
                        ),
                        (now, now, identity),
                    )
                    connection.execute(
                        "UPDATE alarms SET acknowledged_ms=? WHERE timer_id=?", (now, identity)
                    )
                elif (action, status) not in {
                    ("pause", "PAUSED"),
                    ("resume", "RUNNING"),
                    ("cancel", "CANCELLED"),
                    ("acknowledge", "ACKNOWLEDGED"),
                }:
                    raise ServiceError(
                        "invalid_transition",
                        (
                            "Timer state does not permit this operation. Expired alarms must "
                            "be acknowledged."
                        ),
                    )
                event_type = "timer.acknowledged" if action == "acknowledge" else "timer.updated"
            row = connection.execute("SELECT * FROM timers WHERE id=?", (identity,)).fetchone()
            result = {
                "status": "success",
                "data": {"timer": self._record(row, now), "operation_id": str(operation_id)},
            }
            self.events.append(
                connection, principal.id, device_id, event_type, result["data"], identity
            )
            return result

        def transition(connection):
            now = millis(self.clock())
            self._expire(connection, now)
            replayed, receipt = self.db.reserve(
                connection, principal.id, operation_id, "timer." + action, arguments
            )
            if replayed:
                return receipt, True
            try:
                result = apply(connection, now)
            except ServiceError as exc:
                result = {"status": "error", "error": {"code": exc.code, "message": exc.message}}
            self.db.complete(connection, principal.id, operation_id, result)
            return result, False

        result = await self.db.run(transition)
        self.changed.set()
        return result

    async def list(
        self,
        principal,
        device_id=None,
        timer_id=None,
        name=None,
        limit=10,
        offset=0,
        include_finished=False,
    ):
        if device_id is not None:
            self._device(principal, device_id)

        def query(connection):
            now = millis(self.clock())
            self._expire(connection, now)
            devices = sorted(principal.device_ids)
            scope = "device_id IN (" + ",".join("?" for _ in devices) + ")" if devices else "0"
            clauses, parameters = ["owner=?", scope], [principal.id, *devices]
            for key, value in (
                ("device_id", device_id),
                ("id", str(timer_id) if timer_id else None),
                ("name", name),
            ):
                if value is not None:
                    clauses.append(key + "=?")
                    parameters.append(value)
            if not include_finished and timer_id is None:
                clauses.append("status IN ('RUNNING','PAUSED','EXPIRED')")
            where = " AND ".join(clauses)
            total = connection.execute(
                "SELECT count(*) FROM timers WHERE " + where, parameters
            ).fetchone()[0]
            rows = connection.execute(
                "SELECT * FROM timers WHERE " + where + " ORDER BY created_ms,id LIMIT ? OFFSET ?",
                (*parameters, limit, offset),
            ).fetchall()
            if timer_id and not rows:
                raise ServiceError("timer_not_found", "Timer is unavailable in this scope.")
            timers = [self._record(row, now) for row in rows]
            identities = {row["id"] for row in rows}
            alarms = [
                {
                    "alarm_id": row["id"],
                    "timer_id": row["timer_id"],
                    "device_id": row["device_id"],
                    "expired_at": iso(row["created_ms"]),
                }
                for row in connection.execute(
                    (
                        "SELECT * FROM alarms WHERE owner=? AND acknowledged_ms IS NULL "
                        "ORDER BY created_ms,id"
                    ),
                    (principal.id,),
                ).fetchall()
                if row["timer_id"] in identities
            ]
            return {
                "timers": timers,
                "alarms": alarms,
                "total": total,
                "next_offset": offset + limit if offset + limit < total else None,
            }

        return await self.db.run(query)

    async def close(self):
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
