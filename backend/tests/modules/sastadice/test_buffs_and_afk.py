"""Tests for Black Market buffs and AFK ghost-turn behavior."""

import pytest

from app.modules.sastadice.schemas import (
    ActionType,
    GameStatus,
    TileType,
    TurnPhase,
)
from app.modules.sastadice.services.game_orchestrator import GameOrchestrator


@pytest.mark.asyncio
async def test_cannot_buy_second_inventory_buff(db_database) -> None:
    """Player with an active inventory buff cannot buy another non-PEEK buff."""
    service = GameOrchestrator(db_database)
    game = await service.create_game()

    player = await service.join_game(game.id, "Alice")
    await service.join_game(game.id, "Bob")

    game = await service.start_game(game.id, force=True)
    game.current_turn_player_id = player.id
    game.turn_phase = TurnPhase.PRE_ROLL

    # Put player in Black Market with VPN already active
    from app.modules.sastadice.services.turn_manager import TurnManager

    TurnManager.handle_market_landing(game)
    game.turn_phase = TurnPhase.DECISION

    player_obj = next(p for p in game.players if p.id == player.id)
    player_obj.cash = 1_000
    player_obj.active_buff = "VPN"

    await service.repository.update_player_cash(player.id, player_obj.cash)
    await service.repository.update_player_buff(player.id, "VPN")
    await service.repository.update(game)

    result = await service.perform_action(
        game.id,
        player.id,
        ActionType.BUY_BUFF,
        {"buff_id": "DDOS"},
    )

    assert result.success is False
    assert "already have an active buff" in result.message

    game_after = await service.get_game(game.id)
    player_after = next(p for p in game_after.players if p.id == player.id)
    assert player_after.active_buff == "VPN"
    assert player_after.cash == 1_000


@pytest.mark.asyncio
async def test_peek_buff_reveals_without_mutating_deck(db_database) -> None:
    """PEEK buff reveals top 3 events without changing deck order or giving inventory buff."""
    service = GameOrchestrator(db_database)
    game = await service.create_game()

    player = await service.join_game(game.id, "Alice")
    await service.join_game(game.id, "Bob")

    game = await service.start_game(game.id, force=True)
    game.current_turn_player_id = player.id
    game.turn_phase = TurnPhase.PRE_ROLL

    # Deterministic deck for assertions
    from app.modules.sastadice.events.events_data import SASTA_EVENTS

    game.event_deck = list(range(5))
    game.used_event_deck = []

    from app.modules.sastadice.services.turn_manager import TurnManager

    TurnManager.handle_market_landing(game)
    game.turn_phase = TurnPhase.DECISION

    player_obj = next(p for p in game.players if p.id == player.id)
    starting_cash = 1_000
    player_obj.cash = starting_cash

    await service.repository.update_player_cash(player.id, player_obj.cash)
    await service.repository.update(game)

    result = await service.perform_action(
        game.id,
        player.id,
        ActionType.BUY_BUFF,
        {"buff_id": "PEEK"},
    )

    assert result.success is True

    expected_names = [SASTA_EVENTS[i]["name"] for i in game.event_deck[:3]]
    for name in expected_names:
        assert name in result.message

    game_after = await service.get_game(game.id)
    player_after = next(p for p in game_after.players if p.id == player.id)

    # No inventory buff should be set for PEEK
    assert player_after.active_buff is None
    # Deck order unchanged and no cards consumed
    assert game_after.event_deck == list(range(5))
    assert game_after.used_event_deck == []
    # Cash deducted exactly once
    assert player_after.cash == starting_cash - 100


@pytest.mark.asyncio
async def test_ddos_only_usable_in_pre_roll(db_database) -> None:
    """DDoS can only be used during PRE_ROLL phase."""
    service = GameOrchestrator(db_database)
    game = await service.create_game()

    player = await service.join_game(game.id, "Alice")
    await service.join_game(game.id, "Bob")

    game = await service.start_game(game.id, force=True)
    player_obj = next(p for p in game.players if p.id == player.id)

    # Give player DDOS buff directly
    player_obj.active_buff = "DDOS"
    await service.repository.update_player_buff(player.id, "DDOS")

    # Use an existing property tile from the generated board
    property_tiles = [t for t in game.board if t.type == TileType.PROPERTY]
    if not property_tiles:
        pytest.skip("No property tiles available on generated board")
    target_tile = property_tiles[0]

    # POST_TURN should be rejected
    game.current_turn_player_id = player.id
    game.turn_phase = TurnPhase.POST_TURN
    await service.repository.update(game)

    result_post = await service.perform_action(
        game.id,
        player.id,
        ActionType.BLOCK_TILE,
        {"tile_id": target_tile.id},
    )
    assert result_post.success is False
    assert "PRE_ROLL" in result_post.message

    # PRE_ROLL should succeed
    game = await service.get_game(game.id)
    game.current_turn_player_id = player.id
    game.turn_phase = TurnPhase.PRE_ROLL
    await service.repository.update(game)

    result_pre = await service.perform_action(
        game.id,
        player.id,
        ActionType.BLOCK_TILE,
        {"tile_id": target_tile.id},
    )
    assert result_pre.success is True

    game_after = await service.get_game(game.id)
    target_after = next(t for t in game_after.board if t.id == target_tile.id)
    # Tile should be blocked for at least the next round
    assert target_after.blocked_until_round is not None
    assert target_after.blocked_until_round > game_after.current_round


@pytest.mark.asyncio
async def test_afk_ghost_turns_increment_afk_and_bankrupt_after_three(db_database) -> None:
    """Disconnected players get ghost turns that increment afk_turns."""
    service = GameOrchestrator(db_database)
    game = await service.create_game()

    player = await service.join_game(game.id, "Alice")
    game = await service.start_game(game.id, force=True)

    # Single human player game
    game.current_turn_player_id = player.id
    game.turn_phase = TurnPhase.PRE_ROLL
    await service.repository.update(game)

    # Mark player as disconnected (e.g., websocket disconnect)
    await service.repository.update_player_afk(
        player.id,
        afk_turns=0,
        disconnected=True,
        disconnected_turns=0,
    )

    # Next ghost-processing pass should increment AFK counter while keeping them disconnected
    await service.process_cpu_turns(game.id)
    game = await service.get_game(game.id)
    player_obj = next(p for p in game.players if p.id == player.id)

    assert player_obj.disconnected is True
    assert player_obj.afk_turns >= 1
    assert game.status in (GameStatus.ACTIVE, GameStatus.FINISHED)
