"""MongoDB connection management - Async singleton pattern."""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import AsyncGenerator, Optional
from app.core.config import settings


class MongoDBManager:
    """Singleton manager for MongoDB connections."""

    _instance: Optional["MongoDBManager"] = None
    _client: AsyncIOMotorClient | None = None
    _database: AsyncIOMotorDatabase | None = None
    _initialized: bool = False

    def __new__(cls) -> "MongoDBManager":
        """Ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._client = None
            cls._instance._database = None
            cls._instance._initialized = False
        return cls._instance

    async def initialize(self) -> None:
        """Initialize the MongoDB connection."""
        if self._initialized and self._client is not None:
            return

        self._client = AsyncIOMotorClient(settings.mongodb_url)
        self._database = self._client[settings.mongodb_database]
        self._initialized = True

    @property
    def database(self) -> AsyncIOMotorDatabase:
        """Get the MongoDB database instance."""
        if not self._initialized or self._database is None:
            raise RuntimeError("MongoDB not initialized. Call initialize() first.")
        return self._database

    async def close(self) -> None:
        """Close the MongoDB connection."""
        if self._client is not None:
            self._client.close()
            self._client = None
            self._database = None
            self._initialized = False


_db_manager: MongoDBManager | None = None


def _get_db_manager() -> MongoDBManager:
    """Get or create the database manager singleton."""
    global _db_manager
    if _db_manager is None:
        _db_manager = MongoDBManager()
    return _db_manager


async def get_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """
    Async dependency function that yields a MongoDB database instance.
    
    FastAPI will automatically handle this as a dependency with proper cleanup.
    
    Usage in FastAPI routes:
        @app.get("/endpoint")
        async def my_endpoint(db: AsyncIOMotorDatabase = Depends(get_db)):
            ...
    """
    manager = _get_db_manager()
    yield manager.database
