"""Download logic shared by boot script and agent."""
from __future__ import annotations
import os
from typing import Optional

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def clean_token(raw: Optional[str]) -> str:
    """Strip whitespace and surrounding quotes from a token env var.

    vast.ai's UI sometimes stores values with literal quote chars; we strip
    them defensively so the token is always usable as-is.
    """
    if not raw:
        return ""
    return raw.strip().strip('"').strip("'")


def build_url(url: str) -> str:
    """Inject ?token=XXX into Civitai URLs (their canonical auth method)."""
    if "civitai.com" in url:
        token = clean_token(os.environ.get("CIVITAI_TOKEN", ""))
        if token:
            sep = "&" if "?" in url else "?"
            return f"{url}{sep}token={token}"
    return url


def get_headers(url: str) -> dict[str, str]:
    """Browser User-Agent always; Bearer for HuggingFace; Civitai uses ?token=."""
    headers = {"User-Agent": UA}
    if "huggingface.co" in url:
        token = clean_token(os.environ.get("HF_TOKEN", ""))
        if token:
            headers["Authorization"] = f"Bearer {token}"
    return headers
