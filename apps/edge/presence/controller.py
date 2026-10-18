"""One local arbiter, using the existing command journal and sole Feather owner."""

import asyncio
import json
import time
from datetime import timedelta

from apps.edge.presence.policy import PresenceMachine
from apps.edge.presence.sensors import SimulatedSensor, UnavailableSensor
from packages.presence import PresenceOptions, PresenceReading, PresenceStatus
from packages.protocol import DeviceCommand, SetBrightness, utc_now


class DisplayController:
    def __init__(self, settings, commands, *, sensor=None, clock=time.monotonic, wall=utc_now):
        self.edge, self.commands, self.clock, self.wall = settings, commands, clock, wall
        self.hardware = commands.hardware
        self.sensor = sensor or (
            SimulatedSensor() if settings.presence_driver == "simulated" else UnavailableSensor()
        )
        self.machine = PresenceMachine(settings.presence, clock())
        self.lock = asyncio.Lock()
        self.wake = asyncio.Event()
        self.latest_reading = PresenceReading()
        self.updates = asyncio.Queue(maxsize=1)
        self.last_status = None
        self.uncertain = False
        self.managed = settings.presence.enabled or settings.presence.night.enabled
        saved = commands.preference("display")
        if saved:
            record = json.loads(saved)
            self.machine.settings = PresenceOptions.model_validate_json(
                json.dumps(record["settings"])
            )
            self.uncertain = record["uncertain"]
            remaining = max(0, record["manual_expires"] - wall().timestamp())
            if record["manual"] is not None and remaining:
                self.machine.manual = record["manual"]
                self.machine.manual_until = clock() + min(
                    remaining, self.machine.settings.manual_override_seconds
                )
            self.managed = (
                self.machine.settings.enabled
                or self.machine.settings.night.enabled
                or self.machine.manual is not None
            )
        self.reason = "default"
        self._report()

    def _save(self):
        self.commands.save_preference(
            "display",
            json.dumps(
                {
                    "settings": self.machine.settings.model_dump(mode="json"),
                    "manual": self.machine.manual,
                    "manual_expires": self.wall().timestamp()
                    + max(0, self.machine.manual_until - self.clock()),
                    "uncertain": self.uncertain,
                }
            ),
        )

    @property
    def status(self):
        m = self.machine
        return PresenceStatus(
            settings=m.settings,
            reading=m.reading if m.settings.enabled else PresenceReading(health="disabled"),
            confirmed=m.confirmed if m.settings.enabled else "UNKNOWN",
            driver=self.edge.presence_driver,
            simulated=isinstance(self.sensor, SimulatedSensor),
            target_percent=m.target,
            acknowledged_percent=self.hardware.status.target_percent,
            display="unknown" if m.target is None else "asleep" if m.target == 0 else "awake",
            reason=self.reason,
            override_active=m.manual is not None and self.clock() < m.manual_until,
            activity_protected=bool(m.activity) or self.clock() < m.grace_until,
            uncertain=self.uncertain,
        )

    def _report(self):
        status = self.status
        if status != self.last_status:
            self.last_status = status
            if self.updates.full():
                self.updates.get_nowait()
            self.updates.put_nowait(status)

    def _prepare_target(self, percent):
        self.machine.selected(percent, self.clock())
        # Atomically commit intent/uncertainty with the command reservation.
        self.uncertain = True
        self._save()

    async def _apply_target(self, percent):
        if not (self.hardware.status.connected and self.hardware.status.target_percent == percent):
            await self.hardware.set_brightness(percent)

    def _completed(self, ack):
        # This preference and the ACK commit together; a crash cannot separate them.
        self.uncertain = ack.payload.status == "error"
        self._save()

    def _manual(self, payload):
        m, now = self.machine, self.clock()
        if payload.action == "set_display_policy":
            if payload.settings is not None:
                m.settings = payload.settings
                # Reconfirm with the new debounce settings; never inherit an old absence.
                m.observe(PresenceReading(), now)
                m.awake_since = now
            if payload.release_override:
                m.manual = None
            if payload.override_percent is not None:
                m.override(payload.override_percent, now)
        else:
            percent = (
                payload.percent
                if payload.action == "set_brightness"
                else 0
                if payload.mode == "sleep"
                else m.settings.preferred_percent
            )
            if payload.action == "set_brightness" and percent > 0:
                m.settings = m.settings.model_copy(update={"preferred_percent": percent})
            m.override(percent, now)
        self.managed = True
        percent, self.reason = m.choose(now, self.wall())
        self._prepare_target(percent)

    async def execute(self, command):
        async with self.lock:
            try:
                return await self.commands.execute(
                    command,
                    prepare=self._manual,
                    apply=lambda _: self._apply_target(self.machine.target),
                    complete=self._completed,
                )
            except BaseException:
                if command.payload.action != "get_status":
                    self.uncertain = True
                raise
            finally:
                self._report()

    async def tick(self, reading=None):
        async with self.lock:
            m, now = self.machine, self.clock()
            if reading is not None:
                m.observe(reading, now)
            if self.managed and not self.uncertain:
                percent, self.reason = m.choose(now, self.wall())
                if percent != m.target or (
                    not self.hardware.status.connected
                    and self.hardware.status.target_percent is None
                ):
                    stamp = self.wall()
                    command = DeviceCommand(
                        device_id=self.edge.device_id,
                        timestamp=stamp,
                        expires_at=stamp + timedelta(seconds=5),
                        payload=SetBrightness(action="set_brightness", percent=percent),
                    )
                    # Local policy writes use exactly the same durable replay journal.
                    try:
                        await self.commands.execute(
                            command,
                            prepare=lambda _: self._prepare_target(percent),
                            apply=lambda _: self._apply_target(percent),
                            complete=self._completed,
                        )
                    except BaseException:
                        self.uncertain = True
                        self._report()
                        raise
            self._report()

    async def activity(self, name, active):
        # No await/serial lock here: capture and playback must never wait for a
        # slow hardware ACK. All callers run on the owning event loop.
        self.machine.protect(name, active, self.clock())
        self.wake.set()
        self._report()

    async def _sense(self):
        initialized = False
        reconnect_at = 0
        try:
            while True:
                reading = PresenceReading(health="disabled")
                if self.machine.settings.enabled and self.clock() >= reconnect_at:
                    try:
                        async with asyncio.timeout(self.edge.presence_read_timeout):
                            if not initialized:
                                await self.sensor.initialize()
                                initialized = True
                            reading = await self.sensor.read()
                            if not isinstance(reading, PresenceReading):
                                raise ValueError("Malformed sensor reading")
                    except Exception as exc:
                        reading = PresenceReading(
                            health="timeout"
                            if isinstance(exc, TimeoutError)
                            else "malformed"
                            if isinstance(exc, ValueError)
                            else "unavailable"
                        )
                    if reading.health in {"timeout", "malformed", "unavailable"}:
                        try:
                            async with asyncio.timeout(self.edge.presence_read_timeout):
                                await self.sensor.close()
                        except Exception:
                            pass
                        initialized = False
                        reconnect_at = self.clock() + self.edge.presence_reconnect_interval
                elif self.machine.settings.enabled:
                    reading = PresenceReading()
                elif initialized:
                    await self.sensor.close()
                    initialized = False
                self.latest_reading = reading
                self.wake.set()
                await asyncio.sleep(self.edge.presence_poll_interval)
        finally:
            await self.sensor.close()

    async def run(self):
        sensor_task = asyncio.create_task(self._sense())
        try:
            while True:
                self.wake.clear()
                await self.tick(self.latest_reading)
                try:
                    await asyncio.wait_for(self.wake.wait(), self.edge.presence_poll_interval)
                except TimeoutError:
                    pass
                if sensor_task.done():
                    sensor_task.result()
        finally:
            sensor_task.cancel()
            await asyncio.gather(sensor_task, return_exceptions=True)
