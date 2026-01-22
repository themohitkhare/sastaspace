"""Tests for EventManager."""
import pytest
from unittest.mock import AsyncMock
from app.modules.sastadice.schemas import GameSession, Player, GameSettings
from app.modules.sastadice.events.event_manager import EventManager
from app.modules.sastadice.events.events_data import SASTA_EVENTS


@pytest.fixture
def mock_repository():
    """Create a mock repository."""
    repo = AsyncMock()
    repo.update_player_cash = AsyncMock()
    repo.update_player_position = AsyncMock()
    repo.update = AsyncMock()
    return repo


@pytest.fixture
def sample_game():
    """Create a sample game session."""
    game = GameSession(
        id="test-game",
        players=[],
        board=[],
        settings=GameSettings(),
        rent_multiplier=1.0,
    )
    return game


@pytest.fixture
def sample_player():
    """Create a sample player."""
    return Player(id="player1", name="TestPlayer", cash=1000)


def test_initialize_deck(sample_game):
    """Test event deck initialization."""
    EventManager.initialize_deck(sample_game)
    assert len(sample_game.event_deck) == len(SASTA_EVENTS)
    assert len(sample_game.used_event_deck) == 0
    assert set(sample_game.event_deck) == set(range(len(SASTA_EVENTS)))


def test_draw_event(sample_game):
    """Test drawing an event from deck."""
    EventManager.initialize_deck(sample_game)
    event = EventManager.draw_event(sample_game)
    assert event is not None
    assert "name" in event
    assert "type" in event
    assert len(sample_game.event_deck) == len(SASTA_EVENTS) - 1
    assert len(sample_game.used_event_deck) == 1


def test_ensure_capacity_reshuffle(sample_game):
    """Test deck reshuffling when capacity is low."""
    EventManager.initialize_deck(sample_game)
    # Draw all but 2 cards
    for _ in range(len(SASTA_EVENTS) - 2):
        EventManager.draw_event(sample_game)

    assert len(sample_game.event_deck) == 2
    EventManager.ensure_capacity(sample_game, count=5)
    # Should reshuffle discard pile
    assert len(sample_game.event_deck) >= 5


@pytest.mark.asyncio
async def test_apply_effect_cash_gain(mock_repository, sample_game, sample_player):
    """Test applying CASH_GAIN event."""
    manager = EventManager(mock_repository)
    event = {"name": "Tax Rebate", "type": "CASH_GAIN", "value": 100}

    actions = await manager.apply_effect(sample_game, sample_player, event)

    assert actions["cash_changes"][sample_player.id] == 100
    assert sample_player.cash == 1100
    mock_repository.update_player_cash.assert_called_once_with(sample_player.id, 1100)


@pytest.mark.asyncio
async def test_apply_effect_cash_loss(mock_repository, sample_game, sample_player):
    """Test applying CASH_LOSS event."""
    manager = EventManager(mock_repository)
    event = {"name": "Subscription Trap", "type": "CASH_LOSS", "value": 100}

    actions = await manager.apply_effect(sample_game, sample_player, event)

    assert actions["cash_changes"][sample_player.id] == -100
    assert sample_player.cash == 900
    mock_repository.update_player_cash.assert_called_once_with(sample_player.id, 900)


@pytest.mark.asyncio
async def test_apply_effect_collect_from_all(
    mock_repository, sample_game, sample_player
):
    """Test applying COLLECT_FROM_ALL event."""
    manager = EventManager(mock_repository)
    player2 = Player(id="player2", name="Player2", cash=500)
    player3 = Player(id="player3", name="Player3", cash=300)
    sample_game.players = [sample_player, player2, player3]

    event = {"name": "Influencer Collab", "type": "COLLECT_FROM_ALL", "value": 50}

    actions = await manager.apply_effect(sample_game, sample_player, event)

    assert actions["cash_changes"][sample_player.id] == 100  # 50 * 2
    assert actions["cash_changes"][player2.id] == -50
    assert actions["cash_changes"][player3.id] == -50
    assert sample_player.cash == 1100
    assert player2.cash == 450
    assert player3.cash == 250


@pytest.mark.asyncio
async def test_apply_effect_market_crash(mock_repository, sample_game, sample_player):
    """Test applying MARKET_CRASH global effect."""
    manager = EventManager(mock_repository)
    sample_game.rent_multiplier = 1.0
    event = {"name": "Market Crash", "type": "MARKET_CRASH", "value": 0}

    actions = await manager.apply_effect(sample_game, sample_player, event)

    assert actions["special"] == "MARKET_CRASH"
    assert sample_game.rent_multiplier == 0.5


@pytest.mark.asyncio
async def test_apply_effect_bull_market(mock_repository, sample_game, sample_player):
    """Test applying BULL_MARKET global effect."""
    manager = EventManager(mock_repository)
    sample_game.rent_multiplier = 1.0
    event = {"name": "Bull Market", "type": "BULL_MARKET", "value": 0}

    actions = await manager.apply_effect(sample_game, sample_player, event)

    assert actions["special"] == "BULL_MARKET"
    assert sample_game.rent_multiplier == 1.5


@pytest.mark.asyncio
async def test_apply_effect_move_back(mock_repository, sample_game, sample_player):
    """Test applying MOVE_BACK event."""
    manager = EventManager(mock_repository)
    sample_player.position = 10
    event = {"name": "Transit Strike", "type": "MOVE_BACK", "value": 3}

    actions = await manager.apply_effect(sample_game, sample_player, event)

    assert actions["position_changes"][sample_player.id] == 7
    assert sample_player.position == 7
    mock_repository.update_player_position.assert_called_once_with(sample_player.id, 7)


def test_deck_persistence_after_full_cycle(sample_game):
    """Test deck reshuffles correctly after drawing all 36 cards."""
    EventManager.initialize_deck(sample_game)
    initial_deck = sample_game.event_deck.copy()

    # Draw all cards
    for _ in range(len(SASTA_EVENTS)):
        EventManager.draw_event(sample_game)

    assert len(sample_game.event_deck) == 0
    assert len(sample_game.used_event_deck) == len(SASTA_EVENTS)

    # Draw one more - should reshuffle
    EventManager.ensure_capacity(sample_game, 1)
    event = EventManager.draw_event(sample_game)
    assert event is not None
    assert len(sample_game.event_deck) == len(SASTA_EVENTS) - 1
