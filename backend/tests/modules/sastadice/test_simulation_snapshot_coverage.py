"""Coverage tests for simulation_manager.py and snapshot_manager.py."""

import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.sastadice.schemas import (
    AuctionState,
    ChaosConfig,
    GameSession,
    GameSettings,
    GameStatus,
    PendingDecision,
    Player,
    Tile,
    TileType,
    TradeOffer,
    TurnPhase,
)
from app.modules.sastadice.services.simulation_manager import SimulationManager
from app.modules.sastadice.services.snapshot_manager import (
    GameSnapshot,
    SnapshotManager,
    StateFrame,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_player(pid: str, name: str = "Player", cash: int = 1000, **kwargs: Any) -> Player:
    return Player(id=pid, name=name, cash=cash, **kwargs)


def _make_game(
    game_id: str = "game1",
    players: list[Player] | None = None,
    board: list[Tile] | None = None,
    status: GameStatus = GameStatus.ACTIVE,
    phase: TurnPhase = TurnPhase.PRE_ROLL,
    current_player_id: str = "p1",
) -> GameSession:
    return GameSession(
        id=game_id,
        status=status,
        turn_phase=phase,
        current_turn_player_id=current_player_id,
        players=players or [],
        board=board or [],
        settings=GameSettings(),
    )


def _make_action_result(message: str = "OK", data: dict[str, Any] | None = None) -> MagicMock:
    r = MagicMock()
    r.message = message
    r.data = data or {}
    return r


@pytest.fixture
def mock_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.update = AsyncMock()
    repo.update_player_cash = AsyncMock()
    return repo


@pytest.fixture
def mock_dispatcher() -> AsyncMock:
    d = AsyncMock()
    d.dispatch = AsyncMock(return_value=_make_action_result())
    return d


@pytest.fixture
def sim_manager(mock_repo: AsyncMock, mock_dispatcher: AsyncMock) -> SimulationManager:
    return SimulationManager(
        repository=mock_repo,
        action_dispatcher=mock_dispatcher,
        get_game_callback=AsyncMock(),
        start_game_callback=AsyncMock(),
    )


# ===========================================================================
# SnapshotManager tests
# ===========================================================================


class TestStateFrame:
    def test_to_dict_serializes_fields(self) -> None:
        p1 = _make_player("p1")
        game = _make_game(players=[p1])
        ts = datetime(2024, 1, 1, 12, 0, 0)
        frame = StateFrame(
            turn_number=3,
            round_number=2,
            timestamp=ts,
            game_state=game,
            last_action={"type": "ROLL_DICE"},
            invariant_status=["ok"],
        )
        d = frame.to_dict()
        assert d["turn_number"] == 3
        assert d["round_number"] == 2
        assert d["timestamp"] == ts.isoformat()
        assert d["last_action"] == {"type": "ROLL_DICE"}
        assert d["invariant_status"] == ["ok"]
        assert isinstance(d["game_state"], dict)

    def test_to_dict_defaults(self) -> None:
        game = _make_game()
        frame = StateFrame(
            turn_number=0,
            round_number=0,
            timestamp=datetime.utcnow(),
            game_state=game,
        )
        d = frame.to_dict()
        assert d["last_action"] is None
        assert d["invariant_status"] == []


class TestGameSnapshot:
    def test_to_dict_no_chaos_config(self) -> None:
        snap = GameSnapshot(
            capture_reason="test",
            error="some error",
            chaos_config=None,
            invariant_violations=["v1", "v2"],
            state_history=[],
            action_history=[{"a": 1}],
        )
        d = snap.to_dict()
        assert d["capture_reason"] == "test"
        assert d["error"] == "some error"
        assert d["chaos_config"] is None
        assert d["invariant_violations"] == ["v1", "v2"]
        assert d["state_history"] == []
        assert d["action_history"] == [{"a": 1}]

    def test_to_dict_with_chaos_config(self) -> None:
        config = ChaosConfig(seed=42, chaos_probability=0.5)
        snap = GameSnapshot(
            capture_reason="chaos",
            error=None,
            chaos_config=config,
            invariant_violations=[],
            state_history=[],
            action_history=[],
        )
        d = snap.to_dict()
        assert d["chaos_config"] is not None
        assert d["chaos_config"]["seed"] == 42
        assert d["chaos_config"]["chaos_probability"] == 0.5

    def test_to_dict_with_state_frames(self) -> None:
        game = _make_game()
        frame = StateFrame(
            turn_number=1,
            round_number=1,
            timestamp=datetime.utcnow(),
            game_state=game,
        )
        snap = GameSnapshot(
            capture_reason="test",
            error=None,
            chaos_config=None,
            invariant_violations=[],
            state_history=[frame],
            action_history=[],
        )
        d = snap.to_dict()
        assert len(d["state_history"]) == 1
        assert d["state_history"][0]["turn_number"] == 1


class TestSnapshotManager:
    def test_init(self) -> None:
        mgr = SnapshotManager()
        assert mgr._config is None
        assert mgr._state_buffer == {}
        assert mgr._action_log == {}

    def test_init_with_chaos_config(self) -> None:
        config = ChaosConfig(seed=1)
        mgr = SnapshotManager(chaos_config=config)
        assert mgr._config == config

    def test_record_state_creates_buffer(self) -> None:
        mgr = SnapshotManager()
        game = _make_game("g1")
        mgr.record_state(game)
        assert "g1" in mgr._state_buffer
        assert len(mgr._state_buffer["g1"]) == 1

    def test_record_state_with_action(self) -> None:
        mgr = SnapshotManager()
        game = _make_game("g1")
        mgr.record_state(game, action={"type": "ROLL_DICE"})
        assert len(mgr._action_log["g1"]) == 1
        assert mgr._action_log["g1"][0]["action"] == {"type": "ROLL_DICE"}

    def test_record_state_without_action(self) -> None:
        mgr = SnapshotManager()
        game = _make_game("g1")
        mgr.record_state(game)
        assert len(mgr._action_log["g1"]) == 0
        assert len(mgr._state_buffer["g1"]) == 1

    def test_record_state_rolling_buffer(self) -> None:
        """Buffer should not exceed HISTORY_SIZE."""
        mgr = SnapshotManager()
        game = _make_game("g1")
        for _ in range(SnapshotManager.HISTORY_SIZE + 3):
            mgr.record_state(game)
        assert len(mgr._state_buffer["g1"]) == SnapshotManager.HISTORY_SIZE

    def test_record_state_multiple_games(self) -> None:
        mgr = SnapshotManager()
        g1 = _make_game("g1")
        g2 = _make_game("g2")
        mgr.record_state(g1)
        mgr.record_state(g2)
        assert "g1" in mgr._state_buffer
        assert "g2" in mgr._state_buffer

    def test_capture_writes_file(self) -> None:
        mgr = SnapshotManager()
        game = _make_game("g1")
        mgr.record_state(game)
        with tempfile.TemporaryDirectory() as tmp:
            with patch("app.modules.sastadice.services.snapshot_manager.Path") as mock_path_cls:
                # Make the snapshots dir and filepath real inside tmp
                real_dir = Path(tmp)
                real_filepath = real_dir / "test_g1_1000.json"

                mock_dir_instance = MagicMock()
                mock_dir_instance.__truediv__ = lambda self, other: real_filepath  # noqa: ARG005
                mock_dir_instance.mkdir = MagicMock()
                mock_path_cls.return_value = mock_dir_instance

                with patch("builtins.open", create=True) as mock_open:
                    mock_file = MagicMock()
                    mock_open.return_value.__enter__ = lambda s: mock_file  # noqa: ARG005
                    mock_open.return_value.__exit__ = MagicMock(return_value=False)

                    with patch("json.dump") as mock_dump:
                        path_str = mgr.capture(game, reason="test_reason", error="err")
                        assert mock_dump.called
                        assert "test_reason" in path_str or isinstance(path_str, str)

    def test_capture_returns_path_string(self) -> None:
        """capture() should return a string path."""
        mgr = SnapshotManager()
        game = _make_game("abcdefghij")
        with patch("app.modules.sastadice.services.snapshot_manager.Path") as mock_path_cls:
            mock_dir = MagicMock()
            fake_fp = MagicMock()
            fake_fp.__str__ = lambda s: "snapshots/test_abcdefgh_12345.json"  # noqa: ARG005
            mock_dir.__truediv__ = lambda s, o: fake_fp  # noqa: ARG005
            mock_dir.mkdir = MagicMock()
            mock_path_cls.return_value = mock_dir

            with patch("builtins.open", MagicMock()), patch("json.dump"):
                result = mgr.capture(game, reason="invariant_violation")
        assert isinstance(result, str)

    def test_capture_with_violations(self) -> None:
        """capture() passes violations through to snapshot."""
        mgr = SnapshotManager()
        game = _make_game("g1")
        captured_snapshots: list[Any] = []

        with patch("app.modules.sastadice.services.snapshot_manager.Path") as mock_path_cls:
            mock_dir = MagicMock()
            fake_fp = MagicMock()
            fake_fp.__str__ = lambda s: "snapshots/x.json"  # noqa: ARG005
            mock_dir.__truediv__ = lambda s, o: fake_fp  # noqa: ARG005
            mock_dir.mkdir = MagicMock()
            mock_path_cls.return_value = mock_dir

            with patch("builtins.open", MagicMock()):
                with patch(
                    "json.dump",
                    side_effect=lambda d, f, **kw: captured_snapshots.append(d),  # noqa: ARG005
                ):
                    mgr.capture(game, reason="r", violations=["v1", "v2"])

        assert len(captured_snapshots) == 1
        assert captured_snapshots[0]["invariant_violations"] == ["v1", "v2"]

    def test_capture_uses_empty_buffer_when_no_history(self) -> None:
        """capture() still works when no states have been recorded."""
        mgr = SnapshotManager()
        game = _make_game("g1")
        with patch("app.modules.sastadice.services.snapshot_manager.Path") as mock_path_cls:
            mock_dir = MagicMock()
            fake_fp = MagicMock()
            fake_fp.__str__ = lambda s: "snapshots/x.json"  # noqa: ARG005
            mock_dir.__truediv__ = lambda s, o: fake_fp  # noqa: ARG005
            mock_dir.mkdir = MagicMock()
            mock_path_cls.return_value = mock_dir
            with patch("builtins.open", MagicMock()), patch("json.dump"):
                path = mgr.capture(game, reason="empty")
        assert isinstance(path, str)

    def test_load_snapshot(self) -> None:
        """load_snapshot parses JSON into a GameSnapshot."""
        mgr = SnapshotManager()
        game = _make_game("g1")
        frame_dict = {
            "turn_number": 1,
            "round_number": 1,
            "timestamp": datetime.utcnow().isoformat(),
            "game_state": game.model_dump(),
            "last_action": {"type": "END_TURN"},
            "invariant_status": ["ok"],
        }
        data = {
            "capture_reason": "test",
            "error": "boom",
            "chaos_config": None,
            "invariant_violations": ["v1"],
            "state_history": [frame_dict],
            "action_history": [{"a": 1}],
        }

        with patch("builtins.open", MagicMock()):
            with patch("json.load", return_value=data):
                snapshot = mgr.load_snapshot("fake_path.json")

        assert snapshot.capture_reason == "test"
        assert snapshot.error == "boom"
        assert len(snapshot.state_history) == 1
        assert snapshot.state_history[0].turn_number == 1
        assert snapshot.state_history[0].last_action == {"type": "END_TURN"}
        assert snapshot.invariant_violations == ["v1"]
        assert snapshot.chaos_config is None

    def test_load_snapshot_with_chaos_config(self) -> None:
        mgr = SnapshotManager()
        _make_game("g1")
        data = {
            "capture_reason": "chaos_test",
            "error": None,
            "chaos_config": {
                "seed": 99,
                "chaos_probability": 0.7,
                "enable_invalid_actions": False,
                "enable_race_conditions": False,
                "fault_injection": {},
            },
            "invariant_violations": [],
            "state_history": [],
            "action_history": [],
        }
        with patch("builtins.open", MagicMock()):
            with patch("json.load", return_value=data):
                snapshot = mgr.load_snapshot("fake.json")

        assert snapshot.chaos_config is not None
        assert snapshot.chaos_config.seed == 99

    def test_replay_to_frame_last(self) -> None:
        """replay_to_frame with default -1 returns last frame."""
        mgr = SnapshotManager()
        game = _make_game("g1")
        frame_dict = {
            "turn_number": 5,
            "round_number": 3,
            "timestamp": datetime.utcnow().isoformat(),
            "game_state": game.model_dump(),
            "last_action": None,
            "invariant_status": [],
        }
        data = {
            "capture_reason": "r",
            "error": None,
            "chaos_config": None,
            "invariant_violations": [],
            "state_history": [frame_dict],
            "action_history": [],
        }
        with patch("builtins.open", MagicMock()):
            with patch("json.load", return_value=data):
                result = mgr.replay_to_frame("fake.json")
        assert isinstance(result, GameSession)

    def test_replay_to_frame_explicit_index(self) -> None:
        """replay_to_frame with explicit index 0 returns first frame."""
        mgr = SnapshotManager()
        game = _make_game("g1")
        frame_dict = {
            "turn_number": 1,
            "round_number": 1,
            "timestamp": datetime.utcnow().isoformat(),
            "game_state": game.model_dump(),
            "last_action": None,
            "invariant_status": [],
        }
        data = {
            "capture_reason": "r",
            "error": None,
            "chaos_config": None,
            "invariant_violations": [],
            "state_history": [frame_dict, frame_dict],
            "action_history": [],
        }
        with patch("builtins.open", MagicMock()):
            with patch("json.load", return_value=data):
                result = mgr.replay_to_frame("fake.json", frame_index=0)
        assert isinstance(result, GameSession)

    def test_replay_to_frame_empty_raises(self) -> None:
        """replay_to_frame raises ValueError on empty history."""
        mgr = SnapshotManager()
        data = {
            "capture_reason": "r",
            "error": None,
            "chaos_config": None,
            "invariant_violations": [],
            "state_history": [],
            "action_history": [],
        }
        with patch("builtins.open", MagicMock()):
            with patch("json.load", return_value=data):
                with pytest.raises(ValueError, match="no state history"):
                    mgr.replay_to_frame("fake.json")

    def test_replay_to_frame_out_of_range_raises(self) -> None:
        """replay_to_frame raises IndexError for bad frame_index."""
        mgr = SnapshotManager()
        game = _make_game("g1")
        frame_dict = {
            "turn_number": 1,
            "round_number": 1,
            "timestamp": datetime.utcnow().isoformat(),
            "game_state": game.model_dump(),
            "last_action": None,
            "invariant_status": [],
        }
        data = {
            "capture_reason": "r",
            "error": None,
            "chaos_config": None,
            "invariant_violations": [],
            "state_history": [frame_dict],
            "action_history": [],
        }
        with patch("builtins.open", MagicMock()):
            with patch("json.load", return_value=data):
                with pytest.raises(IndexError):
                    mgr.replay_to_frame("fake.json", frame_index=99)

    def test_print_snapshot_summary_no_violations(self, capsys: Any) -> None:
        """print_snapshot_summary outputs expected text."""
        mgr = SnapshotManager()
        game = _make_game("g1")
        frame_dict = {
            "turn_number": 1,
            "round_number": 1,
            "timestamp": datetime.utcnow().isoformat(),
            "game_state": game.model_dump(),
            "last_action": None,
            "invariant_status": [],
        }
        data = {
            "capture_reason": "test_reason",
            "error": None,
            "chaos_config": None,
            "invariant_violations": [],
            "state_history": [frame_dict],
            "action_history": [{"a": 1}, {"b": 2}],
        }
        with patch("builtins.open", MagicMock()):
            with patch("json.load", return_value=data):
                mgr.print_snapshot_summary("fake.json")
        out = capsys.readouterr().out
        assert "test_reason" in out
        assert "State History: 1 frames" in out
        assert "Action History: 2 actions" in out

    def test_print_snapshot_summary_with_violations_and_chaos(self, capsys: Any) -> None:
        mgr = SnapshotManager()
        data = {
            "capture_reason": "violation_reason",
            "error": "critical error",
            "chaos_config": {
                "seed": 77,
                "chaos_probability": 0.9,
                "enable_invalid_actions": True,
                "enable_race_conditions": False,
                "fault_injection": {},
            },
            "invariant_violations": ["viol_1", "viol_2"],
            "state_history": [],
            "action_history": [],
        }
        with patch("builtins.open", MagicMock()):
            with patch("json.load", return_value=data):
                mgr.print_snapshot_summary("fake.json")
        out = capsys.readouterr().out
        assert "viol_1" in out
        assert "viol_2" in out
        assert "Seed: 77" in out
        assert "0.9" in out

    def test_print_snapshot_summary_with_last_action(self, capsys: Any) -> None:
        """Frames with last_action should show action type in summary."""
        mgr = SnapshotManager()
        game = _make_game("g1")
        frame_dict = {
            "turn_number": 2,
            "round_number": 1,
            "timestamp": datetime.utcnow().isoformat(),
            "game_state": game.model_dump(),
            "last_action": {"type": "ROLL_DICE"},
            "invariant_status": [],
        }
        data = {
            "capture_reason": "r",
            "error": None,
            "chaos_config": None,
            "invariant_violations": [],
            "state_history": [frame_dict],
            "action_history": [],
        }
        with patch("builtins.open", MagicMock()):
            with patch("json.load", return_value=data):
                mgr.print_snapshot_summary("fake.json")
        out = capsys.readouterr().out
        assert "ROLL_DICE" in out

    def test_clear_history(self) -> None:
        mgr = SnapshotManager()
        game = _make_game("g1")
        mgr.record_state(game)
        assert "g1" in mgr._state_buffer
        mgr.clear_history("g1")
        assert "g1" not in mgr._state_buffer
        assert "g1" not in mgr._action_log

    def test_clear_history_nonexistent_game(self) -> None:
        """clear_history on unknown game_id should not raise."""
        mgr = SnapshotManager()
        mgr.clear_history("nonexistent")  # Should not raise


# ===========================================================================
# SimulationManager tests
# ===========================================================================


class TestSimulationManagerInit:
    def test_default_init(self, mock_repo: AsyncMock, mock_dispatcher: AsyncMock) -> None:
        mgr = SimulationManager(
            repository=mock_repo,
            action_dispatcher=mock_dispatcher,
            get_game_callback=AsyncMock(),
            start_game_callback=AsyncMock(),
        )
        assert mgr.inflation_monitor is None
        assert mgr.enable_economic_monitoring is False
        assert mgr.chaos_config is None

    def test_init_with_economic_monitoring(
        self, mock_repo: AsyncMock, mock_dispatcher: AsyncMock
    ) -> None:
        mgr = SimulationManager(
            repository=mock_repo,
            action_dispatcher=mock_dispatcher,
            get_game_callback=AsyncMock(),
            start_game_callback=AsyncMock(),
            enable_economic_monitoring=True,
        )
        assert mgr.inflation_monitor is not None
        assert mgr.enable_economic_monitoring is True

    def test_init_with_chaos_config(self, mock_repo: AsyncMock, mock_dispatcher: AsyncMock) -> None:
        config = ChaosConfig(seed=42)
        mgr = SimulationManager(
            repository=mock_repo,
            action_dispatcher=mock_dispatcher,
            get_game_callback=AsyncMock(),
            start_game_callback=AsyncMock(),
            chaos_config=config,
        )
        assert mgr.chaos_config is config


class TestInitTurnInfo:
    def test_basic_fields(self, sim_manager: SimulationManager) -> None:
        p1 = _make_player("p1", cash=500, position=3)
        game = _make_game(players=[p1])
        turn_info = sim_manager._init_turn_info(game, p1, turns_played=4)
        assert turn_info["turn"] == 5
        assert turn_info["round"] == game.current_round
        assert turn_info["player"] == "Player"
        assert turn_info["player_id"] == "p1"
        assert turn_info["cash_before"] == 500
        assert turn_info["position_before"] == 3
        assert turn_info["in_jail"] is False
        assert turn_info["actions"] == []

    def test_in_jail_flag(self, sim_manager: SimulationManager) -> None:
        p1 = _make_player("p1", in_jail=True)
        game = _make_game(players=[p1])
        turn_info = sim_manager._init_turn_info(game, p1, turns_played=0)
        assert turn_info["in_jail"] is True


class TestUpdateTurnInfoPostTurn:
    def test_updates_cash_and_position(self, sim_manager: SimulationManager) -> None:
        p1 = _make_player("p1", cash=750, position=10)
        game = _make_game(players=[p1])
        turn_info = {"player_id": "p1", "actions": []}
        sim_manager._update_turn_info_post_turn(game, turn_info)
        assert turn_info["cash_after"] == 750
        assert turn_info["position_after"] == 10

    def test_no_update_if_player_not_found(self, sim_manager: SimulationManager) -> None:
        game = _make_game()
        turn_info = {"player_id": "missing", "actions": []}
        sim_manager._update_turn_info_post_turn(game, turn_info)
        assert "cash_after" not in turn_info


class TestCheckSimulationEnd:
    def test_returns_false_when_two_active(self, sim_manager: SimulationManager) -> None:
        p1 = _make_player("p1", cash=100)
        p2 = _make_player("p2", cash=200)
        game = _make_game(players=[p1, p2])
        assert sim_manager._check_simulation_end(game) is False

    def test_returns_true_when_one_active(self, sim_manager: SimulationManager) -> None:
        p1 = _make_player("p1", cash=100)
        p2 = _make_player("p2", cash=-1, is_bankrupt=True)
        game = _make_game(players=[p1, p2])
        result = sim_manager._check_simulation_end(game)
        assert result is True
        assert game.status == GameStatus.FINISHED

    def test_returns_true_when_all_bankrupt(self, sim_manager: SimulationManager) -> None:
        p1 = _make_player("p1", cash=-1, is_bankrupt=True)
        p2 = _make_player("p2", cash=-1, is_bankrupt=True)
        game = _make_game(players=[p1, p2])
        result = sim_manager._check_simulation_end(game)
        assert result is True

    def test_negative_cash_player_excluded(self, sim_manager: SimulationManager) -> None:
        """Players with cash < 0 (but not explicitly bankrupt) are treated as inactive."""
        p1 = _make_player("p1", cash=500)
        p2 = _make_player("p2", cash=-50)  # cash < 0 but not is_bankrupt
        game = _make_game(players=[p1, p2])
        result = sim_manager._check_simulation_end(game)
        assert result is True


class TestBuildSimulationResult:
    def test_result_structure(self, sim_manager: SimulationManager) -> None:
        p1 = _make_player("p1", cash=1000)
        p2 = _make_player("p2", cash=500)
        game = _make_game("g1", players=[p1, p2], status=GameStatus.FINISHED)
        game.current_round = 5

        with patch("app.modules.sastadice.services.economy_manager.EconomyManager") as MockEconMgr:
            mock_eco = MagicMock()
            mock_eco.determine_winner.return_value = {"name": "Player", "player_id": "p1"}
            MockEconMgr.return_value = mock_eco

            result = sim_manager._build_simulation_result(game, turns_played=10, turn_log=[])

        assert result["game_id"] == "g1"
        assert result["status"] == "FINISHED"
        assert result["turns_played"] == 10
        assert result["rounds_played"] == 5
        assert len(result["final_standings"]) == 2
        # Sorted by cash descending
        assert result["final_standings"][0]["name"] == "Player"
        assert result["final_standings"][0]["cash"] == 1000

    def test_turn_log_truncated_to_last_10(self, sim_manager: SimulationManager) -> None:
        p1 = _make_player("p1", cash=100)
        game = _make_game("g1", players=[p1])
        full_log = [{"turn": i} for i in range(20)]
        result = sim_manager._build_simulation_result(game, turns_played=20, turn_log=full_log)
        assert len(result["turn_log"]) == 10
        assert result["turn_log"][0]["turn"] == 10


class TestRecord:
    def test_increments_counter(self, sim_manager: SimulationManager) -> None:
        cov: dict[str, int] = {}
        sim_manager._record(cov, "ROLL_DICE")
        assert cov["ROLL_DICE"] == 1
        sim_manager._record(cov, "ROLL_DICE")
        assert cov["ROLL_DICE"] == 2

    def test_initializes_new_key(self, sim_manager: SimulationManager) -> None:
        cov: dict[str, int] = {}
        sim_manager._record(cov, "NEW_ACTION")
        assert cov["NEW_ACTION"] == 1


class TestHandleStuckState:
    @pytest.mark.asyncio
    async def test_increments_counter_on_repeat_state(
        self, sim_manager: SimulationManager, mock_repo: AsyncMock
    ) -> None:
        p1 = _make_player("p1")
        game = _make_game(players=[p1], phase=TurnPhase.PRE_ROLL)
        stuck_state: dict[str, Any] = {
            "counter": 4,
            "last_state": "PRE_ROLL:p1:None",
        }
        await sim_manager._handle_stuck_state(game, p1, stuck_state)
        assert stuck_state["counter"] == 5

    @pytest.mark.asyncio
    async def test_resets_phase_when_stuck_over_5(
        self, sim_manager: SimulationManager, mock_repo: AsyncMock
    ) -> None:
        p1 = _make_player("p1")
        game = _make_game(players=[p1], phase=TurnPhase.PRE_ROLL)
        game.pending_decision = None
        stuck_state: dict[str, Any] = {
            "counter": 6,
            "last_state": "PRE_ROLL:p1:None",
        }
        await sim_manager._handle_stuck_state(game, p1, stuck_state)
        assert game.turn_phase == TurnPhase.POST_TURN
        assert stuck_state["counter"] == 0
        mock_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_resets_on_state_change(
        self, sim_manager: SimulationManager, mock_repo: AsyncMock
    ) -> None:
        p1 = _make_player("p1")
        game = _make_game(players=[p1], phase=TurnPhase.PRE_ROLL)
        stuck_state: dict[str, Any] = {
            "counter": 3,
            "last_state": "DECISION:p1:None",
        }
        await sim_manager._handle_stuck_state(game, p1, stuck_state)
        assert stuck_state["counter"] == 0
        assert stuck_state["last_state"] == "PRE_ROLL:p1:None"
        mock_repo.update.assert_not_called()


class TestCalculateExpectedCashDelta:
    def _run(self, sim_manager: SimulationManager, actions: list[dict[str, Any]]) -> int:
        turn_info = {"actions": actions}
        return sim_manager._calculate_expected_cash_delta(_make_game(), turn_info)

    def test_property_purchase_is_sink(self, sim_manager: SimulationManager) -> None:
        actions = [{"result": "Bought Old Delhi for $200"}]
        delta = self._run(sim_manager, actions)
        assert delta == -200

    def test_tax_is_sink(self, sim_manager: SimulationManager) -> None:
        actions = [{"result": "Paid $100 tax on income"}]
        delta = self._run(sim_manager, actions)
        assert delta == -100

    def test_bribe_is_sink(self, sim_manager: SimulationManager) -> None:
        actions = [{"result": "Paid bribe of $50 to escape"}]
        delta = self._run(sim_manager, actions)
        assert delta == -50

    def test_go_bonus_is_source(self, sim_manager: SimulationManager) -> None:
        actions = [{"result": "Received $200 from GO bonus"}]
        delta = self._run(sim_manager, actions)
        assert delta == 200

    def test_mortgage_is_source(self, sim_manager: SimulationManager) -> None:
        actions = [{"result": "Mortgaged Prop for $150"}]
        delta = self._run(sim_manager, actions)
        assert delta == 150

    def test_event_bank_payment_is_sink(self, sim_manager: SimulationManager) -> None:
        # Message must contain "event:" and "paid $" and "bank", but NOT "tax" (to avoid double-counting)
        actions = [{"result": "event: Wealth Drain! paid $100 to bank"}]
        delta = self._run(sim_manager, actions)
        assert delta == -100

    def test_event_bank_received_is_source(self, sim_manager: SimulationManager) -> None:
        actions = [{"result": "event: Stimulus! received $200 from bank"}]
        delta = self._run(sim_manager, actions)
        assert delta == 200

    def test_empty_actions(self, sim_manager: SimulationManager) -> None:
        delta = self._run(sim_manager, [])
        assert delta == 0

    def test_malformed_buy_message_graceful(self, sim_manager: SimulationManager) -> None:
        """Malformed messages should not raise — should just skip."""
        actions = [{"result": "bought property but no price mentioned"}]
        delta = self._run(sim_manager, actions)
        assert delta == 0

    def test_multiple_actions_accumulate(self, sim_manager: SimulationManager) -> None:
        actions = [
            {"result": "Received $200 from GO bonus"},
            {"result": "Bought Prop for $300"},
        ]
        delta = self._run(sim_manager, actions)
        assert delta == -100


class TestCheckBankruptcy:
    @pytest.mark.asyncio
    async def test_marks_negative_cash_players(
        self, sim_manager: SimulationManager, mock_repo: AsyncMock
    ) -> None:
        p1 = _make_player("p1", cash=-50)
        p2 = _make_player("p2", cash=500)
        game = _make_game("g1", players=[p1, p2])
        sim_manager._get_game = AsyncMock(return_value=game)

        await sim_manager._check_bankruptcy("g1")

        assert p1.cash == -9999
        mock_repo.update_player_cash.assert_called_once_with("p1", -9999)

    @pytest.mark.asyncio
    async def test_no_change_for_positive_cash(
        self, sim_manager: SimulationManager, mock_repo: AsyncMock
    ) -> None:
        p1 = _make_player("p1", cash=100)
        game = _make_game("g1", players=[p1])
        sim_manager._get_game = AsyncMock(return_value=game)
        await sim_manager._check_bankruptcy("g1")
        mock_repo.update_player_cash.assert_not_called()


class TestHandleSimulatedDecision:
    @pytest.mark.asyncio
    async def test_buy_node_when_enough_cash(
        self, sim_manager: SimulationManager, mock_dispatcher: AsyncMock
    ) -> None:
        tile = Tile(
            id="t1",
            name="Node1",
            type=TileType.NODE,
            price=100,
            owner_id=None,
            position=0,
        )
        p1 = _make_player("p1", cash=800, position=0)
        game = _make_game("g1", players=[p1], board=[tile], current_player_id="p1")
        sim_manager._get_game = AsyncMock(return_value=game)

        turn_info: dict[str, Any] = {"actions": []}
        coverage: dict[str, int] = {}
        await sim_manager._handle_simulated_decision("g1", p1, turn_info, coverage)
        assert "BUY_PROPERTY" in coverage

    @pytest.mark.asyncio
    async def test_skip_node_buy_when_insufficient_cash(
        self, sim_manager: SimulationManager, mock_dispatcher: AsyncMock
    ) -> None:
        """Player with less than price+200 should NOT buy the node."""
        tile = Tile(
            id="t1",
            name="Node1",
            type=TileType.NODE,
            price=100,
            owner_id=None,
            position=0,
        )
        p1 = _make_player("p1", cash=50, position=0)
        game = _make_game("g1", players=[p1], board=[tile], current_player_id="p1")
        game.pending_decision = PendingDecision(type="BUY", price=100)
        sim_manager._get_game = AsyncMock(return_value=game)

        turn_info: dict[str, Any] = {"actions": []}
        coverage: dict[str, int] = {}
        await sim_manager._handle_simulated_decision("g1", p1, turn_info, coverage)
        # Should not have called BUY_PROPERTY for node
        assert "BUY_PROPERTY" not in coverage

    @pytest.mark.asyncio
    async def test_go_to_jail_tile(
        self, sim_manager: SimulationManager, mock_dispatcher: AsyncMock
    ) -> None:
        tile = Tile(id="t1", name="404", type=TileType.GO_TO_JAIL, position=0)
        p1 = _make_player("p1", position=0)
        game = _make_game("g1", players=[p1], board=[tile], current_player_id="p1")
        sim_manager._get_game = AsyncMock(return_value=game)

        turn_info: dict[str, Any] = {"actions": []}
        coverage: dict[str, int] = {}
        await sim_manager._handle_simulated_decision("g1", p1, turn_info, coverage)
        actions = [a["action"] for a in turn_info["actions"]]
        assert "SENT_TO_JAIL" in actions

    @pytest.mark.asyncio
    async def test_jail_buy_release_enough_cash(
        self, sim_manager: SimulationManager, mock_dispatcher: AsyncMock
    ) -> None:
        p1 = _make_player("p1", cash=1000, in_jail=True)
        game = _make_game("g1", players=[p1], current_player_id="p1")
        sim_manager._get_game = AsyncMock(return_value=game)

        turn_info: dict[str, Any] = {"actions": []}
        coverage: dict[str, int] = {}
        await sim_manager._handle_simulated_decision("g1", p1, turn_info, coverage)
        assert "BUY_RELEASE" in coverage

    @pytest.mark.asyncio
    async def test_jail_roll_for_doubles_insufficient_cash(
        self, sim_manager: SimulationManager, mock_dispatcher: AsyncMock
    ) -> None:
        p1 = _make_player("p1", cash=10, in_jail=True)
        game = _make_game("g1", players=[p1], current_player_id="p1")
        game.settings.jail_bribe_cost = 50
        sim_manager._get_game = AsyncMock(return_value=game)

        turn_info: dict[str, Any] = {"actions": []}
        coverage: dict[str, int] = {}
        await sim_manager._handle_simulated_decision("g1", p1, turn_info, coverage)
        assert "ROLL_FOR_DOUBLES" in coverage

    @pytest.mark.asyncio
    async def test_no_pending_decision_returns_early(self, sim_manager: SimulationManager) -> None:
        p1 = _make_player("p1")
        game = _make_game("g1", players=[p1], current_player_id="p1")
        game.pending_decision = None
        sim_manager._get_game = AsyncMock(return_value=game)
        turn_info: dict[str, Any] = {"actions": []}
        coverage: dict[str, int] = {}
        # Should return early without dispatching
        await sim_manager._handle_simulated_decision("g1", p1, turn_info, coverage)
        assert turn_info["actions"] == []

    @pytest.mark.asyncio
    async def test_buy_decision_enough_cash(
        self, sim_manager: SimulationManager, mock_dispatcher: AsyncMock
    ) -> None:
        p1 = _make_player("p1", cash=2000)
        game = _make_game("g1", players=[p1], current_player_id="p1")
        game.pending_decision = PendingDecision(type="BUY", price=100)
        sim_manager._get_game = AsyncMock(return_value=game)

        turn_info: dict[str, Any] = {"actions": []}
        coverage: dict[str, int] = {}
        await sim_manager._handle_simulated_decision("g1", p1, turn_info, coverage)
        assert "BUY_PROPERTY" in coverage

    @pytest.mark.asyncio
    async def test_buy_decision_insufficient_cash_passes(
        self, sim_manager: SimulationManager, mock_dispatcher: AsyncMock
    ) -> None:
        p1 = _make_player("p1", cash=50)
        game = _make_game("g1", players=[p1], current_player_id="p1")
        game.pending_decision = PendingDecision(type="BUY", price=100)
        sim_manager._get_game = AsyncMock(return_value=game)

        turn_info: dict[str, Any] = {"actions": []}
        coverage: dict[str, int] = {}
        await sim_manager._handle_simulated_decision("g1", p1, turn_info, coverage)
        assert "PASS_PROPERTY" in coverage

    @pytest.mark.asyncio
    async def test_buy_decision_chaos_skip(
        self, mock_repo: AsyncMock, mock_dispatcher: AsyncMock
    ) -> None:
        config = ChaosConfig(chaos_probability=1.0)
        mgr = SimulationManager(
            repository=mock_repo,
            action_dispatcher=mock_dispatcher,
            get_game_callback=AsyncMock(),
            start_game_callback=AsyncMock(),
            chaos_config=config,
        )
        p1 = _make_player("p1", cash=5000)
        game = _make_game("g1", players=[p1], current_player_id="p1")
        game.pending_decision = PendingDecision(type="BUY", price=100)
        mgr._get_game = AsyncMock(return_value=game)

        turn_info: dict[str, Any] = {"actions": []}
        coverage: dict[str, int] = {}
        with patch("random.random", return_value=0.0):  # always trigger chaos, always skip
            await mgr._handle_simulated_decision("g1", p1, turn_info, coverage)

        assert "MONKEY_SKIP_BUY" in coverage

    @pytest.mark.asyncio
    async def test_market_decision_buys_buff(
        self, sim_manager: SimulationManager, mock_dispatcher: AsyncMock
    ) -> None:
        p1 = _make_player("p1", cash=2000)
        game = _make_game("g1", players=[p1], current_player_id="p1")
        game.pending_decision = PendingDecision(
            type="MARKET",
            event_data={"buffs": [{"id": "DDOS", "cost": 100}]},
        )
        sim_manager._get_game = AsyncMock(return_value=game)

        turn_info: dict[str, Any] = {"actions": []}
        coverage: dict[str, int] = {}
        await sim_manager._handle_simulated_decision("g1", p1, turn_info, coverage)
        assert "BUY_BUFF" in coverage

    @pytest.mark.asyncio
    async def test_market_decision_passes_when_poor(
        self, sim_manager: SimulationManager, mock_dispatcher: AsyncMock
    ) -> None:
        p1 = _make_player("p1", cash=50)
        game = _make_game("g1", players=[p1], current_player_id="p1")
        game.pending_decision = PendingDecision(
            type="MARKET",
            event_data={"buffs": [{"id": "DDOS", "cost": 400}]},
        )
        sim_manager._get_game = AsyncMock(return_value=game)

        turn_info: dict[str, Any] = {"actions": []}
        coverage: dict[str, int] = {}
        await sim_manager._handle_simulated_decision("g1", p1, turn_info, coverage)
        assert "PASS_PROPERTY" in coverage

    @pytest.mark.asyncio
    async def test_market_decision_skips_if_buff_active(
        self, sim_manager: SimulationManager, mock_dispatcher: AsyncMock
    ) -> None:
        """If player already has active buff, should not buy another."""
        p1 = _make_player("p1", cash=2000, active_buff="DDOS")
        game = _make_game("g1", players=[p1], current_player_id="p1")
        game.pending_decision = PendingDecision(
            type="MARKET",
            event_data={"buffs": [{"id": "SHIELD", "cost": 100}]},
        )
        sim_manager._get_game = AsyncMock(return_value=game)

        turn_info: dict[str, Any] = {"actions": []}
        coverage: dict[str, int] = {}
        await sim_manager._handle_simulated_decision("g1", p1, turn_info, coverage)
        assert "BUY_BUFF" not in coverage
        assert "PASS_PROPERTY" in coverage

    @pytest.mark.asyncio
    async def test_event_clone_upgrade_with_valid_tiles(
        self, sim_manager: SimulationManager, mock_dispatcher: AsyncMock
    ) -> None:
        src_tile = Tile(
            id="src", name="Source", type=TileType.PROPERTY, upgrade_level=1, owner_id="p2"
        )
        tgt_tile = Tile(id="tgt", name="Target", type=TileType.PROPERTY, owner_id="p1")
        p1 = _make_player("p1", cash=1000)
        game = _make_game("g1", players=[p1], board=[src_tile, tgt_tile], current_player_id="p1")
        game.pending_decision = PendingDecision(type="EVENT_CLONE_UPGRADE")
        sim_manager._get_game = AsyncMock(return_value=game)

        turn_info: dict[str, Any] = {"actions": []}
        coverage: dict[str, int] = {}
        await sim_manager._handle_simulated_decision("g1", p1, turn_info, coverage)
        assert "EVENT_CLONE_UPGRADE" in coverage

    @pytest.mark.asyncio
    async def test_event_clone_upgrade_no_valid_tiles(
        self, sim_manager: SimulationManager, mock_repo: AsyncMock
    ) -> None:
        """No sources with upgrade_level > 0, so should skip."""
        p1 = _make_player("p1", cash=1000)
        game = _make_game("g1", players=[p1], current_player_id="p1")
        game.pending_decision = PendingDecision(type="EVENT_CLONE_UPGRADE")
        sim_manager._get_game = AsyncMock(return_value=game)

        turn_info: dict[str, Any] = {"actions": []}
        coverage: dict[str, int] = {}
        await sim_manager._handle_simulated_decision("g1", p1, turn_info, coverage)
        actions = [a["action"] for a in turn_info["actions"]]
        assert "SKIP_EVENT_CLONE_UPGRADE" in actions
        mock_repo.update.assert_called()

    @pytest.mark.asyncio
    async def test_event_force_buy_with_target(
        self, sim_manager: SimulationManager, mock_dispatcher: AsyncMock
    ) -> None:
        p1 = _make_player("p1", cash=1000)
        p2 = _make_player("p2", cash=1000)
        other_prop = Tile(id="t1", name="OtherProp", type=TileType.PROPERTY, owner_id="p2")
        game = _make_game("g1", players=[p1, p2], board=[other_prop], current_player_id="p1")
        game.pending_decision = PendingDecision(type="EVENT_FORCE_BUY")
        sim_manager._get_game = AsyncMock(return_value=game)

        turn_info: dict[str, Any] = {"actions": []}
        coverage: dict[str, int] = {}
        await sim_manager._handle_simulated_decision("g1", p1, turn_info, coverage)
        assert "EVENT_FORCE_BUY" in coverage

    @pytest.mark.asyncio
    async def test_event_force_buy_no_targets(
        self, sim_manager: SimulationManager, mock_repo: AsyncMock
    ) -> None:
        p1 = _make_player("p1", cash=1000)
        game = _make_game("g1", players=[p1], current_player_id="p1")
        game.pending_decision = PendingDecision(type="EVENT_FORCE_BUY")
        sim_manager._get_game = AsyncMock(return_value=game)

        turn_info: dict[str, Any] = {"actions": []}
        coverage: dict[str, int] = {}
        await sim_manager._handle_simulated_decision("g1", p1, turn_info, coverage)
        actions = [a["action"] for a in turn_info["actions"]]
        assert "SKIP_EVENT_FORCE_BUY" in actions

    @pytest.mark.asyncio
    async def test_event_free_landing_with_owned_property(
        self, sim_manager: SimulationManager, mock_dispatcher: AsyncMock
    ) -> None:
        p1 = _make_player("p1", cash=1000)
        my_prop = Tile(id="t1", name="MyProp", type=TileType.PROPERTY, owner_id="p1")
        game = _make_game("g1", players=[p1], board=[my_prop], current_player_id="p1")
        game.pending_decision = PendingDecision(type="EVENT_FREE_LANDING")
        sim_manager._get_game = AsyncMock(return_value=game)

        turn_info: dict[str, Any] = {"actions": []}
        coverage: dict[str, int] = {}
        await sim_manager._handle_simulated_decision("g1", p1, turn_info, coverage)
        assert "EVENT_FREE_LANDING" in coverage

    @pytest.mark.asyncio
    async def test_event_free_landing_no_properties(
        self, sim_manager: SimulationManager, mock_repo: AsyncMock
    ) -> None:
        p1 = _make_player("p1", cash=1000)
        game = _make_game("g1", players=[p1], current_player_id="p1")
        game.pending_decision = PendingDecision(type="EVENT_FREE_LANDING")
        sim_manager._get_game = AsyncMock(return_value=game)

        turn_info: dict[str, Any] = {"actions": []}
        coverage: dict[str, int] = {}
        await sim_manager._handle_simulated_decision("g1", p1, turn_info, coverage)
        actions = [a["action"] for a in turn_info["actions"]]
        assert "SKIP_EVENT_FREE_LANDING" in actions

    @pytest.mark.asyncio
    async def test_unknown_decision_type_skips(
        self, sim_manager: SimulationManager, mock_repo: AsyncMock
    ) -> None:
        p1 = _make_player("p1", cash=500)
        game = _make_game("g1", players=[p1], current_player_id="p1")
        game.pending_decision = PendingDecision(type="MYSTERY_DECISION")
        sim_manager._get_game = AsyncMock(return_value=game)

        turn_info: dict[str, Any] = {"actions": []}
        coverage: dict[str, int] = {}
        await sim_manager._handle_simulated_decision("g1", p1, turn_info, coverage)
        assert "SKIP_MYSTERY_DECISION" in coverage
        actions = [a["action"] for a in turn_info["actions"]]
        assert "SKIP_MYSTERY_DECISION" in actions
        mock_repo.update.assert_called()


class TestProcessIncomingTradeOffers:
    @pytest.mark.asyncio
    async def test_accepts_trade_with_low_random(
        self, sim_manager: SimulationManager, mock_dispatcher: AsyncMock
    ) -> None:
        p1 = _make_player("p1")
        p2 = _make_player("p2")
        offer = TradeOffer(
            id="o1",
            initiator_id="p1",
            target_id="p2",
        )
        game = _make_game("g1", players=[p1, p2])
        game.active_trade_offers = [offer]

        turn_info: dict[str, Any] = {"actions": []}
        coverage: dict[str, int] = {}

        with patch("random.random", return_value=0.1):  # < 0.3 => accept
            await sim_manager._process_incoming_trade_offers(game, turn_info, coverage)

        assert "ACCEPT_TRADE" in coverage
        mock_dispatcher.dispatch.assert_called_once()

    @pytest.mark.asyncio
    async def test_declines_trade_with_high_random(
        self, sim_manager: SimulationManager, mock_dispatcher: AsyncMock
    ) -> None:
        p1 = _make_player("p1")
        p2 = _make_player("p2")
        offer = TradeOffer(id="o1", initiator_id="p1", target_id="p2")
        game = _make_game("g1", players=[p1, p2])
        game.active_trade_offers = [offer]

        turn_info: dict[str, Any] = {"actions": []}
        coverage: dict[str, int] = {}

        with patch("random.random", return_value=0.9):  # >= 0.3 => decline
            await sim_manager._process_incoming_trade_offers(game, turn_info, coverage)

        assert "DECLINE_TRADE" in coverage

    @pytest.mark.asyncio
    async def test_skips_offer_if_target_not_found(
        self, sim_manager: SimulationManager, mock_dispatcher: AsyncMock
    ) -> None:
        p1 = _make_player("p1")
        offer = TradeOffer(id="o1", initiator_id="p1", target_id="missing")
        game = _make_game("g1", players=[p1])
        game.active_trade_offers = [offer]

        turn_info: dict[str, Any] = {"actions": []}
        coverage: dict[str, int] = {}
        await sim_manager._process_incoming_trade_offers(game, turn_info, coverage)
        mock_dispatcher.dispatch.assert_not_called()


class TestSimulateCpuTrades:
    @pytest.mark.asyncio
    async def test_calls_process_incoming_and_proposal(
        self, sim_manager: SimulationManager, mock_dispatcher: AsyncMock
    ) -> None:
        """_simulate_cpu_trades calls both incoming and proposal helpers."""
        p1 = _make_player("p1")
        game = _make_game("g1", players=[p1], phase=TurnPhase.POST_TURN, current_player_id="p1")

        turn_info: dict[str, Any] = {"actions": []}
        coverage: dict[str, int] = {}

        with (
            patch.object(
                sim_manager, "_process_incoming_trade_offers", new_callable=AsyncMock
            ) as mock_inc,
            patch.object(
                sim_manager, "_attempt_cpu_trade_proposal", new_callable=AsyncMock
            ) as mock_prop,
        ):
            await sim_manager._simulate_cpu_trades(game, turn_info, coverage)

        mock_inc.assert_called_once()
        mock_prop.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_proposal_when_not_post_turn(self, sim_manager: SimulationManager) -> None:
        p1 = _make_player("p1")
        game = _make_game("g1", players=[p1], phase=TurnPhase.PRE_ROLL, current_player_id="p1")

        turn_info: dict[str, Any] = {"actions": []}
        coverage: dict[str, int] = {}

        with (
            patch.object(sim_manager, "_process_incoming_trade_offers", new_callable=AsyncMock),
            patch.object(
                sim_manager, "_attempt_cpu_trade_proposal", new_callable=AsyncMock
            ) as mock_prop,
        ):
            await sim_manager._simulate_cpu_trades(game, turn_info, coverage)

        mock_prop.assert_not_called()


class TestSimulateCpuGame:
    @pytest.mark.asyncio
    async def test_raises_if_not_enough_players_in_lobby(
        self, sim_manager: SimulationManager
    ) -> None:
        p1 = _make_player("p1")
        game = _make_game("g1", players=[p1], status=GameStatus.LOBBY)
        sim_manager._get_game = AsyncMock(return_value=game)

        with pytest.raises(ValueError, match="at least 2"):
            await sim_manager.simulate_cpu_game("g1")

    @pytest.mark.asyncio
    async def test_raises_if_game_not_active_after_start(
        self, sim_manager: SimulationManager
    ) -> None:
        p1 = _make_player("p1")
        p2 = _make_player("p2")
        lobby_game = _make_game("g1", players=[p1, p2], status=GameStatus.LOBBY)
        finished_game = _make_game("g1", players=[p1, p2], status=GameStatus.FINISHED)
        sim_manager._get_game = AsyncMock(return_value=lobby_game)
        sim_manager._start_game = AsyncMock(return_value=finished_game)

        with pytest.raises(ValueError, match="not active"):
            await sim_manager.simulate_cpu_game("g1")

    @pytest.mark.asyncio
    async def test_raises_if_game_not_active(self, sim_manager: SimulationManager) -> None:
        game = _make_game("g1", status=GameStatus.FINISHED)
        sim_manager._get_game = AsyncMock(return_value=game)

        with pytest.raises(ValueError, match="not active"):
            await sim_manager.simulate_cpu_game("g1")

    @pytest.mark.asyncio
    async def test_returns_result_dict_on_no_active_player(
        self, sim_manager: SimulationManager, mock_repo: AsyncMock
    ) -> None:
        """When no player matches current_turn_player_id, loop breaks immediately."""
        p1 = _make_player("p1", cash=1000)
        game = _make_game("g1", players=[p1], status=GameStatus.ACTIVE, current_player_id="nobody")
        sim_manager._get_game = AsyncMock(return_value=game)
        sim_manager._advance_if_bankrupt_current = AsyncMock()

        result = await sim_manager.simulate_cpu_game("g1", max_turns=5)

        assert "game_id" in result
        assert result["turns_played"] == 0

    @pytest.mark.asyncio
    async def test_economic_monitoring_generates_report(
        self, mock_repo: AsyncMock, mock_dispatcher: AsyncMock
    ) -> None:
        """With economic monitoring enabled, final result should include economic_report."""
        mgr = SimulationManager(
            repository=mock_repo,
            action_dispatcher=mock_dispatcher,
            get_game_callback=AsyncMock(),
            start_game_callback=AsyncMock(),
            enable_economic_monitoring=True,
        )

        p1 = _make_player("p1", cash=1000)
        game = _make_game("g1", players=[p1], status=GameStatus.ACTIVE, current_player_id="nobody")
        mgr._get_game = AsyncMock(return_value=game)

        mock_report = MagicMock()
        mock_report.diagnosis = "healthy"
        mock_report.inflation_detected = False
        mock_report.stalemate_detected = False
        mock_report.recommendations = []
        mock_report.game_id = "g1"
        mgr.inflation_monitor = MagicMock()  # type: ignore[assignment]
        mgr.inflation_monitor.generate_report.return_value = mock_report

        result = await mgr.simulate_cpu_game("g1", max_turns=1)

        assert "economic_report" in result
        assert result["economic_report"]["diagnosis"] == "healthy"


class TestExecuteSimulatedTurn:
    @pytest.mark.asyncio
    async def test_pre_roll_phase_dispatches_roll_dice(
        self, sim_manager: SimulationManager, mock_dispatcher: AsyncMock
    ) -> None:
        p1 = _make_player("p1")
        # Return POST_TURN after initial PRE_ROLL game is consumed; use return_value so it
        # repeats indefinitely for any subsequent _get_game calls.
        post_turn_game = _make_game(
            "g1", players=[p1], phase=TurnPhase.POST_TURN, current_player_id="p1"
        )
        pre_roll_game = _make_game(
            "g1", players=[p1], phase=TurnPhase.PRE_ROLL, current_player_id="p1"
        )
        end_result = _make_action_result("OK", data={"game_over": False})
        mock_dispatcher.dispatch.return_value = end_result
        # First call: PRE_ROLL, all subsequent: POST_TURN (so code sees ROLL_DICE then ends)
        call_count = 0

        async def get_game_side_effect(gid: str) -> GameSession:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return pre_roll_game
            return post_turn_game

        sim_manager._get_game = get_game_side_effect  # type: ignore[assignment]

        turn_info: dict[str, Any] = {"actions": []}
        coverage: dict[str, int] = {}
        await sim_manager._execute_simulated_turn("g1", p1, turn_info, coverage)
        assert "ROLL_DICE" in coverage

    @pytest.mark.asyncio
    async def test_game_over_signal_returns_true(
        self, sim_manager: SimulationManager, mock_dispatcher: AsyncMock
    ) -> None:
        p1 = _make_player("p1")
        post_game = _make_game(
            "g1", players=[p1], phase=TurnPhase.POST_TURN, current_player_id="p1"
        )
        game_over_result = _make_action_result("Game over", data={"game_over": True})
        mock_dispatcher.dispatch.return_value = game_over_result
        sim_manager._get_game = AsyncMock(return_value=post_game)

        turn_info: dict[str, Any] = {"actions": []}
        coverage: dict[str, int] = {}
        result = await sim_manager._execute_simulated_turn("g1", p1, turn_info, coverage)
        assert result is True

    @pytest.mark.asyncio
    async def test_end_turn_normal_returns_false(
        self, sim_manager: SimulationManager, mock_dispatcher: AsyncMock
    ) -> None:
        p1 = _make_player("p1")
        post_game = _make_game(
            "g1", players=[p1], phase=TurnPhase.POST_TURN, current_player_id="p1"
        )
        normal_result = _make_action_result("OK", data={})
        mock_dispatcher.dispatch.return_value = normal_result
        sim_manager._get_game = AsyncMock(return_value=post_game)

        turn_info: dict[str, Any] = {"actions": []}
        coverage: dict[str, int] = {}
        result = await sim_manager._execute_simulated_turn("g1", p1, turn_info, coverage)
        assert result is False

    @pytest.mark.asyncio
    async def test_auction_phase_bids_and_resolves(
        self, sim_manager: SimulationManager, mock_dispatcher: AsyncMock
    ) -> None:
        """Tests the normal BID path inside AUCTION phase."""
        import time as time_module

        p1 = _make_player("p1", cash=5000)
        auction = AuctionState(
            property_id="t1",
            highest_bid=100,
            end_time=time_module.time() + 9999,
            participants=["p1"],
            min_bid_increment=10,
        )
        game = _make_game("g1", players=[p1], phase=TurnPhase.AUCTION, current_player_id="p1")
        game.auction_state = auction
        normal_result = _make_action_result("OK", data={})
        mock_dispatcher.dispatch.return_value = normal_result
        sim_manager._get_game = AsyncMock(return_value=game)

        turn_info: dict[str, Any] = {"actions": []}
        coverage: dict[str, int] = {}
        # Force random to < 0.5 so normal BID triggers
        with patch("random.random", return_value=0.1):
            await sim_manager._execute_simulated_turn("g1", p1, turn_info, coverage)

        assert "BID" in coverage
        assert "RESOLVE_AUCTION" in coverage

    @pytest.mark.asyncio
    async def test_post_turn_upgrade_path(
        self, sim_manager: SimulationManager, mock_dispatcher: AsyncMock
    ) -> None:
        """Tests the UPGRADE path in POST_TURN when player owns a full color set."""
        p1 = _make_player("p1", cash=1000, properties=["t1", "t2"])
        # Two tiles of same color, both owned by p1 - satisfies owns_full_set
        t1 = Tile(
            id="t1",
            name="Prop1",
            type=TileType.PROPERTY,
            owner_id="p1",
            color="RED",
            upgrade_level=0,
        )
        t2 = Tile(
            id="t2",
            name="Prop2",
            type=TileType.PROPERTY,
            owner_id="p1",
            color="RED",
            upgrade_level=0,
        )
        game = _make_game(
            "g1", players=[p1], board=[t1, t2], phase=TurnPhase.POST_TURN, current_player_id="p1"
        )
        game.settings.enable_upgrades = True
        normal_result = _make_action_result("OK", data={})
        mock_dispatcher.dispatch.return_value = normal_result
        sim_manager._get_game = AsyncMock(return_value=game)

        turn_info: dict[str, Any] = {"actions": []}
        coverage: dict[str, int] = {}
        # random < 0.2 for upgrade trigger
        with patch("random.random", return_value=0.1), patch("random.choice", return_value=t1):
            await sim_manager._execute_simulated_turn("g1", p1, turn_info, coverage)

        assert "UPGRADE" in coverage

    @pytest.mark.asyncio
    async def test_post_turn_block_tile_ddos(
        self, sim_manager: SimulationManager, mock_dispatcher: AsyncMock
    ) -> None:
        """Tests BLOCK_TILE action when player has DDOS buff."""
        p1 = _make_player("p1", cash=500, active_buff="DDOS")
        blockable = Tile(id="t1", name="SomeProp", type=TileType.PROPERTY)
        game = _make_game(
            "g1", players=[p1], board=[blockable], phase=TurnPhase.POST_TURN, current_player_id="p1"
        )
        normal_result = _make_action_result("OK", data={})
        mock_dispatcher.dispatch.return_value = normal_result
        sim_manager._get_game = AsyncMock(return_value=game)

        turn_info: dict[str, Any] = {"actions": []}
        coverage: dict[str, int] = {}
        with (
            patch("random.random", return_value=0.1),
            patch("random.choice", return_value=blockable),
        ):
            await sim_manager._execute_simulated_turn("g1", p1, turn_info, coverage)

        assert "BLOCK_TILE" in coverage


class TestSimulateCpuGameMainLoop:
    """Tests for the simulate_cpu_game main loop branches."""

    def _make_full_sim_manager(
        self, mock_repo: AsyncMock, mock_dispatcher: AsyncMock, **kwargs: Any
    ) -> SimulationManager:
        return SimulationManager(
            repository=mock_repo,
            action_dispatcher=mock_dispatcher,
            get_game_callback=AsyncMock(),
            start_game_callback=AsyncMock(),
            **kwargs,
        )

    @pytest.mark.asyncio
    async def test_game_over_from_execute_turn_appends_and_breaks(
        self, mock_repo: AsyncMock, mock_dispatcher: AsyncMock
    ) -> None:
        """When _execute_simulated_turn returns True, turn_info is appended and loop breaks."""
        mgr = self._make_full_sim_manager(mock_repo, mock_dispatcher)

        p1 = _make_player("p1", cash=1000)
        p2 = _make_player("p2", cash=500)
        game = _make_game("g1", players=[p1, p2], status=GameStatus.ACTIVE, current_player_id="p1")

        mgr._get_game = AsyncMock(return_value=game)
        mgr._execute_simulated_turn = AsyncMock(return_value=True)  # type: ignore[assignment]
        mgr._handle_stuck_state = AsyncMock()  # type: ignore[assignment]

        result = await mgr.simulate_cpu_game("g1", max_turns=5)
        assert result["turns_played"] == 0  # breaks before incrementing
        assert len(result["turn_log"]) == 1  # appended the turn_info

    @pytest.mark.asyncio
    async def test_simulate_cpu_game_lobby_with_two_players_starts(
        self, mock_repo: AsyncMock, mock_dispatcher: AsyncMock
    ) -> None:
        """When status is LOBBY with 2+ players, _start_game is called."""
        mgr = self._make_full_sim_manager(mock_repo, mock_dispatcher)

        p1 = _make_player("p1", cash=1000)
        p2 = _make_player("p2", cash=500)
        lobby_game = _make_game("g1", players=[p1, p2], status=GameStatus.LOBBY)
        active_game = _make_game(
            "g1", players=[p1, p2], status=GameStatus.ACTIVE, current_player_id="nobody"
        )

        mgr._get_game = AsyncMock(return_value=active_game)
        mgr._start_game = AsyncMock(return_value=active_game)

        # First _get_game call returns lobby
        call_num = 0

        async def get_game_se(gid: str) -> GameSession:
            nonlocal call_num
            call_num += 1
            if call_num == 1:
                return lobby_game
            return active_game

        mgr._get_game = get_game_se  # type: ignore[assignment]

        result = await mgr.simulate_cpu_game("g1", max_turns=3)
        mgr._start_game.assert_called_once()
        assert "game_id" in result
