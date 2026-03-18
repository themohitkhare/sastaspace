"""Shared GA helpers extracted from SudokuService — used by both ai_tick and SolverCoordinator."""

from __future__ import annotations

import random
from typing import Any

from app.modules.sudoku import genetic
from app.modules.sudoku.models import Difficulty

# Difficulty-tuned GA parameters
PARAMS: dict[Difficulty, dict[str, Any]] = {
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


def serialize_chromosome(c: genetic.Chromosome) -> list[list[int]]:
    """Convert chromosome to JSON-serializable format."""
    return [list(row) for row in c.rows]


def deserialize_chromosome(rows: list[list[int]]) -> genetic.Chromosome:
    """Reconstruct chromosome from serialized rows."""
    return genetic.Chromosome(rows=[list(r) for r in rows])
