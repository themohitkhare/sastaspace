"""Tests for GameService and GameRepository."""

import pytest

from app.modules.sastadice.repository import GameRepository
from app.modules.sastadice.schemas import (
    ActionType,
    GameStatus,
    PlayerCreate,
    TileCreate,
    TileType,
    TurnPhase,
)
from app.modules.sastadice.services.game_service import GameService


class TestGameRepository:
    """Test suite for GameRepository."""

    @pytest.mark.asyncio
    async def test_create_game(self, db_database):
        """Test creating a new game session."""
        repo = GameRepository(db_database)
        game = await repo.create_game()

        assert game.id is not None
        assert game.status == GameStatus.LOBBY
        assert game.players == []
        assert game.board == []

        # Verify in database
        result = await db_database.game_sessions.find_one({"_id": game.id})
        assert result is not None
        assert result["_id"] == game.id
        assert result["status"] == GameStatus.LOBBY.value

    @pytest.mark.asyncio
    async def test_get_game_by_id(self, db_database):
        """Test retrieving a game by ID."""
        repo = GameRepository(db_database)
        game = await repo.create_game()
        retrieved = await repo.get_by_id(game.id)

        assert retrieved is not None
        assert retrieved.id == game.id
        assert retrieved.status == game.status

    @pytest.mark.asyncio
    async def test_add_player(self, db_database):
        """Test adding a player to a game."""
        repo = GameRepository(db_database)
        game = await repo.create_game()
        player_create = PlayerCreate(name="Test Player")

        player = await repo.add_player(game.id, player_create)

        assert player.id is not None
        assert player.name == "Test Player"
        # Cash is now 0 until game starts (dynamic economy)
        assert player.cash == 0
        # Player should have a color assigned
        assert player.color is not None
        assert player.color.startswith("#")

        # Verify in database
        result = await db_database.players.find_one({"_id": player.id})
        assert result is not None
        assert result["name"] == "Test Player"
        assert result["cash"] == 0  # Cash set at game start
        assert result["color"] is not None  # Color assigned

    @pytest.mark.asyncio
    async def test_submit_tiles(self, db_database):
        """Test submitting tiles for a player."""
        repo = GameRepository(db_database)
        game = await repo.create_game()
        player_create = PlayerCreate(name="Test Player")
        player = await repo.add_player(game.id, player_create)

        tiles = [TileCreate(type=TileType.PROPERTY, name=f"Property {i}") for i in range(5)]

        await repo.submit_tiles(game.id, player.id, tiles)

        # Verify tiles in database
        count = await db_database.submitted_tiles.count_documents({"player_id": player.id})
        assert count == 5

    @pytest.mark.asyncio
    async def test_get_game_with_players(self, db_database):
        """Test retrieving game with all players."""
        repo = GameRepository(db_database)
        game = await repo.create_game()
        player1 = await repo.add_player(game.id, PlayerCreate(name="Player 1"))
        player2 = await repo.add_player(game.id, PlayerCreate(name="Player 2"))

        retrieved = await repo.get_by_id(game.id)
        assert len(retrieved.players) == 2
        assert player1.id in [p.id for p in retrieved.players]
        assert player2.id in [p.id for p in retrieved.players]

    @pytest.mark.asyncio
    async def test_update_game_status(self, db_database):
        """Test updating game status."""
        repo = GameRepository(db_database)
        game = await repo.create_game()

        updated = await repo.update_game_status(game.id, GameStatus.ACTIVE)
        assert updated.status == GameStatus.ACTIVE

        retrieved = await repo.get_by_id(game.id)
        assert retrieved.status == GameStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_delete_game(self, db_database):
        """Test deleting a game."""
        repo = GameRepository(db_database)
        game = await repo.create_game()

        # Verify game exists
        retrieved = await repo.get_by_id(game.id)
        assert retrieved is not None

        # Delete game
        deleted = await repo.delete(game.id)
        assert deleted is True

        # Verify game is deleted
        retrieved_after = await repo.get_by_id(game.id)
        assert retrieved_after is None

    @pytest.mark.asyncio
    async def test_get_version(self, db_database):
        """Test getting game version."""
        repo = GameRepository(db_database)
        game = await repo.create_game()

        version = await repo.get_version(game.id)
        assert version == 0

        # Update game to increment version
        await repo.update_game_status(game.id, GameStatus.ACTIVE)
        new_version = await repo.get_version(game.id)
        assert new_version == 1


class TestGameService:
    """Test suite for GameService."""

    @pytest.mark.asyncio
    async def test_create_game(self, db_database):
        """Test creating a new game."""
        service = GameService(db_database)
        game = await service.create_game()

        assert game.id is not None
        assert game.status == GameStatus.LOBBY

    @pytest.mark.asyncio
    async def test_join_game(self, db_database):
        """Test joining a game."""
        service = GameService(db_database)
        game = await service.create_game()

        tiles = [TileCreate(type=TileType.PROPERTY, name=f"Property {i}") for i in range(5)]

        player = await service.join_game(game.id, "Test Player", tiles)

        assert player.name == "Test Player"
        assert len(player.submitted_tiles) == 5

        # Verify game has the player
        updated_game = await service.get_game(game.id)
        assert len(updated_game.players) == 1

    @pytest.mark.asyncio
    async def test_join_game_wrong_number_of_tiles(self, db_database):
        """Test joining with wrong number of tiles."""
        service = GameService(db_database)
        game = await service.create_game()

        # Try with 4 tiles (should be 5)
        tiles = [TileCreate(type=TileType.PROPERTY, name=f"Property {i}") for i in range(4)]

        with pytest.raises(ValueError, match="exactly 5 tiles"):
            await service.join_game(game.id, "Test Player", tiles)

    @pytest.mark.asyncio
    async def test_start_game_generates_board(self, db_database):
        """Test starting a game generates the board."""
        service = GameService(db_database)
        game = await service.create_game()

        # Add 2 players
        tiles1 = [TileCreate(type=TileType.PROPERTY, name=f"P1-Property {i}") for i in range(5)]
        tiles2 = [TileCreate(type=TileType.PROPERTY, name=f"P2-Property {i}") for i in range(5)]

        await service.join_game(game.id, "Player 1", tiles1)
        await service.join_game(game.id, "Player 2", tiles2)

        # Start game (force=True bypasses launch key requirement for tests)
        started_game = await service.start_game(game.id, force=True)

        assert started_game.status == GameStatus.ACTIVE
        assert len(started_game.board) > 0
        assert started_game.board_size > 0
        assert started_game.current_turn_player_id is not None
        # Verify dynamic economy is set
        assert started_game.starting_cash > 0
        assert started_game.go_bonus > 0
        # Verify players have starting cash
        assert all(p.cash > 0 for p in started_game.players)

    @pytest.mark.asyncio
    async def test_roll_dice(self, db_database):
        """Test rolling dice."""
        service = GameService(db_database)
        game = await service.create_game()

        # Add 2 players to allow starting the game
        tiles1 = [TileCreate(type=TileType.PROPERTY, name=f"Property {i}") for i in range(5)]
        tiles2 = [TileCreate(type=TileType.PROPERTY, name=f"Property {i + 5}") for i in range(5)]
        player1 = await service.join_game(game.id, "Player 1", tiles1)
        player2 = await service.join_game(game.id, "Player 2", tiles2)
        await service.start_game(game.id, force=True)

        result = await service.roll_dice(game.id, player1.id)

        assert result.dice1 >= 1 and result.dice1 <= 6
        assert result.dice2 >= 1 and result.dice2 <= 6
        assert result.total == result.dice1 + result.dice2
        assert result.is_doubles == (result.dice1 == result.dice2)

    @pytest.mark.asyncio
    async def test_get_game_not_found(self, db_database):
        """Test getting a non-existent game raises error."""
        service = GameService(db_database)
        with pytest.raises(ValueError, match="not found"):
            await service.get_game("nonexistent-id")

    @pytest.mark.asyncio
    async def test_join_game_wrong_status(self, db_database):
        """Test joining a game that's not in LOBBY status."""
        service = GameService(db_database)
        game = await service.create_game()

        tiles = [TileCreate(type=TileType.PROPERTY, name=f"Property {i}") for i in range(5)]
        await service.join_game(game.id, "Player 1", tiles)
        await service.join_game(game.id, "Player 2", tiles)
        await service.start_game(game.id, force=True)

        # Try to join active game
        with pytest.raises(ValueError, match="Cannot join game"):
            await service.join_game(game.id, "Player 3", tiles)

    @pytest.mark.asyncio
    async def test_start_game_wrong_status(self, db_database):
        """Test starting a game that's not in LOBBY status."""
        service = GameService(db_database)
        game = await service.create_game()

        tiles = [TileCreate(type=TileType.PROPERTY, name=f"Property {i}") for i in range(5)]
        await service.join_game(game.id, "Player 1", tiles)
        await service.join_game(game.id, "Player 2", tiles)
        await service.start_game(game.id, force=True)

        # Try to start already active game
        with pytest.raises(ValueError, match="must be in LOBBY status"):
            await service.start_game(game.id, force=True)

    @pytest.mark.asyncio
    async def test_roll_dice_wrong_status(self, db_database):
        """Test rolling dice in wrong game status."""
        service = GameService(db_database)
        game = await service.create_game()

        tiles = [TileCreate(type=TileType.PROPERTY, name=f"Property {i}") for i in range(5)]
        player = await service.join_game(game.id, "Player 1", tiles)

        # Try to roll dice in LOBBY status
        with pytest.raises(ValueError, match="must be ACTIVE"):
            await service.roll_dice(game.id, player.id)

    @pytest.mark.asyncio
    async def test_roll_dice_not_your_turn(self, db_database):
        """Test rolling dice when it's not your turn."""
        service = GameService(db_database)
        game = await service.create_game()

        tiles1 = [TileCreate(type=TileType.PROPERTY, name=f"Property {i}") for i in range(5)]
        tiles2 = [TileCreate(type=TileType.PROPERTY, name=f"Property {i + 5}") for i in range(5)]
        player1 = await service.join_game(game.id, "Player 1", tiles1)
        player2 = await service.join_game(game.id, "Player 2", tiles2)
        await service.start_game(game.id, force=True)

        # Player 2 tries to roll when it's player 1's turn
        with pytest.raises(ValueError, match="Not your turn"):
            await service.roll_dice(game.id, player2.id)

    @pytest.mark.asyncio
    async def test_perform_action_roll_dice(self, db_database):
        """Test perform_action with ROLL_DICE."""
        service = GameService(db_database)
        game = await service.create_game()

        tiles1 = [TileCreate(type=TileType.PROPERTY, name=f"Property {i}") for i in range(5)]
        tiles2 = [TileCreate(type=TileType.PROPERTY, name=f"Property {i + 5}") for i in range(5)]
        player1 = await service.join_game(game.id, "Player 1", tiles1)
        player2 = await service.join_game(game.id, "Player 2", tiles2)
        await service.start_game(game.id, force=True)

        result = await service.perform_action(game.id, player1.id, ActionType.ROLL_DICE, {})
        assert result.success is True
        assert result.data is not None

    @pytest.mark.asyncio
    async def test_perform_action_end_turn(self, db_database):
        """Test perform_action with END_TURN after rolling dice."""
        service = GameService(db_database)
        game = await service.create_game()

        tiles1 = [TileCreate(type=TileType.PROPERTY, name=f"Property {i}") for i in range(5)]
        tiles2 = [TileCreate(type=TileType.PROPERTY, name=f"Property {i + 5}") for i in range(5)]
        player1 = await service.join_game(game.id, "Player 1", tiles1)
        player2 = await service.join_game(game.id, "Player 2", tiles2)

        # Disable auctions for this test
        game = await service.get_game(game.id)
        game.settings.enable_auctions = False
        await service.repository.update(game)

        await service.start_game(game.id, force=True)

        # First roll dice to advance to DECISION/POST_TURN phase
        roll_result = await service.perform_action(game.id, player1.id, ActionType.ROLL_DICE, {})
        assert roll_result.success is True

        # Get game state to check phase
        game_state = await service.get_game(game.id)

        # If in DECISION phase with pending decision, pass on it
        if game_state.turn_phase == TurnPhase.DECISION and game_state.pending_decision:
            pass_result = await service.perform_action(
                game.id, player1.id, ActionType.PASS_PROPERTY, {}
            )
            assert pass_result.success is True

        # Now should be in POST_TURN phase (or AUCTION if auctions enabled)
        game_state = await service.get_game(game.id)
        assert game_state.turn_phase in [TurnPhase.POST_TURN, TurnPhase.AUCTION]

        # If in AUCTION phase, resolve it
        if game_state.turn_phase == TurnPhase.AUCTION:
            resolve_result = await service.perform_action(
                game.id, player1.id, ActionType.RESOLVE_AUCTION, {}
            )
            assert resolve_result.success is True
            game_state = await service.get_game(game.id)

        assert game_state.turn_phase == TurnPhase.POST_TURN

        # End turn
        result = await service.perform_action(game.id, player1.id, ActionType.END_TURN, {})
        assert result.success is True

        # Verify turn moved to next player
        updated_game = await service.get_game(game.id)
        assert updated_game.current_turn_player_id == player2.id
        assert updated_game.turn_phase == TurnPhase.PRE_ROLL

    @pytest.mark.asyncio
    async def test_perform_action_end_turn_not_your_turn(self, db_database):
        """Test perform_action END_TURN when not your turn."""
        service = GameService(db_database)
        game = await service.create_game()

        tiles1 = [TileCreate(type=TileType.PROPERTY, name=f"Property {i}") for i in range(5)]
        tiles2 = [TileCreate(type=TileType.PROPERTY, name=f"Property {i + 5}") for i in range(5)]
        player1 = await service.join_game(game.id, "Player 1", tiles1)
        player2 = await service.join_game(game.id, "Player 2", tiles2)
        await service.start_game(game.id, force=True)

        result = await service.perform_action(game.id, player2.id, ActionType.END_TURN, {})
        assert result.success is False
        assert "Not your turn" in result.message

    @pytest.mark.asyncio
    async def test_perform_action_buy_property(self, db_database):
        """Test perform_action with BUY_PROPERTY requires DECISION phase."""
        service = GameService(db_database)
        game = await service.create_game()

        tiles1 = [TileCreate(type=TileType.PROPERTY, name=f"Property {i}") for i in range(5)]
        tiles2 = [TileCreate(type=TileType.PROPERTY, name=f"Property {i + 5}") for i in range(5)]
        player1 = await service.join_game(game.id, "Player 1", tiles1)
        player2 = await service.join_game(game.id, "Player 2", tiles2)
        await service.start_game(game.id, force=True)

        # Try to buy without rolling first - should fail
        result = await service.perform_action(game.id, player1.id, ActionType.BUY_PROPERTY, {})
        assert result.success is False
        assert "Cannot buy property now" in result.message

    @pytest.mark.asyncio
    async def test_turn_phase_state_machine(self, db_database):
        """Test the turn phase state machine flow."""
        service = GameService(db_database)
        game = await service.create_game()

        # Disable auctions for deterministic flow
        game.settings.enable_auctions = False
        await service.repository.update(game)

        tiles1 = [TileCreate(type=TileType.PROPERTY, name=f"Property {i}") for i in range(5)]
        tiles2 = [TileCreate(type=TileType.PROPERTY, name=f"Property {i + 5}") for i in range(5)]
        player1 = await service.join_game(game.id, "Player 1", tiles1)
        player2 = await service.join_game(game.id, "Player 2", tiles2)
        started_game = await service.start_game(game.id, force=True)

        # Initial state should be PRE_ROLL
        assert started_game.turn_phase == TurnPhase.PRE_ROLL

        # Roll dice
        roll_result = await service.perform_action(game.id, player1.id, ActionType.ROLL_DICE, {})
        assert roll_result.success is True

        # After rolling, should be in DECISION or POST_TURN
        game_state = await service.get_game(game.id)
        assert game_state.turn_phase in [TurnPhase.DECISION, TurnPhase.POST_TURN]

        # If in DECISION with pending decision, handle it
        if game_state.turn_phase == TurnPhase.DECISION and game_state.pending_decision:
            pass_result = await service.perform_action(
                game.id, player1.id, ActionType.PASS_PROPERTY, {}
            )
            assert pass_result.success is True
            game_state = await service.get_game(game.id)

        # Should now be in POST_TURN
        assert game_state.turn_phase == TurnPhase.POST_TURN

        # End turn
        end_result = await service.perform_action(game.id, player1.id, ActionType.END_TURN, {})
        assert end_result.success is True

        # Should be back to PRE_ROLL for next player
        final_state = await service.get_game(game.id)
        assert final_state.turn_phase == TurnPhase.PRE_ROLL
        assert final_state.current_turn_player_id == player2.id

    @pytest.mark.asyncio
    async def test_perform_action_unknown(self, db_database):
        """Test perform_action with all valid action types."""
        service = GameService(db_database)
        game = await service.create_game()

        tiles = [TileCreate(type=TileType.PROPERTY, name=f"Property {i}") for i in range(5)]
        player1 = await service.join_game(game.id, "Player 1", tiles)
        player2 = await service.join_game(game.id, "Player 2", tiles)

        # Disable auctions for deterministic flow
        game.settings.enable_auctions = False
        await service.repository.update(game)

        await service.start_game(game.id, force=True)

        # Test ROLL_DICE
        result1 = await service.perform_action(game.id, player1.id, ActionType.ROLL_DICE, {})
        assert result1.success is True

        # Handle decision phase if needed
        game_state = await service.get_game(game.id)
        if game_state.turn_phase == TurnPhase.DECISION and game_state.pending_decision:
            await service.perform_action(game.id, player1.id, ActionType.PASS_PROPERTY, {})

        # Test END_TURN
        result2 = await service.perform_action(game.id, player1.id, ActionType.END_TURN, {})
        assert result2.success is True

        # Test BUY_PROPERTY (should fail without proper phase)
        result3 = await service.perform_action(game.id, player2.id, ActionType.BUY_PROPERTY, {})
        assert result3.success is False

    @pytest.mark.asyncio
    async def test_perform_action_unknown_enum_value(self, db_database):
        """Test perform_action else branch with unknown action."""
        service = GameService(db_database)
        game = await service.create_game()

        tiles = [TileCreate(type=TileType.PROPERTY, name=f"Property {i}") for i in range(5)]
        player1 = await service.join_game(game.id, "Player 1", tiles)
        player2 = await service.join_game(game.id, "Player 2", tiles)
        await service.start_game(game.id, force=True)

        # Create a mock ActionType that's not handled
        class MockActionType:
            def __eq__(self, other):
                return False

            def __str__(self):
                return "UNKNOWN_ACTION"

        mock_action = MockActionType()
        # Bypass type checking to test else branch
        result = await service.perform_action(game.id, player1.id, mock_action, {})  # type: ignore
        assert result.success is False
        assert "Unknown action" in result.message

    @pytest.mark.asyncio
    async def test_kick_player(self, db_database):
        """Test kicking a player from lobby."""
        service = GameService(db_database)
        game = await service.create_game()

        tiles = [TileCreate(type=TileType.PROPERTY, name=f"Property {i}") for i in range(5)]
        player1 = await service.join_game(game.id, "Player 1", tiles)
        player2 = await service.join_game(game.id, "Player 2", tiles)

        # Player 1 should be host (first to join)
        game_state = await service.get_game(game.id)
        assert game_state.host_id == player1.id
        assert len(game_state.players) == 2

        # Host kicks player 2
        result = await service.kick_player(game.id, player1.id, player2.id)
        assert result["kicked"] is True
        assert result["player_id"] == player2.id

        # Verify player is removed
        game_state = await service.get_game(game.id)
        assert len(game_state.players) == 1

    @pytest.mark.asyncio
    async def test_kick_player_not_host(self, db_database):
        """Test that non-host cannot kick players."""
        service = GameService(db_database)
        game = await service.create_game()

        tiles = [TileCreate(type=TileType.PROPERTY, name=f"Property {i}") for i in range(5)]
        player1 = await service.join_game(game.id, "Player 1", tiles)
        player2 = await service.join_game(game.id, "Player 2", tiles)

        # Player 2 tries to kick player 1
        with pytest.raises(ValueError, match="Only the host can kick"):
            await service.kick_player(game.id, player2.id, player1.id)

    @pytest.mark.asyncio
    async def test_kick_player_after_start(self, db_database):
        """Test cannot kick after game started."""
        service = GameService(db_database)
        game = await service.create_game()

        tiles = [TileCreate(type=TileType.PROPERTY, name=f"Property {i}") for i in range(5)]
        player1 = await service.join_game(game.id, "Player 1", tiles)
        player2 = await service.join_game(game.id, "Player 2", tiles)
        await service.toggle_ready(game.id, player1.id)
        await service.toggle_ready(game.id, player2.id)

        # Game auto-starts when all ready
        with pytest.raises(ValueError, match="Cannot kick players after game has started"):
            await service.kick_player(game.id, player1.id, player2.id)

    @pytest.mark.asyncio
    async def test_kick_self_fails(self, db_database):
        """Test host cannot kick themselves."""
        service = GameService(db_database)
        game = await service.create_game()

        tiles = [TileCreate(type=TileType.PROPERTY, name=f"Property {i}") for i in range(5)]
        player1 = await service.join_game(game.id, "Player 1", tiles)

        with pytest.raises(ValueError, match="Cannot kick yourself"):
            await service.kick_player(game.id, player1.id, player1.id)

    @pytest.mark.asyncio
    async def test_toggle_ready_auto_start(self, db_database):
        """Test that game auto-starts when all players are ready."""
        service = GameService(db_database)
        game = await service.create_game()

        tiles = [TileCreate(type=TileType.PROPERTY, name=f"Property {i}") for i in range(5)]
        player1 = await service.join_game(game.id, "Player 1", tiles)
        player2 = await service.join_game(game.id, "Player 2", tiles)

        # Player 1 turns key
        result1 = await service.toggle_ready(game.id, player1.id)
        assert result1["ready"] is True
        assert result1["game_started"] is False

        # Player 2 turns key - should auto-start
        result2 = await service.toggle_ready(game.id, player2.id)
        assert result2["ready"] is True
        assert result2["game_started"] is True

        # Verify game started
        game_state = await service.get_game(game.id)
        assert game_state.status == GameStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_toggle_ready_not_in_lobby(self, db_database):
        """Test cannot toggle ready after game started."""
        service = GameService(db_database)
        game = await service.create_game()

        tiles = [TileCreate(type=TileType.PROPERTY, name=f"Property {i}") for i in range(5)]
        player1 = await service.join_game(game.id, "Player 1", tiles)
        player2 = await service.join_game(game.id, "Player 2", tiles)
        await service.toggle_ready(game.id, player1.id)
        await service.toggle_ready(game.id, player2.id)

        # Game is now active
        with pytest.raises(ValueError, match="Game already started"):
            await service.toggle_ready(game.id, player1.id)

    @pytest.mark.asyncio
    async def test_toggle_ready_player_not_found(self, db_database):
        """Test toggle ready with invalid player."""
        service = GameService(db_database)
        game = await service.create_game()

        tiles = [TileCreate(type=TileType.PROPERTY, name=f"Property {i}") for i in range(5)]
        await service.join_game(game.id, "Player 1", tiles)

        with pytest.raises(ValueError, match="Player not in this game"):
            await service.toggle_ready(game.id, "invalid-player-id")

    @pytest.mark.asyncio
    async def test_cpu_players_added_when_needed(self, db_database):
        """Test CPU players are added when only one player."""
        service = GameService(db_database)
        game = await service.create_game()

        tiles = [TileCreate(type=TileType.PROPERTY, name=f"Property {i}") for i in range(5)]
        player1 = await service.join_game(game.id, "Player 1", tiles)

        # Add CPU players to reach 2
        await service.add_cpu_players(game.id, target_count=2)

        game_state = await service.get_game(game.id)
        assert len(game_state.players) == 2
        # Check using the proper CPU detection method
        assert any(service._is_cpu_player(p) for p in game_state.players)

    @pytest.mark.asyncio
    async def test_pass_property_action(self, db_database):
        """Test passing on property purchase."""
        service = GameService(db_database)
        game = await service.create_game()

        tiles = [TileCreate(type=TileType.PROPERTY, name=f"Property {i}") for i in range(5)]
        player1 = await service.join_game(game.id, "Player 1", tiles)
        player2 = await service.join_game(game.id, "Player 2", tiles)

        # Disable auctions for this test
        game = await service.get_game(game.id)
        game.settings.enable_auctions = False
        await service.repository.update(game)

        await service.toggle_ready(game.id, player1.id)
        await service.toggle_ready(game.id, player2.id)

        # Roll until we hit a property (DECISION phase)
        for _ in range(20):  # Try up to 20 times
            await service.perform_action(game.id, player1.id, ActionType.ROLL_DICE, {})
            game_state = await service.get_game(game.id)
            if game_state.turn_phase == TurnPhase.DECISION:
                break
            if game_state.turn_phase == TurnPhase.POST_TURN:
                await service.perform_action(game.id, player1.id, ActionType.END_TURN, {})
                game_state = await service.get_game(game.id)
                if game_state.current_turn_player_id == player1.id:
                    continue
                await service.perform_action(game.id, player2.id, ActionType.ROLL_DICE, {})
                game_state = await service.get_game(game.id)
                if game_state.turn_phase == TurnPhase.DECISION:
                    player1 = player2  # Switch to current player
                    break
                if game_state.turn_phase == TurnPhase.POST_TURN:
                    await service.perform_action(game.id, player2.id, ActionType.END_TURN, {})

        # If we're in DECISION phase, test passing
        game_state = await service.get_game(game.id)
        if game_state.turn_phase == TurnPhase.DECISION:
            current_player_id = game_state.current_turn_player_id
            result = await service.perform_action(
                game.id, current_player_id, ActionType.PASS_PROPERTY, {}
            )
            assert result.success is True
            # Message can be "Passed on decision" or "Auction started" depending on settings
            assert "Passed" in result.message or "Auction" in result.message
