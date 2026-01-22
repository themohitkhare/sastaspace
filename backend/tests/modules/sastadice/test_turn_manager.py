"""Tests for TurnManager."""
import pytest
from app.modules.sastadice.services.turn_manager import TurnManager
from app.modules.sastadice.schemas import (
    GameSession,
    GameStatus,
    TurnPhase,
    TileType,
    Tile,
    Player,
    GameSettings,
    WinCondition,
    ChaosLevel,
)


@pytest.fixture
def sample_game():
    """Create a sample game for testing."""
    settings = GameSettings(
        win_condition=WinCondition.SUDDEN_DEATH,
        round_limit=30,
        target_cash=10000,
        starting_cash_multiplier=1.0,
        go_bonus_base=200,
        go_inflation_per_round=20,
        chaos_level=ChaosLevel.NORMAL,
    )
    return GameSession(
        id="test-game",
        status=GameStatus.ACTIVE,
        turn_phase=TurnPhase.PRE_ROLL,
        players=[],
        board=[],
        settings=settings,
        current_round=5,
        rent_multiplier=1.0,
        blocked_tiles=[],
        event_deck=[],
        used_event_deck=[],
    )


@pytest.fixture
def sample_player():
    """Create a sample player."""
    return Player(
        id="player1",
        name="Test Player",
        cash=1500,
        position=0,
        color="#FF0000",
        properties=[],
        ready=True,
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
        upgrade_level=0,
    )


class TestTurnManager:
    """Test suite for TurnManager."""

    def test_calculate_go_bonus(self, sample_game):
        """Test GO bonus calculation with inflation."""
        bonus = TurnManager.calculate_go_bonus(sample_game)
        assert bonus == 200 + (5 * 20)  # base + (round * inflation)

    def test_owns_full_set_true(self, sample_player, sample_tile):
        """Test owns_full_set returns True when player owns all tiles of a color."""
        board = [
            Tile(
                id=f"tile{i}",
                type=TileType.PROPERTY,
                name=f"Property {i}",
                position=i,
                price=200,
                rent=20,
                color="RED",
                owner_id=sample_player.id,
            )
            for i in range(3)
        ]
        assert TurnManager.owns_full_set(sample_player, "RED", board) is True

    def test_owns_full_set_false(self, sample_player, sample_tile):
        """Test owns_full_set returns False when player doesn't own all tiles."""
        board = [
            Tile(
                id="tile1",
                type=TileType.PROPERTY,
                name="Property 1",
                position=0,
                price=200,
                rent=20,
                color="RED",
                owner_id=sample_player.id,
            ),
            Tile(
                id="tile2",
                type=TileType.PROPERTY,
                name="Property 2",
                position=1,
                price=200,
                rent=20,
                color="RED",
                owner_id="other_player",
            ),
        ]
        assert TurnManager.owns_full_set(sample_player, "RED", board) is False

    def test_calculate_rent_base(self, sample_tile, sample_player, sample_game):
        """Test rent calculation for base property."""
        # Create a tile without a color set to avoid set bonus
        base_tile = Tile(
            id="tile1",
            type=TileType.PROPERTY,
            name="Test Property",
            position=0,
            price=200,
            rent=20,
            color=None,  # No color = no set bonus
            owner_id=sample_player.id,
        )
        sample_game.board = [base_tile]
        rent = TurnManager.calculate_rent(base_tile, sample_player, sample_game)
        assert rent == 20

    def test_calculate_rent_with_set_bonus(self, sample_player, sample_game):
        """Test rent calculation with full set bonus."""
        tiles = [
            Tile(
                id=f"tile{i}",
                type=TileType.PROPERTY,
                name=f"Property {i}",
                position=i,
                price=200,
                rent=20,
                color="RED",
                owner_id=sample_player.id,
            )
            for i in range(3)
        ]
        sample_game.board = tiles
        rent = TurnManager.calculate_rent(tiles[0], sample_player, sample_game)
        assert rent == 40  # 20 * 2 (set bonus)

    def test_calculate_rent_blocked(self, sample_tile, sample_player, sample_game):
        """Test rent calculation for blocked tile returns 0."""
        sample_tile.owner_id = sample_player.id
        sample_tile.blocked_until_round = 10
        sample_game.current_round = 5
        sample_game.board = [sample_tile]
        rent = TurnManager.calculate_rent(sample_tile, sample_player, sample_game)
        assert rent == 0

    def test_initialize_event_deck(self, sample_game):
        """Test event deck initialization."""
        TurnManager.initialize_event_deck(sample_game)
        assert len(sample_game.event_deck) > 0
        assert len(sample_game.used_event_deck) == 0

    def test_draw_event(self, sample_game):
        """Test drawing an event from the deck."""
        TurnManager.initialize_event_deck(sample_game)
        event = TurnManager.draw_event(sample_game)
        assert event is not None
        assert "name" in event
        assert "type" in event

    def test_handle_go_landing(self, sample_game, sample_tile):
        """Test handling GO tile landing."""
        sample_tile.type = TileType.GO
        TurnManager.handle_go_landing(sample_game, sample_tile)
        assert sample_game.turn_phase == TurnPhase.POST_TURN
        assert "GO" in sample_game.last_event_message

    def test_handle_property_landing_unowned(self, sample_game, sample_player, sample_tile):
        """Test handling unowned property landing."""
        result = TurnManager.handle_property_landing(sample_game, sample_player, sample_tile)
        assert result["action"] == "buy_decision"
        assert sample_game.pending_decision is not None
        assert sample_game.pending_decision.type == "BUY"

    def test_handle_property_landing_owned_by_player(self, sample_game, sample_player, sample_tile):
        """Test handling property owned by the landing player."""
        sample_tile.owner_id = sample_player.id
        result = TurnManager.handle_property_landing(sample_game, sample_player, sample_tile)
        assert result["action"] == "owned_by_player"
        assert sample_game.turn_phase == TurnPhase.POST_TURN

    def test_handle_property_landing_owned_by_other(self, sample_game, sample_player, sample_tile):
        """Test handling property owned by another player."""
        sample_tile.owner_id = "other_player"
        result = TurnManager.handle_property_landing(sample_game, sample_player, sample_tile)
        assert result["action"] == "pay_rent"

    def test_handle_market_landing(self, sample_game):
        """Test handling market tile landing."""
        TurnManager.handle_market_landing(sample_game)
        assert sample_game.pending_decision is not None
        assert sample_game.pending_decision.type == "MARKET"

    def test_handle_jail_landing(self, sample_game):
        """Test handling jail tile landing."""
        TurnManager.handle_jail_landing(sample_game)
        assert sample_game.turn_phase == TurnPhase.POST_TURN
