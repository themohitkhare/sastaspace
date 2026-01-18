#!/usr/bin/env python3
"""Enhanced simulation script to test all SastaDice game configurations."""
import sys
import random
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorClient

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.modules.sastadice.services.game_service import GameService
from app.modules.sastadice.schemas import (
    TileType, GameSettings, WinCondition, ChaosLevel
)


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
        self.errors: List[str] = []
        
        # Feature tracking
        self.go_bonus_collected = 0
        self.properties_bought = 0
        self.jail_visits = 0
        self.glitch_teleports = 0
        self.market_visits = 0
        self.buffs_bought = 0
        self.doubles_rolled = 0
        self.stimulus_checks = 0
        
        # Config tracking
        self.configs_tested: Dict[str, int] = {}


# Define test configurations
TEST_CONFIGS = [
    # Standard configs
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
    # Last Standing (no round limit)
    {
        "name": "Last Standing (∞ rounds)",
        "players": 2,
        "settings": GameSettings(
            win_condition=WinCondition.LAST_STANDING,
            round_limit=0
        )
    },
    # Economy variations
    {
        "name": "Rich Start (2x cash)",
        "players": 4,
        "settings": GameSettings(starting_cash_multiplier=2.0)
    },
    {
        "name": "High Inflation (+$50/round)",
        "players": 3,
        "settings": GameSettings(go_inflation_per_round=50)
    },
    # Chaos variations
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
    # Jail variations
    {
        "name": "Strict Jail (3 turns)",
        "players": 3,
        "settings": GameSettings(jail_turns_max=3)
    },
    # Player count variations
    {
        "name": "2 Players",
        "players": 2,
        "settings": GameSettings(round_limit=20)
    },
    {
        "name": "5 Players",
        "players": 5,
        "settings": GameSettings()
    },
    # Feature toggles
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
]


async def simulate_single_game(
    service: GameService, 
    game_num: int, 
    cpu_count: int,
    settings: GameSettings,
    stats: SimulationStats,
    config_name: str,
    verbose: bool = True,
    max_turns: int = 500  # Higher for Last Standing
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
        # Create game with custom settings
        game = await service.create_game(cpu_count=cpu_count)
        
        # Apply settings (we need to update the game with settings)
        game.settings = settings
        game.max_rounds = settings.round_limit
        await service.repository.update(game)
        
        if verbose:
            print(f"✓ Game created: {game.id[:8]}...")
            print(f"  Players: {[p.name for p in game.players]}")
        
        # Start game
        if game.status.value == "LOBBY":
            game = await service.start_game(game.id, force=True)
        
        # Analyze board
        board_analysis = analyze_board(game)
        if verbose:
            print(f"  Board: {len(game.board)} tiles, {board_analysis['properties']} properties")
        
        # Run simulation with higher max for Last Standing
        effective_max = max_turns if settings.win_condition == WinCondition.LAST_STANDING else 300
        result = await service.simulate_cpu_game(game.id, max_turns=effective_max)
        
        # Collect statistics
        stats.games_completed += 1
        stats.total_turns += result.get("turns_played", 0)
        stats.total_rounds += result.get("rounds_played", 0)
        
        if result.get("rounds_played", 0) >= settings.round_limit and settings.round_limit > 0:
            stats.sudden_deaths += 1
        
        for p in result.get("final_standings", []):
            if p.get("bankrupt"):
                stats.bankruptcies += 1
        
        # Check for Last Standing wins
        if settings.win_condition == WinCondition.LAST_STANDING:
            active = [p for p in result.get("final_standings", []) if not p.get("bankrupt")]
            if len(active) <= 1:
                stats.last_standing_wins += 1
        
        # Analyze turn log
        for turn in result.get("turn_log", []):
            for action in turn.get("actions", []):
                action_result = action.get("result", "")
                if "DOUBLES" in action_result.upper():
                    stats.doubles_rolled += 1
                if "STIMULUS" in action_result.upper():
                    stats.stimulus_checks += 1
                if "GLITCH" in action_result.upper():
                    stats.glitch_teleports += 1
                if "JAIL" in action_result.upper() or "SERVER DOWNTIME" in action_result.upper():
                    stats.jail_visits += 1
                if "BUY_BUFF" in action.get("action", ""):
                    stats.buffs_bought += 1
        
        result["success"] = result.get("status") in ["ACTIVE", "FINISHED"]
        
        if verbose:
            win_type = "SUDDEN DEATH" if stats.sudden_deaths > 0 else "LAST STANDING" if stats.last_standing_wins > 0 else "?"
            print(f"\n✓ Game completed: {result['status']}")
            print(f"  Turns: {result['turns_played']} | Rounds: {result.get('rounds_played', 0)}")
            if result.get("winner"):
                print(f"  Winner: {result['winner'].get('name', 'N/A')} (${result['winner'].get('cash', 0)})")
        
        return result
        
    except Exception as e:
        stats.games_errored += 1
        stats.errors.append(f"[{config_name}] {str(e)}")
        
        if verbose:
            print(f"\n✗ Game failed: {str(e)}")
            import traceback
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


async def main():
    """Run comprehensive game simulation across all configurations."""
    print("="*70)
    print("SASTADICE COMPREHENSIVE CONFIGURATION TESTING")
    print(f"Testing {len(TEST_CONFIGS)} different game configurations")
    print("="*70)
    
    # Connect to MongoDB
    import os
    mongo_url = os.environ.get("MONGODB_URL", "mongodb://mongodb:27017")
    print(f"Connecting to: {mongo_url}")
    
    client = AsyncIOMotorClient(mongo_url)
    database = client.test_simulations
    
    try:
        service = GameService(database)
        stats = SimulationStats()
        
        game_num = 0
        
        # Run each configuration
        for config in TEST_CONFIGS:
            game_num += 1
            await simulate_single_game(
                service=service,
                game_num=game_num,
                cpu_count=config["players"],
                settings=config["settings"],
                stats=stats,
                config_name=config["name"],
                verbose=True
            )
        
        # Run additional random variations
        print(f"\n{'='*70}")
        print("Running additional random configuration tests...")
        print(f"{'='*70}")
        
        random.seed(42)
        for i in range(5):
            game_num += 1
            random_settings = GameSettings(
                win_condition=random.choice(list(WinCondition)),
                round_limit=random.choice([0, 15, 30, 50]),
                go_bonus_base=random.choice([150, 200, 250]),
                go_inflation_per_round=random.choice([10, 20, 30]),
                chaos_level=random.choice(list(ChaosLevel)),
            )
            await simulate_single_game(
                service=service,
                game_num=game_num,
                cpu_count=random.randint(2, 5),
                settings=random_settings,
                stats=stats,
                config_name=f"Random Config #{i+1}",
                verbose=True
            )
        
        # Print comprehensive summary
        print(f"\n{'='*70}")
        print("COMPREHENSIVE SIMULATION SUMMARY")
        print(f"{'='*70}")
        
        print(f"\n📊 OVERALL STATISTICS")
        print(f"  Total games run: {stats.games_run}")
        print(f"  Games completed: {stats.games_completed}")
        print(f"  Games errored: {stats.games_errored}")
        print(f"  Success rate: {stats.games_completed / max(1, stats.games_run) * 100:.1f}%")
        
        print(f"\n🎮 GAME OUTCOMES")
        print(f"  Sudden Deaths: {stats.sudden_deaths}")
        print(f"  Last Standing Wins: {stats.last_standing_wins}")
        print(f"  Bankruptcies: {stats.bankruptcies}")
        
        print(f"\n⏱️  TIMING")
        print(f"  Total turns: {stats.total_turns}")
        print(f"  Total rounds: {stats.total_rounds}")
        print(f"  Avg turns/game: {stats.total_turns / max(1, stats.games_completed):.1f}")
        
        print(f"\n🔧 FEATURES OBSERVED")
        print(f"  Doubles rolled: {stats.doubles_rolled}")
        print(f"  Jail visits: {stats.jail_visits}")
        print(f"  Glitch teleports: {stats.glitch_teleports}")
        print(f"  Buffs bought: {stats.buffs_bought}")
        print(f"  Stimulus checks: {stats.stimulus_checks}")
        
        print(f"\n📋 CONFIGURATIONS TESTED")
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
