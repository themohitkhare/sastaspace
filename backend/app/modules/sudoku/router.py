"""REST endpoints for the Sudoku solver module."""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.redis import get_redis
from app.db.session import get_db
from app.modules.sudoku.models import MatchStatus
from app.modules.sudoku.ocr_utils import extract_sudoku_board
from app.modules.sudoku.repository import SudokuRepository
from app.modules.sudoku.schemas import (
    ClaimVictoryResponse,
    ExtractBoardResponse,
    MatchStateResponse,
    PlayerUpdateRequest,
    SolveResponse,
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
    result = await service.start_match(request.difficulty, request.grid_size, request.custom_board)
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


@router.post(
    "/matches/{match_id}/solve", response_model=SolveResponse, status_code=status.HTTP_202_ACCEPTED
)
async def solve_match(
    match_id: str,
    db: AsyncIOMotorDatabase[Any] = Depends(get_db),
    r: aioredis.Redis = Depends(get_redis),
) -> SolveResponse:
    """Queue a match for distributed GA solving via Redis Streams."""
    repo = SudokuRepository(db)
    match_doc = await repo.get_match(match_id)
    if not match_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    if match_doc["status"] != MatchStatus.IN_PROGRESS.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Match not in progress")

    await r.xadd("sudoku:solve-requests", {"payload": json.dumps({"match_id": match_id})})
    return SolveResponse(match_id=match_id, status="queued")


@router.post("/extract-board", response_model=ExtractBoardResponse)
async def extract_board(file: UploadFile = File(...)) -> ExtractBoardResponse:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be an image")
    try:
        content = await file.read()
        board, confidences = extract_sudoku_board(content)
        confidences = [min(1.0, max(0.0, float(c))) for c in confidences]
        return ExtractBoardResponse(board=board, confidences=confidences)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"OCR failed: {str(e)}")
