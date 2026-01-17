"""Tests for GameService and GameRepository."""
import pytest
from app.modules.sastadice.services.game_service import GameService
from app.modules.sastadice.repository import GameRepository
from app.modules.sastadice.schemas import (
    GameStatus,
    TileType,
    TileCreate,
    PlayerCreate,
    ActionType,
)


class TestGameRepository:
    """Test suite for GameRepository."""

    def test_create_game(self, db_cursor):
        """Test creating a new game session."""
        repo = GameRepository(db_cursor)
        game = repo.create_game()

        assert game.id is not None
        assert game.status == GameStatus.LOBBY
        assert game.players == []
        assert game.board == []

        # Verify in database
        result = db_cursor.execute(
            "SELECT id, status FROM sd_game_sessions WHERE id = ?", [game.id]
        ).fetchone()
        assert result is not None
        assert result[0] == game.id
        assert result[1] == "LOBBY"

    def test_get_game_by_id(self, db_cursor):
        """Test retrieving a game by ID."""
        repo = GameRepository(db_cursor)
        game = repo.create_game()
        retrieved = repo.get_game_by_id(game.id)

        assert retrieved is not None
        assert retrieved.id == game.id
        assert retrieved.status == game.status

    def test_add_player(self, db_cursor):
        """Test adding a player to a game."""
        repo = GameRepository(db_cursor)
        game = repo.create_game()
        player_create = PlayerCreate(name="Test Player")

        player = repo.add_player(game.id, player_create)

        assert player.id is not None
        assert player.name == "Test Player"
        assert player.cash == 1500

        # Verify in database
        result = db_cursor.execute(
            "SELECT name, cash FROM sd_players WHERE id = ?", [player.id]
        ).fetchone()
        assert result is not None
        assert result[0] == "Test Player"
        assert result[1] == 1500

    def test_submit_tiles(self, db_cursor):
        """Test submitting tiles for a player."""
        repo = GameRepository(db_cursor)
        game = repo.create_game()
        player_create = PlayerCreate(name="Test Player")
        player = repo.add_player(game.id, player_create)

        tiles = [
            TileCreate(type=TileType.PROPERTY, name=f"Property {i}")
            for i in range(5)
        ]

        repo.submit_tiles(game.id, player.id, tiles)

        # Verify tiles in database
        result = db_cursor.execute(
            "SELECT COUNT(*) FROM sd_submitted_tiles WHERE player_id = ?", [player.id]
        ).fetchall()
        assert result[0][0] == 5

    def test_get_game_with_players(self, db_cursor):
        """Test retrieving game with all players."""
        repo = GameRepository(db_cursor)
        game = repo.create_game()
        player1 = repo.add_player(game.id, PlayerCreate(name="Player 1"))
        player2 = repo.add_player(game.id, PlayerCreate(name="Player 2"))

        retrieved = repo.get_game_by_id(game.id)
        assert len(retrieved.players) == 2
        assert player1.id in [p.id for p in retrieved.players]
        assert player2.id in [p.id for p in retrieved.players]

    def test_update_game_status(self, db_cursor):
        """Test updating game status."""
        repo = GameRepository(db_cursor)
        game = repo.create_game()

        updated = repo.update_game_status(game.id, GameStatus.ACTIVE)
        assert updated.status == GameStatus.ACTIVE

        retrieved = repo.get_game_by_id(game.id)
        assert retrieved.status == GameStatus.ACTIVE


class TestGameService:
    """Test suite for GameService."""

    def test_create_game(self, db_cursor):
        """Test creating a new game."""
        service = GameService(db_cursor)
        game = service.create_game()

        assert game.id is not None
        assert game.status == GameStatus.LOBBY

    def test_join_game(self, db_cursor):
        """Test joining a game."""
        service = GameService(db_cursor)
        game = service.create_game()

        tiles = [
            TileCreate(type=TileType.PROPERTY, name=f"Property {i}")
            for i in range(5)
        ]

        player = service.join_game(game.id, "Test Player", tiles)

        assert player.name == "Test Player"
        assert len(player.submitted_tiles) == 5

        # Verify game has the player
        updated_game = service.get_game(game.id)
        assert len(updated_game.players) == 1

    def test_start_game_generates_board(self, db_cursor):
        """Test starting a game generates the board."""
        service = GameService(db_cursor)
        game = service.create_game()

        # Add 2 players
        tiles1 = [
            TileCreate(type=TileType.PROPERTY, name=f"P1-Property {i}")
            for i in range(5)
        ]
        tiles2 = [
            TileCreate(type=TileType.PROPERTY, name=f"P2-Property {i}")
            for i in range(5)
        ]

        service.join_game(game.id, "Player 1", tiles1)
        service.join_game(game.id, "Player 2", tiles2)

        # Start game
        started_game = service.start_game(game.id)

        assert started_game.status == GameStatus.ACTIVE
        assert len(started_game.board) > 0
        assert started_game.board_size > 0
        assert started_game.current_turn_player_id is not None

    def test_roll_dice(self, db_cursor):
        """Test rolling dice."""
        service = GameService(db_cursor)
        game = service.create_game()

        tiles = [
            TileCreate(type=TileType.PROPERTY, name=f"Property {i}")
            for i in range(5)
        ]
        player = service.join_game(game.id, "Test Player", tiles)
        service.start_game(game.id)

        result = service.roll_dice(game.id, player.id)

        assert result.dice1 >= 1 and result.dice1 <= 6
        assert result.dice2 >= 1 and result.dice2 <= 6
        assert result.total == result.dice1 + result.dice2
        assert result.is_doubles == (result.dice1 == result.dice2)
