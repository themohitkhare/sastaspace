"""MongoDB document models for SastaDice."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from app.modules.sastadice.schemas import (
    GameSession,
    GameStatus,
    TurnPhase,
    Player,
    Tile,
    TileCreate,
    TileType,
    PendingDecision,
    GameSettings,
    AuctionState,
)


class GameSessionDocument(BaseModel):
    """MongoDB document model for game sessions."""
    
    id: str = Field(alias="_id")
    status: GameStatus
    turn_phase: TurnPhase
    current_turn_player_id: Optional[str] = None
    host_id: Optional[str] = None
    board_size: int = 0
    version: int = 0
    starting_cash: int = 0
    go_bonus: int = 0
    last_dice_roll: Optional[dict] = None
    pending_decision: Optional[dict] = None
    last_event_message: Optional[str] = None
    created_at: Optional[datetime] = None
    current_round: int = 0
    max_rounds: int = 30
    first_player_id: Optional[str] = None
    auction_state: Optional[dict] = None
    rent_multiplier: float = 1.0
    blocked_tiles: list[str] = Field(default_factory=list)
    settings: Optional[dict] = None
    turn_start_time: float = 0.0
    event_deck: list[int] = Field(default_factory=list)
    used_event_deck: list[int] = Field(default_factory=list)

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}

    def to_game_session(self, players: list[Player], board: list[Tile]) -> GameSession:
        """Convert document to GameSession schema."""
        pending_decision = None
        if self.pending_decision:
            pending_decision = PendingDecision(**self.pending_decision)
        
        settings = GameSettings(**(self.settings or {}))
        
        auction_state = None
        if self.auction_state:
            auction_state = AuctionState(**self.auction_state)
        
        return GameSession(
            id=self.id,
            status=self.status,
            turn_phase=self.turn_phase,
            current_turn_player_id=self.current_turn_player_id,
            host_id=self.host_id,
            players=players,
            board=board,
            board_size=self.board_size,
            starting_cash=self.starting_cash,
            go_bonus=self.go_bonus,
            last_dice_roll=self.last_dice_roll,
            pending_decision=pending_decision,
            last_event_message=self.last_event_message,
            current_round=self.current_round,
            max_rounds=self.max_rounds,
            first_player_id=self.first_player_id,
            auction_state=auction_state,
            rent_multiplier=self.rent_multiplier,
            blocked_tiles=self.blocked_tiles,
            settings=settings,
            turn_start_time=self.turn_start_time,
            event_deck=getattr(self, 'event_deck', []),
            used_event_deck=getattr(self, 'used_event_deck', []),
        )

    @classmethod
    def from_game_session(cls, game: GameSession) -> "GameSessionDocument":
        """Create document from GameSession schema."""
        pending_decision_dict = None
        if game.pending_decision:
            pending_decision_dict = game.pending_decision.model_dump()
        
        settings_dict = game.settings.model_dump() if game.settings else None
        
        auction_state_dict = None
        if game.auction_state:
            auction_state_dict = game.auction_state.model_dump()
        
        return cls(
            id=game.id,
            status=game.status,
            turn_phase=game.turn_phase,
            current_turn_player_id=game.current_turn_player_id,
            host_id=game.host_id,
            board_size=game.board_size,
            version=getattr(game, 'version', 0),
            starting_cash=game.starting_cash,
            go_bonus=game.go_bonus,
            last_dice_roll=game.last_dice_roll,
            pending_decision=pending_decision_dict,
            last_event_message=game.last_event_message,
            created_at=datetime.utcnow(),
            # Phase 1 fields
            current_round=game.current_round,
            max_rounds=game.max_rounds,
            first_player_id=game.first_player_id,
            auction_state=auction_state_dict,
            rent_multiplier=game.rent_multiplier,
            blocked_tiles=game.blocked_tiles,
            settings=settings_dict,
            turn_start_time=getattr(game, 'turn_start_time', 0.0),
            event_deck=getattr(game, 'event_deck', []),
            used_event_deck=getattr(game, 'used_event_deck', []),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for MongoDB operations."""
        return self.model_dump(by_alias=True, exclude_none=True)


class PlayerDocument(BaseModel):
    """MongoDB document model for players."""
    
    id: str = Field(alias="_id")
    game_id: str
    name: str
    cash: int = 0
    position: int = 0
    color: str = "#888888"
    properties: list[str] = Field(default_factory=list)
    ready: bool = False
    is_bankrupt: bool = False
    created_at: Optional[datetime] = None
    in_jail: bool = False
    jail_turns: int = 0
    consecutive_doubles: int = 0
    active_buff: Optional[str] = None

    model_config = {"populate_by_name": True}

    def to_player(self, submitted_tiles: list[TileCreate]) -> Player:
        """Convert document to Player schema."""
        return Player(
            id=self.id,
            name=self.name,
            cash=self.cash,
            position=self.position,
            color=self.color,
            properties=self.properties,
            submitted_tiles=submitted_tiles,
            ready=self.ready,
            is_bankrupt=self.is_bankrupt,
            in_jail=self.in_jail,
            jail_turns=self.jail_turns,
            consecutive_doubles=self.consecutive_doubles,
            active_buff=self.active_buff,
        )

    @classmethod
    def from_player(cls, player: Player, game_id: str) -> "PlayerDocument":
        """Create document from Player schema."""
        return cls(
            id=player.id,
            game_id=game_id,
            name=player.name,
            cash=player.cash,
            position=player.position,
            color=player.color,
            properties=player.properties,
            ready=player.ready,
            is_bankrupt=player.is_bankrupt,
            created_at=datetime.utcnow(),
            in_jail=player.in_jail,
            jail_turns=player.jail_turns,
            consecutive_doubles=player.consecutive_doubles,
            active_buff=player.active_buff,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for MongoDB operations."""
        return self.model_dump(by_alias=True, exclude_none=True)


class TileDocument(BaseModel):
    """MongoDB document model for board tiles."""
    
    id: str = Field(alias="_id")
    game_id: str
    owner_id: Optional[str] = None
    type: TileType
    name: str
    effect_config: dict = Field(default_factory=dict)
    position: int = 0
    x: int = 0
    y: int = 0
    price: int = 0
    rent: int = 0
    color: Optional[str] = None
    upgrade_level: int = 0
    blocked_until_round: Optional[int] = None

    model_config = {"populate_by_name": True}

    def to_tile(self) -> Tile:
        """Convert document to Tile schema."""
        return Tile(
            id=self.id,
            owner_id=self.owner_id,
            type=self.type,
            name=self.name,
            effect_config=self.effect_config,
            position=self.position,
            x=self.x,
            y=self.y,
            price=self.price,
            rent=self.rent,
            color=self.color,
            upgrade_level=self.upgrade_level,
            blocked_until_round=self.blocked_until_round,
        )

    @classmethod
    def from_tile(cls, tile: Tile, game_id: str) -> "TileDocument":
        """Create document from Tile schema."""
        return cls(
            id=tile.id,
            game_id=game_id,
            owner_id=tile.owner_id,
            type=tile.type,
            name=tile.name,
            effect_config=tile.effect_config,
            position=tile.position,
            x=tile.x,
            y=tile.y,
            price=tile.price,
            rent=tile.rent,
            color=tile.color,
            upgrade_level=tile.upgrade_level,
            blocked_until_round=tile.blocked_until_round,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for MongoDB operations."""
        data = self.model_dump(by_alias=True, exclude_none=True)
        data["type"] = self.type.value
        return data


class SubmittedTileDocument(BaseModel):
    """MongoDB document model for submitted tiles."""
    
    id: str = Field(alias="_id")
    game_id: str
    player_id: str
    type: TileType
    name: str
    effect_config: dict = Field(default_factory=dict)

    model_config = {"populate_by_name": True}

    def to_tile_create(self) -> TileCreate:
        """Convert document to TileCreate schema."""
        return TileCreate(
            type=self.type,
            name=self.name,
            effect_config=self.effect_config,
        )

    @classmethod
    def from_tile_create(cls, tile: TileCreate, game_id: str, player_id: str, tile_id: str) -> "SubmittedTileDocument":
        """Create document from TileCreate schema."""
        return cls(
            id=tile_id,
            game_id=game_id,
            player_id=player_id,
            type=tile.type,
            name=tile.name,
            effect_config=tile.effect_config,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for MongoDB operations."""
        data = self.model_dump(by_alias=True, exclude_none=True)
        data["type"] = self.type.value
        return data
