"""Tests for launcher.boot — the one-shot boot script."""
import base64
import json
from pathlib import Path
import pytest
from launcher.boot import run_boot, BootResult


def _b64(manifest: dict) -> str:
    return base64.b64encode(json.dumps(manifest).encode()).decode()


class TestRunBoot:
    def test_empty_models_succeeds_immediately(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LAUNCHER_MANIFEST_B64", _b64({"version": 1, "models": []}))
        result = run_boot(models_base=tmp_path)
        assert result.success is True
        assert result.downloaded_count == 0

    def test_missing_manifest_env_fails_clearly(self, tmp_path, monkeypatch):
        monkeypatch.delenv("LAUNCHER_MANIFEST_B64", raising=False)
        result = run_boot(models_base=tmp_path)
        assert result.success is False
        assert "LAUNCHER_MANIFEST_B64" in result.error

    def test_invalid_manifest_fails_clearly(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LAUNCHER_MANIFEST_B64", "garbage!!")
        result = run_boot(models_base=tmp_path)
        assert result.success is False
        assert "manifest" in result.error.lower()

    def test_writes_sentinel_file_on_success(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LAUNCHER_MANIFEST_B64", _b64({"version": 1, "models": []}))
        sentinel = tmp_path / "boot_done"
        result = run_boot(models_base=tmp_path, sentinel_path=sentinel)
        assert result.success is True
        assert sentinel.exists()

    def test_no_sentinel_on_failure(self, tmp_path, monkeypatch):
        monkeypatch.delenv("LAUNCHER_MANIFEST_B64", raising=False)
        sentinel = tmp_path / "boot_done"
        result = run_boot(models_base=tmp_path, sentinel_path=sentinel)
        assert result.success is False
        assert not sentinel.exists()
