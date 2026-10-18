"""Stop-and-wait chunk flow control on the existing authenticated socket."""

import asyncio
import base64
import time
from uuid import uuid4

from packages.audio import SpeechError
from packages.protocol import (
    MAX_FRAME_BYTES,
    AudioChunkPayload,
    AudioEndPayload,
    PlaybackBegin,
    PlaybackBeginPayload,
    PlaybackCancel,
    PlaybackChunk,
    PlaybackEnd,
)


class Delivery:
    def __init__(self, timeout):
        self.timeout = timeout
        self.pending = {}

    def receive(self, connection, event):
        record = self.pending.get(event.request_id)
        if (
            not record
            or record["connection"] is not connection
            or event.session_id != record["session_id"]
        ):
            return False
        if event.payload.status == "started" and record["started"] is None:
            record["started"] = time.monotonic()
        if event.payload.status == "completed":
            record["completed"] = time.monotonic()
        record["status"] = event.payload
        record["changed"].set()
        return True

    async def play(self, connection, audio, session_id):
        request_id = uuid4()
        identity = {
            "device_id": connection.state.device_id,
            "session_id": session_id,
            "request_id": request_id,
        }
        record = {
            "connection": connection,
            "session_id": session_id,
            "status": None,
            "changed": asyncio.Event(),
            "started": None,
            "completed": None,
        }
        self.pending[request_id] = record

        async def wait(predicate, duration=None):
            async with asyncio.timeout(duration or self.timeout):
                while True:
                    record["changed"].clear()
                    status = record["status"]
                    if status and status.status in {"failed", "cancelled", "indeterminate"}:
                        raise SpeechError("playback_" + status.status)
                    if status and predicate(status):
                        return status
                    await record["changed"].wait()

        began = time.monotonic()
        try:
            async with asyncio.timeout(audio.duration + self.timeout + 30):
                await connection.send(
                    PlaybackBegin(
                        **identity,
                        payload=PlaybackBeginPayload(
                            sample_rate=audio.sample_rate,
                            total_bytes=len(audio.pcm),
                            sample_count=audio.sample_count,
                            duration_seconds=audio.duration,
                        ),
                    )
                )
                await wait(lambda status: status.status == "accepted")
                chunks = 0
                for offset in range(0, len(audio.pcm), MAX_FRAME_BYTES):
                    data = base64.b64encode(audio.pcm[offset : offset + MAX_FRAME_BYTES]).decode(
                        "ascii"
                    )
                    await connection.send(
                        PlaybackChunk(
                            **identity, payload=AudioChunkPayload(sequence=chunks, data=data)
                        )
                    )
                    chunks += 1
                    await wait(
                        lambda status, expected=chunks: (
                            status.status == "buffered" and status.next_sequence == expected
                        )
                    )
                delivered = time.monotonic()
                await connection.send(
                    PlaybackEnd(**identity, payload=AudioEndPayload(chunks=chunks))
                )
                await wait(
                    lambda status: status.status == "completed", audio.duration + self.timeout
                )
                return {
                    "delivery_ms": (delivered - began) * 1000,
                    "playback_startup_ms": max(0, (record["started"] - delivered) * 1000)
                    if record["started"]
                    else 0,
                    "software_playback_ms": max(0, (record["completed"] - record["started"]) * 1000)
                    if record["completed"] and record["started"]
                    else 0,
                }
        except BaseException as exc:
            try:
                await connection.send(PlaybackCancel(**identity))
            except Exception:
                pass
            if isinstance(exc, TimeoutError):
                raise SpeechError("playback_timeout") from None
            raise
        finally:
            self.pending.pop(request_id, None)

    def disconnected(self, connection):
        for record in self.pending.values():
            if record["connection"] is connection:
                from packages.protocol import PlaybackStatusPayload

                record["status"] = PlaybackStatusPayload(status="indeterminate")
                record["changed"].set()
