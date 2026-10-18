"""Bounded receive assembly and one priority-controlled speaker owner."""

import asyncio
import base64
import threading
import time
from datetime import UTC, datetime

from packages.audio import SpeechAudio, SpeechError
from packages.protocol import MAX_FRAME_BYTES, PlaybackStatus, PlaybackStatusPayload


class PlaybackManager:
    def __init__(self, driver, send, device_id, store=None, activity=None):
        self.driver, self.send, self.device_id, self.store = driver, send, device_id, store
        self.activity = activity
        self.lock = asyncio.Lock()
        self.task, self.stop = None, None
        self.priority = 0
        self.active_alarm = None
        self.active_request = self.active_session = None

    @property
    def busy(self):
        return self.task is not None and not self.task.done()

    async def play(self, audio, request_id, session_id, *, alarm_id=None, chime=False):
        priority = 3 if alarm_id else 2 if chime else 1
        async with self.lock:
            if alarm_id and self.store:
                previous = await asyncio.to_thread(self.store.receipt, alarm_id)
                if previous is not None:
                    return previous
            if self.busy:
                if priority <= self.priority:
                    raise SpeechError("playback_busy")
                self.stop.set()
                await asyncio.shield(self.task)
            if alarm_id and self.store:
                previous = await asyncio.to_thread(self.store.reserve, alarm_id)
                if previous is not None:
                    return previous
            self.priority, self.active_alarm = priority, alarm_id
            self.active_request, self.active_session = request_id, session_id
            self.stop = threading.Event()
            self.task = asyncio.create_task(
                self._play(audio, request_id, session_id, alarm_id, chime, self.stop)
            )
            task = self.task
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            if task is self.task:
                self.stop.set()
            await asyncio.shield(task)
            raise

    async def _play(self, audio, request_id, session_id, alarm_id, chime, stop):
        loop = asyncio.get_running_loop()
        changed = asyncio.Event()
        observed = {"started": False, "samples": 0, "started_at": None}

        def started():
            if alarm_id and self.store:
                self.store.mark(alarm_id, "started")
            observed["started_at"] = datetime.now(UTC)
            observed["started"] = True
            loop.call_soon_threadsafe(changed.set)

        def progress(samples):
            observed["samples"] = samples
            loop.call_soon_threadsafe(changed.set)

        async def status(value):
            if not chime:
                event = PlaybackStatus(
                    device_id=self.device_id,
                    request_id=request_id,
                    session_id=session_id,
                    payload=PlaybackStatusPayload(
                        status=value,
                        alarm_id=alarm_id,
                        position_samples=observed["samples"],
                        started_at=observed["started_at"],
                    ),
                )
                try:
                    await self.send(event)
                except Exception:
                    if alarm_id is None:
                        raise
                    # Local alarms outlive a failed socket write. The durable receipt
                    # reconciles on reconnect without interrupting or replaying sound.

        if self.activity:
            await self.activity(True, alarm_id)
        worker = asyncio.create_task(
            asyncio.to_thread(self.driver.play, audio, stop, started, progress)
        )
        notified = False
        outcome = "failed"
        try:
            while not worker.done():
                try:
                    await asyncio.wait_for(changed.wait(), 0.2)
                except TimeoutError:
                    pass
                changed.clear()
                if observed["started"]:
                    await status("progress" if notified else "started")
                    notified = True
            await worker
            if not stop.is_set() and (
                not observed["started"] or observed["samples"] != audio.sample_count
            ):
                raise SpeechError("incomplete_output")
            if observed["started"] and not notified:
                await status("started")
            outcome = "cancelled" if stop.is_set() else "completed"
            await status(outcome)
            return outcome
        except asyncio.CancelledError:
            stop.set()
            await asyncio.shield(worker)
            outcome = "cancelled"
            raise
        except Exception:
            stop.set()
            try:
                await asyncio.shield(worker)
            except Exception:
                pass
            try:
                await status("failed")
            except Exception:
                pass
            return "failed"
        finally:
            if alarm_id and self.store:
                await asyncio.to_thread(self.store.mark, alarm_id, outcome)
            if self.activity:
                await self.activity(False, alarm_id)

    async def cancel(self):
        if self.busy:
            self.stop.set()
            await asyncio.shield(self.task)


class PlaybackReceiver:
    def __init__(self, manager, send, device_id, timeout=10, clock=time.monotonic):
        self.manager, self.send, self.device_id, self.timeout, self.clock = (
            manager,
            send,
            device_id,
            timeout,
            clock,
        )
        self.begin = None
        self.buffer = bytearray()
        self.sequence = 0
        self.updated = 0
        self.task = None
        self.used = set()

    async def _status(self, event, status, code=None):
        await self.send(
            PlaybackStatus(
                device_id=self.device_id,
                request_id=event.request_id,
                session_id=event.session_id,
                payload=PlaybackStatusPayload(
                    status=status, next_sequence=self.sequence, code=code
                ),
            )
        )

    async def start(self, event):
        if event.device_id != self.device_id:
            raise SpeechError("playback_device_mismatch")
        if event.request_id in self.used or len(self.used) >= 1024:
            await self._status(event, "failed", "playback_id_reused_or_capacity")
            return
        if self.begin or self.manager.busy:
            await self._status(event, "failed", "playback_busy")
            return
        self.used.add(event.request_id)
        self.begin, self.sequence, self.updated = event, 0, self.clock()
        self.buffer.clear()
        await self._status(event, "accepted")

    def check(self, event):
        if (
            event.device_id != self.device_id
            or not self.begin
            or self.clock() - self.updated > self.timeout
            or (event.request_id, event.session_id)
            != (self.begin.request_id, self.begin.session_id)
        ):
            raise SpeechError("playback_transfer_mismatch")

    async def append(self, event):
        self.check(event)
        try:
            data = base64.b64decode(event.payload.data, validate=True)
        except ValueError:
            raise SpeechError("invalid_playback_frame") from None
        if (
            event.payload.sequence != self.sequence
            or not data
            or len(data) % 2
            or len(data) > MAX_FRAME_BYTES
            or len(self.buffer) + len(data) > self.begin.payload.total_bytes
        ):
            raise SpeechError("invalid_playback_frame")
        self.buffer.extend(data)
        self.sequence += 1
        self.updated = self.clock()
        await self._status(event, "buffered")

    async def finish(self, event):
        self.check(event)
        if (
            event.payload.chunks != self.sequence
            or len(self.buffer) != self.begin.payload.total_bytes
        ):
            raise SpeechError("incomplete_playback")
        begin = self.begin
        audio = SpeechAudio(bytes(self.buffer), begin.payload.sample_rate)
        self.clear()

        async def output():
            try:
                return await self.manager.play(
                    audio, begin.request_id, begin.session_id, alarm_id=begin.payload.alarm_id
                )
            except SpeechError as exc:
                await self._status(begin, "failed", exc.code)
                return "failed"

        self.task = asyncio.create_task(output())
        self.task.add_done_callback(lambda task: task.exception() if not task.cancelled() else None)

    def clear(self):
        self.begin = None
        self.buffer.clear()
        self.sequence = 0

    async def expire(self):
        if self.begin and self.clock() - self.updated > self.timeout:
            event = self.begin
            self.clear()
            await self._status(event, "failed", "playback_transfer_timeout")

    async def cancel(self, event=None):
        assembly_matches = (
            self.begin
            and event is not None
            and (event.request_id, event.session_id)
            == (self.begin.request_id, self.begin.session_id)
        )
        if event is None or assembly_matches:
            self.clear()
            if assembly_matches:
                await self._status(event, "cancelled")
        matches = event is None or (event.request_id, event.session_id) == (
            self.manager.active_request,
            self.manager.active_session,
        )
        if matches:
            await self.manager.cancel()
        if matches and self.task:
            await asyncio.gather(self.task, return_exceptions=True)
