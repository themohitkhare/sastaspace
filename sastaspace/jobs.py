# sastaspace/jobs.py
"""Redis Stream-based async job service for redesign pipelines."""

from __future__ import annotations

import asyncio
import json
import logging
import time as _time
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import redis.asyncio as aioredis

from sastaspace.config import Settings
from sastaspace.crawler import CrawlResult, enhanced_crawl
from sastaspace.database import (
    JobStatus,
    JobUpdate,
    create_job,
    find_failed_job_checkpoint,
    get_job,
    register_site,
    update_job,
)
from sastaspace.deployer import deploy
from sastaspace.html_utils import RedesignError, RedesignResult, inject_badge, sanitize_html
from sastaspace.html_utils import validate_html as _validate_html
from sastaspace.redesigner import run_redesign
from sastaspace.urls import extract_domain, url_hash
from sastaspace.vikunja_sync import get_vikunja_client

logger = logging.getLogger(__name__)

# Redis Stream keys
STREAM_KEY = "sastaspace:jobs"
GROUP_NAME = "redesign-workers"
CONSUMER_PREFIX = "worker"
STATUS_CHANNEL = "sastaspace:job-status"

# How long to block waiting for new messages (ms).
# Lower = faster job pickup, but more Redis round-trips when idle.
# 1s is a good balance: responsive without excessive polling.
BLOCK_MS = 1000
# Max messages to read per batch
BATCH_SIZE = 1

# CrawlResult fields to persist in checkpoint (all dataclass fields except methods)
_CRAWL_FIELDS = [
    "url",
    "title",
    "meta_description",
    "favicon_url",
    "html_source",
    "screenshot_base64",
    "headings",
    "navigation_links",
    "text_content",
    "images",
    "colors",
    "fonts",
    "sections",
    "error",
]


def _serialize_crawl_result(cr: CrawlResult) -> dict:
    """Serialize a CrawlResult dataclass into a JSON-safe dict."""
    return {f: getattr(cr, f) for f in _CRAWL_FIELDS}


def _deserialize_crawl_result(data: dict) -> CrawlResult:
    """Reconstruct a CrawlResult from a serialized dict."""
    return CrawlResult(**{f: data.get(f, "") for f in _CRAWL_FIELDS})


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
        tier: str = "free",
        model_provider: str = "claude",
        prompt: str = "",
    ) -> str:
        """Add a redesign job to the Redis Stream. Returns job_id."""
        job_id = str(uuid4())

        # Persist in SQLite
        await create_job(
            job_id=job_id,
            url=url,
            client_ip=client_ip,
            tier=tier,
            model_provider=model_provider,
        )

        # Push to Redis Stream
        stream_fields: dict[str, str] = {
            "job_id": job_id,
            "url": url,
            "tier": tier,
            "model_provider": model_provider,
            "client_ip": client_ip,
            "created_at": datetime.now(UTC).isoformat(),
        }
        if prompt:
            stream_fields["prompt"] = prompt
        await self.redis.xadd(STREAM_KEY, stream_fields)

        logger.info(
            "Enqueued job %s for %s (tier=%s, model_provider=%s)",
            job_id,
            url,
            tier,
            model_provider,
        )
        return job_id

    async def publish_status(self, job_id: str, event: str, data: dict) -> None:
        """Publish a job status update via Redis Pub/Sub."""
        payload = json.dumps({"job_id": job_id, "event": event, "data": data})
        if self._pubsub_redis:
            await self._pubsub_redis.publish(f"{STATUS_CHANNEL}:{job_id}", payload)

    @staticmethod
    def _job_status_event(job_id: str, job: dict) -> dict:
        """Build an SSE status event dict from a completed/failed job record."""
        return {
            "event": job["status"],
            "data": {
                "job_id": job_id,
                "message": job.get("message", ""),
                "progress": job.get("progress", 0),
                "subdomain": job.get("subdomain"),
                "error": job.get("error"),
            },
        }

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
                yield self._job_status_event(job_id, job)
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
                        yield self._job_status_event(job_id, job)
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
                    tier = fields.get("tier", "free")
                    model_provider = fields.get("model_provider", "claude")
                    prompt = fields.get("prompt", "")

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
                        cp = job.get("checkpoint") if job else None
                        await handler(
                            job_id,
                            url,
                            tier,
                            self,
                            checkpoint=cp,
                            model_provider=model_provider,
                            prompt=prompt,
                        )
                        await self.redis.xack(STREAM_KEY, GROUP_NAME, msg_id)
                        recovered += 1
                    except Exception:  # noqa: BLE001
                        logger.exception("Recovery: job %s failed on retry", job_id)
                        try:
                            await update_job(
                                job_id,
                                status=JobStatus.FAILED.value,
                                error="Redesign failed after recovery. Please try again.",
                                progress=0,
                            )
                        except Exception:  # noqa: BLE001
                            logger.warning("Recovery: failed to update job %s in DB", job_id)
                        try:
                            await self.publish_status(
                                job_id,
                                "error",
                                {
                                    "job_id": job_id,
                                    "error": "Redesign failed after recovery. Please try again.",
                                },
                            )
                        except Exception:  # noqa: BLE001
                            logger.warning("Recovery: failed to publish error for job %s", job_id)
                        await self.redis.xack(STREAM_KEY, GROUP_NAME, msg_id)

                # If next_id is "0-0", we've processed all pending entries
                if next_id == b"0-0" or next_id == "0-0":
                    break
                start_id = next_id

        except (aioredis.RedisError, OSError):
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
                        tier = fields.get("tier", "free")
                        model_provider = fields.get("model_provider", "claude")
                        prompt = fields.get("prompt", "")

                        logger.info("Processing job %s: %s", job_id, url)

                        # Check for checkpoint from a previous failed job for the same URL
                        prev_checkpoint = None
                        try:
                            prev_checkpoint = await find_failed_job_checkpoint(url)
                            if prev_checkpoint:
                                logger.info(
                                    "RESUME | job=%s reusing checkpoint from previous failed job",
                                    job_id,
                                )
                        except (OSError, ConnectionError):
                            pass  # DB unavailable — proceed without checkpoint

                        try:
                            await handler(
                                job_id,
                                url,
                                tier,
                                self,
                                checkpoint=prev_checkpoint,
                                model_provider=model_provider,
                                prompt=prompt,
                            )
                            # Acknowledge message on success
                            await self.redis.xack(STREAM_KEY, GROUP_NAME, msg_id)
                        except Exception:  # noqa: BLE001
                            logger.exception("Job %s failed", job_id)
                            try:
                                await update_job(
                                    job_id,
                                    status=JobStatus.FAILED.value,
                                    error="Internal processing error",
                                    progress=0,
                                )
                            except Exception:  # noqa: BLE001
                                logger.warning("Failed to update job %s status in DB", job_id)
                            try:
                                await self.publish_status(
                                    job_id,
                                    "error",
                                    {
                                        "job_id": job_id,
                                        "error": "Redesign failed. Please try again later.",
                                    },
                                )
                            except Exception:  # noqa: BLE001
                                logger.warning("Failed to publish error status for job %s", job_id)
                            await self.redis.xack(STREAM_KEY, GROUP_NAME, msg_id)

            except aioredis.ConnectionError:
                logger.warning("Redis connection lost, reconnecting in 2s...")
                await asyncio.sleep(2)
            except Exception:  # noqa: BLE001
                logger.exception("Unexpected error in worker loop")
                await asyncio.sleep(1)


async def redesign_handler(
    job_id: str,
    url: str,
    tier: str,
    job_service: JobService,
    checkpoint: dict | None = None,
    model_provider: str = "claude",
    prompt: str = "",
) -> None:
    """
    The actual redesign pipeline handler run by workers.
    Crawl -> Redesign -> Deploy, publishing status updates along the way.

    If a checkpoint dict is provided (from a recovered job), the handler will
    skip already-completed steps:
    - If crawl was completed, skip crawling and reconstruct CrawlResult from checkpoint.
    - Pipeline checkpoint data is forwarded to run_redesign_pipeline so agent steps
      that already finished are also skipped.
    """
    settings = Settings()
    job_start = _time.monotonic()

    pipeline = "agno" if settings.use_agno_pipeline else "legacy"
    has_checkpoint = checkpoint is not None
    logger.info(
        "JOB START | job=%s url=%s tier=%s pipeline=%s checkpoint=%s model_provider=%s",
        job_id,
        url,
        tier,
        pipeline,
        has_checkpoint,
        model_provider,
    )

    # Determine what to skip from checkpoint
    skip_crawl = False
    pipeline_checkpoint: dict | None = None
    crawl_data: dict | None = None

    if checkpoint:
        completed = checkpoint.get("completed_step", "")
        if completed == "crawl" or checkpoint.get("pipeline_data"):
            skip_crawl = True
            crawl_data = checkpoint.get("crawl_result")
        pipeline_checkpoint = checkpoint.get("pipeline_data") or None

    # Step 1: Crawling
    crawl_duration = 0.0
    enhanced_result = None
    if skip_crawl and crawl_data:
        logger.info("JOB STEP 1/3: Crawling SKIPPED (from checkpoint) | job=%s", job_id)
        crawl_result = _deserialize_crawl_result(crawl_data)
    else:
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
        enhanced_result = await enhanced_crawl(url, settings)
        crawl_result = enhanced_result.homepage
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

            # Sync failure to Vikunja (fire-and-forget)
            try:
                vikunja = get_vikunja_client(
                    settings.vikunja_url, settings.vikunja_token, settings.vikunja_project_id
                )
                domain = extract_domain(url)
                await vikunja.create_or_update_lead(
                    domain=domain,
                    job_id=job_id,
                    tier=tier,
                )
            except (httpx.HTTPError, KeyError, ValueError, OSError):
                pass

            return

        logger.info(
            "JOB CRAWL OK | job=%s title=%s sections=%d colors=%d duration=%.1fs",
            job_id,
            crawl_result.title[:50] if crawl_result.title else "N/A",
            len(crawl_result.sections) if hasattr(crawl_result, "sections") else 0,
            len(crawl_result.colors),
            crawl_duration,
        )

        # Save crawl checkpoint to MongoDB
        crawl_data = _serialize_crawl_result(crawl_result)
        await update_job(
            job_id,
            checkpoint={"completed_step": "crawl", "crawl_result": crawl_data, "pipeline_data": {}},
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
    _job_update = JobUpdate(
        site_colors=crawl_result.colors[:5],
        site_title=crawl_result.title,
    )
    if enhanced_result:
        _job_update.status = "analyzing"
        _job_update.progress = 45
        _job_update.message = "Building business profile..."
        _job_update.pages_crawled = len(enhanced_result.internal_pages)
        _job_update.assets_count = len(enhanced_result.assets.assets)
        _job_update.assets_total_size = enhanced_result.assets.total_size_bytes
    await update_job(job_id, updates=_job_update)

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
        except (RuntimeError, OSError):
            pass  # never crash the pipeline thread over a UI event

    def _on_checkpoint(step_name: str, checkpoint_data: dict) -> None:
        """Called synchronously from the pipeline thread — persist checkpoint to MongoDB."""
        full_checkpoint = {
            "completed_step": step_name,
            "crawl_result": crawl_data,
            "pipeline_data": checkpoint_data,
        }
        try:
            asyncio.run_coroutine_threadsafe(
                update_job(job_id, updates=JobUpdate(checkpoint=full_checkpoint)), loop
            )
        except (RuntimeError, OSError):
            pass  # never crash the pipeline thread over a checkpoint save

    # Choose redesign function based on tier / pipeline setting
    redesign_result = await asyncio.to_thread(
        run_redesign,
        crawl_result,
        settings,
        tier,
        _on_agent_progress,
        pipeline_checkpoint,
        _on_checkpoint,
        enhanced=enhanced_result,
        model_provider=model_provider,
        user_prompt=prompt,
    )

    # Handle both RedesignResult and raw string (for backward compat with mocked tests)
    if isinstance(redesign_result, RedesignResult):
        html = redesign_result.html
        build_dir = redesign_result.build_dir
    else:
        html = redesign_result
        build_dir = None

    redesign_duration = _time.monotonic() - redesign_start
    logger.info(
        "JOB REDESIGN OK | job=%s html_size=%d build_dir=%s duration=%.1fs",
        job_id,
        len(html),
        build_dir is not None,
        redesign_duration,
    )

    # Guard: refuse to deploy empty or invalid HTML
    try:
        _validate_html(html)
    except RedesignError as e:
        logger.error("JOB DEPLOY BLOCKED | job=%s reason=%s html_size=%d", job_id, e, len(html))
        await update_job(
            job_id,
            status=JobStatus.FAILED.value,
            error="Redesign produced invalid HTML. Please try again.",
        )
        await job_service.publish_status(
            job_id,
            "error",
            {"job_id": job_id, "error": "Redesign produced invalid HTML. Please try again."},
        )
        return

    # Inject SastaSpace badge (marketing watermark)
    if settings.include_badge:
        html = inject_badge(html)

    # Post-generation validation (non-blocking — fire-and-forget)
    if settings.enable_post_gen_validation:
        try:
            from sastaspace.html_validator import validate_accessibility

            async def _run_a11y_validation(html_content: str, jid: str) -> None:
                try:
                    result = await validate_accessibility(html_content)
                    if result.get("critical_count", 0) > 0:
                        logger.warning(
                            "A11Y SUMMARY | job=%s critical=%d total=%d passes=%d",
                            jid,
                            result["critical_count"],
                            result["total_violations"],
                            result["pass_count"],
                        )
                    else:
                        logger.info(
                            "A11Y SUMMARY | job=%s critical=0 total=%d passes=%d",
                            jid,
                            result.get("total_violations", 0),
                            result.get("pass_count", 0),
                        )
                except Exception:  # noqa: BLE001
                    logger.debug("A11Y validation task failed for job=%s", jid, exc_info=True)

            asyncio.create_task(_run_a11y_validation(html, job_id))
        except Exception:  # noqa: BLE001
            logger.debug("Could not start A11Y validation for job=%s", job_id, exc_info=True)

    # Sanitize AI-generated HTML (strip event handlers, javascript: URLs)
    html = sanitize_html(html)

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

    _assets = enhanced_result.assets.assets if enhanced_result else []
    deploy_start = _time.monotonic()
    try:
        result = await asyncio.to_thread(
            deploy,
            url,
            html,
            settings.sites_dir,
            assets=_assets,
            build_dir=build_dir,
        )
    except Exception as deploy_exc:
        logger.error(
            "JOB DEPLOY FAILED | job=%s error=%s",
            job_id,
            deploy_exc,
            exc_info=True,
        )
        await update_job(
            job_id,
            status=JobStatus.FAILED.value,
            error="Failed to deploy your redesign. Please try again.",
        )
        await job_service.publish_status(
            job_id,
            "error",
            {"job_id": job_id, "error": "Failed to deploy your redesign. Please try again."},
        )
        return

    deploy_duration = _time.monotonic() - deploy_start
    total_duration = _time.monotonic() - job_start
    logger.info(
        "PERF | JOB DONE job=%s subdomain=%s html_size=%d "
        "crawl=%.1fs redesign=%.1fs deploy=%.1fs total=%.1fs",
        job_id,
        result.subdomain,
        len(html),
        crawl_duration,
        redesign_duration,
        deploy_duration,
        total_duration,
    )

    # Register in DB with URL hash for dedup
    await register_site(
        subdomain=result.subdomain,
        original_url=url,
        job_id=job_id,
        html_path=str(result.index_path),
        tier=tier,
        url_hash=url_hash(url),
    )

    # Sync to Vikunja (fire-and-forget — failure doesn't affect pipeline)
    vikunja = get_vikunja_client(
        settings.vikunja_url, settings.vikunja_token, settings.vikunja_project_id
    )
    try:
        bp = getattr(enhanced_result, "business_profile", None) if enhanced_result else None
        company_name = (
            bp.business_name if bp and bp.business_name != "unknown" else crawl_result.title
        )
        domain = extract_domain(url)
        lead_id = await vikunja.create_or_update_lead(
            domain=domain,
            job_id=job_id,
            tier=tier,
            subdomain=result.subdomain,
            site_title=company_name or domain,
        )
        if lead_id:
            logger.info("Vikunja: lead synced for %s (task=%s)", domain, lead_id)
    except (httpx.HTTPError, KeyError, ValueError, OSError) as e:
        logger.warning("Vikunja sync failed for job %s: %s", job_id, e)

    # Clear checkpoint — job is done, no need to keep checkpoint data
    await update_job(
        job_id,
        status=JobStatus.DONE.value,
        progress=100,
        message="Done!",
        subdomain=result.subdomain,
        html_path=str(result.index_path),
        updates=JobUpdate(checkpoint=None),
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
