# Hey Eve Wake Word Training

Custom [openWakeWord](https://github.com/dscripka/openWakeWord) model for the "hey eve" wake word, trained locally on an NVIDIA GPU.

This is the retained training pipeline; the historical GPU/dependency setup below
was not rerun during repository cleanup. Commands in this guide run from
`training/wake_word/`. Models, datasets, environments and generated configurations
are local ignored artifacts. See [repository layout](../../docs/REPOSITORY_LAYOUT.md).

---

## Requirements

- **Python 3.11** (x64) — [python.org](https://www.python.org/downloads/)
- **NVIDIA GPU** with CUDA 12.1+ compatible driver (tested: RTX 4070, driver 581.80)
- **Git** + **git-lfs** — [git-scm.com](https://git-scm.com) / [git-lfs.com](https://git-lfs.github.com)
- ~**25 GB** free disk space for training data and model artifacts

---

## First-time setup

Run once to install all Python dependencies and download the openWakeWord framework:

```powershell
python train.py
```

This will:
1. Clone `openwakeword` into the working directory
2. Install PyTorch 2.5 with CUDA 12.1 (`~2.4 GB`)
3. Install `piper-tts`, training tools, ONNX/TFLite converters
4. Download the four openWakeWord feature-extraction models
5. Automatically launch Phase 2 (training) when done

> **Note:** Phase 1 auto-launches Phase 2. You only need to run `python train.py` once per fresh environment.

---

## Training (subsequent runs)

If dependencies are already installed, run Phase 2 directly:

```powershell
python train.py --train
```

Each run:
- **Skips** clip generation if 30,000 clips already exist
- **Re-augments** if feature `.npy` files are missing
- **Saves to a versioned folder**: `runs/YYYYMMDD_HHMM_neg{penalty}/`
- Exports the finished model to `my_custom_model/` for the legacy listener.

---

## Tuning parameters

Open `train.py` and edit the three values in `phase2_train()`:

```python
n_samples  = 30000   # number of TTS clips to generate (more = better, 50k+ is ideal)
n_steps    = 50000   # training steps (more = better, diminishing returns past 100k)
neg_weight = 1000    # false-activation penalty (higher = fewer false triggers)
```

Re-run `python train.py --train` after any change. The old model is never deleted.

---

## Output

Each training run produces a versioned directory:

```
runs/
  20260819_1045_neg1000/
    hey_eve.onnx        ← use with openWakeWord Python API
    hey_eve.tflite      ← use with Home Assistant / embedded
    hey_eve_float16.tflite
```

The latest model is also automatically copied to the ignored directory:
```
training/wake_word/my_custom_model/
```

`EVE_TRAINING_WORK_DIR` can point to an external data workspace;
`EVE_WAKE_MODEL_DIR` can override the model export directory. Use absolute paths
for overrides. The training script no longer writes into another project's Python
installation. It locates `generate_clips_piper.py` beside its own source.

---

## Testing

```powershell
python test_wakeword.py
```

Say **"hey eve"** into your microphone. Detections print with a confidence score (0–1).

Adjust the threshold at the top of `test_wakeword.py`:
```python
THRESHOLD = 0.3   # lower = more sensitive, higher = fewer false positives
```

---

## Using in the Eve project

```powershell
# From the EveMirror repository root, using the existing voice environment:
.\.venv\Scripts\python.exe legacy/client/listen.py
```

---

## Directory structure

```
training/wake_word/
  train.py                    ← main training script
  generate_clips_piper.py     ← TTS clip generator (called by train.py)
  test_wakeword.py            ← live microphone test
  my_model.yaml               ← last training config (auto-generated)
  models/                     ← piper TTS voice model
  clips/hey_eve/              ← shared TTS clips (generated once, reused)
  runs/                       ← versioned model outputs (never deleted)
  openwakeword/               ← cloned framework
  audioset_16k/               ← background noise (500 clips)
  mit_rirs/                   ← room impulse responses
  openwakeword_features_ACAV100M_2000_hrs_16bit.npy   ← 16 GB feature file
  validation_set_features.npy
```

---

## Troubleshooting

| Error | Fix |
|---|---|
| `No module named 'yaml'` | Wrong Python — use `py -3.11 train.py` or full path to Python 3.11 |
| `pkg_resources` missing | `python -m pip install setuptools` |
| `PermissionError` on `.npy` | Stale file lock — restart terminal and retry |
| `No matching distribution for acoustics` | Already handled; stub is auto-installed |
| `cublasLt64_13.dll missing` | onnxruntime CUDA warning — harmless, falls back to CPU for feature extraction |
| Low detection scores | Lower `THRESHOLD` in `test_wakeword.py` to `0.3`, or retrain with lower `neg_weight` |
| Too many false triggers | Raise `THRESHOLD` to `0.5–0.7`, or retrain with higher `neg_weight` |
