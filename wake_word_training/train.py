# -*- coding: utf-8 -*-
"""
Local training script for openWakeWord custom wake word "hey eve".
Uses piper-tts (Python 3.11 compatible) instead of piper-sample-generator
which requires piper-phonemize (no Windows Python 3.11 wheels).

Usage:
    python train.py           # Phase 1: install all dependencies
    python train.py --train   # Phase 2: download data + train (auto-launched by phase 1)
"""

import os
import sys
import argparse
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

WORK_DIR = r"C:\Users\Work\Downloads\hey_eve_training"
TARGET_WORD = "hey eve"

# Piper ONNX voice model (multi-speaker, 904 speakers, works with piper-tts on Python 3.11)
PIPER_MODEL_URL  = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/libritts_r/medium/en_US-libritts_r-medium.onnx"
PIPER_CONFIG_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/libritts_r/medium/en_US-libritts_r-medium.onnx.json"
PIPER_MODEL_PATH = os.path.join(WORK_DIR, "models", "en_US-libritts_r-medium.onnx")


def run(cmd, cwd=None):
    print(f"  > {' '.join(str(c) for c in cmd)}")
    subprocess.run(cmd, cwd=cwd, check=True)


def download(url, dest):
    import requests
    from tqdm import tqdm
    print(f"  Downloading {os.path.basename(dest)} ...")
    os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
    with requests.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        with open(dest, "wb") as f, tqdm(total=total, unit="B", unit_scale=True, unit_divisor=1024) as bar:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)
                bar.update(len(chunk))


def download_simple(url, dest):
    import urllib.request
    print(f"  Downloading {os.path.basename(dest)} ...")
    os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
    urllib.request.urlretrieve(url, dest)


def pip(*args):
    run([sys.executable, "-m", "pip", "install", *args])


# ── Phase 1: install all dependencies ────────────────────────────────────────

def phase1_install():
    os.makedirs(WORK_DIR, exist_ok=True)
    os.chdir(WORK_DIR)
    print("\n=== Phase 1: Installing dependencies ===\n")

    # Clone openwakeword
    if not os.path.exists("openwakeword"):
        run(["git", "clone", "https://github.com/dscripka/openwakeword"])

    # PyTorch 2.5 with CUDA 12.1 (compatible with RTX 4070 / CUDA 13.0 driver)
    pip("torch==2.5.0", "torchvision==0.20.0", "torchaudio==2.5.0",
        "--index-url", "https://download.pytorch.org/whl/cu121")

    # piper-tts: Python 3.11 compatible, bundles phonemization, no piper-phonemize needed
    pip("piper-tts", "webrtcvad-wheels")

    # openwakeword (no deps to avoid version conflicts)
    pip("-e", "./openwakeword", "--no-deps")

    # Training dependencies
    pip("mutagen==1.47.0", "torchinfo==1.8.0", "torchmetrics==1.2.0",
        "speechbrain==0.5.14", "audiomentations==0.33.0",
        "torch-audiomentations==0.11.0", "acoustics==0.2.6")

    # ONNX / TFLite conversion
    pip("onnxruntime==1.22.1", "ai_edge_litert==1.4.0", "onnxsim")
    pip("onnx2tf")
    pip("onnx==1.19.1")
    pip("onnx_graphsurgeon", "sng4onnx")

    # Data and NLP tools
    pip("pronouncing==0.2.0", "datasets==2.14.6", "deep-phonemizer==0.0.19")
    pip("scipy", "tqdm", "requests", "pyyaml")

    # Fix known version conflicts
    pip("numpy==2.2.6", "--force-reinstall")
    pip("onnx==1.20.1", "--force-reinstall")
    pip("speexdsp-ns")
    pip("onnx2tf", "--upgrade")

    # openWakeWord feature-extraction models
    models_dir = os.path.join(WORK_DIR, "openwakeword", "openwakeword", "resources", "models")
    os.makedirs(models_dir, exist_ok=True)
    for fname in ["embedding_model.onnx", "embedding_model.tflite",
                  "melspectrogram.onnx", "melspectrogram.tflite"]:
        dest = os.path.join(models_dir, fname)
        if not os.path.exists(dest):
            download_simple(
                f"https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/{fname}",
                dest,
            )

    print("\n=== Phase 1 complete. Launching training phase... ===\n")
    run([sys.executable, str(Path(__file__).resolve()), "--train"])


# ── Phase 2: download data and train ─────────────────────────────────────────

def phase2_train():
    os.chdir(WORK_DIR)
    print("\n=== Phase 2: Downloading data and training model ===\n")

    import numpy as np
    import yaml
    import scipy.io.wavfile
    import soundfile as sf
    import librosa
    import datasets as hf_datasets
    from pathlib import Path
    from tqdm import tqdm

    # ── Download piper ONNX voice model ───────────────────────────────────
    os.makedirs(os.path.dirname(PIPER_MODEL_PATH), exist_ok=True)
    if not os.path.exists(PIPER_MODEL_PATH):
        download(PIPER_MODEL_URL, PIPER_MODEL_PATH)
    config_path = PIPER_MODEL_PATH + ".json"
    if not os.path.exists(config_path):
        download(PIPER_CONFIG_URL, config_path)

    # ── Download MIT RIR data ──────────────────────────────────────────────
    rir_out = os.path.join(WORK_DIR, "mit_rirs")
    if not os.path.exists(rir_out):
        os.makedirs(rir_out)
        print("Downloading MIT RIR data...")
        run(["git", "lfs", "install"])
        run(["git", "clone",
             "https://huggingface.co/datasets/davidscripka/MIT_environmental_impulse_responses"],
            cwd=WORK_DIR)
        rir_src = os.path.join(WORK_DIR, "MIT_environmental_impulse_responses", "16khz")
        # Load WAVs directly with soundfile — already 16 kHz per directory name
        for wav_path in tqdm(list(Path(rir_src).glob("*.wav")), desc="Converting RIR clips"):
            data, sr = sf.read(str(wav_path))
            if data.ndim > 1:
                data = data.mean(axis=1)
            if sr != 16000:
                data = librosa.resample(data.astype(np.float32), orig_sr=sr, target_sr=16000)
            scipy.io.wavfile.write(
                os.path.join(rir_out, wav_path.name), 16000,
                (data * 32767).astype(np.int16),
            )

    # ── Download AudioSet background noise (streaming from Parquet) ──────
    audioset_16k = os.path.join(WORK_DIR, "audioset_16k")
    if not os.path.exists(audioset_16k):
        os.makedirs(audioset_16k)
        print("Streaming AudioSet balanced train (500 clips)...")
        audioset_ds = hf_datasets.load_dataset(
            "agkphysics/AudioSet", "balanced", split="train",
            streaming=True, trust_remote_code=True,
        )
        for i, row in tqdm(enumerate(audioset_ds), total=500, desc="AudioSet clips"):
            if i >= 500:
                break
            try:
                arr = np.array(row["audio"]["array"], dtype=np.float32)
                sr  = row["audio"]["sampling_rate"]
                if sr != 16000:
                    arr = librosa.resample(arr, orig_sr=sr, target_sr=16000)
                scipy.io.wavfile.write(
                    os.path.join(audioset_16k, f"{row['video_id']}.wav"),
                    16000, (arr * 32767).astype(np.int16),
                )
            except Exception as e:
                print(f"  Skipping clip: {e}")

    # FMA streaming has HTTP seek issues with its custom loader; AudioSet is sufficient
    fma_dir = audioset_16k  # point to audioset so background_paths stays valid

    # ── Download pre-computed openWakeWord features ────────────────────────
    features_file = os.path.join(WORK_DIR, "openwakeword_features_ACAV100M_2000_hrs_16bit.npy")
    val_file      = os.path.join(WORK_DIR, "validation_set_features.npy")
    base_url = "https://huggingface.co/datasets/davidscripka/openwakeword_features/resolve/main/"
    if not os.path.exists(features_file):
        download(base_url + "openwakeword_features_ACAV100M_2000_hrs_16bit.npy", features_file)
    if not os.path.exists(val_file):
        download(base_url + "validation_set_features.npy", val_file)

    # ── Build training config ──────────────────────────────────────────────
    print("\nConfiguring training...")
    config = yaml.load(
        open(os.path.join(WORK_DIR, "openwakeword", "examples", "custom_model.yml"), "r").read(),
        yaml.Loader,
    )

    n_samples       = 30000
    n_steps         = 50000
    neg_weight      = 1000
    model_name      = TARGET_WORD.replace(" ", "_")

    # Each run gets its own timestamped directory so models are never overwritten
    run_id     = datetime.now().strftime("%Y%m%d_%H%M")
    run_dir    = os.path.join(WORK_DIR, "runs", f"{run_id}_neg{neg_weight}")
    clips_dir  = os.path.join(WORK_DIR, "clips")  # shared across all runs
    os.makedirs(run_dir, exist_ok=True)
    os.makedirs(clips_dir, exist_ok=True)

    config["target_phrase"]       = [TARGET_WORD]
    config["model_name"]          = model_name
    config["n_samples"]           = n_samples
    config["n_samples_val"]       = max(500, n_samples // 10)
    config["steps"]               = n_steps
    config["output_dir"]          = run_dir
    config["max_negative_weight"] = neg_weight
    config["rir_paths"]           = [rir_out]
    config["background_paths"]    = [audioset_16k, fma_dir]
    config["false_positive_validation_data_path"] = val_file
    config["feature_data_files"]  = {"ACAV100M_sample": features_file}
    # piper_sample_generator_path not used — we pre-generate clips below
    config["piper_sample_generator_path"] = os.path.join(WORK_DIR, "piper-sample-generator")

    yaml_path = os.path.join(WORK_DIR, "my_model.yaml")
    with open(yaml_path, "w") as f:
        yaml.dump(config, f)

    # ── Generate clips using piper-tts (no piper-phonemize needed) ────────
    gen_script = os.path.join(WORK_DIR, "generate_clips_piper.py")
    out_base   = os.path.join(clips_dir, model_name)  # shared clips location

    # Generate adversarial texts without the pronouncing library (pkg_resources issues)
    # Partial phrases + phonetically similar words are sufficient for a basic model
    def simple_adversarial_texts(target: str, n: int):
        parts = target.split()
        pool = list(parts)  # individual words
        pool += [" ".join(parts[i:]) for i in range(1, len(parts))]  # suffixes
        pool += [" ".join(parts[:i]) for i in range(1, len(parts))]  # prefixes
        # add phonetically close words for "hey eve"
        pool += ["hey", "eve", "eves", "heave", "heavy", "hey ev", "hey eve",
                 "hey there", "okay", "say", "they", "weave", "leave", "Steve",
                 "sleeve", "believe", "achieve", "receive", "naive", "live",
                 "give", "have", "save", "brave", "grave", "wave", "cave",
                 "hey you", "hey now", "hey man", "eve morning", "christmas eve",
                 "new year's eve", "hey girl", "hey guys"]
        import random, itertools
        return [random.choice(pool) for _ in range(n)]

    adversarial_texts = simple_adversarial_texts(TARGET_WORD, n_samples)

    clips = {
        "positive_train": (n_samples,                 [TARGET_WORD]),
        "positive_test":  (max(500, n_samples // 10), [TARGET_WORD]),
        "negative_train": (n_samples,                 adversarial_texts),
        "negative_test":  (max(500, n_samples // 10), adversarial_texts),
    }

    print("\nStep 1/3: Generating clips with piper-tts...")
    for dir_name, (count, texts) in clips.items():
        clip_dir = os.path.join(out_base, dir_name)
        existing = len(list(Path(clip_dir).glob("*.wav"))) if os.path.exists(clip_dir) else 0
        if existing >= int(0.95 * count):
            print(f"  Skipping {dir_name}: already have {existing}/{count} clips")
            continue
        # Write texts to a temp file to avoid Windows 32k command-line length limit
        texts_file = os.path.join(WORK_DIR, f"_texts_{dir_name}.txt")
        with open(texts_file, "w", encoding="utf-8") as f:
            f.write("\n".join(texts))
        run([sys.executable, gen_script,
             "--model",      PIPER_MODEL_PATH,
             "--texts-file", texts_file,
             "--n_samples",  str(count),
             "--output_dir", clip_dir])

    # ── Link shared clips into the run dir so openwakeword can find them ──
    # Uses directory junctions (Windows) so no data is duplicated
    run_model_dir = os.path.join(run_dir, model_name)
    os.makedirs(run_model_dir, exist_ok=True)
    for clip_subdir in ("positive_train", "positive_test", "negative_train", "negative_test"):
        src = os.path.join(out_base, clip_subdir)
        dst = os.path.join(run_model_dir, clip_subdir)
        if not os.path.exists(dst) and os.path.exists(src):
            subprocess.run(["cmd", "/c", "mklink", "/J", dst, src], check=True)

    # ── Augment and train ──────────────────────────────────────────────────
    train_script = os.path.join(WORK_DIR, "openwakeword", "openwakeword", "train.py")

    print("\nStep 2/3: Augmenting clips with background noise...")
    run([sys.executable, train_script, "--training_config", yaml_path, "--augment_clips"])

    print("\nStep 3/3: Training the model...")
    run([sys.executable, train_script, "--training_config", yaml_path, "--train_model"])

    # ── Convert ONNX → TFLite ──────────────────────────────────────────────
    print("\nConverting ONNX model to TFLite...")
    onnx_out = os.path.join(run_dir, f"{model_name}.onnx")
    run(["onnx2tf", "-i", onnx_out,
         "-o", run_dir,
         "-kat", "onnx____Flatten_0"])

    float32 = os.path.join(run_dir, f"{model_name}_float32.tflite")
    final   = os.path.join(run_dir, f"{model_name}.tflite")
    if os.path.exists(float32):
        shutil.move(float32, final)

    print("\n" + "=" * 60)
    print("Training complete!")
    print(f"  Run:    {run_dir}")
    print(f"  ONNX:   {run_dir}\\{model_name}.onnx")
    print(f"  TFLite: {run_dir}\\{model_name}.tflite")
    print("=" * 60)

    # Copy to Eve project so it's available as a named model
    eve_models = r"C:\Users\Work\Documents\Eve\.venv\Lib\site-packages\openwakeword\resources\models"
    if os.path.exists(eve_models):
        import shutil as _shutil
        _shutil.copy2(os.path.join(run_dir, f"{model_name}.onnx"), eve_models)
        _shutil.copy2(os.path.join(run_dir, f"{model_name}.tflite"), eve_models)
        print(f"  Copied models to Eve project: {eve_models}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", action="store_true")
    args = parser.parse_args()

    if args.train:
        phase2_train()
    else:
        phase1_install()
