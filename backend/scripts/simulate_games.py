#!/usr/bin/env python3
"""Enhanced simulation script to test all SastaDice game configurations."""
import argparse
import asyncio
import logging
import random
import sys
import traceback
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.logging_config import setup_logging
from app.modules.sastadice.schemas import (
    ChaosConfig,
    ChaosLevel,
    GameSettings,
    TileType,
    WinCondition,
)
from app.modules.sastadice.services.game_service import GameService

setup_logging(level="INFO")
logger = logging.getLogger(__name__)


class SimulationStats:
    """Track statistics across all simulated games."""

    def __init__(self):
        self.games_run = 0
        self.games_completed = 0
        self.games_errored = 0
        self.total_turns = 0
        self.total_rounds = 0
        self.sudden_deaths = 0
        self.bankruptcies = 0
        self.last_standing_wins = 0
        self.errors: list[str] = []

        # Feature tracking
        self.go_bonus_collected = 0
        self.properties_bought = 0
        self.jail_visits = 0
        self.glitch_teleports = 0
        self.market_visits = 0
        self.buffs_bought = 0
        self.doubles_rolled = 0
        self.stimulus_checks = 0
        # Phase 3 features
        self.ddos_buffs_bought = 0
        self.ddos_tiles_blocked = 0
        self.peek_buffs_bought = 0
        self.turn_timeouts = 0
        self.blocked_tiles_cleared = 0
        self.trades_proposed = 0
        self.trades_accepted = 0
        # Upgrade features (Monopoly audit fixes)
        self.properties_upgraded = 0
        self.properties_downgraded = 0
        self.cpu_upgrades = 0
        self.upgrade_to_script_kiddie = 0
        self.upgrade_to_1337_haxxor = 0

        self.configs_tested: dict[str, int] = {}
        self.action_coverage_merged: dict[str, int] = {}
        self.chaos_config_global = None


# Define test configurations
TEST_CONFIGS = [
    # ===== STANDARD CONFIGS =====
    {
        "name": "Default (Sudden Death 30)",
        "players": 4,
        "settings": GameSettings()
    },
    {
        "name": "Quick Game (15 rounds)",
        "players": 4,
        "settings": GameSettings(round_limit=15)
    },
    {
        "name": "Long Game (50 rounds)",
        "players": 3,
        "settings": GameSettings(round_limit=50)
    },
    {
        "name": "Extended Game (100 rounds)",
        "players": 2,
        "settings": GameSettings(round_limit=100)
    },

    # ===== WIN CONDITIONS =====
    {
        "name": "Last Standing (∞ rounds)",
        "players": 2,
        "settings": GameSettings(
            win_condition=WinCondition.LAST_STANDING,
            round_limit=0
        )
    },
    {
        "name": "Last Standing 3 Players",
        "players": 3,
        "settings": GameSettings(
            win_condition=WinCondition.LAST_STANDING,
            round_limit=0
        )
    },
    {
        "name": "First to $5000",
        "players": 4,
        "settings": GameSettings(
            win_condition=WinCondition.FIRST_TO_CASH,
            target_cash=5000,
            round_limit=100
        ),
        "max_turns": 800,
    },
    {
        "name": "First to $10000",
        "players": 3,
        "settings": GameSettings(
            win_condition=WinCondition.FIRST_TO_CASH,
            target_cash=10000,
            round_limit=150
        ),
        "max_turns": 1200,
    },

    # ===== ECONOMY VARIATIONS =====
    {
        "name": "Rich Start (2x cash)",
        "players": 4,
        "settings": GameSettings(starting_cash_multiplier=2.0)
    },
    {
        "name": "Poor Start (0.5x cash)",
        "players": 4,
        "settings": GameSettings(starting_cash_multiplier=0.5)
    },
    {
        "name": "High Inflation (+$50/round)",
        "players": 3,
        "settings": GameSettings(go_inflation_per_round=50)
    },
    {
        "name": "Low Inflation (+$5/round)",
        "players": 4,
        "settings": GameSettings(go_inflation_per_round=5)
    },
    {
        "name": "High GO Bonus ($500)",
        "players": 4,
        "settings": GameSettings(go_bonus_base=500)
    },

    # ===== CHAOS LEVELS =====
    {
        "name": "Chill Mode",
        "players": 4,
        "settings": GameSettings(chaos_level=ChaosLevel.CHILL)
    },
    {
        "name": "Chaos Mode",
        "players": 4,
        "settings": GameSettings(chaos_level=ChaosLevel.CHAOS)
    },
    {
        "name": "Chaos + Rich",
        "players": 4,
        "settings": GameSettings(
            chaos_level=ChaosLevel.CHAOS,
            starting_cash_multiplier=2.0
        )
    },

    # ===== JAIL VARIATIONS =====
    {
        "name": "Strict Jail (3 turns)",
        "players": 3,
        "settings": GameSettings(jail_turns_max=3)
    },
    {
        "name": "Expensive Jail ($200 bribe)",
        "players": 4,
        "settings": GameSettings(jail_bribe_cost=200)
    },

    # ===== PLAYER COUNT STRESS =====
    {
        "name": "2 Players",
        "players": 2,
        "settings": GameSettings(round_limit=20)
    },
    {
        "name": "3 Players",
        "players": 3,
        "settings": GameSettings(round_limit=25)
    },
    {
        "name": "5 Players",
        "players": 5,
        "settings": GameSettings()
    },

    # ===== FEATURE TOGGLES =====
    {
        "name": "No Stimulus",
        "players": 4,
        "settings": GameSettings(enable_stimulus=False)
    },
    {
        "name": "No Doubles Bonus",
        "players": 4,
        "settings": GameSettings(doubles_give_extra_turn=False)
    },
    {
        "name": "No Black Market",
        "players": 4,
        "settings": GameSettings(enable_black_market=False)
    },
    {
        "name": "No Trading",
        "players": 4,
        "settings": GameSettings(enable_trading=False)
    },
    {
        "name": "No Auctions",
        "players": 4,
        "settings": GameSettings(enable_auctions=False)
    },
    {
        "name": "No Upgrades",
        "players": 4,
        "settings": GameSettings(enable_upgrades=False)
    },
    {
        "name": "All Features Disabled",
        "players": 4,
        "settings": GameSettings(
            enable_stimulus=False,
            enable_black_market=False,
            enable_trading=False,
            enable_auctions=False,
            enable_upgrades=False,
            doubles_give_extra_turn=False
        )
    },

    # ===== UPGRADE-FOCUSED (Long games for upgrade opportunities) =====
    {
        "name": "Upgrade Focus (Rich + Long)",
        "players": 2,
        "settings": GameSettings(
            starting_cash_multiplier=3.0,
            round_limit=80,
            go_bonus_base=300
        )
    },
    {
        "name": "Upgrade Focus (2 Players Long)",
        "players": 2,
        "settings": GameSettings(
            starting_cash_multiplier=2.5,
            round_limit=100,
        )
    },

    # ===== TRADING FOCUS =====
    {
        "name": "Trading Focus (Long + Rich)",
        "players": 4,
        "settings": GameSettings(
            starting_cash_multiplier=2.0,
            round_limit=60,
            enable_trading=True
        )
    },

    # ===== TIMER/TIMEOUT =====
    {
        "name": "Fast Timer (10s)",
        "players": 4,
        "settings": GameSettings(turn_timer_seconds=10)
    },
    {
        "name": "Slow Timer (60s)",
        "players": 4,
        "settings": GameSettings(turn_timer_seconds=60)
    },

    # ===== STRESS TESTS =====
    {
        "name": "Stress: 5P Long Chaos",
        "players": 5,
        "settings": GameSettings(
            round_limit=100,
            chaos_level=ChaosLevel.CHAOS,
            go_inflation_per_round=30
        )
    },
    {
        "name": "Stress: 2P Last Standing Rich",
        "players": 2,
        "settings": GameSettings(
            win_condition=WinCondition.LAST_STANDING,
            starting_cash_multiplier=3.0,
            round_limit=0
        )
    },

    # ===== ECONOMIC STRESS TESTS =====
    {
        "name": "Inflation_Stress_200R",
        "players": 4,
        "settings": GameSettings(
            win_condition=WinCondition.LAST_STANDING,
            round_limit=200,  # Force long game
            enable_auctions=True,
            enable_trading=True,
        ),
        "expected_end": True,  # MUST end naturally via bankruptcy
        "max_turns": 2000,
    },
    {
        "name": "Deflation_Check_NoGO",
        "players": 4,
        "settings": GameSettings(
            go_bonus_base=0,  # No GO income
            go_inflation_per_round=0,
            round_limit=50,
        ),
        "expected_end": True,  # Should bankrupt quickly
    },
    {
        "name": "Hyperinflation_GO",
        "players": 3,
        "settings": GameSettings(
            go_bonus_base=500,
            go_inflation_per_round=100,  # Extreme inflation
            round_limit=0,  # No limit
            win_condition=WinCondition.LAST_STANDING,
        ),
        "expected_end": False,  # Expect this to potentially FAIL (reveals inflation bug)
        "max_turns": 1000,
    },

    # ===== MONKEY CHAOS =====
    {
        "name": "Monkey Chaos (High Probability)",
        "players": 4,
        "settings": GameSettings(
            chaos_level=ChaosLevel.CHAOS,
            round_limit=50,
        ),
        "chaos_override": True,
        "chaos_prob": 0.8,
    },
    {
        "name": "Monkey Economy Stress",
        "players": 4,
        "settings": GameSettings(
            go_inflation_per_round=50,
            starting_cash_multiplier=2.0,
            round_limit=60,
        ),
        "chaos_override": True,
        "chaos_prob": 0.5,
    },
]


async def simulate_single_game(
    service: GameService,
    game_num: int,
    cpu_count: int,
    settings: GameSettings,
    stats: SimulationStats,
    config_name: str,
    verbose: bool = True,
    max_turns: int = 500,
    enable_economic_monitoring: bool = False,
) -> dict:
    """Simulate a single game and track statistics."""

    if verbose:
        print(f"\n{'='*60}")
        print(f"Game {game_num}: {config_name}")
        print(f"  Players: {cpu_count} | Win: {settings.win_condition.value} | Rounds: {settings.round_limit or '∞'}")
        print(f"{'='*60}")

    stats.games_run += 1
    stats.configs_tested[config_name] = stats.configs_tested.get(config_name, 0) + 1

    try:
        game = await service.create_game(cpu_count=cpu_count)
        game.settings = settings
        game.max_rounds = settings.round_limit
        await service.repository.update(game)

        if verbose:
            print(f"✓ Game created: {game.id[:8]}...")
            print(f"  Players: {[p.name for p in game.players]}")

        logger.info(
            "Game created for simulation",
            extra={
                "extra_fields": {
                    "component": "simulation",
                    "game_id": game.id,
                    "config_name": config_name,
                    "cpu_count": cpu_count,
                    "win_condition": settings.win_condition.value,
                    "round_limit": settings.round_limit,
                }
            }
        )

        if game.status.value == "LOBBY":
            game = await service.start_game(game.id, force=True)

        board_analysis = analyze_board(game)
        if verbose:
            print(f"  Board: {len(game.board)} tiles, {board_analysis['properties']} properties")

        effective_max = max_turns
        if (
            settings.win_condition == WinCondition.SUDDEN_DEATH
            and settings.round_limit
            and settings.round_limit > 0
        ):
            effective_max = max(
                effective_max, settings.round_limit * cpu_count * 2
            )
        logger.info(
            "Starting game simulation",
            extra={
                "extra_fields": {
                    "component": "simulation",
                    "game_id": game.id,
                    "max_turns": effective_max,
                }
            }
        )

        sim_chaos_config = stats.chaos_config_global
        chaos_override_active = False
        config_override_prob = 0.5

        if game_num <= len(TEST_CONFIGS):
            conf = TEST_CONFIGS[game_num - 1]
            if conf.get("chaos_override"):
                chaos_override_active = True
                config_override_prob = conf.get("chaos_prob", 0.5)

        if chaos_override_active:
            sim_chaos_config = ChaosConfig(chaos_probability=config_override_prob)

        result = await service.simulate_cpu_game(
            game.id,
            max_turns=effective_max,
            enable_economic_monitoring=enable_economic_monitoring,
            chaos_config=sim_chaos_config
        )
        for k, v in result.get("action_coverage", {}).items():
            stats.action_coverage_merged[k] = stats.action_coverage_merged.get(k, 0) + v
        stats.games_completed += 1
        stats.total_turns += result.get("turns_played", 0)
        stats.total_rounds += result.get("rounds_played", 0)

        if result.get("rounds_played", 0) >= settings.round_limit and settings.round_limit > 0:
            stats.sudden_deaths += 1

        for p in result.get("final_standings", []):
            if p.get("bankrupt"):
                stats.bankruptcies += 1

        if settings.win_condition == WinCondition.LAST_STANDING:
            active = [p for p in result.get("final_standings", []) if not p.get("bankrupt")]
            if len(active) <= 1:
                stats.last_standing_wins += 1

        try:
            final_game = await service.get_game(game.id)
            cleared_count = sum(1 for t in final_game.board if t.blocked_until_round and t.blocked_until_round <= final_game.current_round)
            if final_game.current_round > 1 and cleared_count > 0:
                stats.blocked_tiles_cleared += cleared_count
        except Exception as e:
            if verbose:
                print(f"  Note: Could not check blocked tiles: {e}")

        # Analyze turn log
        for turn in result.get("turn_log", []):
            for action in turn.get("actions", []):
                action_result = action.get("result", "")
                action_type = action.get("action", "")
                if "DOUBLES" in action_result.upper():
                    stats.doubles_rolled += 1
                if "STIMULUS" in action_result.upper():
                    stats.stimulus_checks += 1
                if "GLITCH" in action_result.upper():
                    stats.glitch_teleports += 1
                if "JAIL" in action_result.upper() or "SERVER DOWNTIME" in action_result.upper():
                    stats.jail_visits += 1
                if "BUY_BUFF" in action_type:
                    stats.buffs_bought += 1
                    # Track specific buffs
                    if "DDOS" in action_result.upper() or "DDoS" in action_result:
                        stats.ddos_buffs_bought += 1
                    if "PEEK" in action_result.upper() or "INSIDER INFO" in action_result.upper():
                        stats.peek_buffs_bought += 1
                if "BLOCK_TILE" in action_type or "DDOS ATTACK" in action_result.upper():
                    stats.ddos_tiles_blocked += 1
                if "TIMEOUT" in action_result.upper() or "FORCED" in action_result.upper():
                    stats.turn_timeouts += 1
                if "PROPOSE_TRADE" in action_result or "PROPOSE_TRADE" in action_type:
                    stats.trades_proposed += 1
                if "ACCEPT_TRADE" in action_result or "ACCEPT_TRADE" in action_type:
                    stats.trades_accepted += 1
                # Upgrade/Downgrade tracking
                if "UPGRADE" in action_type or "upgraded" in action_result.lower():
                    stats.properties_upgraded += 1
                    if "SCRIPT KIDDIE" in action_result.upper():
                        stats.upgrade_to_script_kiddie += 1
                    if "1337 HAXXOR" in action_result.upper():
                        stats.upgrade_to_1337_haxxor += 1
                    # Check if CPU (CPU names in action result)
                    cpu_names = ["ROBOCOP", "CHAD BOT", "KAREN.EXE", "STONKS", "CPU-"]
                    if any(cpu in action_result.upper() for cpu in cpu_names):
                        stats.cpu_upgrades += 1
                if "DOWNGRADE" in action_type or "sold" in action_result.lower() and "upgrade" in action_result.lower():
                    stats.properties_downgraded += 1

        result["success"] = result.get("status") in ["ACTIVE", "FINISHED"]

        logger.info(
            "Game simulation completed",
            extra={
                "extra_fields": {
                    "component": "simulation",
                    "game_id": game.id,
                    "config_name": config_name,
                    "status": result.get("status"),
                    "turns_played": result.get("turns_played", 0),
                    "rounds_played": result.get("rounds_played", 0),
                    "winner": result.get("winner", {}).get("name") if result.get("winner") else None,
                }
            }
        )

        if verbose:
            print(f"\n✓ Game completed: {result['status']}")
            print(f"  Turns: {result['turns_played']} | Rounds: {result.get('rounds_played', 0)}")
            if result.get("winner"):
                print(f"  Winner: {result['winner'].get('name', 'N/A')} (${result['winner'].get('cash', 0)})")
            cov = result.get("action_coverage", {})
            if cov:
                print(f"  Coverage: {', '.join(f'{k}={v}' for k, v in sorted(cov.items())[:12])}{'...' if len(cov) > 12 else ''}")
        return result

    except Exception as e:
        stats.games_errored += 1
        stats.errors.append(f"[{config_name}] {str(e)}")

        logger.error(
            "Game simulation failed",
            extra={
                "extra_fields": {
                    "component": "simulation",
                    "config_name": config_name,
                    "error": str(e),
                }
            },
            exc_info=True
        )

        if verbose:
            print(f"\n✗ Game failed: {str(e)}")
            traceback.print_exc()

        return {
            "status": "ERROR",
            "turns_played": 0,
            "errors": [str(e)],
            "success": False
        }


def analyze_board(game) -> dict:
    """Analyze board composition."""
    properties = [t for t in game.board if t.type == TileType.PROPERTY]
    colors = set(t.color for t in properties if t.color)

    return {
        "total_tiles": len(game.board),
        "properties": len(properties),
        "colors": colors,
        "corner_tiles": {
            "GO": any(t.type == TileType.GO for t in game.board),
            "JAIL": any(t.type == TileType.JAIL for t in game.board),
            "GLITCH": any(t.type == TileType.TELEPORT for t in game.board),
            "MARKET": any(t.type == TileType.MARKET for t in game.board),
        }
    }


def save_economic_report(report, config_name: str):
    """Save economic balance report to file."""
    from app.modules.sastadice.services.inflation_monitor import InflationMonitor

    # Create reports directory
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    # Format report
    monitor = InflationMonitor()
    formatted_report = monitor.format_report(report)

    # Save to file
    timestamp = int(asyncio.get_event_loop().time() * 1000)
    filename = reports_dir / f"economy_balance_{config_name.replace(' ', '_')}_{timestamp}.txt"

    with open(filename, 'w') as f:
        f.write(formatted_report)

    print(f"\n📊 Economic report saved to: {filename}")
    print(formatted_report)


async def main():
    """Run comprehensive game simulation across all configurations."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run SastaDice game simulations with chaos testing")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--chaos-mode", action="store_true", help="Enable monkey/chaos strategy")
    parser.add_argument("--chaos-probability", type=float, default=0.3, help="Chaos probability (0.0-1.0)")
    parser.add_argument("--strictness", choices=["strict", "lenient"], default="strict",
                        help="Invariant checking mode (strict=fail fast, lenient=auto-correct)")
    parser.add_argument("--enable-economic-monitoring", action="store_true",
                        help="Enable economic health tracking and inflation detection")
    parser.add_argument("--drop-db-writes", type=float, default=0.0,
                        help="Probability of simulated DB write failures (0.0-1.0)")
    parser.add_argument("--delay-ms", type=int, default=0,
                        help="Milliseconds to delay all responses")
    parser.add_argument("--replay", type=str, default=None,
                        help="Path to snapshot JSON file to replay")
    parser.add_argument("--num-games", type=int, default=None, help="Number of games to run (default: all configs)")
    parser.add_argument("--quiet", action="store_true", help="One-line per game; no per-game blocks")
    args = parser.parse_args()

    # Set seed if provided
    seed = args.seed if args.seed is not None else random.randint(0, 2**32)
    random.seed(seed)
    print(f"SEED: {seed}")

    # Create chaos config if chaos mode enabled
    chaos_config = None
    if args.chaos_mode:
        from app.modules.sastadice.schemas import FaultInjectionConfig
        chaos_config = ChaosConfig(
            seed=seed,
            chaos_probability=args.chaos_probability,
            enable_invalid_actions=False,
            enable_race_conditions=False,
            fault_injection=FaultInjectionConfig(
                drop_db_writes=args.drop_db_writes,
                delay_responses_ms=args.delay_ms,
                corrupt_state_prob=0.0,
                network_partition=False
            )
        )

    # Handle replay mode
    if args.replay:
        from app.modules.sastadice.services.snapshot_manager import SnapshotManager
        snapshot_mgr = SnapshotManager()
        print(f"\n🔄 REPLAY MODE: Loading snapshot from {args.replay}")
        snapshot_mgr.print_snapshot_summary(args.replay)
        print("\nTo replay programmatically, use SnapshotManager.replay_to_frame()")
        return 0

    print("="*70)
    print("SASTADICE COMPREHENSIVE CONFIGURATION TESTING")
    if args.chaos_mode:
        print("🐒 CHAOS MODE ENABLED")
        print(f"   Chaos Probability: {args.chaos_probability}")
        print(f"   Strictness: {args.strictness}")
        if args.drop_db_writes > 0:
            print(f"   DB Write Failures: {args.drop_db_writes * 100:.1f}%")
        if args.delay_ms > 0:
            print(f"   Response Delay: {args.delay_ms}ms")
    if args.enable_economic_monitoring:
        print("📊 ECONOMIC MONITORING ENABLED")

    total = (
        args.num_games
        if args.num_games is not None
        else (len(TEST_CONFIGS) + 5)
    )
    n_fixed = min(total, len(TEST_CONFIGS))
    n_random = total - n_fixed
    if args.num_games is not None:
        print(f"Running {total} simulations ({n_fixed} fixed + {n_random} random configs)")
    else:
        print(f"Testing {len(TEST_CONFIGS)} fixed + 5 random configurations ({total} total)")
    print("="*70)

    # Connect to MongoDB (default localhost for host runs; set MONGODB_URL in Docker)
    import os
    mongo_url = os.environ.get("MONGODB_URL", "mongodb://localhost:27017")
    print(f"Connecting to: {mongo_url}")

    client = AsyncIOMotorClient(mongo_url)
    database = client.test_simulations

    try:
        service = GameService(database)
        stats = SimulationStats()
        stats.chaos_config_global = chaos_config

        game_num = 0

        semaphore = asyncio.Semaphore(50)  # Run 10 games in parallel for faster execution

        verbose = not args.quiet

        async def run_game_safely(g_num, config=None, is_random=False, r_cpu=None, r_settings=None, r_name=None):
            async with semaphore:
                if is_random:
                    await simulate_single_game(
                        service=service,
                        game_num=g_num,
                        cpu_count=r_cpu,
                        settings=r_settings,
                        stats=stats,
                        config_name=r_name,
                        verbose=verbose,
                        max_turns=500,
                        enable_economic_monitoring=args.enable_economic_monitoring,
                    )
                else:
                    await simulate_single_game(
                        service=service,
                        game_num=g_num,
                        cpu_count=config["players"],
                        settings=config["settings"],
                        stats=stats,
                        config_name=config["name"],
                        verbose=verbose,
                        max_turns=config.get("max_turns", 500),
                        enable_economic_monitoring=args.enable_economic_monitoring,
                    )

        tasks = []

        def make_random_settings():
            wc = random.choice(list(WinCondition))
            kw: dict = {
                "win_condition": wc,
                "round_limit": random.choice([0, 15, 20, 25, 30, 50, 60, 80, 100, 150, 200]),
                "go_bonus_base": random.choice([0, 150, 200, 250, 300, 500]),
                "go_inflation_per_round": random.choice([0, 5, 10, 20, 30, 50, 100]),
                "chaos_level": random.choice(list(ChaosLevel)),
                "starting_cash_multiplier": random.choice([0.5, 1.0, 1.5, 2.0, 2.5, 3.0]),
            }
            if wc == WinCondition.FIRST_TO_CASH:
                kw["target_cash"] = random.choice([3000, 5000, 8000, 10000, 15000])
            return GameSettings(**kw)

        for i in range(n_fixed):
            game_num += 1
            tasks.append(run_game_safely(game_num, config=TEST_CONFIGS[i]))

        if args.num_games is None:
            random.seed(42)
        for i in range(n_random):
            game_num += 1
            r_cpu = random.randint(2, 5)
            r_settings = make_random_settings()
            tasks.append(run_game_safely(
                game_num,
                is_random=True,
                r_cpu=r_cpu,
                r_settings=r_settings,
                r_name=f"Random #{i+1}",
            ))

        print(f"\n{'='*70}")
        print(f"Running {len(tasks)} simulations in parallel (Concurrency: 10)...")
        print(f"{'='*70}")

        await asyncio.gather(*tasks)

        # Print comprehensive summary
        print(f"\n{'='*70}")
        print("COMPREHENSIVE SIMULATION SUMMARY")
        print(f"{'='*70}")

        print("\n📊 OVERALL STATISTICS")
        print(f"  Total games run: {stats.games_run}")
        print(f"  Games completed: {stats.games_completed}")
        print(f"  Games errored: {stats.games_errored}")
        print(f"  Success rate: {stats.games_completed / max(1, stats.games_run) * 100:.1f}%")

        print("\n🎮 GAME OUTCOMES")
        print(f"  Sudden Deaths: {stats.sudden_deaths}")
        print(f"  Last Standing Wins: {stats.last_standing_wins}")
        print(f"  Bankruptcies: {stats.bankruptcies}")

        print("\n⏱️  TIMING")
        print(f"  Total turns: {stats.total_turns}")
        print(f"  Total rounds: {stats.total_rounds}")
        print(f"  Avg turns/game: {stats.total_turns / max(1, stats.games_completed):.1f}")

        print("\n🔧 FEATURES OBSERVED")
        print(f"  Doubles rolled: {stats.doubles_rolled}")
        print(f"  Jail visits: {stats.jail_visits}")
        print(f"  Glitch teleports: {stats.glitch_teleports}")
        print(f"  Buffs bought: {stats.buffs_bought}")
        print(f"  Stimulus checks: {stats.stimulus_checks}")

        print("\n🎯 PHASE 3 FEATURES")
        print(f"  DDOS buffs bought: {stats.ddos_buffs_bought}")
        print(f"  Tiles blocked (DDOS): {stats.ddos_tiles_blocked}")
        print(f"  PEEK buffs bought: {stats.peek_buffs_bought}")
        print(f"  Turn timeouts: {stats.turn_timeouts}")
        print(f"  Blocked tiles cleared: {stats.blocked_tiles_cleared}")
        print(f"  Trades proposed: {stats.trades_proposed}")
        print(f"  Trades accepted: {stats.trades_accepted}")

        print("\n🔨 UPGRADE FEATURES")
        print(f"  Properties upgraded: {stats.properties_upgraded}")
        print(f"    → Script Kiddie (L1): {stats.upgrade_to_script_kiddie}")
        print(f"    → 1337 Haxxor (L2): {stats.upgrade_to_1337_haxxor}")
        print(f"  CPU upgrades: {stats.cpu_upgrades}")
        print(f"  Properties downgraded: {stats.properties_downgraded}")

        print("\n📈 ACTION COVERAGE (actions/dispatch types hit across all games)")
        if stats.action_coverage_merged:
            for k, v in sorted(stats.action_coverage_merged.items()):
                print(f"  {k}: {v}")
            all_action_types = {"ROLL_DICE", "BUY_PROPERTY", "PASS_PROPERTY", "BID", "RESOLVE_AUCTION", "UPGRADE", "DOWNGRADE", "BUY_BUFF", "BLOCK_TILE", "PROPOSE_TRADE", "ACCEPT_TRADE", "DECLINE_TRADE", "CANCEL_TRADE", "END_TURN", "BUY_RELEASE", "ROLL_FOR_DOUBLES", "EVENT_CLONE_UPGRADE", "EVENT_FORCE_BUY", "EVENT_FREE_LANDING"}
            hit = set(stats.action_coverage_merged.keys()) & all_action_types
            missed = all_action_types - hit
            if missed:
                print(f"  NOT HIT: {', '.join(sorted(missed))}")
        else:
            print("  (no coverage data)")

        print("\n📋 CONFIGURATIONS TESTED")
        for config, count in stats.configs_tested.items():
            print(f"  ✓ {config}: {count} game(s)")

        if stats.errors:
            print(f"\n⚠️  ERRORS ({len(stats.errors)} total)")
            for error in stats.errors[:10]:
                print(f"  - {error}")

        print(f"\n{'='*70}")
        if stats.games_errored == 0:
            print("✅ ALL CONFIGURATIONS PASSED!")
            return_code = 0
        else:
            print(f"❌ {stats.games_errored} configurations failed")
            return_code = 1
        print(f"{'='*70}\n")

        return return_code

    finally:
        client.close()


if __name__ == "__main__":
    exit(asyncio.run(main()))
