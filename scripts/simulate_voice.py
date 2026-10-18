"""Run reproducible voice scenarios over real loopback HTTP/WebSockets and fake audio."""

import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    raise SystemExit(
        subprocess.call(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "tests/test_voice_endtoend.py",
                "tests/test_voice_recovery.py",
                "tests/test_voice_alarm_recovery.py",
            ],
            cwd=root,
        )
    )
