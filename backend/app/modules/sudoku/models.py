"""Pydantic models for Sudoku module — MongoDB documents."""

from __future__ import annotations

import enum

from pydantic import BaseModel, Field


class Difficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class MatchStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    SOLVED = "solved"
    # Legacy aliases kept for backward compatibility with existing DB documents
    PLAYER_WON = "player_won"
    AI_WON = "ai_won"


class GameMatch(BaseModel):
    """Persisted match document."""

    match_id: str
    difficulty: Difficulty = Difficulty.MEDIUM
    status: MatchStatus = MatchStatus.IN_PROGRESS
    starting_board: list[int] = Field(default_factory=list)
    grid_size: int = 9
    player_board: list[int] = Field(default_factory=list)


class AiState(BaseModel):
    """GA solver evolution state stored alongside the match."""

    match_id: str
    generation_count: int = 0
    stall_count: int = 0
    fitness_score: float = 0.0
    heatmap_data: list[float] = Field(default_factory=list)
    best_board: list[int] = Field(default_factory=list)
