"""
Phase 2 — Voice Capture
Listens continuously for "Hey Eve", plays an acknowledgement chime, records
the user's command via Silero VAD, and writes command.wav for the STT stage.

Usage:
    python listen.py
    python listen.py --list-devices
    python listen.py --device 1 --threshold 0.4 --silence-ms 600
    python listen.py --no-clear-on-start
"""

import argparse
import queue
import time
import urllib.request
from datetime import datetime
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

SAMPLE_RATE  = 16000
OWW_CHUNK    = 1280   # 80ms — openWakeWord requirement
VAD_CHUNK    = 512    # 32ms — Silero VAD requirement
OWW_THRESHOLD = 0.3
SILENCE_MS   = 1500
MAX_RECORD_S = 15
OWW_COOLDOWN = 3.0    # seconds to suppress OWW after a wake event

_REPO_ROOT     = Path(__file__).resolve().parent.parent
MODEL_PATH     = _REPO_ROOT / "wake_word_training" / "my_custom_model" / "hey_eve.onnx"
OWW_MODELS_DIR = _REPO_ROOT / "wake_word_training" / "models" / "openwakeword"
MELSPEC_PATH   = OWW_MODELS_DIR / "melspectrogram.onnx"
EMBED_PATH     = OWW_MODELS_DIR / "embedding_model.onnx"
RECORDINGS_DIR = Path(__file__).resolve().parent / "recordings"


def _ensure_oww_feature_models() -> None:
    OWW_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    required = {
        MELSPEC_PATH: "https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/melspectrogram.onnx",
        EMBED_PATH: "https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/embedding_model.onnx",
    }

    for dest, url in required.items():
        if dest.exists() and dest.stat().st_size > 0:
            continue
        print(f"Downloading openWakeWord resource: {dest.name}")
        urllib.request.urlretrieve(url, str(dest))


def _generate_chime(sr: int = SAMPLE_RATE) -> np.ndarray:
    duration, fade = 0.20, 0.025
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    wave = np.sin(2 * np.pi * 880 * t).astype(np.float32) * 0.6
    n = int(sr * fade)
    wave[:n] *= np.linspace(0, 1, n)
    wave[-n:] *= np.linspace(1, 0, n)
    return wave


def main() -> None:
    parser = argparse.ArgumentParser(description="Hey Eve — voice capture")
    parser.add_argument("--device", type=int, default=None,
                        help="Input device index (see --list-devices)")
    parser.add_argument("--list-devices", action="store_true")
    parser.add_argument("--threshold", type=float, default=OWW_THRESHOLD,
                        help="Wake word confidence threshold (0–1)")
    parser.add_argument("--silence-ms", type=int, default=SILENCE_MS,
                        help="Trailing silence (ms) that ends a recording")
    parser.add_argument("--no-clear-on-start", action="store_true",
                        help="Preserve existing recordings at startup")
    args = parser.parse_args()

    if args.list_devices:
        for i, d in enumerate(sd.query_devices()):
            if d["max_input_channels"] > 0:
                print(f"  [{i}] {d['name']}")
        return

    import torch
    from silero_vad import load_silero_vad, VADIterator
    from openwakeword.model import Model as OWWModel

    _ensure_oww_feature_models()

    print(f"Loading wake word model: {MODEL_PATH}")
    oww = OWWModel(
        wakeword_models=[str(MODEL_PATH)],
        inference_framework="onnx",
        melspec_model_path=str(MELSPEC_PATH),
        embedding_model_path=str(EMBED_PATH),
    )

    print("Loading Silero VAD...")
    vad_model = load_silero_vad()

    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    if args.no_clear_on_start:
        print(f"Recordings directory preserved: {RECORDINGS_DIR}")
    else:
        for f in RECORDINGS_DIR.glob("*.wav"):
            f.unlink()
        print(f"Recordings directory cleared: {RECORDINGS_DIR}")

    chime    = _generate_chime()
    audio_q: queue.Queue = queue.Queue()

    def _callback(indata, frames, time_info, status):
        audio_q.put(indata[:, 0].copy())

    print(f"\nListening for 'Hey Eve'... (threshold={args.threshold})")
    print("Press Ctrl+C to stop.\n")

    oww_buf     = np.zeros(0, dtype=np.float32)
    vad_buf     = np.zeros(0, dtype=np.float32)
    rec_chunks: list = []
    mode        = "WAITING"
    last_wake   = 0.0
    vad_iter    = None
    rec_start   = 0.0

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=VAD_CHUNK,
        device=args.device,
        callback=_callback,
    ):
        try:
            while True:
                try:
                    chunk = audio_q.get(timeout=0.5)
                except queue.Empty:
                    continue

                if mode == "WAITING":
                    oww_buf = np.concatenate([oww_buf, chunk])
                    while len(oww_buf) >= OWW_CHUNK:
                        window, oww_buf = oww_buf[:OWW_CHUNK], oww_buf[OWW_CHUNK:]
                        pred = oww.predict((window * 32767).astype(np.int16))
                        if (time.monotonic() - last_wake) < OWW_COOLDOWN:
                            continue
                        for name, score in pred.items():
                            if score >= args.threshold:
                                print(f"  Wake word detected ({score:.3f})")
                                last_wake = time.monotonic()
                                sd.play(chime, samplerate=SAMPLE_RATE, blocking=True)
                                time.sleep(0.05)  # brief pause for echo to settle
                                while True:  # drain stale audio accumulated during chime
                                    try:
                                        audio_q.get_nowait()
                                    except queue.Empty:
                                        break
                                vad_iter = VADIterator(
                                    vad_model,
                                    sampling_rate=SAMPLE_RATE,
                                    threshold=0.4,
                                    min_silence_duration_ms=args.silence_ms,
                                )
                                vad_buf    = np.zeros(0, dtype=np.float32)
                                rec_chunks = []
                                rec_start  = time.monotonic()
                                mode       = "RECORDING"

                elif mode == "RECORDING":
                    rec_chunks.append(chunk)
                    vad_buf = np.concatenate([vad_buf, chunk])

                    # Keep OWW state current even while recording
                    oww_buf = np.concatenate([oww_buf, chunk])
                    while len(oww_buf) >= OWW_CHUNK:
                        window, oww_buf = oww_buf[:OWW_CHUNK], oww_buf[OWW_CHUNK:]
                        oww.predict((window * 32767).astype(np.int16))

                    speech_ended = False
                    while len(vad_buf) >= VAD_CHUNK:
                        window, vad_buf = vad_buf[:VAD_CHUNK], vad_buf[VAD_CHUNK:]
                        result = vad_iter(torch.from_numpy(window), return_seconds=False)
                        if result and "end" in result:
                            speech_ended = True

                    elapsed = time.monotonic() - rec_start
                    if speech_ended or elapsed > MAX_RECORD_S:
                        audio    = np.concatenate(rec_chunks)
                        reason   = "silence" if speech_ended else "timeout"
                        out_path = RECORDINGS_DIR / f"command_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
                        print(f"  Recording stopped ({reason}, {elapsed:.1f}s)")
                        sf.write(str(out_path), audio, SAMPLE_RATE)
                        print(f"  Saved → {out_path}\n")
                        oww_buf = np.zeros(0, dtype=np.float32)
                        mode    = "WAITING"

        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
