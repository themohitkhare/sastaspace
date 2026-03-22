# sastaspace/jobs.py
"""Redis Stream-based async job service for redesign pipelines."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from uuid import uuid4

import redis.asyncio as aioredis

from sastaspace.database import (
    JobStatus,
    create_job,
    get_job,
    register_site,
    update_job,
)

logger = logging.getLogger(__name__)

# Redis Stream keys
STREAM_KEY = "sastaspace:jobs"
GROUP_NAME = "redesign-workers"
CONSUMER_PREFIX = "worker"
STATUS_CHANNEL = "sastaspace:job-status"

# How long to block waiting for new messages (ms)
BLOCK_MS = 5000
# Max messages to read per batch
BATCH_SIZE = 1


class JobService:
    """Manages redesign jobs via Redis Streams."""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self._redis: aioredis.Redis | None = None
        self._pubsub_redis: aioredis.Redis | None = None

    async def connect(self) -> None:
        """Initialize Redis connections."""
        self._redis = aioredis.from_url(self.redis_url, decode_responses=True, max_connections=10)
        self._pubsub_redis = aioredis.from_url(self.redis_url, decode_responses=True)
        # Create consumer group if it doesn't exist
        try:
            await self._redis.xgroup_create(STREAM_KEY, GROUP_NAME, id="0", mkstream=True)
        except aioredis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

    async def close(self) -> None:
        """Close Redis connections."""
        if self._redis:
            await self._redis.aclose()
        if self._pubsub_redis:
            await self._pubsub_redis.aclose()

    @property
    def redis(self) -> aioredis.Redis:
        if self._redis is None:
            raise RuntimeError("JobService not connected. Call connect() first.")
        return self._redis

    async def enqueue(
        self,
        url: str,
        client_ip: str,
        tier: str = "standard",
    ) -> str:
        """Add a redesign job to the Redis Stream. Returns job_id."""
        job_id = str(uuid4())

        # Persist in SQLite
        await create_job(job_id=job_id, url=url, client_ip=client_ip, tier=tier)

        # Push to Redis Stream
        await self.redis.xadd(
            STREAM_KEY,
            {
                "job_id": job_id,
                "url": url,
                "tier": tier,
                "client_ip": client_ip,
                "created_at": datetime.now(UTC).isoformat(),
            },
        )

        logger.info("Enqueued job %s for %s (tier=%s)", job_id, url, tier)
        return job_id

    async def publish_status(self, job_id: str, event: str, data: dict) -> None:
        """Publish a job status update via Redis Pub/Sub."""
        payload = json.dumps({"job_id": job_id, "event": event, "data": data})
        if self._pubsub_redis:
            await self._pubsub_redis.publish(f"{STATUS_CHANNEL}:{job_id}", payload)

    async def subscribe_job(self, job_id: str):
        """Subscribe to status updates for a specific job. Returns an async generator."""
        if self._pubsub_redis is None:
            raise RuntimeError("JobService not connected.")

        pubsub = self._pubsub_redis.pubsub()
        channel = f"{STATUS_CHANNEL}:{job_id}"
        await pubsub.subscribe(channel)

        try:
            # First, check if job is already completed
            job = await get_job(job_id)
            if job and job["status"] in (JobStatus.DONE.value, JobStatus.FAILED.value):
                yield {
                    "event": job["status"],
                    "data": {
                        "job_id": job_id,
                        "message": job.get("message", ""),
                        "progress": job.get("progress", 0),
                        "subdomain": job.get("subdomain"),
                        "error": job.get("error"),
                    },
                }
                return

            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=30.0)
                if message is None:
                    # Timeout — check if job completed while we were waiting
                    job = await get_job(job_id)
                    if job and job["status"] in (
                        JobStatus.DONE.value,
                        JobStatus.FAILED.value,
                    ):
                        yield {
                            "event": job["status"],
                            "data": {
                                "job_id": job_id,
                                "message": job.get("message", ""),
                                "progress": job.get("progress", 0),
                                "subdomain": job.get("subdomain"),
                                "error": job.get("error"),
                            },
                        }
                        return
                    continue

                if message["type"] == "message":
                    payload = json.loads(message["data"])
                    yield payload
                    if payload.get("event") in ("done", "error", "failed"):
                        return
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()

    async def _recover_pending(
        self,
        consumer_name: str,
        handler,
    ) -> int:
        """
        Claim and reprocess messages abandoned by dead workers.

        Uses XAUTOCLAIM to steal messages idle for >60s from any consumer,
        then reprocesses them. Returns count of recovered messages.
        """
        min_idle_ms = 60_000  # 60 seconds — if a message is idle this long, the worker is dead
        recovered = 0

        try:
            # XAUTOCLAIM: claim idle messages from any consumer in the group
            # Returns (next_start_id, claimed_entries, deleted_ids)
            start_id = "0-0"
            while True:
                result = await self.redis.xautoclaim(
                    STREAM_KEY, GROUP_NAME, consumer_name, min_idle_ms, start_id, count=10
                )
                next_id, entries, _deleted = result

                if not entries:
                    break

                for msg_id, fields in entries:
                    job_id = fields["job_id"]
                    url = fields["url"]
                    tier = fields.get("tier", "standard")

                    # Check if job already completed (avoid double-processing)
                    job = await get_job(job_id)
                    if job and job.get("status") in (
                        JobStatus.DONE.value,
                        JobStatus.FAILED.value,
                    ):
                        logger.info("Recovery: job %s already %s, acking", job_id, job["status"])
                        await self.redis.xack(STREAM_KEY, GROUP_NAME, msg_id)
                        continue

                    logger.warning("Recovery: reprocessing abandoned job %s: %s", job_id, url)
                    try:
                        await handler(job_id, url, tier, self)
                        await self.redis.xack(STREAM_KEY, GROUP_NAME, msg_id)
                        recovered += 1
                    except Exception:
                        logger.exception("Recovery: job %s failed on retry", job_id)
                        await update_job(
                            job_id,
                            status=JobStatus.FAILED.value,
                            error="Redesign failed after recovery. Please try again.",
                            progress=0,
                        )
                        await self.publish_status(
                            job_id,
                            "error",
                            {
                                "job_id": job_id,
                                "error": "Redesign failed after recovery. Please try again.",
                            },
                        )
                        await self.redis.xack(STREAM_KEY, GROUP_NAME, msg_id)

                # If next_id is "0-0", we've processed all pending entries
                if next_id == b"0-0" or next_id == "0-0":
                    break
                start_id = next_id

        except Exception:
            logger.exception("Recovery scan failed — continuing with normal processing")

        return recovered

    async def process_messages(
        self,
        consumer_name: str,
        handler,
    ) -> None:
        """
        Worker loop: read from the Redis Stream consumer group and process jobs.

        On startup, recovers any abandoned jobs from dead workers (pending entries
        idle >60s). Then reads new messages in a loop.

        `handler` is an async callable(job_id, url, tier, job_service) -> None
        that does the actual crawl → redesign → deploy work.
        """
        logger.info("Worker %s starting on stream %s", consumer_name, STREAM_KEY)

        # Recover abandoned jobs from dead workers before reading new ones
        recovered = await self._recover_pending(consumer_name, handler)
        if recovered:
            logger.info("Recovery: reprocessed %d abandoned job(s)", recovered)

        while True:
            try:
                messages = await self.redis.xreadgroup(
                    GROUP_NAME,
                    consumer_name,
                    {STREAM_KEY: ">"},
                    count=BATCH_SIZE,
                    block=BLOCK_MS,
                )

                if not messages:
                    continue

                for stream_name, entries in messages:
                    for msg_id, fields in entries:
                        job_id = fields["job_id"]
                        url = fields["url"]
                        tier = fields.get("tier", "standard")

                        logger.info("Processing job %s: %s", job_id, url)

                        try:
                            await handler(job_id, url, tier, self)
                            # Acknowledge message on success
                            await self.redis.xack(STREAM_KEY, GROUP_NAME, msg_id)
                        except Exception:
                            logger.exception("Job %s failed", job_id)
                            await update_job(
                                job_id,
                                status=JobStatus.FAILED.value,
                                error="Internal processing error",
                                progress=0,
                            )
                            await self.publish_status(
                                job_id,
                                "error",
                                {
                                    "job_id": job_id,
                                    "error": "Redesign failed. Please try again later.",
                                },
                            )
                            await self.redis.xack(STREAM_KEY, GROUP_NAME, msg_id)

            except aioredis.ConnectionError:
                logger.warning("Redis connection lost, reconnecting in 2s...")
                await asyncio.sleep(2)
            except Exception:
                logger.exception("Unexpected error in worker loop")
                await asyncio.sleep(1)


async def redesign_handler(
    job_id: str,
    url: str,
    tier: str,
    job_service: JobService,
) -> None:
    """
    The actual redesign pipeline handler run by workers.
    Crawl → Redesign → Deploy, publishing status updates along the way.
    """
    import time as _time

    from sastaspace.config import Settings
    from sastaspace.crawler import crawl
    from sastaspace.deployer import deploy

    settings = Settings()
    job_start = _time.monotonic()

    pipeline = "agno" if settings.use_agno_pipeline else "legacy"
    logger.info("JOB START | job=%s url=%s tier=%s pipeline=%s", job_id, url, tier, pipeline)

    # Step 1: Crawling
    logger.info("JOB STEP 1/3: Crawling | job=%s url=%s", job_id, url)
    await update_job(
        job_id, status=JobStatus.CRAWLING.value, progress=10, message="Crawling your site..."
    )
    await job_service.publish_status(
        job_id,
        "crawling",
        {"job_id": job_id, "message": "Crawling your site...", "progress": 10},
    )

    crawl_start = _time.monotonic()
    crawl_result = await crawl(url)
    crawl_duration = _time.monotonic() - crawl_start

    if crawl_result.error:
        logger.warning(
            "JOB CRAWL FAILED | job=%s url=%s error=%s duration=%.1fs",
            job_id,
            url,
            crawl_result.error,
            crawl_duration,
        )
        await update_job(
            job_id,
            status=JobStatus.FAILED.value,
            error="Could not reach that website. Check the URL and try again.",
        )
        err = "Could not reach that website. Check the URL and try again."
        await job_service.publish_status(
            job_id,
            "error",
            {"job_id": job_id, "error": err},
        )
        return

    logger.info(
        "JOB CRAWL OK | job=%s title=%s sections=%d colors=%d duration=%.1fs",
        job_id,
        crawl_result.title[:50] if crawl_result.title else "N/A",
        len(crawl_result.sections) if hasattr(crawl_result, "sections") else 0,
        len(crawl_result.colors),
        crawl_duration,
    )

    # Emit discovered site facts for the UI discovery grid
    _discovery_items = []
    if crawl_result.title:
        _discovery_items.append({"label": "Title", "value": crawl_result.title})
    if crawl_result.colors:
        _discovery_items.append(
            {"label": "Colors", "value": f"{len(crawl_result.colors)} detected"}
        )
    if crawl_result.sections:
        _discovery_items.append(
            {"label": "Sections", "value": f"{len(crawl_result.sections)} content sections"}
        )
    if crawl_result.fonts:
        _discovery_items.append({"label": "Fonts", "value": crawl_result.fonts[0]})
    if _discovery_items:
        await job_service.publish_status(
            job_id, "discovery", {"job_id": job_id, "items": _discovery_items}
        )

    # Persist crawl data so polling clients can show brand colors + title
    await update_job(
        job_id,
        site_colors=crawl_result.colors[:5],
        site_title=crawl_result.title,
    )

    # Emit screenshot for before/after reveal — skip if too large for SSE
    _MAX_SCREENSHOT_B64 = 500_000  # ~375KB raw PNG
    if (
        crawl_result.screenshot_base64
        and len(crawl_result.screenshot_base64) <= _MAX_SCREENSHOT_B64
    ):
        await job_service.publish_status(
            job_id,
            "screenshot",
            {"job_id": job_id, "screenshot_base64": crawl_result.screenshot_base64},
        )

    # Step 2: Redesigning
    logger.info("JOB STEP 2/3: Redesigning | job=%s pipeline=%s", job_id, pipeline)
    await update_job(
        job_id,
        status=JobStatus.REDESIGNING.value,
        progress=40,
        message="AI is redesigning your site...",
    )
    await job_service.publish_status(
        job_id,
        "redesigning",
        {"job_id": job_id, "message": "AI is redesigning your site...", "progress": 40},
    )

    redesign_start = _time.monotonic()

    # Capture the running loop before entering the thread
    loop = asyncio.get_running_loop()

    def _on_agent_progress(event: str, data: dict) -> None:
        """Called synchronously from the pipeline thread — schedule publish on the event loop."""
        data["job_id"] = job_id
        try:
            asyncio.run_coroutine_threadsafe(
                job_service.publish_status(job_id, event, data),
                loop,
            )
        except Exception:
            pass  # never crash the pipeline thread over a UI event

    # Choose redesign function based on tier / pipeline setting
    from sastaspace.redesigner import run_redesign

    html = await asyncio.to_thread(
        run_redesign,
        crawl_result,
        settings,
        tier,
        _on_agent_progress,
    )

    redesign_duration = _time.monotonic() - redesign_start
    logger.info(
        "JOB REDESIGN OK | job=%s html_size=%d duration=%.1fs",
        job_id,
        len(html),
        redesign_duration,
    )

    # Step 3: Deploying
    logger.info("JOB STEP 3/3: Deploying | job=%s", job_id)
    await update_job(
        job_id,
        status=JobStatus.DEPLOYING.value,
        progress=80,
        message="Deploying your redesign...",
    )
    await job_service.publish_status(
        job_id,
        "deploying",
        {"job_id": job_id, "message": "Deploying your redesign...", "progress": 80},
    )

    result = await asyncio.to_thread(deploy, url, html, settings.sites_dir)

    total_duration = _time.monotonic() - job_start
    logger.info(
        "JOB DONE | job=%s subdomain=%s html_size=%d crawl=%.1fs redesign=%.1fs total=%.1fs",
        job_id,
        result.subdomain,
        len(html),
        crawl_duration,
        redesign_duration,
        total_duration,
    )

    # Register in DB with URL hash for dedup
    from sastaspace.urls import url_hash

    await register_site(
        subdomain=result.subdomain,
        original_url=url,
        job_id=job_id,
        html_path=str(result.index_path),
        tier=tier,
        url_hash=url_hash(url),
    )

    # Step 4: Done
    await update_job(
        job_id,
        status=JobStatus.DONE.value,
        progress=100,
        message="Done!",
        subdomain=result.subdomain,
        html_path=str(result.index_path),
    )
    await job_service.publish_status(
        job_id,
        "done",
        {
            "job_id": job_id,
            "message": "Done!",
            "progress": 100,
            "url": f"/{result.subdomain}/",
            "subdomain": result.subdomain,
        },
    )
