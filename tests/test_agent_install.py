"""Tests for POST /install and GET /jobs/{id}."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("LAUNCHER_AGENT_TOKEN", "secret123")
    from launcher.agent.app import build_app
    app = build_app()
    return TestClient(app)


def _auth():
    return {"Authorization": "Bearer secret123"}


class TestInstall:
    def test_install_returns_job_id(self, client):
        payload = {
            "models": [{"type": "lora", "url": "https://huggingface.co/x", "filename": "y.safetensors"}]
        }
        r = client.post("/install", json=payload, headers=_auth())
        assert r.status_code == 202
        body = r.json()
        assert "job_id" in body
        assert len(body["job_id"]) > 8

    def test_install_invalid_payload_returns_400(self, client):
        # Missing required field "filename"
        payload = {"models": [{"type": "lora", "url": "https://x"}]}
        r = client.post("/install", json=payload, headers=_auth())
        assert r.status_code == 400

    def test_get_job_unknown_returns_404(self, client):
        r = client.get("/jobs/unknown-uuid", headers=_auth())
        assert r.status_code == 404

    def test_get_job_returns_status(self, client):
        payload = {"models": [{"type": "lora", "url": "https://huggingface.co/x", "filename": "y.bin"}]}
        post_r = client.post("/install", json=payload, headers=_auth())
        job_id = post_r.json()["job_id"]
        get_r = client.get(f"/jobs/{job_id}", headers=_auth())
        assert get_r.status_code == 200
        body = get_r.json()
        assert body["status"] in ("pending", "downloading", "done", "failed")
        assert "progress_pct" in body
