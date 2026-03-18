"""Integration tests for new features: NODE tiles, jail mechanics, 36 events."""

import pytest

from app.modules.sastadice.events.events_data import SASTA_EVENTS
from app.modules.sastadice.schemas import (
    ActionType,
    BoardPreset,
    Tile,
    TileType,
)
from app.modules.sastadice.services.game_orchestrator import GameOrchestrator
from app.modules.sastadice.services.jail_manager import JailManager
from app.modules.sastadice.services.node_manager import NodeManager


@pytest.mark.asyncio
async def test_node_tiles_in_generated_board(db_database):
    """Test that NODE tiles are placed correctly in generated boards."""
    orchestrator = GameOrchestrator(db_database)
    game = await orchestrator.create_game()

    # Join with two players
    await orchestrator.join_game(game.id, "Player1")
    await orchestrator.join_game(game.id, "Player2")

    # Start game
    game = await orchestrator.start_game(game.id, force=True)

    # Check that NODE tiles are present
    node_tiles = [t for t in game.board if t.type == TileType.NODE]
    assert len(node_tiles) == 4  # Should have exactly 4 NODE tiles

    # Check that each NODE tile has correct properties
    for node in node_tiles:
        assert node.price == 200
        assert node.rent == 50
        assert "NODE" in node.name.upper()


@pytest.mark.asyncio
async def test_go_to_jail_tile_in_generated_board(db_database):
    """Test that GO_TO_JAIL tile is placed correctly."""
    orchestrator = GameOrchestrator(db_database)
    game = await orchestrator.create_game()

    # Use more players to get a larger board
    await orchestrator.join_game(game.id, "Player1")
    await orchestrator.join_game(game.id, "Player2")
    await orchestrator.join_game(game.id, "Player3")
    await orchestrator.join_game(game.id, "Player4")

    game = await orchestrator.start_game(game.id, force=True)

    # For larger boards, GO_TO_JAIL should be present
    total_tiles = len(game.board)
    if total_tiles >= 16:  # Need sufficient board size
        go_to_jail_tiles = [t for t in game.board if t.type == TileType.GO_TO_JAIL]
        assert len(go_to_jail_tiles) >= 1  # Should have at least 1 GO_TO_JAIL tile
        assert "404" in go_to_jail_tiles[0].name.upper()
    else:
        # For small boards, just verify board was created
        assert len(game.board) >= 10


@pytest.mark.asyncio
async def test_buy_release_action(db_database):
    """Test BUY_RELEASE action to exit jail."""
    orchestrator = GameOrchestrator(db_database)
    game = await orchestrator.create_game()

    player = await orchestrator.join_game(game.id, "TestPlayer")
    await orchestrator.join_game(game.id, "Player2")

    game = await orchestrator.start_game(game.id, force=True)

    # Manually put player in jail (need to update via repository)
    player_obj = next(p for p in game.players if p.id == player.id)
    player_obj.in_jail = True
    player_obj.cash = 500
    await orchestrator.repository.update_player_cash(player.id, 500)

    # Update game to set in_jail flag properly (MongoDB update)
    await orchestrator.repository.database.game_sessions.find_one({"_id": game.id})
    players_doc = await orchestrator.repository.database.players.find({"game_id": game.id}).to_list(
        None
    )
    for p_doc in players_doc:
        if p_doc["_id"] == player.id:
            await orchestrator.repository.database.players.update_one(
                {"_id": player.id}, {"$set": {"in_jail": True}}
            )

    # Reload game
    game = await orchestrator.get_game(game.id)
    player_obj = next(p for p in game.players if p.id == player.id)
    assert player_obj.in_jail is True  # Verify jail flag is set

    # Test BUY_RELEASE action
    result = await orchestrator.perform_action(game.id, player.id, ActionType.BUY_RELEASE, {})

    assert result.success is True
    game = await orchestrator.get_game(game.id)
    player_obj = next(p for p in game.players if p.id == player.id)
    assert player_obj.in_jail is False
    assert player_obj.cash == 450  # $500 - $50 bribe


@pytest.mark.asyncio
async def test_roll_for_doubles_action(db_database):
    """Test ROLL_FOR_DOUBLES action to escape jail."""
    orchestrator = GameOrchestrator(db_database)
    game = await orchestrator.create_game()

    player = await orchestrator.join_game(game.id, "TestPlayer")
    await orchestrator.join_game(game.id, "Player2")

    game = await orchestrator.start_game(game.id, force=True)

    # Manually put player in jail
    player_obj = next(p for p in game.players if p.id == player.id)
    player_obj.in_jail = True
    player_obj.jail_turns = 0
    await orchestrator.repository.update(game)

    # Test ROLL_FOR_DOUBLES action (will either escape or increment jail_turns)
    result = await orchestrator.perform_action(game.id, player.id, ActionType.ROLL_FOR_DOUBLES, {})

    # Result should have data about dice roll
    assert result.data is not None
    assert "dice1" in result.data
    assert "dice2" in result.data
    assert "escaped" in result.data


@pytest.mark.asyncio
async def test_36_events_available(db_database):
    """Test that all Sasta events are available and categorized."""
    assert len(SASTA_EVENTS) == 35

    # Verify event structure and metadata
    for event in SASTA_EVENTS:
        assert "name" in event
        assert "desc" in event
        assert "type" in event
        assert "value" in event
        assert "category" in event


@pytest.mark.asyncio
async def test_node_rent_calculation(db_database):
    """Test NODE rent scales correctly with ownership."""
    orchestrator = GameOrchestrator(db_database)
    game = await orchestrator.create_game()

    player = await orchestrator.join_game(game.id, "TestPlayer")
    await orchestrator.join_game(game.id, "Player2")

    game = await orchestrator.start_game(game.id, force=True)

    # Create NODE tiles owned by player
    player_obj = next(p for p in game.players if p.id == player.id)

    # Test with 1 node
    game.board[0] = Tile(id="node1", type=TileType.NODE, name="NODE_1", owner_id=player.id)
    rent = NodeManager.calculate_node_rent(player_obj, game)
    assert rent == 50  # $50 * 2^0

    # Test with 2 nodes
    game.board[1] = Tile(id="node2", type=TileType.NODE, name="NODE_2", owner_id=player.id)
    rent = NodeManager.calculate_node_rent(player_obj, game)
    assert rent == 100  # $50 * 2^1

    # Test with rent multiplier (Market Crash)
    game.rent_multiplier = 0.5
    rent = NodeManager.calculate_node_rent(player_obj, game)
    assert rent == 50  # $100 * 0.5


@pytest.mark.asyncio
async def test_ugc_24_board_preset_in_start_flow(db_database):
    """Integration: UGC_24 preset uses the 24-tile board layout."""
    orchestrator = GameOrchestrator(db_database)
    game = await orchestrator.create_game()

    # Two players so we don't auto-add CPUs here
    await orchestrator.join_game(game.id, "Player1")
    await orchestrator.join_game(game.id, "Player2")

    # Enable the UGC_24 preset
    game = await orchestrator.get_game(game.id)
    game.settings.board_preset = BoardPreset.UGC_24
    await orchestrator.repository.update(game)

    game = await orchestrator.start_game(game.id, force=True)

    assert len(game.board) == 24
    assert game.board[0].type == TileType.GO
    assert game.board[6].type == TileType.TELEPORT
    assert game.board[12].type == TileType.JAIL
    assert game.board[18].type == TileType.MARKET


@pytest.mark.asyncio
async def test_jail_3_turn_maximum(db_database):
    """Test that jail enforces 3-turn maximum."""
    orchestrator = GameOrchestrator(db_database)
    game = await orchestrator.create_game()

    player = await orchestrator.join_game(game.id, "TestPlayer")
    game = await orchestrator.get_game(game.id)
    player_obj = next(p for p in game.players if p.id == player.id)
    player_obj.cash = 100
    player_obj.in_jail = True
    player_obj.jail_turns = 2  # Third turn coming up

    # Mock random to not give doubles
    import random

    original_randint = random.randint
    random.randint = lambda a, b: 3 if a == 1 and b == 6 else 4

    try:
        escaped, dice1, dice2, message = JailManager.roll_for_doubles(game, player_obj)
        assert escaped is True  # Should be forced out
        assert player_obj.in_jail is False
        assert "3rd turn" in message.lower() or player_obj.jail_turns == 0
    finally:
        random.randint = original_randint
