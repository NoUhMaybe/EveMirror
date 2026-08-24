import io
import math
import re
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Sequence, Tuple

import numpy as np
import sounddevice as sd
from piper import PiperVoice, SynthesisConfig


@dataclass
class LocalTTSConfig:
    model_path: Path
    speaker_id: int = 0
    length_scale: float = 1.06
    noise_scale: float = 0.58
    noise_w_scale: float = 0.82
    volume: float = 0.95
    use_cuda: bool = False


class LocalTTS:
    def __init__(self, config: LocalTTSConfig):
        self.config = config
        self.voice = PiperVoice.load(str(config.model_path), use_cuda=config.use_cuda)

    def _synthesize_audio(self, text: str) -> Tuple[np.ndarray, int]:
        synth_cfg = SynthesisConfig(
            speaker_id=self.config.speaker_id,
            length_scale=self.config.length_scale,
            noise_scale=self.config.noise_scale,
            noise_w_scale=self.config.noise_w_scale,
        )

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav_file:
            self.voice.synthesize_wav(text, wav_file, syn_config=synth_cfg)

        buf.seek(0)
        with wave.open(buf, "rb") as wav_file:
            sample_rate = wav_file.getframerate()
            channels = wav_file.getnchannels()
            frames = wav_file.readframes(wav_file.getnframes())

        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767.0
        if channels > 1:
            audio = audio.reshape(-1, channels).mean(axis=1)

        audio = np.clip(audio * self.config.volume, -1.0, 1.0)
        return audio, sample_rate

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"\S+", text)

    def _word_time_ranges(self, words: Sequence[str], duration_s: float) -> List[Tuple[float, float]]:
        if not words:
            return []

        weights = []
        for w in words:
            stripped = re.sub(r"[^A-Za-z0-9]", "", w)
            weights.append(max(1, len(stripped)))

        total = float(sum(weights))
        out: List[Tuple[float, float]] = []
        cursor = 0.0
        for wt in weights:
            span = duration_s * (wt / total)
            start = cursor
            end = cursor + span
            out.append((start, end))
            cursor = end

        if out:
            start, _ = out[-1]
            out[-1] = (start, duration_s)

        return out

    def _audio_levels(self, audio: np.ndarray, sample_rate: int, frame_ms: int = 30) -> List[Tuple[float, float]]:
        if len(audio) == 0:
            return []

        frame_samples = max(1, int(sample_rate * frame_ms / 1000.0))
        levels: List[Tuple[float, float]] = []
        max_rms = 1e-6

        for start in range(0, len(audio), frame_samples):
            end = min(len(audio), start + frame_samples)
            frame = audio[start:end]
            if len(frame) == 0:
                continue
            rms = float(np.sqrt(np.mean(np.square(frame))))
            max_rms = max(max_rms, rms)
            t_s = start / float(sample_rate)
            levels.append((t_s, rms))

        out: List[Tuple[float, float]] = []
        for t_s, rms in levels:
            # Keep low levels visible while avoiding saturation on peaks.
            norm = min(1.0, (rms / max_rms) ** 0.65)
            out.append((t_s, norm))

        return out

    def _audio_bands(
        self,
        audio: np.ndarray,
        sample_rate: int,
        frame_ms: int = 30,
        low_hz: float = 85.0,
        split_hz: float = 260.0,
        high_hz: float = 3200.0,
    ) -> List[Tuple[float, float, float]]:
        if len(audio) == 0:
            return []

        frame_samples = max(64, int(sample_rate * frame_ms / 1000.0))
        if frame_samples % 2 == 1:
            frame_samples += 1

        freqs = np.fft.rfftfreq(frame_samples, d=1.0 / float(sample_rate))
        low_mask = (freqs >= low_hz) & (freqs < split_hz)
        high_mask = (freqs >= split_hz) & (freqs <= high_hz)

        bands: List[Tuple[float, float, float]] = []
        max_low = 1e-6
        max_high = 1e-6
        window = np.hanning(frame_samples).astype(np.float32)

        for start in range(0, len(audio), frame_samples):
            frame = audio[start:start + frame_samples]
            if len(frame) < frame_samples:
                padded = np.zeros(frame_samples, dtype=np.float32)
                padded[: len(frame)] = frame
                frame = padded

            spectrum = np.fft.rfft(frame * window)
            power = np.abs(spectrum)

            low_power = float(np.mean(power[low_mask])) if np.any(low_mask) else 0.0
            high_power = float(np.mean(power[high_mask])) if np.any(high_mask) else 0.0
            max_low = max(max_low, low_power)
            max_high = max(max_high, high_power)

            t_s = start / float(sample_rate)
            bands.append((t_s, low_power, high_power))

        out: List[Tuple[float, float, float]] = []
        for t_s, low_power, high_power in bands:
            low_norm = min(1.0, math.pow(low_power / max_low, 0.6)) if max_low > 0 else 0.0
            high_norm = min(1.0, math.pow(high_power / max_high, 0.6)) if max_high > 0 else 0.0
            out.append((t_s, low_norm, high_norm))

        return out

    def speak(self, text: str, emit_event: Callable[[str, dict], None]) -> None:
        text = (text or "").strip()
        if not text:
            return

        audio, sample_rate = self._synthesize_audio(text)
        duration_s = float(len(audio)) / float(sample_rate)

        words = self._tokenize(text)
        word_ranges = self._word_time_ranges(words, duration_s)
        level_ranges = self._audio_levels(audio, sample_rate)
        band_ranges = self._audio_bands(audio, sample_rate)

        emit_event("subtitle_prepare", {"text": text, "words": words})
        emit_event("state_change", {"state": "SPEAKING", "duration_s": duration_s})

        sd.play(audio, samplerate=sample_rate, blocking=False)
        t0 = time.monotonic()

        next_word = 0
        next_level = 0
        next_band = 0
        while next_word < len(word_ranges) or next_level < len(level_ranges) or next_band < len(band_ranges):
            elapsed = time.monotonic() - t0
            if next_word < len(word_ranges):
                start, _ = word_ranges[next_word]
                if elapsed >= start:
                    emit_event("subtitle_progress", {"word_index": next_word, "elapsed_s": elapsed})
                    next_word += 1
            while next_level < len(level_ranges) and elapsed >= level_ranges[next_level][0]:
                emit_event("tts_audio_level", {"level": level_ranges[next_level][1], "elapsed_s": elapsed})
                next_level += 1
            while next_band < len(band_ranges) and elapsed >= band_ranges[next_band][0]:
                _, low_level, high_level = band_ranges[next_band]
                emit_event(
                    "tts_audio_bands",
                    {"low": low_level, "high": high_level, "elapsed_s": elapsed},
                )
                next_band += 1
            time.sleep(0.01)

        sd.wait()
        emit_event("tts_audio_level", {"level": 0.0, "elapsed_s": duration_s})
        emit_event("tts_audio_bands", {"low": 0.0, "high": 0.0, "elapsed_s": duration_s})
        emit_event("subtitle_done", {"text": text})
