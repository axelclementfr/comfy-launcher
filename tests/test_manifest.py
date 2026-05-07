"""Tests for launcher.manifest."""
import base64
import json
import pytest
from launcher.manifest import (
    parse_manifest_b64,
    resolve_destination,
    DEFAULT_DIRS,
    ManifestError,
)


class TestParseManifestB64:
    def test_valid_minimal(self):
        m = {"version": 1, "models": []}
        b64 = base64.b64encode(json.dumps(m).encode()).decode()
        parsed = parse_manifest_b64(b64)
        assert parsed["version"] == 1
        assert parsed["models"] == []

    def test_missing_version_raises(self):
        m = {"models": []}
        b64 = base64.b64encode(json.dumps(m).encode()).decode()
        with pytest.raises(ManifestError, match="version"):
            parse_manifest_b64(b64)

    def test_unsupported_version_raises(self):
        m = {"version": 99, "models": []}
        b64 = base64.b64encode(json.dumps(m).encode()).decode()
        with pytest.raises(ManifestError, match="unsupported"):
            parse_manifest_b64(b64)

    def test_invalid_base64_raises(self):
        with pytest.raises(ManifestError, match="base64"):
            parse_manifest_b64("not-base64!!!")

    def test_invalid_json_raises(self):
        b64 = base64.b64encode(b"not json").decode()
        with pytest.raises(ManifestError, match="json"):
            parse_manifest_b64(b64)

    def test_missing_required_model_field_raises(self):
        m = {"version": 1, "models": [{"type": "checkpoint", "url": "x"}]}  # missing filename
        b64 = base64.b64encode(json.dumps(m).encode()).decode()
        with pytest.raises(ManifestError, match="filename"):
            parse_manifest_b64(b64)

    def test_empty_string_raises(self):
        with pytest.raises(ManifestError, match="empty"):
            parse_manifest_b64("")


class TestResolveDestination:
    def test_default_checkpoint_dir(self, tmp_path):
        item = {"type": "checkpoint", "filename": "model.safetensors"}
        dest = resolve_destination(item, base=tmp_path)
        assert dest == tmp_path / "checkpoints" / "model.safetensors"

    def test_custom_dest_dir_overrides_default(self, tmp_path):
        item = {"type": "checkpoint", "filename": "model.safetensors", "dest_dir": "checkpoints/sdxl/"}
        dest = resolve_destination(item, base=tmp_path)
        assert dest == tmp_path / "checkpoints" / "sdxl" / "model.safetensors"

    def test_unknown_type_uses_unknown_dir(self, tmp_path):
        item = {"type": "weird_unsupported", "filename": "x.bin"}
        dest = resolve_destination(item, base=tmp_path)
        assert dest == tmp_path / "_unknown" / "x.bin"

    def test_default_dirs_covers_8_known_types(self):
        expected = {"checkpoint", "lora", "vae", "controlnet",
                    "upscaler", "embedding", "clip", "unet"}
        assert set(DEFAULT_DIRS.keys()) == expected
