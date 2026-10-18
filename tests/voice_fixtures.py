"""Deterministic audio/model fixtures. No real capture, synthesis or speaker output."""

import asyncio
import struct
import time
from collections import deque

from packages.audio import SpeechAudio, Transcription

SPEECH_FRAME = struct.pack("<512h", *([2000, -2000] * 256))
WAKE_FRAME = struct.pack("<512h", *([30000, -30000] * 256))
SILENCE_FRAME = bytes(1024)


class Detector:
    def __init__(self):
        self.wakes = self.vads = 0

    def reset(self):
        pass

    def wake_score(self, pcm):
        self.wakes += 1
        return 1.0 if abs(struct.unpack("<h", pcm[:2])[0]) == 30000 else 0.0

    def vad_score(self, pcm):
        self.vads += 1
        return 1.0 if any(pcm) else 0.0


class Microphone:
    def __init__(self):
        self.queue = asyncio.Queue(maxsize=32)
        self.available = False
        self.closed = 0

    async def frames(self):
        self.available = True
        try:
            while True:
                frame = await self.queue.get()
                if isinstance(frame, Exception):
                    raise frame
                yield frame
        finally:
            self.available = False
            self.closed += 1

    def flush(self):
        while not self.queue.empty():
            self.queue.get_nowait()

    async def emit(self, frame, count):
        for _ in range(count):
            await self.queue.put(frame)


class Speaker:
    def __init__(self):
        self.calls, self.completed, self.cancelled = [], [], []
        self.available = True
        self.block = False
        self.fail = False

    def play(self, audio, stop, started, progress):
        self.calls.append(audio)
        if self.fail:
            raise OSError("fixture speaker disconnected")
        started()
        while self.block and not stop.is_set():
            time.sleep(0.005)
        if stop.is_set():
            self.cancelled.append(audio)
            return
        progress(audio.sample_count)
        self.completed.append(audio)


class STT:
    def __init__(self, *texts):
        self.texts, self.calls = deque(texts), []
        self.wait = None

    async def transcribe(self, audio):
        self.calls.append(audio)
        if self.wait:
            await self.wait.wait()
        return Transcription(
            audio.session_id,
            audio.request_id,
            self.texts.popleft(),
            "en",
            len(audio.pcm) / 32000,
            1,
        )

    async def close(self):
        pass


class TTS:
    def __init__(self):
        self.calls = []

    async def synthesize(self, text):
        self.calls.append(text)
        return SpeechAudio(b"\x03\x00" * 12000, 22050)

    async def close(self):
        pass


async def say(runtime, microphone, *, wake=True):
    from tests.test_edge_integration import until

    if wake:
        remaining = max(
            0,
            runtime.voice.machine.last_wake
            + runtime.settings.voice.wake_cooldown
            - runtime.voice.clock(),
            runtime.voice.machine.suppressed_until - runtime.voice.clock(),
        )
        await asyncio.sleep(remaining + 0.01)
        await microphone.emit(WAKE_FRAME, 5)
        await until(lambda: runtime.voice.machine.state == "LISTENING")
    await asyncio.sleep(0.12)  # Configured software echo tail; no real acoustics.
    await microphone.emit(SPEECH_FRAME, 8)
    await microphone.emit(SILENCE_FRAME, 6)
