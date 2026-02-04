"""Common API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.session import get_db

router = APIRouter()


@router.get("/health")
async def health_check(db: AsyncIOMotorDatabase[Any] = Depends(get_db)) -> dict[str, str]:
    try:
        await db.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception:
        return {"status": "unhealthy", "database": "disconnected"}
