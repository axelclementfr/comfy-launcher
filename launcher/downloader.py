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
    """Inject ?token=XXX into Civitai URLs (their canonical auth method).

    Preserves URL fragments correctly: token goes before the fragment, not after.
    """
    if "civitai.com" in url:
        token = clean_token(os.environ.get("CIVITAI_TOKEN", ""))
        if token:
            if "#" in url:
                base, fragment = url.split("#", 1)
            else:
                base, fragment = url, ""
            sep = "&" if "?" in base else "?"
            result = f"{base}{sep}token={token}"
            if fragment:
                result = f"{result}#{fragment}"
            return result
    return url


def get_headers(url: str) -> dict[str, str]:
    """Browser User-Agent always; Bearer for HuggingFace; Civitai uses ?token=."""
    headers = {"User-Agent": UA}
    if "huggingface.co" in url:
        token = clean_token(os.environ.get("HF_TOKEN", ""))
        if token:
            headers["Authorization"] = f"Bearer {token}"
    return headers
