"""Abstract base repository pattern for DuckDB operations."""
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import duckdb

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """Abstract base repository for database operations."""

    def __init__(self, cursor) -> None:  # type: ignore
        """Initialize repository with a DuckDB cursor."""
        self.cursor = cursor

    @abstractmethod
    def get_by_id(self, id: str) -> Optional[T]:
        """Get entity by ID."""
        ...

    @abstractmethod
    def create(self, entity: T) -> T:
        """Create new entity."""
        ...

    @abstractmethod
    def update(self, entity: T) -> T:
        """Update existing entity."""
        ...

    @abstractmethod
    def delete(self, id: str) -> bool:
        """Delete entity by ID."""
        ...
