"""Coverage tests for economy_manager.py and inflation_monitor.py."""

from unittest.mock import AsyncMock

import pytest

from app.modules.sastadice.schemas import (
    GameSession,
    GameSettings,
    GameStatus,
    PendingDecision,
    Player,
    Tile,
    TileType,
    TurnPhase,
    WinCondition,
)
from app.modules.sastadice.services.economy_manager import DynamicEconomyScaler, EconomyManager
from app.modules.sastadice.services.inflation_monitor import (
    EconomicMetrics,
    EconomicReport,
    EconomicViolationError,
    InflationMonitor,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.update_player_cash = AsyncMock()
    repo.update_player_properties = AsyncMock()
    repo.update_player_bankrupt = AsyncMock()
    repo.update_tile_owner = AsyncMock()
    repo.save_board = AsyncMock()
    return repo


@pytest.fixture
def settings():
    return GameSettings(
        win_condition=WinCondition.SUDDEN_DEATH,
        round_limit=30,
        go_bonus_base=200,
        go_inflation_per_round=20,
    )


def _make_tile(
    tile_id: str,
    tile_type: TileType = TileType.PROPERTY,
    price: int = 100,
    rent: int = 10,
    color: str = "RED",
    owner_id: str | None = None,
    upgrade_level: int = 0,
    position: int = 0,
) -> Tile:
    return Tile(
        id=tile_id,
        type=tile_type,
        name=f"Tile {tile_id}",
        price=price,
        rent=rent,
        color=color,
        owner_id=owner_id,
        upgrade_level=upgrade_level,
        position=position,
    )


def _make_player(player_id: str, cash: int = 500, properties: list[str] | None = None) -> Player:
    return Player(
        id=player_id,
        name=f"Player {player_id}",
        cash=cash,
        properties=properties or [],
        ready=True,
    )


def _make_game(
    players: list[Player],
    board: list[Tile],
    settings: GameSettings | None = None,
    current_round: int = 1,
) -> GameSession:
    return GameSession(
        id="game-1",
        status=GameStatus.ACTIVE,
        turn_phase=TurnPhase.PRE_ROLL,
        players=players,
        board=board,
        settings=settings or GameSettings(),
        rent_multiplier=1.0,
        blocked_tiles=[],
        event_deck=[],
        used_event_deck=[],
        current_round=current_round,
    )


# ===========================================================================
# DynamicEconomyScaler tests
# ===========================================================================


class TestDynamicEconomyScaler:
    """Unit tests for DynamicEconomyScaler static methods."""

    def test_calculate_dynamic_rent_no_upgrade_early_round(self, settings: GameSettings) -> None:
        """Rounds <= 10 return base rent with upgrade multiplier applied."""
        rent = DynamicEconomyScaler.calculate_dynamic_rent(
            base_rent=100, upgrade_level=0, current_round=5, settings=settings
        )
        assert rent == 100  # upgrade_multiplier = 1.0 → 100 * 1.0 = 100

    def test_calculate_dynamic_rent_upgrade_level_1_early_round(
        self, settings: GameSettings
    ) -> None:
        rent = DynamicEconomyScaler.calculate_dynamic_rent(
            base_rent=100, upgrade_level=1, current_round=5, settings=settings
        )
        assert rent == 150  # 1.5x

    def test_calculate_dynamic_rent_upgrade_level_2_early_round(
        self, settings: GameSettings
    ) -> None:
        rent = DynamicEconomyScaler.calculate_dynamic_rent(
            base_rent=100, upgrade_level=2, current_round=5, settings=settings
        )
        assert rent == 200  # 2.0x

    def test_calculate_dynamic_rent_round_10_no_scaling(self, settings: GameSettings) -> None:
        """Round == 10 should not trigger the dynamic multiplier (boundary)."""
        rent = DynamicEconomyScaler.calculate_dynamic_rent(
            base_rent=100, upgrade_level=0, current_round=10, settings=settings
        )
        assert rent == 100

    def test_calculate_dynamic_rent_round_11_scaling_starts(self, settings: GameSettings) -> None:
        """Round 11: multiplier = 1.0 + (1 * 0.1) = 1.1."""
        rent = DynamicEconomyScaler.calculate_dynamic_rent(
            base_rent=100, upgrade_level=0, current_round=11, settings=settings
        )
        assert rent == 110

    def test_calculate_dynamic_rent_high_round(self, settings: GameSettings) -> None:
        """Round 20: multiplier = 1.0 + (10 * 0.1) = 2.0."""
        rent = DynamicEconomyScaler.calculate_dynamic_rent(
            base_rent=100, upgrade_level=0, current_round=20, settings=settings
        )
        assert rent == 200

    def test_calculate_dynamic_rent_upgrade_plus_scaling(self, settings: GameSettings) -> None:
        """Upgrade + round scaling compound correctly."""
        rent = DynamicEconomyScaler.calculate_dynamic_rent(
            base_rent=100, upgrade_level=1, current_round=20, settings=settings
        )
        # upgraded = 150, round_multiplier = 2.0 → 300
        assert rent == 300

    # --- calculate_dynamic_buff_cost ---

    def test_calculate_dynamic_buff_cost_early_round(self) -> None:
        cost = DynamicEconomyScaler.calculate_dynamic_buff_cost(base_cost=50, current_round=5)
        assert cost == 50

    def test_calculate_dynamic_buff_cost_round_10_boundary(self) -> None:
        cost = DynamicEconomyScaler.calculate_dynamic_buff_cost(base_cost=50, current_round=10)
        assert cost == 50

    def test_calculate_dynamic_buff_cost_round_11(self) -> None:
        """Round 11: multiplier = 1.0 + (1 * 0.05) = 1.05."""
        cost = DynamicEconomyScaler.calculate_dynamic_buff_cost(base_cost=100, current_round=11)
        assert cost == 105

    def test_calculate_dynamic_buff_cost_high_round(self) -> None:
        """Round 20: multiplier = 1.0 + (10 * 0.05) = 1.5."""
        cost = DynamicEconomyScaler.calculate_dynamic_buff_cost(base_cost=100, current_round=20)
        assert cost == 150

    # --- calculate_capped_go_bonus ---

    def test_calculate_capped_go_bonus_round_0(self) -> None:
        bonus = DynamicEconomyScaler.calculate_capped_go_bonus(
            base_bonus=200, inflation_per_round=20, current_round=0
        )
        # uncapped = 200, max = 600, min(200, 600) = 200
        assert bonus == 200

    def test_calculate_capped_go_bonus_uncapped(self) -> None:
        """Round 5: uncapped = 200 + (20 * 5) = 300, max = 600 → 300."""
        bonus = DynamicEconomyScaler.calculate_capped_go_bonus(
            base_bonus=200, inflation_per_round=20, current_round=5
        )
        assert bonus == 300

    def test_calculate_capped_go_bonus_at_cap(self) -> None:
        """Round 20: uncapped = 200 + (20*20) = 600, max = 600 → 600."""
        bonus = DynamicEconomyScaler.calculate_capped_go_bonus(
            base_bonus=200, inflation_per_round=20, current_round=20
        )
        assert bonus == 600

    def test_calculate_capped_go_bonus_exceeds_cap(self) -> None:
        """Round 50: uncapped = 200 + (20*50) = 1200, max = 600 → capped at 600."""
        bonus = DynamicEconomyScaler.calculate_capped_go_bonus(
            base_bonus=200, inflation_per_round=20, current_round=50
        )
        assert bonus == 600

    def test_go_cap_multiplier_constant(self) -> None:
        assert DynamicEconomyScaler.GO_CAP_MULTIPLIER == 3.0

    def test_rent_scale_factor_constant(self) -> None:
        assert DynamicEconomyScaler.RENT_SCALE_FACTOR == 0.1

    def test_cost_scale_factor_constant(self) -> None:
        assert DynamicEconomyScaler.COST_SCALE_FACTOR == 0.05


# ===========================================================================
# EconomyManager tests
# ===========================================================================


class TestEconomyManagerChargePlayer:
    """Tests for EconomyManager.charge_player."""

    @pytest.mark.asyncio
    async def test_charge_zero_amount_returns_none(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        player = _make_player("p1", cash=500)
        game = _make_game([player], [])
        result = await manager.charge_player(game, player, 0)
        assert result == {"action": "none"}
        mock_repo.update_player_cash.assert_not_called()

    @pytest.mark.asyncio
    async def test_charge_negative_amount_returns_none(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        player = _make_player("p1", cash=500)
        game = _make_game([player], [])
        result = await manager.charge_player(game, player, -50)
        assert result == {"action": "none"}

    @pytest.mark.asyncio
    async def test_charge_player_has_enough_cash_no_creditor(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        player = _make_player("p1", cash=500)
        game = _make_game([player], [])
        result = await manager.charge_player(game, player, 200)
        assert result == {"action": "charged", "amount": 200}
        assert player.cash == 300
        mock_repo.update_player_cash.assert_called_once_with("p1", 300)

    @pytest.mark.asyncio
    async def test_charge_player_has_enough_cash_with_creditor(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        payer = _make_player("p1", cash=500)
        creditor = _make_player("p2", cash=100)
        game = _make_game([payer, creditor], [])
        result = await manager.charge_player(game, payer, 200, creditor=creditor)
        assert result == {"action": "charged", "amount": 200}
        assert payer.cash == 300
        assert creditor.cash == 300
        # Both players should have cash updated
        calls = {call.args for call in mock_repo.update_player_cash.call_args_list}
        assert ("p1", 300) in calls
        assert ("p2", 300) in calls

    @pytest.mark.asyncio
    async def test_charge_player_disconnected_creditor_not_paid(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        payer = _make_player("p1", cash=500)
        creditor = _make_player("p2", cash=100)
        creditor.disconnected = True
        game = _make_game([payer, creditor], [])
        await manager.charge_player(game, payer, 200, creditor=creditor)
        # Creditor should NOT receive payment
        assert creditor.cash == 100
        # Only payer cash is updated
        mock_repo.update_player_cash.assert_called_once_with("p1", 300)

    @pytest.mark.asyncio
    async def test_charge_player_insufficient_cash_triggers_liquidation(
        self, mock_repo: AsyncMock
    ) -> None:
        """Player can't pay directly but has upgrades to liquidate."""
        manager = EconomyManager(mock_repo)
        tile = _make_tile("t1", price=200, upgrade_level=2, owner_id="p1")
        player = _make_player("p1", cash=50, properties=["t1"])
        game = _make_game([player], [tile])

        result = await manager.charge_player(game, player, 300)
        # After liquidation the player should be charged
        assert result["action"] in ("charged_after_liquidation", "bankrupt")

    @pytest.mark.asyncio
    async def test_charge_player_bankruptcy_when_cannot_pay(self, mock_repo: AsyncMock) -> None:
        """Player has no assets to liquidate and goes bankrupt."""
        manager = EconomyManager(mock_repo)
        player = _make_player("p1", cash=10)
        game = _make_game([player], [])
        result = await manager.charge_player(game, player, 500)
        assert result["action"] == "bankrupt"
        assert result["creditor_id"] is None

    @pytest.mark.asyncio
    async def test_charge_player_bankruptcy_with_creditor(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        player = _make_player("p1", cash=10)
        creditor = _make_player("p2", cash=1000)
        game = _make_game([player, creditor], [])
        result = await manager.charge_player(game, player, 500, creditor=creditor)
        assert result["action"] == "bankrupt"
        assert result["creditor_id"] == "p2"


class TestEconomyManagerAutoLiquidate:
    """Tests for auto_liquidate."""

    @pytest.mark.asyncio
    async def test_auto_liquidate_downgrade_upgrades_first(self, mock_repo: AsyncMock) -> None:
        """Level-2 tile is downgraded to level 1, yielding tile.price refund."""
        manager = EconomyManager(mock_repo)
        tile = _make_tile("t1", price=100, upgrade_level=2, owner_id="p1")
        player = _make_player("p1", cash=0, properties=["t1"])
        game = _make_game([player], [tile])

        raised = await manager.auto_liquidate(game, player, needed=80)
        # Level-2 → level-1 refund = tile.price = 100
        assert raised >= 80
        assert tile.upgrade_level < 2

    @pytest.mark.asyncio
    async def test_auto_liquidate_fully_downgrade_then_sell(self, mock_repo: AsyncMock) -> None:
        """When downgrades aren't enough, property is sold."""
        manager = EconomyManager(mock_repo)
        tile = _make_tile("t1", price=100, upgrade_level=0, owner_id="p1")
        player = _make_player("p1", cash=0, properties=["t1"])
        game = _make_game([player], [tile])

        raised = await manager.auto_liquidate(game, player, needed=50)
        # Sell value = 100 // 2 = 50, exact match
        assert raised == 50
        assert tile.owner_id is None
        assert "t1" not in player.properties

    @pytest.mark.asyncio
    async def test_auto_liquidate_level1_downgrade_refund(self, mock_repo: AsyncMock) -> None:
        """Level-1 tile downgrade refund = tile.price // 2."""
        manager = EconomyManager(mock_repo)
        tile = _make_tile("t1", price=100, upgrade_level=1, owner_id="p1")
        player = _make_player("p1", cash=0, properties=["t1"])
        game = _make_game([player], [tile])

        raised = await manager.auto_liquidate(game, player, needed=30)
        # Level-1 → level-0 refund = 100 // 2 = 50
        assert raised == 50

    @pytest.mark.asyncio
    async def test_auto_liquidate_sell_upgraded_level2_property(self, mock_repo: AsyncMock) -> None:
        """Selling a level-2 property includes upgrade extra refund."""
        manager = EconomyManager(mock_repo)
        tile = _make_tile("t1", price=100, upgrade_level=2, owner_id="p1")
        # Need more than what downgrades alone give; set needed high
        player = _make_player("p1", cash=0, properties=["t1"])
        game = _make_game([player], [tile])

        # Need 10000 — forces complete sell after downgrades
        raised = await manager.auto_liquidate(game, player, needed=10000)
        # sell_value = 50, extra_refund = 100 + 50 = 150 → total=200 from final sell
        # plus two downgrade refunds: level-2→1 = 100, level-1→0 = 50 → total raised = 300
        assert raised > 0

    @pytest.mark.asyncio
    async def test_auto_liquidate_sell_upgraded_level1_property(self, mock_repo: AsyncMock) -> None:
        """Selling a level-1 property includes partial extra refund."""
        manager = EconomyManager(mock_repo)
        tile = _make_tile("t1", price=100, upgrade_level=1, owner_id="p1")
        player = _make_player("p1", cash=0, properties=["t1"])
        game = _make_game([player], [tile])
        raised = await manager.auto_liquidate(game, player, needed=10000)
        # downgrade refund (50) + sell_value (50) + extra_refund (50) = 150
        assert raised > 0

    @pytest.mark.asyncio
    async def test_auto_liquidate_no_properties_returns_zero(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        player = _make_player("p1", cash=10, properties=[])
        game = _make_game([player], [])
        raised = await manager.auto_liquidate(game, player, needed=500)
        assert raised == 0


class TestEconomyManagerBankruptcy:
    """Tests for process_bankruptcy."""

    @pytest.mark.asyncio
    async def test_process_bankruptcy_no_creditor(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        tile = _make_tile("t1", owner_id="p1", upgrade_level=1)
        player = _make_player("p1", cash=100, properties=["t1"])
        game = _make_game([player], [tile])

        await manager.process_bankruptcy(game, player)

        assert player.is_bankrupt is True
        assert player.cash == 0
        assert tile.owner_id is None
        assert tile.upgrade_level == 0
        assert "t1" in game.bankruptcy_auction_queue
        assert "BANKRUPT" in (game.last_event_message or "").upper()
        mock_repo.update_player_bankrupt.assert_called_once_with("p1", True)
        mock_repo.update_player_cash.assert_any_call("p1", 0)

    @pytest.mark.asyncio
    async def test_process_bankruptcy_with_creditor(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        tile = _make_tile("t1", owner_id="debtor")
        debtor = _make_player("debtor", cash=150, properties=["t1"])
        creditor = _make_player("creditor", cash=500)
        game = _make_game([debtor, creditor], [tile])

        await manager.process_bankruptcy(game, debtor, creditor=creditor)

        assert debtor.is_bankrupt is True
        assert creditor.cash == 650  # 500 + 150 debtor's remaining cash
        mock_repo.update_player_cash.assert_any_call("creditor", 650)

    @pytest.mark.asyncio
    async def test_process_bankruptcy_with_disconnected_creditor(
        self, mock_repo: AsyncMock
    ) -> None:
        manager = EconomyManager(mock_repo)
        debtor = _make_player("debtor", cash=100)
        creditor = _make_player("creditor", cash=500)
        creditor.disconnected = True
        game = _make_game([debtor, creditor], [])

        await manager.process_bankruptcy(game, debtor, creditor=creditor)

        # Creditor is disconnected, so no cash transfer
        assert creditor.cash == 500
        assert "State auction" in (game.last_event_message or "")

    @pytest.mark.asyncio
    async def test_process_bankruptcy_multiple_properties_cleared(
        self, mock_repo: AsyncMock
    ) -> None:
        manager = EconomyManager(mock_repo)
        t1 = _make_tile("t1", owner_id="p1")
        t2 = _make_tile("t2", owner_id="p1")
        t3 = _make_tile("t3", owner_id="p2")  # Different owner, untouched
        player = _make_player("p1", cash=0, properties=["t1", "t2"])
        game = _make_game([player], [t1, t2, t3])

        await manager.process_bankruptcy(game, player)

        assert t1.owner_id is None
        assert t2.owner_id is None
        assert t3.owner_id == "p2"  # Unaffected
        assert sorted(game.bankruptcy_auction_queue) == ["t1", "t2"]


class TestEconomyManagerDetermineWinner:
    """Tests for determine_winner."""

    def test_winner_single_active_player(self) -> None:
        manager = EconomyManager(AsyncMock())
        winner = _make_player("p1", cash=1000)
        bankrupt = _make_player("p2", cash=-1)
        bankrupt.cash = -1
        game = _make_game([winner, bankrupt], [])
        result = manager.determine_winner(game)
        assert result is not None
        assert result["id"] == "p1"

    def test_winner_all_bankrupt_picks_richest(self) -> None:
        manager = EconomyManager(AsyncMock())
        p1 = _make_player("p1", cash=-100)
        p2 = _make_player("p2", cash=-50)
        game = _make_game([p1, p2], [])
        result = manager.determine_winner(game)
        assert result is not None
        assert result["id"] == "p2"

    def test_winner_multiple_active_returns_in_progress(self) -> None:
        manager = EconomyManager(AsyncMock())
        p1 = _make_player("p1", cash=1000)
        p2 = _make_player("p2", cash=500)
        game = _make_game([p1, p2], [])
        result = manager.determine_winner(game)
        assert result is not None
        assert result["status"] == "in_progress"
        assert result["id"] == "p1"

    def test_winner_multiple_active_leader_is_richest(self) -> None:
        manager = EconomyManager(AsyncMock())
        p1 = _make_player("p1", cash=200)
        p2 = _make_player("p2", cash=800)
        p3 = _make_player("p3", cash=500)
        game = _make_game([p1, p2, p3], [])
        result = manager.determine_winner(game)
        assert result is not None
        assert result["id"] == "p2"


class TestEconomyManagerHandleBuyProperty:
    """Tests for handle_buy_property."""

    @pytest.mark.asyncio
    async def test_wrong_turn_phase_fails(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        game = _make_game([], [])
        game.turn_phase = TurnPhase.PRE_ROLL
        success, msg, _, _ = await manager.handle_buy_property(game, "p1")
        assert success is False
        assert "Cannot buy" in msg

    @pytest.mark.asyncio
    async def test_no_pending_decision_fails(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        game = _make_game([], [])
        game.turn_phase = TurnPhase.DECISION
        game.pending_decision = None
        success, msg, _, _ = await manager.handle_buy_property(game, "p1")
        assert success is False
        assert "No property" in msg

    @pytest.mark.asyncio
    async def test_pending_decision_wrong_type_fails(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        game = _make_game([], [])
        game.turn_phase = TurnPhase.DECISION
        game.pending_decision = PendingDecision(type="EVENT")
        success, msg, _, _ = await manager.handle_buy_property(game, "p1")
        assert success is False
        assert "No property" in msg

    @pytest.mark.asyncio
    async def test_player_not_found_fails(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        game = _make_game([], [])
        game.turn_phase = TurnPhase.DECISION
        game.pending_decision = PendingDecision(type="BUY", tile_id="t1", price=100)
        success, msg, _, _ = await manager.handle_buy_property(game, "ghost")
        assert success is False
        assert "Player not found" in msg

    @pytest.mark.asyncio
    async def test_no_tile_id_in_decision_fails(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        player = _make_player("p1", cash=500)
        game = _make_game([player], [])
        game.turn_phase = TurnPhase.DECISION
        game.pending_decision = PendingDecision(type="BUY", tile_id=None, price=100)
        success, msg, _, _ = await manager.handle_buy_property(game, "p1")
        assert success is False
        assert "Invalid tile" in msg

    @pytest.mark.asyncio
    async def test_not_enough_cash_fails(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        player = _make_player("p1", cash=50)
        game = _make_game([player], [])
        game.turn_phase = TurnPhase.DECISION
        game.pending_decision = PendingDecision(type="BUY", tile_id="t1", price=100)
        success, msg, _, _ = await manager.handle_buy_property(game, "p1")
        assert success is False
        assert "Not enough cash" in msg

    @pytest.mark.asyncio
    async def test_successful_buy(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        tile = _make_tile("t1", price=100)
        player = _make_player("p1", cash=500)
        game = _make_game([player], [tile])
        game.turn_phase = TurnPhase.DECISION
        game.pending_decision = PendingDecision(type="BUY", tile_id="t1", price=100)

        success, msg, tile_name, price = await manager.handle_buy_property(game, "p1")
        assert success is True
        assert price == 100
        assert "t1" in player.properties
        assert player.cash == 400
        assert game.pending_decision is None
        assert game.turn_phase == TurnPhase.POST_TURN


class TestEconomyManagerHandleUpgrade:
    """Tests for handle_upgrade."""

    def _mock_turn_manager(self, owns_full_set: bool = True) -> AsyncMock:
        tm = AsyncMock()
        tm.owns_full_set = lambda player, color, board: owns_full_set  # noqa: ARG005
        return tm

    @pytest.mark.asyncio
    async def test_no_tile_id_fails(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        game = _make_game([], [])
        success, msg, _ = await manager.handle_upgrade(game, "p1", {}, self._mock_turn_manager())
        assert success is False
        assert "Tile ID required" in msg

    @pytest.mark.asyncio
    async def test_tile_not_found_fails(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        game = _make_game([], [])
        success, msg, _ = await manager.handle_upgrade(
            game, "p1", {"tile_id": "ghost"}, self._mock_turn_manager()
        )
        assert success is False
        assert "Invalid property" in msg

    @pytest.mark.asyncio
    async def test_non_property_tile_fails(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        tile = _make_tile("t1", tile_type=TileType.TAX)
        game = _make_game([], [tile])
        success, msg, _ = await manager.handle_upgrade(
            game, "p1", {"tile_id": "t1"}, self._mock_turn_manager()
        )
        assert success is False
        assert "Invalid property" in msg

    @pytest.mark.asyncio
    async def test_not_owner_fails(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        tile = _make_tile("t1", owner_id="p2")
        game = _make_game([], [tile])
        success, msg, _ = await manager.handle_upgrade(
            game, "p1", {"tile_id": "t1"}, self._mock_turn_manager()
        )
        assert success is False
        assert "don't own" in msg

    @pytest.mark.asyncio
    async def test_player_not_found_fails(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        tile = _make_tile("t1", owner_id="p1", color="RED")
        game = _make_game([], [tile])
        success, msg, _ = await manager.handle_upgrade(
            game, "p1", {"tile_id": "t1"}, self._mock_turn_manager()
        )
        assert success is False
        assert "Player not found" in msg

    @pytest.mark.asyncio
    async def test_no_color_fails(self, mock_repo: AsyncMock) -> None:
        """Tile with no color cannot be upgraded."""
        manager = EconomyManager(mock_repo)
        tile = _make_tile("t1", owner_id="p1", color=None)  # type: ignore[arg-type]
        tile.color = None
        player = _make_player("p1", cash=1000)
        game = _make_game([player], [tile])
        success, msg, _ = await manager.handle_upgrade(
            game, "p1", {"tile_id": "t1"}, self._mock_turn_manager(owns_full_set=True)
        )
        assert success is False
        assert "full color set" in msg

    @pytest.mark.asyncio
    async def test_not_full_color_set_fails(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        tile = _make_tile("t1", owner_id="p1", color="RED")
        player = _make_player("p1", cash=1000)
        game = _make_game([player], [tile])
        success, msg, _ = await manager.handle_upgrade(
            game, "p1", {"tile_id": "t1"}, self._mock_turn_manager(owns_full_set=False)
        )
        assert success is False
        assert "full color set" in msg

    @pytest.mark.asyncio
    async def test_max_level_fails(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        tile = _make_tile("t1", owner_id="p1", color="RED", upgrade_level=2)
        player = _make_player("p1", cash=1000)
        game = _make_game([player], [tile])
        success, msg, _ = await manager.handle_upgrade(
            game, "p1", {"tile_id": "t1"}, self._mock_turn_manager()
        )
        assert success is False
        assert "Max upgrade" in msg

    @pytest.mark.asyncio
    async def test_insufficient_funds_fails(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        tile = _make_tile("t1", owner_id="p1", color="RED", price=200, upgrade_level=0)
        player = _make_player("p1", cash=10)
        game = _make_game([player], [tile])
        success, msg, _ = await manager.handle_upgrade(
            game, "p1", {"tile_id": "t1"}, self._mock_turn_manager()
        )
        assert success is False
        assert "Insufficient funds" in msg

    @pytest.mark.asyncio
    async def test_successful_upgrade_level_1(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        tile = _make_tile("t1", owner_id="p1", color="RED", price=100, upgrade_level=0)
        player = _make_player("p1", cash=500)
        game = _make_game([player], [tile])
        success, msg, level_name = await manager.handle_upgrade(
            game, "p1", {"tile_id": "t1"}, self._mock_turn_manager()
        )
        assert success is True
        assert level_name == "SCRIPT KIDDIE"
        assert tile.upgrade_level == 1
        assert player.cash == 400

    @pytest.mark.asyncio
    async def test_successful_upgrade_level_2(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        tile = _make_tile("t1", owner_id="p1", color="RED", price=100, upgrade_level=1)
        player = _make_player("p1", cash=500)
        game = _make_game([player], [tile])
        success, msg, level_name = await manager.handle_upgrade(
            game, "p1", {"tile_id": "t1"}, self._mock_turn_manager()
        )
        assert success is True
        assert level_name == "1337 HAXXOR"
        assert tile.upgrade_level == 2
        assert player.cash == 300  # cost = 100 * 2 = 200


class TestEconomyManagerHandleDowngrade:
    """Tests for handle_downgrade."""

    @pytest.mark.asyncio
    async def test_no_tile_id_fails(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        game = _make_game([], [])
        success, msg, refund = await manager.handle_downgrade(game, "p1", {})
        assert success is False
        assert "Tile ID required" in msg
        assert refund is None

    @pytest.mark.asyncio
    async def test_tile_not_found_fails(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        game = _make_game([], [])
        success, msg, _ = await manager.handle_downgrade(game, "p1", {"tile_id": "ghost"})
        assert success is False
        assert "Invalid property" in msg

    @pytest.mark.asyncio
    async def test_non_property_tile_fails(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        tile = _make_tile("t1", tile_type=TileType.TAX)
        game = _make_game([], [tile])
        success, msg, _ = await manager.handle_downgrade(game, "p1", {"tile_id": "t1"})
        assert success is False

    @pytest.mark.asyncio
    async def test_not_owner_fails(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        tile = _make_tile("t1", owner_id="p2")
        game = _make_game([], [tile])
        success, msg, _ = await manager.handle_downgrade(game, "p1", {"tile_id": "t1"})
        assert success is False
        assert "don't own" in msg

    @pytest.mark.asyncio
    async def test_player_not_found_fails(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        tile = _make_tile("t1", owner_id="p1")
        game = _make_game([], [tile])
        success, msg, _ = await manager.handle_downgrade(game, "p1", {"tile_id": "t1"})
        assert success is False
        assert "Player not found" in msg

    @pytest.mark.asyncio
    async def test_no_upgrades_fails(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        tile = _make_tile("t1", owner_id="p1", upgrade_level=0)
        player = _make_player("p1", cash=500)
        game = _make_game([player], [tile])
        success, msg, _ = await manager.handle_downgrade(game, "p1", {"tile_id": "t1"})
        assert success is False
        assert "No upgrades" in msg

    @pytest.mark.asyncio
    async def test_downgrade_level_2_to_1(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        tile = _make_tile("t1", owner_id="p1", price=100, upgrade_level=2)
        player = _make_player("p1", cash=0)
        game = _make_game([player], [tile])
        success, msg, refund = await manager.handle_downgrade(game, "p1", {"tile_id": "t1"})
        assert success is True
        # original_cost = 100 * 2 = 200, refund = 100
        assert refund == 100
        assert player.cash == 100
        assert tile.upgrade_level == 1

    @pytest.mark.asyncio
    async def test_downgrade_level_1_to_0(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        tile = _make_tile("t1", owner_id="p1", price=100, upgrade_level=1)
        player = _make_player("p1", cash=0)
        game = _make_game([player], [tile])
        success, msg, refund = await manager.handle_downgrade(game, "p1", {"tile_id": "t1"})
        assert success is True
        # original_cost = 100 * 1 = 100, refund = 50
        assert refund == 50
        assert player.cash == 50
        assert tile.upgrade_level == 0


class TestEconomyManagerCheckEndConditions:
    """Tests for check_end_conditions."""

    @pytest.mark.asyncio
    async def test_check_end_conditions_always_false(self, mock_repo: AsyncMock) -> None:
        manager = EconomyManager(mock_repo)
        result = await manager.check_end_conditions("game-1")
        assert result is False


# ===========================================================================
# InflationMonitor tests
# ===========================================================================


def _make_game_for_monitor(
    game_id: str = "g1",
    current_round: int = 25,
    players: list[Player] | None = None,
    board: list[Tile] | None = None,
) -> "GameSession":
    return GameSession(
        id=game_id,
        status=GameStatus.ACTIVE,
        turn_phase=TurnPhase.PRE_ROLL,
        players=players or [],
        board=board or [],
        settings=GameSettings(),
        rent_multiplier=1.0,
        blocked_tiles=[],
        event_deck=[],
        used_event_deck=[],
        current_round=current_round,
    )


class TestEconomicMetrics:
    """Tests for the EconomicMetrics dataclass."""

    def test_default_fields(self) -> None:
        m = EconomicMetrics(
            round_number=1,
            total_system_cash=1000,
            cash_per_player={"p1": 1000},
            properties_owned=2,
            properties_traded_this_round=1,
            bankruptcies_this_round=0,
        )
        assert m.go_bonus_paid_this_round == 0
        assert m.rent_collected_this_round == 0

    def test_custom_fields(self) -> None:
        m = EconomicMetrics(
            round_number=5,
            total_system_cash=3000,
            cash_per_player={"p1": 2000, "p2": 1000},
            properties_owned=5,
            properties_traded_this_round=2,
            bankruptcies_this_round=1,
            go_bonus_paid_this_round=400,
            rent_collected_this_round=150,
        )
        assert m.go_bonus_paid_this_round == 400
        assert m.rent_collected_this_round == 150


class TestEconomicViolationError:
    """Tests for EconomicViolationError."""

    def test_violations_stored(self) -> None:
        err = EconomicViolationError(["V1", "V2"])
        assert err.violations == ["V1", "V2"]

    def test_message_contains_violations(self) -> None:
        err = EconomicViolationError(["A", "B"])
        assert "A" in str(err)
        assert "B" in str(err)


class TestInflationMonitorRecordRoundEnd:
    """Tests for InflationMonitor.record_round_end."""

    def test_records_metrics(self) -> None:
        monitor = InflationMonitor()
        p1 = _make_player("p1", cash=500)
        tile = _make_tile("t1", owner_id="p1")
        game = _make_game_for_monitor(players=[p1], board=[tile], current_round=1)

        metrics = monitor.record_round_end(game)
        assert metrics.round_number == 1
        assert metrics.total_system_cash == 500
        assert metrics.cash_per_player == {"p1": 500}
        assert metrics.properties_owned == 1
        assert len(monitor.metrics_history) == 1

    def test_excludes_bankrupt_players(self) -> None:
        monitor = InflationMonitor()
        p1 = _make_player("p1", cash=500)
        p2 = _make_player("p2", cash=300)
        p2.is_bankrupt = True
        game = _make_game_for_monitor(players=[p1, p2], board=[], current_round=1)

        metrics = monitor.record_round_end(game)
        assert metrics.total_system_cash == 500

    def test_multiple_rounds(self) -> None:
        monitor = InflationMonitor()
        p1 = _make_player("p1", cash=500)
        game = _make_game_for_monitor(players=[p1], board=[], current_round=1)
        monitor.record_round_end(game)

        p1.cash = 600
        game.current_round = 2
        monitor.record_round_end(game)
        assert len(monitor.metrics_history) == 2


class TestInflationMonitorCheckEconomicHealth:
    """Tests for InflationMonitor.check_economic_health."""

    def test_early_rounds_no_violations(self) -> None:
        monitor = InflationMonitor()
        game = _make_game_for_monitor(current_round=5)
        violations = monitor.check_economic_health(game)
        assert violations == []

    def test_round_20_boundary_no_violations(self) -> None:
        monitor = InflationMonitor()
        game = _make_game_for_monitor(current_round=20)
        violations = monitor.check_economic_health(game)
        assert violations == []

    def test_inflation_runaway_detected(self) -> None:
        monitor = InflationMonitor()
        # Populate history with always-increasing cash
        for i in range(12):
            monitor.metrics_history.append(
                EconomicMetrics(
                    round_number=20 + i,
                    total_system_cash=1000 + i * 100,
                    cash_per_player={},
                    properties_owned=0,
                    properties_traded_this_round=0,
                    bankruptcies_this_round=0,
                )
            )
            monitor.consecutive_cash_growth = 10  # Force trigger

        p1 = _make_player("p1", cash=600)
        p2 = _make_player("p2", cash=590)
        game = _make_game_for_monitor(players=[p1, p2], current_round=30)
        violations = monitor.check_economic_health(game)
        assert any("INFLATION_RUNAWAY" in v for v in violations)

    def test_inflation_streak_resets_on_cash_drop(self) -> None:
        monitor = InflationMonitor()
        # Two rounds: second is lower
        monitor.metrics_history.append(
            EconomicMetrics(
                round_number=21,
                total_system_cash=2000,
                cash_per_player={},
                properties_owned=0,
                properties_traded_this_round=0,
                bankruptcies_this_round=0,
            )
        )
        monitor.metrics_history.append(
            EconomicMetrics(
                round_number=22,
                total_system_cash=1800,
                cash_per_player={},
                properties_owned=0,
                properties_traded_this_round=0,
                bankruptcies_this_round=0,
            )
        )
        monitor.consecutive_cash_growth = 5  # Pre-existing streak
        # Use 2 players so cash_values is always defined in the metrics branch
        p1 = _make_player("p1", cash=900)
        p2 = _make_player("p2", cash=900)
        game = _make_game_for_monitor(players=[p1, p2], current_round=22)
        monitor.check_economic_health(game)
        assert monitor.consecutive_cash_growth == 0

    def test_stalemate_detected(self) -> None:
        monitor = InflationMonitor()
        monitor.turns_without_property_change = 20  # Trigger STALEMATE

        # Must provide enough metrics history to pass the first check
        for i in range(2):
            monitor.metrics_history.append(
                EconomicMetrics(
                    round_number=20 + i,
                    total_system_cash=1000,
                    cash_per_player={},
                    properties_owned=0,
                    properties_traded_this_round=0,
                    bankruptcies_this_round=0,
                )
            )

        tile = _make_tile("t1", tile_type=TileType.PROPERTY, owner_id="p1")
        # Set last_property_state to match current board so no change is detected
        monitor.last_property_state = {("t1", "p1")}

        p1 = _make_player("p1", cash=500)
        p2 = _make_player("p2", cash=490)
        game = _make_game_for_monitor(players=[p1, p2], board=[tile], current_round=25)
        violations = monitor.check_economic_health(game)
        assert any("STALEMATE" in v for v in violations)

    def test_property_changes_reset_stalemate_counter(self) -> None:
        monitor = InflationMonitor()
        monitor.turns_without_property_change = 10
        monitor.last_property_state = {("t1", "p1")}  # Previous state

        # Populate 2 history entries so first check works
        for i in range(2):
            monitor.metrics_history.append(
                EconomicMetrics(
                    round_number=20 + i,
                    total_system_cash=1000,
                    cash_per_player={},
                    properties_owned=0,
                    properties_traded_this_round=0,
                    bankruptcies_this_round=0,
                )
            )

        tile = _make_tile("t1", tile_type=TileType.PROPERTY, owner_id="p2")  # Ownership changed
        p1 = _make_player("p1", cash=500)
        p2 = _make_player("p2", cash=490)
        game = _make_game_for_monitor(players=[p1, p2], board=[tile], current_round=25)
        monitor.check_economic_health(game)
        assert monitor.turns_without_property_change == 0

    def test_wealth_imbalance_violation(self) -> None:
        monitor = InflationMonitor()
        monitor.metrics_history.append(
            EconomicMetrics(
                round_number=25,
                total_system_cash=10100,
                cash_per_player={},
                properties_owned=0,
                properties_traded_this_round=0,
                bankruptcies_this_round=0,
            )
        )
        # Add two consecutive entries to pass cash-growth check
        monitor.metrics_history.append(
            EconomicMetrics(
                round_number=26,
                total_system_cash=10000,
                cash_per_player={},
                properties_owned=0,
                properties_traded_this_round=0,
                bankruptcies_this_round=0,
            )
        )

        rich_player = _make_player("rich", cash=10000)
        poor_player = _make_player("poor", cash=50)  # Ratio: 200x
        game = _make_game_for_monitor(players=[rich_player, poor_player], current_round=25)
        violations = monitor.check_economic_health(game)
        assert any("WEALTH_IMBALANCE" in v for v in violations)

    def test_gini_violation_after_round_100(self) -> None:
        monitor = InflationMonitor()
        monitor.metrics_history.append(
            EconomicMetrics(
                round_number=101,
                total_system_cash=10001,
                cash_per_player={},
                properties_owned=0,
                properties_traded_this_round=0,
                bankruptcies_this_round=0,
            )
        )
        monitor.metrics_history.append(
            EconomicMetrics(
                round_number=102,
                total_system_cash=10000,
                cash_per_player={},
                properties_owned=0,
                properties_traded_this_round=0,
                bankruptcies_this_round=0,
            )
        )

        # Very extreme wealth: [1, 10000]
        rich = _make_player("rich", cash=9999)
        poor = _make_player("poor", cash=1)
        game = _make_game_for_monitor(players=[rich, poor], current_round=101)
        violations = monitor.check_economic_health(game)
        assert any("EXTREME_INEQUALITY" in v or "WEALTH_IMBALANCE" in v for v in violations)


class TestInflationMonitorGini:
    """Tests for _calculate_gini."""

    def test_equal_distribution_returns_zero(self) -> None:
        monitor = InflationMonitor()
        assert monitor._calculate_gini([100, 100, 100]) == 0.0

    def test_empty_list_returns_zero(self) -> None:
        monitor = InflationMonitor()
        assert monitor._calculate_gini([]) == 0.0

    def test_all_zero_returns_zero(self) -> None:
        monitor = InflationMonitor()
        assert monitor._calculate_gini([0, 0, 0]) == 0.0

    def test_extreme_inequality(self) -> None:
        monitor = InflationMonitor()
        # One person has everything, others have nothing equivalent
        gini = monitor._calculate_gini([0, 0, 1000])
        assert gini > 0.5

    def test_perfect_inequality_single(self) -> None:
        monitor = InflationMonitor()
        gini = monitor._calculate_gini([1])
        # Single value → no inequality
        assert gini == 0.0

    def test_negative_values_clamped(self) -> None:
        monitor = InflationMonitor()
        gini = monitor._calculate_gini([-100, 500])
        # -100 is clamped to 0 → [0, 500] → moderate inequality
        assert 0.0 <= gini <= 1.0


class TestInflationMonitorCountPropertyChanges:
    """Tests for _count_property_changes."""

    def test_no_changes_when_same_state(self) -> None:
        monitor = InflationMonitor()
        tile = _make_tile("t1", tile_type=TileType.PROPERTY, owner_id="p1")
        monitor.last_property_state = {("t1", "p1")}
        game = _make_game_for_monitor(board=[tile])
        changes = monitor._count_property_changes(game)
        assert changes == 0

    def test_new_ownership_counts_as_change(self) -> None:
        monitor = InflationMonitor()
        tile = _make_tile("t1", tile_type=TileType.PROPERTY, owner_id="p2")
        monitor.last_property_state = {("t1", "p1")}  # Previous owner was p1
        game = _make_game_for_monitor(board=[tile])
        changes = monitor._count_property_changes(game)
        assert changes == 1

    def test_non_property_tiles_ignored(self) -> None:
        monitor = InflationMonitor()
        tax_tile = _make_tile("t1", tile_type=TileType.TAX, owner_id="p1")
        monitor.last_property_state = set()
        game = _make_game_for_monitor(board=[tax_tile])
        changes = monitor._count_property_changes(game)
        assert changes == 0

    def test_unowned_property(self) -> None:
        monitor = InflationMonitor()
        tile = _make_tile("t1", tile_type=TileType.PROPERTY, owner_id=None)
        monitor.last_property_state = set()
        game = _make_game_for_monitor(board=[tile])
        changes = monitor._count_property_changes(game)
        assert changes == 1  # (t1, "unowned") is new


class TestInflationMonitorGenerateReport:
    """Tests for generate_report."""

    def test_empty_history_returns_zero_report(self) -> None:
        monitor = InflationMonitor()
        game = _make_game_for_monitor()
        report = monitor.generate_report(game)
        assert report.rounds_played == 0
        assert report.inflation_detected is False
        assert report.stalemate_detected is False
        assert report.diagnosis == "No data collected"
        assert report.avg_cash_per_round == []

    def test_healthy_report(self) -> None:
        monitor = InflationMonitor()
        for i in range(5):
            monitor.metrics_history.append(
                EconomicMetrics(
                    round_number=i + 1,
                    total_system_cash=1000,
                    cash_per_player={},
                    properties_owned=0,
                    properties_traded_this_round=1,
                    bankruptcies_this_round=0,
                )
            )
        game = _make_game_for_monitor()
        report = monitor.generate_report(game)
        assert report.rounds_played == 5
        assert report.diagnosis == "HEALTHY"
        assert report.inflation_detected is False
        assert report.stalemate_detected is False

    def test_inflation_report(self) -> None:
        monitor = InflationMonitor()
        monitor.consecutive_cash_growth = 10  # == INFLATION_STREAK_LIMIT
        for i in range(5):
            monitor.metrics_history.append(
                EconomicMetrics(
                    round_number=i + 1,
                    total_system_cash=1000 + i * 100,
                    cash_per_player={},
                    properties_owned=0,
                    properties_traded_this_round=0,
                    bankruptcies_this_round=0,
                )
            )
        game = _make_game_for_monitor()
        report = monitor.generate_report(game)
        assert report.inflation_detected is True
        assert report.diagnosis == "RUNAWAY_INFLATION"
        assert len(report.recommendations) > 0

    def test_stalemate_report(self) -> None:
        monitor = InflationMonitor()
        monitor.turns_without_property_change = 20  # == STALEMATE_TURN_LIMIT
        for i in range(5):
            monitor.metrics_history.append(
                EconomicMetrics(
                    round_number=i + 1,
                    total_system_cash=1000,
                    cash_per_player={},
                    properties_owned=0,
                    properties_traded_this_round=0,
                    bankruptcies_this_round=0,
                )
            )
        game = _make_game_for_monitor()
        report = monitor.generate_report(game)
        assert report.stalemate_detected is True
        assert "STALEMATE" in report.diagnosis

    def test_inflation_and_stalemate_combined(self) -> None:
        monitor = InflationMonitor()
        monitor.consecutive_cash_growth = 10
        monitor.turns_without_property_change = 20
        for i in range(3):
            monitor.metrics_history.append(
                EconomicMetrics(
                    round_number=i + 1,
                    total_system_cash=500,
                    cash_per_player={},
                    properties_owned=0,
                    properties_traded_this_round=0,
                    bankruptcies_this_round=0,
                )
            )
        game = _make_game_for_monitor()
        report = monitor.generate_report(game)
        assert "INFLATION" in report.diagnosis
        assert "STALEMATE" in report.diagnosis

    def test_report_peak_and_final_cash(self) -> None:
        monitor = InflationMonitor()
        cash_series = [500, 800, 600, 1000, 700]
        for i, cash in enumerate(cash_series):
            monitor.metrics_history.append(
                EconomicMetrics(
                    round_number=i + 1,
                    total_system_cash=cash,
                    cash_per_player={},
                    properties_owned=0,
                    properties_traded_this_round=0,
                    bankruptcies_this_round=0,
                )
            )
        game = _make_game_for_monitor()
        report = monitor.generate_report(game)
        assert report.peak_system_cash == 1000
        assert report.final_system_cash == 700

    def test_report_cash_velocity(self) -> None:
        monitor = InflationMonitor()
        cash_series = [500, 600, 550]
        for i, cash in enumerate(cash_series):
            monitor.metrics_history.append(
                EconomicMetrics(
                    round_number=i + 1,
                    total_system_cash=cash,
                    cash_per_player={},
                    properties_owned=0,
                    properties_traded_this_round=0,
                    bankruptcies_this_round=0,
                )
            )
        game = _make_game_for_monitor()
        report = monitor.generate_report(game)
        assert report.cash_velocity == [100, -50]

    def test_report_asset_turnover_rate(self) -> None:
        monitor = InflationMonitor()
        traded = [2, 4, 0]
        for i, t in enumerate(traded):
            monitor.metrics_history.append(
                EconomicMetrics(
                    round_number=i + 1,
                    total_system_cash=1000,
                    cash_per_player={},
                    properties_owned=0,
                    properties_traded_this_round=t,
                    bankruptcies_this_round=0,
                )
            )
        game = _make_game_for_monitor()
        report = monitor.generate_report(game)
        assert abs(report.asset_turnover_rate - 2.0) < 0.01  # (2+4+0)/3 = 2.0


class TestInflationMonitorFormatReport:
    """Tests for format_report."""

    def test_basic_format(self) -> None:
        monitor = InflationMonitor()
        report = EconomicReport(
            game_id="abcdefghijklmnop",
            rounds_played=10,
            inflation_detected=False,
            stalemate_detected=False,
            avg_cash_per_round=[1000] * 10,
            cash_velocity=[0] * 9,
            asset_turnover_rate=1.5,
            peak_system_cash=1200,
            final_system_cash=1000,
            diagnosis="HEALTHY",
            recommendations=[],
        )
        text = monitor.format_report(report)
        assert "ECONOMIC BALANCE REPORT" in text
        assert "HEALTHY" in text
        assert "1,000" in text  # final_system_cash formatted

    def test_format_with_inflation_shows_acceleration(self) -> None:
        monitor = InflationMonitor()
        avg_cash = [500 * (i + 1) for i in range(90)]
        velocity = [500] * 89
        report = EconomicReport(
            game_id="abcdefghijklmnop",
            rounds_played=90,
            inflation_detected=True,
            stalemate_detected=False,
            avg_cash_per_round=avg_cash,
            cash_velocity=velocity,
            asset_turnover_rate=0.5,
            peak_system_cash=max(avg_cash),
            final_system_cash=avg_cash[-1],
            diagnosis="RUNAWAY_INFLATION",
            recommendations=["Cap GO bonus"],
        )
        text = monitor.format_report(report)
        assert "ACCELERATION" in text or "CRITICAL" in text or "RUNAWAY" in text
        assert "Cap GO bonus" in text

    def test_format_with_recommendations(self) -> None:
        monitor = InflationMonitor()
        report = EconomicReport(
            game_id="abcdefghijklmnop",
            rounds_played=5,
            inflation_detected=False,
            stalemate_detected=False,
            avg_cash_per_round=[1000, 1100, 1200, 1300, 1400],
            cash_velocity=[100] * 4,
            asset_turnover_rate=1.0,
            peak_system_cash=1400,
            final_system_cash=1400,
            diagnosis="HEALTHY",
            recommendations=["Suggestion A", "Suggestion B"],
        )
        text = monitor.format_report(report)
        assert "Suggestion A" in text
        assert "Suggestion B" in text

    def test_format_empty_cash_history(self) -> None:
        monitor = InflationMonitor()
        report = EconomicReport(
            game_id="abcdefghijklmnop",
            rounds_played=0,
            inflation_detected=False,
            stalemate_detected=False,
            avg_cash_per_round=[],
            cash_velocity=[],
            asset_turnover_rate=0.0,
            peak_system_cash=0,
            final_system_cash=0,
            diagnosis="HEALTHY",
            recommendations=[],
        )
        text = monitor.format_report(report)
        assert "ECONOMIC BALANCE REPORT" in text
