"""Verify privately supplied model assets; no automatic downloads or guessed hashes."""

from __future__ import annotations

import argparse
from pathlib import Path

from packages.assets import Asset, verify  # noqa: F401 -- preserve existing verifier imports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path(".assets"))
    args = parser.parse_args()
    for name in verify(args.manifest, args.root):
        print(f"Verified: {name}")


if __name__ == "__main__":
    main()
