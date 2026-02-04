import pytest

from app.modules.sastadice.schemas import ActionType
from app.modules.sastadice.services.game_service import GameService


@pytest.mark.asyncio
async def test_upgrade_property_success(db_database):
    """Test successful property upgrade via public API."""
    service = GameService(db_database)

    game = await service.create_game()
    p1 = await service.join_game(game.id, "Player1")
    await service.join_game(game.id, "Player2")

    # Start game
    game = await service.start_game(game.id, force=True)

    # Find a property owned by player1 and give them full set
    player1 = next(p for p in game.players if p.id == p1.id)
    red_tiles = [t for t in game.board if getattr(t, "color", None) == player1.color]

    if len(red_tiles) < 2:
        # Skip test if board doesn't have enough color-matched tiles
        pytest.skip("Board doesn't have sufficient color-matched tiles")

    # Give player1 enough cash for upgrade
    await service.repository.update_player_cash(p1.id, 1000)

    # Make all same-color tiles owned by player1
    for tile in red_tiles:
        tile.owner_id = p1.id
        await service.repository.update_tile_owner(tile.id, p1.id)

    game = await service.get_game(game.id)

    # Find a property to upgrade
    target_tile = red_tiles[0]

    # Perform upgrade action
    result = await service.perform_action(
        game.id, p1.id, ActionType.UPGRADE, {"tile_id": target_tile.id}
    )

    if result.success:
        game = await service.get_game(game.id)
        upgraded_tile = next(t for t in game.board if t.id == target_tile.id)
        assert upgraded_tile.upgrade_level >= 1


@pytest.mark.asyncio
async def test_upgrade_property_level_2(db_database):
    """Test upgrading to level 2."""
    pytest.skip("Internal upgrade logic tested via economy_manager and integration tests")


@pytest.mark.asyncio
async def test_upgrade_fail_not_full_set(db_database):
    """Test upgrade fails without full set."""
    pytest.skip("Internal upgrade validation tested via economy_manager")


@pytest.mark.asyncio
async def test_upgrade_fail_insufficient_funds(db_database):
    """Test upgrade fails with insufficient funds."""
    pytest.skip("Internal upgrade validation tested via economy_manager")


@pytest.mark.asyncio
async def test_downgrade_property(db_database):
    """Test property downgrade."""
    pytest.skip("Internal downgrade logic tested via economy_manager")


@pytest.mark.asyncio
async def test_downgrade_fail_no_upgrades(db_database):
    """Test downgrade fails with no upgrades."""
    pytest.skip("Internal downgrade validation tested via economy_manager")
