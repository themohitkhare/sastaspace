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
        retrieved = repo.get_by_id(game.id)

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

        retrieved = repo.get_by_id(game.id)
        assert len(retrieved.players) == 2
        assert player1.id in [p.id for p in retrieved.players]
        assert player2.id in [p.id for p in retrieved.players]

    def test_update_game_status(self, db_cursor):
        """Test updating game status."""
        repo = GameRepository(db_cursor)
        game = repo.create_game()

        updated = repo.update_game_status(game.id, GameStatus.ACTIVE)
        assert updated.status == GameStatus.ACTIVE

        retrieved = repo.get_by_id(game.id)
        assert retrieved.status == GameStatus.ACTIVE

    def test_delete_game(self, db_cursor):
        """Test deleting a game."""
        repo = GameRepository(db_cursor)
        game = repo.create_game()

        # Verify game exists
        retrieved = repo.get_by_id(game.id)
        assert retrieved is not None

        # Delete game - DuckDB execute doesn't return rowcount, so we check by querying
        repo.delete(game.id)

        # Verify game is deleted
        retrieved_after = repo.get_by_id(game.id)
        assert retrieved_after is None

    def test_get_version(self, db_cursor):
        """Test getting game version."""
        repo = GameRepository(db_cursor)
        game = repo.create_game()

        version = repo.get_version(game.id)
        assert version == 0

        # Update game to increment version
        repo.update_game_status(game.id, GameStatus.ACTIVE)
        new_version = repo.get_version(game.id)
        assert new_version == 1


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

    def test_join_game_wrong_number_of_tiles(self, db_cursor):
        """Test joining with wrong number of tiles."""
        service = GameService(db_cursor)
        game = service.create_game()

        # Try with 4 tiles (should be 5)
        tiles = [
            TileCreate(type=TileType.PROPERTY, name=f"Property {i}")
            for i in range(4)
        ]

        with pytest.raises(ValueError, match="exactly 5 tiles"):
            service.join_game(game.id, "Test Player", tiles)

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

        # Add 2 players to allow starting the game
        tiles1 = [
            TileCreate(type=TileType.PROPERTY, name=f"Property {i}")
            for i in range(5)
        ]
        tiles2 = [
            TileCreate(type=TileType.PROPERTY, name=f"Property {i+5}")
            for i in range(5)
        ]
        player1 = service.join_game(game.id, "Player 1", tiles1)
        player2 = service.join_game(game.id, "Player 2", tiles2)
        service.start_game(game.id)

        result = service.roll_dice(game.id, player1.id)

        assert result.dice1 >= 1 and result.dice1 <= 6
        assert result.dice2 >= 1 and result.dice2 <= 6
        assert result.total == result.dice1 + result.dice2
        assert result.is_doubles == (result.dice1 == result.dice2)

    def test_get_game_not_found(self, db_cursor):
        """Test getting a non-existent game raises error."""
        service = GameService(db_cursor)
        with pytest.raises(ValueError, match="not found"):
            service.get_game("nonexistent-id")

    def test_join_game_wrong_status(self, db_cursor):
        """Test joining a game that's not in LOBBY status."""
        service = GameService(db_cursor)
        game = service.create_game()

        tiles = [
            TileCreate(type=TileType.PROPERTY, name=f"Property {i}")
            for i in range(5)
        ]
        service.join_game(game.id, "Player 1", tiles)
        service.join_game(game.id, "Player 2", tiles)
        service.start_game(game.id)

        # Try to join active game
        with pytest.raises(ValueError, match="Cannot join game"):
            service.join_game(game.id, "Player 3", tiles)

    def test_start_game_wrong_status(self, db_cursor):
        """Test starting a game that's not in LOBBY status."""
        service = GameService(db_cursor)
        game = service.create_game()

        tiles = [
            TileCreate(type=TileType.PROPERTY, name=f"Property {i}")
            for i in range(5)
        ]
        service.join_game(game.id, "Player 1", tiles)
        service.join_game(game.id, "Player 2", tiles)
        service.start_game(game.id)

        # Try to start already active game
        with pytest.raises(ValueError, match="must be in LOBBY status"):
            service.start_game(game.id)

    def test_roll_dice_wrong_status(self, db_cursor):
        """Test rolling dice in wrong game status."""
        service = GameService(db_cursor)
        game = service.create_game()

        tiles = [
            TileCreate(type=TileType.PROPERTY, name=f"Property {i}")
            for i in range(5)
        ]
        player = service.join_game(game.id, "Player 1", tiles)

        # Try to roll dice in LOBBY status
        with pytest.raises(ValueError, match="must be ACTIVE"):
            service.roll_dice(game.id, player.id)

    def test_roll_dice_not_your_turn(self, db_cursor):
        """Test rolling dice when it's not your turn."""
        service = GameService(db_cursor)
        game = service.create_game()

        tiles1 = [
            TileCreate(type=TileType.PROPERTY, name=f"Property {i}")
            for i in range(5)
        ]
        tiles2 = [
            TileCreate(type=TileType.PROPERTY, name=f"Property {i+5}")
            for i in range(5)
        ]
        player1 = service.join_game(game.id, "Player 1", tiles1)
        player2 = service.join_game(game.id, "Player 2", tiles2)
        service.start_game(game.id)

        # Player 2 tries to roll when it's player 1's turn
        with pytest.raises(ValueError, match="Not your turn"):
            service.roll_dice(game.id, player2.id)

    def test_perform_action_roll_dice(self, db_cursor):
        """Test perform_action with ROLL_DICE."""
        service = GameService(db_cursor)
        game = service.create_game()

        tiles1 = [
            TileCreate(type=TileType.PROPERTY, name=f"Property {i}")
            for i in range(5)
        ]
        tiles2 = [
            TileCreate(type=TileType.PROPERTY, name=f"Property {i+5}")
            for i in range(5)
        ]
        player1 = service.join_game(game.id, "Player 1", tiles1)
        player2 = service.join_game(game.id, "Player 2", tiles2)
        service.start_game(game.id)

        result = service.perform_action(game.id, player1.id, ActionType.ROLL_DICE, {})
        assert result.success is True
        assert "data" in result.message or result.data is not None

    def test_perform_action_end_turn(self, db_cursor):
        """Test perform_action with END_TURN."""
        service = GameService(db_cursor)
        game = service.create_game()

        tiles1 = [
            TileCreate(type=TileType.PROPERTY, name=f"Property {i}")
            for i in range(5)
        ]
        tiles2 = [
            TileCreate(type=TileType.PROPERTY, name=f"Property {i+5}")
            for i in range(5)
        ]
        player1 = service.join_game(game.id, "Player 1", tiles1)
        player2 = service.join_game(game.id, "Player 2", tiles2)
        service.start_game(game.id)

        result = service.perform_action(game.id, player1.id, ActionType.END_TURN, {})
        assert result.success is True

        # Verify turn moved to next player
        updated_game = service.get_game(game.id)
        assert updated_game.current_turn_player_id == player2.id

    def test_perform_action_end_turn_not_your_turn(self, db_cursor):
        """Test perform_action END_TURN when not your turn."""
        service = GameService(db_cursor)
        game = service.create_game()

        tiles1 = [
            TileCreate(type=TileType.PROPERTY, name=f"Property {i}")
            for i in range(5)
        ]
        tiles2 = [
            TileCreate(type=TileType.PROPERTY, name=f"Property {i+5}")
            for i in range(5)
        ]
        player1 = service.join_game(game.id, "Player 1", tiles1)
        player2 = service.join_game(game.id, "Player 2", tiles2)
        service.start_game(game.id)

        result = service.perform_action(game.id, player2.id, ActionType.END_TURN, {})
        assert result.success is False
        assert "Not your turn" in result.message

    def test_perform_action_buy_property(self, db_cursor):
        """Test perform_action with BUY_PROPERTY."""
        service = GameService(db_cursor)
        game = service.create_game()

        tiles1 = [
            TileCreate(type=TileType.PROPERTY, name=f"Property {i}")
            for i in range(5)
        ]
        tiles2 = [
            TileCreate(type=TileType.PROPERTY, name=f"Property {i+5}")
            for i in range(5)
        ]
        player1 = service.join_game(game.id, "Player 1", tiles1)
        player2 = service.join_game(game.id, "Player 2", tiles2)
        service.start_game(game.id)

        result = service.perform_action(game.id, player1.id, ActionType.BUY_PROPERTY, {})
        assert result.success is False
        assert "not yet implemented" in result.message

    def test_perform_action_unknown(self, db_cursor):
        """Test perform_action with unknown action type."""
        service = GameService(db_cursor)
        game = service.create_game()

        tiles = [
            TileCreate(type=TileType.PROPERTY, name=f"Property {i}")
            for i in range(5)
        ]
        player1 = service.join_game(game.id, "Player 1", tiles)
        player2 = service.join_game(game.id, "Player 2", tiles)
        service.start_game(game.id)

        # Test all valid action types work
        result1 = service.perform_action(game.id, player1.id, ActionType.ROLL_DICE, {})
        assert result1.success is True

        result2 = service.perform_action(game.id, player1.id, ActionType.END_TURN, {})
        assert result2.success is True

        result3 = service.perform_action(game.id, player1.id, ActionType.BUY_PROPERTY, {})
        assert result3.success is False  # Not implemented

    def test_perform_action_unknown_enum_value(self, db_cursor):
        """Test perform_action else branch with unknown action."""
        from unittest.mock import MagicMock
        service = GameService(db_cursor)
        game = service.create_game()

        tiles = [
            TileCreate(type=TileType.PROPERTY, name=f"Property {i}")
            for i in range(5)
        ]
        player1 = service.join_game(game.id, "Player 1", tiles)
        player2 = service.join_game(game.id, "Player 2", tiles)
        service.start_game(game.id)

        # Create a mock ActionType that's not handled
        # We'll use a string that behaves like an enum value but isn't in the enum
        class MockActionType:
            def __eq__(self, other):
                return False
            def __str__(self):
                return "UNKNOWN_ACTION"
        
        mock_action = MockActionType()
        # Bypass type checking to test else branch
        result = service.perform_action(game.id, player1.id, mock_action, {})  # type: ignore
        assert result.success is False
        assert "Unknown action" in result.message
