"""Base worker — Redis Streams consumer with consumer groups, heartbeat, and graceful shutdown."""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import uuid
from abc import ABC, abstractmethod
from typing import Any

import redis.asyncio as aioredis

from app.core.redis import _get_redis_manager
from app.db.session import _get_db_manager

logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL_S = 10
HEARTBEAT_TTL_S = 30
STALE_CLAIM_IDLE_MS = 60_000
READ_BLOCK_MS = 5000
READ_COUNT = 5


class BaseWorker(ABC):
    """Abstract Redis Streams consumer.

    Subclasses define ``stream``, ``group``, and implement ``process()``.
    The ``run()`` loop handles XREADGROUP, XACK, heartbeat, stale claiming,
    and graceful shutdown on SIGTERM/SIGINT.
    """

    stream: str
    group: str

    def __init__(self) -> None:
        self.consumer_name = f"{self.__class__.__name__}-{uuid.uuid4().hex[:8]}"
        self._shutdown = asyncio.Event()
        self._redis: aioredis.Redis | None = None

    # ── Setup ────────────────────────────────────────────────────────

    async def setup(self) -> None:
        """Initialize Redis + MongoDB connections and create consumer group."""
        redis_mgr = _get_redis_manager()
        await redis_mgr.initialize()
        self._redis = redis_mgr.client

        db_mgr = _get_db_manager()
        await db_mgr.initialize()

        # Create consumer group (idempotent — ignore BUSYGROUP)
        try:
            await self._redis.xgroup_create(self.stream, self.group, id="0", mkstream=True)
        except aioredis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

        logger.info(
            "Worker ready: %s (stream=%s, group=%s)",
            self.consumer_name,
            self.stream,
            self.group,
        )

    # ── Abstract ─────────────────────────────────────────────────────

    @abstractmethod
    async def process(self, message_id: str, data: dict[str, Any]) -> None:
        """Process a single stream message. Subclass implements this."""

    # ── Publish ──────────────────────────────────────────────────────

    async def publish(self, target_stream: str, data: dict[str, Any]) -> str:
        """XADD a message to *target_stream*. Returns the message ID."""
        assert self._redis is not None
        payload = json.dumps(data)
        msg_id: str = await self._redis.xadd(target_stream, {"payload": payload})
        return msg_id

    # ── Main Loop ────────────────────────────────────────────────────

    async def run(self) -> None:
        """Consumer loop: read → process → ack → repeat."""
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._handle_signal)

        heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        logger.info("Starting consumer loop: %s", self.consumer_name)
        try:
            while not self._shutdown.is_set():
                await self._claim_stale()
                await self._read_and_process()
        except asyncio.CancelledError:
            pass
        finally:
            heartbeat_task.cancel()
            await self._cleanup()
            logger.info("Worker shut down: %s", self.consumer_name)

    async def _read_and_process(self) -> None:
        assert self._redis is not None
        try:
            messages: list[Any] = await self._redis.xreadgroup(
                groupname=self.group,
                consumername=self.consumer_name,
                streams={self.stream: ">"},
                count=READ_COUNT,
                block=READ_BLOCK_MS,
            )
        except aioredis.ConnectionError:
            logger.warning("Redis connection lost, retrying in 2s...")
            await asyncio.sleep(2)
            return

        if not messages:
            return

        for _stream_name, entries in messages:
            for msg_id, msg_data in entries:
                try:
                    payload = json.loads(msg_data.get("payload", "{}"))
                    await self.process(msg_id, payload)
                    await self._redis.xack(self.stream, self.group, msg_id)
                except Exception:
                    logger.exception("Error processing message %s", msg_id)
                    # Message stays in PEL for retry / stale claiming

    # ── Heartbeat ────────────────────────────────────────────────────

    async def _heartbeat_loop(self) -> None:
        assert self._redis is not None
        key = f"worker:{self.consumer_name}:heartbeat"
        try:
            while not self._shutdown.is_set():
                await self._redis.set(key, "alive", ex=HEARTBEAT_TTL_S)
                await asyncio.sleep(HEARTBEAT_INTERVAL_S)
        except asyncio.CancelledError:
            pass

    # ── Stale Claim ──────────────────────────────────────────────────

    async def _claim_stale(self) -> None:
        """Reclaim messages that have been pending > STALE_CLAIM_IDLE_MS."""
        assert self._redis is not None
        try:
            result = await self._redis.xautoclaim(
                self.stream,
                self.group,
                self.consumer_name,
                min_idle_time=STALE_CLAIM_IDLE_MS,
                count=READ_COUNT,
            )
            if result and len(result) >= 2:
                claimed = result[1]
                if claimed:
                    logger.info("Claimed %d stale messages", len(claimed))
        except (aioredis.ResponseError, aioredis.ConnectionError):
            pass  # XAUTOCLAIM not critical

    # ── Shutdown ─────────────────────────────────────────────────────

    def _handle_signal(self) -> None:
        logger.info("Received shutdown signal")
        self._shutdown.set()

    async def _cleanup(self) -> None:
        redis_mgr = _get_redis_manager()
        await redis_mgr.close()
        db_mgr = _get_db_manager()
        await db_mgr.close()
