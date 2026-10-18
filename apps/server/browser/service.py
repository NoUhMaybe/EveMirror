"""Adapt browser scopes to the existing state stores and tool executor."""

import asyncio
import time
from uuid import UUID, uuid4, uuid5

from fastapi import HTTPException

from apps.server.agent.messages import ToolCall
from apps.server.browser.models import BrowserFrame
from apps.server.browser.sessions import BrowserSessions
from apps.server.gateway import GatewayError
from apps.server.services.common import ServiceError
from apps.server.speech.state import VoiceSnapshot
from apps.server.tools.base import Principal, ToolContext
from apps.server.tools.executor import ExecutionLedger
from packages.protocol import Cancel, SetDisplayPolicy, VoiceControl, VoiceControlPayload


class BrowserService:
    def __init__(self, settings, services, gateway, voice, agent):
        self.settings, self.hub, self.gateway, self.voice, self.agent = (
            settings,
            services,
            gateway,
            voice,
            agent,
        )
        self.config = settings.browser
        self.sessions = BrowserSessions(self.config, services.db, services.clock)
        self.epoch = uuid4()
        self.refresh_tasks, self.refreshed, self.weather, self.home = {}, {}, {}, {}
        self.controls, self.action_locks = {}, {}

    def principal(self, row, mutate=False):
        device = row["device_id"]
        grant = self.config.devices[device]
        return Principal(
            "voice:" + device,
            frozenset({device}),
            mutate,
            frozenset(grant.home_entities),
            allow_voice_state=True,
        )

    def refresh(self, row):
        device = row["device_id"]
        if (
            device in self.refresh_tasks
            or time.monotonic() - self.refreshed.get(device, float("-inf")) < 10
        ):
            return
        self.refreshed[device] = time.monotonic()

        async def fetch():
            try:
                if self.settings.weather.enabled:
                    try:
                        # All modes share WeatherService's one location/unit cache.
                        # Weekly deliberately omits hours in its public tool result.
                        await self.hub.weather.get("current")
                        forecast = await self.hub.weather.get("weekly")
                        daily = await self.hub.weather.get("daily")
                        self.weather[device] = {
                            **forecast,
                            "hourly": daily["hourly"],
                            "freshness_ttl_seconds": self.settings.weather.current_ttl,
                        }
                    except ServiceError:
                        pass
                if self.hub.home.configured:
                    try:
                        self.home[device] = await self.hub.home.list(self.principal(row))
                    except ServiceError:
                        self.home[device] = []
            finally:
                self.refresh_tasks.pop(device, None)

        self.refresh_tasks[device] = asyncio.create_task(fetch())

    async def frame(self, row, token, after, voice_after, epoch):
        principal = self.principal(row)
        reset = str(self.epoch) != epoch or after is None
        page = None
        if not reset:
            try:
                page = await self.hub.events.read(principal, after, limit=200)
            except ServiceError as exc:
                if exc.code != "snapshot_required":
                    raise
                reset = True
        # A complete snapshot follows the event read. Events are notifications;
        # they never patch/revert this newer authoritative database projection.
        application = await self.hub.snapshot(principal)
        application.availability["mutations_enabled"] = self.settings.agent.allow_mutations
        connection = self.gateway.connections.get(row["device_id"])
        application.availability["voice_control"] = bool(
            connection and "voice_control" in connection.capabilities
        )
        if reset:
            page = {"version": 1, "cursor": application.revision, "events": []}
        voice = self.voice.snapshot(principal, 0 if reset else voice_after)
        if not voice["devices"]:
            voice["devices"] = [
                {"device_id": row["device_id"], "connected": connection is not None}
            ]
        grant = self.config.devices[row["device_id"]]
        if not grant.captions:
            for event in voice["events"]:
                event["payload"] = {
                    k: v for k, v in event["payload"].items() if k not in {"transcript", "response"}
                }
        voice["alarm_delivery"] = await self.voice.alarm_snapshot(principal)
        self.refresh(row)
        weather = self.weather.get(row["device_id"])
        if weather:
            from datetime import datetime

            age = max(
                0,
                (self.hub.clock() - datetime.fromisoformat(weather["fetched_at"])).total_seconds(),
            )
            weather = {
                **weather,
                "cache_age_seconds": age,
                "stale": weather["stale"] or age >= weather["freshness_ttl_seconds"],
            }
            if age > self.settings.weather.max_stale:
                weather = None
        model = getattr(self.settings, self.settings.llm_provider + "_model")
        return self.hub.redact(
            BrowserFrame(
                presence=connection.state.presence if connection else None,
                epoch=self.epoch,
                reset=reset,
                server_time=self.hub.clock().isoformat(),
                session=self.sessions.public(row, token),
                application=application,
                events=page,
                voice=VoiceSnapshot.model_validate(voice),
                ambient_weather=weather,
                home=[
                    {
                        **item,
                        "remote_commands": sorted(
                            self.settings.home.entities[item["entity_id"]].remote_commands
                        ),
                        "power_on": self.hub.home.supported(item["entity_id"], "power", True),
                        "power_off": self.hub.home.supported(item["entity_id"], "power", False),
                    }
                    for item in self.home.get(row["device_id"], [])
                    if item["entity_id"] in grant.home_entities
                ],
                provider=self.settings.llm_provider,
                model=model,
            ).model_dump(mode="json")
        )

    async def action(self, row, action):
        device, name = row["device_id"], action.name
        grant = self.config.devices[device]
        mutates = name.startswith(("timer.", "home.", "media.", "dashboard."))
        if name.startswith("timer.") and not grant.timers:
            raise HTTPException(403, "browser_timer_permission_required")
        home_mutation = name.startswith(("home.", "media.")) and name not in {
            "home.get_state",
            "home.list_entities",
            "media.get_state",
        }
        if home_mutation and not grant.home_control:
            raise HTTPException(403, "browser_home_permission_required")
        if set(action.arguments) & {"device_id", "operation_id"}:
            raise HTTPException(422, "browser_scope_override_forbidden")
        arguments = dict(action.arguments)
        if home_mutation or name.startswith(("timer.", "dashboard.")):
            arguments["device_id"] = device
        principal = self.principal(row, mutates)
        identity = uuid5(UUID(row["id"]), str(action.request_id))
        context = ToolContext(principal, UUID(row["id"]), identity, device)
        call = ToolCall("browser", name, arguments)
        if name.startswith("dashboard."):
            # Browser presentation changes are separate from LLM action permissions.
            # Reuse the finite tool schema and existing semantic service, never an
            # arbitrary executor or a hardware/home mutation permission override.
            try:
                arguments = self.agent.registry.validate(self.agent.registry.tools[name], arguments)
            except Exception:
                raise HTTPException(422, "invalid_view") from None
            data = await self.hub.present(
                context,
                device,
                view="default" if name == "dashboard.dismiss_view" else arguments.get("view"),
                layout=arguments.get("layout"),
            )
            return {"status": "success", "data": data}
        lock = self.action_locks.setdefault(device, asyncio.Lock())
        if lock.locked():
            raise HTTPException(409, "browser_action_busy")
        async with lock:
            result = await self.agent.executor.execute(call, context, ExecutionLedger())
            await self.hub.observe(call, result, context)
            if home_mutation:
                # Read evidence after the existing service invalidates its cache.
                # An acknowledged command never becomes optimistic physical state.
                try:
                    self.home[device] = await self.hub.home.list(principal)
                except ServiceError:
                    self.home[device] = []
        return self.hub.redact(result.payload())

    async def display(self, row, body):
        device = row["device_id"]
        if (
            not self.config.devices[device].display_control
            or not self.settings.agent.allow_mutations
        ):
            raise HTTPException(403, "browser_display_permission_required")
        try:
            ack = await self.gateway.command(
                device,
                uuid5(UUID(row["id"]), str(body.request_id)),
                SetDisplayPolicy(
                    action="set_display_policy",
                    settings=body.settings,
                    override_percent=body.override_percent,
                    release_override=body.release_override,
                ),
            )
        except GatewayError as exc:
            raise HTTPException(exc.status_code, exc.code) from None
        return {
            "status": ack.payload.status,
            "code": ack.payload.code,
            "hardware": ack.payload.hardware.model_dump(mode="json"),
            "replayed": ack.payload.replayed,
        }

    async def mute(self, row, muted):
        device = row["device_id"]
        if not self.config.devices[device].voice_control:
            raise HTTPException(403, "browser_voice_permission_required")
        connection = self.gateway.connections.get(device)
        if connection is None or "voice_control" not in connection.capabilities:
            raise HTTPException(503, "edge_voice_unavailable")
        if device in self.controls:
            raise HTTPException(409, "voice_control_busy")
        request_id = uuid4()
        future = asyncio.get_running_loop().create_future()
        self.controls[device] = (connection, request_id, future, muted)
        try:
            await connection.send(
                VoiceControl(
                    device_id=device,
                    request_id=request_id,
                    payload=VoiceControlPayload(muted=muted),
                )
            )
            async with asyncio.timeout(5):
                result = await future
            if result.status != "completed" or result.muted != muted:
                raise HTTPException(503, "mute_not_confirmed")
            return {"status": "completed", "muted": result.muted}
        except (OSError, RuntimeError, TimeoutError):
            raise HTTPException(503, "mute_outcome_unknown") from None
        finally:
            self.controls.pop(device, None)
            if not future.done():
                future.cancel()

    def acknowledge(self, connection, event):
        pending = self.controls.get(event.device_id)
        if (
            pending
            and pending[0] is connection
            and pending[1] == event.request_id
            and not pending[2].done()
        ):
            pending[2].set_result(event.payload)

    async def cancel(self, row):
        device = row["device_id"]
        if not self.config.devices[device].voice_control:
            raise HTTPException(403, "browser_voice_permission_required")
        upload, connection = self.voice.uploads.get(device), self.gateway.connections.get(device)
        session_id = (
            upload[0]
            if upload
            else next(
                (
                    event["payload"].get("session_id")
                    for event in reversed(self.voice.events.get(device, ()))
                    if event["payload"].get("session_id")
                ),
                None,
            )
        )
        try:
            if session_id and connection:
                await connection.send(
                    Cancel(
                        device_id=device,
                        session_id=UUID(str(session_id)),
                        request_id=upload[1] if upload else uuid4(),
                    )
                )
        finally:
            await self.voice.cancel(device)
            self.voice.follow_until.pop(device, None)
            self.voice.capture_until.pop(device, None)
        return {"status": "cancel_requested" if session_id and connection else "idle"}

    async def close(self):
        tasks = list(self.refresh_tasks.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
