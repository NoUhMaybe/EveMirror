import hashlib
import json

import pytest

from scripts.verify_assets import verify


def test_private_asset_checksum_and_missing_file(tmp_path):
    artifact = tmp_path / "fixture.onnx"
    artifact.write_bytes(b"fixture only, not a model")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "wake": {
                    "path": "fixture.onnx",
                    "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                }
            }
        )
    )
    assert verify(manifest, tmp_path) == ["wake"]
    artifact.write_bytes(b"corrupt fixture")
    with pytest.raises(ValueError, match="checksum"):
        verify(manifest, tmp_path)
    artifact.unlink()
    with pytest.raises(ValueError, match="missing"):
        verify(manifest, tmp_path)


def test_asset_paths_are_contained_and_hashes_required(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"wake": {"path": "../outside", "sha256": "a" * 64}}))
    with pytest.raises(ValueError, match="leaves"):
        verify(manifest, tmp_path)
    manifest.write_text(json.dumps({"wake": {"path": "fixture.onnx", "sha256": "unknown"}}))
    with pytest.raises(ValueError):
        verify(manifest, tmp_path)
