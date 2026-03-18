"""Pydantic schemas for SastaDice game models."""

import random
import uuid
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


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
    NODE = "NODE"  # Server Node (railroad equivalent)
    GO_TO_JAIL = "GO_TO_JAIL"  # 404: Access Denied


class WinCondition(str, Enum):
    """Game win condition modes."""

    SUDDEN_DEATH = "SUDDEN_DEATH"
    LAST_STANDING = "LAST_STANDING"
    FIRST_TO_CASH = "FIRST_TO_CASH"


class ChaosLevel(str, Enum):
    """Event chaos intensity."""

    CHILL = "CHILL"
    NORMAL = "NORMAL"
    CHAOS = "CHAOS"


class BoardPreset(str, Enum):
    """Predefined board generation modes."""

    CLASSIC = "CLASSIC"
    UGC_24 = "UGC_24"


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

    doubles_give_extra_turn: bool = True
    triple_doubles_jail: bool = True

    income_tax_rate: float = 0.1  # 10% default
    board_preset: BoardPreset = BoardPreset.CLASSIC


class FaultInjectionConfig(BaseModel):
    """Infrastructure fault simulation for resilience testing."""

    drop_db_writes: float = 0.0  # 0-1: Probability of simulating DB write failure
    delay_responses_ms: int = 0  # Milliseconds to delay all responses
    corrupt_state_prob: float = 0.0  # Probability of injecting invalid state
    network_partition: bool = False  # Simulate network partition mid-action


class ChaosConfig(BaseModel):
    """Configuration for chaos testing with reproducible randomness."""

    seed: int = Field(default_factory=lambda: random.randint(0, 2**32))
    chaos_probability: float = 0.3  # 30% chance of "stupid" moves
    enable_invalid_actions: bool = False  # Try invalid actions (expect failures)
    enable_race_conditions: bool = False  # Zero delays between actions
    fault_injection: FaultInjectionConfig = Field(default_factory=FaultInjectionConfig)


PROPERTY_COLORS = ["RED", "BLUE", "GREEN", "PURPLE", "ORANGE", "TEAL"]


class TileCreate(BaseModel):
    """Schema for creating a tile."""

    type: TileType
    name: str
    effect_config: dict[str, Any] = Field(default_factory=dict)


class Tile(TileCreate):
    """Schema for a game tile."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    owner_id: str | None = None
    position: int = 0
    x: int = 0
    y: int = 0
    price: int = 0
    rent: int = 0
    color: str | None = None
    upgrade_level: int = 0
    blocked_until_round: int | None = None
    free_landing_until_round: int | None = None


class PlayerCreate(BaseModel):
    """Schema for creating a player."""

    name: str


PLAYER_COLORS = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7"]


class Player(PlayerCreate):
    """Schema for a game player."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    cash: int = 0
    position: int = 0
    previous_position: int = 0
    color: str = "#888888"
    properties: list[str] = Field(default_factory=list)
    submitted_tiles: list[TileCreate] = Field(default_factory=list)
    ready: bool = False
    is_bankrupt: bool = False
    in_jail: bool = False
    jail_turns: int = 0
    consecutive_doubles: int = 0
    active_buff: str | None = None
    skip_next_move: bool = False
    double_rent_next_turn: bool = False
    disconnected: bool = False
    afk_turns: int = 0
    disconnected_turns: int = 0


class PendingDecision(BaseModel):
    """Pending decision for current player."""

    type: str
    tile_id: str | None = None
    price: int = 0
    event_data: dict[str, Any] | None = None


class GameSession(BaseModel):
    """Schema for a game session."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: GameStatus = GameStatus.LOBBY
    turn_phase: TurnPhase = TurnPhase.PRE_ROLL
    current_turn_player_id: str | None = None
    host_id: str | None = None
    players: list[Player] = Field(default_factory=list)
    board: list[Tile] = Field(default_factory=list)
    board_size: int = 0
    starting_cash: int = 0
    go_bonus: int = 0
    last_dice_roll: dict[str, Any] | None = None
    pending_decision: PendingDecision | None = None
    last_event_message: str | None = None
    current_round: int = 0
    max_rounds: int = 30
    first_player_id: str | None = None
    auction_state: Optional["AuctionState"] = None
    rent_multiplier: float = 1.0
    go_bonus_multiplier: float = 1.0
    blocked_tiles: list[str] = Field(default_factory=list)
    settings: GameSettings = Field(default_factory=GameSettings)
    event_deck: list[int] = Field(default_factory=list)
    used_event_deck: list[int] = Field(default_factory=list)
    turn_start_time: float = 0.0
    active_trade_offers: list["TradeOffer"] = Field(default_factory=list)
    winner_id: str | None = None
    bankruptcy_auction_queue: list[str] = Field(default_factory=list)


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
    tiles: list[TileCreate] | None = None


class ActionType(str, Enum):
    """Game action types."""

    ROLL_DICE = "ROLL_DICE"
    BUY_PROPERTY = "BUY_PROPERTY"
    PASS_PROPERTY = "PASS_PROPERTY"
    END_TURN = "END_TURN"
    BID = "BID"
    RESOLVE_AUCTION = "RESOLVE_AUCTION"
    UPGRADE = "UPGRADE"
    DOWNGRADE = "DOWNGRADE"
    BUY_BUFF = "BUY_BUFF"
    PEEK_EVENTS = "PEEK_EVENTS"
    BLOCK_TILE = "BLOCK_TILE"
    PROPOSE_TRADE = "PROPOSE_TRADE"
    ACCEPT_TRADE = "ACCEPT_TRADE"
    DECLINE_TRADE = "DECLINE_TRADE"
    CANCEL_TRADE = "CANCEL_TRADE"
    BUY_RELEASE = "BUY_RELEASE"
    ROLL_FOR_DOUBLES = "ROLL_FOR_DOUBLES"
    EVENT_CLONE_UPGRADE = "EVENT_CLONE_UPGRADE"
    EVENT_FORCE_BUY = "EVENT_FORCE_BUY"
    EVENT_FREE_LANDING = "EVENT_FREE_LANDING"


class AuctionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ENDED = "ENDED"
    CANCELLED = "CANCELLED"


class AuctionState(BaseModel):
    """Current state of an active auction."""

    property_id: str
    highest_bid: int
    highest_bidder_id: str | None = None
    end_time: float
    participants: list[str] = Field(default_factory=list)
    status: AuctionStatus = AuctionStatus.ACTIVE
    min_bid_increment: int = 10
    start_time: float = 0.0


class TradeOffer(BaseModel):
    """Schema for a trade offer."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    initiator_id: str
    target_id: str
    offering_cash: int = 0
    offering_properties: list[str] = Field(default_factory=list)
    requesting_cash: int = 0
    requesting_properties: list[str] = Field(default_factory=list)
    created_at: float = 0.0


class SastaEvent(BaseModel):
    """Scripted game events with Indian flavor."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    effect_type: str
    effect_value: int = 0


class GameActionRequest(BaseModel):
    """Request schema for game actions."""

    type: ActionType
    payload: dict[str, Any] = Field(default_factory=dict)


class ActionResult(BaseModel):
    """Result of a game action."""

    success: bool
    message: str
    data: dict[str, Any] | None = None
