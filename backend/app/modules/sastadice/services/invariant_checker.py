"""Invariant checker for game state validation with strict/lenient modes."""
import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from app.modules.sastadice.schemas import GameStatus, TileType, TurnPhase

if TYPE_CHECKING:
    from app.modules.sastadice.schemas import GameSession, Player, Tile

logger = logging.getLogger(__name__)


class StrictnessMode(Enum):
    """Invariant checking strictness modes."""
    STRICT = "strict"      # Fail fast (dev/test)
    LENIENT = "lenient"    # Log + auto-correct (prod)


@dataclass
class InvariantViolation:
    """Represents a violation of a game state invariant."""
    type: str
    severity: str  # "CRITICAL", "WARNING"
    message: str
    game_id: str
    round_number: int
    turn_phase: str


class InvariantViolationError(Exception):
    """Raised when invariants are violated in strict mode."""
    
    def __init__(self, violations: list[InvariantViolation]):
        self.violations = violations
        messages = [f"{v.type}: {v.message}" for v in violations]
        super().__init__(f"Invariant violations detected:\n" + "\n".join(messages))


class InvariantChecker:
    """Validates game state consistency after every action."""
    
    def __init__(self, mode: StrictnessMode = StrictnessMode.STRICT):
        self.mode = mode
        self.violation_log: list[InvariantViolation] = []
    
    def check_all(self, game: "GameSession") -> list[InvariantViolation]:
        """Run all invariant checks on game state."""
        violations = []
        violations.extend(self._check_asset_conservation(game))
        violations.extend(self._check_cash_integrity(game))
        violations.extend(self._check_turn_order(game))
        violations.extend(self._check_phase_validity(game))
        violations.extend(self._check_position_bounds(game))
        
        if violations:
            self.violation_log.extend(violations)
            if self.mode == StrictnessMode.STRICT:
                raise InvariantViolationError(violations)
            else:
                self._attempt_auto_corrections(game, violations)
        
        return violations
    
    def _check_asset_conservation(self, game: "GameSession") -> list[InvariantViolation]:
        """Verify property ownership consistency."""
        violations = []
        property_tiles = [t for t in game.board if t.type == TileType.PROPERTY]
        
        ownership_map = {}
        for tile in property_tiles:
            if tile.owner_id:
                if tile.id in ownership_map:
                    violations.append(InvariantViolation(
                        type="DUPLICATE_OWNERSHIP",
                        severity="CRITICAL",
                        message=f"Tile {tile.id} ({tile.name}) has duplicate owner",
                        game_id=game.id,
                        round_number=game.current_round,
                        turn_phase=game.turn_phase.value
                    ))
                ownership_map[tile.id] = tile.owner_id
        
        for player in game.players:
            for prop_id in player.properties:
                tile = next((t for t in game.board if t.id == prop_id), None)
                if not tile:
                    violations.append(InvariantViolation(
                        type="ORPHANED_PROPERTY",
                        severity="CRITICAL",
                        message=f"Player {player.name} owns non-existent property {prop_id}",
                        game_id=game.id,
                        round_number=game.current_round,
                        turn_phase=game.turn_phase.value
                    ))
                elif tile.owner_id != player.id:
                    violations.append(InvariantViolation(
                        type="OWNERSHIP_MISMATCH",
                        severity="CRITICAL",
                        message=f"Player {player.name} claims {tile.name} but tile owner is {tile.owner_id}",
                        game_id=game.id,
                        round_number=game.current_round,
                        turn_phase=game.turn_phase.value
                    ))
        
        for tile in property_tiles:
            if tile.owner_id:
                player = next((p for p in game.players if p.id == tile.owner_id), None)
                if not player:
                    violations.append(InvariantViolation(
                        type="ORPHANED_OWNER",
                        severity="CRITICAL",
                        message=f"Tile {tile.name} owned by non-existent player {tile.owner_id}",
                        game_id=game.id,
                        round_number=game.current_round,
                        turn_phase=game.turn_phase.value
                    ))
                elif tile.id not in player.properties:
                    violations.append(InvariantViolation(
                        type="MISSING_PROPERTY_REFERENCE",
                        severity="CRITICAL",
                        message=f"Tile {tile.name} owner is {player.name} but not in their properties list",
                        game_id=game.id,
                        round_number=game.current_round,
                        turn_phase=game.turn_phase.value
                    ))
        
        return violations

    def check_financial_integrity(
        self, 
        game: "GameSession", 
        previous_system_cash: int, 
        expected_delta: int
    ) -> list[InvariantViolation]:
        """Verify conservation of mass for system cash."""
        violations = []
        
        current_system_cash = sum(p.cash for p in game.players if not p.is_bankrupt)
        expected_total = previous_system_cash + expected_delta
        
        if current_system_cash != expected_total:
            violations.append(InvariantViolation(
                type="FINANCIAL_INTEGRITY_FAILURE",
                severity="CRITICAL",
                message=f"System cash mismatch. Expected ${expected_total:,} (Prev ${previous_system_cash:,} + Delta ${expected_delta:,}), "
                        f"but found ${current_system_cash:,}. Variance: ${current_system_cash - expected_total}",
                game_id=game.id,
                round_number=game.current_round,
                turn_phase=game.turn_phase.value
            ))
            
        return violations

    def _check_cash_integrity(self, game: "GameSession") -> list[InvariantViolation]:
        """Verify cash consistency (no negatives)."""
        violations = []
        
        for player in game.players:
            if player.cash < 0 and not player.is_bankrupt:
                violations.append(InvariantViolation(
                    type="NEGATIVE_CASH_NOT_BANKRUPT",
                    severity="CRITICAL",
                    message=f"Player {player.name} has ${player.cash} but is_bankrupt=False",
                    game_id=game.id,
                    round_number=game.current_round,
                    turn_phase=game.turn_phase.value
                ))
        
        return violations
    
    def _check_turn_order(self, game: "GameSession") -> list[InvariantViolation]:
        """Verify turn order validity."""
        violations = []
        if game.status == GameStatus.ACTIVE:
            if not game.current_turn_player_id:
                violations.append(InvariantViolation(
                    type="MISSING_TURN_PLAYER",
                    severity="CRITICAL",
                    message="Game is ACTIVE but current_turn_player_id is None",
                    game_id=game.id,
                    round_number=game.current_round,
                    turn_phase=game.turn_phase.value
                ))
            else:
                current_player = next((p for p in game.players if p.id == game.current_turn_player_id), None)
                if not current_player:
                    violations.append(InvariantViolation(
                        type="ORPHANED_TURN_PLAYER",
                        severity="CRITICAL",
                        message=f"current_turn_player_id {game.current_turn_player_id} does not exist",
                        game_id=game.id,
                        round_number=game.current_round,
                        turn_phase=game.turn_phase.value
                    ))
                elif current_player.is_bankrupt:
                    violations.append(InvariantViolation(
                        type="BANKRUPT_TURN_PLAYER",
                        severity="CRITICAL",
                        message=f"current_turn_player {current_player.name} is bankrupt",
                        game_id=game.id,
                        round_number=game.current_round,
                        turn_phase=game.turn_phase.value
                    ))
        
        return violations
    
    def _check_phase_validity(self, game: "GameSession") -> list[InvariantViolation]:
        """Verify phase transition rules."""
        violations = []
        if game.pending_decision and game.turn_phase != TurnPhase.DECISION:
            violations.append(InvariantViolation(
                type="ORPHANED_PENDING_DECISION",
                severity="WARNING",
                message=f"pending_decision exists but turn_phase is {game.turn_phase.value}",
                game_id=game.id,
                round_number=game.current_round,
                turn_phase=game.turn_phase.value
            ))
        
        return violations
    
    def _check_position_bounds(self, game: "GameSession") -> list[InvariantViolation]:
        """Verify player positions are valid."""
        violations = []
        
        board_size = len(game.board)
        
        for player in game.players:
            if not (0 <= player.position < board_size):
                violations.append(InvariantViolation(
                    type="POSITION_OUT_OF_BOUNDS",
                    severity="CRITICAL",
                    message=f"Player {player.name} position {player.position} out of bounds (board size: {board_size})",
                    game_id=game.id,
                    round_number=game.current_round,
                    turn_phase=game.turn_phase.value
                ))
            
            if player.previous_position is not None and not (0 <= player.previous_position < board_size):
                violations.append(InvariantViolation(
                    type="PREVIOUS_POSITION_OUT_OF_BOUNDS",
                    severity="WARNING",
                    message=f"Player {player.name} previous_position {player.previous_position} out of bounds",
                    game_id=game.id,
                    round_number=game.current_round,
                    turn_phase=game.turn_phase.value
                ))
        
        return violations
    
    def _attempt_auto_corrections(self, game: "GameSession", violations: list[InvariantViolation]) -> None:
        """Best-effort fixes to keep game playable in production."""
        for v in violations:
            if v.type == "ORPHANED_PENDING_DECISION":
                game.pending_decision = None
                logger.warning(f"Auto-corrected: Cleared orphaned pending_decision: {v.message}")
            
            elif v.type == "NEGATIVE_CASH_NOT_BANKRUPT":
                player = next((p for p in game.players if f"Player {p.name}" in v.message), None)
                if player:
                    player.is_bankrupt = True
                    logger.warning(f"Auto-corrected: Marked {player.name} as bankrupt: {v.message}")
            
            elif v.type == "ORPHANED_TURN_PLAYER" or v.type == "BANKRUPT_TURN_PLAYER":
                next_player = self._find_next_active_player(game)
                if next_player:
                    game.current_turn_player_id = next_player.id
                    game.turn_phase = TurnPhase.PRE_ROLL
                    logger.warning(f"Auto-corrected: Advanced to next player {next_player.name}: {v.message}")
            
            elif v.type == "POSITION_OUT_OF_BOUNDS":
                player = next((p for p in game.players if f"Player {p.name}" in v.message), None)
                if player:
                    player.position = max(0, min(player.position, len(game.board) - 1))
                    logger.warning(f"Auto-corrected: Clamped {player.name} position: {v.message}")
    
    def _find_next_active_player(self, game: "GameSession") -> "Player | None":
        """Find next active, non-bankrupt player."""
        if not game.players:
            return None
        
        current_idx = 0
        if game.current_turn_player_id:
            current_idx = next((i for i, p in enumerate(game.players) if p.id == game.current_turn_player_id), 0)
        
        for offset in range(1, len(game.players) + 1):
            next_idx = (current_idx + offset) % len(game.players)
            candidate = game.players[next_idx]
            if not candidate.is_bankrupt:
                return candidate
        
        return None
