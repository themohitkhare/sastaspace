"""Shared GA helpers extracted from SudokuService — used by both ai_tick and SolverCoordinator."""

from __future__ import annotations

import random
from typing import Any

from app.modules.sudoku import genetic
from app.modules.sudoku.models import Difficulty

# Difficulty-tuned GA parameters — larger populations for better convergence
PARAMS: dict[Difficulty, dict[str, Any]] = {
    Difficulty.EASY: {
        "population_size": 300,
        "top_fraction": 0.3,
        "mutation_rate": 0.08,
        "stall_threshold": 50,
    },
    Difficulty.MEDIUM: {
        "population_size": 300,
        "top_fraction": 0.3,
        "mutation_rate": 0.12,
        "stall_threshold": 40,
    },
    Difficulty.HARD: {
        "population_size": 300,
        "top_fraction": 0.3,
        "mutation_rate": 0.15,
        "stall_threshold": 30,
    },
}

STALL_EPS = 1e-5
MAX_TABU = 4000
# Fitness threshold above which we attempt backtracking to finish
# Only use backtracking as a finisher when GA is very close to a solution
BACKTRACK_FITNESS_THRESHOLD = 0.95


def evaluate_and_sort(
    population: list[genetic.Chromosome],
    starting_board: list[int],
    grid_size: int,
) -> list[tuple[float, genetic.Chromosome]]:
    """Evaluate fitness for all chromosomes and return sorted (desc) list."""
    return sorted(
        [(genetic.calculate_fitness(c, starting_board, grid_size), c) for c in population],
        key=lambda x: -x[0],
    )


def select_top(
    with_fitness: list[tuple[float, genetic.Chromosome]],
    top_fraction: float,
    population_size: int,
) -> list[genetic.Chromosome]:
    top_n = max(2, int(population_size * top_fraction))
    top_n = min(top_n, len(with_fitness))
    return [c for _, c in with_fitness[:top_n]]


def check_stall(
    best_fitness: float,
    prev_best_fitness: float,
    prev_stall_count: int,
) -> tuple[bool, int]:
    """Returns (improved, new_stall_count)."""
    improved = best_fitness > prev_best_fitness + STALL_EPS
    stall_count = 0 if improved else prev_stall_count + 1
    return improved, stall_count


def create_crossover_pairs(
    top: list[genetic.Chromosome],
    count: int,
    rng: random.Random,
) -> list[tuple[genetic.Chromosome, genetic.Chromosome]]:
    """Create *count* random pairs from the top pool for crossover."""
    pairs = []
    for _ in range(count):
        a = top[rng.randrange(len(top))]
        b = top[rng.randrange(len(top))]
        pairs.append((a, b))
    return pairs


def trim_tabu(tabu_hashes: list[int]) -> list[int]:
    """Trim tabu list to MAX_TABU size."""
    while len(tabu_hashes) > MAX_TABU:
        tabu_hashes.pop(0)
    return tabu_hashes


def try_backtrack_finish(
    best_chrom: genetic.Chromosome,
    starting_board: list[int],
    grid_size: int,
) -> list[int] | None:
    """Attempt to solve the puzzle using backtracking.

    Strategy 1: Solve directly from clues (instant for valid puzzles).
    Strategy 2: Use GA's best board, clear conflicting cells, backtrack from there.

    Returns the solved board or None if backtracking can't fix it.
    """
    # Strategy 1: direct backtracking from clues
    board = list(starting_board)
    if genetic.solve_sudoku(board, grid_size) and genetic.is_valid_solution(board, grid_size):
        return board

    # Strategy 2: use GA's best effort, clear cells with conflicts, then backtrack
    ga_board = genetic.reconstruct_grid(starting_board, best_chrom, grid_size)
    # Find conflicting cells and clear them
    cleaned = _clear_conflicts(ga_board, starting_board, grid_size)
    if genetic.solve_sudoku(cleaned, grid_size) and genetic.is_valid_solution(cleaned, grid_size):
        return cleaned

    return None


def _clear_conflicts(board: list[int], starting_board: list[int], grid_size: int) -> list[int]:
    """Clear non-clue cells that participate in row/col/box conflicts."""
    n = grid_size
    sub = int(n**0.5)
    result = list(board)

    for idx in range(n * n):
        if starting_board[idx] != 0:
            continue  # don't touch clues
        r, c = divmod(idx, n)
        v = result[idx]
        if v == 0:
            continue

        # Check if this value conflicts in its row, column, or box
        has_conflict = False
        for i in range(n):
            if i != c and result[r * n + i] == v:
                has_conflict = True
                break
            if i != r and result[i * n + c] == v:
                has_conflict = True
                break
        if not has_conflict:
            br, bc = (r // sub) * sub, (c // sub) * sub
            for bi in range(sub):
                for bj in range(sub):
                    nr, nc = br + bi, bc + bj
                    if (nr, nc) != (r, c) and result[nr * n + nc] == v:
                        has_conflict = True
                        break
                if has_conflict:
                    break

        if has_conflict:
            result[idx] = 0

    return result


def serialize_chromosome(c: genetic.Chromosome) -> list[list[int]]:
    """Convert chromosome to JSON-serializable format."""
    return [list(row) for row in c.rows]


def deserialize_chromosome(rows: list[list[int]]) -> genetic.Chromosome:
    """Reconstruct chromosome from serialized rows."""
    return genetic.Chromosome(rows=[list(r) for r in rows])
