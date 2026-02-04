"""Tests for database session management."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings
from app.db.session import MongoDBManager, _get_db_manager, get_db


class TestMongoDBManager:
    """Test MongoDBManager singleton pattern and methods."""

    def test_singleton_pattern(self):
        """Test that MongoDBManager is a singleton."""
        # Reset singleton
        MongoDBManager._instance = None
        MongoDBManager._client = None
        MongoDBManager._database = None
        MongoDBManager._initialized = False

        manager1 = MongoDBManager()
        manager2 = MongoDBManager()

        assert manager1 is manager2
        assert MongoDBManager._instance is manager1

    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test MongoDB initialization."""
        # Reset singleton
        MongoDBManager._instance = None
        MongoDBManager._client = None
        MongoDBManager._database = None
        MongoDBManager._initialized = False

        manager = MongoDBManager()

        with patch("app.db.session.AsyncIOMotorClient") as mock_client_class:
            mock_client = AsyncMock(spec=AsyncIOMotorClient)
            mock_database = AsyncMock(spec=AsyncIOMotorDatabase)
            mock_client.__getitem__.return_value = mock_database
            # Code uses AsyncIOMotorClient[Any](url): __getitem__ then call with url
            mock_client_class.__getitem__.return_value = MagicMock(return_value=mock_client)

            await manager.initialize()

            assert manager._initialized is True
            assert manager._client is not None
            assert manager._database is not None
            mock_client_class.__getitem__.return_value.assert_called_once_with(settings.mongodb_url)

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self):
        """Test that initialize can be called multiple times safely."""
        # Reset singleton
        MongoDBManager._instance = None
        MongoDBManager._client = None
        MongoDBManager._database = None
        MongoDBManager._initialized = False

        manager = MongoDBManager()

        with patch("app.db.session.AsyncIOMotorClient") as mock_client_class:
            mock_client = AsyncMock(spec=AsyncIOMotorClient)
            mock_database = AsyncMock(spec=AsyncIOMotorDatabase)
            mock_client.__getitem__.return_value = mock_database
            mock_client_class.__getitem__.return_value = MagicMock(return_value=mock_client)

            await manager.initialize()
            first_client = manager._client

            await manager.initialize()

            assert manager._client is first_client
            assert mock_client_class.__getitem__.return_value.call_count == 1

    @pytest.mark.asyncio
    async def test_database_property_success(self):
        """Test database property when initialized."""
        # Reset singleton
        MongoDBManager._instance = None
        MongoDBManager._client = None
        MongoDBManager._database = None
        MongoDBManager._initialized = False

        manager = MongoDBManager()

        with patch("app.db.session.AsyncIOMotorClient") as mock_client_class:
            mock_client = AsyncMock(spec=AsyncIOMotorClient)
            mock_database = AsyncMock(spec=AsyncIOMotorDatabase)
            mock_client.__getitem__.return_value = mock_database
            mock_client_class.__getitem__.return_value = MagicMock(return_value=mock_client)

            await manager.initialize()
            db = manager.database

            assert db is mock_database

    def test_database_property_not_initialized(self):
        """Test database property raises error when not initialized."""
        # Reset singleton
        MongoDBManager._instance = None
        MongoDBManager._client = None
        MongoDBManager._database = None
        MongoDBManager._initialized = False

        manager = MongoDBManager()

        with pytest.raises(RuntimeError, match="MongoDB not initialized"):
            _ = manager.database

    @pytest.mark.asyncio
    async def test_close(self):
        """Test closing MongoDB connection."""
        # Reset singleton
        MongoDBManager._instance = None
        MongoDBManager._client = None
        MongoDBManager._database = None
        MongoDBManager._initialized = False

        manager = MongoDBManager()

        with patch("app.db.session.AsyncIOMotorClient") as mock_client_class:
            mock_client = AsyncMock(spec=AsyncIOMotorClient)
            mock_database = AsyncMock(spec=AsyncIOMotorDatabase)
            mock_client.__getitem__.return_value = mock_database
            mock_client_class.__getitem__.return_value = MagicMock(return_value=mock_client)

            await manager.initialize()
            await manager.close()

            mock_client.close.assert_called_once()
            assert manager._client is None
            assert manager._database is None
            assert manager._initialized is False

    @pytest.mark.asyncio
    async def test_close_when_not_initialized(self):
        """Test closing when not initialized (should not error)."""
        # Reset singleton
        MongoDBManager._instance = None
        MongoDBManager._client = None
        MongoDBManager._database = None
        MongoDBManager._initialized = False

        manager = MongoDBManager()

        # Should not raise error
        await manager.close()

        assert manager._client is None
        assert manager._database is None
        assert manager._initialized is False


class TestGetDBManager:
    """Test _get_db_manager function."""

    def test_get_db_manager_creates_singleton(self):
        """Test that _get_db_manager returns singleton."""
        # Reset global
        import app.db.session as session_module

        session_module._db_manager = None

        manager1 = _get_db_manager()
        manager2 = _get_db_manager()

        assert manager1 is manager2


class TestGetDB:
    """Test get_db async generator."""

    @pytest.mark.asyncio
    async def test_get_db_yields_database(self):
        """Test that get_db yields database instance."""
        import app.db.session as session_module

        # Reset singleton and global so _get_db_manager() returns fresh manager
        MongoDBManager._instance = None
        MongoDBManager._client = None
        MongoDBManager._database = None
        MongoDBManager._initialized = False
        session_module._db_manager = None

        with patch("app.db.session.AsyncIOMotorClient") as mock_client_class:
            mock_client = AsyncMock(spec=AsyncIOMotorClient)
            mock_database = AsyncMock(spec=AsyncIOMotorDatabase)
            mock_client.__getitem__.return_value = mock_database
            mock_client_class.__getitem__.return_value = MagicMock(return_value=mock_client)

            manager = _get_db_manager()
            await manager.initialize()

            # Test async generator
            async for db in get_db():
                assert db is mock_database
                break  # Only test first yield
