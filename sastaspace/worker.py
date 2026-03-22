"""Worker process -- consumes redesign jobs from Redis Stream."""

from __future__ import annotations

import asyncio
import logging
import os
import sys

from sastaspace.config import Settings
from sastaspace.database import close_db, init_db, set_mongo_url
from sastaspace.jobs import JobService, redesign_handler

logger = logging.getLogger("sastaspace.worker")


async def _connect_mongodb(settings: Settings, max_retries: int, retry_delay: int) -> None:
    """Connect to MongoDB with retries."""
    set_mongo_url(settings.mongodb_url, settings.mongodb_db)
    for attempt in range(1, max_retries + 1):
        try:
            await init_db()
            logger.info("MongoDB connected")
            return
        except (ConnectionError, OSError, TimeoutError):
            if attempt == max_retries:
                logger.error(
                    "MongoDB unavailable after %d attempts — refusing to start", max_retries
                )
                raise
            logger.warning(
                "MongoDB attempt %d/%d failed, retrying in %ds...",
                attempt,
                max_retries,
                retry_delay,
            )
            await asyncio.sleep(retry_delay)


async def _connect_redis(settings: Settings, max_retries: int, retry_delay: int) -> JobService:
    """Connect to Redis with retries and return the JobService."""
    for attempt in range(1, max_retries + 1):
        try:
            svc = JobService(redis_url=settings.redis_url)
            await svc.connect()
            logger.info("Redis connected, starting job consumer loop...")
            return svc
        except (ConnectionError, OSError, TimeoutError):
            if attempt == max_retries:
                logger.error("Redis unavailable after %d attempts — refusing to start", max_retries)
                raise
            logger.warning(
                "Redis attempt %d/%d failed, retrying in %ds...", attempt, max_retries, retry_delay
            )
            await asyncio.sleep(retry_delay)
    raise RuntimeError("Unreachable")


async def main():
    settings = Settings()
    logger.info(
        "Worker initializing | pid=%d redis=%s mongodb=%s/%s agno=%s",
        os.getpid(),
        settings.redis_url,
        settings.mongodb_url,
        settings.mongodb_db,
        settings.use_agno_pipeline,
    )

    await _connect_mongodb(settings, max_retries=5, retry_delay=2)
    svc = await _connect_redis(settings, max_retries=5, retry_delay=2)

    try:
        await svc.process_messages(
            consumer_name=f"worker-{os.getpid()}",
            handler=redesign_handler,
        )
    except KeyboardInterrupt:
        logger.info("Worker shutting down (KeyboardInterrupt)")
    except Exception:  # noqa: pycodegate[no-broad-exception] — top-level worker crash handler
        logger.exception("Worker crashed")
        raise
    finally:
        await svc.close()
        await close_db()
        logger.info("Worker shutdown complete")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )
    # Also set agno/httpx to WARNING to reduce noise
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("agno").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    asyncio.run(main())
