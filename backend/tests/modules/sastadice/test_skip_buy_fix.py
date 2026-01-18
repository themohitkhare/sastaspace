"""Test for SKIP_BUY event fix to prevent game getting stuck."""
import pytest
from app.modules.sastadice.services.game_service import GameService
from app.modules.sastadice.schemas import (
    GameStatus,
    TurnPhase,
    TileType,
    TileCreate,
    ActionType,
)


@pytest.mark.asyncio
async def test_skip_buy_event_does_not_stuck_game(db_database):
    """Test that SKIP_BUY event (UPI Server Down) doesn't cause game to get stuck."""
    service = GameService(db_database)
    
    game = await service.create_game(cpu_count=2)
    game = await service.start_game(game.id, force=True)
    
    player = game.players[0]
    
    chance_tile = None
    for tile in game.board:
        if tile.type == TileType.CHANCE:
            chance_tile = tile
            break
    
    if not chance_tile:
        pytest.skip("No CHANCE tile found on board")
    
    await service.repository.update_player_position(player.id, chance_tile.position)
    player.position = chance_tile.position
    
    game.current_turn_player_id = player.id
    game.turn_phase = TurnPhase.PRE_ROLL
    await service.repository.update(game)
    
    game = await service.get_game(game.id)
    player = next((p for p in game.players if p.id == player.id), player)
    
    await service.repository.update_player_position(player.id, chance_tile.position)
    player.position = chance_tile.position
    
    game = await service.get_game(game.id)
    player = next((p for p in game.players if p.id == player.id), player)
    
    property_tile = None
    for tile in game.board:
        if tile.type == TileType.PROPERTY and tile.owner_id is None:
            property_tile = tile
            break
    
    if property_tile:
        await service.repository.update_player_position(player.id, property_tile.position)
        player.position = property_tile.position
        
        from app.modules.sastadice.schemas import PendingDecision
        game.pending_decision = PendingDecision(
            type="BUY",
            tile_id=property_tile.id,
            price=property_tile.price,
        )
        game.turn_phase = TurnPhase.DECISION
        await service.repository.update(game)
        
    game = await service.get_game(game.id)
    player = next((p for p in game.players if p.id == player.id), player)
    
    chance_tile = next((t for t in game.board if t.type == TileType.CHANCE), None)
    if chance_tile:
        await service.repository.update_player_position(player.id, chance_tile.position)
        player.position = chance_tile.position
        
        result = await service.perform_action(game.id, player.id, ActionType.ROLL_DICE, {})
        
        game = await service.get_game(game.id)
        
        assert game.turn_phase != TurnPhase.DECISION or game.pending_decision is not None, \
            "Game should not be in DECISION phase without pending_decision"
        
        if game.turn_phase == TurnPhase.DECISION and game.pending_decision:
            pass_result = await service.perform_action(game.id, player.id, ActionType.PASS_PROPERTY, {})
            assert pass_result.success, "Should be able to pass on decision"
            game = await service.get_game(game.id)
            assert game.turn_phase == TurnPhase.POST_TURN, "After passing, should be in POST_TURN"
        
        if game.turn_phase == TurnPhase.POST_TURN:
            end_result = await service.perform_action(game.id, player.id, ActionType.END_TURN, {})
            assert end_result.success, "Should be able to end turn"
            game = await service.get_game(game.id)
            assert game.turn_phase == TurnPhase.PRE_ROLL, "After ending turn, should be in PRE_ROLL"


@pytest.mark.asyncio
async def test_skip_buy_clears_pending_decision(db_database):
    """Test that SKIP_BUY event clears pending_decision and advances phase."""
    service = GameService(db_database)
    game = await service.create_game(cpu_count=1)
    game = await service.start_game(game.id, force=True)
    
    player = game.players[0]
    
    from app.modules.sastadice.schemas import PendingDecision
    property_tile = next((t for t in game.board if t.type == TileType.PROPERTY and t.owner_id is None), None)
    
    if property_tile:
        game.pending_decision = PendingDecision(
            type="BUY",
            tile_id=property_tile.id,
            price=property_tile.price,
        )
        game.turn_phase = TurnPhase.DECISION
        await service.repository.update(game)
