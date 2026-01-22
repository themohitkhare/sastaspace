"""Tests for AuctionManager."""

import time

import pytest

from app.modules.sastadice.schemas import (
    AuctionState,
    GameSession,
    GameSettings,
    GameStatus,
    Player,
    Tile,
    TileType,
    TurnPhase,
    WinCondition,
)
from app.modules.sastadice.services.auction_manager import AuctionManager


@pytest.fixture
def sample_game():
    """Create a sample game for testing."""
    settings = GameSettings(
        win_condition=WinCondition.SUDDEN_DEATH,
        round_limit=30,
    )
    return GameSession(
        id="test-game",
        status=GameStatus.ACTIVE,
        turn_phase=TurnPhase.AUCTION,
        players=[],
        board=[],
        settings=settings,
        current_round=1,
        rent_multiplier=1.0,
        blocked_tiles=[],
        event_deck=[],
        used_event_deck=[],
    )


@pytest.fixture
def sample_tile():
    """Create a sample property tile."""
    return Tile(
        id="tile1",
        type=TileType.PROPERTY,
        name="Test Property",
        position=0,
        price=200,
        rent=20,
        color="RED",
        owner_id=None,
    )


@pytest.fixture
def sample_player():
    """Create a sample player."""
    return Player(
        id="player1",
        name="Test Player",
        cash=1000,
        position=0,
        color="#FF0000",
        properties=[],
        ready=True,
    )


class TestAuctionManager:
    """Test suite for AuctionManager."""

    def test_start_auction(self, sample_game, sample_tile):
        """Test starting an auction."""
        sample_game.players = [
            Player(
                id="p1",
                name="P1",
                cash=1000,
                position=0,
                color="#FF0000",
                properties=[],
                ready=True,
            ),
            Player(
                id="p2",
                name="P2",
                cash=1000,
                position=0,
                color="#00FF00",
                properties=[],
                ready=True,
            ),
        ]
        auction = AuctionManager.start_auction(sample_game, sample_tile, auction_duration=30)
        assert auction is not None
        assert sample_game.turn_phase == TurnPhase.AUCTION
        assert sample_game.auction_state is not None
        assert len(auction.participants) == 2

    def test_validate_bid_valid(self, sample_player):
        """Test validating a valid bid."""
        auction = AuctionState(
            property_id="tile1",
            highest_bid=100,
            highest_bidder_id=None,
            start_time=time.time(),
            end_time=time.time() + 30,
            participants=[sample_player.id],
            min_bid_increment=10,
        )
        error = AuctionManager.validate_bid(auction, sample_player, 110)
        assert error is None

    def test_validate_bid_too_low(self, sample_player):
        """Test validating a bid that's too low."""
        auction = AuctionState(
            property_id="tile1",
            highest_bid=100,
            highest_bidder_id=None,
            start_time=time.time(),
            end_time=time.time() + 30,
            participants=[sample_player.id],
            min_bid_increment=10,
        )
        error = AuctionManager.validate_bid(auction, sample_player, 105)
        assert error is not None
        assert "too low" in error.lower()

    def test_validate_bid_insufficient_funds(self, sample_player):
        """Test validating a bid with insufficient funds."""
        sample_player.cash = 50
        auction = AuctionState(
            property_id="tile1",
            highest_bid=0,
            highest_bidder_id=None,
            start_time=time.time(),
            end_time=time.time() + 30,
            participants=[sample_player.id],
            min_bid_increment=10,
        )
        error = AuctionManager.validate_bid(auction, sample_player, 100)
        assert error is not None
        assert "insufficient" in error.lower()

    def test_place_bid(self, sample_game, sample_player, sample_tile):
        """Test placing a bid."""
        sample_game.players = [sample_player]
        sample_game.turn_phase = TurnPhase.AUCTION
        auction = AuctionManager.start_auction(sample_game, sample_tile, auction_duration=30)
        success, message = AuctionManager.place_bid(sample_game, sample_player.id, 100)
        assert success is True
        assert sample_game.auction_state.highest_bid == 100
        assert sample_game.auction_state.highest_bidder_id == sample_player.id

    def test_resolve_auction_with_winner(self, sample_game, sample_player):
        """Test resolving an auction with a winner."""
        sample_game.players = [sample_player]
        sample_game.board = [
            Tile(id="tile1", type=TileType.PROPERTY, name="Test", position=0, price=200, rent=20)
        ]
        auction = AuctionState(
            property_id="tile1",
            highest_bid=150,
            highest_bidder_id=sample_player.id,
            start_time=time.time() - 35,
            end_time=time.time() - 5,
            participants=[sample_player.id],
            min_bid_increment=10,
        )
        sample_game.auction_state = auction
        success, message, winner_id, amount, prop_id = AuctionManager.resolve_auction(sample_game)
        assert success is True
        assert winner_id == sample_player.id
        assert amount == 150

    def test_resolve_auction_no_bids(self, sample_game):
        """Test resolving an auction with no bids."""
        sample_game.board = [
            Tile(id="tile1", type=TileType.PROPERTY, name="Test", position=0, price=200, rent=20)
        ]
        auction = AuctionState(
            property_id="tile1",
            highest_bid=0,
            highest_bidder_id=None,
            start_time=time.time() - 35,
            end_time=time.time() - 5,
            participants=[],
            min_bid_increment=10,
        )
        sample_game.auction_state = auction
        success, message, winner_id, amount, prop_id = AuctionManager.resolve_auction(sample_game)
        assert success is True
        assert winner_id is None
        assert sample_game.turn_phase == TurnPhase.POST_TURN
