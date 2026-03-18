"""Request / response schemas for Sudoku endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.modules.sudoku.models import Difficulty, MatchStatus


class StartMatchRequest(BaseModel):
    difficulty: Difficulty = Difficulty.MEDIUM
    grid_size: int = Field(default=9, ge=4, le=16)
    custom_board: list[int] | None = None


class StartMatchResponse(BaseModel):
    match_id: str
    starting_board: list[int]
    grid_size: int


class ExtractBoardResponse(BaseModel):
    board: list[int] = Field(min_length=81, max_length=81)
    confidences: list[float] = Field(min_length=81, max_length=81)


class PlayerUpdateRequest(BaseModel):
    board: list[int]


class ClaimVictoryResponse(BaseModel):
    valid: bool
    status: MatchStatus


class AiStateResponse(BaseModel):
    generation_count: int
    fitness_score: float
    heatmap_data: list[float]
    best_board: list[int]
    status: MatchStatus


class MatchStateResponse(BaseModel):
    match_id: str
    difficulty: Difficulty
    status: MatchStatus
    starting_board: list[int]
    grid_size: int
    player_board: list[int]
    ai: AiStateResponse


class SolveResponse(BaseModel):
    match_id: str
    status: str
