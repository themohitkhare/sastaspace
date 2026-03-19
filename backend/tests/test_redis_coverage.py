"""Tests for app/core/redis.py — RedisManager singleton, initialize, client property, close, and get_redis."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
import redis.asyncio as aioredis

from app.core.redis import RedisManager, _get_redis_manager, get_redis


def _reset_redis_manager() -> None:
    """Reset the RedisManager singleton and module-level global between tests."""
    RedisManager._instance = None
    RedisManager._client = None
    RedisManager._initialized = False

    import app.core.redis as redis_module

    redis_module._redis_manager = None


class TestRedisManagerSingleton:
    def test_singleton_returns_same_instance(self):
        _reset_redis_manager()
        m1 = RedisManager()
        m2 = RedisManager()
        assert m1 is m2

    def test_new_instance_is_not_initialized(self):
        _reset_redis_manager()
        manager = RedisManager()
        assert manager._initialized is False
        assert manager._client is None


class TestRedisManagerInitialize:
    @pytest.mark.asyncio
    async def test_initialize_creates_client(self):
        _reset_redis_manager()
        manager = RedisManager()

        mock_client = AsyncMock(spec=aioredis.Redis)
        with patch("app.core.redis.aioredis.from_url", return_value=mock_client) as mock_from_url:
            await manager.initialize()

        assert manager._initialized is True
        assert manager._client is mock_client
        mock_from_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self):
        _reset_redis_manager()
        manager = RedisManager()

        mock_client = AsyncMock(spec=aioredis.Redis)
        with patch("app.core.redis.aioredis.from_url", return_value=mock_client) as mock_from_url:
            await manager.initialize()
            await manager.initialize()  # Second call should be a no-op

        mock_from_url.assert_called_once()
        assert manager._client is mock_client

    @pytest.mark.asyncio
    async def test_initialize_uses_redis_url_from_settings(self):
        _reset_redis_manager()
        manager = RedisManager()

        from app.core.config import settings

        mock_client = AsyncMock(spec=aioredis.Redis)
        with patch("app.core.redis.aioredis.from_url", return_value=mock_client) as mock_from_url:
            await manager.initialize()

        call_kwargs = mock_from_url.call_args
        assert call_kwargs[0][0] == settings.redis_url

    @pytest.mark.asyncio
    async def test_initialize_sets_decode_responses_true(self):
        _reset_redis_manager()
        manager = RedisManager()

        mock_client = AsyncMock(spec=aioredis.Redis)
        with patch("app.core.redis.aioredis.from_url", return_value=mock_client) as mock_from_url:
            await manager.initialize()

        call_kwargs = mock_from_url.call_args
        assert call_kwargs[1].get("decode_responses") is True


class TestRedisManagerClientProperty:
    @pytest.mark.asyncio
    async def test_client_property_returns_client_after_init(self):
        _reset_redis_manager()
        manager = RedisManager()

        mock_client = AsyncMock(spec=aioredis.Redis)
        with patch("app.core.redis.aioredis.from_url", return_value=mock_client):
            await manager.initialize()

        assert manager.client is mock_client

    def test_client_property_raises_if_not_initialized(self):
        _reset_redis_manager()
        manager = RedisManager()

        with pytest.raises(RuntimeError, match="Redis not initialized"):
            _ = manager.client

    def test_client_property_raises_if_initialized_but_client_none(self):
        _reset_redis_manager()
        manager = RedisManager()
        manager._initialized = True
        manager._client = None

        with pytest.raises(RuntimeError, match="Redis not initialized"):
            _ = manager.client


class TestRedisManagerClose:
    @pytest.mark.asyncio
    async def test_close_resets_state(self):
        _reset_redis_manager()
        manager = RedisManager()

        mock_client = AsyncMock(spec=aioredis.Redis)
        with patch("app.core.redis.aioredis.from_url", return_value=mock_client):
            await manager.initialize()

        await manager.close()

        mock_client.aclose.assert_called_once()
        assert manager._client is None
        assert manager._initialized is False

    @pytest.mark.asyncio
    async def test_close_when_not_initialized_is_safe(self):
        _reset_redis_manager()
        manager = RedisManager()

        # Should not raise
        await manager.close()

        assert manager._client is None
        assert manager._initialized is False

    @pytest.mark.asyncio
    async def test_close_allows_reinitialize(self):
        _reset_redis_manager()
        manager = RedisManager()

        mock_client = AsyncMock(spec=aioredis.Redis)
        with patch("app.core.redis.aioredis.from_url", return_value=mock_client):
            await manager.initialize()
            await manager.close()

            mock_client2 = AsyncMock(spec=aioredis.Redis)
            with patch("app.core.redis.aioredis.from_url", return_value=mock_client2):
                await manager.initialize()

        assert manager._initialized is True
        assert manager._client is mock_client2


class TestGetRedisManager:
    def test_returns_singleton(self):
        _reset_redis_manager()
        m1 = _get_redis_manager()
        m2 = _get_redis_manager()
        assert m1 is m2

    def test_creates_redis_manager_instance(self):
        _reset_redis_manager()
        manager = _get_redis_manager()
        assert isinstance(manager, RedisManager)

    def test_reuses_existing_module_global(self):
        _reset_redis_manager()
        first = _get_redis_manager()

        import app.core.redis as redis_module

        assert redis_module._redis_manager is first

        # Calling again should return the same object
        second = _get_redis_manager()
        assert second is first


class TestGetRedis:
    @pytest.mark.asyncio
    async def test_get_redis_yields_client(self):
        _reset_redis_manager()
        manager = _get_redis_manager()

        mock_client = AsyncMock(spec=aioredis.Redis)
        with patch("app.core.redis.aioredis.from_url", return_value=mock_client):
            await manager.initialize()

        # get_redis is an async generator
        yielded = []
        async for client in get_redis():
            yielded.append(client)

        assert len(yielded) == 1
        assert yielded[0] is mock_client

    @pytest.mark.asyncio
    async def test_get_redis_raises_if_not_initialized(self):
        _reset_redis_manager()
        # Do NOT call initialize

        with pytest.raises(RuntimeError, match="Redis not initialized"):
            async for _ in get_redis():
                pass
