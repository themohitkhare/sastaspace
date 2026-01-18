"""Abstract base repository pattern for MongoDB operations."""
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """Abstract base repository for database operations."""

    def __init__(self, database) -> None:  # type: ignore
        """Initialize repository with a MongoDB database instance."""
        self.database = database

    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[T]:
        """Get entity by ID."""
        ...

    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create new entity."""
        ...

    @abstractmethod
    async def update(self, entity: T) -> T:
        """Update existing entity."""
        ...

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete entity by ID."""
        ...
