"""Common API endpoints."""
from fastapi import APIRouter, Depends
import duckdb

from app.db.session import get_db

router = APIRouter()


@router.get("/health")
def health_check(db: duckdb.DuckDBCursor = Depends(get_db)) -> dict[str, str]:
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
