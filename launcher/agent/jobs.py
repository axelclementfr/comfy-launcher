"""In-memory job tracking for the launcher agent."""
from __future__ import annotations
import threading
import uuid
from dataclasses import dataclass
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    DONE = "done"
    FAILED = "failed"


@dataclass
class Job:
    id: str
    payload: dict
    status: JobStatus = JobStatus.PENDING
    progress_pct: int = 0
    speed_mbps: float = 0.0
    error: str = ""


class JobRegistry:
    """Thread-safe in-memory store for active and recent jobs."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self, payload: dict) -> Job:
        job = Job(id=str(uuid.uuid4()), payload=payload)
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **fields) -> None:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            job = self._jobs[job_id]
            for k, v in fields.items():
                setattr(job, k, v)

    def list(self) -> list[Job]:
        with self._lock:
            return list(self._jobs.values())
