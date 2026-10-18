"""Trusted, administrator-supplied local assets. Never download at runtime."""

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class Asset(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str
    sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")


class AssetCatalog:
    def __init__(self, manifest: Path, root: Path):
        if manifest.stat().st_size > 2_000_000:
            raise ValueError("Asset manifest exceeds limit")
        self.root = root.resolve()
        self.assets = {
            key: Asset.model_validate(value)
            for key, value in json.loads(manifest.read_text(encoding="utf-8")).items()
        }
        if not self.assets or len(self.assets) > 10000:
            raise ValueError("Invalid asset manifest size")

    def path(self, name):
        asset = self.assets[name]
        path = (self.root / asset.path).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Asset path leaves the configured directory")
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError("Asset missing, empty or outside root")
        with path.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        if digest.lower() != asset.sha256.lower():
            raise ValueError("Asset checksum mismatch")
        return path

    def directory(self, relative):
        directory = (self.root / relative).resolve()
        if not directory.is_relative_to(self.root) or not directory.is_dir():
            raise ValueError("Model directory outside asset root or missing")
        verified = {
            self.path(key)
            for key, asset in self.assets.items()
            if (self.root / asset.path).resolve().is_relative_to(directory)
        }
        actual = {path.resolve() for path in directory.rglob("*") if path.is_file()}
        if not actual or actual != verified:
            raise ValueError("Every model-directory file must be in the trusted manifest")
        return directory


def verify(manifest: Path, root: Path) -> list[str]:
    catalog = AssetCatalog(manifest, root)
    for key in catalog.assets:
        catalog.path(key)
    return list(catalog.assets)
