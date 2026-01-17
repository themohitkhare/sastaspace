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

    def __new__(cls) -> "DuckDBManager":
        """Ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the connection if it doesn't exist."""
        if self._connection is None:
            self._initialize_connection()

    def _initialize_connection(self) -> None:
        """Initialize the DuckDB connection and ensure database file exists."""
        db_path = Path(settings.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Connect to DuckDB (creates file if it doesn't exist)
        self._connection = duckdb.connect(str(db_path), read_only=False)

    @property
    def connection(self) -> duckdb.DuckDBPyConnection:
        """Get the DuckDB connection."""
        if self._connection is None:
            self._initialize_connection()
        return self._connection

    def close(self) -> None:
        """Close the DuckDB connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None


# Global singleton instance
_db_manager = DuckDBManager()


@contextmanager
def get_db() -> Generator[duckdb.DuckDBCursor, None, None]:
    """
    Dependency function that yields a DuckDB cursor from the singleton connection.
    
    Usage in FastAPI routes:
        @app.get("/endpoint")
        def my_endpoint(db: duckdb.DuckDBCursor = Depends(get_db)):
            ...
    """
    cursor = _db_manager.connection.cursor()
    try:
        yield cursor
    finally:
        cursor.close()
