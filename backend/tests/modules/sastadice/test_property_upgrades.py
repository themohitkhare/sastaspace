from unittest.mock import AsyncMock

import pytest

from app.modules.sastadice.schemas import (
    GameSession,
    Player,
    Tile,
    TileType,
)
from app.modules.sastadice.services.game_service import GameService


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.update = AsyncMock()
    repo.update_player_cash = AsyncMock()
    repo.update_player_properties = AsyncMock()
    repo.save_board = AsyncMock()
    repo.update_tile_owner = AsyncMock()
    return repo


@pytest.fixture
def game_service(mock_repo):
    # GameService expects a database in init, but we want to inject our mock repo
    # So we pass a dummy db and then overwrite the repository attribute
    mock_db = AsyncMock()
    service = GameService(database=mock_db)
    service.repository = mock_repo
    return service


@pytest.mark.asyncio
async def test_upgrade_property_success(game_service):
    # Setup: Player owns full set of RED properties
    player = Player(id="p1", name="Test", cash=1000)

    prop1 = Tile(
        id="t1",
        name="Red1",
        type=TileType.PROPERTY,
        color="RED",
        price=100,
        owner_id="p1",
        upgrade_level=0,
    )
    prop2 = Tile(
        id="t2",
        name="Red2",
        type=TileType.PROPERTY,
        color="RED",
        price=100,
        owner_id="p1",
        upgrade_level=0,
    )

    game = GameSession(id="g1", players=[player], board=[prop1, prop2])

    # Test: Upgrade Red1 to Level 1
    # Cost should be base price (100)
    payload = {"tile_id": "t1"}

    result = await game_service._handle_upgrade(game, "p1", payload)

    assert result.success is True
    assert prop1.upgrade_level == 1
    assert player.cash == 900  # 1000 - 100
    assert "SCRIPT KIDDIE" in result.message


@pytest.mark.asyncio
async def test_upgrade_property_level_2(game_service):
    player = Player(id="p1", name="Test", cash=1000)

    prop1 = Tile(
        id="t1",
        name="Red1",
        type=TileType.PROPERTY,
        color="RED",
        price=100,
        owner_id="p1",
        upgrade_level=1,
    )
    prop2 = Tile(
        id="t2",
        name="Red2",
        type=TileType.PROPERTY,
        color="RED",
        price=100,
        owner_id="p1",
        upgrade_level=0,
    )

    game = GameSession(id="g1", players=[player], board=[prop1, prop2])

    # Test: Upgrade Red1 from Level 1 to 2
    # Cost should be base price * 2 (200)
    payload = {"tile_id": "t1"}

    result = await game_service._handle_upgrade(game, "p1", payload)

    assert result.success is True
    assert prop1.upgrade_level == 2
    assert player.cash == 800  # 1000 - 200
    assert "1337 HAXXOR" in result.message


@pytest.mark.asyncio
async def test_upgrade_fail_not_full_set(game_service):
    player = Player(id="p1", name="Test", cash=1000)

    prop1 = Tile(
        id="t1", name="Red1", type=TileType.PROPERTY, color="RED", price=100, owner_id="p1"
    )
    prop2 = Tile(
        id="t2", name="Red2", type=TileType.PROPERTY, color="RED", price=100, owner_id="p2"
    )  # Owned by other

    game = GameSession(id="g1", players=[player], board=[prop1, prop2])

    payload = {"tile_id": "t1"}
    result = await game_service._handle_upgrade(game, "p1", payload)

    assert result.success is False
    assert "must own the full color set" in result.message


@pytest.mark.asyncio
async def test_upgrade_fail_insufficient_funds(game_service):
    player = Player(id="p1", name="Test", cash=50)  # Not enough for 100 cost

    prop1 = Tile(
        id="t1", name="Red1", type=TileType.PROPERTY, color="RED", price=100, owner_id="p1"
    )
    prop2 = Tile(
        id="t2", name="Red2", type=TileType.PROPERTY, color="RED", price=100, owner_id="p1"
    )

    game = GameSession(id="g1", players=[player], board=[prop1, prop2])

    payload = {"tile_id": "t1"}
    result = await game_service._handle_upgrade(game, "p1", payload)

    assert result.success is False
    assert "Insufficient funds" in result.message


@pytest.mark.asyncio
async def test_downgrade_property(game_service):
    player = Player(id="p1", name="Test", cash=1000)

    # Level 2 property costs 100 (level 1 cost) + 200 (level 2 cost) = 300 total invested in upgrades
    # Original logic says refund is 50% of the cost of the *current* level being removed
    # Removing Level 2 (cost 200) -> refund 100
    prop1 = Tile(
        id="t1",
        name="Red1",
        type=TileType.PROPERTY,
        color="RED",
        price=100,
        owner_id="p1",
        upgrade_level=2,
    )
    prop2 = Tile(
        id="t2",
        name="Red2",
        type=TileType.PROPERTY,
        color="RED",
        price=100,
        owner_id="p1",
        upgrade_level=0,
    )

    game = GameSession(id="g1", players=[player], board=[prop1, prop2])

    payload = {"tile_id": "t1"}
    result = await game_service._handle_downgrade(game, "p1", payload)

    assert result.success is True
    assert prop1.upgrade_level == 1
    assert player.cash == 1100  # 1000 + 100 refund
    assert "Sold upgrade" in result.message


@pytest.mark.asyncio
async def test_downgrade_fail_no_upgrades(game_service):
    player = Player(id="p1", name="Test", cash=1000)

    prop1 = Tile(
        id="t1",
        name="Red1",
        type=TileType.PROPERTY,
        color="RED",
        price=100,
        owner_id="p1",
        upgrade_level=0,
    )

    game = GameSession(id="g1", players=[player], board=[prop1])

    payload = {"tile_id": "t1"}
    result = await game_service._handle_downgrade(game, "p1", payload)

    assert result.success is False
    assert "No upgrades to sell" in result.message
