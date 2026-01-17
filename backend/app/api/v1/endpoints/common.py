"""Common API endpoints."""
from fastapi import APIRouter, Depends
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import duckdb

from app.db.session import get_db

router = APIRouter()


@router.get("/health")
def health_check(db = Depends(get_db)) -> dict[str, str]:  # type: ignore
    """
    Health check endpoint that verifies the database connection.
    
    Returns:
        dict: Status message confirming database connectivity
    """
    # Simple query to verify DB connection
    result = db.execute("SELECT 1 as status").fetchone()
    
    if result and result[0] == 1:
        return {"status": "healthy", "database": "connected"}
    return {"status": "unhealthy", "database": "disconnected"}
