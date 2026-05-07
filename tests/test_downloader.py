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

    def test_civitai_with_fragment_preserves_fragment(self, monkeypatch):
        monkeypatch.setenv("CIVITAI_TOKEN", "secret123")
        url = "https://civitai.com/api/download/models/6297#section"
        assert build_url(url) == "https://civitai.com/api/download/models/6297?token=secret123#section"


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


import urllib.error
from pathlib import Path
from unittest.mock import patch, MagicMock
from launcher.downloader import download_one, DownloadResult


class TestDownloadOne:
    def test_successful_download_writes_file(self, tmp_path: Path, monkeypatch):
        monkeypatch.delenv("CIVITAI_TOKEN", raising=False)
        dest = tmp_path / "model.safetensors"
        fake_response = MagicMock()
        fake_response.__enter__ = MagicMock(return_value=fake_response)
        fake_response.__exit__ = MagicMock(return_value=False)
        # Simulate 2 chunks then EOF
        fake_response.read = MagicMock(side_effect=[b"x" * 1024, b"y" * 512, b""])

        with patch("urllib.request.urlopen", return_value=fake_response):
            result = download_one(
                url="https://huggingface.co/foo/bar",
                dest=dest,
            )

        assert result.success is True
        assert result.bytes_written == 1536
        assert dest.read_bytes() == b"x" * 1024 + b"y" * 512

    def test_http_error_returns_failure(self, tmp_path: Path):
        dest = tmp_path / "model.safetensors"
        err = urllib.error.HTTPError(
            url="https://example.com", code=403, msg="Forbidden",
            hdrs=None, fp=None,
        )

        with patch("urllib.request.urlopen", side_effect=err):
            result = download_one(
                url="https://example.com/model",
                dest=dest,
            )

        assert result.success is False
        assert "403" in result.error
        assert not dest.exists()

    def test_creates_parent_directory(self, tmp_path: Path):
        dest = tmp_path / "deep" / "nested" / "model.safetensors"
        fake_response = MagicMock()
        fake_response.__enter__ = MagicMock(return_value=fake_response)
        fake_response.__exit__ = MagicMock(return_value=False)
        fake_response.read = MagicMock(side_effect=[b"data", b""])

        with patch("urllib.request.urlopen", return_value=fake_response):
            result = download_one(
                url="https://huggingface.co/foo/bar",
                dest=dest,
            )

        assert result.success is True
        assert dest.parent.is_dir()
        assert dest.read_bytes() == b"data"
