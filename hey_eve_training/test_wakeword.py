"""
Live microphone test for the "hey eve" wake word model.
Run this script, then say "hey eve" into your microphone.
Press Ctrl+C to stop.
"""

import sys
import numpy as np
import sounddevice as sd
import openwakeword
from openwakeword.model import Model

MODEL_PATH = r"C:\Users\Work\Downloads\hey_eve_training\my_custom_model\hey_eve.onnx"
SAMPLE_RATE = 16000
CHUNK_SIZE  = 1280   # 80ms at 16kHz — recommended by openWakeWord
THRESHOLD   = 0.3    # detection confidence threshold (0–1); raise to reduce false positives

def list_devices():
    print("\nAvailable input devices:")
    for i, d in enumerate(sd.query_devices()):
        if d['max_input_channels'] > 0:
            print(f"  [{i}] {d['name']}")
    print()

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", type=int, default=None,
                        help="Input device index (run with --list-devices to see options)")
    parser.add_argument("--list-devices", action="store_true")
    args = parser.parse_args()

    if args.list_devices:
        list_devices()
        return
    print(f"Loading model: {MODEL_PATH}")
    oww = Model(wakeword_models=[MODEL_PATH], inference_framework="onnx")
    print(f"\nListening for 'hey eve'... (threshold={THRESHOLD})")
    if args.device is not None:
        print(f"Using device [{args.device}]: {sd.query_devices(args.device)['name']}")
    print("Say the wake word clearly. Press Ctrl+C to stop.\n")

    buffer = np.zeros(0, dtype=np.int16)

    def audio_callback(indata, frames, time_info, status):
        nonlocal buffer
        # Convert float32 input to int16
        chunk = (indata[:, 0] * 32767).astype(np.int16)
        buffer = np.concatenate([buffer, chunk])

        # Process in CHUNK_SIZE windows
        while len(buffer) >= CHUNK_SIZE:
            window = buffer[:CHUNK_SIZE]
            buffer = buffer[CHUNK_SIZE:]

            prediction = oww.predict(window)
            for ww_name, score in prediction.items():
                if score >= THRESHOLD:
                    print(f"  ✓ Wake word detected! score={score:.3f}  ({ww_name})")
                elif score > 0.2:
                    # Show near-misses so you can tune the threshold
                    print(f"  ~ Near miss:  score={score:.3f}", end="\r")

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=CHUNK_SIZE,
        device=args.device,
        callback=audio_callback,
    ):
        try:
            while True:
                sd.sleep(100)
        except KeyboardInterrupt:
            print("\nStopped.")

if __name__ == "__main__":
    main()
