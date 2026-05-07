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


from launcher.downloader import download_many


class TestDownloadMany:
    def test_downloads_all_models_in_parallel(self, tmp_path: Path, monkeypatch):
        monkeypatch.delenv("CIVITAI_TOKEN", raising=False)
        items = [
            {"url": f"https://huggingface.co/m{i}", "dest": tmp_path / f"m{i}.bin"}
            for i in range(3)
        ]
        fake_response = MagicMock()
        fake_response.__enter__ = MagicMock(return_value=fake_response)
        fake_response.__exit__ = MagicMock(return_value=False)
        fake_response.read = MagicMock(side_effect=[b"data", b""] * 3)

        with patch("urllib.request.urlopen", return_value=fake_response):
            results = download_many(items, max_parallel=3)

        assert len(results) == 3
        assert all(r.success for r in results)

    def test_respects_priority_order(self, tmp_path: Path):
        # Higher priority is downloaded first
        call_order = []

        def fake_urlopen(req, timeout=None):
            call_order.append(req.full_url)
            m = MagicMock()
            m.__enter__ = MagicMock(return_value=m)
            m.__exit__ = MagicMock(return_value=False)
            m.read = MagicMock(side_effect=[b"data", b""])
            return m

        items = [
            {"url": "https://huggingface.co/low", "dest": tmp_path / "low.bin", "priority": 0},
            {"url": "https://huggingface.co/high", "dest": tmp_path / "high.bin", "priority": 10},
            {"url": "https://huggingface.co/mid", "dest": tmp_path / "mid.bin", "priority": 5},
        ]

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            results = download_many(items, max_parallel=1)  # serial to enforce order

        # Priority 10, then 5, then 0
        assert call_order == [
            "https://huggingface.co/high",
            "https://huggingface.co/mid",
            "https://huggingface.co/low",
        ]
