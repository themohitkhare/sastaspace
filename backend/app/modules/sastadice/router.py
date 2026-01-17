"""API router for SastaDice game endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import duckdb

from app.db.session import get_db
from app.modules.sastadice.services.game_service import GameService
from app.modules.sastadice.schemas import (
    GameSession,
    GameStateResponse,
    JoinGameRequest,
    Player,
    GameActionRequest,
    ActionResult,
    DiceRollResult,
)

router = APIRouter()


def get_game_service(db = Depends(get_db)) -> GameService:  # type: ignore
    """Dependency to get game service."""
    return GameService(db)


@router.post("/games", response_model=GameSession, status_code=status.HTTP_201_CREATED)
def create_game(service: GameService = Depends(get_game_service)) -> GameSession:
    """Create a new game room."""
    return service.create_game()


@router.get("/games/{game_id}", response_model=GameSession)
def get_game(game_id: str, service: GameService = Depends(get_game_service)) -> GameSession:
    """Get game state by ID."""
    try:
        return service.get_game(game_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/games/{game_id}/state", response_model=GameStateResponse)
def get_game_state(
    game_id: str,
    version: Optional[int] = None,
    service: GameService = Depends(get_game_service),
) -> GameStateResponse:
    """Get game state with version for polling optimization."""
    try:
        game = service.get_game(game_id)
        current_version = service.repository.get_version(game_id)

        # If client version matches, return 304 (handled by FastAPI)
        if version is not None and version >= current_version:
            raise HTTPException(
                status_code=status.HTTP_304_NOT_MODIFIED, detail="No changes"
            )

        return GameStateResponse(version=current_version, game=game)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/games/{game_id}/join", response_model=Player, status_code=status.HTTP_201_CREATED)
def join_game(
    game_id: str,
    request: JoinGameRequest,
    service: GameService = Depends(get_game_service),
) -> Player:
    """Join a game and submit 5 custom tiles."""
    try:
        return service.join_game(game_id, request.name, request.tiles)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )


@router.post("/games/{game_id}/start", response_model=GameSession)
def start_game(
    game_id: str, service: GameService = Depends(get_game_service)
) -> GameSession:
    """Start a game (host only - anyone can start for now)."""
    try:
        return service.start_game(game_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )


@router.post("/games/{game_id}/action", response_model=ActionResult)
def perform_action(
    game_id: str,
    action: GameActionRequest,
    player_id: str = Query(..., description="Player ID performing the action"),  # In production, get from auth token
    service: GameService = Depends(get_game_service),
) -> ActionResult:
    """Perform a game action (roll dice, buy property, end turn)."""
    try:
        return service.perform_action(
            game_id, player_id, action.type, action.payload
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
