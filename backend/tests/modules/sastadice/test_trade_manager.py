"""Tests for TradeManager."""
import pytest
from app.modules.sastadice.services.trade_manager import TradeManager
from app.modules.sastadice.schemas import (
    GameSession,
    GameStatus,
    TurnPhase,
    TileType,
    Tile,
    Player,
    GameSettings,
    WinCondition,
    TradeOffer,
)


@pytest.fixture
def sample_game():
    """Create a sample game for testing."""
    settings = GameSettings(win_condition=WinCondition.SUDDEN_DEATH)
    return GameSession(
        id="test-game",
        status=GameStatus.ACTIVE,
        turn_phase=TurnPhase.POST_TURN,
        players=[],
        board=[],
        settings=settings,
        current_round=1,
        rent_multiplier=1.0,
        blocked_tiles=[],
        event_deck=[],
        used_event_deck=[],
        active_trade_offers=[],
    )


@pytest.fixture
def initiator_player():
    """Create an initiator player."""
    return Player(
        id="initiator",
        name="Initiator",
        cash=1000,
        position=0,
        color="#FF0000",
        properties=["tile1", "tile2"],
        ready=True,
    )


@pytest.fixture
def target_player():
    """Create a target player."""
    return Player(
        id="target",
        name="Target",
        cash=1000,
        position=0,
        color="#00FF00",
        properties=["tile3"],
        ready=True,
    )


class TestTradeManager:
    """Test suite for TradeManager."""

    def test_create_trade_offer_valid(self, sample_game, initiator_player, target_player):
        """Test creating a valid trade offer."""
        sample_game.players = [initiator_player, target_player]
        sample_game.board = [
            Tile(id="tile1", type=TileType.PROPERTY, name="Tile1", position=0, price=200, rent=20, owner_id="initiator"),
            Tile(id="tile3", type=TileType.PROPERTY, name="Tile3", position=1, price=200, rent=20, owner_id="target"),
        ]
        payload = {
            "target_id": target_player.id,
            "offer_cash": 100,
            "req_cash": 50,
            "offer_props": ["tile1"],
            "req_props": ["tile3"],
        }
        offer, error = TradeManager.create_trade_offer(sample_game, initiator_player, payload)
        assert offer is not None
        assert error is None
        assert offer.initiator_id == initiator_player.id
        assert offer.target_id == target_player.id

    def test_create_trade_offer_invalid_target(self, sample_game, initiator_player):
        """Test creating trade offer with invalid target."""
        payload = {"target_id": initiator_player.id}  # Can't trade with self
        offer, error = TradeManager.create_trade_offer(sample_game, initiator_player, payload)
        assert offer is None
        assert error is not None

    def test_create_trade_offer_insufficient_cash(self, sample_game, initiator_player, target_player):
        """Test creating trade offer with insufficient cash."""
        initiator_player.cash = 50
        sample_game.players = [initiator_player, target_player]
        payload = {
            "target_id": target_player.id,
            "offer_cash": 100,  # More than player has
            "req_cash": 0,
            "offer_props": [],
            "req_props": [],
        }
        offer, error = TradeManager.create_trade_offer(sample_game, initiator_player, payload)
        assert offer is None
        assert "insufficient" in error.lower()

    def test_validate_trade_assets_valid(self, sample_game, initiator_player, target_player):
        """Test validating valid trade assets."""
        sample_game.players = [initiator_player, target_player]
        sample_game.board = [
            Tile(id="tile1", type=TileType.PROPERTY, name="Tile1", position=0, price=200, rent=20, owner_id="initiator"),
            Tile(id="tile3", type=TileType.PROPERTY, name="Tile3", position=1, price=200, rent=20, owner_id="target"),
        ]
        offer = TradeOffer(
            initiator_id=initiator_player.id,
            target_id=target_player.id,
            offering_cash=100,
            offering_properties=["tile1"],
            requesting_cash=50,
            requesting_properties=["tile3"],
            created_at=0,
        )
        error = TradeManager.validate_trade_assets(sample_game, offer, initiator_player, target_player)
        assert error is None

    def test_validate_trade_assets_initiator_cant_afford(self, sample_game, initiator_player, target_player):
        """Test validating trade when initiator can't afford."""
        initiator_player.cash = 50
        sample_game.players = [initiator_player, target_player]
        offer = TradeOffer(
            initiator_id=initiator_player.id,
            target_id=target_player.id,
            offering_cash=100,
            offering_properties=[],
            requesting_cash=0,
            requesting_properties=[],
            created_at=0,
        )
        error = TradeManager.validate_trade_assets(sample_game, offer, initiator_player, target_player)
        assert error is not None
        assert "initiator" in error.lower()

    def test_execute_trade_transfer(self, sample_game, initiator_player, target_player):
        """Test executing a trade transfer."""
        sample_game.players = [initiator_player, target_player]
        offer = TradeOffer(
            initiator_id=initiator_player.id,
            target_id=target_player.id,
            offering_cash=100,
            offering_properties=["tile1"],
            requesting_cash=50,
            requesting_properties=["tile3"],
            created_at=0,
        )
        transfer_data = TradeManager.execute_trade_transfer(sample_game, offer, initiator_player, target_player)
        assert transfer_data["initiator_cash"] == initiator_player.cash - 100 + 50
        assert transfer_data["target_cash"] == target_player.cash + 100 - 50
        assert "tile1" in transfer_data["property_transfers"]["initiator_to_target"]
        assert "tile3" in transfer_data["property_transfers"]["target_to_initiator"]
