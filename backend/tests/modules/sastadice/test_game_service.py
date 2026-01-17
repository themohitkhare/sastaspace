"""Tests for GameService and GameRepository."""
import pytest
from app.modules.sastadice.services.game_service import GameService
from app.modules.sastadice.repository import GameRepository
from app.modules.sastadice.schemas import (
    GameStatus,
    TurnPhase,
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
        # Cash is now 0 until game starts (dynamic economy)
        assert player.cash == 0
        # Player should have a color assigned
        assert player.color is not None
        assert player.color.startswith('#')

        # Verify in database
        result = db_cursor.execute(
            "SELECT name, cash, color FROM sd_players WHERE id = ?", [player.id]
        ).fetchone()
        assert result is not None
        assert result[0] == "Test Player"
        assert result[1] == 0  # Cash set at game start
        assert result[2] is not None  # Color assigned

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

        # Start game (force=True bypasses launch key requirement for tests)
        started_game = service.start_game(game.id, force=True)

        assert started_game.status == GameStatus.ACTIVE
        assert len(started_game.board) > 0
        assert started_game.board_size > 0
        assert started_game.current_turn_player_id is not None
        # Verify dynamic economy is set
        assert started_game.starting_cash > 0
        assert started_game.go_bonus > 0
        # Verify players have starting cash
        assert all(p.cash > 0 for p in started_game.players)

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
        service.start_game(game.id, force=True)

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
        service.start_game(game.id, force=True)

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
        service.start_game(game.id, force=True)

        # Try to start already active game
        with pytest.raises(ValueError, match="must be in LOBBY status"):
            service.start_game(game.id, force=True)

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
        service.start_game(game.id, force=True)

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
        service.start_game(game.id, force=True)

        result = service.perform_action(game.id, player1.id, ActionType.ROLL_DICE, {})
        assert result.success is True
        assert result.data is not None

    def test_perform_action_end_turn(self, db_cursor):
        """Test perform_action with END_TURN after rolling dice."""
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
        service.start_game(game.id, force=True)

        # First roll dice to advance to DECISION/POST_TURN phase
        roll_result = service.perform_action(game.id, player1.id, ActionType.ROLL_DICE, {})
        assert roll_result.success is True

        # Get game state to check phase
        game_state = service.get_game(game.id)
        
        # If in DECISION phase with pending decision, pass on it
        if game_state.turn_phase == TurnPhase.DECISION and game_state.pending_decision:
            pass_result = service.perform_action(game.id, player1.id, ActionType.PASS_PROPERTY, {})
            assert pass_result.success is True

        # Now should be in POST_TURN phase
        game_state = service.get_game(game.id)
        assert game_state.turn_phase == TurnPhase.POST_TURN

        # End turn
        result = service.perform_action(game.id, player1.id, ActionType.END_TURN, {})
        assert result.success is True

        # Verify turn moved to next player
        updated_game = service.get_game(game.id)
        assert updated_game.current_turn_player_id == player2.id
        assert updated_game.turn_phase == TurnPhase.PRE_ROLL

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
        service.start_game(game.id, force=True)

        result = service.perform_action(game.id, player2.id, ActionType.END_TURN, {})
        assert result.success is False
        assert "Not your turn" in result.message

    def test_perform_action_buy_property(self, db_cursor):
        """Test perform_action with BUY_PROPERTY requires DECISION phase."""
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
        service.start_game(game.id, force=True)

        # Try to buy without rolling first - should fail
        result = service.perform_action(game.id, player1.id, ActionType.BUY_PROPERTY, {})
        assert result.success is False
        assert "Cannot buy property now" in result.message

    def test_turn_phase_state_machine(self, db_cursor):
        """Test the turn phase state machine flow."""
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
        started_game = service.start_game(game.id, force=True)

        # Initial state should be PRE_ROLL
        assert started_game.turn_phase == TurnPhase.PRE_ROLL

        # Roll dice
        roll_result = service.perform_action(game.id, player1.id, ActionType.ROLL_DICE, {})
        assert roll_result.success is True

        # After rolling, should be in DECISION or POST_TURN
        game_state = service.get_game(game.id)
        assert game_state.turn_phase in [TurnPhase.DECISION, TurnPhase.POST_TURN]

        # If in DECISION with pending decision, handle it
        if game_state.turn_phase == TurnPhase.DECISION and game_state.pending_decision:
            pass_result = service.perform_action(game.id, player1.id, ActionType.PASS_PROPERTY, {})
            assert pass_result.success is True
            game_state = service.get_game(game.id)

        # Should now be in POST_TURN
        assert game_state.turn_phase == TurnPhase.POST_TURN

        # End turn
        end_result = service.perform_action(game.id, player1.id, ActionType.END_TURN, {})
        assert end_result.success is True

        # Should be back to PRE_ROLL for next player
        final_state = service.get_game(game.id)
        assert final_state.turn_phase == TurnPhase.PRE_ROLL
        assert final_state.current_turn_player_id == player2.id

    def test_perform_action_unknown(self, db_cursor):
        """Test perform_action with all valid action types."""
        service = GameService(db_cursor)
        game = service.create_game()

        tiles = [
            TileCreate(type=TileType.PROPERTY, name=f"Property {i}")
            for i in range(5)
        ]
        player1 = service.join_game(game.id, "Player 1", tiles)
        player2 = service.join_game(game.id, "Player 2", tiles)
        service.start_game(game.id, force=True)

        # Test ROLL_DICE
        result1 = service.perform_action(game.id, player1.id, ActionType.ROLL_DICE, {})
        assert result1.success is True

        # Handle decision phase if needed
        game_state = service.get_game(game.id)
        if game_state.turn_phase == TurnPhase.DECISION and game_state.pending_decision:
            service.perform_action(game.id, player1.id, ActionType.PASS_PROPERTY, {})

        # Test END_TURN
        result2 = service.perform_action(game.id, player1.id, ActionType.END_TURN, {})
        assert result2.success is True

        # Test BUY_PROPERTY (should fail without proper phase)
        result3 = service.perform_action(game.id, player2.id, ActionType.BUY_PROPERTY, {})
        assert result3.success is False

    def test_perform_action_unknown_enum_value(self, db_cursor):
        """Test perform_action else branch with unknown action."""
        service = GameService(db_cursor)
        game = service.create_game()

        tiles = [
            TileCreate(type=TileType.PROPERTY, name=f"Property {i}")
            for i in range(5)
        ]
        player1 = service.join_game(game.id, "Player 1", tiles)
        player2 = service.join_game(game.id, "Player 2", tiles)
        service.start_game(game.id, force=True)

        # Create a mock ActionType that's not handled
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

    def test_kick_player(self, db_cursor):
        """Test kicking a player from lobby."""
        service = GameService(db_cursor)
        game = service.create_game()

        tiles = [
            TileCreate(type=TileType.PROPERTY, name=f"Property {i}")
            for i in range(5)
        ]
        player1 = service.join_game(game.id, "Player 1", tiles)
        player2 = service.join_game(game.id, "Player 2", tiles)

        # Player 1 should be host (first to join)
        game_state = service.get_game(game.id)
        assert game_state.host_id == player1.id
        assert len(game_state.players) == 2

        # Host kicks player 2
        result = service.kick_player(game.id, player1.id, player2.id)
        assert result["kicked"] is True
        assert result["player_id"] == player2.id

        # Verify player is removed
        game_state = service.get_game(game.id)
        assert len(game_state.players) == 1

    def test_kick_player_not_host(self, db_cursor):
        """Test that non-host cannot kick players."""
        service = GameService(db_cursor)
        game = service.create_game()

        tiles = [
            TileCreate(type=TileType.PROPERTY, name=f"Property {i}")
            for i in range(5)
        ]
        player1 = service.join_game(game.id, "Player 1", tiles)
        player2 = service.join_game(game.id, "Player 2", tiles)

        # Player 2 tries to kick player 1
        with pytest.raises(ValueError, match="Only the host can kick"):
            service.kick_player(game.id, player2.id, player1.id)

    def test_kick_player_after_start(self, db_cursor):
        """Test cannot kick after game started."""
        service = GameService(db_cursor)
        game = service.create_game()

        tiles = [
            TileCreate(type=TileType.PROPERTY, name=f"Property {i}")
            for i in range(5)
        ]
        player1 = service.join_game(game.id, "Player 1", tiles)
        player2 = service.join_game(game.id, "Player 2", tiles)
        service.toggle_ready(game.id, player1.id)
        service.toggle_ready(game.id, player2.id)

        # Game auto-starts when all ready
        with pytest.raises(ValueError, match="Cannot kick players after game has started"):
            service.kick_player(game.id, player1.id, player2.id)

    def test_kick_self_fails(self, db_cursor):
        """Test host cannot kick themselves."""
        service = GameService(db_cursor)
        game = service.create_game()

        tiles = [
            TileCreate(type=TileType.PROPERTY, name=f"Property {i}")
            for i in range(5)
        ]
        player1 = service.join_game(game.id, "Player 1", tiles)

        with pytest.raises(ValueError, match="Cannot kick yourself"):
            service.kick_player(game.id, player1.id, player1.id)

    def test_toggle_ready_auto_start(self, db_cursor):
        """Test that game auto-starts when all players are ready."""
        service = GameService(db_cursor)
        game = service.create_game()

        tiles = [
            TileCreate(type=TileType.PROPERTY, name=f"Property {i}")
            for i in range(5)
        ]
        player1 = service.join_game(game.id, "Player 1", tiles)
        player2 = service.join_game(game.id, "Player 2", tiles)

        # Player 1 turns key
        result1 = service.toggle_ready(game.id, player1.id)
        assert result1["ready"] is True
        assert result1["game_started"] is False

        # Player 2 turns key - should auto-start
        result2 = service.toggle_ready(game.id, player2.id)
        assert result2["ready"] is True
        assert result2["game_started"] is True

        # Verify game started
        game_state = service.get_game(game.id)
        assert game_state.status == GameStatus.ACTIVE

    def test_toggle_ready_not_in_lobby(self, db_cursor):
        """Test cannot toggle ready after game started."""
        service = GameService(db_cursor)
        game = service.create_game()

        tiles = [
            TileCreate(type=TileType.PROPERTY, name=f"Property {i}")
            for i in range(5)
        ]
        player1 = service.join_game(game.id, "Player 1", tiles)
        player2 = service.join_game(game.id, "Player 2", tiles)
        service.toggle_ready(game.id, player1.id)
        service.toggle_ready(game.id, player2.id)

        # Game is now active
        with pytest.raises(ValueError, match="Game already started"):
            service.toggle_ready(game.id, player1.id)

    def test_toggle_ready_player_not_found(self, db_cursor):
        """Test toggle ready with invalid player."""
        service = GameService(db_cursor)
        game = service.create_game()

        tiles = [
            TileCreate(type=TileType.PROPERTY, name=f"Property {i}")
            for i in range(5)
        ]
        service.join_game(game.id, "Player 1", tiles)

        with pytest.raises(ValueError, match="Player not in this game"):
            service.toggle_ready(game.id, "invalid-player-id")

    def test_cpu_players_added_when_needed(self, db_cursor):
        """Test CPU players are added when only one player."""
        service = GameService(db_cursor)
        game = service.create_game()

        tiles = [
            TileCreate(type=TileType.PROPERTY, name=f"Property {i}")
            for i in range(5)
        ]
        player1 = service.join_game(game.id, "Player 1", tiles)

        # Add CPU players to reach 2
        service.add_cpu_players(game.id, target_count=2)

        game_state = service.get_game(game.id)
        assert len(game_state.players) == 2
        # Check using the proper CPU detection method
        assert any(service._is_cpu_player(p) for p in game_state.players)

    def test_pass_property_action(self, db_cursor):
        """Test passing on property purchase."""
        service = GameService(db_cursor)
        game = service.create_game()

        tiles = [
            TileCreate(type=TileType.PROPERTY, name=f"Property {i}")
            for i in range(5)
        ]
        player1 = service.join_game(game.id, "Player 1", tiles)
        player2 = service.join_game(game.id, "Player 2", tiles)
        service.toggle_ready(game.id, player1.id)
        service.toggle_ready(game.id, player2.id)

        # Roll until we hit a property (DECISION phase)
        for _ in range(20):  # Try up to 20 times
            service.perform_action(game.id, player1.id, ActionType.ROLL_DICE, {})
            game_state = service.get_game(game.id)
            if game_state.turn_phase == TurnPhase.DECISION:
                break
            if game_state.turn_phase == TurnPhase.POST_TURN:
                service.perform_action(game.id, player1.id, ActionType.END_TURN, {})
                game_state = service.get_game(game.id)
                if game_state.current_turn_player_id == player1.id:
                    continue
                service.perform_action(game.id, player2.id, ActionType.ROLL_DICE, {})
                game_state = service.get_game(game.id)
                if game_state.turn_phase == TurnPhase.DECISION:
                    player1 = player2  # Switch to current player
                    break
                if game_state.turn_phase == TurnPhase.POST_TURN:
                    service.perform_action(game.id, player2.id, ActionType.END_TURN, {})

        # If we're in DECISION phase, test passing
        game_state = service.get_game(game.id)
        if game_state.turn_phase == TurnPhase.DECISION:
            current_player_id = game_state.current_turn_player_id
            result = service.perform_action(
                game.id, current_player_id, ActionType.PASS_PROPERTY, {}
            )
            assert result.success is True
            assert "Passed" in result.message
