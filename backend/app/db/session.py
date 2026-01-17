"""DuckDB connection management - Singleton pattern."""
import duckdb
from pathlib import Path
from typing import Generator
from contextlib import contextmanager

from app.core.config import settings


class DuckDBManager:
    """Singleton manager for DuckDB connections."""

    _instance: "DuckDBManager" = None
    _connection: duckdb.DuckDBPyConnection | None = None
    _initialized: bool = False

    def __new__(cls) -> "DuckDBManager":
        """Ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._connection = None
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize instance - connection is lazy-loaded."""
        # Don't initialize connection here to avoid import-time locks
        pass

    def _initialize_connection(self) -> None:
        """Initialize the DuckDB connection and ensure database file exists."""
        if self._initialized and self._connection is not None:
            return
            
        db_path = Path(settings.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Connect to DuckDB (creates file if it doesn't exist)
        self._connection = duckdb.connect(str(db_path), read_only=False)
        self._initialized = True

    @property
    def connection(self) -> duckdb.DuckDBPyConnection:
        """Get the DuckDB connection (lazy initialization)."""
        if self._connection is None or not self._initialized:
            self._initialize_connection()
        return self._connection

    def close(self) -> None:
        """Close the DuckDB connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None


# Global singleton instance - connection is lazy-loaded when first accessed
_db_manager: DuckDBManager | None = None


def _get_db_manager() -> DuckDBManager:
    """Get or create the database manager singleton."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DuckDBManager()
    return _db_manager


def get_db() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """
    Dependency function that yields a DuckDB cursor from the singleton connection.
    
    FastAPI will automatically handle this as a dependency with proper cleanup.
    
    Usage in FastAPI routes:
        @app.get("/endpoint")
        def my_endpoint(db: duckdb.DuckDBPyConnection = Depends(get_db)):
            ...
    """
    manager = _get_db_manager()
    cursor = manager.connection.cursor()
    try:
        yield cursor
    finally:
        cursor.close()


@contextmanager
def get_db_context():
    """
    Context manager version for non-FastAPI usage (e.g., startup events).
    
    Usage:
        with get_db_context() as db_cursor:
            # use db_cursor
            ...
    """
    manager = _get_db_manager()
    cursor = manager.connection.cursor()
    try:
        yield cursor
    finally:
        cursor.close()
