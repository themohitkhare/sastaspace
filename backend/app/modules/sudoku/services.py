"""Sudoku game orchestrator — manages matches and drives the AI's GA evolution."""

from __future__ import annotations

import random
import uuid
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.sudoku import genetic
from app.modules.sudoku.models import Difficulty, MatchStatus
from app.modules.sudoku.repository import SudokuRepository

# Difficulty-tuned GA parameters (ported from Rust constants)
_PARAMS: dict[Difficulty, dict[str, Any]] = {
    Difficulty.EASY: {
        "population_size": 150,
        "top_fraction": 0.5,
        "mutation_rate": 0.05,
        "stall_threshold": 40,
    },
    Difficulty.MEDIUM: {
        "population_size": 100,
        "top_fraction": 0.5,
        "mutation_rate": 0.1,
        "stall_threshold": 30,
    },
    Difficulty.HARD: {
        "population_size": 60,
        "top_fraction": 0.4,
        "mutation_rate": 0.2,
        "stall_threshold": 20,
    },
}
STALL_EPS = 1e-5
MAX_TABU = 2000
MAX_OFFSPRING_DEDUP_RETRIES = 25


class SudokuService:
    """Orchestrates Sudoku matches: puzzle generation, player moves, AI evolution."""

    def __init__(self, db: AsyncIOMotorDatabase[Any]) -> None:
        self.repo = SudokuRepository(db)

    # ------------------------------------------------------------------
    # Start match
    # ------------------------------------------------------------------

    async def start_match(
        self,
        difficulty: Difficulty,
        grid_size: int,
        custom_board: list[int] | None = None,
    ) -> dict[str, Any]:
        rng = random.Random()
        match_id = uuid.uuid4().hex[:12]
        n = grid_size
        if custom_board and len(custom_board) == n * n:
            starting_board = custom_board
        else:
            starting_board = genetic.generate_puzzle(grid_size, rng)

        # Persist match
        doc: dict[str, Any] = {
            "match_id": match_id,
            "difficulty": difficulty.value,
            "status": MatchStatus.IN_PROGRESS.value,
            "starting_board": starting_board,
            "grid_size": n,
            "player_board": list(starting_board),
        }
        await self.repo.create_match(doc)

        # Create initial AI population
        pop = genetic.generate_initial_population(
            starting_board, n, _PARAMS[difficulty]["population_size"], rng
        )
        tabu: list[int] = [genetic.chromosome_hash(c) for c in pop]
        await self.repo.create_ai_state(match_id, pop, tabu)

        return {"match_id": match_id, "starting_board": starting_board, "grid_size": n}

    # ------------------------------------------------------------------
    # Get match state
    # ------------------------------------------------------------------

    async def get_match(self, match_id: str) -> dict[str, Any]:
        match_doc = await self.repo.get_match(match_id)
        if not match_doc:
            raise ValueError(f"Match {match_id} not found")

        ai_doc = await self.repo.get_ai_state(match_id)
        ai_resp: dict[str, Any] = {
            "generation_count": 0,
            "fitness_score": 0.0,
            "heatmap_data": [],
            "best_board": [],
            "status": match_doc["status"],
        }
        if ai_doc:
            ai_resp.update(
                generation_count=ai_doc.get("generation_count", 0),
                fitness_score=ai_doc.get("fitness_score", 0.0),
                heatmap_data=ai_doc.get("heatmap_data", []),
                best_board=ai_doc.get("best_board", []),
            )

        return {
            "match_id": match_doc["match_id"],
            "difficulty": match_doc["difficulty"],
            "status": match_doc["status"],
            "starting_board": match_doc["starting_board"],
            "grid_size": match_doc["grid_size"],
            "player_board": match_doc.get("player_board", []),
            "ai": ai_resp,
        }

    # ------------------------------------------------------------------
    # Player updates
    # ------------------------------------------------------------------

    async def player_update_board(self, match_id: str, board: list[int]) -> None:
        match_doc = await self.repo.get_match(match_id)
        if not match_doc:
            raise ValueError(f"Match {match_id} not found")
        if match_doc["status"] != MatchStatus.IN_PROGRESS.value:
            raise ValueError("Match is not in progress")
        await self.repo.update_match(match_id, {"player_board": board})

    async def claim_victory(self, match_id: str) -> dict[str, Any]:
        match_doc = await self.repo.get_match(match_id)
        if not match_doc:
            raise ValueError(f"Match {match_id} not found")
        if match_doc["status"] != MatchStatus.IN_PROGRESS.value:
            return {"valid": False, "status": match_doc["status"]}

        player_board = match_doc.get("player_board", [])
        grid_size = match_doc["grid_size"]
        valid = genetic.is_valid_solution(player_board, grid_size)

        if valid:
            await self.repo.update_match(match_id, {"status": MatchStatus.PLAYER_WON.value})
            return {"valid": True, "status": MatchStatus.PLAYER_WON.value}
        return {"valid": False, "status": MatchStatus.IN_PROGRESS.value}

    # ------------------------------------------------------------------
    # AI tick — one generation of the GA
    # ------------------------------------------------------------------

    async def ai_tick(self, match_id: str) -> dict[str, Any]:
        match_doc = await self.repo.get_match(match_id)
        if not match_doc:
            raise ValueError(f"Match {match_id} not found")
        if match_doc["status"] != MatchStatus.IN_PROGRESS.value:
            return {"status": match_doc["status"], "fitness_score": 0.0, "generation_count": 0}

        ai_doc = await self.repo.get_ai_state(match_id)
        if not ai_doc:
            raise ValueError(f"AI state for match {match_id} not found")

        difficulty = Difficulty(match_doc["difficulty"])
        params = _PARAMS[difficulty]
        grid_size: int = match_doc["grid_size"]
        starting_board: list[int] = match_doc["starting_board"]
        generation_count: int = ai_doc.get("generation_count", 0)
        prev_best_fitness: float = ai_doc.get("fitness_score", 0.0)
        prev_stall_count: int = ai_doc.get("stall_count", 0)

        population, tabu_hashes = await self.repo.load_population(ai_doc)
        if not population:
            return {
                "status": match_doc["status"],
                "fitness_score": 0.0,
                "generation_count": generation_count,
            }

        rng = random.Random()
        population_size: int = params["population_size"]
        top_fraction: float = params["top_fraction"]
        mutation_rate: float = params["mutation_rate"]
        stall_threshold: int = params["stall_threshold"]

        # Evaluate fitness
        with_fitness = sorted(
            [(genetic.calculate_fitness(c, starting_board, grid_size), c) for c in population],
            key=lambda x: -x[0],
        )
        best_chrom = with_fitness[0][1] if with_fitness else None
        best_fitness = with_fitness[0][0] if with_fitness else 0.0

        improved = best_fitness > prev_best_fitness + STALL_EPS
        stall_count = 0 if improved else prev_stall_count + 1

        top_n = max(2, int(population_size * top_fraction))
        top_n = min(top_n, len(with_fitness))
        top = [c for _, c in with_fitness[:top_n]]

        used_this_gen: set[int] = {genetic.chromosome_hash(c) for c in top}

        if stall_count >= stall_threshold:
            # Repopulate
            best = best_chrom if best_chrom else top[0]
            fresh = genetic.generate_initial_population(
                starting_board, grid_size, population_size, rng
            )
            if fresh:
                fresh[0] = best
            next_population = fresh
            stall_count = 0
        else:
            next_population = list(top)
            while len(next_population) < population_size:
                offspring = genetic.crossover(
                    top[rng.randrange(len(top))],
                    top[rng.randrange(len(top))],
                    rng,
                )
                genetic.mutate(offspring, mutation_rate, rng)
                retries = 0
                while retries < MAX_OFFSPRING_DEDUP_RETRIES:
                    h = genetic.chromosome_hash(offspring)
                    if h not in tabu_hashes and h not in used_this_gen:
                        used_this_gen.add(h)
                        next_population.append(offspring)
                        break
                    offspring = genetic.crossover(
                        top[rng.randrange(len(top))],
                        top[rng.randrange(len(top))],
                        rng,
                    )
                    genetic.mutate(offspring, mutation_rate, rng)
                    retries += 1
                else:
                    used_this_gen.add(genetic.chromosome_hash(offspring))
                    next_population.append(offspring)

        # Final mutation pass
        for c in next_population:
            genetic.mutate(c, mutation_rate, rng)

        # Update tabu
        for c in next_population:
            h = genetic.chromosome_hash(c)
            if h not in tabu_hashes:
                tabu_hashes.append(h)
        while len(tabu_hashes) > MAX_TABU:
            tabu_hashes.pop(0)

        # Heatmap
        heatmap = genetic.generate_heatmap(next_population, starting_board, grid_size, 0.1)

        # Best board
        n = grid_size
        best_board = (
            genetic.reconstruct_grid(starting_board, best_chrom, grid_size)
            if best_chrom
            else [0] * (n * n)
        )

        # Persist
        await self.repo.save_population(match_id, next_population, tabu_hashes)
        await self.repo.update_ai_state(
            match_id,
            {
                "generation_count": generation_count + 1,
                "stall_count": stall_count,
                "fitness_score": best_fitness,
                "heatmap_data": heatmap,
                "best_board": best_board,
            },
        )

        # Check if AI solved it
        if best_fitness >= 1.0 - 1e-5:
            await self.repo.update_match(match_id, {"status": MatchStatus.SOLVED.value})
            return {
                "status": MatchStatus.SOLVED.value,
                "fitness_score": best_fitness,
                "generation_count": generation_count + 1,
            }

        return {
            "status": MatchStatus.IN_PROGRESS.value,
            "fitness_score": best_fitness,
            "generation_count": generation_count + 1,
        }
