"""Shared fixtures for the test suite."""
import pytest
from pathlib import Path


@pytest.fixture
def tmp_models_dir(tmp_path: Path) -> Path:
    """Create a fake /workspace/ComfyUI/models/ tree under tmp_path."""
    base = tmp_path / "ComfyUI" / "models"
    for sub in ["checkpoints", "loras", "vae", "controlnet", "upscale_models",
                "embeddings", "clip", "unet"]:
        (base / sub).mkdir(parents=True, exist_ok=True)
    return base
