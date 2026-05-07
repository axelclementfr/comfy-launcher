"""Tests for launcher.agent.jobs — in-memory job tracking."""
import pytest
from launcher.agent.jobs import JobRegistry, Job, JobStatus


class TestJobRegistry:
    def test_create_job_returns_uuid(self):
        reg = JobRegistry()
        job = reg.create({"models": [{"url": "x", "type": "checkpoint", "filename": "y"}]})
        assert job.id
        assert len(job.id) > 8  # UUID-ish
        assert job.status == JobStatus.PENDING

    def test_get_existing_job(self):
        reg = JobRegistry()
        job = reg.create({"models": []})
        retrieved = reg.get(job.id)
        assert retrieved is job

    def test_get_unknown_returns_none(self):
        reg = JobRegistry()
        assert reg.get("unknown-id") is None

    def test_update_status(self):
        reg = JobRegistry()
        job = reg.create({"models": []})
        reg.update(job.id, status=JobStatus.DOWNLOADING, progress_pct=42)
        retrieved = reg.get(job.id)
        assert retrieved.status == JobStatus.DOWNLOADING
        assert retrieved.progress_pct == 42

    def test_update_unknown_raises(self):
        reg = JobRegistry()
        with pytest.raises(KeyError):
            reg.update("unknown", status=JobStatus.DONE)

    def test_list_returns_all_jobs(self):
        reg = JobRegistry()
        j1 = reg.create({"models": []})
        j2 = reg.create({"models": []})
        all_jobs = reg.list()
        ids = {j.id for j in all_jobs}
        assert ids == {j1.id, j2.id}
