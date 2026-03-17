"""Unit tests for app.modules.sudoku.genetic — ported from spacetimedb/src/genetic.rs tests."""

from __future__ import annotations

import random

from app.modules.sudoku.genetic import (
    ALL_MUTATION_TYPES,
    Chromosome,
    apply_mutation,
    calculate_fitness,
    chromosome_hash,
    crossover,
    generate_heatmap,
    generate_initial_population,
    generate_puzzle,
    is_valid_solution,
    mutate,
    reconstruct_grid,
    solve_sudoku,
)


def _rng(seed: int = 42) -> random.Random:
    return random.Random(seed)


# ------------------------------------------------------------------
# Chromosome basics
# ------------------------------------------------------------------


class TestChromosomeBasics:
    def test_from_missing_rows(self) -> None:
        rows = [[1, 2], [3]]
        c = Chromosome.from_missing_rows(rows)
        assert c.rows == rows


# ------------------------------------------------------------------
# Fitness
# ------------------------------------------------------------------


class TestFitness:
    def test_perfect_9x9_is_one(self) -> None:
        starting_board = [0] * 81
        rows = [[(r * 3 + r // 3 + c) % 9 + 1 for c in range(9)] for r in range(9)]
        chrom = Chromosome(rows=rows)
        f = calculate_fitness(chrom, starting_board, 9)
        assert abs(f - 1.0) < 1e-5, f"expected 1.0 got {f}"

    def test_imperfect_is_less_than_one(self) -> None:
        starting_board = [0] * 81
        rows = [[(r + c) % 9 + 1 for c in range(9)] for r in range(9)]
        rows[0][0] = 2
        rows[0][1] = 2
        chrom = Chromosome(rows=rows)
        f = calculate_fitness(chrom, starting_board, 9)
        assert 0.0 <= f < 1.0


# ------------------------------------------------------------------
# is_valid_solution
# ------------------------------------------------------------------

SOLVED_9X9 = [
    5,
    3,
    4,
    6,
    7,
    8,
    9,
    1,
    2,
    6,
    7,
    2,
    1,
    9,
    5,
    3,
    4,
    8,
    1,
    9,
    8,
    3,
    4,
    2,
    5,
    6,
    7,
    8,
    5,
    9,
    7,
    6,
    1,
    4,
    2,
    3,
    4,
    2,
    6,
    8,
    5,
    3,
    7,
    9,
    1,
    7,
    1,
    3,
    9,
    2,
    4,
    8,
    5,
    6,
    9,
    6,
    1,
    5,
    3,
    7,
    2,
    8,
    4,
    2,
    8,
    7,
    4,
    1,
    9,
    6,
    3,
    5,
    3,
    4,
    5,
    2,
    8,
    6,
    1,
    7,
    9,
]


class TestIsValidSolution:
    def test_valid_9x9(self) -> None:
        assert is_valid_solution(list(SOLVED_9X9), 9) is True

    def test_wrong_length(self) -> None:
        assert is_valid_solution([], 9) is False
        assert is_valid_solution([1] * 80, 9) is False
        assert is_valid_solution([1] * 100, 9) is False

    def test_duplicate_in_row(self) -> None:
        board = [0] * 81
        board[0] = 1
        board[1] = 1
        assert is_valid_solution(board, 9) is False

    def test_zero_in_board(self) -> None:
        board = [
            ((r // 3) * 3 + (c // 3) + (r % 3) * 3 + (c % 3)) % 9 + 1
            for r in range(9)
            for c in range(9)
        ]
        board[0] = 0
        assert is_valid_solution(board, 9) is False


# ------------------------------------------------------------------
# solve_sudoku
# ------------------------------------------------------------------


class TestSolveSudoku:
    def test_fills_valid_solution(self) -> None:
        solved = list(SOLVED_9X9)
        puzzle = list(solved)
        for idx in [0, 4, 10, 20, 40, 60, 80]:
            puzzle[idx] = 0
        ok = solve_sudoku(puzzle, 9)
        assert ok
        assert puzzle == solved


# ------------------------------------------------------------------
# reconstruct_grid
# ------------------------------------------------------------------


class TestReconstructGrid:
    def test_matches_chromosome(self) -> None:
        start = [1, 0, 0, 0, 2, 0, 0, 0, 3]
        chrom = Chromosome(rows=[[4, 5], [7, 8], [2, 3]])
        grid = reconstruct_grid(start, chrom, 3)
        assert grid[0] == 1
        assert grid[1] == 4
        assert grid[2] == 5
        assert grid[3] == 7
        assert grid[4] == 2
        assert grid[5] == 8
        assert grid[6] == 2
        assert grid[7] == 3
        assert grid[8] == 3


# ------------------------------------------------------------------
# generate_initial_population
# ------------------------------------------------------------------


class TestGenerateInitialPopulation:
    def test_size(self) -> None:
        rng = _rng()
        start = [0] * 81
        pop = generate_initial_population(start, 9, 20, rng)
        assert len(pop) == 20
        assert len(pop[0].rows) == 9


# ------------------------------------------------------------------
# chromosome_hash / dedup
# ------------------------------------------------------------------


class TestChromosomeHash:
    def test_deterministic(self) -> None:
        c = Chromosome(rows=[[1, 2, 3], [4, 5], [6, 7, 8, 9]])
        assert chromosome_hash(c) == chromosome_hash(c)

    def test_different_chromosome_different_hash(self) -> None:
        c = Chromosome(rows=[[1, 2, 3], [4, 5], [6, 7, 8, 9]])
        c2 = Chromosome(rows=[[1, 2, 4], [4, 5], [6, 7, 8, 9]])
        assert chromosome_hash(c) != chromosome_hash(c2)

    def test_dedup_initial_population(self) -> None:
        rng = _rng()
        start = [0] * 81
        pop = generate_initial_population(start, 9, 50, rng)
        hashes = {chromosome_hash(c) for c in pop}
        assert len(hashes) == len(pop)


# ------------------------------------------------------------------
# generate_puzzle
# ------------------------------------------------------------------


class TestGeneratePuzzle:
    def test_9x9_shape_and_holes(self) -> None:
        rng = _rng()
        grid = generate_puzzle(9, rng)
        assert len(grid) == 81
        zeros = sum(1 for v in grid if v == 0)
        assert 30 < zeros < 60, f"expected ~45% zeros, got {zeros}"

    def test_4x4_shape_and_holes(self) -> None:
        rng = _rng()
        grid = generate_puzzle(4, rng)
        assert len(grid) == 16
        zeros = sum(1 for v in grid if v == 0)
        assert 0 < zeros < 16

    def test_16x16_shape_and_holes(self) -> None:
        rng = _rng()
        grid = generate_puzzle(16, rng)
        assert len(grid) == 256
        zeros = sum(1 for v in grid if v == 0)
        assert 0 < zeros < 256

    def test_unsupported_size_returns_zeros(self) -> None:
        rng = _rng()
        grid = generate_puzzle(5, rng)
        assert len(grid) == 25
        assert all(v == 0 for v in grid)


# ------------------------------------------------------------------
# crossover
# ------------------------------------------------------------------


class TestCrossover:
    def test_produces_chromosome(self) -> None:
        rng = _rng()
        a = Chromosome(rows=[[1, 2], [3, 4]])
        b = Chromosome(rows=[[5, 6], [7, 8]])
        c = crossover(a, b, rng)
        assert len(c.rows) == 2
        assert len(c.rows[0]) == 2


# ------------------------------------------------------------------
# mutate
# ------------------------------------------------------------------


class TestMutate:
    def test_swap_changes_row(self) -> None:
        rng = _rng()
        chrom = Chromosome(rows=[[1, 2, 3]])
        mutate(chrom, 1.0, rng)
        assert len(chrom.rows[0]) == 3

    def test_zero_rate_does_nothing(self) -> None:
        rng = _rng()
        chrom = Chromosome(rows=[[1, 2, 3]])
        before = list(chrom.rows[0])
        mutate(chrom, 0.0, rng)
        assert chrom.rows[0] == before


# ------------------------------------------------------------------
# heatmap
# ------------------------------------------------------------------


class TestHeatmap:
    def test_empty_population(self) -> None:
        start = [0] * 9
        heat = generate_heatmap([], start, 3, 0.1)
        assert len(heat) == 9
        assert all(v == 0.0 for v in heat)

    def test_with_population(self) -> None:
        rng = _rng()
        start = [0] * 81
        pop = generate_initial_population(start, 9, 5, rng)
        heat = generate_heatmap(pop, start, 9, 0.5)
        assert len(heat) == 81
        assert all(0.0 <= v <= 1.0 for v in heat)


# ------------------------------------------------------------------
# all mutation types — permutation preservation
# ------------------------------------------------------------------


class TestAllMutations:
    def test_preserve_permutation(self) -> None:
        rng = _rng()
        chrom = Chromosome(rows=[[1, 2, 3, 4, 5], [6, 7, 8, 9]])
        original_lens = [len(r) for r in chrom.rows]
        original_sets = [set(r) for r in chrom.rows]

        for mt in ALL_MUTATION_TYPES:
            local = Chromosome(rows=[list(r) for r in chrom.rows])
            for row in local.rows:
                apply_mutation(row, mt, rng)
            for row, orig_len in zip(local.rows, original_lens, strict=True):
                assert len(row) == orig_len, f"mutation {mt} changed row length"
            for row, orig_set in zip(local.rows, original_sets, strict=True):
                assert set(row) == orig_set, f"mutation {mt} changed multiset"
