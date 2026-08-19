"""
Generates TTS audio clips for openWakeWord training using piper-tts (Python 3.11 compatible).
Replaces the piper-sample-generator/generate_samples.py pipeline which requires piper-phonemize
(no Windows Python 3.11 wheels available).

Usage:
    python generate_clips_piper.py \
        --model path/to/en_US-libritts_r-medium.onnx \
        --texts "hey eve" \
        --n_samples 1000 \
        --output_dir my_custom_model/hey_eve/positive_train
"""

import argparse
import io
import os
import sys
import uuid
import wave
import random
import itertools
from pathlib import Path

import numpy as np
import scipy.signal
import scipy.io.wavfile
from tqdm import tqdm
from piper import PiperVoice, SynthesisConfig

TARGET_SR = 16000  # openwakeword requires 16 kHz


# Variation parameters — mirrors the noise/length scale ranges in generate_samples.py
LENGTH_SCALES  = [0.75, 0.85, 1.0, 1.15, 1.25]
NOISE_SCALES   = [0.5, 0.7, 0.9, 0.98]
NOISE_W_SCALES = [0.5, 0.7, 0.9, 0.98]

# Number of speakers to cycle through (libritts_r-medium has 904 speakers)
N_SPEAKERS = 904


def _cycle_configs():
    """Infinite iterator over randomised (length, noise, noise_w, speaker) configs."""
    speaker_ids = list(range(N_SPEAKERS))
    random.shuffle(speaker_ids)
    for speaker_id, length_scale, noise_scale, noise_w in itertools.cycle(
        itertools.product(speaker_ids[:100], LENGTH_SCALES, NOISE_SCALES, NOISE_W_SCALES)
    ):
        yield SynthesisConfig(
            speaker_id=speaker_id,
            length_scale=length_scale,
            noise_scale=noise_scale,
            noise_w_scale=noise_w,
        )


def generate_clips(
    model_path: str,
    texts,
    n_samples: int,
    output_dir: str,
    existing_count: int = 0,
) -> None:
    """Generate `n_samples` WAV clips of `texts` into `output_dir`."""
    if isinstance(texts, str):
        texts = [texts]

    os.makedirs(output_dir, exist_ok=True)
    remaining = n_samples - existing_count
    if remaining <= 0:
        print(f"  Already have {existing_count}/{n_samples} clips in {output_dir}, skipping.")
        return

    print(f"  Generating {remaining} clips → {output_dir}")
    voice = PiperVoice.load(model_path, use_cuda=False)

    text_cycle = itertools.cycle(texts)
    config_cycle = _cycle_configs()

    for _ in tqdm(range(remaining)):
        text = next(text_cycle)
        syn_config = next(config_cycle)
        # Synthesize to an in-memory buffer, then resample to 16 kHz
        buf = io.BytesIO()
        with wave.open(buf, "w") as wav_file:
            voice.synthesize_wav(text, wav_file, syn_config=syn_config)
        buf.seek(0)
        with wave.open(buf, "r") as wav_file:
            native_sr = wav_file.getframerate()
            frames = wav_file.readframes(wav_file.getnframes())
            audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767.0
        if native_sr != TARGET_SR:
            samples_out = int(len(audio) * TARGET_SR / native_sr)
            audio = scipy.signal.resample(audio, samples_out)
        wav_path = os.path.join(output_dir, uuid.uuid4().hex + ".wav")
        scipy.io.wavfile.write(wav_path, TARGET_SR, (audio * 32767).astype(np.int16))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--texts", nargs="+")
    parser.add_argument("--texts-file", dest="texts_file",
                        help="Path to file with one text per line (avoids Windows arg length limit)")
    parser.add_argument("--n_samples", type=int, required=True)
    parser.add_argument("--output_dir", required=True)
    args = parser.parse_args()

    if args.texts_file:
        with open(args.texts_file, "r", encoding="utf-8") as f:
            texts = [line.rstrip("\n") for line in f if line.strip()]
    else:
        texts = args.texts

    existing = len(list(Path(args.output_dir).glob("*.wav"))) if os.path.exists(args.output_dir) else 0
    generate_clips(args.model, texts, args.n_samples, args.output_dir, existing)
