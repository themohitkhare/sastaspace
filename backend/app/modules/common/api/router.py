"""Common API endpoints."""

from fastapi import APIRouter, Depends

from app.db.session import get_db

router = APIRouter()


@router.get("/health")
async def health_check(db=Depends(get_db)) -> dict[str, str]:
    """Health check endpoint that verifies the database connection."""
    try:
        await db.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception:
        return {"status": "unhealthy", "database": "disconnected"}
