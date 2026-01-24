"""Economic health monitoring for detecting inflation and stalemates."""
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.modules.sastadice.schemas import TileType

if TYPE_CHECKING:
    from app.modules.sastadice.schemas import GameSession

logger = logging.getLogger(__name__)


@dataclass
class EconomicMetrics:
    """Tracks economic health of a game at a specific round."""
    round_number: int
    total_system_cash: int
    cash_per_player: dict[str, int]
    properties_owned: int
    properties_traded_this_round: int
    bankruptcies_this_round: int
    go_bonus_paid_this_round: int = 0
    rent_collected_this_round: int = 0


@dataclass
class EconomicReport:
    """Final report on game economic health."""
    game_id: str
    rounds_played: int
    inflation_detected: bool
    stalemate_detected: bool
    avg_cash_per_round: list[int]
    cash_velocity: list[int]  # Delta per round
    asset_turnover_rate: float
    peak_system_cash: int
    final_system_cash: int
    diagnosis: str
    recommendations: list[str]


class EconomicViolationError(Exception):
    """Raised when economic invariants are violated."""
    
    def __init__(self, violations: list[str]):
        self.violations = violations
        super().__init__(f"Economic violations detected:\n" + "\n".join(violations))


class InflationMonitor:
    """Detects economic stalemates and runaway inflation."""
    
    # Failure thresholds
    INFLATION_STREAK_LIMIT = 10  # Fail if cash grows 10 rounds straight after R20
    STALEMATE_TURN_LIMIT = 20    # Fail if 0 property changes for 20 turns
    MIN_AUDIT_ROUND = 20         # Only start checking after round 20
    
    def __init__(self):
        self.metrics_history: list[EconomicMetrics] = []
        self.consecutive_cash_growth = 0
        self.turns_without_property_change = 0
        self.last_property_state: set[tuple[str, str]] = set()  # (tile_id, owner_id)
    
    def record_round_end(self, game: "GameSession") -> EconomicMetrics:
        """Call at end of each round to track economic state."""
        metrics = EconomicMetrics(
            round_number=game.current_round,
            total_system_cash=sum(p.cash for p in game.players if not p.is_bankrupt),
            cash_per_player={p.id: p.cash for p in game.players},
            properties_owned=len([t for t in game.board if t.owner_id]),
            properties_traded_this_round=self._count_property_changes(game),
            bankruptcies_this_round=0,  # Tracked separately
        )
        self.metrics_history.append(metrics)
        return metrics
    
    def check_economic_health(self, game: "GameSession") -> list[str]:
        """Run economic health checks. Returns list of violations."""
        violations = []
        
        if game.current_round < self.MIN_AUDIT_ROUND:
            return violations
        
        if len(self.metrics_history) >= 2:
            current_cash = self.metrics_history[-1].total_system_cash
            previous_cash = self.metrics_history[-2].total_system_cash
            if current_cash > previous_cash:
                self.consecutive_cash_growth += 1
            else:
                self.consecutive_cash_growth = 0
            if self.consecutive_cash_growth >= self.INFLATION_STREAK_LIMIT:
                violations.append(
                    f"INFLATION_RUNAWAY: System cash grew for {self.consecutive_cash_growth} "
                    f"consecutive rounds. Current: ${current_cash:,}"
                )
        current_property_state = {
            (t.id, t.owner_id or "unowned") 
            for t in game.board if t.type == TileType.PROPERTY
        }
        
        if current_property_state == self.last_property_state:
            self.turns_without_property_change += 1
        else:
            self.turns_without_property_change = 0
            self.last_property_state = current_property_state
        
        if self.turns_without_property_change >= self.STALEMATE_TURN_LIMIT:
            violations.append(
                f"ECONOMIC_STALEMATE: No property changes for {self.turns_without_property_change} "
                f"turns. Game is deadlocked."
            )
        
        if len(self.metrics_history) > 0:
            active_players = [p for p in game.players if not p.is_bankrupt]
            if len(active_players) >= 2:
                cash_values = [p.cash for p in active_players]
                max_cash = max(cash_values)
                min_cash = min(cash_values)
                if max_cash > 0 and min_cash > 0 and max_cash / min_cash > 100:
                    violations.append(
                        f"WEALTH_IMBALANCE: Richest player has 100x+ more than poorest "
                        f"(${max_cash:,} vs ${min_cash:,})"
                    )

            # Check Gini Coefficient for inequality stalemate
            gini = self._calculate_gini(cash_values)
            if gini > 0.9 and game.current_round > 100:
                 violations.append(
                     f"EXTREME_INEQUALITY_STALEMATE: Gini coefficient {gini:.2f} > 0.9 after round 100. "
                     f"Game is likely soft-locked by a hoarder."
                 )
        
        return violations

    def _calculate_gini(self, values: list[int]) -> float:
        """Calculate Gini coefficient for wealth inequality."""
        if not values or all(v == 0 for v in values):
            return 0.0
        
        # Ensure non-negative for standard Gini
        values = sorted([max(0, v) for v in values])
        n = len(values)
        if n == 0: 
            return 0.0
            
        mean = sum(values) / n
        if mean == 0:
            return 0.0
            
        sum_abs_diff = sum(abs(x - y) for x in values for y in values)
        return sum_abs_diff / (2 * n * n * mean)
    
    def generate_report(self, game: "GameSession") -> EconomicReport:
        """Generate final economic health report."""
        if not self.metrics_history:
            return EconomicReport(
                game_id=game.id,
                rounds_played=0,
                inflation_detected=False,
                stalemate_detected=False,
                avg_cash_per_round=[],
                cash_velocity=[],
                asset_turnover_rate=0.0,
                peak_system_cash=0,
                final_system_cash=0,
                diagnosis="No data collected",
                recommendations=[]
            )
        
        cash_history = [m.total_system_cash for m in self.metrics_history]
        velocity = [cash_history[i] - cash_history[i-1] for i in range(1, len(cash_history))]
        
        inflation_detected = self.consecutive_cash_growth >= self.INFLATION_STREAK_LIMIT
        stalemate_detected = self.turns_without_property_change >= self.STALEMATE_TURN_LIMIT
        
        total_changes = sum(m.properties_traded_this_round for m in self.metrics_history)
        total_rounds = len(self.metrics_history)
        turnover_rate = total_changes / total_rounds if total_rounds > 0 else 0
        
        diagnosis = "HEALTHY"
        recommendations = []
        
        if inflation_detected:
            diagnosis = "RUNAWAY_INFLATION"
            recommendations.extend([
                "Implement dynamic rent scaling: rent *= (1 + round * 0.1)",
                "Add wealth tax event: pay 10% of net worth",
                "Cap GO bonus at 3x base value"
            ])
        
        if stalemate_detected:
            diagnosis = "ECONOMIC_STALEMATE" if diagnosis == "HEALTHY" else f"{diagnosis} + STALEMATE"
            recommendations.extend([
                "Increase event frequency to force property changes",
                "Add 'Hostile Takeover' event for stuck games",
                "Reduce late-game property prices"
            ])
        
        return EconomicReport(
            game_id=game.id,
            rounds_played=total_rounds,
            inflation_detected=inflation_detected,
            stalemate_detected=stalemate_detected,
            avg_cash_per_round=cash_history,
            cash_velocity=velocity,
            asset_turnover_rate=turnover_rate,
            peak_system_cash=max(cash_history) if cash_history else 0,
            final_system_cash=cash_history[-1] if cash_history else 0,
            diagnosis=diagnosis,
            recommendations=recommendations
        )
    
    def _count_property_changes(self, game: "GameSession") -> int:
        """Count properties that changed hands since last check."""
        current = {(t.id, t.owner_id or "unowned") for t in game.board if t.type == TileType.PROPERTY}
        changes = len(current - self.last_property_state)
        return changes
    
    def format_report(self, report: EconomicReport) -> str:
        """Format economic report as human-readable text."""
        lines = []
        lines.append("=" * 80)
        lines.append(" " * 24 + "ECONOMIC BALANCE REPORT")
        lines.append("=" * 80)
        lines.append(f"Game ID:        {report.game_id[:16]}...")
        lines.append(f"Rounds Played:  {report.rounds_played}")
        lines.append(f"Diagnosis:      {report.diagnosis}")
        lines.append("")
        
        if report.avg_cash_per_round:
            lines.append("📈 CASH VELOCITY")
            if len(report.avg_cash_per_round) > 0:
                lines.append(f"  Round 1:   ${report.avg_cash_per_round[0]:,} total  (+$0)")
            if len(report.avg_cash_per_round) > 20:
                r20_cash = report.avg_cash_per_round[19]
                r20_avg_vel = sum(report.cash_velocity[:20]) // 20 if report.cash_velocity else 0
                lines.append(f"  Round 20:  ${r20_cash:,} total (+${r20_avg_vel}/round avg)")
            if len(report.avg_cash_per_round) > 50:
                r50_cash = report.avg_cash_per_round[49]
                r50_avg_vel = sum(report.cash_velocity[20:50]) // 30 if len(report.cash_velocity) > 50 else 0
                warning = "  ⚠️ ACCELERATION" if report.inflation_detected else ""
                lines.append(f"  Round 50:  ${r50_cash:,} total (+${r50_avg_vel}/round avg){warning}")
            if len(report.avg_cash_per_round) > 87:
                r87_cash = report.avg_cash_per_round[86]
                r87_avg_vel = sum(report.cash_velocity[50:87]) // 37 if len(report.cash_velocity) > 87 else 0
                critical = " 🔴 CRITICAL" if report.inflation_detected else ""
                lines.append(f"  Round 87:  ${r87_cash:,} total (+${r87_avg_vel}/round avg){critical}")
            lines.append("")
        
        lines.append("📊 KEY METRICS")
        lines.append(f"  Peak System Cash:     ${report.peak_system_cash:,}")
        lines.append(f"  Final System Cash:    ${report.final_system_cash:,}")
        lines.append(f"  Asset Turnover Rate:  {report.asset_turnover_rate:.2f} properties/round")
        lines.append("")
        
        if report.recommendations:
            lines.append("🏥 RECOMMENDATIONS")
            for i, rec in enumerate(report.recommendations, 1):
                lines.append(f"  {i}. {rec}")
        
        lines.append("=" * 80)
        return "\n".join(lines)
