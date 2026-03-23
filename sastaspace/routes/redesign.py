# sastaspace/routes/redesign.py
"""Redesign and job status API endpoints."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.sse import EventSourceResponse, format_sse_event
from pydantic import BaseModel

from sastaspace.config import Settings
from sastaspace.database import JobStatus, find_site_by_url_hash, get_job, list_jobs, list_sites
from sastaspace.urls import is_valid_url, url_hash

from .sse import (
    redesign_requests_total,
    redesign_stream,
    redis_job_stream,
)

logger = logging.getLogger(__name__)


class RedesignRequest(BaseModel):
    """Incoming request body for the /redesign endpoint."""

    url: str
    tier: str = "free"  # "free" or "premium"
    model_provider: str = "claude"  # "claude" or "gemini"
    prompt: str = ""  # optional user instructions for the redesign


def create_redesign_router(
    settings: Settings,
    sites_dir,
    get_client_ip,
    is_localhost_fn,
    is_rate_limited_fn,
    record_request_fn,
    semaphore,
    deploy_fn,
    svc_ref: list,
) -> APIRouter:
    """Create the redesign router with injected dependencies."""
    r = APIRouter()

    @r.post("/redesign", response_model=None)
    async def redesign_endpoint(
        body: RedesignRequest, request: Request
    ) -> JSONResponse | EventSourceResponse:
        ip = get_client_ip(request)

        # Validate and normalize URL
        valid, normalized_or_error = is_valid_url(body.url)
        if not valid:
            return JSONResponse(
                status_code=400,
                content={"error": normalized_or_error},
            )
        body.url = normalized_or_error

        # Check for existing redesign (dedup by URL hash)
        uhash = url_hash(body.url)
        try:
            existing = await find_site_by_url_hash(uhash)
            if existing and existing.get("subdomain") and existing.get("job_id"):
                logger.info(
                    "DEDUP HIT | url=%s hash=%s subdomain=%s",
                    body.url,
                    uhash,
                    existing["subdomain"],
                )
                return JSONResponse(content={"job_id": existing["job_id"]})
        except (ConnectionError, OSError) as e:
            logger.warning("Failed to check dedup: %s", e)

        # Validate tier
        tier = body.tier if body.tier in ("free", "premium") else "free"
        model_provider = (
            body.model_provider if body.model_provider in ("claude", "gemini") else "claude"
        )

        # Rate limit check (localhost exempt)
        rate_limit_headers: dict[str, str] = {}
        if not is_localhost_fn(ip):
            limited, retry_after, remaining, reset_ts = is_rate_limited_fn(ip)
            rate_limit_headers = {
                "X-RateLimit-Limit": str(settings.rate_limit_max),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(reset_ts),
            }
            if limited:
                redesign_requests_total.labels(status="rate_limited").inc()
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": (
                            f"Rate limit exceeded. Try again in {retry_after // 60 + 1} minutes."
                        ),
                        "retry_after": retry_after,
                    },
                    headers={
                        **rate_limit_headers,
                        "Retry-After": str(retry_after),
                    },
                )

        # Record attempt (localhost exempt)
        if not is_localhost_fn(ip):
            record_request_fn(ip)
            rate_limit_headers["X-RateLimit-Remaining"] = str(
                max(0, int(rate_limit_headers.get("X-RateLimit-Remaining", "0")) - 1)
            )

        svc = svc_ref[0] if svc_ref else None

        # If Redis is available, use async job queue -- return job_id immediately
        if svc is not None:
            redesign_requests_total.labels(status="started").inc()
            job_id = await svc.enqueue(
                url=body.url,
                client_ip=ip,
                tier=tier,
                model_provider=model_provider,
                prompt=body.prompt,
            )
            return JSONResponse(content={"job_id": job_id}, headers=rate_limit_headers)

        # Fallback: inline processing (no Redis)
        if semaphore.locked():
            redesign_requests_total.labels(status="concurrency_limited").inc()
            return JSONResponse(
                status_code=429,
                content={"error": "A redesign is already in progress. Please wait and try again."},
                headers=rate_limit_headers,
            )

        redesign_requests_total.labels(status="started").inc()
        return EventSourceResponse(
            redesign_stream(
                body.url,
                settings,
                sites_dir,
                semaphore,
                deploy_fn,
                tier,
                model_provider,
                prompt=body.prompt,
            )
        )

    @r.get("/jobs/{job_id}/stream", response_model=None)
    async def job_stream_endpoint(job_id: str) -> EventSourceResponse:
        """SSE stream for a specific job. Reconnectable."""
        job = await get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")

        if job["status"] in (JobStatus.DONE.value, JobStatus.FAILED.value):

            async def _terminal():
                if job["status"] == JobStatus.DONE.value:
                    payload = json.dumps(
                        {
                            "job_id": job_id,
                            "subdomain": job.get("subdomain", ""),
                            "url": job.get("url", ""),
                            "progress": 100,
                        }
                    )
                    yield format_sse_event(data_str=payload, event="done")
                else:
                    payload = json.dumps(
                        {
                            "job_id": job_id,
                            "error": job.get("error", "Job failed"),
                        }
                    )
                    yield format_sse_event(data_str=payload, event="error")

            return EventSourceResponse(_terminal())

        svc = svc_ref[0] if svc_ref else None
        if svc is None:
            raise HTTPException(status_code=503, detail="Job queue unavailable")

        return EventSourceResponse(redis_job_stream(job_id, svc))

    @r.get("/jobs/{job_id}", response_model=None)
    async def get_job_status(job_id: str) -> JSONResponse:
        """Get the current status of a redesign job."""
        job = await get_job(job_id)
        if job is None:
            return JSONResponse(status_code=404, content={"error": "Job not found"})
        return JSONResponse(content=job)

    @r.get("/jobs", response_model=None)
    async def list_jobs_endpoint(
        status: str | None = None,
        limit: int = 50,
    ) -> JSONResponse:
        """List recent redesign jobs."""
        jobs = await list_jobs(limit=min(limit, 100), status=status)
        return JSONResponse(content={"jobs": jobs, "count": len(jobs)})

    @r.get("/sites", response_model=None)
    async def list_sites_endpoint(limit: int = 100) -> JSONResponse:
        """List all deployed redesigned sites."""
        sites_list = await list_sites(limit=min(limit, 200))
        return JSONResponse(content={"sites": sites_list, "count": len(sites_list)})

    return r
