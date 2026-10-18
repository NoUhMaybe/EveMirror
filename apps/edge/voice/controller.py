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
            self.source.suppress(self.muted or self.processing or self.playing)

    async def publish(self):
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
                            bool(self.turn_task and not self.turn_task.done()) or self.player.busy
                        )
                        async with self.machine_lock:
                            events = await owned_thread(self.machine.feed, pcm)
                        if self.muted:
                            continue
                        for kind, data in events:
                            if kind == "wake":
                                self.state = "WAKE_DETECTED"
                                await self.publish()
                                await self.player.play(notification(), uuid4(), uuid4(), chime=True)
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
        self.metrics = {"capture_seconds": len(pcm) / 32000}
        self.processing = True
        self._suppress_source()
        self.session_id = uuid4()
        request_id = uuid4()
        self.done = asyncio.get_running_loop().create_future()
        self.state = "UPLOADING"
        await self.publish()
        started = self.clock()
        try:
            async with asyncio.timeout(self.settings.turn_timeout):
                await self.runtime.upload_pcm(
                    pcm, session_id=self.session_id, request_id=request_id
                )
                self.metrics["upload_ms"] = (self.clock() - started) * 1000
                await self.done
        except asyncio.CancelledError:
            with suppress(Exception):
                await self._send(
                    Cancel(
                        device_id=self.runtime.settings.device_id,
                        session_id=self.session_id,
                        request_id=request_id,
                    )
                )
            raise
        except Exception:
            self.errors += 1
            self.state = "ERROR"
            with suppress(Exception):
                await self._send(
                    Cancel(
                        device_id=self.runtime.settings.device_id,
                        session_id=self.session_id,
                        request_id=request_id,
                    )
                )
        finally:
            self.processing = False
            self._suppress_source()
            self.metrics["turn_ms"] = (self.clock() - started) * 1000
            if self.machine:
                self.machine.busy = False
                if self.state != "FOLLOW_UP":
                    self.machine.clear()
                    self.machine.state = "IDLE"
                    self.state = "IDLE"
            with suppress(Exception):
                await self.publish()

    async def _playback_activity(self, playing, alarm_id):
        self.playing = playing
        self._suppress_source()
        if self.machine:
            async with self.machine_lock:
                self.machine.clear()
                self.machine.busy = playing
            if not playing:
                self.machine.suppressed_until = self.clock() + self.settings.echo_cooldown
                self.source.flush()
        self.playing_alarm = alarm_id if playing else None

    async def handle(self, event):
        if isinstance(event, VoiceStatus):
            if event.session_id != self.session_id:
                return
            self.state = event.payload.state
            if self.state == "ERROR":
                self.last_error = event.payload.error or "voice_failed"
                self.errors += 1
            self.metrics.update(event.payload.metrics)
            if self.machine and self.state == "FOLLOW_UP":
                async with self.machine_lock:
                    self.machine.listen(follow_up=True)
                self.machine.follow_until = self.clock() + min(
                    event.payload.follow_up_seconds, self.settings.follow_up_seconds
                )
                self.machine.suppressed_until = self.clock() + self.settings.echo_cooldown
                self.last_success = self.utc_clock().isoformat()
            if self.done and not self.done.done() and self.state in {"FOLLOW_UP", "ERROR", "IDLE"}:
                self.done.set_result(None)
        elif isinstance(event, PlaybackBegin):
            await self.receiver.start(event)
        elif isinstance(event, PlaybackChunk):
            await self.receiver.append(event)
        elif isinstance(event, PlaybackEnd):
            await self.receiver.finish(event)
        elif isinstance(event, PlaybackCancel):
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
                    await self.publish()
                if self.settings.offline_alarms or self.runtime.connected.is_set():
                    due = await asyncio.to_thread(
                        self.store.due, self.utc_clock(), self.settings.offline_lease_seconds
                    )
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
        if self.turn_task and not self.turn_task.done():
            self.turn_task.cancel()
            await asyncio.gather(self.turn_task, return_exceptions=True)
        if self.player.busy and self.player.active_alarm and not include_alarms:
            self.receiver.clear()
        else:
            await self.receiver.cancel()
        if self.machine:
            async with self.machine_lock:
                self.machine.clear()
                self.machine.busy, self.machine.state = False, "IDLE"
        self.state = "IDLE"

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
