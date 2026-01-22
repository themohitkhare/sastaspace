"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import _get_db_manager

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,  # type: ignore[arg-type]
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


@app.on_event("startup")
async def startup_event():
    """Initialize MongoDB connection on application startup."""
    manager = _get_db_manager()
    await manager.initialize()


@app.on_event("shutdown")
async def shutdown_event():
    """Close MongoDB connection on application shutdown."""
    manager = _get_db_manager()
    await manager.close()


@app.get("/")
def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "message": "Welcome to SastaSpace API",
        "version": settings.app_version,
    }
