"""Pydantic schemas for SastaDice game models."""
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional
import uuid


class GameStatus(str, Enum):
    """Game session status."""

    LOBBY = "LOBBY"
    ACTIVE = "ACTIVE"
    FINISHED = "FINISHED"


class TileType(str, Enum):
    """Tile type enumeration."""

    PROPERTY = "PROPERTY"
    TAX = "TAX"
    CHANCE = "CHANCE"
    TRAP = "TRAP"
    BUFF = "BUFF"
    NEUTRAL = "NEUTRAL"  # Padding tile


class TileCreate(BaseModel):
    """Schema for creating a tile."""

    type: TileType
    name: str
    effect_config: dict = Field(default_factory=dict)


class Tile(TileCreate):
    """Schema for a game tile."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    owner_id: Optional[str] = None
    position: int = 0
    x: int = 0
    y: int = 0


class PlayerCreate(BaseModel):
    """Schema for creating a player."""

    name: str


class Player(PlayerCreate):
    """Schema for a game player."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    cash: int = 1500
    position: int = 0
    submitted_tiles: list[TileCreate] = Field(default_factory=list)


class GameSession(BaseModel):
    """Schema for a game session."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: GameStatus = GameStatus.LOBBY
    current_turn_player_id: Optional[str] = None
    players: list[Player] = Field(default_factory=list)
    board: list[Tile] = Field(default_factory=list)
    board_size: int = 0


class GameStateResponse(BaseModel):
    """Optimized response for polling - includes version for diffing."""

    version: int
    game: GameSession


class DiceRollResult(BaseModel):
    """Result of a dice roll."""

    dice1: int
    dice2: int
    total: int
    is_doubles: bool


class JoinGameRequest(BaseModel):
    """Request schema for joining a game."""

    name: str
    tiles: list[TileCreate] = Field(min_length=5, max_length=5)


class ActionType(str, Enum):
    """Game action types."""

    ROLL_DICE = "ROLL_DICE"
    BUY_PROPERTY = "BUY_PROPERTY"
    END_TURN = "END_TURN"


class GameActionRequest(BaseModel):
    """Request schema for game actions."""

    type: ActionType
    payload: dict = Field(default_factory=dict)


class ActionResult(BaseModel):
    """Result of a game action."""

    success: bool
    message: str
    data: Optional[dict] = None
