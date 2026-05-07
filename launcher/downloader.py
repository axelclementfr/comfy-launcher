"""Download logic shared by boot script and agent."""
from __future__ import annotations
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from itertools import groupby
from pathlib import Path
from typing import Callable, Optional

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


@dataclass
class DownloadResult:
    success: bool
    bytes_written: int = 0
    elapsed_sec: float = 0.0
    error: str = ""


def download_one(
    url: str,
    dest: Path,
    timeout_sec: int = 600,
    progress_callback: Callable[[int], None] | None = None,
) -> DownloadResult:
    """Download `url` to `dest`. Auth headers + ?token= are applied automatically.

    `progress_callback` (if provided) is called with running byte count every chunk.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    fetch_url = build_url(url)
    headers = get_headers(url)
    req = urllib.request.Request(fetch_url, headers=headers)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp, open(dest, "wb") as out:
            total = 0
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                out.write(chunk)
                total += len(chunk)
                if progress_callback is not None:
                    progress_callback(total)
        return DownloadResult(
            success=True,
            bytes_written=total,
            elapsed_sec=time.time() - t0,
        )
    except urllib.error.HTTPError as e:
        if dest.exists():
            dest.unlink()
        body_snippet = ""
        try:
            body_snippet = e.read()[:200].decode(errors="replace")
        except Exception:
            pass
        return DownloadResult(
            success=False,
            error=f"HTTP {e.code} {e.reason} :: {body_snippet}",
            elapsed_sec=time.time() - t0,
        )
    except Exception as e:
        if dest.exists():
            dest.unlink()
        return DownloadResult(
            success=False,
            error=f"{type(e).__name__}: {e}",
            elapsed_sec=time.time() - t0,
        )


def download_many(
    items: list[dict],
    max_parallel: int = 3,
    progress_callback: Callable[[str, int], None] | None = None,
) -> list[DownloadResult]:
    """Download a list of {url, dest, priority?} dicts.

    Higher-priority items are downloaded first. Within the same priority,
    items are downloaded in parallel up to `max_parallel`.

    `progress_callback(url, bytes)` is called as each item progresses.
    """
    # Sort by priority descending (high first), stable order otherwise
    sorted_items = sorted(items, key=lambda x: -x.get("priority", 0))

    results: list[DownloadResult] = []
    for priority, group in groupby(sorted_items, key=lambda x: -x.get("priority", 0)):
        batch = list(group)
        with ThreadPoolExecutor(max_workers=max_parallel) as executor:
            futures = []
            for item in batch:
                cb = (lambda u: lambda b: progress_callback(u, b))(item["url"]) \
                    if progress_callback else None
                futures.append(executor.submit(
                    download_one,
                    url=item["url"],
                    dest=Path(item["dest"]),
                    progress_callback=cb,
                ))
            for f in futures:
                results.append(f.result())
    return results
