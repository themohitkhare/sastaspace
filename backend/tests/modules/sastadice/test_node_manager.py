"""Tests for NodeManager."""

import pytest

from app.modules.sastadice.schemas import GameSession, Player, Tile, TileType
from app.modules.sastadice.services.node_manager import NodeManager


@pytest.fixture
def sample_game():
    """Create a sample game session."""
    from app.modules.sastadice.schemas import GameSettings

    game = GameSession(
        id="test-game",
        players=[],
        board=[],
        settings=GameSettings(),
    )
    return game


@pytest.fixture
def sample_player():
    """Create a sample player."""
    return Player(id="player1", name="TestPlayer", cash=1000)


def test_calculate_node_rent_no_nodes(sample_game, sample_player):
    """Test node rent calculation with 0 nodes."""
    rent = NodeManager.calculate_node_rent(sample_player, sample_game)
    assert rent == 0


def test_calculate_node_rent_one_node(sample_game, sample_player):
    """Test node rent calculation with 1 node."""
    node = Tile(
        id="node1",
        type=TileType.NODE,
        name="NODE_ALPHA",
        owner_id=sample_player.id,
        price=200,
    )
    sample_game.board = [node]
    rent = NodeManager.calculate_node_rent(sample_player, sample_game)
    assert rent == 50  # $50 * 2^(1-1) = $50


def test_calculate_node_rent_two_nodes(sample_game, sample_player):
    """Test node rent calculation with 2 nodes."""
    node1 = Tile(id="node1", type=TileType.NODE, name="NODE_ALPHA", owner_id=sample_player.id)
    node2 = Tile(id="node2", type=TileType.NODE, name="NODE_BETA", owner_id=sample_player.id)
    sample_game.board = [node1, node2]
    rent = NodeManager.calculate_node_rent(sample_player, sample_game)
    assert rent == 100  # $50 * 2^(2-1) = $100


def test_calculate_node_rent_three_nodes(sample_game, sample_player):
    """Test node rent calculation with 3 nodes."""
    nodes = [
        Tile(
            id=f"node{i}",
            type=TileType.NODE,
            name=f"NODE_{i}",
            owner_id=sample_player.id,
        )
        for i in range(3)
    ]
    sample_game.board = nodes
    rent = NodeManager.calculate_node_rent(sample_player, sample_game)
    assert rent == 200  # $50 * 2^(3-1) = $200


def test_calculate_node_rent_four_nodes(sample_game, sample_player):
    """Test node rent calculation with 4 nodes."""
    nodes = [
        Tile(
            id=f"node{i}",
            type=TileType.NODE,
            name=f"NODE_{i}",
            owner_id=sample_player.id,
        )
        for i in range(4)
    ]
    sample_game.board = nodes
    rent = NodeManager.calculate_node_rent(sample_player, sample_game)
    assert rent == 400  # $50 * 2^(4-1) = $400


def test_calculate_node_rent_with_rent_multiplier(sample_game, sample_player):
    """Test node rent respects rent_multiplier from events."""
    nodes = [
        Tile(
            id=f"node{i}",
            type=TileType.NODE,
            name=f"NODE_{i}",
            owner_id=sample_player.id,
        )
        for i in range(2)
    ]
    sample_game.board = nodes
    sample_game.rent_multiplier = 0.5  # Market Crash
    rent = NodeManager.calculate_node_rent(sample_player, sample_game)
    assert rent == 50  # $100 * 0.5 = $50

    sample_game.rent_multiplier = 1.5  # Bull Market
    rent = NodeManager.calculate_node_rent(sample_player, sample_game)
    assert rent == 150  # $100 * 1.5 = $150
