"""One recording state machine. Input is always mono little-endian PCM16/16 kHz."""

import math
import struct
import time
from collections import deque

from packages.assets import AssetCatalog
from packages.audio import SpeechError


class WakeVAD:
    """ONNX openWakeWord and Silero v5/v6-style recurrent state, without Torch."""

    def __init__(self, settings):
        import numpy as np
        import onnxruntime as ort
        from openwakeword.model import Model

        if settings.asset_manifest is None:
            raise SpeechError("wake_assets_unconfigured")
        catalog = AssetCatalog(settings.asset_manifest, settings.asset_root)
        paths = {
            key: catalog.path(key)
            for key in ("wake_word", "melspectrogram", "embedding", "silero_vad")
        }
        self.wake = Model(
            wakeword_models=[str(paths["wake_word"])],
            inference_framework="onnx",
            melspec_model_path=str(paths["melspectrogram"]),
            embedding_model_path=str(paths["embedding"]),
        )
        options = ort.SessionOptions()
        options.inter_op_num_threads = options.intra_op_num_threads = 1
        self.vad = ort.InferenceSession(
            str(paths["silero_vad"]), options, providers=["CPUExecutionProvider"]
        )
        if {item.name for item in self.vad.get_inputs()} != {"input", "state", "sr"}:
            raise SpeechError("unsupported_vad_model")
        self.np = np
        self.reset()

    def reset(self):
        self.wake.reset()
        self.state = self.np.zeros((2, 1, 128), dtype=self.np.float32)
        self.context = self.np.zeros((1, 64), dtype=self.np.float32)

    def wake_score(self, pcm):
        result = self.wake.predict(self.np.frombuffer(pcm, dtype="<i2"))
        return max((float(value) for value in result.values()), default=0)

    def vad_score(self, pcm):
        samples = self.np.frombuffer(pcm, dtype="<i2").astype(self.np.float32)[None, :] / 32768
        if samples.shape != (1, 512):
            raise SpeechError("invalid_vad_frame")
        frame = self.np.concatenate((self.context, samples), axis=1)
        output, self.state = self.vad.run(
            None, {"input": frame, "state": self.state, "sr": self.np.array(16000, dtype="int64")}
        )
        self.context = frame[:, -64:]
        return float(output.reshape(-1)[0])


class CaptureMachine:
    def __init__(self, settings, detector, clock=time.monotonic):
        self.settings, self.detector, self.clock = settings, detector, clock
        self.state = "IDLE"
        self.muted, self.busy = False, False
        self.suppressed_until = 0
        self.follow_until = 0
        self.last_wake = float("-inf")
        self.buffer = bytearray()
        self.wake_buffer = bytearray()
        self.pre_roll = deque(maxlen=math.ceil(settings.pre_roll_ms / 32))
        self.recording = bytearray()
        self.speech_ms = self.silence_ms = self.hits = 0
        self.listen_started = 0
        self.last_rms = 0.0
        self.metrics = {}
        self.blocked = False

    def clear(self):
        self.last_rms = 0.0
        self.buffer.clear()
        self.wake_buffer.clear()
        self.pre_roll.clear()
        self.recording.clear()
        self.speech_ms = self.silence_ms = self.hits = 0
        self.detector.reset()

    def listen(self, follow_up=False):
        self.clear()
        self.listen_started = self.clock()
        self.state = "FOLLOW_UP" if follow_up else "LISTENING"

    def feed(self, pcm):
        if len(pcm) % 2 or len(pcm) > 32000:
            raise SpeechError("invalid_capture_frame")
        if self.muted or self.busy or self.clock() < self.suppressed_until:
            if not self.blocked:
                self.clear()
            self.blocked = True
            return []
        self.blocked = False
        if self.state == "FOLLOW_UP" and self.clock() >= self.follow_until:
            self.clear()
            self.state = "IDLE"
        self.buffer.extend(pcm)
        events = []
        while len(self.buffer) >= 1024:
            frame = bytes(self.buffer[:1024])
            del self.buffer[:1024]
            vad_started = time.monotonic()
            probability = self.detector.vad_score(frame)
            self.metrics["vad_inference_ms"] = (time.monotonic() - vad_started) * 1000
            samples = struct.unpack("<512h", frame)
            rms = math.sqrt(sum(value * value for value in samples) / 512) / 32768
            self.last_rms = rms
            speech = probability >= self.settings.vad_threshold and rms >= 0.008
            if self.state == "IDLE":
                self.wake_buffer.extend(frame)
                while len(self.wake_buffer) >= 2560:
                    window = bytes(self.wake_buffer[:2560])
                    del self.wake_buffer[:2560]
                    inference_started = time.monotonic()
                    positive = self.detector.wake_score(window) >= self.settings.wake_threshold
                    self.metrics["wake_inference_ms"] = (
                        time.monotonic() - inference_started
                    ) * 1000
                    self.hits = self.hits + 1 if positive and speech else 0
                    if (
                        self.hits >= self.settings.wake_hits
                        and self.clock() - self.last_wake >= self.settings.wake_cooldown
                    ):
                        self.last_wake = self.clock()
                        self.clear()
                        self.state = "WAKE_DETECTED"
                        return [("wake", None)]
                continue
            if self.state not in {"LISTENING", "FOLLOW_UP"}:
                continue
            if not self.recording:
                if not speech:
                    self.pre_roll.append(frame)
                    if (
                        self.state == "LISTENING"
                        and self.clock() - self.listen_started >= self.settings.initial_timeout
                    ):
                        self.clear()
                        self.state = "IDLE"
                        return [("empty", None)]
                    continue
                if self.state == "FOLLOW_UP":
                    self.state = "LISTENING"
                    self.listen_started = self.clock()
                    events.append(("speech_started", None))
                self.recording.extend(b"".join(self.pre_roll))
                self.pre_roll.clear()
            self.recording.extend(frame)
            self.speech_ms += 32 if speech else 0
            self.silence_ms = 0 if speech else self.silence_ms + 32
            full = len(self.recording) >= int(self.settings.max_utterance_seconds * 32000)
            ended = self.silence_ms >= self.settings.silence_ms
            if ended or full:
                if self.speech_ms >= self.settings.min_speech_ms:
                    audio = bytes(
                        self.recording[: int(self.settings.max_utterance_seconds * 32000) // 2 * 2]
                    )
                    self.clear()
                    self.busy, self.state = True, "UPLOADING"
                    return events + [("utterance", audio)]
                self.recording.clear()
                self.speech_ms = self.silence_ms = 0
        return events
