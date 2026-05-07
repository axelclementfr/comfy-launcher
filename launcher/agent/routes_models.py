"""GET /models + DELETE /models routes."""
from __future__ import annotations
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

MODELS_BASE = Path("/workspace/ComfyUI/models")


class DeletePayload(BaseModel):
    path: str  # relative to MODELS_BASE


@router.get("/models")
async def list_models():
    """List all files under MODELS_BASE recursively."""
    models = []
    if MODELS_BASE.exists():
        for f in MODELS_BASE.rglob("*"):
            if f.is_file():
                rel = f.relative_to(MODELS_BASE)
                models.append({
                    "path": str(rel),
                    "size_bytes": f.stat().st_size,
                })
    return {"models": models}


@router.delete("/models")
async def delete_model(payload: DeletePayload):
    """Delete a single file under MODELS_BASE. Path is relative."""
    # Reject path traversal
    if ".." in Path(payload.path).parts or Path(payload.path).is_absolute():
        raise HTTPException(status_code=400, detail="path traversal rejected")

    target = (MODELS_BASE / payload.path).resolve()
    base_resolved = MODELS_BASE.resolve()
    if not str(target).startswith(str(base_resolved)):
        raise HTTPException(status_code=400, detail="path outside MODELS_BASE")

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="file not found")

    target.unlink()
    return {"deleted": True, "path": payload.path}
