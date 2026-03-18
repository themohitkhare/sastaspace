"""Solver coordinator — generic orchestrator for GA scatter-gather loops.

This is a placeholder shell. When a domain module (e.g., nesting, scheduling)
is added, it implements the solve loop using the BaseWorker scatter-gather pattern.
Currently no domain is active, so the coordinator logs and acknowledges messages.
"""

from __future__ import annotations

import logging
from typing import Any

from app.worker.base import BaseWorker

logger = logging.getLogger(__name__)


class SolverCoordinator(BaseWorker):
    """Consumes solve requests and orchestrates GA loops via scatter-gather.

    When a domain module is registered, this coordinator:
    1. Loads problem state from MongoDB
    2. Runs the GA generation loop (selection → fan-out → collect → assemble)
    3. Persists results periodically
    Currently a no-op placeholder.
    """

    stream = "solve-requests"
    group = "solver-coordinators"

    async def process(self, message_id: str, data: dict[str, Any]) -> None:
        logger.debug("SolverCoordinator received message %s (no domain registered)", message_id)
