"""Deterministic presence, failure, offline voice and journal acceptance; no devices."""

import subprocess
import sys

if __name__ == "__main__":
    raise SystemExit(
        subprocess.call(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "tests/test_presence.py",
                "tests/test_presence_integration.py",
            ]
        )
    )
