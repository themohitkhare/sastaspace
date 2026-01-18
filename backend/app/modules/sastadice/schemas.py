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

    PRE_ROLL = "PRE_ROLL"
    MOVING = "MOVING"
    DECISION = "DECISION"
    AUCTION = "AUCTION"
    POST_TURN = "POST_TURN"


class TileType(str, Enum):
    """Tile type enumeration."""

    PROPERTY = "PROPERTY"
    TAX = "TAX"
    CHANCE = "CHANCE"
    TRAP = "TRAP"
    BUFF = "BUFF"
    NEUTRAL = "NEUTRAL"
    GO = "GO"
    JAIL = "JAIL"
    TELEPORT = "TELEPORT"
    MARKET = "MARKET"


class WinCondition(str, Enum):
    """Game win condition modes."""
    SUDDEN_DEATH = "SUDDEN_DEATH"
    LAST_STANDING = "LAST_STANDING"
    FIRST_TO_CASH = "FIRST_TO_CASH"


class ChaosLevel(str, Enum):
    """Event chaos intensity."""
    CHILL = "CHILL"  # Fewer events, less dramatic
    NORMAL = "NORMAL"  # Balanced chaos
    CHAOS = "CHAOS"  # Maximum events, high variance


class GameSettings(BaseModel):
    """Customizable game settings that host can configure."""
    
    win_condition: WinCondition = WinCondition.SUDDEN_DEATH
    round_limit: int = 30
    target_cash: int = 10000
    
    starting_cash_multiplier: float = 1.0
    go_bonus_base: int = 200
    go_inflation_per_round: int = 20
    
    chaos_level: ChaosLevel = ChaosLevel.NORMAL
    enable_trading: bool = True
    enable_auctions: bool = True
    enable_upgrades: bool = True
    enable_stimulus: bool = True
    
    jail_turns_max: int = 1
    jail_bribe_cost: int = 50
    
    turn_timer_seconds: int = 30
    
    enable_black_market: bool = True
    
    # Special Modes
    doubles_give_extra_turn: bool = True
    triple_doubles_jail: bool = True


# Property color groups
PROPERTY_COLORS = ["RED", "BLUE", "GREEN", "PURPLE", "ORANGE", "TEAL"]


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
    price: int = 0
    rent: int = 0
    color: Optional[str] = None
    upgrade_level: int = 0


class PlayerCreate(BaseModel):
    """Schema for creating a player."""

    name: str


PLAYER_COLORS = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7"]


class Player(PlayerCreate):
    """Schema for a game player."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    cash: int = 0
    position: int = 0
    color: str = "#888888"
    properties: list[str] = Field(default_factory=list)
    submitted_tiles: list[TileCreate] = Field(default_factory=list)
    ready: bool = False
    is_bankrupt: bool = False
    in_jail: bool = False
    jail_turns: int = 0
    consecutive_doubles: int = 0
    active_buff: Optional[str] = None


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
    starting_cash: int = 0
    go_bonus: int = 0
    last_dice_roll: Optional[dict] = None
    pending_decision: Optional[PendingDecision] = None
    last_event_message: Optional[str] = None
    current_round: int = 0
    max_rounds: int = 30
    first_player_id: Optional[str] = None
    auction_state: Optional["AuctionState"] = None
    rent_multiplier: float = 1.0
    blocked_tiles: list[str] = Field(default_factory=list)
    settings: GameSettings = Field(default_factory=GameSettings)


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
    PASS_PROPERTY = "PASS_PROPERTY"  # Decline to buy -> triggers auction
    END_TURN = "END_TURN"
    BID = "BID"
    RESOLVE_AUCTION = "RESOLVE_AUCTION"
    UPGRADE = "UPGRADE"



class AuctionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ENDED = "ENDED"
    CANCELLED = "CANCELLED"


class AuctionState(BaseModel):
    """Current state of an active auction."""
    property_id: str
    highest_bid: int
    highest_bidder_id: Optional[str] = None
    end_time: float
    participants: list[str] = Field(default_factory=list)
    status: AuctionStatus = AuctionStatus.ACTIVE
    min_bid_increment: int = 10
    start_time: float = 0.0


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
