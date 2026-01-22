"""Tests for base repository."""

from unittest.mock import AsyncMock

import pytest

from app.core.db_repo import BaseRepository


class ConcreteRepository(BaseRepository[str]):
    """Concrete implementation for testing."""

    async def get_by_id(self, id: str) -> str | None:
        """Get by ID implementation."""
        return f"entity_{id}" if id else None

    async def create(self, entity: str) -> str:
        """Create implementation."""
        return entity

    async def update(self, entity: str) -> str:
        """Update implementation."""
        return entity

    async def delete(self, id: str) -> bool:
        """Delete implementation."""
        return True


class TestBaseRepository:
    """Test BaseRepository abstract class."""

    def test_init(self):
        """Test repository initialization."""
        mock_db = AsyncMock()
        repo = ConcreteRepository(mock_db)

        assert repo.database is mock_db

    def test_cannot_instantiate_base(self):
        """Test that BaseRepository cannot be instantiated directly."""
        mock_db = AsyncMock()

        # BaseRepository is abstract, so it should raise TypeError when instantiated
        # However, in Python, abstract methods only raise when called, not on instantiation
        # So we test that abstract methods raise NotImplementedError when called
        try:
            repo = BaseRepository(mock_db)  # type: ignore
            # If instantiation succeeds, abstract methods should raise NotImplementedError
            with pytest.raises(NotImplementedError):
                # This will fail because it's abstract
                pass
        except TypeError:
            # Some Python versions may raise TypeError on instantiation
            pass

    @pytest.mark.asyncio
    async def test_get_by_id(self):
        """Test get_by_id method."""
        mock_db = AsyncMock()
        repo = ConcreteRepository(mock_db)

        result = await repo.get_by_id("test_id")

        assert result == "entity_test_id"

    @pytest.mark.asyncio
    async def test_create(self):
        """Test create method."""
        mock_db = AsyncMock()
        repo = ConcreteRepository(mock_db)

        result = await repo.create("new_entity")

        assert result == "new_entity"

    @pytest.mark.asyncio
    async def test_update(self):
        """Test update method."""
        mock_db = AsyncMock()
        repo = ConcreteRepository(mock_db)

        result = await repo.update("updated_entity")

        assert result == "updated_entity"

    @pytest.mark.asyncio
    async def test_delete(self):
        """Test delete method."""
        mock_db = AsyncMock()
        repo = ConcreteRepository(mock_db)

        result = await repo.delete("test_id")

        assert result is True
