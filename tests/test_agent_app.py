"""Tests for the FastAPI agent app + auth middleware."""
import pytest
from fastapi.testclient import TestClient
from launcher.agent.app import build_app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("LAUNCHER_AGENT_TOKEN", "secret123")
    app = build_app()
    return TestClient(app)


class TestAuth:
    def test_missing_authorization_header_returns_401(self, client):
        r = client.get("/health")
        assert r.status_code == 401

    def test_wrong_token_returns_401(self, client):
        r = client.get("/health", headers={"Authorization": "Bearer wrong"})
        assert r.status_code == 401

    def test_correct_token_allows_request(self, client):
        r = client.get("/health", headers={"Authorization": "Bearer secret123"})
        assert r.status_code == 200

    def test_no_token_configured_rejects_all(self, monkeypatch):
        monkeypatch.delenv("LAUNCHER_AGENT_TOKEN", raising=False)
        from launcher.agent.app import build_app
        app = build_app()
        c = TestClient(app)
        r = c.get("/health", headers={"Authorization": "Bearer anything"})
        # If no token configured server-side, all requests rejected (security default)
        assert r.status_code == 503
