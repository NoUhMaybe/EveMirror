import asyncio
import hashlib
import json
import sys
import threading
from types import SimpleNamespace
from uuid import uuid4

import pytest

from apps.config import SpeechSettings
from apps.server.audio import CompletedAudio
from apps.server.speech.providers import FasterWhisper, ModelWorker, Piper
from packages.audio import SpeechAudio, SpeechError


def audio():
    return CompletedAudio("mirror-1", uuid4(), uuid4(), b"\x01\x00" * 1600)


def assets(tmp_path):
    files = {
        "piper_voice": "voice.onnx",
        "piper_config": "voice.onnx.json",
        "whisper_weights": "whisper/model.bin",
        "whisper_config": "whisper/config.json",
        "whisper_tokenizer": "whisper/tokenizer.json",
    }
    entries = {}
    for key, relative in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(
            b'{"phoneme_type":"espeak"}'
            if key == "piper_config"
            else b"isolated binding fixture " + key.encode()
        )
        entries[key] = {"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    manifest = tmp_path / "assets.json"
    manifest.write_text(json.dumps(entries))
    return SpeechSettings(enabled=True, asset_root=tmp_path, asset_manifest=manifest)


async def test_cpu_int8_whisper_reuses_verified_local_model_and_returns_real_engine_metadata(
    tmp_path, monkeypatch
):
    loads, arguments = [], []

    class Whisper:
        def __init__(self, path, **kwargs):
            loads.append((path, kwargs))

        def transcribe(self, samples, **kwargs):
            assert samples.dtype.name == "float32" and len(samples) == 1600
            arguments.append(kwargs)
            return iter(
                [SimpleNamespace(text=" turn off"), SimpleNamespace(text=" bedroom lights ")]
            ), SimpleNamespace(language="en")

    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=Whisper))
    provider = FasterWhisper(assets(tmp_path))
    try:
        fixture = audio()
        result = await provider.transcribe(fixture)
        assert result.text == "turn off bedroom lights" and result.language == "en"
        assert result.duration == 0.1 and result.final and result.latency_ms >= 0
        assert result.session_id == fixture.session_id and result.request_id == fixture.request_id
        await provider.transcribe(audio())
        assert len(loads) == 1
        assert loads[0][1]["device"] == "cpu" and loads[0][1]["compute_type"] == "int8"
        assert loads[0][1]["local_files_only"] and arguments[0]["vad_filter"] is False
    finally:
        await provider.close()


async def test_whisper_missing_assets_failed_load_backoff_blank_and_bad_audio(
    tmp_path, monkeypatch
):
    provider = FasterWhisper(assets(tmp_path))
    count = []

    def fail(catalog):
        count.append(1)
        raise RuntimeError("private-model-path")

    monkeypatch.setattr(provider, "_load", fail)
    try:
        for _ in range(2):
            with pytest.raises(SpeechError, match="speech_model_unavailable"):
                await provider.transcribe(audio())
        assert len(count) == 1 and provider.status()["error"] == "speech_model_unavailable"
        with pytest.raises(SpeechError, match="invalid_audio"):
            await provider.transcribe(CompletedAudio("mirror-1", uuid4(), uuid4(), b"odd", 48000))
        provider.model = SimpleNamespace(
            transcribe=lambda *args, **kwargs: (iter([]), SimpleNamespace(language="en"))
        )
        with pytest.raises(SpeechError, match="empty_transcript"):
            await provider.transcribe(audio())
    finally:
        await provider.close()


async def test_worker_timeout_and_cancellation_hold_the_slot_until_native_work_exits():
    worker = ModelWorker()
    entered, release = threading.Event(), threading.Event()

    def operation(cancelled):
        entered.set()
        assert release.wait(3)
        return cancelled.is_set()

    try:
        with pytest.raises(SpeechError, match="speech_timeout"):
            await worker.run(operation, 0.03)
        assert entered.is_set()
        with pytest.raises(SpeechError, match="speech_busy"):
            await worker.run(lambda _: None, 1)
        previous = worker.task
        release.set()
        await worker.close()
        assert previous.result() is True
        assert worker.task is None
        release.clear()
        entered.clear()
        task = asyncio.create_task(worker.run(operation, 2))
        assert await asyncio.to_thread(entered.wait, 1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not worker.task.done()
        with pytest.raises(SpeechError, match="speech_busy"):
            await worker.run(lambda _: None, 1)
    finally:
        release.set()
        await worker.close()
    assert await worker.run(lambda _: 42, 1) == 42
    await worker.close()


async def test_piper_reuses_verified_voice_and_produces_bounded_audio_without_playback(
    tmp_path, monkeypatch
):
    loads, configs, texts = [], [], []

    class Voice:
        @staticmethod
        def load(path, **kwargs):
            loads.append((path, kwargs))
            return Voice()

        def synthesize(self, text, syn_config):
            texts.append(text)
            yield SimpleNamespace(
                sample_rate=24000,
                sample_width=2,
                sample_channels=1,
                audio_int16_bytes=b"\x04\x00" * 2400,
            )

    def config(**kwargs):
        configs.append(kwargs)
        return kwargs

    monkeypatch.setitem(
        sys.modules, "piper", SimpleNamespace(PiperVoice=Voice, SynthesisConfig=config)
    )
    settings = assets(tmp_path)
    provider = Piper(settings)
    try:
        result = await provider.synthesize("An actual engine-bound result.")
        assert result.sample_rate == 24000 and result.channels == 1
        assert result.sample_count == 2400 and result.duration == 0.1
        await provider.synthesize("A follow-up response.")
        assert len(loads) == 1 and loads[0][1]["use_cuda"] is False
        assert loads[0][1]["config_path"].endswith("voice.onnx.json")
        assert configs[0]["speaker_id"] == settings.speaker_id
        await provider.synthesize("word " * 150)
        assert all(len(text) <= 300 for text in texts)
        settings.max_text = 100
        with pytest.raises(SpeechError, match="invalid_synthesis_text"):
            await provider.synthesize("x" * 101)
        provider.model = SimpleNamespace(
            synthesize=lambda *args, **kwargs: iter(
                [
                    SimpleNamespace(
                        sample_rate=8000,
                        sample_width=2,
                        sample_channels=1,
                        audio_int16_bytes=b"\x00\x00" * 8001,
                    )
                ]
            )
        )
        settings.max_response_seconds = 1
        with pytest.raises(SpeechError, match="synthesis_too_long"):
            await provider.synthesize("bounded")
    finally:
        await provider.close()


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(pcm=b""),
        dict(pcm=b"odd"),
        dict(pcm=b"00", sample_rate=96000),
        dict(pcm=b"00", channels=2),
        dict(pcm=b"00", encoding="mp3"),
        dict(pcm=b"00", sample_rate=22050.5),
    ],
)
def test_invalid_output_audio_is_rejected(kwargs):
    with pytest.raises(SpeechError):
        SpeechAudio(**kwargs)
