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


class TurnPhase(str, Enum):
    """Turn phase state machine."""

    PRE_ROLL = "PRE_ROLL"      # Waiting to roll dice
    MOVING = "MOVING"          # Animation/movement in progress
    DECISION = "DECISION"      # Buy/Pass/Event choice required
    POST_TURN = "POST_TURN"    # End turn available


class TileType(str, Enum):
    """Tile type enumeration."""

    PROPERTY = "PROPERTY"
    TAX = "TAX"
    CHANCE = "CHANCE"  # Sasta Events
    TRAP = "TRAP"
    BUFF = "BUFF"
    NEUTRAL = "NEUTRAL"  # Padding tile
    GO = "GO"  # Start tile


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
    price: int = 0  # Purchase price (calculated from economy)
    rent: int = 0   # Rent when landed on (calculated from economy)


class PlayerCreate(BaseModel):
    """Schema for creating a player."""

    name: str


# Player colors for visual distinction
PLAYER_COLORS = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7"]


class Player(PlayerCreate):
    """Schema for a game player."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    cash: int = 0
    position: int = 0
    color: str = "#888888"
    properties: list[str] = Field(default_factory=list)
    submitted_tiles: list[TileCreate] = Field(default_factory=list)
    ready: bool = False  # Launch key turned


class PendingDecision(BaseModel):
    """Pending decision for current player."""

    type: str  # "BUY", "EVENT"
    tile_id: Optional[str] = None
    price: int = 0
    event_data: Optional[dict] = None


class GameSession(BaseModel):
    """Schema for a game session."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: GameStatus = GameStatus.LOBBY
    turn_phase: TurnPhase = TurnPhase.PRE_ROLL
    current_turn_player_id: Optional[str] = None
    host_id: Optional[str] = None
    players: list[Player] = Field(default_factory=list)
    board: list[Tile] = Field(default_factory=list)
    board_size: int = 0
    # Dynamic economy
    starting_cash: int = 0
    go_bonus: int = 0
    # Turn state
    last_dice_roll: Optional[dict] = None  # {dice1, dice2, total, is_doubles}
    pending_decision: Optional[PendingDecision] = None
    last_event_message: Optional[str] = None  # For displaying Sasta Events


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
    tiles: Optional[list[TileCreate]] = None


class ActionType(str, Enum):
    """Game action types."""

    ROLL_DICE = "ROLL_DICE"
    BUY_PROPERTY = "BUY_PROPERTY"
    PASS_PROPERTY = "PASS_PROPERTY"  # Decline to buy
    END_TURN = "END_TURN"


class SastaEvent(BaseModel):
    """Scripted game events with Indian flavor."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    effect_type: str  # "CASH_GAIN", "CASH_LOSS", "SKIP_BUY", "COLLECT_FROM_ALL", etc.
    effect_value: int = 0


class GameActionRequest(BaseModel):
    """Request schema for game actions."""

    type: ActionType
    payload: dict = Field(default_factory=dict)


class ActionResult(BaseModel):
    """Result of a game action."""

    success: bool
    message: str
    data: Optional[dict] = None
