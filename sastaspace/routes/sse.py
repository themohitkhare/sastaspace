# sastaspace/routes/sse.py
"""SSE streaming logic for the redesign pipeline."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from collections.abc import AsyncGenerator
from uuid import uuid4

from fastapi.sse import format_sse_event
from prometheus_client import Counter, Gauge, Histogram

from sastaspace.config import Settings
from sastaspace.crawler import crawl
from sastaspace.database import JobStatus, create_job, update_job
from sastaspace.html_utils import inject_badge
from sastaspace.redesigner import run_redesign

logger = logging.getLogger(__name__)

# Business metrics (module-level so they survive app reloads)
sites_deployed_gauge = Gauge("sites_deployed_total", "Number of sites currently deployed")
redesign_requests_total = Counter(
    "redesign_requests_total",
    "Total redesign requests received",
    ["status"],  # "started" | "rate_limited" | "concurrency_limited"
)
redesign_latency_seconds = Histogram(
    "redesign_latency_seconds",
    "End-to-end redesign duration in seconds",
    buckets=[10, 30, 60, 120, 300, 600],
)
redesign_errors_total = Counter(
    "redesign_errors_total",
    "Total redesign errors",
    ["phase"],  # "crawl" | "redesign" | "deploy" | "unknown"
)
active_connections_gauge = Gauge(
    "active_sse_connections",
    "Number of active SSE streaming connections",
)

# Track active SSE connection tasks for graceful shutdown drain
active_sse_tasks: set[asyncio.Task] = set()


def _sanitize_html(html_str: str) -> str:
    """Strip inline event handlers and javascript: URLs from AI-generated HTML."""
    # Strip inline event handlers (on*="...")
    html_str = re.sub(
        r'\s+on\w+\s*=\s*"[^"]*"',
        "",
        html_str,
        flags=re.IGNORECASE,
    )
    html_str = re.sub(
        r"\s+on\w+\s*=\s*'[^']*'",
        "",
        html_str,
        flags=re.IGNORECASE,
    )
    # Strip javascript: URLs in href/src attributes
    html_str = re.sub(
        r'(href|src)\s*=\s*"javascript:[^"]*"',
        r'\1=""',
        html_str,
        flags=re.IGNORECASE,
    )
    html_str = re.sub(
        r"(href|src)\s*=\s*'javascript:[^']*'",
        r"\1=''",
        html_str,
        flags=re.IGNORECASE,
    )
    return html_str


async def redesign_stream(
    url: str,
    settings: Settings,
    sites_dir,
    semaphore: asyncio.Semaphore,
    deploy_fn,
    tier: str = "free",
    model_provider: str = "claude",
) -> AsyncGenerator[bytes, None]:
    """SSE stream (inline fallback when Redis is unavailable)."""
    task = asyncio.current_task()
    if task:
        active_sse_tasks.add(task)
    job_id = str(uuid4())
    start_time = time.monotonic()
    active_connections_gauge.inc()

    # Record job in database
    ip = "inline"
    try:
        await create_job(
            job_id=job_id,
            url=url,
            client_ip=ip,
            tier=tier,
            model_provider=model_provider,
        )
    except (ConnectionError, OSError) as e:
        logger.warning("Failed to record job: %s", e)

    async with semaphore:
        try:
            # Step 1: Crawl
            crawling_data = {
                "job_id": job_id,
                "message": "Crawling your site...",
                "progress": 10,
            }
            yield format_sse_event(data_str=json.dumps(crawling_data), event="crawling")

            await update_job(
                job_id, status=JobStatus.CRAWLING.value, progress=10, message="Crawling..."
            )
            crawl_result = await crawl(url)
            if crawl_result.error:
                err_msg = "Could not reach that website. Check the URL and try again."
                duration_ms = round((time.monotonic() - start_time) * 1000, 2)
                redesign_errors_total.labels(phase="crawl").inc()
                logger.error(
                    "redesign_failed",
                    extra={
                        "job_id": job_id,
                        "url": url,
                        "phase": "crawl",
                        "duration_ms": duration_ms,
                        "error": crawl_result.error,
                    },
                )
                await update_job(job_id, status=JobStatus.FAILED.value, error=err_msg)
                yield format_sse_event(
                    data_str=json.dumps({"job_id": job_id, "error": err_msg}),
                    event="error",
                )
                return

            # Step 2: Redesign (sync -- use to_thread)
            redesigning_data = {
                "job_id": job_id,
                "message": "Claude is redesigning...",
                "progress": 40,
            }
            yield format_sse_event(data_str=json.dumps(redesigning_data), event="redesigning")

            await update_job(
                job_id,
                status=JobStatus.REDESIGNING.value,
                progress=40,
                message="Redesigning...",
            )

            try:
                redesign_result = await asyncio.wait_for(
                    asyncio.to_thread(
                        run_redesign,
                        crawl_result,
                        settings,
                        tier,
                        model_provider=model_provider,
                    ),
                    timeout=600,
                )
            except TimeoutError:
                err_msg = "Redesign timed out after 10 minutes."
                duration_ms = round((time.monotonic() - start_time) * 1000, 2)
                redesign_errors_total.labels(phase="redesign").inc()
                logger.error(
                    "redesign_failed",
                    extra={
                        "job_id": job_id,
                        "url": url,
                        "phase": "redesign",
                        "duration_ms": duration_ms,
                        "error": "timeout_600s",
                    },
                )
                await update_job(job_id, status=JobStatus.FAILED.value, error=err_msg)
                yield format_sse_event(
                    data_str=json.dumps({"job_id": job_id, "error": err_msg}),
                    event="error",
                )
                return

            # Handle both RedesignResult and raw string
            if hasattr(redesign_result, "html"):
                html_content = redesign_result.html
                build_dir = redesign_result.build_dir
            else:
                html_content = redesign_result
                build_dir = None

            # Sanitize AI-generated HTML
            html_content = _sanitize_html(html_content)

            # Inject SastaSpace badge (marketing watermark)
            if settings.include_badge:
                html_content = inject_badge(html_content)

            # Step 3: Deploy (sync -- use to_thread)
            deploying_data = {
                "job_id": job_id,
                "message": "Deploying your redesign...",
                "progress": 80,
            }
            yield format_sse_event(data_str=json.dumps(deploying_data), event="deploying")

            await update_job(
                job_id,
                status=JobStatus.DEPLOYING.value,
                progress=80,
                message="Deploying...",
            )
            result = await asyncio.to_thread(
                deploy_fn, url, html_content, settings.sites_dir, build_dir=build_dir
            )
            sites_deployed_gauge.inc()

            # Step 4: Done
            done_data = {
                "job_id": job_id,
                "message": "Done!",
                "progress": 100,
                "url": f"/{result.subdomain}/",
                "subdomain": result.subdomain,
            }
            await update_job(
                job_id,
                status=JobStatus.DONE.value,
                progress=100,
                message="Done!",
                subdomain=result.subdomain,
                html_path=str(result.index_path),
            )
            redesign_latency_seconds.observe(time.monotonic() - start_time)
            yield format_sse_event(data_str=json.dumps(done_data), event="done")
        except Exception as exc:  # Broad catch: log and emit SSE error to client
            duration_ms = round((time.monotonic() - start_time) * 1000, 2)
            redesign_errors_total.labels(phase="unknown").inc()
            logger.error(
                "redesign_failed",
                extra={
                    "job_id": job_id,
                    "url": url,
                    "phase": "unknown",
                    "duration_ms": duration_ms,
                    "error": str(exc),
                },
                exc_info=True,
            )
            err_data = {
                "job_id": job_id,
                "error": ("Redesign service unavailable. Please try again later."),
            }
            await update_job(
                job_id,
                status=JobStatus.FAILED.value,
                error="Redesign service unavailable",
            )
            yield format_sse_event(data_str=json.dumps(err_data), event="error")
            return
        finally:
            active_connections_gauge.dec()
            if task:
                active_sse_tasks.discard(task)


async def redis_job_stream(job_id: str, job_svc) -> AsyncGenerator[bytes, None]:
    """Stream job status updates from Redis Pub/Sub as SSE events."""
    if not job_svc:
        return

    async for update in job_svc.subscribe_job(job_id):
        event_name = update.get("event", "message")
        data = update.get("data", update)
        yield format_sse_event(data_str=json.dumps(data), event=event_name)
