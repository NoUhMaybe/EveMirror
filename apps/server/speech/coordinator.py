"""Speech feeds the existing agent; scoped volatile captions never enter SQLite."""

import asyncio
import hashlib
import time
from collections import deque
from contextlib import suppress
from datetime import UTC, datetime
from uuid import UUID, uuid4, uuid5

from apps.server.agent.sessions import SessionError
from apps.server.services.common import ServiceError, millis
from apps.server.speech.delivery import Delivery
from apps.server.speech.providers import FasterWhisper, Piper
from apps.server.tools.base import Principal
from packages.audio import SpeechError
from packages.protocol import (
    SyncedTimer,
    TimerSync,
    TimerSyncPayload,
    VoiceStatus,
    VoiceStatusPayload,
)


class VoiceCoordinator:
    def __init__(
        self, settings, gateway, agent, services, stt=None, tts=None, clock=time.monotonic
    ):
        self.settings, self.gateway, self.agent, self.services = settings, gateway, agent, services
        self.config, self.clock = settings.speech, clock
        self.stt, self.tts = stt or FasterWhisper(self.config), tts or Piper(self.config)
        self.delivery = Delivery(self.config.playback_timeout)
        self.sessions, self.follow_until, self.capture_until = {}, {}, {}
        self.uploads = {}
        self.task_connections = {}
        self.events = {device: deque(maxlen=128) for device in settings.voice_devices}
        self.revision = 0
        self.edge_state, self.delivery_state, self.tasks = {}, {}, {}
        self.sync_sent = {}
        self.sync_pending = {}
        self.alarm_task = None
        self.errors = 0
        self.last_success = {}

    def principal(self, device):
        grant = self.settings.voice_devices.get(device)
        if not self.config.enabled:
            raise SpeechError("speech_unconfigured")
        if grant is None:
            raise SpeechError("voice_not_authorized")
        return Principal(
            "voice:" + device,
            frozenset({device}),
            grant.allow_mutations,
            frozenset(grant.home_entities),
            allow_voice_state=True,
        )

    def observe(self, device, kind, payload):
        if device not in self.events:
            return
        self.revision += 1
        self.events[device].append(
            {
                "version": 1,
                "event_id": str(uuid4()),
                "revision": self.revision,
                "timestamp": datetime.now(UTC).isoformat(),
                "device_id": device,
                "type": kind,
                "payload": self.services.redact(payload),
                "_expires": self.clock() + self.config.voice_event_ttl,
            }
        )

    def prune(self):
        for events in self.events.values():
            while events and events[0]["_expires"] <= self.clock():
                events.popleft()

    def snapshot(self, principal, after=0):
        self.prune()
        first = min(
            (
                event["revision"]
                for device in principal.device_ids
                for event in self.events.get(device, ())
            ),
            default=self.revision + 1,
        )
        resync = after > self.revision or (after > 0 and after < first - 1)
        if resync:
            after = 0
        events = []
        for device in principal.device_ids:
            # A voice principal sees its device; trusted scoped clients already have device grants.
            for event in self.events.get(device, ()) if principal.allow_voice_state else ():
                if event["_expires"] > self.clock() and event["revision"] > after:
                    events.append({key: value for key, value in event.items() if key != "_expires"})
        return {
            "version": 1,
            "revision": self.revision,
            "volatile": True,
            "resync_required": resync,
            "expires_after_seconds": self.config.voice_event_ttl,
            "events": sorted(events, key=lambda event: event["revision"]),
            "devices": [
                {
                    "device_id": device,
                    "connected": device in self.gateway.connections,
                    "edge": self.edge_state.get(device),
                    "last_success": self.last_success.get(device),
                }
                for device in principal.device_ids
                if device in self.events
            ],
        }

    def status(self):
        return {
            "enabled": self.config.enabled,
            "active": len(self.tasks),
            "errors": self.errors,
            "last_reported_edges": self.edge_state,
            "stt": self.stt.status() if hasattr(self.stt, "status") else {"injected": True},
            "tts": self.tts.status() if hasattr(self.tts, "status") else {"injected": True},
        }

    async def start(self):
        if self.config.enabled:
            if self.services.db.available:
                with suppress(ServiceError):
                    await self.services.db.run(
                        lambda c: c.execute(
                            "UPDATE alarm_delivery SET status='indeterminate',updated_at=? "
                            "WHERE status='started'",
                            (datetime.now(UTC).isoformat(),),
                        )
                    )
            self.alarm_task = asyncio.create_task(self._alarm_loop())
            if self.config.warmup:

                async def warm(engine, duration):
                    if hasattr(engine, "load"):
                        try:
                            await engine.worker.run(lambda _: engine.load(engine._load), duration)
                        except Exception:
                            self.errors += 1

                await asyncio.gather(
                    warm(self.stt, self.config.stt_timeout), warm(self.tts, self.config.tts_timeout)
                )

    async def process(self, audio, connection):
        device = audio.device_id
        started = self.clock()
        session = None
        text_ready = False
        unverified = [False]

        async def state(phase, **data):
            payload = VoiceStatusPayload(state=phase, **self.services.redact(data))
            self.observe(
                device,
                "assistant." + phase.lower(),
                {
                    "session_id": str(audio.session_id),
                    "request_id": str(audio.request_id),
                    **payload.model_dump(mode="json"),
                },
            )
            await connection.send(
                VoiceStatus(
                    device_id=device,
                    session_id=audio.session_id,
                    request_id=audio.request_id,
                    payload=payload,
                )
            )

        try:
            principal = self.principal(device)
            if device in self.tasks:
                raise SpeechError("voice_busy")
            if "playback" not in connection.capabilities:
                raise SpeechError("playback_unavailable")
            self.tasks[device] = asyncio.current_task()
            self.task_connections[device] = connection
            self.uploads[device] = (audio.session_id, audio.request_id)
            sid = self.sessions.get(device)
            valid = self.clock() < max(
                self.follow_until.get(device, 0), self.capture_until.get(device, 0)
            )
            if sid and valid:
                try:
                    session = self.agent.sessions.get(sid, principal)
                except SessionError:
                    session = None
            if session is None:
                session = self.agent.sessions.create(principal, device)
                self.sessions[device] = session.id
            session.keep_until = (
                self.agent.sessions.clock()
                + self.config.stt_timeout
                + self.settings.agent.turn_timeout
                + self.config.tts_timeout
                + 100
            )
            await state("TRANSCRIBING", conversation_id=session.id)
            transcript = await self.stt.transcribe(audio)
            if (
                transcript.session_id != audio.session_id
                or transcript.request_id != audio.request_id
            ):
                raise SpeechError("transcription_identity_mismatch")
            text = self.services.redact(transcript.text.strip())
            if not text or len(text.encode("utf-8")) > 16000 or len(text) > 8192:
                raise SpeechError("empty_or_invalid_transcript")
            text_ready = True
            await state(
                "THINKING",
                conversation_id=session.id,
                transcript=text[:4000],
                language=transcript.language,
                stt_model=transcript.model,
                metrics={
                    "stt_ms": float(transcript.latency_ms),
                    "capture_seconds": float(transcript.duration),
                },
            )

            async def phase(name, details):
                unverified[0] = unverified[0] or details.get("unverified", False)
                await state(
                    name,
                    conversation_id=session.id,
                    tool=details.get("tool"),
                    tool_status=details.get("status"),
                    metrics={"tool_ms": float(details["latency_ms"])}
                    if "latency_ms" in details
                    else {},
                )

            result = await self.agent.turn(
                principal, text, audio.request_id, session.id, device, on_phase=phase
            )
            if asyncio.current_task().cancelling():
                raise asyncio.CancelledError
            if result["status"] != "complete" or not result["response"]:
                raise SpeechError((result.get("error") or {}).get("code", "agent_failed"))
            response = result["response"]
            if any(tool["status"] != "success" for tool in result["tools"]):
                response = (
                    "One or more actions failed or have an unknown outcome. "
                    "Please check their state before trying again."
                )
            elif unverified[0]:
                response = (
                    "The approved command was acknowledged, but I haven't confirmed "
                    "the device's state. Please check it before trying again."
                )
            if len(response) > self.config.max_text:
                raise SpeechError("response_too_long")
            await state(
                "SYNTHESIZING",
                conversation_id=session.id,
                response=response,
                metrics={"agent_ms": float(result["latency_ms"])},
            )
            synthesis_started = self.clock()
            speech = await self.tts.synthesize(response)
            await state(
                "DELIVERING",
                conversation_id=session.id,
                metrics={
                    "tts_ms": (self.clock() - synthesis_started) * 1000,
                    "duration_seconds": speech.duration,
                    "sample_rate": float(speech.sample_rate),
                    "sample_count": float(speech.sample_count),
                },
            )
            playback_metrics = await self.delivery.play(connection, speech, audio.session_id)
            self.last_success[device] = datetime.now(UTC).isoformat()
            self.follow_until[device] = self.clock() + self.config.follow_up_seconds
            session.touched = self.agent.sessions.clock()
            session.keep_until = session.touched + self.config.follow_up_seconds
            await state(
                "FOLLOW_UP",
                conversation_id=session.id,
                follow_up_seconds=float(self.config.follow_up_seconds),
                metrics={"end_to_end_ms": (self.clock() - started) * 1000, **playback_metrics},
            )
        except asyncio.CancelledError:
            self.follow_until.pop(device, None)
            raise
        except Exception as exc:
            self.follow_until.pop(device, None)
            self.errors += 1
            code = exc.code if isinstance(exc, SpeechError | SessionError) else "voice_failed"
            if text_ready and code.startswith(("provider_", "agent_", "session_", "turn_")):
                failure = (
                    "The assistant model is not configured."
                    if code == "provider_not_configured"
                    else "The assistant couldn't finish that request. Please ask a new question."
                )
                try:
                    await state("SYNTHESIZING", response=failure, error=code)
                    error_audio = await self.tts.synthesize(failure)
                    await state("DELIVERING", error=code)
                    await self.delivery.play(connection, error_audio, audio.session_id)
                except Exception:
                    pass
            try:
                await state(
                    "ERROR",
                    error=code,
                    response=(
                        "Voice processing could not finish. "
                        "Any interrupted action may have an unknown outcome."
                    ),
                )
            except Exception:
                pass
        finally:
            if session and device not in self.follow_until:
                session.keep_until = 0
            if self.tasks.get(device) is asyncio.current_task():
                self.tasks.pop(device, None)
                self.task_connections.pop(device, None)
                self.uploads.pop(device, None)

    async def edge_update(self, device, event):
        updated = self.services.redact(event.payload.model_dump(mode="json"))
        if updated != self.edge_state.get(device):
            self.edge_state[device] = updated
            self.observe(
                device,
                "assistant.edge_state",
                {"session_id": str(event.session_id) if event.session_id else None, **updated},
            )
        if event.payload.state == "LISTENING" and self.clock() < self.follow_until.get(device, 0):
            self.capture_until[device] = self.clock() + 30
            sid = self.sessions.get(device)
            if sid:
                try:
                    session = self.agent.sessions.get(sid, self.principal(device))
                    session.keep_until = self.agent.sessions.clock() + self.config.stt_timeout + 30
                except SessionError:
                    pass

    async def playback_update(self, connection, event):
        device = connection.state.device_id
        self.principal(device)
        accepted = self.delivery.receive(connection, event)
        if event.payload.alarm_id:
            if event.request_id != event.payload.alarm_id:
                return

            def matches(c):
                return (
                    c.execute(
                        "SELECT 1 FROM alarms WHERE id=? AND device_id=?",
                        (str(event.payload.alarm_id), device),
                    ).fetchone()
                    is not None
                )

            if not self.services.db.available or not await self.services.db.run(matches):
                return
            if event.payload.status in {
                "started",
                "completed",
                "cancelled",
                "failed",
                "indeterminate",
            }:
                await self._record_alarm(str(event.payload.alarm_id), device, event.payload.status)
            accepted = True
        if accepted and event.payload.status == "started" and event.payload.alarm_id is None:
            payload = VoiceStatusPayload(state="SPEAKING")
            self.observe(
                device,
                "assistant.speaking",
                {
                    "session_id": str(event.session_id),
                    "request_id": str(event.request_id),
                    **payload.model_dump(mode="json"),
                },
            )
            await connection.send(
                VoiceStatus(
                    device_id=device,
                    session_id=event.session_id,
                    request_id=event.request_id,
                    payload=payload,
                )
            )
        if accepted and event.payload.status not in {"accepted", "buffered"}:
            self.observe(
                device,
                "assistant.playback",
                {
                    "request_id": str(event.request_id),
                    "session_id": str(event.session_id),
                    **event.payload.model_dump(mode="json"),
                },
            )

    async def dismiss(self, device, event):
        self.principal(device)

        def owned(c):
            return c.execute(
                "SELECT timer_id,owner FROM alarms WHERE id=? AND device_id=?",
                (str(event.payload), device),
            ).fetchone()

        row = await self.services.db.run(owned)
        if row:
            principal = Principal(row["owner"], frozenset({device}), True)
            await self.services.timers.mutate(
                principal,
                device,
                uuid5(event.payload, "edge-dismiss"),
                "acknowledge",
                timer_id=row["timer_id"],
            )

    async def sync_device(self, device, connection):
        if not self.services.db.available or "timer_sync" not in connection.capabilities:
            return

        def capture(c):
            self.services.timers._expire(c, millis(self.services.clock()))
            return [
                SyncedTimer(
                    timer_id=UUID(row["id"]),
                    alarm_id=uuid5(UUID(row["id"]), "alarm"),
                    status=row["status"],
                    deadline=datetime.fromtimestamp(row["deadline_ms"] / 1000, UTC)
                    if row["deadline_ms"] is not None
                    else None,
                    version=row["version"],
                )
                for row in c.execute(
                    "SELECT * FROM timers WHERE device_id=? "
                    "AND status IN ('RUNNING','PAUSED','EXPIRED') ORDER BY id LIMIT 1025",
                    (device,),
                ).fetchall()
            ]

        rows = await self.services.db.run(capture)
        if len(rows) > 1024:
            raise SpeechError("timer_sync_capacity")
        fingerprint = hashlib.sha256(
            "".join(row.model_dump_json() for row in rows).encode()
        ).hexdigest()
        previous = self.sync_pending.get(device)
        if (
            self.sync_sent.get(device) == (connection, fingerprint)
            and previous
            and (
                (previous["stored"] and self.clock() - previous["sent_at"] < 30)
                or self.clock() - previous["sent_at"] < 2
            )
        ):
            return
        generation = uuid4()
        self.sync_pending[device] = {
            "connection": connection,
            "generation": generation,
            "stored": False,
            "sent_at": self.clock(),
            "alarm_ids": [str(row.alarm_id) for row in rows if row.status == "EXPIRED"],
        }
        pages = max(1, (len(rows) + 15) // 16)
        for page in range(pages):
            await connection.send(
                TimerSync(
                    device_id=device,
                    payload=TimerSyncPayload(
                        generation=generation,
                        sequence=page,
                        final=page == pages - 1,
                        timers=tuple(rows[page * 16 : page * 16 + 16]),
                    ),
                )
            )
        self.sync_sent[device] = (connection, fingerprint)

    async def _record_alarm(self, alarm_id, device, status):
        def record(c):
            old = c.execute(
                "SELECT status FROM alarm_delivery WHERE alarm_id=?", (alarm_id,)
            ).fetchone()
            if old and (old["status"] == status or status == "delivered"):
                return
            row = c.execute(
                "SELECT owner FROM alarms WHERE id=? AND device_id=?", (alarm_id, device)
            ).fetchone()
            if row is None:
                return
            c.execute(
                "INSERT INTO alarm_delivery VALUES (?,?,?,?) ON CONFLICT(alarm_id) "
                "DO UPDATE SET status=excluded.status,updated_at=excluded.updated_at",
                (alarm_id, device, status, datetime.now(UTC).isoformat()),
            )

        await self.services.db.run(record)

    async def alarm_snapshot(self, principal):
        if not self.services.db.available:
            return {"available": False, "alarms": []}

        owners = [principal.id]
        if principal.allow_voice_state:
            owners += [
                "voice:" + device
                for device in principal.device_ids
                if device in self.settings.voice_devices
            ]

        def read(c):
            return [
                dict(row)
                for row in c.execute(
                    "SELECT alarms.id AS alarm_id,alarms.device_id,"
                    "coalesce(alarm_delivery.status,'pending') AS delivery_status,"
                    "alarm_delivery.updated_at,alarms.acknowledged_ms IS NULL AS pending "
                    "FROM alarms LEFT JOIN alarm_delivery ON alarm_delivery.alarm_id=alarms.id "
                    "WHERE alarms.owner IN (" + ",".join("?" for _ in owners) + ") "
                    "AND alarms.acknowledged_ms IS NULL",
                    owners,
                ).fetchall()
                if row["device_id"] in principal.device_ids
            ]

        return {"available": True, "alarms": await self.services.db.run(read)}

    async def device_application(self, principal, device):
        if not principal.allow_voice_state or device not in principal.device_ids:
            raise SpeechError("voice_state_not_authorized")
        if not self.config.enabled or not self.services.db.available:
            return None
        return await self.services.snapshot(self.principal(device))

    async def sync_received(self, connection, event):
        device = connection.state.device_id
        self.principal(device)
        pending = self.sync_pending.get(device)
        if (
            not pending
            or pending["connection"] is not connection
            or pending["generation"] != event.payload.generation
        ):
            return
        pending["stored"] = True
        for alarm_id in pending["alarm_ids"]:
            await self._record_alarm(alarm_id, device, "delivered")

    async def _alarm_loop(self):
        while True:
            self.prune()
            for device in self.settings.voice_devices:
                connection = self.gateway.connections.get(device)
                if connection:
                    try:
                        await self.sync_device(device, connection)
                    except Exception:
                        self.errors += 1
            await asyncio.sleep(self.config.alarm_poll_seconds)

    async def cancel(self, device, connection=None):
        if connection is not None and self.task_connections.get(device) is not connection:
            return
        task = self.tasks.get(device)
        if task and task is not asyncio.current_task():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def disconnected(self, connection):
        device = connection.state.device_id
        self.delivery.disconnected(connection)
        if not self.config.enabled:
            return
        await self.cancel(device, connection)
        current = self.gateway.connections.get(device)
        if current is not None and current is not connection:
            return
        self.sync_sent.pop(device, None)
        self.sync_pending.pop(device, None)
        self.follow_until.pop(device, None)
        self.capture_until.pop(device, None)
        if self.services.db.available:
            with suppress(ServiceError):
                await self.services.db.run(
                    lambda c: c.execute(
                        "UPDATE alarm_delivery SET status='indeterminate',updated_at=? "
                        "WHERE device_id=? AND status='started'",
                        (datetime.now(UTC).isoformat(), device),
                    )
                )

    async def close(self):
        if self.alarm_task:
            self.alarm_task.cancel()
            await asyncio.gather(self.alarm_task, return_exceptions=True)
        for device in list(self.tasks):
            await self.cancel(device)
        await asyncio.gather(self.stt.close(), self.tts.close())
