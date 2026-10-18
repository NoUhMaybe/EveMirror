"""Verify privately supplied model assets; no automatic downloads or guessed hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class Asset(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str
    sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")


def verify(manifest: Path, root: Path) -> list[str]:
    assets = {
        name: Asset.model_validate(value)
        for name, value in json.loads(
            manifest.read_text(encoding="utf-8"),
        ).items()
    }
    root = root.resolve()
    checked = []
    for name, asset in assets.items():
        path = (root / asset.path).resolve()
        if not path.is_relative_to(root):
            raise ValueError(f"Asset path leaves the configured directory: {name}")
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"Asset missing or empty: {name}")
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest.lower() != asset.sha256.lower():
            raise ValueError(f"Asset checksum mismatch: {name}")
        checked.append(name)
    if not checked:
        raise ValueError("Asset manifest is empty")
    return checked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path(".assets"))
    args = parser.parse_args()
    for name in verify(args.manifest, args.root):
        print(f"Verified: {name}")


if __name__ == "__main__":
    main()
