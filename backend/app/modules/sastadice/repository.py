"""Game repository for DuckDB operations."""
import json
from typing import Optional
import uuid

from app.core.db_repo import BaseRepository
from app.modules.sastadice.schemas import (
    GameSession,
    GameStatus,
    TurnPhase,
    PendingDecision,
    Player,
    PlayerCreate,
    Tile,
    TileCreate,
    TileType,
    PLAYER_COLORS,
)


class GameRepository(BaseRepository[GameSession]):
    """Repository for game session operations."""

    def get_by_id(self, id: str) -> Optional[GameSession]:
        """Get game session by ID."""
        result = self.cursor.execute(
            """SELECT id, status, turn_phase, current_turn_player_id, board_size, 
                      starting_cash, go_bonus, last_dice_roll, pending_decision, last_event_message
               FROM sd_game_sessions WHERE id = ?""",
            [id],
        ).fetchone()

        if not result:
            return None

        (game_id, status, turn_phase, current_turn_player_id, board_size,
         starting_cash, go_bonus, last_dice_roll_json, pending_decision_json,
         last_event_message) = result

        players = self._get_players(game_id)
        board = self._get_board_tiles(game_id)
        last_dice_roll = json.loads(last_dice_roll_json) if last_dice_roll_json else None
        pending_decision_data = json.loads(pending_decision_json) if pending_decision_json else None
        pending_decision = PendingDecision(**pending_decision_data) if pending_decision_data else None

        return GameSession(
            id=game_id,
            status=GameStatus(status),
            turn_phase=TurnPhase(turn_phase) if turn_phase else TurnPhase.PRE_ROLL,
            current_turn_player_id=current_turn_player_id,
            players=players,
            board=board,
            board_size=board_size,
            starting_cash=starting_cash or 0,
            go_bonus=go_bonus or 0,
            last_dice_roll=last_dice_roll,
            pending_decision=pending_decision,
            last_event_message=last_event_message,
        )

    def create(self, entity: GameSession) -> GameSession:
        """Create a new game session."""
        game_id = entity.id if entity.id else str(uuid.uuid4())
        pending_decision_json = (
            json.dumps(entity.pending_decision.model_dump())
            if entity.pending_decision else None
        )
        self.cursor.execute(
            """
            INSERT INTO sd_game_sessions 
            (id, status, turn_phase, current_turn_player_id, board_size, version,
             starting_cash, go_bonus, last_dice_roll, pending_decision, last_event_message)
            VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?)
            """,
            [
                game_id,
                entity.status.value,
                entity.turn_phase.value,
                entity.current_turn_player_id,
                entity.board_size,
                entity.starting_cash,
                entity.go_bonus,
                json.dumps(entity.last_dice_roll) if entity.last_dice_roll else None,
                pending_decision_json,
                entity.last_event_message,
            ],
        )

        entity.id = game_id
        return entity

    def create_game(self) -> GameSession:
        """Create a new empty game session."""
        game = GameSession(
            id=str(uuid.uuid4()),
            status=GameStatus.LOBBY,
            turn_phase=TurnPhase.PRE_ROLL,
            board_size=0,
        )
        return self.create(game)

    def update(self, entity: GameSession) -> GameSession:
        """Update game session."""
        pending_decision_json = (
            json.dumps(entity.pending_decision.model_dump())
            if entity.pending_decision else None
        )
        # Update version for polling optimization
        self.cursor.execute(
            """
            UPDATE sd_game_sessions 
            SET status = ?, turn_phase = ?, current_turn_player_id = ?, board_size = ?,
                starting_cash = ?, go_bonus = ?, last_dice_roll = ?, 
                pending_decision = ?, last_event_message = ?, version = version + 1
            WHERE id = ?
            """,
            [
                entity.status.value,
                entity.turn_phase.value,
                entity.current_turn_player_id,
                entity.board_size,
                entity.starting_cash,
                entity.go_bonus,
                json.dumps(entity.last_dice_roll) if entity.last_dice_roll else None,
                pending_decision_json,
                entity.last_event_message,
                entity.id,
            ],
        )
        return entity

    def delete(self, id: str) -> bool:
        """Delete game session by ID."""
        self.cursor.execute("DELETE FROM sd_game_sessions WHERE id = ?", [id])
        return self.cursor.rowcount > 0

    def get_version(self, game_id: str) -> int:
        """Get current version number for polling optimization."""
        result = self.cursor.execute(
            "SELECT version FROM sd_game_sessions WHERE id = ?", [game_id]
        ).fetchone()
        return result[0] if result else 0

    def add_player(self, game_id: str, player_create: PlayerCreate) -> Player:
        """Add a player to a game."""
        player_id = str(uuid.uuid4())
        
        count_result = self.cursor.execute(
            "SELECT COUNT(*) FROM sd_players WHERE game_id = ?",
            [game_id],
        ).fetchone()
        player_count = count_result[0] if count_result else 0
        color = PLAYER_COLORS[player_count % len(PLAYER_COLORS)]
        
        self.cursor.execute(
            """
            INSERT INTO sd_players (id, game_id, name, cash, position, color, properties, ready)
            VALUES (?, ?, ?, 0, 0, ?, '[]', FALSE)
            """,
            [player_id, game_id, player_create.name, color],
        )

        submitted_tiles = self._get_submitted_tiles(game_id, player_id)

        return Player(
            id=player_id,
            name=player_create.name,
            cash=0,
            position=0,
            color=color,
            properties=[],
            submitted_tiles=submitted_tiles,
            ready=False,
        )

    def toggle_player_ready(self, player_id: str) -> bool:
        """Toggle player's ready status. Returns new ready state."""
        self.cursor.execute(
            "UPDATE sd_players SET ready = NOT ready WHERE id = ?",
            [player_id]
        )
        result = self.cursor.execute(
            "SELECT ready FROM sd_players WHERE id = ?",
            [player_id]
        ).fetchone()
        return result[0] if result else False

    def are_all_players_ready(self, game_id: str) -> bool:
        """Check if all players in a game are ready."""
        result = self.cursor.execute(
            """
            SELECT COUNT(*) as total, 
                   SUM(CASE WHEN ready THEN 1 ELSE 0 END) as ready_count
            FROM sd_players WHERE game_id = ?
            """,
            [game_id]
        ).fetchone()
        if not result or result[0] == 0:
            return False
        return result[0] == result[1]

    def submit_tiles(
        self, game_id: str, player_id: str, tiles: list[TileCreate]
    ) -> None:
        """Submit tiles for a player."""
        self.cursor.execute(
            "DELETE FROM sd_submitted_tiles WHERE game_id = ? AND player_id = ?",
            [game_id, player_id],
        )

        for tile in tiles:
            tile_id = str(uuid.uuid4())
            self.cursor.execute(
                """
                INSERT INTO sd_submitted_tiles (id, game_id, player_id, type, name, effect_config)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    tile_id,
                    game_id,
                    player_id,
                    tile.type.value,
                    tile.name,
                    json.dumps(tile.effect_config),
                ],
            )

    def save_board(self, game_id: str, tiles: list[Tile]) -> None:
        """Save board tiles to database."""
        self.cursor.execute("DELETE FROM sd_tiles WHERE game_id = ?", [game_id])

        for tile in tiles:
            self.cursor.execute(
                """
                INSERT INTO sd_tiles (id, game_id, owner_id, type, name, effect_config, position, x, y, price, rent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    tile.id,
                    game_id,
                    tile.owner_id,
                    tile.type.value,
                    tile.name,
                    json.dumps(tile.effect_config),
                    tile.position,
                    tile.x,
                    tile.y,
                    tile.price,
                    tile.rent,
                ],
            )

    def update_game_status(self, game_id: str, status: GameStatus) -> GameSession:
        """Update game status."""
        self.cursor.execute(
            "UPDATE sd_game_sessions SET status = ?, version = version + 1 WHERE id = ?",
            [status.value, game_id],
        )
        game = self.get_by_id(game_id)
        if game:
            game.status = status
        return game

    def update_player_position(self, player_id: str, position: int) -> None:
        """Update player's board position."""
        self.cursor.execute(
            "UPDATE sd_players SET position = ? WHERE id = ?", [position, player_id]
        )

    def update_player_cash(self, player_id: str, cash: int) -> None:
        """Update player's cash."""
        self.cursor.execute(
            "UPDATE sd_players SET cash = ? WHERE id = ?", [cash, player_id]
        )

    def update_player_properties(self, player_id: str, properties: list[str]) -> None:
        """Update player's owned properties."""
        self.cursor.execute(
            "UPDATE sd_players SET properties = ? WHERE id = ?",
            [json.dumps(properties), player_id]
        )

    def update_tile_owner(self, tile_id: str, owner_id: str) -> None:
        """Update tile ownership."""
        self.cursor.execute(
            "UPDATE sd_tiles SET owner_id = ? WHERE id = ?", [owner_id, tile_id]
        )

    def set_players_starting_cash(self, game_id: str, starting_cash: int) -> None:
        """Set starting cash for all players in a game."""
        self.cursor.execute(
            "UPDATE sd_players SET cash = ? WHERE game_id = ?",
            [starting_cash, game_id]
        )

    def _get_players(self, game_id: str) -> list[Player]:
        """Get all players for a game ordered by join time."""
        results = self.cursor.execute(
            """SELECT id, name, cash, position, color, properties, ready
               FROM sd_players WHERE game_id = ? ORDER BY created_at""",
            [game_id],
        ).fetchall()

        players = []
        for player_id, name, cash, position, color, properties_json, ready in results:
            submitted_tiles = self._get_submitted_tiles(game_id, player_id)
            properties = json.loads(properties_json) if properties_json else []
            players.append(
                Player(
                    id=player_id,
                    name=name,
                    cash=cash,
                    position=position,
                    color=color or "#888888",
                    properties=properties,
                    submitted_tiles=submitted_tiles,
                    ready=bool(ready),
                )
            )

        return players

    def _get_submitted_tiles(
        self, game_id: str, player_id: str
    ) -> list[TileCreate]:
        """Get submitted tiles for a player."""
        results = self.cursor.execute(
            """
            SELECT type, name, effect_config 
            FROM sd_submitted_tiles 
            WHERE game_id = ? AND player_id = ?
            """,
            [game_id, player_id],
        ).fetchall()

        tiles = []
        for tile_type, name, effect_config_json in results:
            effect_config = json.loads(effect_config_json) if effect_config_json else {}
            tiles.append(TileCreate(type=TileType(tile_type), name=name, effect_config=effect_config))

        return tiles

    def _get_board_tiles(self, game_id: str) -> list[Tile]:
        """Get all board tiles for a game."""
        results = self.cursor.execute(
            """
            SELECT id, owner_id, type, name, effect_config, position, x, y, price, rent
            FROM sd_tiles
            WHERE game_id = ?
            ORDER BY position
            """,
            [game_id],
        ).fetchall()

        tiles = []
        for (
            tile_id,
            owner_id,
            tile_type,
            name,
            effect_config_json,
            position,
            x,
            y,
            price,
            rent,
        ) in results:
            effect_config = json.loads(effect_config_json) if effect_config_json else {}
            tiles.append(
                Tile(
                    id=tile_id,
                    owner_id=owner_id,
                    type=TileType(tile_type),
                    name=name,
                    effect_config=effect_config,
                    position=position,
                    x=x,
                    y=y,
                    price=price or 0,
                    rent=rent or 0,
                )
            )

        return tiles
