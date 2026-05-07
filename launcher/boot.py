"""One-shot boot script: decode manifest, download models, write sentinel."""
from __future__ import annotations
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from launcher.downloader import download_many, DownloadResult
from launcher.manifest import parse_manifest_b64, resolve_destination, ManifestError

DEFAULT_MODELS_BASE = Path("/workspace/ComfyUI/models")
DEFAULT_SENTINEL = Path("/var/run/launcher_boot_done")

logger = logging.getLogger("launcher.boot")


@dataclass
class BootResult:
    success: bool
    downloaded_count: int = 0
    failed_count: int = 0
    error: str = ""


def run_boot(
    models_base: Path = DEFAULT_MODELS_BASE,
    sentinel_path: Path | None = None,
) -> BootResult:
    """Decode LAUNCHER_MANIFEST_B64, download all models, write sentinel."""
    b64 = os.environ.get("LAUNCHER_MANIFEST_B64", "")
    if not b64:
        return BootResult(success=False, error="LAUNCHER_MANIFEST_B64 env var missing")

    try:
        manifest = parse_manifest_b64(b64)
    except ManifestError as e:
        return BootResult(success=False, error=f"manifest error: {e}")

    items = []
    for model in manifest["models"]:
        items.append({
            "url": model["url"],
            "dest": resolve_destination(model, base=models_base),
            "priority": model.get("priority", 0),
        })

    logger.info("boot: %d models to download", len(items))
    results: list[DownloadResult] = download_many(
        items,
        max_parallel=3,
        progress_callback=lambda url, n: logger.info("dl %s: %d bytes", url, n),
    )

    succ = sum(1 for r in results if r.success)
    fail = len(results) - succ

    if fail == 0:
        if sentinel_path is not None:
            sentinel_path.parent.mkdir(parents=True, exist_ok=True)
            sentinel_path.write_text("ok\n")
        logger.info("boot complete: %d/%d", succ, len(results))
        return BootResult(success=True, downloaded_count=succ, failed_count=0)

    return BootResult(
        success=False,
        downloaded_count=succ,
        failed_count=fail,
        error=f"{fail}/{len(results)} downloads failed",
    )


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = run_boot(sentinel_path=DEFAULT_SENTINEL)
    if not result.success:
        logger.error("boot failed: %s", result.error)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
