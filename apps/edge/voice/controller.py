"""One edge interaction state, with separate mute/network/alarm conditions."""

import asyncio
import time
from contextlib import aclosing, suppress
from datetime import UTC, datetime
from uuid import UUID, uuid4

from apps.edge.voice.alarms import AlarmStore, TimerSynchronizer
from apps.edge.voice.capture import CaptureMachine, WakeVAD
from apps.edge.voice.io import SoundInput, SoundOutput
from apps.edge.voice.playback import PlaybackManager, PlaybackReceiver
from packages.audio import SpeechError, notification, owned_thread
from packages.protocol import (
    AlarmDismiss,
    Cancel,
    EdgeVoicePayload,
    EdgeVoiceState,
    PlaybackBegin,
    PlaybackCancel,
    PlaybackChunk,
    PlaybackEnd,
    PlaybackStatus,
    PlaybackStatusPayload,
    TimerSync,
    TimerSyncReceipt,
    TimerSyncReceiptPayload,
    VoiceStatus,
)


class VoiceController:
    def __init__(
        self,
        runtime,
        *,
        source=None,
        detector=None,
        speaker=None,
        clock=time.monotonic,
        utc_clock=lambda: datetime.now(UTC),
    ):
        self.runtime, self.settings, self.clock = runtime, runtime.settings.voice, clock
        self.utc_clock = utc_clock
        self.source = source or SoundInput(self.settings)
        self.detector = detector
        self.machine = None
        self.machine_lock = asyncio.Lock()
        self.store = AlarmStore(
            self.settings.state_path, runtime.settings.device_id, self.settings.alarm_receipt_limit
        )
        self.sync = TimerSynchronizer(self.store, utc_clock, clock)
        self.player = PlaybackManager(
            speaker or SoundOutput(self.settings),
            self._send,
            runtime.settings.device_id,
            self.store,
            self._playback_activity,
        )
        self.receiver = PlaybackReceiver(
            self.player,
            self._send,
            runtime.settings.device_id,
            self.settings.transfer_timeout,
            clock,
        )
        self.muted = self.settings.muted_on_start
        self.errors, self.ready, self.storage_ready = 0, False, False
        self.state = "STARTING"
        self.session_id = None
        self.request_id = None
        self.generation = 0
        self.playback_requests = set()
        self.cancel_lock = asyncio.Lock()
        self.cancelling = 0
        self.done = None
        self.turn_task = None
        self.tasks = []
        self.last_success = None
        self.metrics = {}
        self.last_error = None
        self.processing = self.playing = False
        self.started = asyncio.Event()
        self.playing_alarm = None

    async def _send(self, event):
        if self.runtime.connected.is_set():
            await self.runtime._send(event)

    def _suppress_source(self):
        if hasattr(self.source, "suppress"):
            self.source.suppress(
                self.muted or self.processing or self.playing or bool(self.cancelling)
            )

    def _invalidate_turn(self):
        # Revoke acceptance synchronously, before cancellation/driver cleanup awaits.
        self.generation += 1
        self.session_id = self.request_id = None
        self.playback_requests.clear()
        if self.done and not self.done.done():
            self.done.cancel()

    def _active_session(self, session_id):
        return (
            self.session_id is not None
            and session_id == self.session_id
            and self.request_id is not None
            and self.done is not None
            and not self.done.done()
            and not self.cancelling
            and not self.muted
        )

    async def publish(self):
        if display := getattr(self.runtime, "display", None):
            await display.activity("voice", self.state not in {"IDLE", "ERROR", "STARTING"})
        await self._send(
            EdgeVoiceState(
                device_id=self.runtime.settings.device_id,
                session_id=self.session_id,
                payload=EdgeVoicePayload(
                    state=self.state,
                    muted=self.muted,
                    microphone=getattr(self.source, "available", False),
                    wake_ready=self.ready,
                    vad_ready=self.ready,
                    speaker=getattr(self.player.driver, "available", False),
                    errors=self.errors,
                    error=self.last_error,
                    input_level_rms=self.machine.last_rms
                    if self.machine and not self.muted
                    else 0.0,
                    metrics={**(self.machine.metrics if self.machine else {}), **self.metrics},
                ),
            )
        )

    async def start(self):
        try:
            await asyncio.to_thread(self.store.open)
            self.storage_ready = True
            self.muted = await asyncio.to_thread(self.store.muted, self.settings.muted_on_start)
        except Exception:
            self.muted, self.state = True, "ERROR"
            self.errors += 1
            self.last_error = "voice_storage_unavailable"
            self.started.set()
            return
        self.started.set()
        self._suppress_source()
        self.tasks = [asyncio.create_task(self._capture()), asyncio.create_task(self._alarms())]

    async def _capture(self):
        while True:
            try:
                if self.detector is None:
                    self.detector = await asyncio.to_thread(WakeVAD, self.settings)
                if self.machine is None:
                    self.machine = CaptureMachine(self.settings, self.detector, self.clock)
                self.ready = True
                self.state = "IDLE"
                await self.publish()
                async with aclosing(self.source.frames()) as frames:
                    async for pcm in frames:
                        self.machine.muted = self.muted
                        self.machine.busy = (
                            bool(self.turn_task and not self.turn_task.done())
                            or self.player.busy
                            or bool(self.cancelling)
                        )
                        generation = self.generation
                        async with self.machine_lock:
                            events = await owned_thread(self.machine.feed, pcm)
                        if self.muted or self.cancelling or generation != self.generation:
                            continue
                        for kind, data in events:
                            if kind == "wake":
                                self.state = "WAKE_DETECTED"
                                await self.publish()
                                if generation != self.generation or self.cancelling or self.muted:
                                    continue
                                await self.player.play(notification(), uuid4(), uuid4(), chime=True)
                                if generation != self.generation or self.cancelling or self.muted:
                                    continue
                                self.source.flush()
                                self.machine.listen()
                                self.machine.suppressed_until = (
                                    self.clock() + self.settings.chime_cooldown
                                )
                                self.state = "LISTENING"
                                await self.publish()
                            elif kind == "speech_started":
                                self.state = "LISTENING"
                                await self.publish()
                            elif kind == "utterance":
                                self.turn_task = asyncio.create_task(self._turn(data))
                            elif kind == "empty":
                                self.state = "IDLE"
                                await self.publish()
                        if self.state == "FOLLOW_UP" and self.machine.state == "IDLE":
                            self._invalidate_turn()
                            self.state = "IDLE"
                            await self.publish()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.errors += 1
                self.last_error = (
                    exc.code if isinstance(exc, SpeechError) else "capture_unavailable"
                )
                self.state, self.ready = "ERROR", False
                if self.machine:
                    self.machine.clear()
                with suppress(Exception):
                    await self.publish()
                await asyncio.sleep(3 if self.detector else 30)

    async def _turn(self, pcm):
        if self.cancelling or self.muted:
            return
        self.generation += 1
        generation = self.generation
        self.metrics = {"capture_seconds": len(pcm) / 32000}
        self.processing = True
        self._suppress_source()
        session_id, request_id = uuid4(), uuid4()
        self.session_id, self.request_id = session_id, request_id
        self.playback_requests.clear()
        done = self.done = asyncio.get_running_loop().create_future()
        self.state = "UPLOADING"
        started = self.clock()
        try:
            await self.publish()
            async with asyncio.timeout(self.settings.turn_timeout):
                await self.runtime.upload_pcm(pcm, session_id=session_id, request_id=request_id)
                self.metrics["upload_ms"] = (self.clock() - started) * 1000
                await done
        except asyncio.CancelledError:
            if generation == self.generation:
                self._invalidate_turn()
            await self.receiver.cancel(preserve_alarms=True)
            with suppress(Exception):
                await self._send(
                    Cancel(
                        device_id=self.runtime.settings.device_id,
                        session_id=session_id,
                        request_id=request_id,
                    )
                )
            raise
        except Exception:
            if generation == self.generation:
                self._invalidate_turn()
                self.errors += 1
                self.state = "ERROR"
            await self.receiver.cancel(preserve_alarms=True)
            with suppress(Exception):
                await self._send(
                    Cancel(
                        device_id=self.runtime.settings.device_id,
                        session_id=session_id,
                        request_id=request_id,
                    )
                )
        finally:
            async with self.machine_lock:
                if self.turn_task is asyncio.current_task():
                    self.processing = False
                    self.request_id = None
                    self.playback_requests.clear()
                    if not done.done():
                        done.cancel()
                    self.metrics["turn_ms"] = (self.clock() - started) * 1000
                    if self.machine:
                        self.machine.busy = self.player.busy
                    if generation != self.generation or self.state != "FOLLOW_UP":
                        self.session_id = None
                        if self.machine:
                            self.machine.clear()
                            self.machine.state = "IDLE"
                        self.state = "IDLE"
                    self._suppress_source()
            with suppress(Exception):
                await self.publish()

    async def _playback_activity(self, playing, alarm_id):
        self.playing = playing
        self._suppress_source()
        if display := getattr(self.runtime, "display", None):
            await display.activity("playback", playing)
        if self.machine:
            async with self.machine_lock:
                self.machine.clear()
                self.machine.busy = playing
            if not playing:
                self.machine.suppressed_until = self.clock() + self.settings.echo_cooldown
                self.source.flush()
        self.playing_alarm = alarm_id if playing else None

    def _status_matches(self, event):
        if event.device_id != self.runtime.settings.device_id or not self._active_session(
            event.session_id
        ):
            return False
        if event.payload.state == "SPEAKING":
            # Speaking uses the server's playback UUID, not the upload UUID.
            return (
                event.request_id in self.playback_requests
                and self.player.busy
                and self.player.active_request == event.request_id
                and self.player.active_session == event.session_id
                and self.player.active_alarm is None
            )
        return event.request_id == self.request_id

    def _alarm_event(self, event):
        if isinstance(event, PlaybackBegin):
            return (
                event.payload.alarm_id is not None
                and event.request_id == event.session_id == event.payload.alarm_id
            )
        for begin in (self.receiver.begin, self.receiver.output_begin):
            if (
                begin
                and begin.payload.alarm_id is not None
                and (event.request_id, event.session_id) == (begin.request_id, begin.session_id)
            ):
                return True
        return self.player.active_alarm is not None and (event.request_id, event.session_id) == (
            self.player.active_request,
            self.player.active_session,
        )

    def _playback_matches(self, event):
        begin = self.receiver.begin
        return (
            begin is not None
            and (event.request_id, event.session_id) == (begin.request_id, begin.session_id)
            and (self._active_session(event.session_id) or self._alarm_event(event))
        )

    async def handle(self, event):
        if isinstance(event, VoiceStatus):
            generation = self.generation
            if not self._status_matches(event):
                return
            async with self.machine_lock:
                # A handler may have passed the first check before waiting on capture.
                if generation != self.generation or not self._status_matches(event):
                    return
                self.state = event.payload.state
                if self.state == "ERROR":
                    self.last_error = event.payload.error or "voice_failed"
                    self.errors += 1
                self.metrics.update(event.payload.metrics)
                if self.machine and self.state == "FOLLOW_UP":
                    self.machine.listen(follow_up=True)
                    self.machine.follow_until = self.clock() + min(
                        event.payload.follow_up_seconds, self.settings.follow_up_seconds
                    )
                    self.machine.suppressed_until = self.clock() + self.settings.echo_cooldown
                    self.last_success = self.utc_clock().isoformat()
                if self.state in {"FOLLOW_UP", "ERROR", "IDLE"}:
                    self.done.set_result(None)
        elif isinstance(event, PlaybackBegin):
            if not self._active_session(event.session_id) and not self._alarm_event(event):
                return
            generation = self.generation
            await self.receiver.start(event)
            if (
                generation == self.generation
                and self.receiver.begin is event
                and event.payload.alarm_id is None
            ):
                self.playback_requests.add(event.request_id)
        elif isinstance(event, PlaybackChunk):
            if not self._playback_matches(event):
                return
            await self.receiver.append(event)
        elif isinstance(event, PlaybackEnd):
            if not self._playback_matches(event):
                return
            await self.receiver.finish(event)
        elif isinstance(event, PlaybackCancel):
            if not self._active_session(event.session_id) and not self._alarm_event(event):
                return
            await self.receiver.cancel(event)
        elif isinstance(event, TimerSync):
            if not self.storage_ready:
                raise SpeechError("voice_storage_unavailable")
            complete = await asyncio.to_thread(self.sync.accept, event)
            if complete:
                await self._send(
                    TimerSyncReceipt(
                        device_id=self.runtime.settings.device_id,
                        payload=TimerSyncReceiptPayload(generation=event.payload.generation),
                    )
                )
                due = await asyncio.to_thread(
                    self.store.due, self.utc_clock(), self.settings.offline_lease_seconds
                )
                for timer in due:
                    identity = UUID(timer["alarm_id"])
                    previous = await asyncio.to_thread(self.store.receipt, identity)
                    if previous:
                        await self._send(
                            PlaybackStatus(
                                device_id=self.runtime.settings.device_id,
                                request_id=identity,
                                session_id=identity,
                                payload=PlaybackStatusPayload(
                                    alarm_id=identity,
                                    status="indeterminate" if previous == "reserved" else previous,
                                    code="replayed_receipt",
                                ),
                            )
                        )
                for identity in await asyncio.to_thread(self.store.pending_dismissals):
                    await self._send(
                        AlarmDismiss(device_id=self.runtime.settings.device_id, payload=identity)
                    )

    async def _alarms(self):
        while True:
            try:
                await self.receiver.expire()
                if (
                    self.machine
                    and self.state == "FOLLOW_UP"
                    and self.clock() >= self.machine.follow_until
                    and not (self.turn_task and not self.turn_task.done())
                ):
                    async with self.machine_lock:
                        self.machine.clear()
                        self.machine.state = "IDLE"
                    self.state = "IDLE"
                    self._invalidate_turn()
                    await self.publish()
                if self.settings.offline_alarms or self.runtime.connected.is_set():
                    due = await asyncio.to_thread(
                        self.store.due, self.utc_clock(), self.settings.offline_lease_seconds
                    )
                    if display := getattr(self.runtime, "display", None):
                        # Includes already-attempted alarms until dismissed/synchronized away.
                        # Audio attempt receipts remain unchanged and prevent replay.
                        await display.activity("alarms", bool(due))
                    for timer in due:
                        identity = UUID(timer["alarm_id"])
                        # Reserve before output; unknown playback is never replayed.
                        await self.player.play(
                            notification(alarm=True), identity, identity, alarm_id=identity
                        )
            except asyncio.CancelledError:
                raise
            except Exception:
                self.errors += 1
            await asyncio.sleep(0.5)

    async def set_muted(self, muted):
        if not isinstance(muted, bool) or not self.storage_ready:
            raise SpeechError("voice_storage_unavailable")
        # Apply privacy state before any await; an in-flight utterance is discarded.
        self.muted = muted
        self._suppress_source()
        if self.machine:
            async with self.machine_lock:
                self.machine.muted = muted
                self.machine.clear()
        self.source.flush()
        if muted:
            await self.cancel()
        await asyncio.to_thread(self.store.set_muted, muted)
        await self.publish()

    async def dismiss(self, alarm_id):
        await asyncio.to_thread(self.store.dismiss, alarm_id)
        if self.playing_alarm == alarm_id:
            await self.player.cancel()
        await self._send(AlarmDismiss(device_id=self.runtime.settings.device_id, payload=alarm_id))

    async def cancel(self, include_alarms=False):
        self._invalidate_turn()
        self.cancelling += 1
        self.state = "IDLE"
        self._suppress_source()
        try:
            async with self.cancel_lock:
                task = self.turn_task
                if task and not task.done() and not task.cancelling():
                    task.cancel()
                # Cancel queued output before awaiting turn/network cleanup.
                await self.receiver.cancel(preserve_alarms=not include_alarms)
                if task:
                    await asyncio.gather(task, return_exceptions=True)
                async with self.machine_lock:
                    if self.machine:
                        self.machine.clear()
                        self.machine.busy, self.machine.state = self.player.busy, "IDLE"
                    self.processing, self.state = False, "IDLE"
                    self.source.flush()
        finally:
            self.cancelling -= 1
            self._suppress_source()

    async def disconnected(self):
        self.sync.clear()
        await self.cancel()

    async def close(self):
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        await self.cancel(include_alarms=True)
        if self.storage_ready:
            await asyncio.to_thread(self.store.close)
