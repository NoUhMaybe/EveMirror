"""
Phase 3 — Speech-to-Text
Transcribes audio using faster-whisper (Whisper large-v3-turbo).

Usage:
    python transcribe.py path/to/command.wav
    python transcribe.py --watch       # watches mirror_client/recordings/ for new files
"""

import argparse
import os
import site
import sys
import time
from pathlib import Path

MODEL_SIZE   = "large-v3-turbo"
DEVICE       = "cuda"
COMPUTE_TYPE = "float16"

_REPO_ROOT     = Path(__file__).resolve().parent.parent
RECORDINGS_DIR = _REPO_ROOT / "mirror_client" / "recordings"


def configure_windows_cuda_dll_paths() -> None:
    if os.name != "nt":
        return

    bin_dirs = []
    for root in [Path(p) for p in site.getsitepackages()]:
        for relative in [
            Path("nvidia") / "cublas" / "bin",
            Path("nvidia") / "cudnn" / "bin",
            Path("nvidia") / "cuda_nvrtc" / "bin",
        ]:
            path = root / relative
            if path.exists():
                bin_dirs.append(path)

    for dll_dir in bin_dirs:
        os.add_dll_directory(str(dll_dir))

    if bin_dirs:
        current_path = os.environ.get("PATH", "")
        prefix = os.pathsep.join(str(p) for p in bin_dirs)
        os.environ["PATH"] = prefix + os.pathsep + current_path


def get_windows_cuda_bin_dirs() -> list:
    if os.name != "nt":
        return []

    dirs = []
    for root in [Path(p) for p in site.getsitepackages()]:
        for relative in [
            Path("nvidia") / "cublas" / "bin",
            Path("nvidia") / "cudnn" / "bin",
            Path("nvidia") / "cuda_nvrtc" / "bin",
        ]:
            path = root / relative
            if path.exists():
                dirs.append(path)
    return dirs


def load_model():
    configure_windows_cuda_dll_paths()
    from faster_whisper import WhisperModel
    try:
        model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
        print(f"Loaded {MODEL_SIZE} on {DEVICE} ({COMPUTE_TYPE})")
    except Exception:
        print("CUDA unavailable, falling back to CPU (int8)")
        model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    return model


def print_runtime_context() -> None:
    print(f"Python executable: {sys.executable}")
    if os.name == "nt":
        cuda_dirs = get_windows_cuda_bin_dirs()
        print(f"Detected NVIDIA runtime dirs: {len(cuda_dirs)}")
        for d in cuda_dirs:
            print(f"  - {d}")


def print_cuda_fallback_reason(exc: Exception) -> None:
    print("GPU transcription failed; switching to CPU.")
    print(f"Reason: {type(exc).__name__}: {exc}")
    if os.name == "nt":
        print("Hint: verify this same Python has CUDA runtime DLL access.")


def is_cuda_runtime_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    cuda_markers = [
        "cublas64",
        "cudnn",
        "cuda",
        "ctranslate2",
        "cannot be loaded",
        "not found",
    ]
    return isinstance(exc, RuntimeError) and any(m in msg for m in cuda_markers)


def load_cpu_model():
    from faster_whisper import WhisperModel
    print("Falling back to CPU (int8) for transcription")
    return WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")


def transcribe(model, wav_path: Path) -> str:
    segments, _ = model.transcribe(str(wav_path), beam_size=5, language="en")
    return " ".join(seg.text for seg in segments).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Hey Eve — speech-to-text")
    parser.add_argument("file", nargs="?", type=Path,
                        help="WAV file to transcribe")
    parser.add_argument("--watch", action="store_true",
                        help=f"Watch {RECORDINGS_DIR} for new WAV files")
    args = parser.parse_args()

    if not args.file and not args.watch:
        parser.print_help()
        return

    print_runtime_context()
    model = load_model()
    using_cpu_fallback = False

    if args.file:
        try:
            text = transcribe(model, args.file)
        except Exception as exc:
            if not using_cpu_fallback and is_cuda_runtime_error(exc):
                print_cuda_fallback_reason(exc)
                model = load_cpu_model()
                using_cpu_fallback = True
                text = transcribe(model, args.file)
            else:
                raise
        print(f"\nTranscription: {text}")
        return

    print(f"\nWatching {RECORDINGS_DIR} for new recordings...")
    print("Press Ctrl+C to stop.\n")
    seen = set(RECORDINGS_DIR.glob("*.wav"))

    try:
        while True:
            time.sleep(0.5)
            current  = set(RECORDINGS_DIR.glob("*.wav"))
            new_files = sorted(current - seen)
            seen     = current
            for wav_path in new_files:
                print(f"  {wav_path.name}")
                try:
                    text = transcribe(model, wav_path)
                except Exception as exc:
                    if not using_cpu_fallback and is_cuda_runtime_error(exc):
                        print_cuda_fallback_reason(exc)
                        model = load_cpu_model()
                        using_cpu_fallback = True
                        text = transcribe(model, wav_path)
                    else:
                        raise
                print(f"  → {text}\n")
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
