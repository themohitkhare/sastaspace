"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.router import api_router
from app.db.session import get_db_context
from app.modules.sastadice.models import init_tables


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
)

# CORS middleware (configure as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
def startup_event():
    """Initialize database tables on application startup."""
    with get_db_context() as db_cursor:
        init_tables(db_cursor)


@app.get("/")
def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "message": "Welcome to SastaSpace API",
        "version": settings.app_version,
    }
