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
    ErrorEvent,
    Heartbeat,
    Message,
    StateSnapshot,
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
    def __init__(self, settings: EdgeSettings, hardware=None):
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
        self.connected = asyncio.Event()
        self._socket = None
        self._send_lock = asyncio.Lock()
        self._upload_lock = asyncio.Lock()
        self._receipts: dict = {}

    async def _send(self, event: Message):
        async with self._send_lock:
            if self._socket is None:
                raise EdgeOfflineError("Backend unavailable")
            async with asyncio.timeout(5):
                await self._socket.send(event.model_dump_json())

    async def upload_pcm(self, pcm: bytes) -> AudioReceived:
        """Transitional whole utterance, frame bounded. Never retains or retries audio."""
        # Validate before buffering, and refuse additional simultaneous uploads.
        payload = AudioBeginPayload(total_bytes=len(pcm))
        if self._upload_lock.locked():
            raise AudioUploadError("Audio upload already active")
        if not self.connected.is_set():
            raise EdgeOfflineError("Backend unavailable")
        async with self._upload_lock:
            session_id, request_id = uuid4(), uuid4()
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
                ack = await self.commands.execute(event)
                await self._send(ack)
            elif isinstance(event, StateSnapshot):
                self.connected.set()
            elif isinstance(event, (AudioReceived, ErrorEvent)):
                pending = self._receipts.get(event.request_id)
                if pending and not pending.done():
                    if isinstance(event, AudioReceived):
                        pending.set_result(event)
                    else:
                        pending.set_exception(AudioUploadError(event.payload.code))
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
            await asyncio.sleep(self.settings.heartbeat_interval)

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
            await self._send(EdgeHello(device_id=self.settings.device_id))
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
        try:
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
                    self.connected.clear()
                    self._socket = None
                    for pending in self._receipts.values():
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


async def run_cli(settings: EdgeSettings, wav: Path | None):
    runtime = EdgeRuntime(settings)
    if wav is None:
        await runtime.run()
        return
    pcm = read_pcm_wav(wav)
    task = asyncio.create_task(runtime.run())
    try:
        await asyncio.wait_for(runtime.connected.wait(), 15)
        receipt = await runtime.upload_pcm(pcm)
        print(
            f"Backend received {receipt.payload.total_bytes} PCM bytes; "
            "transcription is unconfigured."
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
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    settings = EdgeSettings()
    if args.simulate_hardware:
        settings = settings.model_copy(update={"simulate_hardware": True})
    try:
        asyncio.run(run_cli(settings, args.upload_wav))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
