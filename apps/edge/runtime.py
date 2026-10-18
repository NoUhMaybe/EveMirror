"""Outbound authenticated edge runtime. No inference, recording polling or cloud keys."""

from __future__ import annotations

import argparse
import asyncio
import base64
import logging
import random
import wave
from pathlib import Path
from uuid import uuid4

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidStatus

from apps.config import EdgeSettings
from apps.edge.commands import CommandProcessor
from apps.edge.hardware import FeatherService, SimulatedHardware
from apps.edge.presence.controller import DisplayController
from apps.edge.voice.controller import VoiceController
from packages.audio import SpeechError
from packages.protocol import (
    MAX_FRAME_BYTES,
    MAX_MESSAGE_BYTES,
    AudioBegin,
    AudioBeginPayload,
    AudioChunk,
    AudioChunkPayload,
    AudioEnd,
    AudioEndPayload,
    AudioReceived,
    Cancel,
    DeviceCommand,
    EdgeHello,
    EdgePresenceState,
    ErrorEvent,
    Heartbeat,
    HelloPayload,
    Message,
    PlaybackBegin,
    PlaybackCancel,
    PlaybackChunk,
    PlaybackEnd,
    StateSnapshot,
    TimerSync,
    VoiceControl,
    VoiceControlAck,
    VoiceControlAckPayload,
    VoiceStatus,
    parse_message,
)

logger = logging.getLogger("eve.edge")


class EdgeOfflineError(Exception):
    pass


class AudioUploadError(Exception):
    pass


def reconnect_delay(attempt: int, minimum: float, maximum: float) -> float:
    return min(maximum, minimum * (2 ** min(attempt, 16)) * random.uniform(0.8, 1.2))


class EdgeRuntime:
    def __init__(
        self,
        settings: EdgeSettings,
        hardware=None,
        *,
        audio_source=None,
        detector=None,
        speaker=None,
        voice_clock=None,
        voice_utc_clock=None,
        presence_sensor=None,
        presence_clock=None,
        presence_wall=None,
    ):
        self.settings = settings
        self.hardware = hardware or (
            SimulatedHardware()
            if settings.simulate_hardware
            else FeatherService(
                port=settings.serial_port,
                timeout=settings.serial_timeout,
            )
        )
        self.commands = CommandProcessor(settings.device_id, self.hardware, settings.journal_path)
        self.display = DisplayController(
            settings,
            self.commands,
            sensor=presence_sensor,
            **({"clock": presence_clock} if presence_clock else {}),
            **({"wall": presence_wall} if presence_wall else {}),
        )
        self.connected = asyncio.Event()
        self._socket = None
        self._send_lock = asyncio.Lock()
        self._upload_lock = asyncio.Lock()
        self._receipts: dict = {}
        self._command_tasks = set()
        self.voice = (
            VoiceController(
                self,
                source=audio_source,
                detector=detector,
                speaker=speaker,
                **({"clock": voice_clock} if voice_clock else {}),
                **({"utc_clock": voice_utc_clock} if voice_utc_clock else {}),
            )
            if settings.voice.enabled
            else None
        )

    async def _send(self, event: Message):
        async with self._send_lock:
            if self._socket is None:
                raise EdgeOfflineError("Backend unavailable")
            async with asyncio.timeout(5):
                await self._socket.send(event.model_dump_json())

    async def upload_pcm(self, pcm: bytes, *, session_id=None, request_id=None) -> AudioReceived:
        """Transitional whole utterance, frame bounded. Never retains or retries audio."""
        # Validate before buffering, and refuse additional simultaneous uploads.
        payload = AudioBeginPayload(total_bytes=len(pcm))
        if self._upload_lock.locked():
            raise AudioUploadError("Audio upload already active")
        if not self.connected.is_set():
            raise EdgeOfflineError("Backend unavailable")
        async with self._upload_lock:
            session_id, request_id = session_id or uuid4(), request_id or uuid4()
            identity = {
                "device_id": self.settings.device_id,
                "session_id": session_id,
                "request_id": request_id,
            }
            receipt = asyncio.get_running_loop().create_future()
            self._receipts[request_id] = receipt
            try:
                await self._send(AudioBegin(**identity, payload=payload))
                chunks = 0
                for start in range(0, len(pcm), MAX_FRAME_BYTES):
                    data = base64.b64encode(pcm[start : start + MAX_FRAME_BYTES]).decode("ascii")
                    await self._send(
                        AudioChunk(
                            **identity,
                            payload=AudioChunkPayload(sequence=chunks, data=data),
                        )
                    )
                    chunks += 1
                await self._send(AudioEnd(**identity, payload=AudioEndPayload(chunks=chunks)))
                return await asyncio.wait_for(asyncio.shield(receipt), 65)
            except (asyncio.CancelledError, TimeoutError):
                try:
                    await self._send(Cancel(**identity))
                except (EdgeOfflineError, ConnectionClosed, TimeoutError):
                    pass
                raise
            finally:
                self._receipts.pop(request_id, None)
                if not receipt.done():
                    receipt.cancel()
                elif not receipt.cancelled():
                    receipt.exception()

    async def _receive(self):
        async for raw in self._socket:
            event = parse_message(raw)
            if event.device_id != self.settings.device_id:
                raise ValueError("Unexpected device identity")
            if isinstance(event, DeviceCommand):

                async def execute(command):
                    ack = await self.display.execute(command)
                    await self._send(ack)

                if len(self._command_tasks) >= 8:
                    raise ValueError("Command queue is full")
                task = asyncio.create_task(execute(event))
                self._command_tasks.add(task)
                task.add_done_callback(self._command_tasks.discard)
                task.add_done_callback(
                    lambda finished: finished.exception() if not finished.cancelled() else None
                )
            elif isinstance(event, StateSnapshot):
                self.connected.set()
                if self.voice:
                    await self.voice.publish()
            elif isinstance(event, (AudioReceived, ErrorEvent)):
                pending = self._receipts.get(event.request_id)
                if pending and not pending.done():
                    if isinstance(event, AudioReceived):
                        pending.set_result(event)
                    else:
                        pending.set_exception(AudioUploadError(event.payload.code))
            elif isinstance(
                event,
                (PlaybackBegin, PlaybackChunk, PlaybackEnd, PlaybackCancel, VoiceStatus, TimerSync),
            ):
                if self.voice is None:
                    raise ValueError("Voice messages were not negotiated")
                try:
                    await self.voice.handle(event)
                except SpeechError:
                    self.voice.receiver.clear()
                    if isinstance(event, (PlaybackBegin, PlaybackChunk, PlaybackEnd)):
                        await self.voice.receiver._status(event, "failed", "invalid_playback")
            elif isinstance(event, Cancel):
                if self.voice and event.session_id == self.voice.session_id:
                    await self.voice.cancel()
            elif isinstance(event, VoiceControl):
                if self.voice is None:
                    raise ValueError("Voice control was not negotiated")
                # Persist mute before acknowledging; ordinary cancellation preserves alarms.
                try:
                    await self.voice.set_muted(event.payload.muted)
                    payload = VoiceControlAckPayload(status="completed", muted=self.voice.muted)
                except SpeechError:
                    payload = VoiceControlAckPayload(
                        status="error", muted=self.voice.muted, error="voice_control_failed"
                    )
                await self._send(
                    VoiceControlAck(
                        device_id=self.settings.device_id,
                        request_id=event.request_id,
                        payload=payload,
                    )
                )
            elif not isinstance(event, Heartbeat):
                raise ValueError("Message direction is not permitted")

    async def _heartbeat(self):
        while True:
            await self._send(
                Heartbeat(
                    device_id=self.settings.device_id,
                    payload=self.hardware.status,
                )
            )
            if self.voice:
                await self.voice.publish()
            await self._send(
                EdgePresenceState(device_id=self.settings.device_id, payload=self.display.status)
            )
            await asyncio.sleep(self.settings.heartbeat_interval)

    async def _presence_updates(self):
        while True:
            status = await self.display.updates.get()
            if self.connected.is_set():
                try:
                    await self._send(
                        EdgePresenceState(device_id=self.settings.device_id, payload=status)
                    )
                except (EdgeOfflineError, ConnectionClosed, TimeoutError):
                    pass

    async def _connection(self):
        endpoint = self.settings.server_url.rstrip("/") + f"/ws/edge/{self.settings.device_id}"
        async with connect(
            endpoint,
            additional_headers={
                "Authorization": "Bearer " + self.settings.token.get_secret_value(),
            },
            proxy=None,
            max_size=MAX_MESSAGE_BYTES,
            max_queue=8,
            open_timeout=10,
            close_timeout=3,
            ping_interval=15,
            ping_timeout=15,
        ) as socket:
            self._socket = socket
            capabilities = (
                ("brightness", "pcm_upload", "voice", "playback", "timer_sync", "voice_control")
                if self.voice and self.voice.storage_ready
                else ("brightness", "pcm_upload")
            )
            await self._send(
                EdgeHello(
                    device_id=self.settings.device_id,
                    payload=HelloPayload(capabilities=capabilities + ("presence",)),
                )
            )
            tasks = [asyncio.create_task(self._receive()), asyncio.create_task(self._heartbeat())]
            try:
                done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    task.result()
            finally:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)

    async def run(self):
        attempt = 0
        local_tasks = [
            asyncio.create_task(self.display.run()),
            asyncio.create_task(self._presence_updates()),
        ]
        try:
            if self.voice:
                await self.voice.start()
            while True:
                started = asyncio.get_running_loop().time()
                try:
                    await self._connection()
                except (OSError, ConnectionClosed, InvalidStatus, TimeoutError, ValueError) as exc:
                    # Exception text can contain URLs/headers; log only class and scoped ID.
                    logger.warning(
                        "backend_disconnected device_id=%s error_type=%s",
                        self.settings.device_id,
                        type(exc).__name__,
                    )
                finally:
                    had_socket = self._socket is not None
                    self.connected.clear()
                    self._socket = None
                    if self.voice and had_socket:
                        # A failed reconnect is not a new disconnect. Repeated
                        # attempts must not cancel local offline wake/capture.
                        await self.voice.disconnected()
                    for pending in list(self._receipts.values()):
                        if not pending.done():
                            pending.set_exception(EdgeOfflineError("Backend disconnected"))
                if asyncio.get_running_loop().time() - started > 30:
                    attempt = 0
                await asyncio.sleep(
                    reconnect_delay(
                        attempt,
                        self.settings.reconnect_min,
                        self.settings.reconnect_max,
                    )
                )
                attempt += 1
        finally:
            if self.voice:
                await self.voice.close()
            for command_task in list(self._command_tasks):
                command_task.cancel()
            await asyncio.gather(*self._command_tasks, return_exceptions=True)
            for task in local_tasks:
                task.cancel()
            await asyncio.gather(*local_tasks, return_exceptions=True)
            try:
                await self.hardware.close()
            finally:
                self.commands.close()


def read_pcm_wav(path: Path) -> bytes:
    with wave.open(str(path), "rb") as audio:
        if (audio.getframerate(), audio.getnchannels(), audio.getsampwidth()) != (16000, 1, 2):
            raise ValueError("Expected PCM16 mono 16 kHz WAV")
        AudioBeginPayload(total_bytes=audio.getnframes() * 2)
        pcm = audio.readframes(audio.getnframes())
        if len(pcm) != audio.getnframes() * 2:
            raise ValueError("Truncated PCM WAV")
        return pcm


async def run_cli(settings: EdgeSettings, wav: Path | None, unmute=False):
    runtime = EdgeRuntime(settings)
    if wav is None:
        if not unmute:
            await runtime.run()
            return
        task = asyncio.create_task(runtime.run())
        try:
            await asyncio.wait_for(runtime.voice.started.wait(), 15)
            await runtime.voice.set_muted(False)
            await task
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        return
    pcm = read_pcm_wav(wav)
    task = asyncio.create_task(runtime.run())
    try:
        await asyncio.wait_for(runtime.connected.wait(), 15)
        receipt = await runtime.upload_pcm(pcm)
        print(
            f"Backend received {receipt.payload.total_bytes} PCM bytes; "
            "this diagnostic confirms transport receipt only."
        )
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


def main():
    parser = argparse.ArgumentParser(description="Eve Edge authenticated transport")
    parser.add_argument(
        "--simulate-hardware", action="store_true", help="Explicit simulated Feather"
    )
    parser.add_argument("--upload-wav", type=Path, help="Upload one existing test WAV, then exit")
    parser.add_argument(
        "--voice", action="store_true", help="Enable configured local wake/VAD and playback"
    )
    parser.add_argument(
        "--unmute",
        action="store_true",
        help="Explicitly unmute this voice process and saved preference",
    )
    parser.add_argument(
        "--list-audio-devices",
        action="store_true",
        help="List PortAudio device names without starting capture",
    )
    parser.add_argument(
        "--validate-voice-assets",
        action="store_true",
        help="Verify configured wake/VAD assets without opening audio",
    )
    args = parser.parse_args()
    if args.list_audio_devices:
        import sounddevice as sd

        print(sd.query_devices())
        return
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    settings = EdgeSettings()
    if args.validate_voice_assets:
        from packages.assets import AssetCatalog

        if settings.voice.asset_manifest is None:
            parser.error("Configure EVE_EDGE_VOICE__ASSET_MANIFEST")
        catalog = AssetCatalog(settings.voice.asset_manifest, settings.voice.asset_root)
        for name in ("wake_word", "melspectrogram", "embedding", "silero_vad"):
            catalog.path(name)
        print("All four wake/VAD assets match the trusted manifest.")
        return
    if args.voice:
        settings = settings.model_copy(
            update={"voice": settings.voice.model_copy(update={"enabled": True})}
        )
    if args.unmute and not settings.voice.enabled:
        parser.error("--unmute requires voice to be enabled")
    if args.upload_wav and (settings.voice.enabled or args.unmute):
        parser.error("--upload-wav is a separate transport diagnostic; disable voice capture")
    if args.simulate_hardware:
        settings = settings.model_copy(update={"simulate_hardware": True})
    try:
        asyncio.run(run_cli(settings, args.upload_wav, args.unmute))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
