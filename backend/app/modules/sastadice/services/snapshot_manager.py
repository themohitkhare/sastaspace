"""Snapshot and replay system with time-travel debugging support."""

import json
import logging
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any

from app.modules.sastadice.schemas import ChaosConfig, GameSession

logger = logging.getLogger(__name__)


class StateFrame:
    """Single point-in-time state capture."""

    def __init__(
        self,
        turn_number: int,
        round_number: int,
        timestamp: datetime,
        game_state: GameSession,
        last_action: dict[str, Any] | None = None,
        invariant_status: list[str] | None = None,
    ):
        self.turn_number = turn_number
        self.round_number = round_number
        self.timestamp = timestamp
        self.game_state = game_state
        self.last_action = last_action
        self.invariant_status = invariant_status or []

    def to_dict(self) -> dict[str, Any]:
        """Convert to serializable dict."""
        return {
            "turn_number": self.turn_number,
            "round_number": self.round_number,
            "timestamp": self.timestamp.isoformat(),
            "game_state": self.game_state.model_dump(),
            "last_action": self.last_action,
            "invariant_status": self.invariant_status,
        }


class GameSnapshot:
    """Full snapshot with rolling history."""

    def __init__(
        self,
        capture_reason: str,
        error: str | None,
        chaos_config: ChaosConfig | None,
        invariant_violations: list[str],
        state_history: list[StateFrame],
        action_history: list[dict[str, Any]],
    ):
        self.capture_reason = capture_reason
        self.error = error
        self.chaos_config = chaos_config
        self.invariant_violations = invariant_violations
        self.state_history = state_history
        self.action_history = action_history

    def to_dict(self) -> dict[str, Any]:
        """Convert to serializable dict."""
        return {
            "capture_reason": self.capture_reason,
            "error": self.error,
            "chaos_config": self.chaos_config.model_dump() if self.chaos_config else None,
            "invariant_violations": [str(v) for v in self.invariant_violations],
            "state_history": [frame.to_dict() for frame in self.state_history],
            "action_history": self.action_history,
        }


class SnapshotManager:
    """Manages game state snapshots with time-travel debugging via rolling buffer."""

    HISTORY_SIZE = 5  # Rolling buffer of last N states

    def __init__(self, chaos_config: ChaosConfig | None = None):
        self._config = chaos_config
        self._state_buffer: dict[str, deque[StateFrame]] = {}  # game_id -> buffer
        self._action_log: dict[str, list[dict[str, Any]]] = {}  # game_id -> actions
        logger.info(f"SnapshotManager initialized with history size: {self.HISTORY_SIZE}")

    def record_state(self, game: GameSession, action: dict[str, Any] | None = None) -> None:
        """Maintain rolling history. game: current state; action: last action if any."""
        if game.id not in self._state_buffer:
            self._state_buffer[game.id] = deque(maxlen=self.HISTORY_SIZE)
            self._action_log[game.id] = []

        if action:
            self._action_log[game.id].append(
                {"timestamp": datetime.utcnow().isoformat(), "action": action}
            )

        frame = StateFrame(
            turn_number=len(self._action_log[game.id]),
            round_number=game.current_round,
            timestamp=datetime.utcnow(),
            game_state=game.model_copy(deep=True),  # Deep copy!
            last_action=action,
            invariant_status=[],
        )

        self._state_buffer[game.id].append(frame)
        logger.debug(
            f"Recorded state for game {game.id[:8]}... (buffer size: {len(self._state_buffer[game.id])})"
        )

    def capture(
        self,
        game: GameSession,
        reason: str,
        error: str | None = None,
        violations: list[str] | None = None,
    ) -> str:
        """Save snapshot to JSON; returns path. reason/error/violations for debugging."""
        history = list(self._state_buffer.get(game.id, []))
        action_history = self._action_log.get(game.id, [])

        snapshot = GameSnapshot(
            capture_reason=reason,
            error=error,
            chaos_config=self._config,
            invariant_violations=violations or [],
            state_history=history,
            action_history=action_history,
        )

        snapshots_dir = Path("snapshots")
        snapshots_dir.mkdir(exist_ok=True)

        timestamp = int(datetime.utcnow().timestamp())
        filepath = snapshots_dir / f"{reason}_{game.id[:8]}_{timestamp}.json"

        with open(filepath, "w") as f:
            json.dump(snapshot.to_dict(), f, indent=2)

        logger.info(
            f"Snapshot captured: {filepath} "
            f"({len(history)} historical states, {len(action_history)} actions)"
        )

        return str(filepath)

    def load_snapshot(self, snapshot_path: str) -> GameSnapshot:
        with open(snapshot_path) as f:
            data = json.load(f)
        state_history = []
        for frame_data in data.get("state_history", []):
            game_state = GameSession(**frame_data["game_state"])
            frame = StateFrame(
                turn_number=frame_data["turn_number"],
                round_number=frame_data["round_number"],
                timestamp=datetime.fromisoformat(frame_data["timestamp"]),
                game_state=game_state,
                last_action=frame_data.get("last_action"),
                invariant_status=frame_data.get("invariant_status", []),
            )
            state_history.append(frame)

        chaos_config = None
        if data.get("chaos_config"):
            chaos_config = ChaosConfig(**data["chaos_config"])

        snapshot = GameSnapshot(
            capture_reason=data["capture_reason"],
            error=data.get("error"),
            chaos_config=chaos_config,
            invariant_violations=data.get("invariant_violations", []),
            state_history=state_history,
            action_history=data.get("action_history", []),
        )

        logger.info(f"Loaded snapshot from {snapshot_path}: {len(state_history)} states")
        return snapshot

    def replay_to_frame(self, snapshot_path: str, frame_index: int = -1) -> GameSession:
        snapshot = self.load_snapshot(snapshot_path)

        if not snapshot.state_history:
            raise ValueError("Snapshot has no state history to replay from")

        if frame_index < 0:
            frame_index = len(snapshot.state_history) + frame_index

        if not (0 <= frame_index < len(snapshot.state_history)):
            raise IndexError(
                f"Frame index {frame_index} out of range "
                f"(snapshot has {len(snapshot.state_history)} frames)"
            )

        frame = snapshot.state_history[frame_index]
        logger.info(
            f"Replaying to frame {frame_index} "
            f"(turn {frame.turn_number}, round {frame.round_number})"
        )

        return frame.game_state

    def print_snapshot_summary(self, snapshot_path: str) -> None:
        snapshot = self.load_snapshot(snapshot_path)

        print("=" * 80)
        print(f"SNAPSHOT SUMMARY: {snapshot_path}")
        print("=" * 80)
        print(f"Capture Reason: {snapshot.capture_reason}")
        print(f"Error: {snapshot.error or 'None'}")
        print(f"Violations: {len(snapshot.invariant_violations)}")

        if snapshot.invariant_violations:
            for v in snapshot.invariant_violations:
                print(f"  - {v}")

        print(f"\nState History: {len(snapshot.state_history)} frames")
        for i, frame in enumerate(snapshot.state_history):
            print(
                f"  [{i}] Turn {frame.turn_number}, Round {frame.round_number}, "
                f"Phase: {frame.game_state.turn_phase.value}"
            )
            if frame.last_action:
                print(f"      Last Action: {frame.last_action.get('type', 'unknown')}")

        print(f"\nAction History: {len(snapshot.action_history)} actions")

        if snapshot.chaos_config:
            print("\nChaos Config:")
            print(f"  Seed: {snapshot.chaos_config.seed}")
            print(f"  Chaos Probability: {snapshot.chaos_config.chaos_probability}")

        print("=" * 80)

    def clear_history(self, game_id: str) -> None:
        """Clear history for a specific game to free memory."""
        if game_id in self._state_buffer:
            del self._state_buffer[game_id]
        if game_id in self._action_log:
            del self._action_log[game_id]
        logger.debug(f"Cleared history for game {game_id[:8]}...")
