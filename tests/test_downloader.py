"""Tests for launcher.downloader."""
import pytest
from launcher.downloader import clean_token, build_url, get_headers, UA


class TestCleanToken:
    def test_strips_leading_trailing_whitespace(self):
        assert clean_token("  abc123  ") == "abc123"

    def test_strips_double_quotes(self):
        assert clean_token('"abc123"') == "abc123"

    def test_strips_single_quotes(self):
        assert clean_token("'abc123'") == "abc123"

    def test_empty_string_returns_empty(self):
        assert clean_token("") == ""

    def test_none_returns_empty(self):
        assert clean_token(None) == ""

    def test_only_internal_chars_unchanged(self):
        assert clean_token("ab'cd") == "ab'cd"


class TestBuildUrl:
    def test_civitai_appends_token_query_param(self, monkeypatch):
        monkeypatch.setenv("CIVITAI_TOKEN", "secret123")
        url = "https://civitai.com/api/download/models/6297"
        assert build_url(url) == "https://civitai.com/api/download/models/6297?token=secret123"

    def test_civitai_with_existing_query_uses_ampersand(self, monkeypatch):
        monkeypatch.setenv("CIVITAI_TOKEN", "secret123")
        url = "https://civitai.com/api/download/models/6297?type=Model"
        assert build_url(url) == "https://civitai.com/api/download/models/6297?type=Model&token=secret123"

    def test_civitai_without_token_unchanged(self, monkeypatch):
        monkeypatch.delenv("CIVITAI_TOKEN", raising=False)
        url = "https://civitai.com/api/download/models/6297"
        assert build_url(url) == url

    def test_civitai_strips_token_quotes(self, monkeypatch):
        monkeypatch.setenv("CIVITAI_TOKEN", '"secret123"')
        url = "https://civitai.com/api/download/models/6297"
        assert build_url(url) == "https://civitai.com/api/download/models/6297?token=secret123"

    def test_huggingface_url_unchanged(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "hf_secret")
        url = "https://huggingface.co/foo/bar/resolve/main/file.safetensors"
        assert build_url(url) == url


class TestGetHeaders:
    def test_user_agent_always_set(self, monkeypatch):
        monkeypatch.delenv("CIVITAI_TOKEN", raising=False)
        monkeypatch.delenv("HF_TOKEN", raising=False)
        h = get_headers("https://example.com/file")
        assert h["User-Agent"] == UA

    def test_huggingface_adds_bearer(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "hf_secret")
        h = get_headers("https://huggingface.co/foo/bar")
        assert h["Authorization"] == "Bearer hf_secret"

    def test_huggingface_no_token_no_auth_header(self, monkeypatch):
        monkeypatch.delenv("HF_TOKEN", raising=False)
        h = get_headers("https://huggingface.co/foo/bar")
        assert "Authorization" not in h

    def test_civitai_does_not_set_authorization_header(self, monkeypatch):
        monkeypatch.setenv("CIVITAI_TOKEN", "secret")
        h = get_headers("https://civitai.com/api/download/models/1")
        assert "Authorization" not in h

    def test_huggingface_strips_token_quotes(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", '"hf_secret"')
        h = get_headers("https://huggingface.co/foo")
        assert h["Authorization"] == "Bearer hf_secret"
