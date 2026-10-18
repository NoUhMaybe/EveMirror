"""Explicit speech smoke test with verified assets and an existing WAV; no live devices."""

import argparse
import asyncio
import wave
from uuid import uuid4

from apps.config import SpeechSettings
from apps.edge.runtime import read_pcm_wav
from apps.server.audio import CompletedAudio
from apps.server.speech.providers import FasterWhisper, Piper


async def run(args):
    settings = SpeechSettings(
        enabled=True,
        asset_root=args.root,
        asset_manifest=args.manifest,
        stt_model_directory=args.model_directory,
    )
    engine = FasterWhisper(settings) if args.engine == "stt" else Piper(settings)
    try:
        if args.engine == "stt":
            if args.wav is None:
                raise ValueError("STT requires --wav with an existing PCM16 mono/16 kHz fixture")
            result = await engine.transcribe(
                CompletedAudio("smoke-test", uuid4(), uuid4(), read_pcm_wav(args.wav))
            )
            print(
                f"Final transcript: {len(result.text)} characters; language={result.language}; "
                f"audio={result.duration:.3f}s; STT={result.latency_ms:.1f}ms"
            )
            if args.show_text:
                print(result.text)
        else:
            audio = await engine.synthesize(args.text)
            print(
                f"Validated local PCM: {audio.sample_count} samples, {audio.sample_rate} Hz, "
                f"{audio.channels} channel, {audio.duration:.3f}s"
            )
            if args.output:
                with args.output.open("xb") as target:
                    with wave.open(target, "wb") as wav:
                        wav.setparams((1, 2, audio.sample_rate, 0, "NONE", "not compressed"))
                        wav.writeframes(audio.pcm)
    finally:
        await engine.close()


if __name__ == "__main__":
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", choices=["stt", "tts"])
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--model-directory", default="whisper")
    parser.add_argument("--wav", type=Path)
    parser.add_argument(
        "--show-text", action="store_true", help="Explicitly print the private transcription"
    )
    parser.add_argument("--text", default="Eve speech synthesis is ready for manual verification.")
    parser.add_argument(
        "--output", type=Path, help="Explicitly save TTS to a new WAV; never plays audio"
    )
    asyncio.run(run(parser.parse_args()))
