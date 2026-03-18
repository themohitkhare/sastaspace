"""Solver coordinator — orchestrates the GA loop with scatter-gather across mutation workers."""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
import uuid
from typing import Any

import redis.asyncio as aioredis

from app.core.redis import _get_redis_manager
from app.db.session import _get_db_manager
from app.modules.sudoku import genetic
from app.modules.sudoku.models import Difficulty, MatchStatus
from app.modules.sudoku.repository import SudokuRepository
from app.worker.base import BaseWorker
from app.worker.ga_helpers import (
    BACKTRACK_FITNESS_THRESHOLD,
    PARAMS,
    check_stall,
    create_crossover_pairs,
    deserialize_chromosome,
    evaluate_and_sort,
    select_top,
    serialize_chromosome,
    trim_tabu,
    try_backtrack_finish,
)

logger = logging.getLogger(__name__)

MAX_GENS_PER_SOLVE = 1000
BATCH_SIZE = 20
COLLECT_TIMEOUT_S = 30
PERSIST_EVERY_N_GENS = 1


class SolverCoordinator(BaseWorker):
    """Consumes solve requests, orchestrates the GA loop with fan-out to mutation workers.

    For each puzzle:
      1. Load population from MongoDB
      2. Selection (in-process — needs global view)
      3. Fan out crossover pairs as batches to ``ga:tasks``
      4. Collect results from ``ga:results:{match_id}``
      5. Assemble next generation, update tabu
      6. Persist to MongoDB periodically
      7. Repeat until solved or budget exhausted
    """

    stream = "sudoku:solve-requests"
    group = "solver-coordinators"

    async def process(self, message_id: str, data: dict[str, Any]) -> None:
        match_id: str = data["match_id"]
        logger.info("Starting solve for match %s", match_id)

        db = _get_db_manager().database
        repo = SudokuRepository(db)
        r = _get_redis_manager().client

        # Load match state
        match_doc = await repo.get_match(match_id)
        if not match_doc:
            logger.error("Match %s not found", match_id)
            return
        if match_doc["status"] != MatchStatus.IN_PROGRESS.value:
            logger.info("Match %s not in progress (status=%s)", match_id, match_doc["status"])
            return

        # Distributed lock to prevent duplicate solves
        lock_key = f"solving:{match_id}"
        acquired = await r.set(lock_key, self.consumer_name, nx=True, ex=300)
        if not acquired:
            logger.info("Match %s already being solved", match_id)
            return

        try:
            await self._solve_loop(repo, r, match_doc)
        finally:
            await r.delete(lock_key)
            # Cleanup result stream
            result_stream = f"ga:results:{match_id}"
            await r.delete(result_stream)

    async def _solve_loop(
        self,
        repo: SudokuRepository,
        r: aioredis.Redis,
        match_doc: dict[str, Any],
    ) -> None:
        match_id: str = match_doc["match_id"]
        difficulty = Difficulty(match_doc["difficulty"])
        params = PARAMS[difficulty]
        grid_size: int = match_doc["grid_size"]
        starting_board: list[int] = match_doc["starting_board"]
        population_size: int = params["population_size"]
        mutation_rate: float = params["mutation_rate"]
        stall_threshold: int = params["stall_threshold"]

        # Load AI state
        ai_doc = await repo.get_ai_state(match_id)
        if not ai_doc:
            logger.error("AI state for %s not found", match_id)
            return

        population, tabu_hashes = await repo.load_population(ai_doc)
        if not population:
            logger.error("Empty population for %s", match_id)
            return

        generation_count: int = ai_doc.get("generation_count", 0)
        prev_best_fitness: float = ai_doc.get("fitness_score", 0.0)
        prev_stall_count: int = ai_doc.get("stall_count", 0)

        rng = random.Random()

        result_stream = f"ga:results:{match_id}"
        result_group = f"coord-{match_id}"

        # Create consumer group for result stream
        try:
            await r.xgroup_create(result_stream, result_group, id="0", mkstream=True)
        except aioredis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

        for gen in range(MAX_GENS_PER_SOLVE):
            if self._shutdown.is_set():
                break

            # ── Evaluate + Select ───────────────────────────────
            with_fitness = evaluate_and_sort(population, starting_board, grid_size)
            best_fitness = with_fitness[0][0] if with_fitness else 0.0
            best_chrom = with_fitness[0][1] if with_fitness else None

            # Check if GA solved it directly
            if best_fitness >= 1.0 - 1e-5:
                await self._finish_solved(
                    repo,
                    match_id,
                    population,
                    tabu_hashes,
                    generation_count + gen + 1,
                    best_fitness,
                    starting_board,
                    grid_size,
                    best_chrom,
                )
                logger.info("GA SOLVED %s in %d gens!", match_id, generation_count + gen + 1)
                return

            # Hybrid: try backtracking from clues periodically once GA makes progress
            if best_fitness >= BACKTRACK_FITNESS_THRESHOLD and best_chrom is not None:
                solved_board = try_backtrack_finish(
                    best_chrom,
                    starting_board,
                    grid_size,
                )
                if solved_board is not None:
                    await self._finish_solved(
                        repo,
                        match_id,
                        population,
                        tabu_hashes,
                        generation_count + gen + 1,
                        1.0,
                        starting_board,
                        grid_size,
                        best_chrom,
                        override_board=solved_board,
                    )
                    logger.info(
                        "HYBRID SOLVED %s in %d gens (GA %.2f%% + backtrack)!",
                        match_id,
                        generation_count + gen + 1,
                        best_fitness * 100,
                    )
                    return

            _, stall_count = check_stall(best_fitness, prev_best_fitness, prev_stall_count)

            top = select_top(with_fitness, params["top_fraction"], population_size)

            if stall_count >= stall_threshold:
                # Repopulate — keep best, regenerate rest
                fresh = genetic.generate_initial_population(
                    starting_board, grid_size, population_size, rng
                )
                if fresh and best_chrom:
                    fresh[0] = best_chrom
                population = fresh
                stall_count = 0
                prev_best_fitness = best_fitness
                prev_stall_count = 0
                continue

            # ── Fan out + collect + assemble ────────────────────
            population, tabu_hashes = await self._run_distributed_generation(
                r,
                match_id,
                top,
                population_size,
                mutation_rate,
                starting_board,
                grid_size,
                tabu_hashes,
                rng,
                result_stream,
                result_group,
            )

            prev_best_fitness = best_fitness
            prev_stall_count = stall_count

            # ── Periodic persist ────────────────────────────────
            if gen % PERSIST_EVERY_N_GENS == 0:
                await self._persist_state(
                    repo,
                    match_id,
                    population,
                    tabu_hashes,
                    generation_count + gen + 1,
                    stall_count,
                    best_fitness,
                    starting_board,
                    grid_size,
                    best_chrom,
                )

        # Budget exhausted — persist final state
        with_fitness = evaluate_and_sort(population, starting_board, grid_size)
        best_fitness = with_fitness[0][0] if with_fitness else 0.0
        best_chrom = with_fitness[0][1] if with_fitness else None
        await self._persist_state(
            repo,
            match_id,
            population,
            tabu_hashes,
            generation_count + MAX_GENS_PER_SOLVE,
            prev_stall_count,
            best_fitness,
            starting_board,
            grid_size,
            best_chrom,
        )
        logger.info(
            "Budget exhausted for %s after %d generations (fitness=%.4f)",
            match_id,
            generation_count + MAX_GENS_PER_SOLVE,
            best_fitness,
        )

    async def _run_distributed_generation(
        self,
        r: aioredis.Redis,
        match_id: str,
        top: list[genetic.Chromosome],
        population_size: int,
        mutation_rate: float,
        starting_board: list[int],
        grid_size: int,
        tabu_hashes: list[int],
        rng: random.Random,
        result_stream: str,
        result_group: str,
    ) -> tuple[list[genetic.Chromosome], list[int]]:
        """Fan out crossover pairs to workers, collect results, assemble next generation."""
        offspring_needed = population_size - len(top)
        pairs = create_crossover_pairs(top, offspring_needed, rng)

        batch_ids: list[str] = []
        for i in range(0, len(pairs), BATCH_SIZE):
            batch = pairs[i : i + BATCH_SIZE]
            batch_id = uuid.uuid4().hex[:8]
            batch_ids.append(batch_id)
            await self.publish(
                "ga:tasks",
                {
                    "match_id": match_id,
                    "batch_id": batch_id,
                    "parent_pairs": [
                        [serialize_chromosome(a), serialize_chromosome(b)] for a, b in batch
                    ],
                    "mutation_rate": mutation_rate,
                    "starting_board": starting_board,
                    "grid_size": grid_size,
                },
            )

        collected: dict[str, list[dict[str, Any]]] = {}
        deadline = time.monotonic() + COLLECT_TIMEOUT_S
        while len(collected) < len(batch_ids) and time.monotonic() < deadline:
            try:
                messages = await r.xreadgroup(
                    groupname=result_group,
                    consumername=self.consumer_name,
                    streams={result_stream: ">"},
                    count=10,
                    block=1000,
                )
            except aioredis.ConnectionError:
                await asyncio.sleep(1)
                continue
            if not messages:
                continue
            for _stream_name, entries in messages:
                for msg_id, msg_data in entries:
                    result = json.loads(msg_data.get("payload", "{}"))
                    collected[result["batch_id"]] = result["results"]
                    await r.xack(result_stream, result_group, msg_id)

        next_population = list(top)
        for batch_results in collected.values():
            for result in batch_results:
                offspring = deserialize_chromosome(result["rows"])
                h = result["hash"]
                if h not in tabu_hashes:
                    tabu_hashes.append(h)
                next_population.append(offspring)

        return next_population[:population_size], trim_tabu(tabu_hashes)

    async def _finish_solved(
        self,
        repo: SudokuRepository,
        match_id: str,
        population: list[genetic.Chromosome],
        tabu_hashes: list[int],
        generation_count: int,
        best_fitness: float,
        starting_board: list[int],
        grid_size: int,
        best_chrom: genetic.Chromosome | None,
        override_board: list[int] | None = None,
    ) -> None:
        """Persist final solved state and mark match as won."""
        await self._persist_state(
            repo,
            match_id,
            population,
            tabu_hashes,
            generation_count,
            0,
            best_fitness,
            starting_board,
            grid_size,
            best_chrom,
            override_board=override_board,
        )
        await repo.update_match(match_id, {"status": MatchStatus.SOLVED.value})

    async def _persist_state(
        self,
        repo: SudokuRepository,
        match_id: str,
        population: list[genetic.Chromosome],
        tabu_hashes: list[int],
        generation_count: int,
        stall_count: int,
        best_fitness: float,
        starting_board: list[int],
        grid_size: int,
        best_chrom: genetic.Chromosome | None,
        override_board: list[int] | None = None,
    ) -> None:
        heatmap = genetic.generate_heatmap(population, starting_board, grid_size, 0.1)
        if override_board is not None:
            best_board = override_board
        elif best_chrom:
            best_board = genetic.reconstruct_grid(starting_board, best_chrom, grid_size)
        else:
            best_board = [0] * (grid_size * grid_size)
        await repo.save_population(match_id, population, tabu_hashes)
        await repo.update_ai_state(
            match_id,
            {
                "generation_count": generation_count,
                "stall_count": stall_count,
                "fitness_score": best_fitness,
                "heatmap_data": heatmap,
                "best_board": best_board,
            },
        )
