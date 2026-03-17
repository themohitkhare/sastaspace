"""Genetic algorithm Sudoku solver.

Ported from spacetimedb/src/genetic.rs — chromosome representation,
13 mutation types, crossover, fitness, heatmap, puzzle generation,
backtracking solver, and tabu/dedup helpers.
"""

from __future__ import annotations

import enum
import hashlib
import math
import random
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Core data structures
# ---------------------------------------------------------------------------


@dataclass
class Chromosome:
    """One candidate: each element is the *missing* values for that row, permuted."""

    rows: list[list[int]] = field(default_factory=list)

    @classmethod
    def from_missing_rows(cls, rows: list[list[int]]) -> Chromosome:
        return cls(rows=[list(r) for r in rows])


# ---------------------------------------------------------------------------
# Board helpers
# ---------------------------------------------------------------------------


def _sub_size(grid_size: int) -> int:
    return int(math.isqrt(grid_size))


def reconstruct_grid(
    starting_board: list[int],
    chromosome: Chromosome,
    grid_size: int,
) -> list[int]:
    """Rebuild a full N×N board from a chromosome and the starting clues."""
    n = grid_size
    grid = [0] * (n * n)
    for r, row_missing in enumerate(chromosome.rows):
        start = r * n
        idx = 0
        for c in range(n):
            if starting_board[start + c] != 0:
                grid[start + c] = starting_board[start + c]
            else:
                grid[start + c] = row_missing[idx]
                idx += 1
    return grid


def is_valid_solution(board: list[int], grid_size: int) -> bool:
    """Check rows, columns, and sub-grids for a complete valid board."""
    n = grid_size
    if len(board) != n * n:
        return False
    sub = _sub_size(grid_size)
    for r in range(n):
        seen: set[int] = set()
        for c in range(n):
            v = board[r * n + c]
            if v == 0 or v in seen:
                return False
            seen.add(v)
    for c in range(n):
        seen = set()
        for r in range(n):
            v = board[r * n + c]
            if v in seen:
                return False
            seen.add(v)
    for bi in range(sub):
        for bj in range(sub):
            seen = set()
            for ri in range(sub):
                for rj in range(sub):
                    v = board[(bi * sub + ri) * n + (bj * sub + rj)]
                    if v in seen:
                        return False
                    seen.add(v)
    return True


# ---------------------------------------------------------------------------
# Backtracking solver  (used for puzzle generation & validation)
# ---------------------------------------------------------------------------


def solve_sudoku(board: list[int], grid_size: int) -> bool:
    """In-place backtracking solver.  Returns True if solved."""
    if grid_size != 9:
        return False
    n = grid_size
    if len(board) != n * n:
        return False
    sub = _sub_size(grid_size)

    def _is_safe(idx: int, val: int) -> bool:
        r, c = divmod(idx, n)
        for i in range(n):
            if board[r * n + i] == val or board[i * n + c] == val:
                return False
        br = (r // sub) * sub
        bc = (c // sub) * sub
        for i in range(sub):
            for j in range(sub):
                if board[(br + i) * n + (bc + j)] == val:
                    return False
        return True

    def _backtrack(idx: int) -> bool:
        if idx == n * n:
            return True
        if board[idx] != 0:
            return _backtrack(idx + 1)
        for val in range(1, n + 1):
            if _is_safe(idx, val):
                board[idx] = val
                if _backtrack(idx + 1):
                    return True
                board[idx] = 0
        return False

    return _backtrack(0)


# ---------------------------------------------------------------------------
# Puzzle generation
# ---------------------------------------------------------------------------


def generate_puzzle(grid_size: int, rng: random.Random | None = None) -> list[int]:
    """Generate a valid puzzle with ~45 % holes for 9×9."""
    if rng is None:
        rng = random.Random()

    n = grid_size
    if n == 9:
        board = [0] * 81
        # Fill diagonal sub-grids first (independent → no conflicts)
        sub = 3
        for d in range(3):
            vals = list(range(1, 10))
            rng.shuffle(vals)
            for i in range(3):
                for j in range(3):
                    board[(d * sub + i) * n + (d * sub + j)] = vals[i * 3 + j]
        solve_sudoku(board, 9)
        # Punch holes
        holes = rng.randint(36, 50)
        indices = list(range(81))
        rng.shuffle(indices)
        for idx in indices[:holes]:
            board[idx] = 0
        return board

    if n == 4:
        # Simple 4×4: fill via backtracking then punch holes
        board = [0] * 16
        _fill_small(board, 4, 2, rng)
        holes = rng.randint(4, 8)
        indices = list(range(16))
        rng.shuffle(indices)
        for idx in indices[:holes]:
            board[idx] = 0
        return board

    if n == 16:
        # 16×16: fill via diagonal sub-grids + backtracking, then punch
        board = [0] * 256
        sub = 4
        for d in range(4):
            vals = list(range(1, 17))
            rng.shuffle(vals)
            for i in range(4):
                for j in range(4):
                    board[(d * sub + i) * n + (d * sub + j)] = vals[i * 4 + j]
        _fill_small(board, 16, 4, rng)
        holes = rng.randint(100, 160)
        indices = list(range(256))
        rng.shuffle(indices)
        for idx in indices[:holes]:
            board[idx] = 0
        return board

    # Unsupported: return zeros
    return [0] * (n * n)


def _fill_small(board: list[int], n: int, sub: int, rng: random.Random) -> bool:
    """Backtracking fill for small boards using the given rng for value ordering."""
    for idx in range(n * n):
        if board[idx] != 0:
            continue
        vals = list(range(1, n + 1))
        rng.shuffle(vals)
        for v in vals:
            if _safe_placement(board, n, sub, idx, v):
                board[idx] = v
                if _fill_small(board, n, sub, rng):
                    return True
                board[idx] = 0
        return False
    return True


def _safe_placement(board: list[int], n: int, sub: int, idx: int, val: int) -> bool:
    r, c = divmod(idx, n)
    for i in range(n):
        if board[r * n + i] == val or board[i * n + c] == val:
            return False
    br = (r // sub) * sub
    bc = (c // sub) * sub
    for i in range(sub):
        for j in range(sub):
            if board[(br + i) * n + (bc + j)] == val:
                return False
    return True


# ---------------------------------------------------------------------------
# Chromosome construction
# ---------------------------------------------------------------------------


def _chromosome_from_starting_board(
    starting_board: list[int],
    grid_size: int,
    rng: random.Random,
) -> Chromosome:
    n = grid_size
    rows: list[list[int]] = []
    for r in range(n):
        start = r * n
        present = {starting_board[start + c] for c in range(n) if starting_board[start + c] != 0}
        missing = [v for v in range(1, n + 1) if v not in present]
        rng.shuffle(missing)
        rows.append(missing)
    return Chromosome(rows=rows)


def chromosome_hash(chromosome: Chromosome) -> int:
    """Deterministic hash for tabu / dedup."""
    h = hashlib.sha256()
    for row in chromosome.rows:
        for v in row:
            h.update(v.to_bytes(1, "little"))
        h.update(b"|")
    return int.from_bytes(h.digest()[:8], "little")


def generate_initial_population(
    starting_board: list[int],
    grid_size: int,
    population_count: int,
    rng: random.Random,
) -> list[Chromosome]:
    max_dedup_retries = 50
    seen: set[int] = set()
    out: list[Chromosome] = []
    for _ in range(population_count):
        c = _chromosome_from_starting_board(starting_board, grid_size, rng)
        retries = 0
        h = chromosome_hash(c)
        while retries < max_dedup_retries and h in seen:
            c = _chromosome_from_starting_board(starting_board, grid_size, rng)
            h = chromosome_hash(c)
            retries += 1
        seen.add(h)
        out.append(c)
    return out


# ---------------------------------------------------------------------------
# Fitness
# ---------------------------------------------------------------------------


def calculate_fitness(
    chromosome: Chromosome,
    starting_board: list[int],
    grid_size: int,
) -> float:
    n = grid_size
    grid = reconstruct_grid(starting_board, chromosome, grid_size)
    sub = _sub_size(grid_size)
    duplicates = 0

    for c in range(n):
        seen: set[int] = set()
        for r in range(n):
            v = grid[r * n + c]
            if v in seen:
                duplicates += 1
            else:
                seen.add(v)

    for bi in range(sub):
        for bj in range(sub):
            seen = set()
            for ri in range(sub):
                for rj in range(sub):
                    r = bi * sub + ri
                    c_idx = bj * sub + rj
                    v = grid[r * n + c_idx]
                    if v in seen:
                        duplicates += 1
                    else:
                        seen.add(v)

    normalizer = (n + n) * n
    if normalizer == 0:
        return 1.0
    penalty = duplicates / normalizer
    return max(0.0, 1.0 - penalty)


# ---------------------------------------------------------------------------
# Heatmap
# ---------------------------------------------------------------------------


def generate_heatmap(
    population: list[Chromosome],
    starting_board: list[int],
    grid_size: int,
    top_fraction: float,
) -> list[float]:
    n = grid_size
    length = n * n
    result = [0.0] * length
    if not population:
        return result

    with_fitness = sorted(
        [(calculate_fitness(c, starting_board, grid_size), i) for i, c in enumerate(population)],
        key=lambda x: -x[0],
    )
    top_count = max(1, int(len(population) * top_fraction))
    top_count = min(top_count, len(population))
    top_indices = [idx for _, idx in with_fitness[:top_count]]

    for cell_idx in range(length):
        if starting_board[cell_idx] != 0:
            continue
        counts: dict[int, int] = {}
        for idx in top_indices:
            grid = reconstruct_grid(starting_board, population[idx], grid_size)
            v = grid[cell_idx]
            counts[v] = counts.get(v, 0) + 1
        max_count = max(counts.values()) if counts else 0
        result[cell_idx] = max_count / top_count if top_count > 0 else 0.0
    return result


# ---------------------------------------------------------------------------
# Mutation types (13 operators)
# ---------------------------------------------------------------------------


class MutationType(enum.Enum):
    SWAP = "swap"
    SCRAMBLE = "scramble"
    INVERSION = "inversion"
    INORDER = "inorder"
    CENTER_INVERSION = "center_inversion"
    THROAS = "throas"
    THRORS = "thrors"
    DISTANCE_BASED = "distance_based"
    DISPLACEMENT = "displacement"
    INSERTION = "insertion"
    DISPLACED_INVERSION = "displaced_inversion"
    ADJACENT_SWAP = "adjacent_swap"
    UNIFORM_RANDOM = "uniform_random"


ALL_MUTATION_TYPES = list(MutationType)


def _random_mutation_type(rng: random.Random) -> MutationType:
    return rng.choice(ALL_MUTATION_TYPES)


def _mut_swap(row: list[int], rng: random.Random, n: int) -> None:
    i, j = rng.randrange(n), rng.randrange(n)
    while j == i and n > 1:
        j = rng.randrange(n)
    row[i], row[j] = row[j], row[i]


def _mut_scramble(row: list[int], rng: random.Random, n: int) -> None:
    a = rng.randrange(n - 1)
    b = rng.randint(a + 1, n)
    sub = row[a:b]
    rng.shuffle(sub)
    row[a:b] = sub


def _mut_inversion(row: list[int], rng: random.Random, n: int) -> None:
    a = rng.randrange(n - 1)
    b = rng.randint(a + 1, n)
    row[a:b] = row[a:b][::-1]


def _mut_inorder(row: list[int], rng: random.Random, n: int) -> None:
    for i in range(n):
        if rng.random() < 0.5:
            j = rng.randrange(n)
            while j == i and n > 1:
                j = rng.randrange(n)
            row[i], row[j] = row[j], row[i]


def _mut_center_inversion(row: list[int], rng: random.Random, n: int) -> None:
    mid = n // 2
    if n % 2 == 0:
        row[:mid], row[mid:] = row[:mid][::-1], row[mid:][::-1]
    elif mid > 0:
        row[:mid], row[mid + 1 :] = row[:mid][::-1], row[mid + 1 :][::-1]


def _mut_throas(row: list[int], rng: random.Random, n: int) -> None:
    if n >= 3:
        i = rng.randint(0, n - 3)
        row[i], row[i + 1], row[i + 2] = row[i + 2], row[i], row[i + 1]


def _mut_thrors(row: list[int], rng: random.Random, n: int) -> None:
    if n >= 3:
        i, j = rng.randrange(n), rng.randrange(n)
        while j == i:
            j = rng.randrange(n)
        k = rng.randrange(n)
        while k in (i, j):
            k = rng.randrange(n)
        row[i], row[j], row[k] = row[k], row[i], row[j]


def _mut_distance_based(row: list[int], rng: random.Random, n: int) -> None:
    g = rng.randrange(n)
    d = rng.randint(1, n - 1)
    start, end = max(0, g - d), min(n, g + d + 1)
    if start + 1 < end:
        sub = row[start:end]
        rng.shuffle(sub)
        row[start:end] = sub


def _mut_displacement(row: list[int], rng: random.Random, n: int) -> None:
    a = rng.randrange(n - 1)
    b = rng.randint(a + 1, n)
    seg = row[a:b]
    new_row = row[:a] + row[b:]
    p = rng.randint(0, len(new_row))
    new_row[p:p] = seg
    row[:] = new_row[:n]


def _mut_insertion(row: list[int], rng: random.Random, n: int) -> None:
    i, j = rng.randrange(n), rng.randrange(n)
    while j == i and n > 1:
        j = rng.randrange(n)
    v = row.pop(i)
    if j > i:
        j -= 1
    row.insert(j, v)


def _mut_displaced_inversion(row: list[int], rng: random.Random, n: int) -> None:
    a = rng.randrange(n - 1)
    b = rng.randint(a + 1, n)
    seg = row[a:b][::-1]
    new_row = row[:a] + row[b:]
    p = rng.randint(0, len(new_row))
    new_row[p:p] = seg
    row[:] = new_row[:n]


def _mut_adjacent_swap(row: list[int], rng: random.Random, n: int) -> None:
    i = rng.randrange(n - 1)
    row[i], row[i + 1] = row[i + 1], row[i]


def _mut_uniform_random(row: list[int], rng: random.Random, n: int) -> None:
    rng.shuffle(row)


_MUTATION_DISPATCH = {
    MutationType.SWAP: _mut_swap,
    MutationType.SCRAMBLE: _mut_scramble,
    MutationType.INVERSION: _mut_inversion,
    MutationType.INORDER: _mut_inorder,
    MutationType.CENTER_INVERSION: _mut_center_inversion,
    MutationType.THROAS: _mut_throas,
    MutationType.THRORS: _mut_thrors,
    MutationType.DISTANCE_BASED: _mut_distance_based,
    MutationType.DISPLACEMENT: _mut_displacement,
    MutationType.INSERTION: _mut_insertion,
    MutationType.DISPLACED_INVERSION: _mut_displaced_inversion,
    MutationType.ADJACENT_SWAP: _mut_adjacent_swap,
    MutationType.UNIFORM_RANDOM: _mut_uniform_random,
}


def apply_mutation(row: list[int], mutation: MutationType, rng: random.Random) -> None:
    """Apply a single mutation in-place to *row*."""
    n = len(row)
    if n >= 2:
        _MUTATION_DISPATCH[mutation](row, rng, n)


# ---------------------------------------------------------------------------
# Crossover & mutation entry points
# ---------------------------------------------------------------------------


def crossover(
    a: Chromosome,
    b: Chromosome,
    rng: random.Random,
) -> Chromosome:
    """Uniform row-level crossover."""
    rows = [
        list(ra) if rng.random() < 0.5 else list(rb) for ra, rb in zip(a.rows, b.rows, strict=True)
    ]
    return Chromosome(rows=rows)


def mutate(chromosome: Chromosome, rate: float, rng: random.Random) -> None:
    """Randomly mutate one row of the chromosome at the given rate."""
    if rng.random() >= rate:
        return
    n = len(chromosome.rows)
    if n == 0:
        return
    row_idx = rng.randrange(n)
    mt = _random_mutation_type(rng)
    apply_mutation(chromosome.rows[row_idx], mt, rng)
