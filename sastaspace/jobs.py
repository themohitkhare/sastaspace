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
        self._redis = aioredis.from_url(
            self.redis_url, decode_responses=True, max_connections=10
        )
        self._pubsub_redis = aioredis.from_url(
            self.redis_url, decode_responses=True
        )
        # Create consumer group if it doesn't exist
        try:
            await self._redis.xgroup_create(
                STREAM_KEY, GROUP_NAME, id="0", mkstream=True
            )
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
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=30.0
                )
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

    async def process_messages(
        self,
        consumer_name: str,
        handler,
    ) -> None:
        """
        Worker loop: read from the Redis Stream consumer group and process jobs.

        `handler` is an async callable(job_id, url, tier, job_service) -> None
        that does the actual crawl → redesign → deploy work.
        """
        logger.info("Worker %s starting on stream %s", consumer_name, STREAM_KEY)

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
    from sastaspace.config import Settings
    from sastaspace.crawler import crawl
    from sastaspace.deployer import deploy
    from sastaspace.redesigner import redesign, redesign_premium

    settings = Settings()

    # Step 1: Crawling
    await update_job(
        job_id, status=JobStatus.CRAWLING.value, progress=10, message="Crawling your site..."
    )
    await job_service.publish_status(
        job_id,
        "crawling",
        {"job_id": job_id, "message": "Crawling your site...", "progress": 10},
    )

    crawl_result = await crawl(url)
    if crawl_result.error:
        await update_job(
            job_id,
            status=JobStatus.FAILED.value,
            error="Could not reach that website. Check the URL and try again.",
        )
        err = "Could not reach that website. Check the URL and try again."
        await job_service.publish_status(
            job_id, "error", {"job_id": job_id, "error": err},
        )
        return

    # Step 2: Redesigning
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

    # Choose redesign function based on tier
    if tier == "premium":
        html = await asyncio.to_thread(
            redesign_premium,
            crawl_result,
            api_url=settings.claude_code_api_url,
            model=settings.claude_model,
        )
    else:
        html = await asyncio.to_thread(
            redesign,
            crawl_result,
            api_url=settings.claude_code_api_url,
            model=settings.claude_model,
        )

    # Sanitize
    import nh3

    html = nh3.clean(html)

    # Step 3: Deploying
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

    # Register in DB
    await register_site(
        subdomain=result.subdomain,
        original_url=url,
        job_id=job_id,
        html_path=str(result.index_path),
        tier=tier,
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
