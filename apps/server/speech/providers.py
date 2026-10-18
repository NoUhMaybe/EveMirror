"""Local CPU engines with one retained worker per model, never cloud audio."""

import asyncio
import json
import threading
import time
from typing import Protocol

from apps.server.audio import CompletedAudio
from packages.assets import AssetCatalog
from packages.audio import SpeechAudio, SpeechError, Transcription


class SpeechToTextProvider(Protocol):
    async def transcribe(self, audio: CompletedAudio) -> Transcription: ...
    async def close(self): ...


class TextToSpeechProvider(Protocol):
    async def synthesize(self, text: str) -> SpeechAudio: ...
    async def close(self): ...


class ModelWorker:
    """Timeout discards work; the occupied slot stays owned until native work exits."""

    def __init__(self):
        self.task = None
        self.cancelled = None

    async def run(self, function, duration):
        if self.task and not self.task.done():
            raise SpeechError("speech_busy")
        cancelled = threading.Event()
        self.cancelled = cancelled
        self.task = asyncio.create_task(asyncio.to_thread(function, cancelled))

        def finished(task):
            if not task.cancelled():
                task.exception()
            # Completed task results may contain transcripts/PCM. Do not retain them.
            if self.task is task:
                self.task = None

        self.task.add_done_callback(finished)
        try:
            return await asyncio.wait_for(asyncio.shield(self.task), duration)
        except TimeoutError:
            cancelled.set()
            raise SpeechError("speech_timeout") from None
        except asyncio.CancelledError:
            cancelled.set()
            raise

    async def close(self):
        if self.cancelled:
            self.cancelled.set()
        if self.task:
            # Native inference is not forcibly killable; retain ownership to completion.
            await asyncio.shield(self.task)


class LocalEngine:
    def __init__(self, settings):
        self.settings = settings
        self.worker = ModelWorker()
        self.model = None
        self.error = None
        self.failed_until = 0

    def catalog(self):
        if not self.settings.enabled or self.settings.asset_manifest is None:
            raise SpeechError("speech_unconfigured")
        return AssetCatalog(self.settings.asset_manifest, self.settings.asset_root)

    def load(self, loader):
        if self.model is not None:
            return self.model
        if time.monotonic() < self.failed_until:
            raise SpeechError("speech_model_unavailable")
        try:
            self.model = loader(self.catalog())
            self.error = None
            return self.model
        except Exception:
            self.failed_until = time.monotonic() + 60
            self.error = "speech_model_unavailable"
            raise SpeechError(self.error) from None

    def status(self):
        return {
            "configured": self.settings.enabled and self.settings.asset_manifest is not None,
            "ready": self.model is not None,
            "error": self.error,
            "busy": bool(self.worker.task and not self.worker.task.done()),
        }

    async def close(self):
        try:
            await self.worker.close()
        except Exception:
            pass
        self.model = None


class FasterWhisper(LocalEngine):
    def _load(self, catalog):
        from faster_whisper import WhisperModel

        directory = catalog.directory(self.settings.stt_model_directory)
        if not all(
            (directory / name).is_file() for name in ("model.bin", "config.json", "tokenizer.json")
        ):
            raise SpeechError("speech_model_unavailable")
        return WhisperModel(
            str(directory),
            device="cpu",
            compute_type="int8",
            cpu_threads=self.settings.cpu_threads,
            num_workers=1,
            local_files_only=True,
        )

    async def transcribe(self, audio):
        if (
            audio.sample_rate != 16000
            or not audio.pcm
            or len(audio.pcm) % 2
            or len(audio.pcm) > 960000
        ):
            raise SpeechError("invalid_audio_format")

        def execute(cancelled):
            import numpy as np

            started = time.monotonic()
            model = self.load(self._load)
            if cancelled.is_set():
                raise SpeechError("speech_cancelled")
            samples = np.frombuffer(audio.pcm, dtype="<i2").astype(np.float32) / 32768
            segments, info = model.transcribe(
                samples,
                language=self.settings.stt_language,
                beam_size=1,
                vad_filter=False,
                condition_on_previous_text=False,
            )
            parts, size = [], 0
            for segment in segments:
                if cancelled.is_set():
                    raise SpeechError("speech_cancelled")
                size += len(segment.text.encode("utf-8"))
                if size > 16000:
                    raise SpeechError("transcript_too_long")
                parts.append(segment.text)
            text = "".join(parts).strip()
            if not text:
                raise SpeechError("empty_transcript")
            return Transcription(
                audio.session_id,
                audio.request_id,
                text,
                info.language,
                len(audio.pcm) / 32000,
                (time.monotonic() - started) * 1000,
            )

        try:
            return await self.worker.run(execute, self.settings.stt_timeout)
        except SpeechError:
            raise
        except Exception:
            self.error = "transcription_failed"
            raise SpeechError(self.error) from None


class Piper(LocalEngine):
    def _load(self, catalog):
        from piper import PiperVoice

        config_path = catalog.path("piper_config")
        if config_path.stat().st_size > 1_000_000:
            raise SpeechError("unsupported_voice_config")
        config = json.loads(config_path.read_text(encoding="utf-8"))
        if config.get("phoneme_type", "espeak") not in {"espeak", "text"}:
            raise SpeechError("unsupported_voice_resources")
        voice = PiperVoice.load(
            str(catalog.path("piper_voice")),
            config_path=str(config_path),
            use_cuda=False,
        )
        # Extra diacritization/phonemizer models must never be downloaded at runtime.
        voice.use_tashkeel = False
        return voice

    async def synthesize(self, text):
        if not isinstance(text, str) or not text.strip() or len(text) > self.settings.max_text:
            raise SpeechError("invalid_synthesis_text")

        def execute(cancelled):
            from piper import SynthesisConfig

            voice = self.load(self._load)
            config = SynthesisConfig(
                speaker_id=self.settings.speaker_id,
                length_scale=self.settings.length_scale,
                noise_scale=self.settings.noise_scale,
                noise_w_scale=self.settings.noise_w_scale,
            )
            pcm, rate = bytearray(), None
            remaining = text.strip()
            while remaining:
                end = len(remaining) if len(remaining) <= 300 else remaining.rfind(" ", 0, 301)
                if end <= 0:
                    end = min(300, len(remaining))
                part, remaining = remaining[:end], remaining[end:].lstrip()
                for chunk in voice.synthesize(part, syn_config=config):
                    if cancelled.is_set():
                        raise SpeechError("speech_cancelled")
                    if chunk.sample_channels != 1 or chunk.sample_width != 2:
                        raise SpeechError("invalid_audio_format")
                    if rate is not None and rate != chunk.sample_rate:
                        raise SpeechError("invalid_audio_format")
                    rate = chunk.sample_rate
                    data = chunk.audio_int16_bytes
                    if len(pcm) + len(data) > rate * 2 * self.settings.max_response_seconds:
                        raise SpeechError("synthesis_too_long")
                    pcm.extend(data)
            return SpeechAudio(bytes(pcm), rate or 22050)

        try:
            return await self.worker.run(execute, self.settings.tts_timeout)
        except SpeechError:
            raise
        except Exception:
            self.error = "synthesis_failed"
            raise SpeechError(self.error) from None
