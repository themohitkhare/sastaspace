"""Common API endpoints."""
from fastapi import APIRouter, Depends
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.session import get_db

router = APIRouter()


@router.get("/health")
async def health_check(db = Depends(get_db)) -> dict[str, str]:  # type: ignore
    """
    Health check endpoint that verifies the database connection.
    
    Returns:
        dict: Status message confirming database connectivity
    """
    # Simple query to verify MongoDB connection
    try:
        await db.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception:
        return {"status": "unhealthy", "database": "disconnected"}
