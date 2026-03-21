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

    # Connect MongoDB
    set_mongo_url(settings.mongodb_url, settings.mongodb_db)
    try:
        await init_db()
        logger.info("MongoDB connected")
    except Exception:
        logger.warning("MongoDB unavailable — job persistence disabled", exc_info=True)

    # Connect Redis
    svc = JobService(redis_url=settings.redis_url)
    await svc.connect()
    logger.info("Redis connected, starting job consumer loop...")

    try:
        await svc.process_messages(
            consumer_name=f"worker-{os.getpid()}",
            handler=redesign_handler,
        )
    except KeyboardInterrupt:
        logger.info("Worker shutting down (KeyboardInterrupt)")
    except Exception:
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
