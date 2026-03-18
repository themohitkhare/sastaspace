"""Redis connection management — async singleton pattern."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import redis.asyncio as aioredis

from app.core.config import settings


class RedisManager:
    """Singleton manager for Redis connections."""

    _instance: RedisManager | None = None
    _client: aioredis.Redis | None = None
    _initialized: bool = False

    def __new__(cls) -> RedisManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._client = None
            cls._instance._initialized = False
        return cls._instance

    async def initialize(self) -> None:
        if self._initialized and self._client is not None:
            return
        self._client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
        self._initialized = True

    @property
    def client(self) -> aioredis.Redis:
        if not self._initialized or self._client is None:
            raise RuntimeError("Redis not initialized. Call initialize() first.")
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            self._initialized = False


_redis_manager: RedisManager | None = None


def _get_redis_manager() -> RedisManager:
    global _redis_manager  # noqa: PLW0603
    if _redis_manager is None:
        _redis_manager = RedisManager()
    return _redis_manager


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """FastAPI dependency that yields a Redis client."""
    manager = _get_redis_manager()
    yield manager.client
