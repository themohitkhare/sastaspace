"""Tests for worker/*.py — BaseWorker, MutationWorker, SolverCoordinator, and GA helpers."""

from __future__ import annotations

import asyncio
import json
import random
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import redis.asyncio as aioredis

from app.worker.ga_helpers import (
    check_stall,
    create_crossover_pairs,
    evaluate_and_sort,
    select_top,
    trim_tabu,
)
from app.worker.mutation_worker import MutationWorker
from app.worker.solver_coordinator import SolverCoordinator

# ─────────────────────────────────────────────────────────────────────────────
# GA Helpers
# ─────────────────────────────────────────────────────────────────────────────


class TestEvaluateAndSort:
    def test_returns_sorted_descending(self):
        population = [3, 1, 4, 1, 5]
        result = evaluate_and_sort(population, lambda c: c)
        scores = [score for score, _ in result]
        assert scores == sorted(scores, reverse=True)

    def test_empty_population(self):
        result = evaluate_and_sort([], lambda c: c)
        assert result == []

    def test_single_element(self):
        result = evaluate_and_sort([42], lambda c: c * 2)
        assert result == [(84, 42)]

    def test_fitness_fn_applied(self):
        population = ["a", "bb", "ccc"]
        result = evaluate_and_sort(population, len)
        assert result[0] == (3, "ccc")
        assert result[-1] == (1, "a")


class TestSelectTop:
    def test_basic_selection(self):
        with_fitness = [(5, "e"), (4, "d"), (3, "c"), (2, "b"), (1, "a")]
        result = select_top(with_fitness, 0.4, 5)
        # top_n = max(2, int(5 * 0.4)) = max(2, 2) = 2
        assert result == ["e", "d"]

    def test_minimum_two_enforced(self):
        with_fitness = [(5, "e"), (4, "d"), (3, "c")]
        # fraction is tiny → min is 2
        result = select_top(with_fitness, 0.01, 100)
        assert len(result) == 2

    def test_cannot_exceed_population(self):
        with_fitness = [(3, "c"), (2, "b")]
        # Ask for 80% of 100 = 80, but only 2 available
        result = select_top(with_fitness, 0.8, 100)
        assert len(result) == 2

    def test_full_fraction(self):
        with_fitness = [(3, "c"), (2, "b"), (1, "a")]
        result = select_top(with_fitness, 1.0, 3)
        assert result == ["c", "b", "a"]


class TestCheckStall:
    def test_improved(self):
        improved, stall_count = check_stall(10.0, 9.0, 5)
        assert improved is True
        assert stall_count == 0

    def test_not_improved(self):
        improved, stall_count = check_stall(10.0, 10.0, 3)
        assert improved is False
        assert stall_count == 4

    def test_just_below_eps(self):
        from app.worker.ga_helpers import STALL_EPS

        improved, stall_count = check_stall(10.0 + STALL_EPS / 2, 10.0, 0)
        assert improved is False

    def test_exactly_eps_boundary(self):
        from app.worker.ga_helpers import STALL_EPS

        improved, stall_count = check_stall(10.0 + STALL_EPS + 1e-9, 10.0, 0)
        assert improved is True
        assert stall_count == 0


class TestCreateCrossoverPairs:
    def test_returns_correct_count(self):
        rng = random.Random(42)
        top = ["a", "b", "c"]
        pairs = create_crossover_pairs(top, 5, rng)
        assert len(pairs) == 5

    def test_pairs_are_from_top(self):
        rng = random.Random(0)
        top = ["x", "y", "z"]
        pairs = create_crossover_pairs(top, 10, rng)
        for a, b in pairs:
            assert a in top
            assert b in top

    def test_zero_count(self):
        rng = random.Random(0)
        pairs = create_crossover_pairs(["a", "b"], 0, rng)
        assert pairs == []

    def test_single_element_top(self):
        rng = random.Random(0)
        pairs = create_crossover_pairs(["only"], 3, rng)
        assert len(pairs) == 3
        for a, b in pairs:
            assert a == "only"
            assert b == "only"


class TestTrimTabu:
    def test_no_trim_needed(self):
        from app.worker.ga_helpers import MAX_TABU

        lst = list(range(MAX_TABU - 1))
        result = trim_tabu(lst)
        assert len(result) == MAX_TABU - 1

    def test_trim_to_max(self):
        from app.worker.ga_helpers import MAX_TABU

        lst = list(range(MAX_TABU + 10))
        result = trim_tabu(lst)
        assert len(result) == MAX_TABU

    def test_trim_removes_front(self):
        from app.worker.ga_helpers import MAX_TABU

        lst = list(range(MAX_TABU + 3))
        result = trim_tabu(lst)
        # Should drop the first 3 items
        assert result[0] == 3

    def test_empty_list(self):
        result = trim_tabu([])
        assert result == []


# ─────────────────────────────────────────────────────────────────────────────
# BaseWorker (via concrete subclasses)
# ─────────────────────────────────────────────────────────────────────────────


def _make_redis_mock() -> AsyncMock:
    """Build a fully-async Redis mock."""
    mock = AsyncMock()
    mock.xgroup_create = AsyncMock(return_value="OK")
    mock.xreadgroup = AsyncMock(return_value=None)
    mock.xack = AsyncMock(return_value=1)
    mock.xautoclaim = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.xadd = AsyncMock(return_value="1234-0")
    mock.aclose = AsyncMock()
    return mock


def _patch_managers(redis_mock: AsyncMock) -> tuple[MagicMock, MagicMock]:
    """Return (redis_manager_mock, db_manager_mock) with the given redis_mock as client."""
    redis_mgr = MagicMock()
    redis_mgr.initialize = AsyncMock()
    redis_mgr.client = redis_mock
    redis_mgr.close = AsyncMock()

    db_mgr = MagicMock()
    db_mgr.initialize = AsyncMock()
    db_mgr.close = AsyncMock()

    return redis_mgr, db_mgr


class TestBaseWorkerSetup:
    @pytest.mark.asyncio
    async def test_setup_creates_consumer_group(self):
        worker = MutationWorker()
        redis_mock = _make_redis_mock()
        redis_mgr, db_mgr = _patch_managers(redis_mock)

        with (
            patch("app.worker.base._get_redis_manager", return_value=redis_mgr),
            patch("app.worker.base._get_db_manager", return_value=db_mgr),
        ):
            await worker.setup()

        redis_mock.xgroup_create.assert_called_once_with(
            worker.stream, worker.group, id="0", mkstream=True
        )
        assert worker._redis is redis_mock

    @pytest.mark.asyncio
    async def test_setup_ignores_busygroup_error(self):
        worker = MutationWorker()
        redis_mock = _make_redis_mock()
        redis_mock.xgroup_create = AsyncMock(
            side_effect=aioredis.ResponseError("BUSYGROUP Consumer Group name already exists")
        )
        redis_mgr, db_mgr = _patch_managers(redis_mock)

        with (
            patch("app.worker.base._get_redis_manager", return_value=redis_mgr),
            patch("app.worker.base._get_db_manager", return_value=db_mgr),
        ):
            # Should not raise
            await worker.setup()

    @pytest.mark.asyncio
    async def test_setup_raises_non_busygroup_error(self):
        worker = MutationWorker()
        redis_mock = _make_redis_mock()
        redis_mock.xgroup_create = AsyncMock(
            side_effect=aioredis.ResponseError("ERR something else")
        )
        redis_mgr, db_mgr = _patch_managers(redis_mock)

        with (
            patch("app.worker.base._get_redis_manager", return_value=redis_mgr),
            patch("app.worker.base._get_db_manager", return_value=db_mgr),
        ):
            with pytest.raises(aioredis.ResponseError):
                await worker.setup()

    def test_consumer_name_is_unique(self):
        w1 = MutationWorker()
        w2 = MutationWorker()
        assert w1.consumer_name != w2.consumer_name

    def test_consumer_name_format(self):
        worker = MutationWorker()
        assert worker.consumer_name.startswith("MutationWorker-")


class TestBaseWorkerPublish:
    @pytest.mark.asyncio
    async def test_publish_xadd(self):
        worker = MutationWorker()
        redis_mock = _make_redis_mock()
        worker._redis = redis_mock

        msg_id = await worker.publish("some-stream", {"key": "value"})

        assert msg_id == "1234-0"
        call_args = redis_mock.xadd.call_args
        assert call_args[0][0] == "some-stream"
        payload = json.loads(call_args[0][1]["payload"])
        assert payload == {"key": "value"}


class TestBaseWorkerReadAndProcess:
    @pytest.mark.asyncio
    async def test_no_messages_returns_early(self):
        worker = MutationWorker()
        redis_mock = _make_redis_mock()
        redis_mock.xreadgroup = AsyncMock(return_value=None)
        worker._redis = redis_mock

        # Should not raise
        await worker._read_and_process()
        redis_mock.xack.assert_not_called()

    @pytest.mark.asyncio
    async def test_processes_message_and_acks(self):
        worker = MutationWorker()
        redis_mock = _make_redis_mock()
        msg_payload = json.dumps({"action": "test"})
        # decode_responses=True means Redis returns string keys; simulate that here
        redis_mock.xreadgroup = AsyncMock(
            return_value=[("ga:tasks", [("1-0", {"payload": msg_payload})])]
        )
        worker._redis = redis_mock

        with patch.object(worker, "process", new_callable=AsyncMock) as mock_process:
            await worker._read_and_process()

        mock_process.assert_called_once_with("1-0", {"action": "test"})
        redis_mock.xack.assert_called_once_with(worker.stream, worker.group, "1-0")

    @pytest.mark.asyncio
    async def test_connection_error_sleeps_and_returns(self):
        worker = MutationWorker()
        redis_mock = _make_redis_mock()
        redis_mock.xreadgroup = AsyncMock(side_effect=aioredis.ConnectionError("down"))
        worker._redis = redis_mock

        with patch("app.worker.base.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await worker._read_and_process()

        mock_sleep.assert_called_once_with(2)

    @pytest.mark.asyncio
    async def test_process_exception_does_not_crash(self):
        """Errors in process() are caught; message stays in PEL."""
        worker = MutationWorker()
        redis_mock = _make_redis_mock()
        msg_payload = json.dumps({"bad": True})
        redis_mock.xreadgroup = AsyncMock(
            return_value=[("ga:tasks", [("2-0", {"payload": msg_payload})])]
        )
        worker._redis = redis_mock

        with patch.object(
            worker, "process", new_callable=AsyncMock, side_effect=RuntimeError("boom")
        ):
            # Should not raise
            await worker._read_and_process()

        # xack must NOT be called when process raises
        redis_mock.xack.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_payload_key_uses_empty_dict(self):
        worker = MutationWorker()
        redis_mock = _make_redis_mock()
        # Message has no "payload" key
        redis_mock.xreadgroup = AsyncMock(return_value=[("ga:tasks", [("3-0", {})])])
        worker._redis = redis_mock

        with patch.object(worker, "process", new_callable=AsyncMock) as mock_process:
            await worker._read_and_process()

        mock_process.assert_called_once_with("3-0", {})


class TestBaseWorkerHeartbeat:
    @pytest.mark.asyncio
    async def test_heartbeat_sets_key_then_sleeps(self):
        worker = MutationWorker()
        redis_mock = _make_redis_mock()
        worker._redis = redis_mock

        sleep_call_count = 0

        async def fake_sleep(n: float) -> None:
            nonlocal sleep_call_count
            sleep_call_count += 1
            # After first sleep, set shutdown so the loop exits
            worker._shutdown.set()

        with patch("app.worker.base.asyncio.sleep", side_effect=fake_sleep):
            await worker._heartbeat_loop()

        redis_mock.set.assert_called_once()
        call_args = redis_mock.set.call_args
        assert "heartbeat" in call_args[0][0]
        assert call_args[0][1] == "alive"

    @pytest.mark.asyncio
    async def test_heartbeat_exits_on_cancelled(self):
        worker = MutationWorker()
        redis_mock = _make_redis_mock()
        worker._redis = redis_mock
        redis_mock.set = AsyncMock(side_effect=asyncio.CancelledError)

        # Should exit cleanly on CancelledError
        await worker._heartbeat_loop()


class TestBaseWorkerClaimStale:
    @pytest.mark.asyncio
    async def test_claim_stale_with_messages_logs(self):
        worker = MutationWorker()
        redis_mock = _make_redis_mock()
        redis_mock.xautoclaim = AsyncMock(
            return_value=("0-0", [b"1-0", b"2-0"])  # 2 stale claimed
        )
        worker._redis = redis_mock

        await worker._claim_stale()
        redis_mock.xautoclaim.assert_called_once()

    @pytest.mark.asyncio
    async def test_claim_stale_no_messages(self):
        worker = MutationWorker()
        redis_mock = _make_redis_mock()
        redis_mock.xautoclaim = AsyncMock(return_value=("0-0", []))
        worker._redis = redis_mock

        await worker._claim_stale()

    @pytest.mark.asyncio
    async def test_claim_stale_response_error_ignored(self):
        worker = MutationWorker()
        redis_mock = _make_redis_mock()
        redis_mock.xautoclaim = AsyncMock(
            side_effect=aioredis.ResponseError("XAUTOCLAIM not supported")
        )
        worker._redis = redis_mock

        # Should not raise
        await worker._claim_stale()

    @pytest.mark.asyncio
    async def test_claim_stale_connection_error_ignored(self):
        worker = MutationWorker()
        redis_mock = _make_redis_mock()
        redis_mock.xautoclaim = AsyncMock(side_effect=aioredis.ConnectionError("lost"))
        worker._redis = redis_mock

        await worker._claim_stale()

    @pytest.mark.asyncio
    async def test_claim_stale_none_result(self):
        worker = MutationWorker()
        redis_mock = _make_redis_mock()
        redis_mock.xautoclaim = AsyncMock(return_value=None)
        worker._redis = redis_mock

        await worker._claim_stale()

    @pytest.mark.asyncio
    async def test_claim_stale_short_result(self):
        """Result with fewer than 2 elements should not crash."""
        worker = MutationWorker()
        redis_mock = _make_redis_mock()
        redis_mock.xautoclaim = AsyncMock(return_value=("0-0",))
        worker._redis = redis_mock

        await worker._claim_stale()


class TestBaseWorkerSignalAndCleanup:
    def test_handle_signal_sets_shutdown(self):
        worker = MutationWorker()
        assert not worker._shutdown.is_set()
        worker._handle_signal()
        assert worker._shutdown.is_set()

    @pytest.mark.asyncio
    async def test_cleanup_closes_managers(self):
        worker = MutationWorker()
        redis_mgr = MagicMock()
        redis_mgr.close = AsyncMock()
        db_mgr = MagicMock()
        db_mgr.close = AsyncMock()

        with (
            patch("app.worker.base._get_redis_manager", return_value=redis_mgr),
            patch("app.worker.base._get_db_manager", return_value=db_mgr),
        ):
            await worker._cleanup()

        redis_mgr.close.assert_called_once()
        db_mgr.close.assert_called_once()


class TestBaseWorkerRun:
    @pytest.mark.asyncio
    async def test_run_exits_gracefully_on_shutdown(self):
        """Worker.run() should exit when _shutdown is set immediately."""
        worker = MutationWorker()
        redis_mock = _make_redis_mock()
        redis_mgr, db_mgr = _patch_managers(redis_mock)

        worker._shutdown.set()  # Pre-set shutdown so run exits immediately

        with (
            patch("app.worker.base._get_redis_manager", return_value=redis_mgr),
            patch("app.worker.base._get_db_manager", return_value=db_mgr),
            patch.object(worker, "_claim_stale", new_callable=AsyncMock),
            patch.object(worker, "_read_and_process", new_callable=AsyncMock),
            patch.object(worker, "_heartbeat_loop", new_callable=AsyncMock),
            patch.object(worker, "_cleanup", new_callable=AsyncMock),
            patch("app.worker.base.asyncio.get_event_loop", return_value=MagicMock()),
        ):
            await worker.run()

    @pytest.mark.asyncio
    async def test_run_one_iteration_then_shutdown(self):
        """Worker.run() executes _claim_stale and _read_and_process before shutdown."""
        worker = MutationWorker()
        redis_mock = _make_redis_mock()
        redis_mgr, db_mgr = _patch_managers(redis_mock)

        call_count = 0

        async def fake_claim_stale() -> None:
            pass

        async def fake_read_and_process() -> None:
            nonlocal call_count
            call_count += 1
            # Set shutdown after first iteration so loop exits
            worker._shutdown.set()

        with (
            patch("app.worker.base._get_redis_manager", return_value=redis_mgr),
            patch("app.worker.base._get_db_manager", return_value=db_mgr),
            patch.object(worker, "_claim_stale", side_effect=fake_claim_stale),
            patch.object(worker, "_read_and_process", side_effect=fake_read_and_process),
            patch.object(worker, "_heartbeat_loop", new_callable=AsyncMock),
            patch.object(worker, "_cleanup", new_callable=AsyncMock),
            patch("app.worker.base.asyncio.get_event_loop", return_value=MagicMock()),
        ):
            await worker.run()

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_run_handles_cancelled_error(self):
        worker = MutationWorker()
        _make_redis_mock()

        async def fake_claim_stale() -> None:
            raise asyncio.CancelledError

        with (
            patch.object(worker, "_claim_stale", side_effect=fake_claim_stale),
            patch.object(worker, "_read_and_process", new_callable=AsyncMock),
            patch.object(worker, "_heartbeat_loop", new_callable=AsyncMock),
            patch.object(worker, "_cleanup", new_callable=AsyncMock),
            patch("app.worker.base.asyncio.get_event_loop", return_value=MagicMock()),
        ):
            await worker.run()


# ─────────────────────────────────────────────────────────────────────────────
# MutationWorker
# ─────────────────────────────────────────────────────────────────────────────


class TestMutationWorker:
    def test_stream_and_group(self):
        worker = MutationWorker()
        assert worker.stream == "ga:tasks"
        assert worker.group == "mutation-workers"

    @pytest.mark.asyncio
    async def test_process_logs_and_returns(self, caplog):
        import logging

        worker = MutationWorker()
        with caplog.at_level(logging.DEBUG, logger="app.worker.mutation_worker"):
            await worker.process("msg-1", {"anything": True})
        # No error and no return value (None)

    @pytest.mark.asyncio
    async def test_process_with_empty_data(self):
        worker = MutationWorker()
        result = await worker.process("msg-empty", {})
        assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# SolverCoordinator
# ─────────────────────────────────────────────────────────────────────────────


class TestSolverCoordinator:
    def test_stream_and_group(self):
        worker = SolverCoordinator()
        assert worker.stream == "solve-requests"
        assert worker.group == "solver-coordinators"

    @pytest.mark.asyncio
    async def test_process_logs_and_returns(self, caplog):
        import logging

        worker = SolverCoordinator()
        with caplog.at_level(logging.DEBUG, logger="app.worker.solver_coordinator"):
            await worker.process("coord-1", {"solve": True})

    @pytest.mark.asyncio
    async def test_process_with_empty_data(self):
        worker = SolverCoordinator()
        result = await worker.process("coord-2", {})
        assert result is None
