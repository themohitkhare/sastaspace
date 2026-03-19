"""Tests for P0 fixes: DynamicEconomyScaler wiring, Identity Theft fix, new chaos events."""

from unittest.mock import AsyncMock

import pytest

from app.modules.sastadice.events.event_manager import EventManager
from app.modules.sastadice.events.events_data import SASTA_EVENTS
from app.modules.sastadice.schemas import (
    GameSession,
    GameSettings,
    GameStatus,
    Player,
    Tile,
    TileType,
    TurnPhase,
)
from app.modules.sastadice.services.economy_manager import DynamicEconomyScaler
from app.modules.sastadice.services.turn_manager import TurnManager

# === Fixtures ===


@pytest.fixture
def mock_repository():
    """Create a mock repository."""
    repo = AsyncMock()
    repo.update_player_cash = AsyncMock()
    repo.update_player_position = AsyncMock()
    repo.update_player_buff = AsyncMock()
    repo.update_player_skip_next_move = AsyncMock()
    repo.update_player_double_rent_next_turn = AsyncMock()
    repo.update = AsyncMock()
    repo.save_board = AsyncMock()
    return repo


@pytest.fixture
def default_settings():
    """Default game settings."""
    return GameSettings(go_bonus_base=200, go_inflation_per_round=20)


@pytest.fixture
def sample_game(default_settings):
    """Create a sample game for testing."""
    return GameSession(
        id="test-game",
        status=GameStatus.ACTIVE,
        turn_phase=TurnPhase.PRE_ROLL,
        players=[],
        board=[],
        settings=default_settings,
        current_round=0,
        rent_multiplier=1.0,
        blocked_tiles=[],
        event_deck=[],
        used_event_deck=[],
    )


@pytest.fixture
def sample_player():
    """Create a sample player."""
    return Player(id="player1", name="Alice", cash=1000, position=0, properties=[])


@pytest.fixture
def sample_tile():
    """Create a sample property tile with no color (to avoid color set bonus)."""
    return Tile(
        id="tile1",
        type=TileType.PROPERTY,
        name="Test Prop",
        position=5,
        price=200,
        rent=20,
        color=None,
        owner_id="player2",
        upgrade_level=0,
    )


# === Fix 1: DynamicEconomyScaler wired into live gameplay ===


class TestGoCapWired:
    """Test that DynamicEconomyScaler.calculate_capped_go_bonus is used in TurnManager."""

    def test_go_bonus_capped_at_3x_base(self, sample_game):
        """At high rounds, GO bonus should not exceed 3x base (600 for base=200)."""
        sample_game.current_round = 50
        bonus = TurnManager.calculate_go_bonus(sample_game)
        max_expected = int(200 * DynamicEconomyScaler.GO_CAP_MULTIPLIER)
        assert bonus <= max_expected, f"GO bonus {bonus} exceeds 3x cap {max_expected}"

    def test_go_bonus_uncapped_at_low_rounds(self, sample_game):
        """At low rounds, GO bonus should equal base + inflation normally."""
        sample_game.current_round = 5
        bonus = TurnManager.calculate_go_bonus(sample_game)
        expected = 200 + (20 * 5)  # 300
        assert bonus == expected

    def test_go_bonus_exactly_at_cap_boundary(self, sample_game):
        """Test the exact round where cap kicks in. base=200, inflation=20, cap=600.
        uncapped = 200 + 20*r. Cap at 600 => 20*r = 400 => r=20.
        At r=20: uncapped=600=cap. At r=21: uncapped=620 but capped to 600."""
        sample_game.current_round = 20
        bonus = TurnManager.calculate_go_bonus(sample_game)
        assert bonus == 600  # exactly at cap

        sample_game.current_round = 21
        bonus = TurnManager.calculate_go_bonus(sample_game)
        assert bonus == 600  # capped

    def test_go_bonus_with_event_multiplier(self, sample_game):
        """Hyperinflation (3x multiplier) should apply on top of capped bonus."""
        sample_game.current_round = 25
        sample_game.go_bonus_multiplier = 3.0
        bonus = TurnManager.calculate_go_bonus(sample_game)
        # Capped base = 600, * 3.0 multiplier = 1800
        assert bonus == 1800

    def test_go_bonus_round_zero(self, sample_game):
        """At round 0, GO bonus should just be the base."""
        sample_game.current_round = 0
        bonus = TurnManager.calculate_go_bonus(sample_game)
        assert bonus == 200


class TestDynamicRentWired:
    """Test that DynamicEconomyScaler.calculate_dynamic_rent is used in TurnManager."""

    def test_rent_no_scaling_before_round_10(self, sample_game, sample_tile):
        """Before round 10, rent should not have round-based scaling."""
        sample_game.current_round = 5
        owner = Player(id="player2", name="Owner", cash=500, properties=["tile1"])
        sample_game.board = [sample_tile]
        rent = TurnManager.calculate_rent(sample_tile, owner, sample_game)
        assert rent == 20  # base rent, no scaling

    def test_rent_scales_after_round_10(self, sample_game, sample_tile):
        """After round 10, rent should increase by 10% per round past 10."""
        sample_game.current_round = 15
        owner = Player(id="player2", name="Owner", cash=500, properties=["tile1"])
        sample_game.board = [sample_tile]
        rent = TurnManager.calculate_rent(sample_tile, owner, sample_game)
        # round 15: multiplier = 1.0 + (5 * 0.1) = 1.5
        # DynamicEconomyScaler: base_rent=20, upgrade=0, upgrade_mult=1.0, upgraded=20
        # 20 * 1.5 = 30
        assert rent == 30

    def test_rent_scales_with_upgrade(self, sample_game, sample_tile):
        """Rent scaling with upgrade should use DynamicEconomyScaler upgrade multiplier."""
        sample_game.current_round = 15
        sample_tile.upgrade_level = 1
        owner = Player(id="player2", name="Owner", cash=500, properties=["tile1"])
        sample_game.board = [sample_tile]
        rent = TurnManager.calculate_rent(sample_tile, owner, sample_game)
        # DynamicEconomyScaler: base=20, upgrade_mult=1.5, upgraded=30
        # round_mult = 1.5, scaled = 30 * 1.5 = 45
        assert rent == 45

    def test_rent_with_color_set_bonus(self, sample_game):
        """Color set bonus (2x) should apply on top of dynamic scaling."""
        sample_game.current_round = 15
        tile1 = Tile(
            id="t1",
            type=TileType.PROPERTY,
            name="P1",
            position=1,
            price=200,
            rent=20,
            color="RED",
            owner_id="p2",
        )
        tile2 = Tile(
            id="t2",
            type=TileType.PROPERTY,
            name="P2",
            position=2,
            price=200,
            rent=20,
            color="RED",
            owner_id="p2",
        )
        sample_game.board = [tile1, tile2]
        owner = Player(id="p2", name="Owner", cash=500, properties=["t1", "t2"])
        rent = TurnManager.calculate_rent(tile1, owner, sample_game)
        # DynamicEconomyScaler: base=20, upgrade=0 => upgraded=20, round_mult=1.5 => 30
        # Color set bonus: 30 * 2 = 60
        assert rent == 60

    def test_rent_blocked_tile_returns_zero(self, sample_game, sample_tile):
        """Blocked tiles should return 0 rent."""
        sample_game.current_round = 15
        sample_tile.blocked_until_round = 20
        owner = Player(id="player2", name="Owner", cash=500, properties=["tile1"])
        sample_game.board = [sample_tile]
        rent = TurnManager.calculate_rent(sample_tile, owner, sample_game)
        assert rent == 0

    def test_rent_at_round_20_with_upgrade_level_2(self, sample_game, sample_tile):
        """Test high-round rent with max upgrade."""
        sample_game.current_round = 20
        sample_tile.upgrade_level = 2
        owner = Player(id="player2", name="Owner", cash=500, properties=["tile1"])
        sample_game.board = [sample_tile]
        rent = TurnManager.calculate_rent(sample_tile, owner, sample_game)
        # DynamicEconomyScaler: base=20, upgrade_mult=2.0, upgraded=40
        # round_mult = 1.0 + (10 * 0.1) = 2.0, scaled = 40 * 2.0 = 80
        assert rent == 80


# === Fix 2: Identity Theft (SWAP_CASH) counterplay ===


class TestSwapCashFix:
    """Test that SWAP_CASH now transfers 50% of difference, capped at $500."""

    @pytest.mark.asyncio
    async def test_swap_cash_50_percent_of_difference(self, mock_repository, sample_game):
        """Rich player should only lose 50% of the gap, not everything."""
        poor = Player(id="p1", name="Poor", cash=100)
        rich = Player(id="p2", name="Rich", cash=1100)
        sample_game.players = [poor, rich]

        manager = EventManager(mock_repository)
        event = {"name": "Identity Theft", "type": "SWAP_CASH", "value": 0}

        # Manually seed to ensure the swap targets the rich player
        import random

        random.seed(42)

        await manager.apply_effect(sample_game, poor, event)

        # difference = 1100 - 100 = 1000, transfer = 500 (50%), capped at 500
        # poor gains 500, rich loses 500
        assert poor.cash == 600
        assert rich.cash == 600

    @pytest.mark.asyncio
    async def test_swap_cash_cap_at_500(self, mock_repository, sample_game):
        """Transfer should be capped at $500 even if 50% of diff exceeds it."""
        poor = Player(id="p1", name="Poor", cash=0)
        rich = Player(id="p2", name="Rich", cash=5000)
        sample_game.players = [poor, rich]

        manager = EventManager(mock_repository)
        event = {"name": "Identity Theft", "type": "SWAP_CASH", "value": 0}

        import random

        random.seed(42)

        await manager.apply_effect(sample_game, poor, event)

        # difference = 5000, 50% = 2500, but capped at 500
        assert poor.cash == 500
        assert rich.cash == 4500

    @pytest.mark.asyncio
    async def test_swap_cash_equal_cash_no_transfer(self, mock_repository, sample_game):
        """If both players have same cash, no transfer happens."""
        p1 = Player(id="p1", name="Player1", cash=500)
        p2 = Player(id="p2", name="Player2", cash=500)
        sample_game.players = [p1, p2]

        manager = EventManager(mock_repository)
        event = {"name": "Identity Theft", "type": "SWAP_CASH", "value": 0}

        import random

        random.seed(42)

        await manager.apply_effect(sample_game, p1, event)

        assert p1.cash == 500
        assert p2.cash == 500

    @pytest.mark.asyncio
    async def test_swap_cash_drawer_is_richer(self, mock_repository, sample_game):
        """If drawer is richer, they should lose money (negative transfer)."""
        rich_drawer = Player(id="p1", name="RichDrawer", cash=2000)
        poor_target = Player(id="p2", name="PoorTarget", cash=200)
        sample_game.players = [rich_drawer, poor_target]

        manager = EventManager(mock_repository)
        event = {"name": "Identity Theft", "type": "SWAP_CASH", "value": 0}

        import random

        random.seed(42)

        await manager.apply_effect(sample_game, rich_drawer, event)

        # difference = 200 - 2000 = -1800, transfer = -900, capped at -500
        assert rich_drawer.cash == 1500
        assert poor_target.cash == 700


# === Fix 3: New Chaos Events ===


class TestNewEventsExist:
    """Test that the 3 new events exist in SASTA_EVENTS."""

    def test_wealth_tax_event_exists(self):
        types = [e["type"] for e in SASTA_EVENTS]
        assert "WEALTH_TAX" in types

    def test_audit_season_event_exists(self):
        types = [e["type"] for e in SASTA_EVENTS]
        assert "AUDIT_SEASON" in types

    def test_bailout_package_event_exists(self):
        types = [e["type"] for e in SASTA_EVENTS]
        assert "BAILOUT_PACKAGE" in types

    def test_total_event_count_increased(self):
        """Should now have 38 events (was 35 + 3 new)."""
        assert len(SASTA_EVENTS) == 38


class TestWealthTax:
    """Test WEALTH_TAX event handler."""

    @pytest.mark.asyncio
    async def test_wealth_tax_redistributes(self, mock_repository, sample_game):
        """Rich players above median lose 10% of excess, poor players gain equally."""
        p1 = Player(id="p1", name="Poor", cash=100)
        p2 = Player(id="p2", name="Middle", cash=500)
        p3 = Player(id="p3", name="Rich", cash=1000)
        sample_game.players = [p1, p2, p3]

        manager = EventManager(mock_repository)
        event = {"name": "Wealth Tax", "type": "WEALTH_TAX", "value": 10}

        actions = await manager.apply_effect(sample_game, p1, event)

        # median = 500. Rich(1000) excess = 500, tax = 50. Middle at median => no tax.
        # Below median: Poor(100). Redistribution: 50 to p1.
        assert p3.cash == 950
        assert p1.cash == 150
        assert p2.cash == 500  # at median, unchanged
        assert actions["special"] == "WEALTH_TAX"

    @pytest.mark.asyncio
    async def test_wealth_tax_no_below_median(self, mock_repository, sample_game):
        """If all players are at or above median, tax is collected but not redistributed."""
        p1 = Player(id="p1", name="A", cash=500)
        p2 = Player(id="p2", name="B", cash=500)
        p3 = Player(id="p3", name="C", cash=1000)
        sample_game.players = [p1, p2, p3]

        manager = EventManager(mock_repository)
        event = {"name": "Wealth Tax", "type": "WEALTH_TAX", "value": 10}

        await manager.apply_effect(sample_game, p1, event)

        # median = 500. Only p3 above. Tax = 50.
        # p1, p2 at median => not below. No redistribution.
        assert p3.cash == 950
        assert p1.cash == 500
        assert p2.cash == 500

    @pytest.mark.asyncio
    async def test_wealth_tax_single_player_no_crash(self, mock_repository, sample_game):
        """Single player should not crash."""
        p1 = Player(id="p1", name="Solo", cash=1000)
        sample_game.players = [p1]

        manager = EventManager(mock_repository)
        event = {"name": "Wealth Tax", "type": "WEALTH_TAX", "value": 10}

        await manager.apply_effect(sample_game, p1, event)

        assert p1.cash == 1000  # unchanged, not enough players


class TestAuditSeason:
    """Test AUDIT_SEASON event handler."""

    @pytest.mark.asyncio
    async def test_audit_season_sets_duration(self, mock_repository, sample_game):
        """Audit season should set audit_until_round correctly."""
        sample_game.current_round = 10
        p1 = Player(id="p1", name="Player", cash=1000)
        sample_game.players = [p1]

        manager = EventManager(mock_repository)
        event = {"name": "Audit Season", "type": "AUDIT_SEASON", "value": 2}

        actions = await manager.apply_effect(sample_game, p1, event)

        assert actions["special"] == "AUDIT_SEASON"
        assert actions["audit_until_round"] == 12


class TestBailoutPackage:
    """Test BAILOUT_PACKAGE event handler."""

    @pytest.mark.asyncio
    async def test_bailout_goes_to_poorest(self, mock_repository, sample_game):
        """Bailout should go to the poorest non-bankrupt player."""
        p1 = Player(id="p1", name="Poor", cash=50)
        p2 = Player(id="p2", name="Rich", cash=2000)
        p3 = Player(id="p3", name="Middle", cash=500)
        sample_game.players = [p1, p2, p3]

        manager = EventManager(mock_repository)
        event = {"name": "Bailout Package", "type": "BAILOUT_PACKAGE", "value": 500}

        actions = await manager.apply_effect(sample_game, p2, event)

        assert p1.cash == 550  # poorest gets $500
        assert p2.cash == 2000  # unchanged
        assert actions["special"] == "BAILOUT_PACKAGE"
        assert actions["bailout_recipient"]["id"] == "p1"

    @pytest.mark.asyncio
    async def test_bailout_skips_bankrupt(self, mock_repository, sample_game):
        """Bankrupt players should not receive bailout."""
        bankrupt = Player(id="p1", name="Bankrupt", cash=0, is_bankrupt=True)
        poor = Player(id="p2", name="Poor", cash=100)
        rich = Player(id="p3", name="Rich", cash=2000)
        sample_game.players = [bankrupt, poor, rich]

        manager = EventManager(mock_repository)
        event = {"name": "Bailout Package", "type": "BAILOUT_PACKAGE", "value": 500}

        actions = await manager.apply_effect(sample_game, rich, event)

        assert bankrupt.cash == 0  # still bankrupt
        assert poor.cash == 600  # got the bailout
        assert actions["bailout_recipient"]["id"] == "p2"

    @pytest.mark.asyncio
    async def test_bailout_tiebreaker_fewer_properties(self, mock_repository, sample_game):
        """When tied on cash, player with fewer properties gets bailout."""
        p1 = Player(id="p1", name="NoProps", cash=100, properties=[])
        p2 = Player(id="p2", name="HasProps", cash=100, properties=["t1", "t2"])
        sample_game.players = [p1, p2]

        manager = EventManager(mock_repository)
        event = {"name": "Bailout Package", "type": "BAILOUT_PACKAGE", "value": 500}

        actions = await manager.apply_effect(sample_game, p2, event)

        assert p1.cash == 600  # fewer properties wins tiebreak
        assert actions["bailout_recipient"]["id"] == "p1"

    @pytest.mark.asyncio
    async def test_bailout_drawer_is_poorest(self, mock_repository, sample_game):
        """If the event drawer is the poorest, they should get the bailout."""
        drawer = Player(id="p1", name="PoorDrawer", cash=50)
        other = Player(id="p2", name="Rich", cash=2000)
        sample_game.players = [drawer, other]

        manager = EventManager(mock_repository)
        event = {"name": "Bailout Package", "type": "BAILOUT_PACKAGE", "value": 500}

        actions = await manager.apply_effect(sample_game, drawer, event)

        assert drawer.cash == 550
        assert actions["bailout_recipient"]["id"] == "p1"


# === DynamicEconomyScaler unit tests ===


class TestDynamicEconomyScalerUnit:
    """Unit tests for DynamicEconomyScaler static methods."""

    def test_capped_go_bonus_below_cap(self):
        result = DynamicEconomyScaler.calculate_capped_go_bonus(200, 20, 5)
        assert result == 300  # 200 + 100

    def test_capped_go_bonus_at_cap(self):
        result = DynamicEconomyScaler.calculate_capped_go_bonus(200, 20, 20)
        assert result == 600  # exactly at 3x

    def test_capped_go_bonus_above_cap(self):
        result = DynamicEconomyScaler.calculate_capped_go_bonus(200, 20, 30)
        assert result == 600  # capped at 3x

    def test_dynamic_rent_before_round_10(self):
        settings = GameSettings()
        result = DynamicEconomyScaler.calculate_dynamic_rent(20, 0, 5, settings)
        assert result == 20

    def test_dynamic_rent_after_round_10(self):
        settings = GameSettings()
        result = DynamicEconomyScaler.calculate_dynamic_rent(20, 0, 15, settings)
        # 1.0 + (5 * 0.1) = 1.5 => 20 * 1.5 = 30
        assert result == 30

    def test_dynamic_rent_with_upgrades(self):
        settings = GameSettings()
        result = DynamicEconomyScaler.calculate_dynamic_rent(20, 2, 15, settings)
        # upgrade_mult = 1.0 + 2*0.5 = 2.0, upgraded = 40
        # round_mult = 1.5, result = 60
        assert result == 60
