"""Bounded in-memory PCM transport. No permanent recordings or model imports."""

from __future__ import annotations

import base64
import binascii
import time
from dataclasses import dataclass, field
from uuid import UUID

from packages.protocol import (
    MAX_FRAME_BYTES,
    SAMPLE_RATE,
    AudioBegin,
    AudioChunk,
    AudioEnd,
)


class AudioError(ValueError):
    pass


@dataclass(frozen=True)
class CompletedAudio:
    device_id: str
    session_id: UUID
    request_id: UUID
    pcm: bytes = field(repr=False)
    sample_rate: int = SAMPLE_RATE


class AudioAssembler:
    def __init__(self, timeout: float = 10, max_seconds: int = 30):
        self.timeout = timeout
        self.max_bytes = SAMPLE_RATE * 2 * max_seconds
        self.begin: AudioBegin | None = None
        self.buffer = bytearray()
        self.next_sequence = 0
        self.last_activity = 0.0
        self.started = 0.0

    def clear(self):
        self.begin = None
        self.buffer.clear()
        self.next_sequence = 0

    def expire(self) -> bool:
        now = time.monotonic()
        if self.begin and (
            now - self.last_activity > self.timeout
            or now - self.started > self.max_bytes / (SAMPLE_RATE * 2) + self.timeout
        ):
            self.clear()
            return True
        return False

    def start(self, message: AudioBegin):
        self.expire()
        if self.begin:
            raise AudioError("Only one audio upload per device may be active")
        if message.payload.total_bytes > self.max_bytes:
            raise AudioError("Utterance exceeds configured duration")
        self.begin = message
        self.last_activity = self.started = time.monotonic()

    def _check(self, message):
        self.expire()
        if not self.begin or (message.session_id, message.request_id, message.device_id) != (
            self.begin.session_id,
            self.begin.request_id,
            self.begin.device_id,
        ):
            raise AudioError("No matching audio upload")

    def append(self, message: AudioChunk):
        self._check(message)
        try:
            data = base64.b64decode(message.payload.data, validate=True)
        except (ValueError, binascii.Error):
            raise AudioError("Invalid base64 audio frame") from None
        if (
            message.payload.sequence != self.next_sequence
            or not data
            or len(data) % 2
            or len(data) > MAX_FRAME_BYTES
            or len(self.buffer) + len(data) > self.begin.payload.total_bytes
        ):
            raise AudioError("Invalid frame sequence or byte count")
        self.buffer.extend(data)
        self.next_sequence += 1
        self.last_activity = time.monotonic()

    def finish(self, message: AudioEnd) -> CompletedAudio:
        self._check(message)
        if (
            message.payload.chunks != self.next_sequence
            or len(self.buffer) != self.begin.payload.total_bytes
        ):
            raise AudioError("Incomplete audio upload")
        result = CompletedAudio(
            device_id=message.device_id,
            session_id=message.session_id,
            request_id=message.request_id,
            pcm=bytes(self.buffer),
        )
        self.clear()
        return result
