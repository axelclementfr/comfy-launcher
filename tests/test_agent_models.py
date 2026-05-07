"""Tests for GET /models and DELETE /models."""
import pytest
from pathlib import Path
from fastapi.testclient import TestClient


@pytest.fixture
def client_with_models(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LAUNCHER_AGENT_TOKEN", "secret123")
    # Create fake models tree
    base = tmp_path / "models"
    (base / "checkpoints").mkdir(parents=True)
    (base / "loras").mkdir(parents=True)
    (base / "checkpoints" / "model_a.safetensors").write_bytes(b"x" * 1024)
    (base / "loras" / "lora_b.safetensors").write_bytes(b"y" * 512)

    monkeypatch.setattr("launcher.agent.routes_models.MODELS_BASE", base)
    from launcher.agent.app import build_app
    app = build_app()
    return TestClient(app), base


def _auth():
    return {"Authorization": "Bearer secret123"}


class TestListModels:
    def test_lists_all_files(self, client_with_models):
        client, _ = client_with_models
        r = client.get("/models", headers=_auth())
        assert r.status_code == 200
        body = r.json()
        paths = {m["path"] for m in body["models"]}
        assert "checkpoints/model_a.safetensors" in paths
        assert "loras/lora_b.safetensors" in paths

    def test_includes_size(self, client_with_models):
        client, _ = client_with_models
        r = client.get("/models", headers=_auth())
        body = r.json()
        m = next(m for m in body["models"] if m["path"] == "checkpoints/model_a.safetensors")
        assert m["size_bytes"] == 1024


class TestDeleteModel:
    def test_delete_removes_file(self, client_with_models):
        client, base = client_with_models
        target = base / "loras" / "lora_b.safetensors"
        assert target.exists()
        r = client.request("DELETE", "/models",
                           json={"path": "loras/lora_b.safetensors"},
                           headers=_auth())
        assert r.status_code == 200
        assert not target.exists()

    def test_delete_unknown_returns_404(self, client_with_models):
        client, _ = client_with_models
        r = client.request("DELETE", "/models",
                           json={"path": "loras/does_not_exist.bin"},
                           headers=_auth())
        assert r.status_code == 404

    def test_delete_rejects_path_traversal(self, client_with_models):
        client, base = client_with_models
        r = client.request("DELETE", "/models",
                           json={"path": "../../etc/passwd"},
                           headers=_auth())
        assert r.status_code == 400
