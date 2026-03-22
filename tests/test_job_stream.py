# tests/test_job_stream.py
"""Tests for job_id-based tracking endpoints."""

from unittest.mock import AsyncMock, patch

from sastaspace.database import JobStatus, create_job, update_job


async def test_redesign_returns_job_id(test_client):
    """POST /redesign returns { job_id } immediately when Redis available."""
    with patch("sastaspace.server.svc") as mock_svc:
        mock_svc.enqueue = AsyncMock(return_value="test-job-123")
        resp = test_client.post("/redesign", json={"url": "https://example.com"}, timeout=10)
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == "test-job-123"


async def test_job_stream_404_for_unknown_job(test_client):
    """GET /jobs/{job_id}/stream returns 404 when job not in DB."""
    with patch("sastaspace.server.svc"):
        resp = test_client.get("/jobs/nonexistent-job/stream", timeout=10)
        assert resp.status_code == 404


async def test_job_stream_serves_done_job(test_client):
    """GET /jobs/{job_id}/stream returns done event immediately if job already complete."""
    job_id = "done-job-1"
    await create_job(job_id=job_id, url="https://example.com", client_ip="1.2.3.4")
    await update_job(job_id, status=JobStatus.DONE.value, subdomain="example-com", progress=100)

    with patch("sastaspace.server.svc"):
        resp = test_client.get(f"/jobs/{job_id}/stream", timeout=10)
        assert resp.status_code == 200
