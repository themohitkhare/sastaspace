"""Abstract base repository pattern for MongoDB operations."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """Abstract base repository for database operations."""

    def __init__(self, database: "AsyncIOMotorDatabase[Any]") -> None:
        """Initialize repository with a MongoDB database instance."""
        self.database = database

    @abstractmethod
    async def get_by_id(self, id: str) -> T | None:
        """Get entity by ID."""
        ...  # pragma: no cover

    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create new entity."""
        ...  # pragma: no cover

    @abstractmethod
    async def update(self, entity: T) -> T:
        """Update existing entity."""
        ...  # pragma: no cover

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete entity by ID."""
        ...  # pragma: no cover
