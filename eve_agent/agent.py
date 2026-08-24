"""
Phase 4 — Text Agent
Minimal local Eve agent loop using Ollama chat API.

Usage:
    python agent.py --text "What's the weather?"
    python agent.py --audio ..\\mirror_client\\recordings\\command_20260819_180045.wav
    python agent.py

Interactive commands:
    /reset  -> clear temporary conversation context
    /exit   -> quit
"""

import argparse
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional
from zoneinfo import ZoneInfo

import requests
from dashboard_events import emit_event
from tooling import maybe_call_tools
from tts_local import LocalTTS, LocalTTSConfig

DEFAULT_MODEL = "hf.co/mradermacher/Huihui-Qwen3.5-9B-abliterated-GGUF:Q5_K_M"
DEFAULT_OLLAMA_URL = "http://localhost:11434"
_REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TTS_MODEL = _REPO_ROOT / "wake_word_training" / "models" / "en_US-libritts_r-medium.onnx"
DEFAULT_REQUEST_LOCATION = "Frisco, Texas, USA"
DEFAULT_REQUEST_TIMEZONE = "America/Chicago"

SYSTEM_PROMPT = (
    "You are Eve, a local smart-mirror voice assistant. "
    "The user's name is not Eve unless the user explicitly says so; never address the user as Eve. "
    "Do not start responses with filler acknowledgements like 'Got it', 'Sure', or 'Okay'. "
    "Do not narrate actions like 'checking' or 'looking up'. "
    "When tool context is present, treat it as already fetched and answer directly in the first sentence. "
    "Default to one short sentence; use at most two only if needed for clarity. "
    "For straightforward factual prompts (weather, time, sunset/sunrise), keep replies under 18 words. "
    "Keep responses concise, natural, and directly useful. "
    "Do not reveal chain-of-thought. "
    "Never fabricate real-time facts (weather, time, forecasts, live conditions). "
    "Use tool context when provided; if required live context is missing or failed, say so plainly. "
    "If tool results are provided, treat them as trusted local context."
)


def build_request_context_block() -> str:
    try:
        local_tz = ZoneInfo(DEFAULT_REQUEST_TIMEZONE)
        local_now = datetime.now(local_tz)
    except Exception:
        local_now = datetime.now().astimezone()

    utc_now = datetime.now(timezone.utc)
    local_iso = local_now.isoformat(timespec="seconds")
    utc_iso = utc_now.isoformat(timespec="seconds")

    return (
        "Request context:\n"
        f"- location: {DEFAULT_REQUEST_LOCATION}\n"
        f"- timezone: {DEFAULT_REQUEST_TIMEZONE}\n"
        f"- request_timestamp_local: {local_iso}\n"
        f"- request_timestamp_utc: {utc_iso}\n"
        "- assistant_identity: Eve (the assistant), not the user"
    )


def estimate_speech_duration_s(text: str) -> float:
    trimmed = text.strip()
    if not trimmed:
        return 0.0
    words = trimmed.split()
    punctuation_pauses = sum(1 for c in trimmed if c in ".,!?;:")
    duration = len(words) / 2.7 + punctuation_pauses * 0.12
    return max(0.45, duration)


def emit_text_speaking_timeline(reply: str) -> None:
    words = reply.split()
    if not words:
        emit_event("state_change", {"state": "IDLE"})
        return

    duration_s = estimate_speech_duration_s(reply)
    emit_event("subtitle_prepare", {"text": reply, "words": words, "duration_s": duration_s})
    emit_event("state_change", {"state": "SPEAKING", "duration_s": duration_s, "text": reply})

    step_s = max(0.04, min(0.22, duration_s / max(1, len(words))))
    for idx in range(len(words)):
        emit_event("subtitle_progress", {"word_index": idx})
        time.sleep(step_s)

    emit_event("subtitle_done", {"text": reply})
    emit_event("state_change", {"state": "IDLE"})


def speak_reply(reply: str, tts: Optional[LocalTTS]) -> None:
    emit_event("assistant_response", {"text": reply})
    if tts is not None:
        tts.speak(reply, emit_event)
        emit_event("state_change", {"state": "IDLE"})
    else:
        emit_text_speaking_timeline(reply)


def get_text_from_audio(audio_path: Path) -> str:
    from transcribe import load_model, transcribe

    model = load_model()
    return transcribe(model, audio_path)


def ask_ollama(base_url: str, model: str, messages: List[Dict[str, str]], think: bool) -> str:
    url = base_url.rstrip("/") + "/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "think": think,
    }

    response = requests.post(url, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()

    message = data.get("message", {})
    content = message.get("content", "").strip()
    if content:
        return content

    if think:
        retry_payload = dict(payload)
        retry_payload["think"] = False
        retry = requests.post(url, json=retry_payload, timeout=120)
        retry.raise_for_status()
        retry_data = retry.json()
        retry_message = retry_data.get("message", {})
        retry_content = retry_message.get("content", "").strip()
        if retry_content:
            return retry_content

    return "(No response content returned by Ollama)"


def build_messages(base_messages: List[Dict[str, str]], user_text: str) -> List[Dict[str, str]]:
    notes, tool_payload = maybe_call_tools(user_text)
    messages = list(base_messages)
    context_block = build_request_context_block()
    if notes:
        print("Tool routing:")
        for n in notes:
            print(f"  - {n}")
    if notes or tool_payload:
        emit_event("tool_context", {"notes": notes, "payload": tool_payload})
    if tool_payload:
        user_with_tools = (
            f"User request: {user_text}\n\n"
            f"{context_block}\n\n"
            "Use this trusted local tool context when relevant:\n"
            f"{tool_payload}"
        )
    else:
        user_with_tools = f"User request: {user_text}\n\n{context_block}"

    messages.append({"role": "user", "content": user_with_tools})
    return messages


def run_once(args: argparse.Namespace, tts: Optional[LocalTTS]) -> None:
    messages: List[Dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]

    if args.audio:
        user_text = get_text_from_audio(args.audio)
        print(f"Transcribed: {user_text}")
    else:
        user_text = args.text

    emit_event("user_transcript", {"text": user_text, "source": "text"})

    request_messages = build_messages(messages, user_text)
    think = False
    print(f"Think mode: {'on' if think else 'off'}")
    emit_event("state_change", {"state": "THINKING", "think": think})
    try:
        reply = ask_ollama(args.ollama_url, args.model, request_messages, think=think)
    except requests.exceptions.RequestException as exc:
        raise SystemExit(
            "Ollama request failed. Start Ollama and ensure it is reachable at "
            f"{args.ollama_url}. Details: {exc}"
        )
    speak_reply(reply, tts)
    print(f"Eve: {reply}")


def run_interactive(args: argparse.Namespace, tts: Optional[LocalTTS]) -> None:
    messages: List[Dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]

    print("Eve agent ready. Type a message, /reset, or /exit.")
    while True:
        user_text = input("You: ").strip()
        if not user_text:
            continue
        if user_text == "/exit":
            print("Bye.")
            return
        if user_text == "/reset":
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            print("Session context cleared.")
            emit_event("state_change", {"state": "IDLE"})
            continue

        emit_event("user_transcript", {"text": user_text, "source": "text"})
        request_messages = build_messages(messages, user_text)
        think = False
        print(f"Think mode: {'on' if think else 'off'}")
        emit_event("state_change", {"state": "THINKING", "think": think})
        try:
            reply = ask_ollama(args.ollama_url, args.model, request_messages, think=think)
        except requests.exceptions.RequestException as exc:
            print(f"Ollama request failed: {exc}")
            emit_event("state_change", {"state": "IDLE"})
            continue

        messages.append({"role": "user", "content": user_text})
        messages.append({"role": "assistant", "content": reply})
        speak_reply(reply, tts)
        print(f"Eve: {reply}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Eve text agent (Ollama)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model name")
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL, help="Ollama base URL")
    parser.add_argument("--text", help="Single-turn text input")
    parser.add_argument("--audio", type=Path, help="Single-turn WAV path to transcribe first")
    parser.add_argument("--tts-model", type=Path, default=DEFAULT_TTS_MODEL, help="Path to Piper ONNX voice model")
    parser.add_argument("--tts-speaker", type=int, default=0, help="Speaker id for multi-speaker Piper models")
    parser.add_argument("--no-tts", action="store_true", help="Disable local TTS playback")
    args = parser.parse_args()

    if args.text and args.audio:
        raise SystemExit("Use either --text or --audio, not both.")

    tts: Optional[LocalTTS] = None
    if not args.no_tts:
        if not args.tts_model.exists():
            raise SystemExit(f"TTS model not found: {args.tts_model}")
        tts_cfg = LocalTTSConfig(model_path=args.tts_model, speaker_id=args.tts_speaker)
        tts = LocalTTS(tts_cfg)

    if args.text or args.audio:
        run_once(args, tts)
    else:
        run_interactive(args, tts)


if __name__ == "__main__":
    main()
