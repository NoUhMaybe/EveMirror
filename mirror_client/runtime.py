"""
24/7 mirror runtime supervisor.

- Runs wake listener continuously.
- Runs voice loop worker when Ollama is reachable.
- Restarts crashed subprocesses with backoff.
- Clears recordings once at session start, then preserves on restart.

Usage:
    python runtime.py
    python runtime.py --device 1
    python runtime.py --tts-speaker 64
"""

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from urllib.error import URLError
from urllib.request import urlopen

ROOT_DIR = Path(__file__).resolve().parent.parent
LISTEN_PATH = ROOT_DIR / "mirror_client" / "listen.py"
VOICE_LOOP_PATH = ROOT_DIR / "eve_agent" / "voice_loop.py"
EVENT_SERVER_PATH = ROOT_DIR / "eve_agent" / "dashboard_event_server.py"
RECORDINGS_DIR = ROOT_DIR / "mirror_client" / "recordings"
OLLAMA_HEALTH_URL = "http://127.0.0.1:11434/api/tags"

RESTART_DELAY_S = 3
MONITOR_TICK_S = 1


@dataclass
class ManagedProc:
    name: str
    command: List[str]
    cwd: Path
    process: Optional[subprocess.Popen] = None
    restart_count: int = 0

    def start(self) -> None:
        self.process = subprocess.Popen(self.command, cwd=str(self.cwd))
        print(f"[runtime] started {self.name} (pid={self.process.pid})")

    def stop(self) -> None:
        if not self.process:
            return
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        print(f"[runtime] stopped {self.name}")

    def exited(self) -> bool:
        return bool(self.process and self.process.poll() is not None)

    def exit_code(self) -> Optional[int]:
        if not self.process:
            return None
        return self.process.poll()


def ollama_ready(url: str) -> bool:
    try:
        with urlopen(url, timeout=2) as r:
            return r.status == 200
    except (URLError, TimeoutError):
        return False


def clear_recordings_once() -> None:
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    for wav in RECORDINGS_DIR.glob("*.wav"):
        wav.unlink()
    print(f"[runtime] cleared recordings in {RECORDINGS_DIR}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Eve mirror 24/7 runtime supervisor")
    parser.add_argument("--device", type=int, default=None, help="Input device index for listen.py")
    parser.add_argument("--ollama-url", default=OLLAMA_HEALTH_URL, help="Ollama health endpoint")
    parser.add_argument("--tts-model", type=Path, default=None, help="Optional Piper TTS model path")
    parser.add_argument("--tts-speaker", type=int, default=0, help="Piper speaker id for voice_loop")
    parser.add_argument("--no-tts", action="store_true", help="Disable local TTS in voice_loop")
    args = parser.parse_args()

    clear_recordings_once()

    listen_cmd = [sys.executable, str(LISTEN_PATH), "--no-clear-on-start"]
    if args.device is not None:
        listen_cmd.extend(["--device", str(args.device)])

    voice_cmd = [sys.executable, str(VOICE_LOOP_PATH), "--watch", "--tts-speaker", str(args.tts_speaker)]
    if args.tts_model is not None:
        voice_cmd.extend(["--tts-model", str(args.tts_model)])
    if args.no_tts:
        voice_cmd.append("--no-tts")
    event_server_cmd = [sys.executable, str(EVENT_SERVER_PATH)]

    listener = ManagedProc("listener", listen_cmd, ROOT_DIR)
    event_server = ManagedProc("event_server", event_server_cmd, ROOT_DIR)
    voice_worker = ManagedProc("voice_loop", voice_cmd, ROOT_DIR)

    print("[runtime] state=STARTING")
    event_server.start()
    listener.start()

    try:
        while True:
            if listener.exited():
                print(f"[runtime] listener exited code={listener.exit_code()} state=RECOVERING")
                listener.restart_count += 1
                time.sleep(RESTART_DELAY_S)
                listener.start()

            if event_server.exited():
                print(f"[runtime] event_server exited code={event_server.exit_code()} state=RECOVERING")
                event_server.restart_count += 1
                time.sleep(RESTART_DELAY_S)
                event_server.start()

            if voice_worker.process is None:
                if ollama_ready(args.ollama_url):
                    voice_worker.start()
                    print("[runtime] state=RUNNING")
                else:
                    print("[runtime] waiting for Ollama...")
            elif voice_worker.exited():
                print(f"[runtime] voice_loop exited code={voice_worker.exit_code()} state=RECOVERING")
                voice_worker.restart_count += 1
                time.sleep(RESTART_DELAY_S)
                if ollama_ready(args.ollama_url):
                    voice_worker.start()
                    print("[runtime] state=RUNNING")
                else:
                    voice_worker.process = None

            time.sleep(MONITOR_TICK_S)
    except KeyboardInterrupt:
        print("\n[runtime] state=STOPPING")
    finally:
        listener.stop()
        event_server.stop()
        voice_worker.stop()
        print("[runtime] state=STOPPED")


if __name__ == "__main__":
    main()
