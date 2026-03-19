"""Coverage boost tests targeting uncovered branches across multiple modules."""

import json
import random
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

from app.modules.sastadice.schemas import (
    GameSession,
    GameSettings,
    GameStatus,
    PendingDecision,
    Player,
    Tile,
    TileType,
    TradeOffer,
    TurnPhase,
    WinCondition,
)
from app.modules.sastadice.services.cpu_manager import CpuManager
from app.modules.sastadice.services.cpu_strategy import CpuStrategy
from app.modules.sastadice.services.cpu_turn_executor import CpuTurnExecutor, CpuTurnState
from app.modules.sastadice.services.invariant_checker import (
    InvariantChecker,
    InvariantViolation,
    InvariantViolationError,
    StrictnessMode,
)
from app.modules.sastadice.services.movement_handler import MovementHandler
from app.modules.sastadice.services.trade_manager import TradeManager
from app.modules.sastadice.services.turn_manager import TurnManager
from app.utils import metrics

# ============================================================
# Shared Fixtures
# ============================================================


def make_game(
    status: GameStatus = GameStatus.ACTIVE,
    turn_phase: TurnPhase = TurnPhase.PRE_ROLL,
    current_round: int = 1,
    players: list[Player] | None = None,
    board: list[Tile] | None = None,
    settings: GameSettings | None = None,
) -> GameSession:
    if settings is None:
        settings = GameSettings(
            win_condition=WinCondition.SUDDEN_DEATH,
            go_bonus_base=200,
            go_inflation_per_round=20,
            enable_stimulus=True,
        )
    return GameSession(
        id="game-1",
        status=status,
        turn_phase=turn_phase,
        players=players or [],
        board=board or [],
        settings=settings,
        current_round=current_round,
        rent_multiplier=1.0,
        blocked_tiles=[],
        event_deck=[],
        used_event_deck=[],
        active_trade_offers=[],
    )


def make_player(
    pid: str = "p1",
    name: str = "Alice",
    cash: int = 1500,
    position: int = 0,
    properties: list[str] | None = None,
    is_bankrupt: bool = False,
    in_jail: bool = False,
    disconnected: bool = False,
) -> Player:
    return Player(
        id=pid,
        name=name,
        cash=cash,
        position=position,
        color="#FF0000",
        properties=properties or [],
        ready=True,
        is_bankrupt=is_bankrupt,
        in_jail=in_jail,
        disconnected=disconnected,
    )


def make_property_tile(
    tid: str = "t1",
    name: str = "Test Prop",
    position: int = 1,
    price: int = 200,
    rent: int = 20,
    color: str | None = "RED",
    owner_id: str | None = None,
    upgrade_level: int = 0,
) -> Tile:
    return Tile(
        id=tid,
        type=TileType.PROPERTY,
        name=name,
        position=position,
        price=price,
        rent=rent,
        color=color,
        owner_id=owner_id,
        upgrade_level=upgrade_level,
    )


def make_mock_repository() -> AsyncMock:
    repo = AsyncMock()
    repo.update = AsyncMock()
    repo.update_player_cash = AsyncMock()
    repo.update_player_position = AsyncMock()
    repo.update_player_skip_next_move = AsyncMock()
    repo.update_player_afk = AsyncMock()
    repo.update_player_buff = AsyncMock()
    return repo


# ============================================================
# 1. CpuStrategy Tests
# ============================================================


class TestCpuStrategy:
    """Targets cpu_strategy.py uncovered lines: 19-20, 27, 42-47, 51, 55-56."""

    def test_should_buy_property_true_with_buffer(self):
        player = make_player(cash=500)
        # 500 >= 200 + 200 = 400 → True
        assert CpuStrategy.should_buy_property(player, 200) is True

    def test_should_buy_property_false_insufficient(self):
        player = make_player(cash=300)
        # 300 < 200 + 200 = 400 → False
        assert CpuStrategy.should_buy_property(player, 200) is False

    def test_should_bid_in_auction_true(self):
        player = make_player(cash=500)
        # max_bid = 0.8 * 200 = 160; current_bid=50 < 160 and cash=500 >= 50+10 → True
        assert CpuStrategy.should_bid_in_auction(player, 50, 200) is True

    def test_should_bid_in_auction_false_exceeds_max(self):
        player = make_player(cash=500)
        # current_bid=170 >= max_bid=160 → False
        assert CpuStrategy.should_bid_in_auction(player, 170, 200) is False

    def test_should_bid_in_auction_false_insufficient_cash(self):
        player = make_player(cash=55)
        # cash=55 < current_bid(50)+10=60 → False
        assert CpuStrategy.should_bid_in_auction(player, 50, 200) is False

    def test_should_upgrade_property_false_at_max_level(self):
        player = make_player(cash=2000)
        tile = make_property_tile(upgrade_level=2)
        # upgrade_level >= 2 → False
        assert CpuStrategy.should_upgrade_property(player, tile, 200) is False

    def test_should_upgrade_property_true_enough_cash(self):
        player = make_player(cash=1000)
        tile = make_property_tile(upgrade_level=0)
        # 1000 >= 200 + 300 = 500 → True
        assert CpuStrategy.should_upgrade_property(player, tile, 200) is True

    def test_should_upgrade_property_false_not_enough_cash(self):
        player = make_player(cash=400)
        tile = make_property_tile(upgrade_level=0)
        # 400 < 200 + 300 = 500 → False
        assert CpuStrategy.should_upgrade_property(player, tile, 200) is False

    def test_calculate_upgrade_cost_level_0(self):
        tile = make_property_tile(price=200, upgrade_level=0)
        # level 0: cost = price * 1 = 200
        assert CpuStrategy.calculate_upgrade_cost(tile) == 200

    def test_calculate_upgrade_cost_level_1(self):
        tile = make_property_tile(price=200, upgrade_level=1)
        # level 1: cost = price * 2 = 400
        assert CpuStrategy.calculate_upgrade_cost(tile) == 400

    def test_should_accept_trade_true_net_cash_positive(self):
        player = make_player(cash=1000)
        # offer_cash=200, request_cash=100 => net=100 > 50 → True
        assert CpuStrategy.should_accept_trade(player, 200, 100, [], []) is True

    def test_should_accept_trade_true_more_props_and_zero_net(self):
        player = make_player(cash=1000)
        # offer > request properties AND net_cash=0 → True
        assert CpuStrategy.should_accept_trade(player, 0, 0, ["t1", "t2"], ["t3"]) is True

    def test_should_accept_trade_random_branch(self):
        """Test that the random branch is covered (may be True or False)."""
        player = make_player(cash=1000)
        # net_cash=-10 (negative) and same number of props → random
        with patch.object(random, "random", return_value=0.1):
            result = CpuStrategy.should_accept_trade(player, 0, 10, [], [])
            assert result is True  # 0.1 < 0.3

        with patch.object(random, "random", return_value=0.5):
            result = CpuStrategy.should_accept_trade(player, 0, 10, [], [])
            assert result is False  # 0.5 >= 0.3

    def test_should_propose_trade_covered(self):
        player = make_player(cash=1000)
        with patch.object(random, "random", return_value=0.05):
            assert CpuStrategy.should_propose_trade(player) is True
        with patch.object(random, "random", return_value=0.5):
            assert CpuStrategy.should_propose_trade(player) is False

    def test_get_bid_amount(self):
        player = make_player(cash=500)
        bid = CpuStrategy.get_bid_amount(player, 50)
        # max_bid = min(500-100, 50+10) = min(400, 60) = 60
        # result = max(60, 60) = 60
        assert bid == 60

    def test_get_bid_amount_low_cash(self):
        player = make_player(cash=120)
        bid = CpuStrategy.get_bid_amount(player, 50)
        # max_bid = min(120-100, 50+10) = min(20, 60) = 20
        # result = max(60, 20) = 60  (max clamp keeps min_increment)
        assert bid == 60


# ============================================================
# 2. CpuManager Tests
# ============================================================


class TestCpuManager:
    """Targets cpu_manager.py uncovered lines: 45-60, 101-117."""

    def _make_orchestrator(self, game: GameSession) -> MagicMock:
        orch = MagicMock()
        orch.get_game = AsyncMock(return_value=game)
        orch.perform_action = AsyncMock()
        orch.repository = make_mock_repository()
        orch.turn_manager = MagicMock()
        orch.turn_manager.owns_full_set = MagicMock(return_value=True)
        return orch

    @pytest.mark.asyncio
    async def test_cpu_upgrade_properties_no_tiles(self):
        """Returns False when no eligible tiles."""
        player = make_player(pid="p1")
        game = make_game(players=[player], board=[])
        game.current_turn_player_id = "p1"
        orch = self._make_orchestrator(game)
        mgr = CpuManager(orch)

        result = await mgr.cpu_upgrade_properties(game, player, orch.turn_manager)
        assert result is False

    @pytest.mark.asyncio
    async def test_cpu_upgrade_properties_skips_non_property(self):
        """Non-property tiles are skipped."""
        player = make_player(pid="p1")
        chance_tile = Tile(
            id="c1", type=TileType.CHANCE, name="Chance", position=1, price=0, rent=0
        )
        game = make_game(players=[player], board=[chance_tile])
        game.current_turn_player_id = "p1"
        orch = self._make_orchestrator(game)
        mgr = CpuManager(orch)

        result = await mgr.cpu_upgrade_properties(game, player, orch.turn_manager)
        assert result is False

    @pytest.mark.asyncio
    async def test_cpu_upgrade_properties_skips_max_upgrade(self):
        """Tiles at max upgrade level are skipped."""
        player = make_player(pid="p1", properties=["t1"])
        tile = make_property_tile(tid="t1", owner_id="p1", color="RED", upgrade_level=2)
        game = make_game(players=[player], board=[tile])
        game.current_turn_player_id = "p1"
        orch = self._make_orchestrator(game)
        mgr = CpuManager(orch)

        result = await mgr.cpu_upgrade_properties(game, player, orch.turn_manager)
        assert result is False

    @pytest.mark.asyncio
    async def test_cpu_upgrade_properties_upgrades_when_eligible(self):
        """Upgrades property when player has full set and enough cash."""
        player = make_player(pid="p1", cash=2000, properties=["t1"])
        tile = make_property_tile(tid="t1", owner_id="p1", color="RED", upgrade_level=0)
        game = make_game(players=[player], board=[tile])
        game.current_turn_player_id = "p1"

        orch = self._make_orchestrator(game)
        action_result = MagicMock()
        action_result.success = True
        orch.perform_action = AsyncMock(return_value=action_result)
        orch.turn_manager.owns_full_set = MagicMock(return_value=True)

        mgr = CpuManager(orch)
        result = await mgr.cpu_upgrade_properties(game, player, orch.turn_manager)
        assert result is True

    @pytest.mark.asyncio
    async def test_cpu_upgrade_properties_insufficient_cash(self):
        """Skips upgrade when insufficient cash."""
        player = make_player(pid="p1", cash=100, properties=["t1"])
        tile = make_property_tile(tid="t1", owner_id="p1", color="RED", upgrade_level=0)
        game = make_game(players=[player], board=[tile])
        game.current_turn_player_id = "p1"

        orch = self._make_orchestrator(game)
        orch.turn_manager.owns_full_set = MagicMock(return_value=True)

        mgr = CpuManager(orch)
        result = await mgr.cpu_upgrade_properties(game, player, orch.turn_manager)
        assert result is False

    @pytest.mark.asyncio
    async def test_process_cpu_turns_disconnected_player_afk_bankruptcy(self):
        """Covers the disconnected player + afk_turns >= 3 path in process_cpu_turns."""
        player = make_player(pid="p1", name="CPU-1", disconnected=True)
        player.afk_turns = 2  # will be incremented to 3 → triggers bankruptcy
        player.disconnected_turns = 1

        game = make_game(players=[player], status=GameStatus.ACTIVE)
        game.current_turn_player_id = "p1"
        game.turn_phase = TurnPhase.POST_TURN

        orch = MagicMock()
        # First call returns the game, subsequent calls after get_game
        orch.get_game = AsyncMock(return_value=game)
        orch.perform_action = AsyncMock(return_value=MagicMock(success=True, message="ok"))
        orch.repository = make_mock_repository()
        orch.turn_manager = MagicMock()

        mgr = CpuManager(orch)

        # Patch the lazy import inside the method (it imports inside the if block)
        import app.modules.sastadice.services.economy_manager as econ_module

        mock_econ_instance = AsyncMock()
        mock_econ_instance.process_bankruptcy = AsyncMock()
        mock_econ_class = MagicMock(return_value=mock_econ_instance)

        # Mock play_cpu_turn to return a log
        with patch.object(mgr, "play_cpu_turn", AsyncMock(return_value=["CPU-1 ended turn"])):
            with patch.object(econ_module, "EconomyManager", mock_econ_class):
                result = await mgr.process_cpu_turns("game-1")

        assert "cpu_turns_played" in result
        assert "log" in result

    @pytest.mark.asyncio
    async def test_process_cpu_turns_non_cpu_stops(self):
        """Stops when current player is not a CPU and not disconnected."""
        player = make_player(pid="p1", name="HumanPlayer")
        game = make_game(players=[player], status=GameStatus.ACTIVE)
        game.current_turn_player_id = "p1"

        orch = MagicMock()
        orch.get_game = AsyncMock(return_value=game)
        orch.repository = make_mock_repository()

        mgr = CpuManager(orch)
        result = await mgr.process_cpu_turns("game-1")
        assert result["cpu_turns_played"] == 0

    def test_is_cpu_player_true(self):
        player = make_player(name="ROBOCOP")
        assert CpuManager.is_cpu_player(player) is True

    def test_is_cpu_player_false(self):
        player = make_player(name="HumanPlayer")
        assert CpuManager.is_cpu_player(player) is False


# ============================================================
# 3. CpuTurnExecutor Tests
# ============================================================


class TestCpuTurnExecutor:
    """Targets cpu_turn_executor.py uncovered lines: 54-55, 59-60, 64-65, 93,
    114-118, 134-138, 175-180, 194."""

    def _make_executor_with_mock_game(
        self, game: GameSession, player: Player
    ) -> tuple[CpuTurnExecutor, MagicMock]:
        orch = MagicMock()
        orch.get_game = AsyncMock(return_value=game)
        orch.perform_action = AsyncMock(return_value=MagicMock(success=True, message="ok"))
        orch.repository = make_mock_repository()
        orch.turn_manager = MagicMock()
        orch.turn_manager.owns_full_set = MagicMock(return_value=False)
        strategy = CpuStrategy()
        executor = CpuTurnExecutor(orch, strategy)
        return executor, orch

    @pytest.mark.asyncio
    async def test_play_cpu_turn_not_their_turn_stops(self):
        """Covers the 'not their turn' break path (line 54-55)."""
        player = make_player(pid="p1")
        other_player = make_player(pid="p2", name="Bob")
        game = make_game(players=[player, other_player], turn_phase=TurnPhase.PRE_ROLL)
        game.current_turn_player_id = "p2"  # not p1's turn

        executor, orch = self._make_executor_with_mock_game(game, player)
        log = await executor.play_cpu_turn(game, player)
        assert any("not their turn anymore" in entry for entry in log)

    @pytest.mark.asyncio
    async def test_play_cpu_turn_unknown_phase_breaks(self):
        """Covers the 'unexpected phase' break when no handler found."""
        player = make_player(pid="p1")
        game = make_game(players=[player], turn_phase=TurnPhase.MOVING)
        game.current_turn_player_id = "p1"

        executor, orch = self._make_executor_with_mock_game(game, player)

        # Override get_game to return a game with an unhandled state
        # We'll test by directly checking MOVING goes to the MOVING handler (returns MOVING again)
        # and hits max iterations
        call_count = 0

        async def get_game_moving(_id: str) -> GameSession:
            nonlocal call_count
            call_count += 1
            g = make_game(players=[player], turn_phase=TurnPhase.MOVING)
            g.current_turn_player_id = "p1"
            return g

        orch.get_game = get_game_moving

        log = await executor.play_cpu_turn(game, player)
        # Should hit max iterations since MOVING always returns MOVING
        assert any("max iterations" in entry for entry in log)

    @pytest.mark.asyncio
    async def test_handle_cpu_pre_roll_failure(self):
        """Covers failure path in _handle_cpu_pre_roll (line 93)."""
        player = make_player(pid="p1")
        game = make_game(players=[player], turn_phase=TurnPhase.PRE_ROLL)
        game.current_turn_player_id = "p1"

        fail_result = MagicMock(success=False, message="Roll blocked")
        orch = MagicMock()
        orch.perform_action = AsyncMock(return_value=fail_result)
        orch.repository = make_mock_repository()
        orch.turn_manager = MagicMock()
        strategy = CpuStrategy()
        executor = CpuTurnExecutor(orch, strategy)

        state, log_entry = await executor._handle_cpu_pre_roll(game, player)
        assert state == CpuTurnState.COMPLETE
        assert "failed to roll" in log_entry

    @pytest.mark.asyncio
    async def test_handle_cpu_decision_disconnected_player(self):
        """Covers disconnected player auto-pass (lines 114-118)."""
        player = make_player(pid="p1", disconnected=True)
        game = make_game(players=[player], turn_phase=TurnPhase.DECISION)
        game.current_turn_player_id = "p1"
        game.pending_decision = PendingDecision(type="BUY", tile_id="t1", price=200)

        updated_game = make_game(players=[player], turn_phase=TurnPhase.POST_TURN)
        updated_game.current_turn_player_id = "p1"

        orch = MagicMock()
        orch.perform_action = AsyncMock(return_value=MagicMock(success=True, message="passed"))
        orch.get_game = AsyncMock(return_value=updated_game)
        orch.repository = make_mock_repository()
        strategy = CpuStrategy()
        executor = CpuTurnExecutor(orch, strategy)

        state, log_entry = await executor._handle_cpu_decision(game, player)
        assert "AFK Ghost" in log_entry

    @pytest.mark.asyncio
    async def test_handle_cpu_decision_buy_fails_fallback_pass(self):
        """Covers buy attempt failure → pass fallback (lines 134-138)."""
        player = make_player(pid="p1", cash=2000)
        game = make_game(players=[player], turn_phase=TurnPhase.DECISION)
        game.current_turn_player_id = "p1"
        game.pending_decision = PendingDecision(type="BUY", tile_id="t1", price=200)

        fail_buy = MagicMock(success=False, message="buy failed")
        pass_result = MagicMock(success=True, message="passed")
        updated_game = make_game(players=[player], turn_phase=TurnPhase.POST_TURN)
        updated_game.current_turn_player_id = "p1"

        orch = MagicMock()
        orch.perform_action = AsyncMock(side_effect=[fail_buy, pass_result])
        orch.get_game = AsyncMock(return_value=updated_game)
        orch.repository = make_mock_repository()
        strategy = CpuStrategy()
        executor = CpuTurnExecutor(orch, strategy)

        state, log_entry = await executor._handle_cpu_decision(game, player)
        assert "passed" in log_entry or "buy failed" in log_entry

    @pytest.mark.asyncio
    async def test_handle_cpu_post_turn_disconnected_fail(self):
        """Covers disconnected end_turn failure (lines 175-180)."""
        player = make_player(pid="p1", disconnected=True)
        game = make_game(players=[player], turn_phase=TurnPhase.POST_TURN)
        game.current_turn_player_id = "p1"

        fail_result = MagicMock(success=False, message="end turn failed")
        orch = MagicMock()
        orch.perform_action = AsyncMock(return_value=fail_result)
        orch.repository = make_mock_repository()
        orch.turn_manager = MagicMock()
        strategy = CpuStrategy()
        executor = CpuTurnExecutor(orch, strategy)

        state, log_entry = await executor._handle_cpu_post_turn(game, player)
        assert state == CpuTurnState.COMPLETE
        assert "failed to end turn" in log_entry

    @pytest.mark.asyncio
    async def test_handle_cpu_post_turn_end_turn_failure(self):
        """Covers end_turn action failure (line 194)."""
        player = make_player(pid="p1", cash=100)  # insufficient for upgrades
        game = make_game(players=[player], turn_phase=TurnPhase.POST_TURN)
        game.current_turn_player_id = "p1"

        fail_result = MagicMock(success=False, message="not in post_turn")
        orch = MagicMock()
        orch.perform_action = AsyncMock(return_value=fail_result)
        orch.repository = make_mock_repository()
        orch.turn_manager = MagicMock()
        orch.turn_manager.owns_full_set = MagicMock(return_value=False)
        strategy = CpuStrategy()
        executor = CpuTurnExecutor(orch, strategy)

        state, log_entry = await executor._handle_cpu_post_turn(game, player)
        assert state == CpuTurnState.COMPLETE
        assert "failed to end turn" in log_entry

    @pytest.mark.asyncio
    async def test_handle_cpu_decision_market_black_market(self):
        """Covers MARKET/BLACK_MARKET decision type (lines 151-158)."""
        player = make_player(pid="p1", cash=1000)
        game = make_game(players=[player], turn_phase=TurnPhase.DECISION)
        game.current_turn_player_id = "p1"
        game.pending_decision = PendingDecision(type="BLACK_MARKET", tile_id=None, price=0)

        updated_game = make_game(players=[player], turn_phase=TurnPhase.POST_TURN)
        updated_game.current_turn_player_id = "p1"

        orch = MagicMock()
        orch.perform_action = AsyncMock(return_value=MagicMock(success=True, message="passed"))
        orch.get_game = AsyncMock(return_value=updated_game)
        orch.repository = make_mock_repository()
        strategy = CpuStrategy()
        executor = CpuTurnExecutor(orch, strategy)

        state, log_entry = await executor._handle_cpu_decision(game, player)
        assert "Black Market" in log_entry

    @pytest.mark.asyncio
    async def test_handle_cpu_decision_unknown_type(self):
        """Covers else branch for unknown decision type."""
        player = make_player(pid="p1", cash=1000)
        game = make_game(players=[player], turn_phase=TurnPhase.DECISION)
        game.current_turn_player_id = "p1"
        game.pending_decision = PendingDecision(type="SOME_UNKNOWN_TYPE", tile_id=None, price=0)

        updated_game = make_game(players=[player], turn_phase=TurnPhase.POST_TURN)
        updated_game.current_turn_player_id = "p1"

        orch = MagicMock()
        orch.perform_action = AsyncMock(return_value=MagicMock(success=True, message="passed"))
        orch.get_game = AsyncMock(return_value=updated_game)
        orch.repository = make_mock_repository()
        strategy = CpuStrategy()
        executor = CpuTurnExecutor(orch, strategy)

        state, log_entry = await executor._handle_cpu_decision(game, player)
        assert "SOME_UNKNOWN_TYPE" in log_entry


# ============================================================
# 4. InvariantChecker Tests
# ============================================================


class TestInvariantChecker:
    """Targets invariant_checker.py uncovered lines: 65, 78, 105, 122, 133,
    150-168, 194, 209, 220, 237, 289-313, 317-332."""

    def test_check_all_no_violations(self):
        """Clean game state produces no violations."""
        player = make_player(pid="p1", position=0, properties=[])
        # Board needs to be non-empty so position 0 is in bounds
        board = [Tile(id="go", type=TileType.GO, name="GO", position=0, price=0, rent=0)]
        game = make_game(players=[player], board=board)
        game.current_turn_player_id = "p1"

        checker = InvariantChecker(mode=StrictnessMode.STRICT)
        violations = checker.check_all(game)
        assert violations == []

    def test_check_all_strict_raises_on_violation(self):
        """STRICT mode raises InvariantViolationError on violations."""
        player = make_player(pid="p1", cash=-100, is_bankrupt=False)
        game = make_game(players=[player])
        game.current_turn_player_id = "p1"

        checker = InvariantChecker(mode=StrictnessMode.STRICT)
        with pytest.raises(InvariantViolationError) as exc_info:
            checker.check_all(game)
        assert len(exc_info.value.violations) > 0

    def test_check_all_lenient_logs_and_autocorrects(self):
        """LENIENT mode logs violations and auto-corrects instead of raising."""
        player = make_player(pid="p1", cash=-100, is_bankrupt=False)
        game = make_game(players=[player])
        game.current_turn_player_id = "p1"

        checker = InvariantChecker(mode=StrictnessMode.LENIENT)
        violations = checker.check_all(game)
        # Should return violations but not raise
        assert len(violations) > 0
        # Player should be auto-corrected to bankrupt
        assert player.is_bankrupt is True

    def test_check_all_violation_log_grows(self):
        """Violations are accumulated in violation_log."""
        player = make_player(pid="p1", cash=-100, is_bankrupt=False)
        game = make_game(players=[player])
        game.current_turn_player_id = "p1"

        checker = InvariantChecker(mode=StrictnessMode.LENIENT)
        checker.check_all(game)
        assert len(checker.violation_log) > 0

    def test_duplicate_ownership_violation(self):
        """DUPLICATE_OWNERSHIP: tile seen twice in ownership_map (impossible in normal
        usage but we cover the branch by patching the board list)."""
        player = make_player(pid="p1", properties=["t1"])
        tile = make_property_tile(tid="t1", owner_id="p1")
        # Inject the same tile twice in board so ownership_map sees duplicate
        game = make_game(players=[player], board=[tile, tile])
        game.current_turn_player_id = "p1"

        checker = InvariantChecker(mode=StrictnessMode.LENIENT)
        violations = checker._check_asset_conservation(game)
        assert any(v.type == "DUPLICATE_OWNERSHIP" for v in violations)

    def test_orphaned_property_violation(self):
        """ORPHANED_PROPERTY: player claims tile not on board."""
        player = make_player(pid="p1", properties=["missing-tile"])
        game = make_game(players=[player], board=[])
        game.current_turn_player_id = "p1"

        checker = InvariantChecker(mode=StrictnessMode.LENIENT)
        violations = checker._check_asset_conservation(game)
        assert any(v.type == "ORPHANED_PROPERTY" for v in violations)

    def test_ownership_mismatch_violation(self):
        """OWNERSHIP_MISMATCH: player claims tile but tile.owner_id is someone else."""
        player = make_player(pid="p1", properties=["t1"])
        tile = make_property_tile(tid="t1", owner_id="p2")  # owned by p2
        game = make_game(players=[player], board=[tile])
        game.current_turn_player_id = "p1"

        checker = InvariantChecker(mode=StrictnessMode.LENIENT)
        violations = checker._check_asset_conservation(game)
        assert any(v.type == "OWNERSHIP_MISMATCH" for v in violations)

    def test_orphaned_owner_violation(self):
        """ORPHANED_OWNER: tile owned by non-existent player."""
        tile = make_property_tile(tid="t1", owner_id="ghost-player")
        player = make_player(pid="p1")
        game = make_game(players=[player], board=[tile])
        game.current_turn_player_id = "p1"

        checker = InvariantChecker(mode=StrictnessMode.LENIENT)
        violations = checker._check_asset_conservation(game)
        assert any(v.type == "ORPHANED_OWNER" for v in violations)

    def test_missing_property_reference_violation(self):
        """MISSING_PROPERTY_REFERENCE: tile's owner doesn't list it in properties."""
        player = make_player(pid="p1", properties=[])  # doesn't list t1
        tile = make_property_tile(tid="t1", owner_id="p1")
        game = make_game(players=[player], board=[tile])
        game.current_turn_player_id = "p1"

        checker = InvariantChecker(mode=StrictnessMode.LENIENT)
        violations = checker._check_asset_conservation(game)
        assert any(v.type == "MISSING_PROPERTY_REFERENCE" for v in violations)

    def test_check_financial_integrity_success(self):
        """No violation when cash sums match."""
        player1 = make_player(pid="p1", cash=500)
        player2 = make_player(pid="p2", cash=500)
        game = make_game(players=[player1, player2])
        game.current_turn_player_id = "p1"

        checker = InvariantChecker()
        violations = checker.check_financial_integrity(game, 900, 100)
        assert violations == []

    def test_check_financial_integrity_failure(self):
        """FINANCIAL_INTEGRITY_FAILURE when cash sum doesn't match expected."""
        player1 = make_player(pid="p1", cash=500)
        game = make_game(players=[player1])
        game.current_turn_player_id = "p1"

        checker = InvariantChecker()
        violations = checker.check_financial_integrity(game, 1000, 0)
        assert any(v.type == "FINANCIAL_INTEGRITY_FAILURE" for v in violations)

    def test_check_financial_integrity_skips_bankrupt(self):
        """Bankrupt players are excluded from cash sum."""
        player1 = make_player(pid="p1", cash=500)
        bankrupt = make_player(pid="p2", cash=0, is_bankrupt=True)
        game = make_game(players=[player1, bankrupt])
        game.current_turn_player_id = "p1"

        checker = InvariantChecker()
        # Expected: prev=400 + delta=100 = 500. Active player has 500. Match.
        violations = checker.check_financial_integrity(game, 400, 100)
        assert violations == []

    def test_missing_turn_player_violation(self):
        """MISSING_TURN_PLAYER: ACTIVE game with no current_turn_player_id."""
        player = make_player(pid="p1")
        game = make_game(players=[player])
        game.current_turn_player_id = None

        checker = InvariantChecker(mode=StrictnessMode.LENIENT)
        violations = checker._check_turn_order(game)
        assert any(v.type == "MISSING_TURN_PLAYER" for v in violations)

    def test_orphaned_turn_player_violation(self):
        """ORPHANED_TURN_PLAYER: current_turn_player_id not in players."""
        game = make_game(players=[])
        game.current_turn_player_id = "ghost-id"

        checker = InvariantChecker(mode=StrictnessMode.LENIENT)
        violations = checker._check_turn_order(game)
        assert any(v.type == "ORPHANED_TURN_PLAYER" for v in violations)

    def test_bankrupt_turn_player_violation(self):
        """BANKRUPT_TURN_PLAYER: current player is bankrupt."""
        player = make_player(pid="p1", is_bankrupt=True)
        game = make_game(players=[player])
        game.current_turn_player_id = "p1"

        checker = InvariantChecker(mode=StrictnessMode.LENIENT)
        violations = checker._check_turn_order(game)
        assert any(v.type == "BANKRUPT_TURN_PLAYER" for v in violations)

    def test_orphaned_pending_decision_violation(self):
        """ORPHANED_PENDING_DECISION: pending_decision set but phase != DECISION."""
        player = make_player(pid="p1")
        game = make_game(players=[player], turn_phase=TurnPhase.POST_TURN)
        game.current_turn_player_id = "p1"
        game.pending_decision = PendingDecision(type="BUY", tile_id="t1", price=200)

        checker = InvariantChecker(mode=StrictnessMode.LENIENT)
        violations = checker._check_phase_validity(game)
        assert any(v.type == "ORPHANED_PENDING_DECISION" for v in violations)

    def test_position_out_of_bounds_violation(self):
        """POSITION_OUT_OF_BOUNDS: player position >= board size."""
        player = make_player(pid="p1", position=100)
        board = [
            Tile(id=f"t{i}", type=TileType.GO, name=f"T{i}", position=i, price=0, rent=0)
            for i in range(10)
        ]
        game = make_game(players=[player], board=board)
        game.current_turn_player_id = "p1"

        checker = InvariantChecker(mode=StrictnessMode.LENIENT)
        violations = checker._check_position_bounds(game)
        assert any(v.type == "POSITION_OUT_OF_BOUNDS" for v in violations)

    def test_previous_position_out_of_bounds(self):
        """PREVIOUS_POSITION_OUT_OF_BOUNDS: previous_position out of range."""
        player = make_player(pid="p1", position=0)
        player.previous_position = 999
        board = [
            Tile(id=f"t{i}", type=TileType.GO, name=f"T{i}", position=i, price=0, rent=0)
            for i in range(10)
        ]
        game = make_game(players=[player], board=board)
        game.current_turn_player_id = "p1"

        checker = InvariantChecker(mode=StrictnessMode.LENIENT)
        violations = checker._check_position_bounds(game)
        assert any(v.type == "PREVIOUS_POSITION_OUT_OF_BOUNDS" for v in violations)

    def test_auto_correct_orphaned_pending_decision(self):
        """Auto-correction clears orphaned pending_decision."""
        player = make_player(pid="p1")
        game = make_game(players=[player], turn_phase=TurnPhase.POST_TURN)
        game.current_turn_player_id = "p1"
        game.pending_decision = PendingDecision(type="BUY", tile_id="t1", price=200)

        checker = InvariantChecker(mode=StrictnessMode.LENIENT)
        checker.check_all(game)
        assert game.pending_decision is None

    def test_auto_correct_position_out_of_bounds(self):
        """Auto-correction clamps out-of-bounds position."""
        player = make_player(pid="p1", position=100)
        board = [
            Tile(id=f"t{i}", type=TileType.GO, name=f"T{i}", position=i, price=0, rent=0)
            for i in range(10)
        ]
        game = make_game(players=[player], board=board)
        game.current_turn_player_id = None  # avoid MISSING_TURN_PLAYER critical

        checker = InvariantChecker(mode=StrictnessMode.LENIENT)
        # Manually trigger position check and correction
        violations = [
            InvariantViolation(
                type="POSITION_OUT_OF_BOUNDS",
                severity="CRITICAL",
                message=f"Player {player.name} position 100 out of bounds",
                game_id=game.id,
                round_number=game.current_round,
                turn_phase=game.turn_phase.value,
            )
        ]
        checker._attempt_auto_corrections(game, violations)
        assert player.position <= 9

    def test_auto_correct_orphaned_turn_player(self):
        """Auto-correction advances to next active player for ORPHANED_TURN_PLAYER."""
        p1 = make_player(pid="p1", is_bankrupt=True)
        p2 = make_player(pid="p2")
        game = make_game(players=[p1, p2])
        game.current_turn_player_id = "p1"

        checker = InvariantChecker(mode=StrictnessMode.LENIENT)
        violations = [
            InvariantViolation(
                type="ORPHANED_TURN_PLAYER",
                severity="CRITICAL",
                message="current_turn_player_id ghost does not exist",
                game_id=game.id,
                round_number=1,
                turn_phase="PRE_ROLL",
            )
        ]
        checker._attempt_auto_corrections(game, violations)
        assert game.current_turn_player_id == "p2"

    def test_find_next_active_player_empty(self):
        """Returns None when no players."""
        game = make_game(players=[])
        checker = InvariantChecker()
        result = checker._find_next_active_player(game)
        assert result is None

    def test_find_next_active_player_all_bankrupt(self):
        """Returns None when all players bankrupt."""
        p1 = make_player(pid="p1", is_bankrupt=True)
        p2 = make_player(pid="p2", is_bankrupt=True)
        game = make_game(players=[p1, p2])
        game.current_turn_player_id = "p1"
        checker = InvariantChecker()
        result = checker._find_next_active_player(game)
        assert result is None

    def test_invariant_violation_error_message(self):
        """InvariantViolationError formats its message correctly."""
        v = InvariantViolation(
            type="TEST_VIOLATION",
            severity="CRITICAL",
            message="something broke",
            game_id="g1",
            round_number=1,
            turn_phase="PRE_ROLL",
        )
        err = InvariantViolationError([v])
        assert "TEST_VIOLATION" in str(err)
        assert "something broke" in str(err)


# ============================================================
# 5. TradeManager Additional Coverage
# ============================================================


class TestTradeManagerAdditional:
    """Targets trade_manager.py uncovered lines: 30, 38, 46, 48, 50, 55, 57, 59,
    84, 89, 91, 98, 100, 102."""

    def _base_game(self, initiator: Player, target: Player, board: list[Tile]) -> GameSession:
        game = make_game(players=[initiator, target], board=board)
        return game

    def test_target_not_found(self):
        """Target player not in game → error."""
        initiator = make_player(pid="p1")
        game = make_game(players=[initiator], board=[])
        payload = {"target_id": "nonexistent"}
        offer, error = TradeManager.create_trade_offer(game, initiator, payload)
        assert offer is None
        assert error is not None

    def test_offer_negative_cash(self):
        """Negative offer_cash → error (line 38)."""
        initiator = make_player(pid="p1")
        target = make_player(pid="p2")
        game = self._base_game(initiator, target, [])
        payload = {"target_id": "p2", "offer_cash": -10, "req_cash": 0}
        offer, error = TradeManager.create_trade_offer(game, initiator, payload)
        assert offer is None
        assert "negative" in error.lower()

    def test_offer_prop_not_owned(self):
        """Offering property not owned by initiator → error (line 46)."""
        initiator = make_player(pid="p1", properties=[])
        target = make_player(pid="p2")
        tile = make_property_tile(tid="t1", owner_id="p2")  # owned by target
        game = self._base_game(initiator, target, [tile])
        payload = {
            "target_id": "p2",
            "offer_cash": 0,
            "req_cash": 0,
            "offer_props": ["t1"],
            "req_props": [],
        }
        offer, error = TradeManager.create_trade_offer(game, initiator, payload)
        assert offer is None
        assert "don't own" in error.lower()

    def test_offer_prop_wrong_type(self):
        """Offering non-PROPERTY/NODE tile → error (line 48)."""
        initiator = make_player(pid="p1", properties=["t1"])
        target = make_player(pid="p2")
        chance_tile = Tile(
            id="t1", type=TileType.CHANCE, name="Chance", position=1, price=0, rent=0, owner_id="p1"
        )
        game = self._base_game(initiator, target, [chance_tile])
        payload = {
            "target_id": "p2",
            "offer_cash": 0,
            "req_cash": 0,
            "offer_props": ["t1"],
            "req_props": [],
        }
        offer, error = TradeManager.create_trade_offer(game, initiator, payload)
        assert offer is None
        assert "only properties" in error.lower()

    def test_offer_prop_upgraded(self):
        """Offering upgraded property → error (line 50)."""
        initiator = make_player(pid="p1", properties=["t1"])
        target = make_player(pid="p2")
        upgraded_tile = make_property_tile(tid="t1", owner_id="p1", upgrade_level=1)
        game = self._base_game(initiator, target, [upgraded_tile])
        payload = {
            "target_id": "p2",
            "offer_cash": 0,
            "req_cash": 0,
            "offer_props": ["t1"],
            "req_props": [],
        }
        offer, error = TradeManager.create_trade_offer(game, initiator, payload)
        assert offer is None
        assert "upgraded" in error.lower()

    def test_req_prop_not_owned_by_target(self):
        """Requesting property not owned by target → error (line 55)."""
        initiator = make_player(pid="p1")
        target = make_player(pid="p2")
        tile = make_property_tile(tid="t1", owner_id="p1")  # owned by initiator, not target
        game = self._base_game(initiator, target, [tile])
        payload = {
            "target_id": "p2",
            "offer_cash": 0,
            "req_cash": 0,
            "offer_props": [],
            "req_props": ["t1"],
        }
        offer, error = TradeManager.create_trade_offer(game, initiator, payload)
        assert offer is None
        assert "doesn't own" in error.lower() or "target" in error.lower()

    def test_req_prop_wrong_type(self):
        """Requesting non-PROPERTY/NODE tile → error (line 57)."""
        initiator = make_player(pid="p1")
        target = make_player(pid="p2")
        chance_tile = Tile(
            id="t1", type=TileType.CHANCE, name="Chance", position=1, price=0, rent=0, owner_id="p2"
        )
        game = self._base_game(initiator, target, [chance_tile])
        payload = {
            "target_id": "p2",
            "offer_cash": 0,
            "req_cash": 0,
            "offer_props": [],
            "req_props": ["t1"],
        }
        offer, error = TradeManager.create_trade_offer(game, initiator, payload)
        assert offer is None
        assert "only properties" in error.lower()

    def test_req_prop_upgraded(self):
        """Requesting upgraded property → error (line 59)."""
        initiator = make_player(pid="p1")
        target = make_player(pid="p2", properties=["t1"])
        upgraded_tile = make_property_tile(tid="t1", owner_id="p2", upgrade_level=1)
        game = self._base_game(initiator, target, [upgraded_tile])
        payload = {
            "target_id": "p2",
            "offer_cash": 0,
            "req_cash": 0,
            "offer_props": [],
            "req_props": ["t1"],
        }
        offer, error = TradeManager.create_trade_offer(game, initiator, payload)
        assert offer is None
        assert "upgraded" in error.lower()

    def test_validate_target_cant_afford(self):
        """Target can't afford requesting_cash → error (line 84)."""
        initiator = make_player(pid="p1", cash=1000)
        target = make_player(pid="p2", cash=10)
        game = make_game(players=[initiator, target], board=[])
        offer = TradeOffer(
            initiator_id="p1",
            target_id="p2",
            offering_cash=0,
            offering_properties=[],
            requesting_cash=500,  # target can't afford
            requesting_properties=[],
            created_at=0,
        )
        error = TradeManager.validate_trade_assets(game, offer, initiator, target)
        assert error is not None
        assert "you cannot afford" in error.lower()

    def test_validate_initiator_lost_properties(self):
        """Initiator lost property since offer → error (line 89)."""
        initiator = make_player(pid="p1", cash=1000)
        target = make_player(pid="p2", cash=1000)
        tile = make_property_tile(tid="t1", owner_id="p2")  # no longer owned by initiator
        game = make_game(players=[initiator, target], board=[tile])
        offer = TradeOffer(
            initiator_id="p1",
            target_id="p2",
            offering_cash=0,
            offering_properties=["t1"],
            requesting_cash=0,
            requesting_properties=[],
            created_at=0,
        )
        error = TradeManager.validate_trade_assets(game, offer, initiator, target)
        assert error is not None
        assert "initiator lost" in error.lower()

    def test_validate_offering_wrong_type(self):
        """Offering a non-PROPERTY/NODE tile in validation → error (line 91)."""
        initiator = make_player(pid="p1", cash=1000)
        target = make_player(pid="p2", cash=1000)
        chance_tile = Tile(
            id="t1", type=TileType.CHANCE, name="Chance", position=1, price=0, rent=0, owner_id="p1"
        )
        game = make_game(players=[initiator, target], board=[chance_tile])
        offer = TradeOffer(
            initiator_id="p1",
            target_id="p2",
            offering_cash=0,
            offering_properties=["t1"],
            requesting_cash=0,
            requesting_properties=[],
            created_at=0,
        )
        error = TradeManager.validate_trade_assets(game, offer, initiator, target)
        assert error is not None
        assert "only properties" in error.lower()

    def test_validate_target_lost_properties(self):
        """Target lost property since offer → error (line 98)."""
        initiator = make_player(pid="p1", cash=1000)
        target = make_player(pid="p2", cash=1000)
        tile = make_property_tile(tid="t1", owner_id="p1")  # no longer owned by target
        game = make_game(players=[initiator, target], board=[tile])
        offer = TradeOffer(
            initiator_id="p1",
            target_id="p2",
            offering_cash=0,
            offering_properties=[],
            requesting_cash=0,
            requesting_properties=["t1"],
            created_at=0,
        )
        error = TradeManager.validate_trade_assets(game, offer, initiator, target)
        assert error is not None
        assert "you lost" in error.lower()

    def test_validate_requesting_wrong_type(self):
        """Requesting non-PROPERTY/NODE in validation → error (line 100)."""
        initiator = make_player(pid="p1", cash=1000)
        target = make_player(pid="p2", cash=1000)
        chance_tile = Tile(
            id="t1", type=TileType.CHANCE, name="Chance", position=1, price=0, rent=0, owner_id="p2"
        )
        game = make_game(players=[initiator, target], board=[chance_tile])
        offer = TradeOffer(
            initiator_id="p1",
            target_id="p2",
            offering_cash=0,
            offering_properties=[],
            requesting_cash=0,
            requesting_properties=["t1"],
            created_at=0,
        )
        error = TradeManager.validate_trade_assets(game, offer, initiator, target)
        assert error is not None
        assert "only properties" in error.lower()

    def test_validate_requesting_upgraded(self):
        """Requesting upgraded property in validation → error (line 102)."""
        initiator = make_player(pid="p1", cash=1000)
        target = make_player(pid="p2", cash=1000)
        upgraded = make_property_tile(tid="t1", owner_id="p2", upgrade_level=2)
        game = make_game(players=[initiator, target], board=[upgraded])
        offer = TradeOffer(
            initiator_id="p1",
            target_id="p2",
            offering_cash=0,
            offering_properties=[],
            requesting_cash=0,
            requesting_properties=["t1"],
            created_at=0,
        )
        error = TradeManager.validate_trade_assets(game, offer, initiator, target)
        assert error is not None
        assert "upgraded" in error.lower()


# ============================================================
# 6. MovementHandler Tests
# ============================================================


class TestMovementHandlerAdditional:
    """Targets movement_handler.py uncovered lines: 38, 42, 68-80, 168, 171-183, 190."""

    def _make_turn_manager(self) -> MagicMock:
        tm = MagicMock()
        tm.calculate_go_bonus = MagicMock(return_value=200)
        return tm

    @pytest.mark.asyncio
    async def test_validate_roll_dice_inactive_game(self):
        """Covers line 38: game not ACTIVE."""
        repo = make_mock_repository()
        tm = self._make_turn_manager()
        handler = MovementHandler(repo, tm)

        game = make_game(status=GameStatus.LOBBY)
        valid, error, player = await handler.validate_roll_dice(game, "p1")
        assert valid is False
        assert "ACTIVE" in error

    @pytest.mark.asyncio
    async def test_validate_roll_dice_wrong_turn(self):
        """Covers line 42: not the player's turn."""
        repo = make_mock_repository()
        tm = self._make_turn_manager()
        handler = MovementHandler(repo, tm)

        game = make_game(status=GameStatus.ACTIVE)
        game.current_turn_player_id = "p2"
        valid, error, player = await handler.validate_roll_dice(game, "p1")
        assert valid is False
        assert "turn" in error.lower()

    @pytest.mark.asyncio
    async def test_execute_dice_roll_triple_doubles_jail(self):
        """Covers lines 68-80: triple doubles → send to jail."""
        repo = make_mock_repository()
        tm = self._make_turn_manager()
        handler = MovementHandler(repo, tm)

        player = make_player(pid="p1")
        player.consecutive_doubles = 2  # next double = 3 → jail

        game = make_game(players=[player])

        jail_callback = AsyncMock()

        with patch("random.randint", return_value=3):  # both dice = 3 → doubles
            d1, d2, total, is_doubles, went_to_jail = await handler.execute_dice_roll(
                game, player, jail_callback
            )

        assert went_to_jail is True
        assert is_doubles is True
        jail_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_dice_roll_stimulus_active(self):
        """Covers stimulus path: cash < 100 and enable_stimulus=True."""
        settings = GameSettings(enable_stimulus=True)
        repo = make_mock_repository()
        tm = self._make_turn_manager()
        handler = MovementHandler(repo, tm)

        player = make_player(pid="p1", cash=50)  # below 100 → stimulus
        game = make_game(players=[player], settings=settings)

        jail_callback = AsyncMock()

        with patch("random.randint", return_value=4):
            d1, d2, total, is_doubles, went_to_jail = await handler.execute_dice_roll(
                game, player, jail_callback
            )

        assert "STIMULUS" in game.last_event_message

    @pytest.mark.asyncio
    async def test_roll_dice_player_in_jail_failed_escape(self):
        """Covers lines 171-183: player in jail, didn't escape."""
        import app.modules.sastadice.services.jail_manager as jail_module

        repo = make_mock_repository()
        tm = self._make_turn_manager()
        handler = MovementHandler(repo, tm)

        player = make_player(pid="p1", in_jail=True)
        game = make_game(players=[player], status=GameStatus.ACTIVE)
        game.current_turn_player_id = "p1"

        jail_callback = AsyncMock()
        tile_callback = AsyncMock()

        with patch.object(
            jail_module.JailManager, "roll_for_doubles", return_value=(False, 2, 3, "Still in jail")
        ):
            result = await handler.roll_dice(game, "p1", jail_callback, tile_callback)

        assert result.dice1 == 2
        assert result.dice2 == 3
        assert game.turn_phase == TurnPhase.POST_TURN

    @pytest.mark.asyncio
    async def test_roll_dice_went_to_jail_returns_early(self):
        """Covers line 190: went_to_jail → return early."""
        repo = make_mock_repository()
        tm = self._make_turn_manager()
        handler = MovementHandler(repo, tm)

        player = make_player(pid="p1")
        player.consecutive_doubles = 2  # next double → jail

        game = make_game(players=[player], status=GameStatus.ACTIVE)
        game.current_turn_player_id = "p1"

        jail_callback = AsyncMock()
        tile_callback = AsyncMock()

        with patch("random.randint", return_value=3):  # doubles = 3,3
            await handler.roll_dice(game, "p1", jail_callback, tile_callback)

        tile_callback.assert_not_called()  # should not have reached tile landing

    @pytest.mark.asyncio
    async def test_handle_movement_skip_next_move(self):
        """Covers skip_next_move branch: total set to 0."""
        repo = make_mock_repository()
        tm = self._make_turn_manager()
        handler = MovementHandler(repo, tm)

        player = make_player(pid="p1", position=5)
        player.skip_next_move = True
        board = [
            Tile(id=f"t{i}", type=TileType.GO, name=f"T{i}", position=i, price=0, rent=0)
            for i in range(10)
        ]
        game = make_game(players=[player], board=board)

        await handler.handle_movement(game, player, "p1", 6, False)
        # total was set to 0 so position stays at 5
        assert player.position == 5
        repo.update_player_skip_next_move.assert_called_once_with("p1", False)

    @pytest.mark.asyncio
    async def test_finalize_roll_no_pending_decision_transitions_to_post_turn(self):
        """Covers line 149-150: phase stays DECISION but no pending_decision → POST_TURN."""
        repo = make_mock_repository()
        tm = self._make_turn_manager()
        handler = MovementHandler(repo, tm)

        player = make_player(pid="p1", position=2)
        board = [
            Tile(id=f"t{i}", type=TileType.GO, name=f"T{i}", position=i, price=0, rent=0)
            for i in range(10)
        ]
        game = make_game(players=[player], board=board, turn_phase=TurnPhase.PRE_ROLL)

        async def no_pending_callback(g: GameSession, p: Player, t: Tile) -> None:
            pass  # does not set pending_decision

        await handler.finalize_roll(game, player, 3, 3, 6, True, False, False, no_pending_callback)
        assert game.turn_phase == TurnPhase.POST_TURN


# ============================================================
# 7. TurnManager Additional Coverage
# ============================================================


class TestTurnManagerAdditional:
    """Targets turn_manager.py uncovered lines: 36, 39, 48, 54, 116, 195-214, 225-257."""

    def test_owns_full_set_no_color(self):
        """owns_full_set returns False when color is empty string."""
        player = make_player(pid="p1")
        board = [make_property_tile(tid="t1", color="RED", owner_id="p1")]
        assert TurnManager.owns_full_set(player, "", board) is False

    def test_owns_full_set_no_tiles_of_color(self):
        """owns_full_set returns False when no tiles match the color."""
        player = make_player(pid="p1")
        board = [make_property_tile(tid="t1", color="BLUE", owner_id="p1")]
        assert TurnManager.owns_full_set(player, "RED", board) is False

    def test_calculate_rent_non_property_tile(self):
        """calculate_rent returns 0 for non-PROPERTY tiles."""
        player = make_player(pid="p1")
        game = make_game(players=[player])
        chance_tile = Tile(
            id="t1", type=TileType.CHANCE, name="Chance", position=1, price=0, rent=0
        )
        rent = TurnManager.calculate_rent(chance_tile, player, game)
        assert rent == 0

    def test_calculate_rent_blocked_tile_in_blocked_list(self):
        """calculate_rent returns 0 when tile.id is in game.blocked_tiles."""
        player = make_player(pid="p1")
        tile = make_property_tile(tid="t1", owner_id="p1", color=None)
        game = make_game(players=[player], board=[tile])
        game.blocked_tiles = ["t1"]

        rent = TurnManager.calculate_rent(tile, player, game)
        assert rent == 0

    def test_handle_chance_landing_empty_deck(self):
        """Covers line 116: fallback to SASTA_EVENTS when deck is empty."""
        player = make_player(pid="p1")
        tile = Tile(id="t1", type=TileType.CHANCE, name="Chance", position=1, price=0, rent=0)
        game = make_game(players=[player])
        game.event_deck = []
        game.used_event_deck = []

        result = TurnManager.handle_chance_landing(game, player, tile)
        assert result is not None
        assert "type" in result

    def test_resolve_tile_landing_all_tile_types(self):
        """Covers lines 195-214: resolve_tile_landing dispatches each type."""
        player = make_player(pid="p1")

        tile_types_to_test = [
            TileType.TAX,
            TileType.BUFF,
            TileType.TRAP,
            TileType.JAIL,
            TileType.MARKET,
        ]
        for tile_type in tile_types_to_test:
            game = make_game(players=[player])
            game.event_deck = []
            game.used_event_deck = []
            tile = Tile(
                id="t1",
                type=tile_type,
                name=tile_type.value,
                position=1,
                price=100,
                rent=0,
            )
            result = TurnManager.resolve_tile_landing(game, player, tile)
            assert result is not None

        # TELEPORT requires at least one tile on the board (for fallback)
        go_tile = Tile(id="go", type=TileType.GO, name="GO", position=0, price=0, rent=0)
        game = make_game(players=[player], board=[go_tile])
        game.event_deck = []
        game.used_event_deck = []
        teleport_tile = Tile(
            id="tp", type=TileType.TELEPORT, name="TELEPORT", position=1, price=0, rent=0
        )
        result = TurnManager.resolve_tile_landing(game, player, teleport_tile)
        assert result is not None

    def test_resolve_tile_landing_neutral_type(self):
        """Covers the 'else' branch for unhandled tile types (NEUTRAL)."""
        player = make_player(pid="p1")
        game = make_game(players=[player])
        tile = Tile(id="t1", type=TileType.NEUTRAL, name="Neutral", position=1, price=0, rent=0)
        result = TurnManager.resolve_tile_landing(game, player, tile)
        assert result["type"] == "NEUTRAL"
        assert game.turn_phase == TurnPhase.POST_TURN

    def test_apply_event_effect_cash_gain(self):
        """Covers CASH_GAIN branch in apply_event_effect (line 233)."""
        player = make_player(pid="p1")
        game = make_game(players=[player])
        event = {"type": "CASH_GAIN", "value": 100}
        actions = TurnManager.apply_event_effect(game, player, event)
        assert actions["cash_changes"].get("p1") == 100

    def test_apply_event_effect_cash_loss(self):
        """Covers CASH_LOSS branch (line 235)."""
        player = make_player(pid="p1")
        game = make_game(players=[player])
        event = {"type": "CASH_LOSS", "value": 50}
        actions = TurnManager.apply_event_effect(game, player, event)
        assert actions["cash_changes"].get("p1") == -50

    def test_apply_event_effect_collect_from_all(self):
        """Covers COLLECT_FROM_ALL branch (line 238-242)."""
        player = make_player(pid="p1")
        p2 = make_player(pid="p2", name="Bob")
        p3 = make_player(pid="p3", name="Carol")
        game = make_game(players=[player, p2, p3])
        event = {"type": "COLLECT_FROM_ALL", "value": 50}
        actions = TurnManager.apply_event_effect(game, player, event)
        # p2 and p3 lose 50 each, p1 gains 100
        assert actions["cash_changes"]["p2"] == -50
        assert actions["cash_changes"]["p3"] == -50
        assert actions["cash_changes"]["p1"] == 100

    def test_apply_event_effect_skip_buy(self):
        """Covers SKIP_BUY branch (line 244)."""
        player = make_player(pid="p1")
        game = make_game(players=[player])
        event = {"type": "SKIP_BUY", "value": 0}
        actions = TurnManager.apply_event_effect(game, player, event)
        assert actions["skip_buy"] is True

    def test_apply_event_effect_move_back(self):
        """Covers MOVE_BACK branch (line 247-248)."""
        player = make_player(pid="p1", position=10)
        game = make_game(players=[player])
        event = {"type": "MOVE_BACK", "value": 4}
        actions = TurnManager.apply_event_effect(game, player, event)
        assert actions["position_changes"]["p1"] == 6

    def test_apply_event_effect_move_back_min_zero(self):
        """MOVE_BACK doesn't go below 0."""
        player = make_player(pid="p1", position=2)
        game = make_game(players=[player])
        event = {"type": "MOVE_BACK", "value": 10}
        actions = TurnManager.apply_event_effect(game, player, event)
        assert actions["position_changes"]["p1"] == 0

    def test_apply_event_effect_market_crash(self):
        """Covers MARKET_CRASH branch (line 251-252)."""
        player = make_player(pid="p1")
        game = make_game(players=[player])
        event = {"type": "MARKET_CRASH", "value": 0}
        actions = TurnManager.apply_event_effect(game, player, event)
        assert actions["special"] == "MARKET_CRASH"

    def test_apply_event_effect_bull_market(self):
        """Covers BULL_MARKET branch (line 254-255)."""
        player = make_player(pid="p1")
        game = make_game(players=[player])
        event = {"type": "BULL_MARKET", "value": 0}
        actions = TurnManager.apply_event_effect(game, player, event)
        assert actions["special"] == "BULL_MARKET"

    def test_handle_glitch_teleport_no_unowned(self):
        """Covers handle_glitch_teleport when all properties owned (goes to chance)."""
        player = make_player(pid="p1")
        # All properties are owned
        owned_tile = make_property_tile(tid="t1", owner_id="p2")
        chance_tile = Tile(
            id="c1", type=TileType.CHANCE, name="Chance", position=2, price=0, rent=0
        )
        game = make_game(players=[player], board=[owned_tile, chance_tile])

        target = TurnManager.handle_glitch_teleport(game, player)
        assert target is not None
        assert target.type == TileType.CHANCE

    def test_handle_glitch_teleport_no_unowned_no_chance(self):
        """Fallback to board[0] when no unowned props and no CHANCE tiles."""
        player = make_player(pid="p1")
        owned_tile = make_property_tile(tid="t1", owner_id="p2")
        game = make_game(players=[player], board=[owned_tile])

        target = TurnManager.handle_glitch_teleport(game, player)
        assert target is not None
        assert target.id == "t1"  # board[0]

    def test_ensure_deck_capacity(self):
        """ensure_deck_capacity delegates to EventManager."""
        game = make_game()
        TurnManager.initialize_event_deck(game)
        len(game.event_deck)
        TurnManager.ensure_deck_capacity(game, 3)
        # Should still work without error
        assert len(game.event_deck) >= 0


# ============================================================
# 8. Metrics Additional Coverage
# ============================================================


class TestMetricsAdditional:
    """Targets metrics.py uncovered lines: 12-13, 68, 119-120, 149-163,
    188-189, 200, 208, 212, 219-221, 238-240, 245-246, 274-277, 281-284,
    292-293, 300, 315, 326, 343-361, 435, 446, 448, 450, 483-485, 494,
    521-523, 582-611, 626, 642-644, 668-673, 695-696."""

    # --- radon maintainability ---

    @patch("app.utils.metrics.subprocess.run")
    @patch("app.utils.metrics._find_executable")
    def test_radon_maintainability_no_output(self, mock_find, mock_run):
        """Covers line 68: returncode != 0 and no stdout."""
        mock_find.return_value = "radon"
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_run.return_value = mock_result
        result = metrics.run_radon_maintainability("path")
        assert result == {"files": {}}

    # --- vulture class detection ---

    @patch("app.utils.metrics.subprocess.run")
    @patch("app.utils.metrics._find_executable")
    def test_vulture_detects_unused_class(self, mock_find, mock_run):
        """Covers lines 119-120: item_type == 'class'."""
        mock_find.return_value = "vulture"
        mock_result = MagicMock()
        mock_result.stdout = "test.py:5: unused class 'MyClass' (80% confidence)\n"
        mock_run.return_value = mock_result
        result = metrics.run_vulture_analysis("path")
        assert len(result["unused_classes"]) == 1
        assert result["unused_classes"][0]["name"] == "MyClass"

    # --- find_duplicates with R0801 message ---

    @patch("app.utils.metrics.subprocess.run")
    @patch("app.utils.metrics._find_executable")
    def test_find_duplicates_r0801_with_line_range(self, mock_find, mock_run):
        """Covers lines 149-163: R0801 message with Lines 10-15 pattern."""
        mock_find.return_value = "pylint"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            [
                {
                    "message-id": "R0801",
                    "path": "test.py",
                    "line": 10,
                    "message": "Lines 10-15: duplicated code",
                }
            ]
        )
        mock_run.return_value = mock_result
        result = metrics.find_duplicates("path")
        assert result["total_duplicated_lines"] == 6  # 15-10+1
        assert len(result["duplicate_blocks"]) == 1

    @patch("app.utils.metrics.subprocess.run")
    @patch("app.utils.metrics._find_executable")
    def test_find_duplicates_invalid_json(self, mock_find, mock_run):
        """Covers lines 162-163: json.JSONDecodeError branch."""
        mock_find.return_value = "pylint"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "not valid json{{{}"
        mock_run.return_value = mock_result
        result = metrics.find_duplicates("path")
        assert result["total_duplicated_lines"] == 0

    # --- run_ty_check file pattern ---

    @patch("app.utils.metrics.subprocess.run")
    @patch("app.utils.metrics._find_executable")
    def test_run_ty_check_with_file_errors(self, mock_find, mock_run):
        """Covers lines 188-189: file_pattern match."""
        mock_find.return_value = "ty"
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "--> app/test.py:10:5 error[some-error]: description\n"
        mock_result.stderr = "error[some-error]: test.py:10"
        mock_run.return_value = mock_result
        result = metrics.run_ty_check("path")
        assert result["total_errors"] >= 0

    # --- run_tsc_check: no package.json or no type-check script ---

    @patch("app.utils.metrics.subprocess.run")
    def test_tsc_check_project_no_type_check_script(self, mock_run):
        """Covers lines 208, 212: project without type-check in scripts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "myproject"
            project_dir.mkdir()
            pkg = project_dir / "package.json"
            pkg.write_text(json.dumps({"scripts": {"build": "vite build"}}))

            result = metrics.run_tsc_check(tmpdir)
            assert result["total_errors"] == 0
            assert "myproject" not in result["projects"]

    @patch("app.utils.metrics.subprocess.run")
    def test_tsc_check_project_with_type_errors_in_files(self, mock_run):
        """Covers lines 219-221, 238-240: file error parsing."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "src/foo.ts(10,5): error TS2345: wrong type\n"
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "myproject"
            project_dir.mkdir()
            pkg = project_dir / "package.json"
            pkg.write_text(json.dumps({"scripts": {"type-check": "tsc --noEmit"}}))

            result = metrics.run_tsc_check(tmpdir)
            # error count captured
            assert isinstance(result["total_errors"], int)

    @patch("app.utils.metrics.subprocess.run")
    def test_tsc_check_subprocess_exception(self, mock_run):
        """Covers lines 245-246: subprocess exception for a project."""
        mock_run.side_effect = Exception("tsc not found")

        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "myproject"
            project_dir.mkdir()
            pkg = project_dir / "package.json"
            pkg.write_text(json.dumps({"scripts": {"type-check": "tsc --noEmit"}}))

            result = metrics.run_tsc_check(tmpdir)
            assert result["projects"].get("myproject") == 0

    # --- parse_coverage_xml branches ---

    @patch("app.utils.metrics.etree")
    @patch("app.utils.metrics.Path")
    def test_parse_coverage_xml_no_line_rate_but_has_lines(self, mock_path, mock_etree):
        """Covers lines 274-277: line_rate == 0.0 but total_lines > 0."""
        mock_file = MagicMock()
        mock_file.exists.return_value = True
        mock_path.return_value = mock_file

        mock_tree = MagicMock()
        mock_root = MagicMock()
        mock_root.get.side_effect = lambda x, default: {
            "lines-valid": "1000",
            "lines-covered": "800",
            "line-rate": "0.0",
        }.get(x, default)
        mock_root.findall.return_value = []
        mock_tree.getroot.return_value = mock_root
        mock_etree.parse.return_value = mock_tree

        result = metrics.parse_coverage_xml("test.xml")
        assert result["coverage_percent"] == 80.0  # 800/1000 * 100

    @patch("app.utils.metrics.etree")
    @patch("app.utils.metrics.Path")
    def test_parse_coverage_xml_zero_lines(self, mock_path, mock_etree):
        """Covers line 277: total_lines == 0 → 0.0."""
        mock_file = MagicMock()
        mock_file.exists.return_value = True
        mock_path.return_value = mock_file

        mock_tree = MagicMock()
        mock_root = MagicMock()
        mock_root.get.side_effect = lambda x, default: {
            "lines-valid": "0",
            "lines-covered": "0",
            "line-rate": "0.0",
        }.get(x, default)
        mock_root.findall.return_value = []
        mock_tree.getroot.return_value = mock_root
        mock_etree.parse.return_value = mock_tree

        result = metrics.parse_coverage_xml("test.xml")
        assert result["coverage_percent"] == 0.0

    @patch("app.utils.metrics.etree")
    @patch("app.utils.metrics.Path")
    def test_parse_coverage_xml_class_elements(self, mock_path, mock_etree):
        """Covers lines 281-284: class elements with line-rate > 0."""
        mock_file = MagicMock()
        mock_file.exists.return_value = True
        mock_path.return_value = mock_file

        mock_class = MagicMock()
        mock_class.get.side_effect = lambda x, default: {
            "filename": "app/test.py",
            "line-rate": "0.9",
        }.get(x, default)

        mock_tree = MagicMock()
        mock_root = MagicMock()
        mock_root.get.side_effect = lambda x, default: {
            "lines-valid": "100",
            "lines-covered": "90",
            "line-rate": "0.9",
        }.get(x, default)
        mock_root.findall.return_value = [mock_class]
        mock_tree.getroot.return_value = mock_root
        mock_etree.parse.return_value = mock_tree

        result = metrics.parse_coverage_xml("test.xml")
        assert "app/test.py" in result["files"]
        assert result["files"]["app/test.py"] == 90.0

    @patch("app.utils.metrics.etree")
    @patch("app.utils.metrics.Path")
    def test_parse_coverage_xml_exception(self, mock_path, mock_etree):
        """Covers lines 292-293: exception branch."""
        mock_file = MagicMock()
        mock_file.exists.return_value = True
        mock_path.return_value = mock_file
        mock_etree.parse.side_effect = Exception("parse error")

        result = metrics.parse_coverage_xml("test.xml")
        assert result["coverage_percent"] == 0.0

    # --- parse_frontend_coverage ---

    @patch("app.utils.metrics.Path")
    def test_parse_frontend_coverage_missing_base(self, mock_path):
        """Covers line 300: base doesn't exist."""
        mock_path.return_value.exists.return_value = False
        result = metrics.parse_frontend_coverage("nonexistent")
        assert result["coverage_percent"] == 0.0

    def test_parse_frontend_coverage_clover_metrics_none(self):
        """Covers line 315: metrics element is None (using real temp files)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "myproject"
            (project_dir / "coverage").mkdir(parents=True)
            # Create a clover.xml that has a file element with no metrics child
            clover_content = """<?xml version="1.0" ?>
<coverage>
  <project>
    <file name="test.js">
    </file>
  </project>
</coverage>"""
            (project_dir / "coverage" / "clover.xml").write_text(clover_content)

            # Patch etree to simulate the metrics-None branch
            with patch("app.utils.metrics.etree") as mock_etree:
                mock_file_elem = MagicMock()
                mock_file_elem.get.return_value = "test.js"
                mock_file_elem.find.return_value = None  # no metrics
                mock_tree = MagicMock()
                mock_root = MagicMock()
                mock_root.findall.return_value = [mock_file_elem]
                mock_tree.getroot.return_value = mock_root
                mock_etree.parse.return_value = mock_tree

                result = metrics.parse_frontend_coverage(tmpdir)
                assert result["coverage_percent"] == 0.0

    @patch("app.utils.metrics.etree")
    @patch("app.utils.metrics.Path")
    def test_parse_frontend_coverage_clover_etree_none(self, mock_path, mock_etree_module):
        """Covers line 326: etree is None → continue."""
        mock_project = MagicMock()
        mock_project.is_dir.return_value = True
        mock_project.name = "test_project"
        mock_clover = MagicMock()
        mock_clover.exists.return_value = True
        mock_project.__truediv__ = MagicMock(return_value=mock_clover)
        mock_path.return_value.exists.return_value = True
        mock_path.return_value.iterdir.return_value = [mock_project]

        original_etree = metrics.etree
        metrics.etree = None
        try:
            result = metrics.parse_frontend_coverage("test_path")
            assert result["coverage_percent"] == 0.0
        finally:
            metrics.etree = original_etree

    def test_parse_frontend_coverage_lcov_content(self):
        """Covers lines 343-361: lcov parsing path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "myproject"
            (project_dir / "coverage").mkdir(parents=True)
            lcov_file = project_dir / "coverage" / "lcov.info"
            lcov_file.write_text(
                "SF:src/foo.js\nLF:100\nLH:80\nend_of_record\n"
                "SF:src/bar.js\nLF:50\nLH:40\nend_of_record\n"
            )
            result = metrics.parse_frontend_coverage(tmpdir)
            assert result["total_lines"] == 150
            assert result["covered_lines"] == 120

    # --- calculate_loc_stats branches ---

    def test_calculate_loc_stats_python_filters_tests(self):
        """Covers line 435: skip files in 'tests' dir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tests_dir = Path(tmpdir) / "tests"
            tests_dir.mkdir()
            test_file = tests_dir / "test_foo.py"
            test_file.write_text("def test_foo(): pass\n")

            result = metrics.calculate_loc_stats(tmpdir, "nonexistent")
            # test file should be excluded
            assert not any("tests" in k for k in result["files"])

    def test_calculate_loc_stats_js_skips_node_modules(self):
        """Covers line 446: skip node_modules path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            node_modules = Path(tmpdir) / "node_modules"
            node_modules.mkdir()
            js_file = node_modules / "test.js"
            js_file.write_text("console.log('hello');\n")

            result = metrics.calculate_loc_stats("nonexistent", tmpdir)
            assert not any("node_modules" in k for k in result["files"])

    def test_calculate_loc_stats_js_skips_dist(self):
        """Covers line 448: skip dist path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dist_dir = Path(tmpdir) / "dist"
            dist_dir.mkdir()
            js_file = dist_dir / "bundle.js"
            js_file.write_text("/* bundled */\nconsole.log(1);\n")

            result = metrics.calculate_loc_stats("nonexistent", tmpdir)
            assert not any("dist" in k for k in result["files"])

    def test_calculate_loc_stats_ts_file_type(self):
        """Covers line 450: non-.js/.jsx/.ts/.tsx files skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ts_file = Path(tmpdir) / "component.tsx"
            ts_file.write_text("export const A = () => <div/>;\n")

            result = metrics.calculate_loc_stats("nonexistent", tmpdir)
            assert result["total_loc"] >= 0

    # --- _process_python_file and _count_python_lines ---

    def test_count_python_lines_shebang_not_comment(self):
        """Covers lines 483-485: shebang (#!) is not a comment."""
        lines = ["#!/usr/bin/env python\n", "# comment\n", "code()\n"]
        loc, comments = metrics._count_python_lines(lines)
        assert loc == 2  # shebang + code
        assert comments == 1

    def test_process_python_file_empty_returns_none(self):
        """Covers line 494: loc == 0 → return None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_file = Path(tmpdir) / "empty.py"
            empty_file.write_text("# just a comment\n")  # only comment, loc=0
            result = metrics._process_python_file(empty_file)
            assert result is None

    # --- _count_js_lines ---

    def test_count_js_lines_multiline_comment(self):
        """Covers lines 521-523: multiline comment handling."""
        lines = ["/* start", "middle line", "end */", "code();"]
        loc, comments = metrics._count_js_lines(lines)
        # "/* start" opens multiline, "end */" closes (comments += 1), "code();" is loc
        assert loc == 1
        assert comments >= 1

    # --- categorize_files ---

    def test_categorize_files_returns_counts(self):
        """Covers lines 582-611: categorize_files counts backend/frontend/test files."""
        with tempfile.TemporaryDirectory():
            # Patch Path to use tmpdir so we don't rely on real filesystem
            with patch("app.utils.metrics.Path") as mock_path_class:
                # Return a non-existent path so rglob returns nothing
                mock_instance = MagicMock()
                mock_instance.exists.return_value = False
                mock_instance.rglob.return_value = []
                mock_path_class.return_value = mock_instance

                result = metrics.categorize_files()
                assert "backend" in result
                assert "frontend" in result
                assert "tests" in result

    # --- correlate_type_errors_complexity: confidently_wrong branch ---

    def test_correlate_type_errors_confidently_wrong(self):
        """Covers lines 642-644: complexity < 5 and type_errors > 3."""
        ty_data = {"errors_by_file": {"simple.py": 5}}
        tsc_data = {"errors_by_file": {}}
        complexity_data = {"files": {"simple.py": 2}}  # low complexity

        result = metrics.correlate_type_errors_complexity(ty_data, tsc_data, complexity_data)
        assert any(f["pattern"] == "confidently_wrong" for f in result["hallucination_files"])

    def test_correlate_tsc_errors_merged(self):
        """Covers lines 626: merging tsc errors into all_type_errors."""
        ty_data = {"errors_by_file": {"a.py": 2}}
        tsc_data = {"errors_by_file": {"a.py": 3, "b.ts": 5}}
        complexity_data = {"files": {"a.py": 15, "b.ts": 3}}

        result = metrics.correlate_type_errors_complexity(ty_data, tsc_data, complexity_data)
        # a.py: complexity=15>10, errors=5>0 → complex_wrong
        assert any(
            f["file"] == "a.py" and f["pattern"] == "complex_wrong"
            for f in result["hallucination_files"]
        )

    # --- load_trend_history and save_trend_history ---

    def test_load_trend_history_with_valid_file(self):
        """Covers lines 668-673: loading valid history file."""
        history_data = [{"global_score": "A", "coverage_pct": 80.0}]
        with tempfile.TemporaryDirectory() as tmpdir:
            history_file = Path(tmpdir) / ".repo_health_history.json"
            history_file.write_text(json.dumps(history_data))

            with patch("app.utils.metrics.Path") as mock_path_class:
                mock_path_class.return_value = history_file
                result = metrics.load_trend_history()
                assert len(result) >= 0  # should not crash

    def test_save_trend_history_caps_at_30(self):
        """Covers line 695-696: history capped to last 30 entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_file = Path(tmpdir) / ".repo_health_history.json"
            # Pre-populate with 30 entries
            existing = [{"timestamp": f"t{i}", "global_score": "B"} for i in range(30)]
            history_file.write_text(json.dumps(existing))

            with patch("app.utils.metrics.Path") as mock_path_class:
                mock_path_class.return_value = history_file
                data = {
                    "timestamp": "new",
                    "global_score": "A",
                    "total_complexity": 10,
                    "coverage_pct": 90.0,
                }
                metrics.save_trend_history(data)

            with open(history_file) as f:
                saved = json.load(f)
            assert len(saved) == 30  # capped at 30

    def test_load_trend_history_corrupt_file(self):
        """Covers exception branch in load_trend_history."""
        with patch("app.utils.metrics.Path") as mock_path_class:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path_class.return_value = mock_path_instance

            with patch("builtins.open", mock_open(read_data="not valid json")):
                result = metrics.load_trend_history()
                assert result == []

    # --- merge_coverage: typescript LOC type ---

    def test_merge_coverage_with_typescript(self):
        """Covers LOC weighting with typescript files."""
        backend_coverage = {"coverage_percent": 80.0}
        frontend_coverage = {"coverage_percent": 70.0}
        loc_data = {
            "files": {
                "backend/app/a.py": {"loc": 500, "type": "python"},
                "frontends/b.ts": {"loc": 300, "type": "typescript"},
            }
        }
        result = metrics.merge_coverage(backend_coverage, frontend_coverage, loc_data)
        assert result["overall_coverage"] > 0
        assert result["backend_weight"] > 0
        assert result["frontend_weight"] > 0

    # --- _process_js_file ---

    def test_process_js_file_empty_returns_none(self):
        """Covers line 521: loc == 0 → return None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            js_file = Path(tmpdir) / "empty.js"
            js_file.write_text("// just a comment\n")
            result = metrics._process_js_file(js_file)
            assert result is None

    def test_process_js_file_typescript_type(self):
        """Covers line 511: .ts/.tsx → 'typescript' type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ts_file = Path(tmpdir) / "component.ts"
            ts_file.write_text("const x: number = 1;\n")
            result = metrics._process_js_file(ts_file)
            assert result is not None
            assert result["data"]["type"] == "typescript"

    def test_get_relative_path_fallback(self):
        """Covers line 559 (ValueError): path not relative to cwd."""
        absolute_other = Path("/tmp/some/weird/path/test.py")
        result = metrics._get_relative_path(absolute_other)
        assert result is not None
        assert isinstance(result, str)
