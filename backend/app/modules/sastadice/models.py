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
)


class GameSessionDocument(BaseModel):
    """MongoDB document model for game sessions."""
    
    _id: str = Field(alias="_id")
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

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True

    def to_game_session(self, players: list[Player], board: list[Tile]) -> GameSession:
        """Convert document to GameSession schema."""
        pending_decision = None
        if self.pending_decision:
            pending_decision = PendingDecision(**self.pending_decision)
        
        return GameSession(
            id=self._id,
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
        )

    @classmethod
    def from_game_session(cls, game: GameSession) -> "GameSessionDocument":
        """Create document from GameSession schema."""
        pending_decision_dict = None
        if game.pending_decision:
            pending_decision_dict = game.pending_decision.model_dump()
        
        return cls(
            _id=game.id,
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
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for MongoDB operations."""
        data = self.model_dump(by_alias=True, exclude_none=True)
        return data


class PlayerDocument(BaseModel):
    """MongoDB document model for players."""
    
    _id: str = Field(alias="_id")
    game_id: str
    name: str
    cash: int = 0
    position: int = 0
    color: str = "#888888"
    properties: list[str] = Field(default_factory=list)
    ready: bool = False
    is_bankrupt: bool = False
    created_at: Optional[datetime] = None

    class Config:
        populate_by_name = True

    def to_player(self, submitted_tiles: list[TileCreate]) -> Player:
        """Convert document to Player schema."""
        return Player(
            id=self._id,
            name=self.name,
            cash=self.cash,
            position=self.position,
            color=self.color,
            properties=self.properties,
            submitted_tiles=submitted_tiles,
            ready=self.ready,
            is_bankrupt=self.is_bankrupt,
        )

    @classmethod
    def from_player(cls, player: Player, game_id: str) -> "PlayerDocument":
        """Create document from Player schema."""
        return cls(
            _id=player.id,
            game_id=game_id,
            name=player.name,
            cash=player.cash,
            position=player.position,
            color=player.color,
            properties=player.properties,
            ready=player.ready,
            is_bankrupt=player.is_bankrupt,
            created_at=datetime.utcnow(),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for MongoDB operations."""
        return self.model_dump(by_alias=True, exclude_none=True)


class TileDocument(BaseModel):
    """MongoDB document model for board tiles."""
    
    _id: str = Field(alias="_id")
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

    class Config:
        populate_by_name = True

    def to_tile(self) -> Tile:
        """Convert document to Tile schema."""
        return Tile(
            id=self._id,
            owner_id=self.owner_id,
            type=self.type,
            name=self.name,
            effect_config=self.effect_config,
            position=self.position,
            x=self.x,
            y=self.y,
            price=self.price,
            rent=self.rent,
        )

    @classmethod
    def from_tile(cls, tile: Tile, game_id: str) -> "TileDocument":
        """Create document from Tile schema."""
        return cls(
            _id=tile.id,
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
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for MongoDB operations."""
        data = self.model_dump(by_alias=True, exclude_none=True)
        # Convert enum to string for MongoDB
        data["type"] = self.type.value
        return data


class SubmittedTileDocument(BaseModel):
    """MongoDB document model for submitted tiles."""
    
    _id: str = Field(alias="_id")
    game_id: str
    player_id: str
    type: TileType
    name: str
    effect_config: dict = Field(default_factory=dict)

    class Config:
        populate_by_name = True

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
            _id=tile_id,
            game_id=game_id,
            player_id=player_id,
            type=tile.type,
            name=tile.name,
            effect_config=tile.effect_config,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for MongoDB operations."""
        data = self.model_dump(by_alias=True, exclude_none=True)
        # Convert enum to string for MongoDB
        data["type"] = self.type.value
        return data
