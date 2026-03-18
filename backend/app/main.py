"""FastAPI application entry point + worker mode dispatch."""

from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.redis import _get_redis_manager
from app.db.session import _get_db_manager


def create_app() -> FastAPI:
    """Create and configure the FastAPI application (SERVER mode)."""
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost",
            "http://localhost:3000",
            "http://localhost:8000",
            "http://localhost:9000",
            "http://localhost:9001",
            "http://localhost:9002",
            "http://localhost:9004",
            "http://127.0.0.1",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000",
            "http://127.0.0.1:9000",
            "http://127.0.0.1:9001",
            "http://127.0.0.1:9002",
            "http://127.0.0.1:9004",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_router, prefix="/api/v1")

    @application.on_event("startup")
    async def startup_event() -> None:
        logger.info("Application starting", extra={"extra_fields": {"component": "startup"}})
        db_manager = _get_db_manager()
        await db_manager.initialize()
        logger.info("MongoDB initialized", extra={"extra_fields": {"component": "database"}})
        redis_manager = _get_redis_manager()
        await redis_manager.initialize()
        logger.info("Redis initialized", extra={"extra_fields": {"component": "redis"}})

    @application.on_event("shutdown")
    async def shutdown_event() -> None:
        logger.info("Application shutting down", extra={"extra_fields": {"component": "shutdown"}})
        db_manager = _get_db_manager()
        await db_manager.close()
        redis_manager = _get_redis_manager()
        await redis_manager.close()

    @application.get("/")
    def root() -> dict[str, str]:
        return {
            "message": "Welcome to SastaSpace API",
            "version": settings.app_version,
        }

    return application


# Create app for uvicorn import path (used in SERVER mode and docker CMD)
app = create_app()

log_level = "DEBUG" if settings.debug else "INFO"
setup_logging(level=log_level)
logger = logging.getLogger(__name__)


async def run_consumer() -> None:
    """Run a MutationWorker (CONSUMER mode)."""
    from app.worker.mutation_worker import MutationWorker

    worker = MutationWorker()
    await worker.setup()
    await worker.run()


async def run_coordinator() -> None:
    """Run a SolverCoordinator (COORDINATOR mode)."""
    from app.worker.solver_coordinator import SolverCoordinator

    coord = SolverCoordinator()
    await coord.setup()
    await coord.run()


if __name__ == "__main__":
    mode = settings.app_mode.upper()
    if mode == "SERVER":
        import uvicorn

        uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
    elif mode == "CONSUMER":
        asyncio.run(run_consumer())
    elif mode == "COORDINATOR":
        asyncio.run(run_coordinator())
    elif mode == "JOB":
        logger.info("JOB mode: no jobs configured yet")
    elif mode == "CRONJOB":
        logger.info("CRONJOB mode: no cron tasks configured yet")
    else:
        raise ValueError(f"Unknown APP_MODE: {mode}")
