"""REST endpoints for the Sudoku solver module."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.session import get_db
from app.modules.sudoku.schemas import (
    ClaimVictoryResponse,
    MatchStateResponse,
    PlayerUpdateRequest,
    StartMatchRequest,
    StartMatchResponse,
)
from app.modules.sudoku.services import SudokuService

router = APIRouter()


async def _get_service(db: AsyncIOMotorDatabase[Any] = Depends(get_db)) -> SudokuService:
    return SudokuService(db)


@router.post("/matches", response_model=StartMatchResponse, status_code=status.HTTP_201_CREATED)
async def start_match(
    request: StartMatchRequest,
    service: SudokuService = Depends(_get_service),
) -> StartMatchResponse:
    result = await service.start_match(request.difficulty, request.grid_size)
    return StartMatchResponse(**result)


@router.get("/matches/{match_id}", response_model=MatchStateResponse)
async def get_match(
    match_id: str,
    service: SudokuService = Depends(_get_service),
) -> MatchStateResponse:
    try:
        data = await service.get_match(match_id)
        return MatchStateResponse(**data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/matches/{match_id}/board")
async def update_board(
    match_id: str,
    request: PlayerUpdateRequest,
    service: SudokuService = Depends(_get_service),
) -> dict[str, str]:
    try:
        await service.player_update_board(match_id, request.board)
        return {"status": "ok"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/matches/{match_id}/claim-victory", response_model=ClaimVictoryResponse)
async def claim_victory(
    match_id: str,
    service: SudokuService = Depends(_get_service),
) -> ClaimVictoryResponse:
    try:
        data = await service.claim_victory(match_id)
        return ClaimVictoryResponse(**data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/matches/{match_id}/ai-tick")
async def ai_tick(
    match_id: str,
    service: SudokuService = Depends(_get_service),
) -> dict[str, Any]:
    try:
        return await service.ai_tick(match_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
