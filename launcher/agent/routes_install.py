"""POST /install + GET /jobs/{id} routes."""
from __future__ import annotations
import asyncio
from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from launcher.downloader import download_one
from launcher.manifest import resolve_destination, REQUIRED_MODEL_FIELDS
from launcher.agent.jobs import JobRegistry, JobStatus

router = APIRouter()
registry = JobRegistry()

MODELS_BASE = Path("/workspace/ComfyUI/models")


class InstallPayload(BaseModel):
    models: list[dict] = Field(..., min_length=1)


@router.post("/install", status_code=status.HTTP_202_ACCEPTED)
async def install(payload: InstallPayload):
    # Validate required fields
    for i, m in enumerate(payload.models):
        missing = REQUIRED_MODEL_FIELDS - set(m.keys())
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"model[{i}] missing required field(s): {sorted(missing)}",
            )

    job = registry.create(payload.model_dump())
    asyncio.create_task(_run_job(job.id, payload.models))
    return {"job_id": job.id}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    job = registry.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return {
        "job_id": job.id,
        "status": job.status.value,
        "progress_pct": job.progress_pct,
        "speed_mbps": job.speed_mbps,
        "error": job.error or None,
    }


async def _run_job(job_id: str, models: list[dict]) -> None:
    """Background DL of all models in the job. Updates registry as it goes."""
    registry.update(job_id, status=JobStatus.DOWNLOADING)
    total = len(models)
    done = 0
    last_err = ""
    for m in models:
        dest = resolve_destination(m, base=MODELS_BASE)
        # Run blocking DL in default executor
        result = await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: download_one(url=m["url"], dest=dest),
        )
        if result.success:
            done += 1
            registry.update(job_id, progress_pct=int(100 * done / total))
        else:
            last_err = result.error
            registry.update(job_id, status=JobStatus.FAILED, error=last_err)
            return
    registry.update(job_id, status=JobStatus.DONE, progress_pct=100)
