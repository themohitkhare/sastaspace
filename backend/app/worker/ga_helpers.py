"""Shared GA helpers — generic utilities for genetic algorithm workers.

Domain-specific chromosome, fitness, and mutation logic should be provided
by the module that uses the worker framework (e.g., a nesting module, a
scheduling module, etc.). This file contains only domain-agnostic GA operations.
"""

from __future__ import annotations

import random
from typing import Any

STALL_EPS = 1e-5
MAX_TABU = 4000


def evaluate_and_sort(
    population: list[Any],
    fitness_fn: Any,
) -> list[tuple[float, Any]]:
    """Evaluate fitness for all chromosomes and return sorted (desc) list."""
    return sorted(
        [(fitness_fn(c), c) for c in population],
        key=lambda x: -x[0],
    )


def select_top(
    with_fitness: list[tuple[float, Any]],
    top_fraction: float,
    population_size: int,
) -> list[Any]:
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
    top: list[Any],
    count: int,
    rng: random.Random,
) -> list[tuple[Any, Any]]:
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
