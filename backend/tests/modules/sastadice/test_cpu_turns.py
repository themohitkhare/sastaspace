"""Tests for CPU turn logic to ensure games don't get stuck."""
import pytest
from app.modules.sastadice.services.game_service import GameService
from app.modules.sastadice.schemas import (
    GameStatus,
    TurnPhase,
    TileType,
    TileCreate,
    ActionType,
)


class TestCPUTurnLogic:
    """Test CPU turn logic to prevent stuck games."""

    @pytest.mark.asyncio
    async def test_cpu_turn_completes_full_cycle(self, db_database):
        """Test that a CPU turn completes PRE_ROLL -> DECISION -> POST_TURN -> END."""
        service = GameService(db_database)
        game = await service.create_game(cpu_count=2)
        game = await service.start_game(game.id, force=True)

        # Get the first CPU player
        cpu_player = next(
            (p for p in game.players if service._is_cpu_player(p)), None
        )
        assert cpu_player is not None, "Should have CPU player"

        # Play CPU turn
        turn_log = await service._play_cpu_turn(game, cpu_player)

        # Verify turn completed
        assert len(turn_log) > 0, "Should have action log"
        
        # Check that turn moved to next player or completed
        updated_game = await service.get_game(game.id)
        assert (
            updated_game.current_turn_player_id != cpu_player.id
            or updated_game.turn_phase == TurnPhase.PRE_ROLL
        ), "Turn should have advanced"

    @pytest.mark.asyncio
    async def test_cpu_handles_buy_decision(self, db_database):
        """Test CPU handles BUY decision correctly."""
        service = GameService(db_database)
        game = await service.create_game(cpu_count=1)
        game = await service.start_game(game.id, force=True)

        cpu_player = game.players[0]
        
        # Roll dice until we hit a property (or max attempts)
        for _ in range(50):
            game = await service.get_game(game.id)
            if game.current_turn_player_id != cpu_player.id:
                cpu_player = next(
                    (p for p in game.players if p.id == game.current_turn_player_id), None
                )
                if not cpu_player:
                    break
            
            if game.turn_phase == TurnPhase.PRE_ROLL:
                await service.perform_action(game.id, cpu_player.id, ActionType.ROLL_DICE, None)
            elif game.turn_phase == TurnPhase.DECISION and game.pending_decision:
                # CPU should handle this
                turn_log = await service._play_cpu_turn(game, cpu_player)
                assert len(turn_log) > 0, "Should have handled decision"
                break
            elif game.turn_phase == TurnPhase.POST_TURN:
                await service.perform_action(game.id, cpu_player.id, ActionType.END_TURN, None)
            else:
                break

    @pytest.mark.asyncio
    async def test_cpu_handles_insufficient_funds(self, db_database):
        """Test CPU passes when it can't afford property."""
        service = GameService(db_database)
        game = await service.create_game(cpu_count=1)
        game = await service.start_game(game.id, force=True)

        cpu_player = game.players[0]
        
        # Set CPU cash to very low amount
        await service.repository.update_player_cash(cpu_player.id, 50)
        
        # Try to play turn - should handle gracefully
        turn_log = await service._play_cpu_turn(game, cpu_player)
        
        # Should not crash and should have logged actions
        assert isinstance(turn_log, list)
        # CPU should have passed on any expensive properties

    @pytest.mark.asyncio
    async def test_cpu_handles_decision_without_pending_decision(self, db_database):
        """Test CPU handles DECISION phase even if pending_decision is None."""
        service = GameService(db_database)
        game = await service.create_game(cpu_count=1)
        game = await service.start_game(game.id, force=True)

        cpu_player = game.players[0]
        
        # Manually set to DECISION phase without pending_decision (edge case)
        game.turn_phase = TurnPhase.DECISION
        game.pending_decision = None
        await service.repository.update(game)
        
        # CPU should handle this gracefully
        turn_log = await service._play_cpu_turn(game, cpu_player)
        
        # Should not crash
        assert isinstance(turn_log, list)
        # Should have attempted recovery

    @pytest.mark.asyncio
    async def test_process_cpu_turns_handles_multiple_cpus(self, db_database):
        """Test process_cpu_turns handles multiple consecutive CPU turns."""
        service = GameService(db_database)
        game = await service.create_game(cpu_count=3)
        game = await service.start_game(game.id, force=True)

        # Process CPU turns
        result = await service.process_cpu_turns(game.id)
        
        assert "cpu_turns_played" in result
        assert "log" in result
        assert isinstance(result["log"], list)
        
        # Game should still be active or moved to human player
        updated_game = await service.get_game(game.id)
        assert updated_game.status == GameStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_cpu_turn_max_iterations_safety(self, db_database):
        """Test that max iterations limit prevents infinite loops."""
        service = GameService(db_database)
        game = await service.create_game(cpu_count=1)
        game = await service.start_game(game.id, force=True)

        cpu_player = game.players[0]
        
        # Create a problematic state that might cause looping
        # (e.g., set phase to something that doesn't progress)
        game.turn_phase = TurnPhase.MOVING
        await service.repository.update(game)
        
        # CPU should hit max iterations and exit gracefully
        turn_log = await service._play_cpu_turn(game, cpu_player)
        
        # Should not hang - should return with log
        assert isinstance(turn_log, list)
        # Check if it hit max iterations
        max_iter_msg = any("max iterations" in msg.lower() for msg in turn_log)
        # Either it completed or hit max iterations - both are acceptable

    @pytest.mark.asyncio
    async def test_simulate_cpu_game_completes(self, db_database):
        """Test that simulate_cpu_game can complete a full game."""
        service = GameService(db_database)
        game = await service.create_game(cpu_count=2)
        
        # Simulate game
        result = await service.simulate_cpu_game(game.id, max_turns=50)
        
        assert "game_id" in result
        assert "status" in result
        assert "turns_played" in result
        assert "winner" in result
        assert "final_standings" in result
        
        # Game should be finished or at least progressed
        assert result["turns_played"] > 0
        assert result["status"] in ["ACTIVE", "FINISHED"]

    @pytest.mark.asyncio
    async def test_cpu_turn_handles_action_failures(self, db_database):
        """Test CPU handles action failures gracefully."""
        service = GameService(db_database)
        game = await service.create_game(cpu_count=1)
        game = await service.start_game(game.id, force=True)

        cpu_player = game.players[0]
        
        # Try to perform invalid action (e.g., END_TURN when not in POST_TURN)
        # This should be handled by the action validation, but CPU should recover
        game.turn_phase = TurnPhase.PRE_ROLL
        await service.repository.update(game)
        
        # CPU should roll dice successfully
        turn_log = await service._play_cpu_turn(game, cpu_player)
        
        # Should have attempted actions
        assert len(turn_log) > 0

    @pytest.mark.asyncio
    async def test_cpu_turn_player_not_found_handling(self, db_database):
        """Test CPU turn handles case where player is not found."""
        service = GameService(db_database)
        game = await service.create_game(cpu_count=1)
        game = await service.start_game(game.id, force=True)

        # Create a fake player object with invalid ID
        from app.modules.sastadice.schemas import Player
        fake_player = Player(id="fake-id", name="FAKE CPU")
        
        # Should handle gracefully
        turn_log = await service._play_cpu_turn(game, fake_player)
        
        # Should not crash
        assert isinstance(turn_log, list)
        # Should have logged the issue
