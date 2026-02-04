"""Tests for JailManager."""

import pytest

from app.modules.sastadice.schemas import GameSession, GameSettings, Player
from app.modules.sastadice.services.jail_manager import JailManager


@pytest.fixture
def sample_game():
    """Create a sample game session."""
    from app.modules.sastadice.schemas import Tile, TileType

    board = [
        Tile(
            id=f"tile{i}",
            type=TileType.NEUTRAL,
            name=f"Tile {i}",
            position=i,
        )
        for i in range(24)
    ]

    game = GameSession(
        id="test-game",
        players=[],
        board=board,
        settings=GameSettings(jail_bribe_cost=50, jail_turns_max=3),
    )
    return game


@pytest.fixture
def sample_player():
    """Create a sample player."""
    return Player(id="player1", name="TestPlayer", cash=1000, in_jail=False)


def test_send_to_jail(sample_game, sample_player):
    """Test sending player to jail."""
    JailManager.send_to_jail(sample_game, sample_player)
    assert sample_player.in_jail is True
    assert sample_player.jail_turns == 0
    assert sample_player.position == 12  # len(board) // 2
    assert sample_player.consecutive_doubles == 0


def test_attempt_bribe_release_not_in_jail(sample_game, sample_player):
    """Test bribe release when not in jail."""
    success, message = JailManager.attempt_bribe_release(sample_game, sample_player)
    assert success is False
    assert "not in jail" in message.lower()


def test_attempt_bribe_release_insufficient_funds(sample_game, sample_player):
    """Test bribe release with insufficient funds."""
    sample_player.in_jail = True
    sample_player.cash = 30  # Less than $50 bribe
    success, message = JailManager.attempt_bribe_release(sample_game, sample_player)
    assert success is False
    assert "not enough cash" in message.lower()


def test_attempt_bribe_release_success(sample_game, sample_player):
    """Test successful bribe release."""
    sample_player.in_jail = True
    sample_player.cash = 200
    initial_cash = sample_player.cash
    success, message = JailManager.attempt_bribe_release(sample_game, sample_player)
    assert success is True
    assert sample_player.in_jail is False
    assert sample_player.jail_turns == 0
    assert sample_player.cash == initial_cash - 50


def test_roll_for_doubles_not_in_jail(sample_game, sample_player):
    """Test roll for doubles when not in jail."""
    escaped, dice1, dice2, message = JailManager.roll_for_doubles(sample_game, sample_player)
    assert escaped is False
    assert "not in jail" in message.lower()


def test_roll_for_doubles_escape_on_first_attempt(sample_game, sample_player):
    """Test escaping jail on first doubles roll."""
    import random

    sample_player.in_jail = True
    # Mock random to return doubles
    original_randint = random.randint

    def mock_randint(a, b):
        return 3  # Always return 3 (doubles)

    random.randint = mock_randint

    try:
        escaped, dice1, dice2, message = JailManager.roll_for_doubles(sample_game, sample_player)
        assert escaped is True
        assert dice1 == dice2
        assert sample_player.in_jail is False
        assert sample_player.jail_turns == 0
    finally:
        random.randint = original_randint


def test_roll_for_doubles_third_attempt_forced_release(sample_game, sample_player):
    """Test forced release on 3rd failed attempt."""
    import random

    sample_player.in_jail = True
    sample_player.jail_turns = 2  # Already failed twice
    sample_player.cash = 200

    # Mock random to NOT return doubles
    original_randint = random.randint
    call_count = [0]

    def mock_randint(a, b):
        call_count[0] += 1
        return 3 if call_count[0] == 1 else 4  # Different values

    random.randint = mock_randint

    try:
        escaped, dice1, dice2, message = JailManager.roll_for_doubles(sample_game, sample_player)
        assert escaped is True  # Forced release
        assert sample_player.in_jail is False
        assert sample_player.jail_turns == 0
        assert "3rd turn" in message.lower()
        assert sample_player.cash == 150  # Paid $50 bribe
    finally:
        random.randint = original_randint


def test_roll_for_doubles_third_attempt_no_cash(sample_game, sample_player):
    """Test forced release on 3rd attempt with no cash for bribe."""
    import random

    sample_player.in_jail = True
    sample_player.jail_turns = 2
    sample_player.cash = 10  # Not enough for bribe

    # Mock random to NOT return doubles
    original_randint = random.randint
    call_count = [0]

    def mock_randint(a, b):
        call_count[0] += 1
        return 3 if call_count[0] == 1 else 4  # Different values

    random.randint = mock_randint

    try:
        escaped, dice1, dice2, message = JailManager.roll_for_doubles(sample_game, sample_player)
        assert escaped is True  # Auto-released
        assert sample_player.in_jail is False
        assert "auto-released" in message.lower()
    finally:
        random.randint = original_randint


def test_can_collect_rent_while_jailed(sample_game, sample_player):
    """Test that players in jail CAN collect rent."""
    from app.modules.sastadice.schemas import Tile

    sample_player.in_jail = True
    tile = Tile(
        id="tile1",
        type="PROPERTY",
        name="Test Property",
        owner_id=sample_player.id,
    )

    can_collect = JailManager.can_collect_rent(sample_player, tile, sample_game)
    assert can_collect is True  # Players in jail CAN collect rent


def test_can_collect_rent_blocked_tile(sample_game, sample_player):
    """Test that blocked tiles cannot collect rent."""
    from app.modules.sastadice.schemas import Tile

    tile = Tile(
        id="tile1",
        type="PROPERTY",
        name="Test Property",
        owner_id=sample_player.id,
        blocked_until_round=10,
    )
    sample_game.current_round = 5

    can_collect = JailManager.can_collect_rent(sample_player, tile, sample_game)
    assert can_collect is False  # Tile is blocked
