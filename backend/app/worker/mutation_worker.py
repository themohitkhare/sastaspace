"""Mutation worker — stateless crossover + mutate + fitness evaluation."""

from __future__ import annotations

import logging
import random
from typing import Any

from app.modules.sudoku import genetic
from app.worker.base import BaseWorker
from app.worker.ga_helpers import deserialize_chromosome, serialize_chromosome

logger = logging.getLogger(__name__)


class MutationWorker(BaseWorker):
    """Consumes batched parent pairs from ``ga:tasks``, produces offspring with fitness scores.

    Each message contains N parent pairs + config. Worker does crossover, mutation,
    and fitness evaluation for each pair, then publishes results to ``ga:results:{match_id}``.
    """

    stream = "ga:tasks"
    group = "mutation-workers"

    async def process(self, message_id: str, data: dict[str, Any]) -> None:
        match_id: str = data["match_id"]
        batch_id: str = data["batch_id"]
        parent_pairs: list[list[list[list[int]]]] = data["parent_pairs"]
        mutation_rate: float = data["mutation_rate"]
        starting_board: list[int] = data["starting_board"]
        grid_size: int = data["grid_size"]

        rng = random.Random()
        results: list[dict[str, Any]] = []

        for pair in parent_pairs:
            parent_a = deserialize_chromosome(pair[0])
            parent_b = deserialize_chromosome(pair[1])

            offspring = genetic.crossover(parent_a, parent_b, rng)
            genetic.mutate(offspring, mutation_rate, rng)
            fitness = genetic.calculate_fitness(offspring, starting_board, grid_size)

            results.append(
                {
                    "rows": serialize_chromosome(offspring),
                    "fitness": fitness,
                    "hash": genetic.chromosome_hash(offspring),
                }
            )

        await self.publish(
            f"ga:results:{match_id}",
            {
                "batch_id": batch_id,
                "match_id": match_id,
                "results": results,
            },
        )

        logger.debug(
            "Batch %s: %d offspring (best=%.4f)",
            batch_id,
            len(results),
            max((r["fitness"] for r in results), default=0),
        )
