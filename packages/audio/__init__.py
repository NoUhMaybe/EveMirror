"""PCM validation and local notification tones, independent of audio drivers."""

import asyncio
import math
import struct
from dataclasses import dataclass, field
from uuid import UUID


async def owned_thread(function, *args):
    """A caller holding a model lock must keep it until cancelled native work finishes."""
    task = asyncio.create_task(asyncio.to_thread(function, *args))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                continue
            except Exception:
                break
        if not task.cancelled():
            task.exception()
        raise


class SpeechError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class SpeechAudio:
    pcm: bytes = field(repr=False)
    sample_rate: int = 22050
    channels: int = 1
    encoding: str = "pcm_s16le"

    def __post_init__(self):
        if (
            not isinstance(self.pcm, bytes)
            or not isinstance(self.sample_rate, int)
            or isinstance(self.sample_rate, bool)
            or self.encoding != "pcm_s16le"
            or self.channels != 1
            or not 8000 <= self.sample_rate <= 48000
        ):
            raise SpeechError("invalid_audio_format")
        if not self.pcm or len(self.pcm) % 2 or len(self.pcm) > self.sample_rate * 2 * 60:
            raise SpeechError("invalid_audio_size")

    @property
    def sample_count(self):
        return len(self.pcm) // 2

    @property
    def duration(self):
        return self.sample_count / self.sample_rate


@dataclass(frozen=True)
class Transcription:
    session_id: UUID
    request_id: UUID
    text: str = field(repr=False)
    language: str | None = None
    duration: float = 0
    latency_ms: float = 0
    model: str = "faster_whisper"
    final: bool = True


def notification(alarm=False):
    rate, duration = 16000, 1.2 if alarm else 0.16
    values = bytearray()
    count = int(rate * duration)
    for index in range(count):
        frequency = 880 if not alarm or (index // 4000) % 2 == 0 else 660
        envelope = min(1, index / 320, (count - index) / 320)
        sample = round(math.sin(2 * math.pi * frequency * index / rate) * 10000 * envelope)
        values.extend(struct.pack("<h", sample))
    return SpeechAudio(bytes(values), rate)
