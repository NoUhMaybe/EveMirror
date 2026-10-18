import hashlib
import json
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from apps.config import EdgeVoiceSettings
from apps.edge.voice.capture import CaptureMachine, WakeVAD
from apps.edge.voice.io import Resampler, SoundInput, select_device
from packages.assets import AssetCatalog
from packages.audio import SpeechError
from tests.voice_fixtures import SILENCE_FRAME, SPEECH_FRAME, WAKE_FRAME, Detector


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def machine(**changes):
    config = EdgeVoiceSettings(min_speech_ms=160, silence_ms=160, wake_hits=1, **changes)
    clock = Clock()
    return CaptureMachine(config, Detector(), clock), clock


@pytest.mark.parametrize("rate", [16000, 44100, 48000])
def test_streaming_resampling_keeps_duration_and_filters_aliasing(rate):
    times = np.arange(rate, dtype=np.float32) / rate
    signal = (
        0.2 * np.sin(2 * np.pi * 500 * times) + 0.2 * np.sin(2 * np.pi * 15000 * times)
    ).astype(np.float32)
    # Stereo conversion must average channels before the sample-rate converter.
    stereo = np.column_stack((signal, signal))
    converter = Resampler(rate)
    chunks = [
        converter.feed(stereo[start : start + rate // 50]) for start in range(0, rate, rate // 50)
    ]
    chunks.append(converter.feed(np.zeros((0, 2), dtype=np.float32), final=True))
    samples = np.frombuffer(b"".join(chunks), dtype="<i2")
    assert len(samples) == 16000
    if rate > 16000:
        spectrum = abs(np.fft.rfft(samples[1600:-1600]))
        assert spectrum[400] > spectrum[800] * 100  # 500 Hz vs the rejected 1 kHz alias
    opposite = Resampler(rate)
    silence = opposite.feed(np.column_stack((signal, -signal)), final=True)
    assert not np.any(np.frombuffer(silence, dtype="<i2"))


def test_capture_wake_vad_trailing_silence_repeat_and_followup():
    capture, clock = machine()
    assert capture.feed(WAKE_FRAME * 3) == [("wake", None)]
    assert capture.feed(WAKE_FRAME * 3) == []  # no second recording from another wake
    capture.listen()
    assert capture.feed(SPEECH_FRAME * 8) == []
    events = capture.feed(SILENCE_FRAME * 5)
    assert events[0][0] == "utterance" and events[0][1].startswith(SPEECH_FRAME)
    assert capture.busy and capture.feed(WAKE_FRAME * 3) == []
    capture.busy = False
    capture.listen(follow_up=True)
    capture.follow_until = clock.now + 60
    capture.feed(SPEECH_FRAME * 8)
    assert capture.feed(SILENCE_FRAME * 5)[0][0] == "utterance"


def test_false_wakes_short_noise_empty_timeout_cooldown_mute_and_echo():
    capture, clock = machine()
    capture.settings.wake_hits = 2
    positive = WAKE_FRAME * 2 + WAKE_FRAME[:512]
    negative = SPEECH_FRAME * 2 + SPEECH_FRAME[:512]
    assert capture.feed(positive + negative) == []  # interrupted positive sequence
    assert capture.feed(WAKE_FRAME * 5) == [("wake", None)]
    capture.listen()
    capture.feed(SPEECH_FRAME)
    assert capture.feed(SILENCE_FRAME * 5) == []  # noise shorter than minimum speech
    clock.now += 6
    assert capture.feed(SILENCE_FRAME) == [("empty", None)]
    capture.settings.wake_hits = 1
    capture.muted = True
    assert capture.feed(WAKE_FRAME * 5) == [] and not capture.recording
    capture.muted = False
    capture.suppressed_until = clock.now + 1
    assert capture.feed(WAKE_FRAME * 5) == []
    clock.now += 2
    assert capture.feed(WAKE_FRAME * 3) == [("wake", None)]
    capture.clear()
    capture.state = "IDLE"
    assert capture.feed(WAKE_FRAME * 3) == []  # cooldown from the prior wake


def test_maximum_duration_is_bounded_and_followup_silence_expires():
    capture, clock = machine(max_utterance_seconds=1)
    capture.listen()
    events = []
    for _ in range(32):
        events += capture.feed(SPEECH_FRAME)
    assert len(events[0][1]) == 32000
    capture.busy = False
    capture.listen(follow_up=True)
    capture.follow_until = clock.now + 1
    clock.now += 2
    assert capture.feed(SILENCE_FRAME) == [] and capture.state == "IDLE"


def manifest(tmp_path, names):
    values = {}
    for name in names:
        path = tmp_path / (name + ".bin")
        path.write_bytes(b"isolated model binding fixture " + name.encode())
        values[name] = {"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    target = tmp_path / "manifest.json"
    target.write_text(json.dumps(values))
    return target


def test_verified_onnx_wake_and_silero_bindings_recurrent_context_without_torch(
    tmp_path, monkeypatch
):
    record = {}

    class Wake:
        def __init__(self, **kwargs):
            record["wake_config"] = kwargs

        def reset(self):
            pass

        def predict(self, frame):
            assert frame.dtype == np.int16 and len(frame) == 1280
            return {"hey_eve": 0.9}

    class Session:
        def __init__(self, path, options, providers):
            assert providers == ["CPUExecutionProvider"]

        def get_inputs(self):
            return [SimpleNamespace(name=name) for name in ["input", "state", "sr"]]

        def run(self, outputs, inputs):
            assert inputs["input"].shape == (1, 576) and inputs["state"].shape == (2, 1, 128)
            assert inputs["sr"] == 16000
            record["state"] = inputs["state"].copy()
            return np.array([[0.9]]), inputs["state"] + 1

    monkeypatch.setitem(sys.modules, "openwakeword.model", SimpleNamespace(Model=Wake))
    monkeypatch.setitem(
        sys.modules,
        "onnxruntime",
        SimpleNamespace(SessionOptions=SimpleNamespace, InferenceSession=Session),
    )
    config = EdgeVoiceSettings(
        asset_root=tmp_path,
        asset_manifest=manifest(
            tmp_path, ["wake_word", "melspectrogram", "embedding", "silero_vad"]
        ),
    )
    detector = WakeVAD(config)
    assert detector.wake_score(WAKE_FRAME * 2 + WAKE_FRAME[:512]) == 0.9
    assert detector.vad_score(SPEECH_FRAME) == 0.9
    detector.vad_score(SPEECH_FRAME)
    assert np.all(record["state"] == 1)
    detector.reset()
    detector.vad_score(SPEECH_FRAME)
    assert np.all(record["state"] == 0)
    assert record["wake_config"]["inference_framework"] == "onnx"
    config.asset_manifest.write_text("{}")
    with pytest.raises(ValueError):
        WakeVAD(config)


async def test_microphone_overrun_is_bounded_and_stream_is_closed(monkeypatch):
    streams = []

    class Stream:
        active = True

        def __init__(self, **config):
            self.config = config
            self.closed = False
            streams.append(self)

        def start(self):
            for _ in range(20):
                self.config["callback"](np.zeros((960, 1), dtype=np.float32), 960, None, None)

        def abort(self):
            self.active = False

        def close(self):
            self.closed = True

    monkeypatch.setitem(
        sys.modules,
        "sounddevice",
        SimpleNamespace(
            InputStream=Stream, query_devices=lambda *args: {"default_samplerate": 48000}
        ),
    )
    source = SoundInput(EdgeVoiceSettings(queue_blocks=4))
    with pytest.raises(SpeechError, match="capture_overrun"):
        async for _ in source.frames():
            pass
    assert source.queue.qsize() <= 4 and not source.available and streams[0].closed


def test_stable_audio_names_require_unique_matching_devices(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "sounddevice",
        SimpleNamespace(
            query_devices=lambda: [
                {"name": "USB microphone", "max_input_channels": 1},
                {"name": "USB microphone", "max_input_channels": 2},
            ]
        ),
    )
    with pytest.raises(SpeechError):
        select_device("USB microphone", "input")
    assert select_device("index:1", "input") == 1
    assert select_device(None, "input") is None


def test_whisper_directory_requires_every_file_to_have_a_trusted_hash(tmp_path):
    directory = tmp_path / "whisper"
    directory.mkdir()
    (directory / "model.bin").write_bytes(b"model")
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {"model": {"path": "whisper/model.bin", "sha256": hashlib.sha256(b"model").hexdigest()}}
        )
    )
    catalog = AssetCatalog(path, tmp_path)
    assert catalog.directory("whisper") == directory
    (directory / "config.json").write_bytes(b"unverified")
    with pytest.raises(ValueError, match="Every"):
        catalog.directory("whisper")
