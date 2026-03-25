# tests/test_circuit_breaker.py
"""Tests for the thread-safe circuit breaker."""

import time

import pytest

from sastaspace.circuit_breaker import CircuitBreaker
from sastaspace.html_utils import RedesignError

# --- State lifecycle tests ---


class TestCircuitBreakerStates:
    def test_starts_closed(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitBreaker.CLOSED

    def test_stays_closed_on_success(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.call(lambda: "ok")
        assert cb.state == CircuitBreaker.CLOSED

    def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError("boom")))
        assert cb.state == CircuitBreaker.OPEN

    def test_open_rejects_immediately(self):
        cb = CircuitBreaker(failure_threshold=1)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("boom")))
        assert cb.state == CircuitBreaker.OPEN
        with pytest.raises(RedesignError, match="circuit breaker is open"):
            cb.call(lambda: "should not run")

    def test_transitions_to_half_open_after_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, reset_timeout=0.1)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("boom")))
        assert cb.state == CircuitBreaker.OPEN
        time.sleep(0.15)
        assert cb.state == CircuitBreaker.HALF_OPEN

    def test_half_open_success_closes(self):
        cb = CircuitBreaker(failure_threshold=1, reset_timeout=0.1)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("boom")))
        time.sleep(0.15)
        assert cb.state == CircuitBreaker.HALF_OPEN
        result = cb.call(lambda: "recovered")
        assert result == "recovered"
        assert cb.state == CircuitBreaker.CLOSED

    def test_half_open_failure_reopens(self):
        cb = CircuitBreaker(failure_threshold=1, reset_timeout=0.1)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("boom")))
        time.sleep(0.15)
        assert cb.state == CircuitBreaker.HALF_OPEN
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("boom again")))
        assert cb.state == CircuitBreaker.OPEN


# --- Failure counting tests ---


class TestFailureCounting:
    def test_resets_on_success(self):
        cb = CircuitBreaker(failure_threshold=3)
        # 2 failures, then 1 success should reset
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError()))
        cb.call(lambda: "ok")
        assert cb.state == CircuitBreaker.CLOSED
        # Need 3 more failures to trip, not 1
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError()))
        assert cb.state == CircuitBreaker.CLOSED

    def test_propagates_original_exception(self):
        cb = CircuitBreaker(failure_threshold=5)
        with pytest.raises(TypeError, match="custom error"):
            cb.call(lambda: (_ for _ in ()).throw(TypeError("custom error")))

    def test_returns_function_result(self):
        cb = CircuitBreaker()
        result = cb.call(lambda: 42)
        assert result == 42

    def test_passes_args_and_kwargs(self):
        cb = CircuitBreaker()

        def add(a, b, extra=0):
            return a + b + extra

        result = cb.call(add, 1, 2, extra=10)
        assert result == 13
