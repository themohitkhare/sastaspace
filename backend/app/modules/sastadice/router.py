"""API router for SastaDice game endpoints."""

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query, status

if TYPE_CHECKING:
    pass

from app.db.session import get_db
from app.modules.sastadice.schemas import (
    ActionResult,
    GameActionRequest,
    GameSession,
    GameStateResponse,
    JoinGameRequest,
    Player,
)
from app.modules.sastadice.services.game_orchestrator import GameOrchestrator

# Backward compatibility alias
GameService = GameOrchestrator

router = APIRouter()


async def get_game_service(db=Depends(get_db)) -> GameService:
    """Dependency to get game service."""
    return GameService(db)


@router.post("/games", response_model=GameSession, status_code=status.HTTP_201_CREATED)
async def create_game(
    cpu_count: int = Query(default=0, ge=0, le=4, description="Number of CPU players to add"),
    service: GameService = Depends(get_game_service),
) -> GameSession:
    """Create a new game room with optional CPU players."""
    return await service.create_game(cpu_count=cpu_count)


@router.get("/games/{game_id}", response_model=GameSession)
async def get_game(game_id: str, service: GameService = Depends(get_game_service)) -> GameSession:
    """Get game state by ID."""
    try:
        return await service.get_game(game_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/games/{game_id}/state", response_model=GameStateResponse)
async def get_game_state(
    game_id: str,
    version: int | None = None,
    service: GameService = Depends(get_game_service),
) -> GameStateResponse:
    """Get game state with version for polling optimization."""
    try:
        await service.check_timeout(game_id)

        game = await service.get_game(game_id)
        current_version = await service.repository.get_version(game_id)

        if version is not None and version >= current_version:
            raise HTTPException(status_code=status.HTTP_304_NOT_MODIFIED, detail="No changes")

        return GameStateResponse(version=current_version, game=game)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/games/{game_id}/join", response_model=Player, status_code=status.HTTP_201_CREATED)
async def join_game(
    game_id: str,
    request: JoinGameRequest,
    service: GameService = Depends(get_game_service),
) -> Player:
    """Join a game and submit 5 custom tiles."""
    try:
        return await service.join_game(game_id, request.name, request.tiles)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/games/{game_id}/ready/{player_id}")
async def toggle_ready(
    game_id: str,
    player_id: str,
    service: GameService = Depends(get_game_service),
) -> dict:
    """Toggle player's launch key (ready status). Auto-starts if all ready."""
    try:
        return await service.toggle_ready(game_id, player_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/games/{game_id}/players/{player_id}")
async def kick_player(
    game_id: str,
    player_id: str,
    host_id: str = Query(..., description="Host player ID"),
    service: GameService = Depends(get_game_service),
) -> dict:
    """Kick a player from the lobby. Only host can kick."""
    try:
        return await service.kick_player(game_id, host_id, player_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/games/{game_id}/settings")
async def update_settings(
    game_id: str,
    request: dict,
    service: GameService = Depends(get_game_service),
) -> dict:
    """Update game settings. Only host can update."""
    try:
        host_id = request.get("host_id")
        if not host_id or not isinstance(host_id, str):
            raise ValueError("host_id is required and must be a string")
        settings = request.get("settings", {})
        return await service.update_settings(game_id, host_id, settings)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/games/{game_id}/start", response_model=GameSession)
async def start_game(game_id: str, service: GameService = Depends(get_game_service)) -> GameSession:
    """Force start game (bypasses ready check - for testing)."""
    try:
        return await service.start_game(game_id, force=True)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/games/{game_id}/action", response_model=ActionResult)
async def perform_action(
    game_id: str,
    action: GameActionRequest,
    player_id: str = Query(..., description="Player ID performing the action"),
    service: GameService = Depends(get_game_service),
) -> ActionResult:
    """Perform a game action (roll dice, buy property, end turn)."""
    try:
        await service.check_timeout(game_id)

        return await service.perform_action(game_id, player_id, action.type, action.payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/games/{game_id}/simulate")
async def simulate_game(
    game_id: str,
    max_turns: int = Query(default=100, ge=1, le=500, description="Maximum turns to simulate"),
    service: GameService = Depends(get_game_service),
) -> dict:
    """Simulate CPU turns until game ends or max_turns reached. For testing."""
    try:
        return await service.simulate_cpu_game(game_id, max_turns)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/games/{game_id}/cpu-turn")
async def process_cpu_turns(
    game_id: str,
    service: GameService = Depends(get_game_service),
) -> dict:
    """Process CPU turns until it's a human player's turn."""
    try:
        return await service.process_cpu_turns(game_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
