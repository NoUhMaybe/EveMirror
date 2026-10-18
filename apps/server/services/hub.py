"""Application lifecycle and scoped state, sharing the existing gateway and agent."""

import json
from datetime import datetime
from uuid import uuid5

from apps.server.redaction import secret_redactor
from apps.server.services.common import ServiceError, iso, millis, utc_now
from apps.server.services.database import Database
from apps.server.services.events import ApplicationSnapshot, EventStore
from apps.server.services.home import HomeService
from apps.server.services.search import SearchService
from apps.server.services.timers import TimerService
from apps.server.services.weather import WeatherService


class Services:
    def __init__(self, settings, gateway, clock=utc_now, transports=None):
        self.settings, self.gateway, self.clock = settings, gateway, clock
        self.redact = secret_redactor(settings)
        transports = transports or {}
        self.db = Database(
            settings.database_path, settings.database_busy_ms, settings.max_operations
        )
        self.events = EventStore(self.db, settings.event_retention, clock)
        self.timers = TimerService(self.db, self.events, settings.timers, clock)
        self.weather = WeatherService(settings.weather, clock, transports.get("weather"))
        self.home = HomeService(settings.home, self.db, transports.get("home"))
        self.search = SearchService(settings.search, transports.get("search"))
        self.started = False
        self.explicit_views = {}

    async def start(self):
        await self.db.open()
        await self.weather.start()
        await self.home.start()
        await self.search.start()
        await self.timers.start()
        self.started = True

    async def close(self):
        self.started = False
        await self.timers.close()
        await self.weather.close()
        await self.home.close()
        await self.search.close()
        await self.db.close()

    async def prepare(self):
        if self.started:
            await self.home.refresh()

    def availability(self):
        return {
            "database": self.db.available,
            "database_error": self.db.error,
            "timers": self.db.available,
            "weather": self.settings.weather.enabled,
            "weather_error": self.weather.last_error,
            "home_configured": self.home.configured,
            "home_error": self.home.error,
            "search_configured": bool(self.settings.search.url),
            "search_error": self.search.error,
            "audible_alarms": False,
        }

    def _present(self, connection, context, device_id, view=None, layout=None, transient_seconds=0):
        self.timers._expire(connection, millis(self.clock()))
        row = connection.execute(
            "SELECT view,layout FROM views WHERE owner=? AND device_id=?",
            (context.principal.id, device_id),
        ).fetchone()
        selected, arranged = (row["view"], row["layout"]) if row else ("default", "default")
        protected = (
            connection.execute(
                (
                    "SELECT 1 FROM alarms WHERE owner=? AND device_id=? AND "
                    "acknowledged_ms IS NULL LIMIT 1"
                ),
                (context.principal.id, device_id),
            ).fetchone()
            is not None
        )
        selected = "timers" if protected else (view or selected)
        arranged = layout or arranged
        connection.execute(
            (
                "INSERT INTO views VALUES (?,?,?,?) ON CONFLICT(owner,device_id) "
                "DO UPDATE SET view=excluded.view,layout=excluded.layout"
            ),
            (context.principal.id, device_id, selected, arranged),
        )
        if view:
            connection.execute(
                "DELETE FROM resources WHERE owner=? AND device_id=? AND kind='view-expiry'",
                (context.principal.id, device_id),
            )
        if transient_seconds:
            connection.execute(
                "INSERT OR REPLACE INTO resources VALUES (?,?,'view-expiry','selected',?)",
                (
                    context.principal.id,
                    device_id,
                    json.dumps({"expires_ms": millis(self.clock()) + transient_seconds * 1000}),
                ),
            )
        result = {
            "view": selected,
            "layout": arranged,
            "device_id": device_id,
            "alarm_protected": protected,
        }
        self.events.append(
            connection, context.principal.id, device_id, "dashboard.show_view", result
        )
        return result

    async def present(self, context, device_id, *, view=None, layout=None):
        if device_id not in context.principal.device_ids:
            raise ServiceError("device_not_authorized", "Select an authorized dashboard device.")
        result = await self.db.run(lambda c: self._present(c, context, device_id, view, layout))
        self.explicit_views[(context.principal.id, device_id)] = context.turn_id
        return result

    async def observe(self, call, result, context):
        if not self.started or not self.db.available:
            return
        owner, device = context.principal.id, context.device_id or ""
        summary = {
            "name": call.name,
            "status": result.status,
            "error_code": result.code,
            "replayed": result.replayed,
        }

        def publish(connection):
            event_id = uuid5(context.turn_id, owner + ":tool:" + call.id)
            self.events.append(
                connection,
                owner,
                device or None,
                "tool.execution_completed",
                summary,
                event_id=str(event_id),
            )
            connection.execute(
                "INSERT OR REPLACE INTO resources VALUES (?,?, 'tool',?,?)",
                (owner, device, str(event_id), json.dumps(summary)),
            )
            connection.execute(
                (
                    "DELETE FROM resources WHERE rowid IN (SELECT rowid FROM "
                    "resources WHERE owner=? AND device_id=? AND kind='tool' ORDER "
                    "BY rowid DESC LIMIT -1 OFFSET 20)"
                ),
                (owner, device),
            )
            if result.status != "success" or result.replayed:
                return
            kind, type, view = None, None, None
            if call.name.startswith("weather."):
                kind, type, view = (
                    "weather",
                    "weather.updated",
                    "weather_" + call.name.split(".")[1],
                )
                connection.execute(
                    "INSERT OR REPLACE INTO resources VALUES (?,?,?,'selected',?)",
                    (owner, device, kind, json.dumps(result.data)),
                )
            elif call.name.startswith(("home.", "media.")):
                kind, type = (
                    "home",
                    "media.state_changed"
                    if call.name.startswith("media.")
                    else "home.entity_changed",
                )
                view = "media" if call.name.startswith("media.") else "smart_home"
                states = (
                    result.data
                    if isinstance(result.data, list)
                    else [
                        result.data.get("state") if "acknowledged" in result.data else result.data
                    ]
                )
                for state in states:
                    if state and state.get("entity_id") in context.principal.home_entities:
                        connection.execute(
                            "INSERT OR REPLACE INTO resources VALUES (?,?,?,?,?)",
                            (owner, device, kind, state["entity_id"], json.dumps(state)),
                        )
            elif call.name.startswith("timer."):
                view = "timers"
            if type:
                self.events.append(connection, owner, device or None, type, {"updated": True})
            if view and device and self.explicit_views.get((owner, device)) != context.turn_id:
                transient = call.name.startswith(("home.", "media.")) and call.name not in {
                    "home.get_state",
                    "home.list_entities",
                    "media.get_state",
                }
                self._present(
                    connection, context, device, view, transient_seconds=12 if transient else 0
                )

        try:
            await self.db.run(publish)
        except ServiceError:
            # A presentation failure cannot rewrite a successfully persisted action as failed.
            pass

    async def presence_update(self, device, previous, current):
        """Minimal notifications in the existing scoped ledger, never raw sensor history."""
        if previous == current:
            return
        types = []
        if previous is None or (previous.confirmed, previous.reading.health) != (
            current.confirmed,
            current.reading.health,
        ):
            types.append(
                "presence.unavailable"
                if current.reading.health in {"unavailable", "timeout", "malformed"}
                else {"PRESENT": "presence.detected", "ABSENT": "presence.lost"}.get(
                    current.confirmed, "presence.unknown"
                )
            )
        if previous is None or previous.target_percent != current.target_percent:
            types.append("display.brightness_changed")
            if current.display != "unknown" and (
                previous is None or previous.display != current.display
            ):
                types.append("display." + current.display)
        try:
            for event in types:
                await self.events.publish(
                    "voice:" + device,
                    device,
                    event,
                    {
                        "presence": current.confirmed,
                        "health": current.reading.health,
                        "target_percent": current.target_percent,
                        "simulated": current.simulated,
                    },
                )
        except ServiceError:
            pass

    async def snapshot(self, principal):
        def capture(connection):
            now = millis(self.clock())
            self.timers._expire(connection, now)
            rows = connection.execute(
                (
                    "SELECT * FROM timers WHERE owner=? AND status IN ('RUNNING',"
                    "'PAUSED','EXPIRED') ORDER BY created_ms,id"
                ),
                (principal.id,),
            ).fetchall()
            timers = [
                self.timers._record(row, now)
                for row in rows
                if row["device_id"] in principal.device_ids
            ]
            alarms = [
                {
                    "alarm_id": row["id"],
                    "timer_id": row["timer_id"],
                    "device_id": row["device_id"],
                    "expired_at": iso(row["created_ms"]),
                }
                for row in connection.execute(
                    "SELECT * FROM alarms WHERE owner=? AND acknowledged_ms IS NULL",
                    (principal.id,),
                ).fetchall()
                if row["device_id"] in principal.device_ids
            ]
            views = []
            for row in connection.execute(
                "SELECT * FROM views WHERE owner=?", (principal.id,)
            ).fetchall():
                if row["device_id"] not in principal.device_ids:
                    continue
                expiry = connection.execute(
                    "SELECT payload FROM resources WHERE owner=? AND device_id=? "
                    "AND kind='view-expiry' AND id='selected'",
                    (principal.id, row["device_id"]),
                ).fetchone()
                expired = expiry and json.loads(expiry["payload"])["expires_ms"] <= now
                views.append(
                    {
                        "device_id": row["device_id"],
                        "view": "default" if expired else row["view"],
                        "layout": row["layout"],
                    }
                )
            weather, devices, tools = [], [], []
            for row in connection.execute(
                "SELECT * FROM resources WHERE owner=?", (principal.id,)
            ).fetchall():
                if row["device_id"] and row["device_id"] not in principal.device_ids:
                    continue
                payload = json.loads(row["payload"])
                if row["kind"] == "weather":
                    age = max(
                        0,
                        (
                            self.clock() - datetime.fromisoformat(payload["fetched_at"])
                        ).total_seconds(),
                    )
                    if age <= self.settings.weather.max_stale:
                        weather.append(
                            {
                                **payload,
                                "cache_age_seconds": age,
                                "source_age_seconds": max(
                                    0,
                                    (
                                        self.clock()
                                        - datetime.fromisoformat(payload["source_timestamp"])
                                    ).total_seconds(),
                                )
                                if payload.get("source_timestamp")
                                else None,
                                "stale": payload["stale"]
                                or age
                                >= payload.get(
                                    "freshness_ttl_seconds", self.settings.weather.current_ttl
                                ),
                            }
                        )
                elif (
                    row["kind"] == "home"
                    and row["id"] in principal.home_entities
                    and row["id"] in self.settings.home.entities
                ):
                    devices.append({**payload, "cached": True})
                elif row["kind"] == "tool":
                    tools.append(payload)
            for device_id, state in self.gateway.states.items():
                if device_id in principal.device_ids:
                    devices.append({"kind": "edge", **state.model_dump(mode="json")})
            revision = connection.execute(
                "SELECT coalesce(max(sequence),0) FROM events"
            ).fetchone()[0]
            return ApplicationSnapshot(
                timestamp=self.clock().isoformat(),
                revision=revision,
                timers=timers,
                alarms=alarms,
                weather=weather,
                devices=devices,
                views=views,
                tools=tools,
                availability=self.availability(),
            )

        return await self.db.run(capture)
