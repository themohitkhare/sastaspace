"""Mutation worker — generic stateless crossover + mutate + fitness evaluation.

This is a placeholder shell. When a domain module (e.g., nesting, scheduling)
is added, it registers its crossover/mutate/fitness functions here.
Currently no domain is active, so the worker logs and acknowledges messages.
"""

from __future__ import annotations

import logging
from typing import Any

from app.worker.base import BaseWorker

logger = logging.getLogger(__name__)


class MutationWorker(BaseWorker):
    """Consumes batched parent pairs from ``ga:tasks``, produces offspring with fitness scores.

    When a domain module is registered, this worker deserializes pairs,
    applies crossover + mutation + fitness, and publishes results.
    Currently a no-op placeholder.
    """

    stream = "ga:tasks"
    group = "mutation-workers"

    async def process(self, message_id: str, data: dict[str, Any]) -> None:
        logger.debug("MutationWorker received message %s (no domain registered)", message_id)
