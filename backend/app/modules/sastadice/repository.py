"""Game repository for DuckDB operations."""
import json
from typing import Optional
import duckdb
import uuid

from app.core.db_repo import BaseRepository
from app.modules.sastadice.schemas import (
    GameSession,
    GameStatus,
    Player,
    PlayerCreate,
    Tile,
    TileCreate,
)


class GameRepository(BaseRepository[GameSession]):
    """Repository for game session operations."""

    def get_by_id(self, id: str) -> Optional[GameSession]:
        """Get game session by ID."""
        result = self.cursor.execute(
            "SELECT id, status, current_turn_player_id, board_size FROM sd_game_sessions WHERE id = ?",
            [id],
        ).fetchone()

        if not result:
            return None

        game_id, status, current_turn_player_id, board_size = result

        # Load players
        players = self._get_players(game_id)

        # Load board tiles
        board = self._get_board_tiles(game_id)

        return GameSession(
            id=game_id,
            status=GameStatus(status),
            current_turn_player_id=current_turn_player_id,
            players=players,
            board=board,
            board_size=board_size,
        )

    def create(self, entity: GameSession) -> GameSession:
        """Create a new game session."""
        game_id = entity.id if entity.id else str(uuid.uuid4())
        self.cursor.execute(
            """
            INSERT INTO sd_game_sessions (id, status, current_turn_player_id, board_size, version)
            VALUES (?, ?, ?, ?, 0)
            """,
            [
                game_id,
                entity.status.value,
                entity.current_turn_player_id,
                entity.board_size,
            ],
        )

        entity.id = game_id
        return entity

    def create_game(self) -> GameSession:
        """Create a new empty game session."""
        game = GameSession(
            id=str(uuid.uuid4()),
            status=GameStatus.LOBBY,
            board_size=0,
        )
        return self.create(game)

    def update(self, entity: GameSession) -> GameSession:
        """Update game session."""
        # Update version for polling optimization
        self.cursor.execute(
            """
            UPDATE sd_game_sessions 
            SET status = ?, current_turn_player_id = ?, board_size = ?, version = version + 1
            WHERE id = ?
            """,
            [
                entity.status.value,
                entity.current_turn_player_id,
                entity.board_size,
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
        self.cursor.execute(
            """
            INSERT INTO sd_players (id, game_id, name, cash, position)
            VALUES (?, ?, ?, 1500, 0)
            """,
            [player_id, game_id, player_create.name],
        )

        # Load submitted tiles
        submitted_tiles = self._get_submitted_tiles(game_id, player_id)

        return Player(
            id=player_id,
            name=player_create.name,
            cash=1500,
            position=0,
            submitted_tiles=submitted_tiles,
        )

    def submit_tiles(
        self, game_id: str, player_id: str, tiles: list[TileCreate]
    ) -> None:
        """Submit tiles for a player."""
        # Clear existing submissions
        self.cursor.execute(
            "DELETE FROM sd_submitted_tiles WHERE game_id = ? AND player_id = ?",
            [game_id, player_id],
        )

        # Insert new submissions
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
        # Clear existing board
        self.cursor.execute("DELETE FROM sd_tiles WHERE game_id = ?", [game_id])

        # Insert board tiles
        for tile in tiles:
            self.cursor.execute(
                """
                INSERT INTO sd_tiles (id, game_id, owner_id, type, name, effect_config, position, x, y)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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

    def _get_players(self, game_id: str) -> list[Player]:
        """Get all players for a game."""
        results = self.cursor.execute(
            "SELECT id, name, cash, position FROM sd_players WHERE game_id = ? ORDER BY name",
            [game_id],
        ).fetchall()

        players = []
        for player_id, name, cash, position in results:
            submitted_tiles = self._get_submitted_tiles(game_id, player_id)
            players.append(
                Player(
                    id=player_id,
                    name=name,
                    cash=cash,
                    position=position,
                    submitted_tiles=submitted_tiles,
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
            SELECT id, owner_id, type, name, effect_config, position, x, y
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
                )
            )

        return tiles
