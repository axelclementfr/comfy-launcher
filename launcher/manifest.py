"""Manifest decoding and validation (LAUNCHER_MANIFEST_B64)."""
from __future__ import annotations
import base64
import binascii
import json
from pathlib import Path

SUPPORTED_VERSIONS = {1}

DEFAULT_DIRS: dict[str, str] = {
    "checkpoint": "checkpoints",
    "lora": "loras",
    "vae": "vae",
    "controlnet": "controlnet",
    "upscaler": "upscale_models",
    "embedding": "embeddings",
    "clip": "clip",
    "unet": "unet",
}

REQUIRED_MODEL_FIELDS = {"type", "url", "filename"}


class ManifestError(ValueError):
    """Raised when the manifest cannot be parsed or is malformed."""


def parse_manifest_b64(b64: str) -> dict:
    """Decode and validate the LAUNCHER_MANIFEST_B64 env var.

    Returns the parsed manifest dict. Raises ManifestError on any problem.
    """
    if not b64 or not b64.strip():
        raise ManifestError("manifest is empty")

    try:
        decoded = base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError) as e:
        raise ManifestError(f"invalid base64: {e}") from e

    try:
        manifest = json.loads(decoded)
    except json.JSONDecodeError as e:
        raise ManifestError(f"invalid json: {e}") from e

    if "version" not in manifest:
        raise ManifestError("manifest missing required field: version")

    if manifest["version"] not in SUPPORTED_VERSIONS:
        raise ManifestError(
            f"unsupported manifest version: {manifest['version']} "
            f"(supported: {sorted(SUPPORTED_VERSIONS)})"
        )

    for i, model in enumerate(manifest.get("models", [])):
        missing = REQUIRED_MODEL_FIELDS - set(model.keys())
        if missing:
            raise ManifestError(f"model[{i}] missing required field(s): {sorted(missing)}")

    return manifest


def resolve_destination(item: dict, base: Path) -> Path:
    """Compute final filesystem path for a model item.

    Priority: explicit `dest_dir` > default by `type` > "_unknown" fallback.
    Always returns base/<dir>/<filename>.
    """
    if "dest_dir" in item and item["dest_dir"]:
        sub = item["dest_dir"].rstrip("/")
    else:
        sub = DEFAULT_DIRS.get(item["type"], "_unknown")
    return Path(base) / sub / item["filename"]
