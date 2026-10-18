"""Lazy PortAudio adapters and stateful band-limited rate conversion."""

import asyncio
import queue
import threading
import time

from packages.audio import SpeechError


def select_device(name, kind):
    import sounddevice as sd

    if name is None:
        return None
    if name.startswith("index:"):
        return int(name[6:])
    available = sd.query_devices()
    matches = [
        index
        for index, item in enumerate(available)
        if item["max_" + kind + "_channels"] > 0 and item["name"] == name
    ]
    if len(matches) != 1:
        raise SpeechError("audio_device_ambiguous_or_missing")
    return matches[0]


class Resampler:
    def __init__(self, input_rate, gain=1):
        import soxr

        self.gain, self.input_rate = gain, input_rate
        self.lock = threading.Lock()
        self.stream = soxr.ResampleStream(input_rate, 16000, 1, dtype="float32", quality="HQ")

    def feed(self, samples, final=False):
        import numpy as np

        samples = np.asarray(samples, dtype=np.float32)
        if samples.ndim == 2:
            samples = samples.mean(axis=1, dtype=np.float32)
        if samples.ndim != 1 or len(samples) > self.input_rate:
            raise SpeechError("invalid_capture_frame")
        samples = np.clip(np.nan_to_num(samples) * self.gain, -1, 1)
        with self.lock:
            output = self.stream.resample_chunk(samples, last=final)
        return np.clip(output * 32767, -32768, 32767).astype("<i2").tobytes()

    def clear(self):
        with self.lock:
            self.stream.clear()


class SoundInput:
    def __init__(self, settings):
        self.settings = settings
        self.queue = queue.Queue(maxsize=settings.queue_blocks)
        self.overrun = threading.Event()
        self.converter = None
        self.available = False
        self.generation = 0
        self.suppressed = False
        self.last_callback = time.monotonic()

    def suppress(self, value):
        self.suppressed = value
        self.flush()

    def flush(self):
        self.generation += 1
        while True:
            try:
                self.queue.get_nowait()
            except queue.Empty:
                break
        if self.converter:
            self.converter.clear()

    async def frames(self):
        import sounddevice as sd

        device = await asyncio.to_thread(select_device, self.settings.input_device, "input")
        info = await asyncio.to_thread(sd.query_devices, device, "input")
        rate = self.settings.capture_rate or round(info["default_samplerate"])
        self.converter = Resampler(rate, self.settings.gain)
        self.flush()

        def callback(data, frames, timing, status):
            self.last_callback = time.monotonic()
            if status or frames > rate // 10:
                self.overrun.set()
                return
            if self.suppressed:
                return  # Do not copy, queue or resample muted/busy microphone samples.
            try:
                generation = self.generation
                self.queue.put_nowait((data.copy(), generation))
            except queue.Full:
                self.overrun.set()

        stream = None
        try:
            stream = await asyncio.to_thread(
                sd.InputStream,
                samplerate=rate,
                device=device,
                channels=self.settings.capture_channels,
                dtype="float32",
                blocksize=max(1, rate // 50),
                callback=callback,
            )
            await asyncio.to_thread(stream.start)
            self.available = True
            self.last_callback = time.monotonic()
            while True:
                if self.overrun.is_set():
                    self.overrun.clear()
                    self.flush()
                    raise SpeechError("capture_overrun")
                try:
                    frame, generation = await asyncio.to_thread(self.queue.get, True, 0.25)
                except queue.Empty:
                    if not stream.active or time.monotonic() - self.last_callback > 2:
                        raise SpeechError("microphone_unavailable") from None
                    continue
                if generation != self.generation:
                    continue
                converted = await asyncio.to_thread(self.converter.feed, frame)
                if converted and generation == self.generation:
                    yield converted
        finally:
            self.available = False
            if stream is not None:
                await asyncio.to_thread(stream.abort)
                await asyncio.to_thread(stream.close)
            self.flush()


class SoundOutput:
    def __init__(self, settings):
        self.settings = settings
        self.available = False

    def play(self, audio, stopped, started, progress):
        import numpy as np
        import sounddevice as sd
        import soxr

        device = select_device(self.settings.output_device, "output")
        info = sd.query_devices(device, "output")
        rate = self.settings.output_rate or round(info["default_samplerate"])
        if not 8000 <= rate <= 96000:
            raise SpeechError("unsupported_output_rate")
        data = np.frombuffer(audio.pcm, dtype="<i2").astype(np.float32) / 32768
        if rate != audio.sample_rate:
            data = soxr.resample(data, audio.sample_rate, rate, quality="HQ")
        data = np.clip(data * self.settings.volume, -1, 1).astype(np.float32)
        stream = None
        try:
            stream = sd.OutputStream(device=device, samplerate=rate, channels=1, dtype="float32")
            stream.start()
            self.available = True
            if stopped.is_set():
                return
            started()
            step, reported = max(1, rate // 50), 0
            for offset in range(0, len(data), step):
                if stopped.is_set():
                    stream.abort()
                    return
                if stream.write(data[offset : offset + step]):
                    raise SpeechError("playback_underflow")
                written = min(offset + step, len(data))
                if written - reported >= rate // 5 or written == len(data):
                    progress(round(written / rate * audio.sample_rate))
                    reported = written
            stream.stop()  # Drain the driver's final buffer before completion.
            progress(audio.sample_count)
        except Exception:
            self.available = False
            raise
        finally:
            if stream is not None:
                stream.close()
