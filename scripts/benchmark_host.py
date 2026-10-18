"""Sample Linux process/thermal counters without audio, serial or service changes."""

import argparse
import json
import time
from pathlib import Path


def sample(pids, root=Path("/proc"), sys_root=Path("/sys")):
    processes = {}
    for pid in pids:
        try:
            status = (root / str(pid) / "status").read_text().splitlines()
            stat = (root / str(pid) / "stat").read_text().rsplit(")", 1)[1].split()
            processes[str(pid)] = {
                "rss": next(
                    (line.split(":", 1)[1].strip() for line in status if line.startswith("VmRSS:")),
                    None,
                ),
                "user_ticks": int(stat[11]),
                "system_ticks": int(stat[12]),
            }
        except (OSError, ValueError, IndexError):
            processes[str(pid)] = {"unavailable": True}
    temperatures = {}
    for path in (sys_root / "class/thermal").glob("thermal_zone*/temp"):
        try:
            temperatures[path.parent.name] = int(path.read_text()) / 1000
        except (OSError, ValueError):
            pass
    return {"monotonic": time.monotonic(), "processes": processes, "temperature_c": temperatures}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, action="append", default=[])
    parser.add_argument("--seconds", type=int, default=60)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 28800 or any(pid <= 0 for pid in args.pid):
        parser.error("Positive PIDs and 1..28800 seconds required")
    for _ in range(args.seconds):
        print(json.dumps(sample(args.pid)), flush=True)
        time.sleep(1)


if __name__ == "__main__":
    main()
