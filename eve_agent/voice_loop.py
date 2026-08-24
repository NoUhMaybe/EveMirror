"""
Single-command voice loop runner.

Default behavior:
- picks the latest WAV in mirror_client/recordings
- transcribes it
- sends text through Eve agent routing + Ollama
- prints final Eve response

Usage:
    python voice_loop.py
    python voice_loop.py --audio ..\\mirror_client\\recordings\\command_20260819_180045.wav
    python voice_loop.py --watch
"""

import argparse
import time
from pathlib import Path
from typing import Optional, Set

import requests

from agent import (
    DEFAULT_MODEL,
    DEFAULT_OLLAMA_URL,
    SYSTEM_PROMPT,
    ask_ollama,
    build_messages,
)
from dashboard_events import emit_event
from tooling import should_enable_thinking
from tts_local import LocalTTS, LocalTTSConfig
from transcribe import load_model, transcribe

_REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RECORDINGS_DIR = _REPO_ROOT / "mirror_client" / "recordings"
DEFAULT_TTS_MODEL = _REPO_ROOT / "wake_word_training" / "models" / "en_US-libritts_r-medium.onnx"


def get_latest_wav(recordings_dir: Path) -> Optional[Path]:
    wavs = list(recordings_dir.glob("*.wav"))
    if not wavs:
        return None
    return max(wavs, key=lambda p: p.stat().st_mtime)


def run_turn(audio_path: Path, stt_model, model_name: str, ollama_url: str, tts: Optional[LocalTTS]) -> None:
    print(f"Audio: {audio_path.name}")
    emit_event("state_change", {"state": "TRANSCRIBING", "audio": audio_path.name})

    user_text = transcribe(stt_model, audio_path)
    print(f"Transcribed: {user_text}")
    emit_event("user_transcript", {"text": user_text, "audio": audio_path.name})

    think = should_enable_thinking(user_text)
    print(f"Think mode: {'on' if think else 'off'}")
    emit_event("state_change", {"state": "THINKING", "think": think})

    base_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    request_messages = build_messages(base_messages, user_text)

    try:
        reply = ask_ollama(ollama_url, model_name, request_messages, think=think)
    except requests.exceptions.RequestException as exc:
        raise SystemExit(
            "Ollama request failed. Start Ollama and ensure it is reachable at "
            f"{ollama_url}. Details: {exc}"
        )

    print(f"Eve: {reply}\n")
    emit_event("assistant_response", {"text": reply})
    if tts is not None:
        tts.speak(reply, emit_event)
    emit_event("state_change", {"state": "IDLE"})


def watch_loop(recordings_dir: Path, stt_model, model_name: str, ollama_url: str, tts: Optional[LocalTTS]) -> None:
    print(f"Watching recordings directory: {recordings_dir}")
    print("Press Ctrl+C to stop.\n")
    emit_event("state_change", {"state": "IDLE"})

    seen: Set[Path] = set(recordings_dir.glob("*.wav"))

    try:
        while True:
            time.sleep(0.5)
            current = set(recordings_dir.glob("*.wav"))
            new_files = sorted(current - seen, key=lambda p: p.stat().st_mtime)
            seen = current
            for wav_path in new_files:
                run_turn(wav_path, stt_model, model_name, ollama_url, tts)
    except KeyboardInterrupt:
        print("Stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Eve full voice loop runner")
    parser.add_argument("--audio", type=Path, help="Explicit WAV file to process")
    parser.add_argument("--watch", action="store_true", help="Watch recordings directory for new WAV files")
    parser.add_argument("--recordings-dir", type=Path, default=DEFAULT_RECORDINGS_DIR, help="Directory containing command WAV files")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model name")
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL, help="Ollama base URL")
    parser.add_argument("--tts-model", type=Path, default=DEFAULT_TTS_MODEL, help="Path to Piper ONNX voice model")
    parser.add_argument("--tts-speaker", type=int, default=0, help="Speaker id for multi-speaker Piper models")
    parser.add_argument("--no-tts", action="store_true", help="Disable local TTS playback")
    args = parser.parse_args()

    recordings_dir = args.recordings_dir
    recordings_dir.mkdir(parents=True, exist_ok=True)

    stt_model = load_model()

    tts: Optional[LocalTTS] = None
    if not args.no_tts:
        if not args.tts_model.exists():
            raise SystemExit(f"TTS model not found: {args.tts_model}")
        tts_cfg = LocalTTSConfig(model_path=args.tts_model, speaker_id=args.tts_speaker)
        tts = LocalTTS(tts_cfg)

    if args.watch:
        watch_loop(recordings_dir, stt_model, args.model, args.ollama_url, tts)
        return

    if args.audio:
        if not args.audio.exists():
            raise SystemExit(f"Audio file not found: {args.audio}")
        run_turn(args.audio, stt_model, args.model, args.ollama_url, tts)
        return

    latest = get_latest_wav(recordings_dir)
    if not latest:
        raise SystemExit(f"No WAV files found in {recordings_dir}")

    run_turn(latest, stt_model, args.model, args.ollama_url, tts)


if __name__ == "__main__":
    main()
