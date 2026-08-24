"""
Quickly audition Piper speaker IDs and save/play test clips.

Usage:
    python audition_tts_voices.py
    python audition_tts_voices.py --speakers 12,24,36,48 --play
    python audition_tts_voices.py --start 0 --count 12 --step 8 --text "Hey, I'm Eve."
"""

import argparse
import io
import wave
from pathlib import Path
from typing import List

import numpy as np
import sounddevice as sd
from piper import PiperVoice, SynthesisConfig

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = REPO_ROOT / "wake_word_training" / "models" / "en_US-libritts_r-medium.onnx"
DEFAULT_OUT_DIR = REPO_ROOT / "eve_agent" / "voice_auditions"
DEFAULT_TEXT = "Hi, I'm Eve. Nice to meet you. How can I help you today?"


def parse_speakers(args: argparse.Namespace) -> List[int]:
    if args.speakers:
        return [int(x.strip()) for x in args.speakers.split(",") if x.strip()]
    return [args.start + i * args.step for i in range(args.count)]


def synthesize(voice: PiperVoice, text: str, speaker_id: int, length_scale: float, noise_scale: float, noise_w_scale: float) -> tuple[np.ndarray, int]:
    syn_cfg = SynthesisConfig(
        speaker_id=speaker_id,
        length_scale=length_scale,
        noise_scale=noise_scale,
        noise_w_scale=noise_w_scale,
    )

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        voice.synthesize_wav(text, wf, syn_config=syn_cfg)

    buf.seek(0)
    with wave.open(buf, "rb") as wf:
        sr = wf.getframerate()
        ch = wf.getnchannels()
        frames = wf.readframes(wf.getnframes())

    audio = np.frombuffer(frames, dtype=np.int16)
    if ch > 1:
        audio = audio.reshape(-1, ch).mean(axis=1).astype(np.int16)

    return audio, sr


def write_wav(path: Path, audio: np.ndarray, sample_rate: int) -> None:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio.astype(np.int16).tobytes())


def main() -> None:
    parser = argparse.ArgumentParser(description="Audition local Piper TTS speaker IDs")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL, help="Path to Piper ONNX model")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="Directory for generated WAVs")
    parser.add_argument("--text", default=DEFAULT_TEXT, help="Prompt spoken by each voice")
    parser.add_argument("--speakers", default="", help="Comma-separated speaker IDs (overrides start/count/step)")
    parser.add_argument("--start", type=int, default=0, help="Starting speaker id when --speakers not set")
    parser.add_argument("--count", type=int, default=10, help="Number of speaker IDs to test")
    parser.add_argument("--step", type=int, default=8, help="Step between IDs when --speakers not set")
    parser.add_argument("--play", action="store_true", help="Play each generated clip")
    parser.add_argument("--length-scale", type=float, default=1.06)
    parser.add_argument("--noise-scale", type=float, default=0.58)
    parser.add_argument("--noise-w-scale", type=float, default=0.82)
    args = parser.parse_args()

    if not args.model.exists():
        raise SystemExit(f"TTS model not found: {args.model}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    speaker_ids = parse_speakers(args)

    print(f"Loading model: {args.model}")
    voice = PiperVoice.load(str(args.model), use_cuda=False)

    print(f"Testing speaker IDs: {speaker_ids}")
    for sid in speaker_ids:
        audio, sr = synthesize(
            voice,
            text=args.text,
            speaker_id=sid,
            length_scale=args.length_scale,
            noise_scale=args.noise_scale,
            noise_w_scale=args.noise_w_scale,
        )

        out_path = args.out_dir / f"speaker_{sid}.wav"
        write_wav(out_path, audio, sr)
        print(f"Saved: {out_path}")

        if args.play:
            print(f"Playing speaker {sid}...")
            sd.play(audio.astype(np.float32) / 32767.0, samplerate=sr, blocking=True)

    print("\nDone. Choose your preferred speaker ID and run:")
    print("  python mirror_client/runtime.py --tts-speaker <ID>")


if __name__ == "__main__":
    main()
