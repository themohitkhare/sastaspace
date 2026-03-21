"""Worker process -- consumes redesign jobs from Redis Stream."""

from __future__ import annotations

import asyncio
import logging
import os

from sastaspace.config import Settings
from sastaspace.database import close_db, init_db, set_mongo_url
from sastaspace.jobs import JobService, redesign_handler


async def main():
    settings = Settings()
    set_mongo_url(settings.mongodb_url, settings.mongodb_db)
    await init_db()

    svc = JobService(redis_url=settings.redis_url)
    await svc.connect()

    logging.info("Worker started, consuming from Redis Stream...")
    try:
        await svc.process_messages(
            consumer_name=f"worker-{os.getpid()}",
            handler=redesign_handler,
        )
    finally:
        await svc.close()
        await close_db()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(main())
