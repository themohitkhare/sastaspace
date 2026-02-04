"""FastAPI application entry point."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.db.session import _get_db_manager

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:9001",
        "http://127.0.0.1:9001",
        "http://192.168.0.38:9001",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

log_level = "DEBUG" if settings.debug else "INFO"
setup_logging(level=log_level)
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("Application starting", extra={"extra_fields": {"component": "startup"}})
    manager = _get_db_manager()
    await manager.initialize()
    logger.info("MongoDB connection initialized", extra={"extra_fields": {"component": "database"}})


@app.on_event("shutdown")
async def shutdown_event() -> None:
    logger.info("Application shutting down", extra={"extra_fields": {"component": "shutdown"}})
    manager = _get_db_manager()
    await manager.close()
    logger.info("MongoDB connection closed", extra={"extra_fields": {"component": "database"}})


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "Welcome to SastaSpace API",
        "version": settings.app_version,
    }
