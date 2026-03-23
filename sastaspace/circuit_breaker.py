# sastaspace/circuit_breaker.py
"""Thread-safe circuit breaker for LLM API calls."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable

from sastaspace.html_utils import RedesignError

_logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Thread-safe circuit breaker — no external dependencies.

    States:
        CLOSED   — normal operation, requests pass through
        OPEN     — consecutive failures >= threshold, requests rejected immediately
        HALF_OPEN — after reset_timeout, allow one probe request through
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(self, failure_threshold: int = 5, reset_timeout: float = 60.0):
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._consecutive_failures = 0
        self._state = self.CLOSED
        self._opened_at: float = 0.0
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        with self._lock:
            if self._state == self.OPEN:
                if time.monotonic() - self._opened_at >= self._reset_timeout:
                    self._state = self.HALF_OPEN
            return self._state

    def call(self, fn: Callable, *args, **kwargs):
        """Execute *fn* through the circuit breaker.

        Raises RedesignError immediately when the circuit is open.
        """
        current_state = self.state

        if current_state == self.OPEN:
            _logger.warning("Circuit breaker OPEN — rejecting API call")
            raise RedesignError(
                "Claude API circuit breaker is open after repeated failures. "
                "Retrying automatically in 60 seconds."
            )

        try:
            result = fn(*args, **kwargs)
        except Exception:  # noqa: BLE001 — circuit breaker is generic; must catch all to record failures
            self._record_failure()
            raise
        else:
            self._record_success()
            return result

    def _record_failure(self) -> None:
        with self._lock:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self._failure_threshold:
                self._state = self.OPEN
                self._opened_at = time.monotonic()
                _logger.error(
                    "Circuit breaker tripped OPEN after %d consecutive failures",
                    self._consecutive_failures,
                )

    def _record_success(self) -> None:
        with self._lock:
            self._consecutive_failures = 0
            if self._state == self.HALF_OPEN:
                _logger.info("Circuit breaker recovered — moving to CLOSED")
            self._state = self.CLOSED
