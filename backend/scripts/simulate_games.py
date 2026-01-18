#!/usr/bin/env python3
"""Script to simulate multiple games with CPU players to verify game stability."""
import sys
import random
import asyncio
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.modules.sastadice.services.game_service import GameService


async def simulate_single_game(service: GameService, game_num: int, cpu_count: int) -> dict:
    """Simulate a single game to completion."""
    print(f"\n{'='*60}")
    print(f"Game {game_num}: Starting with {cpu_count} CPU players")
    print(f"{'='*60}")
    
    try:
        game = await service.create_game(cpu_count=cpu_count)
        print(f"✓ Game created: {game.id}")
        print(f"  Players: {[p.name for p in game.players]}")
        
        print(f"✓ Starting simulation...")
        result = await service.simulate_cpu_game(game.id, max_turns=200)
        
        errors = []
        if result.get("status") not in ["ACTIVE", "FINISHED"]:
            errors.append(f"Unexpected game status: {result.get('status')}")
        
        if result.get("turns_played", 0) == 0:
            errors.append("No turns were played")
        
        turn_log = result.get("turn_log", [])
        for turn in turn_log:
            actions = turn.get("actions", [])
            for action in actions:
                if "failed" in str(action.get("result", "")).lower():
                    errors.append(f"Turn {turn.get('turn', '?')}: {action.get('action')} failed - {action.get('result')}")
        
        result["cpu_count"] = cpu_count
        result["errors"] = errors
        result["success"] = len(errors) == 0 and result.get("status") in ["ACTIVE", "FINISHED"]
        
        print(f"\n✓ Game {game_num} completed:")
        print(f"  Status: {result['status']}")
        print(f"  Turns played: {result['turns_played']}")
        if result.get("winner"):
            winner = result["winner"]
            print(f"  Winner: {winner.get('name', 'N/A')} (${winner.get('cash', 0)})")
        if errors:
            print(f"  ⚠️  Errors: {len(errors)}")
            for error in errors[:5]:  # Show first 5 errors
                print(f"    - {error}")
        else:
            print(f"  ✓ No errors")
        
        return result
        
    except Exception as e:
        print(f"\n✗ Game {game_num} failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "game_id": "N/A",
            "status": "ERROR",
            "turns_played": 0,
            "cpu_count": cpu_count,
            "errors": [f"Exception: {str(e)}"],
            "success": False
        }


async def main():
    """Run simulation of 10 games."""
    print("="*60)
    print("SASTADICE GAME SIMULATION")
    print("Simulating 10 games with 2-4 random CPU players each")
    print("="*60)
    
    # Connect to MongoDB (use localhost for scripts)
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    database = client.test_simulations
    
    try:
        service = GameService(database)
        
        results = []
        random.seed(42)  # For reproducibility
        
        for i in range(10):
            cpu_count = random.randint(2, 4)
            result = await simulate_single_game(service, i + 1, cpu_count)
            results.append(result)
        
        # Summary
        print(f"\n{'='*60}")
        print("SIMULATION SUMMARY")
        print(f"{'='*60}")
        
        successful = sum(1 for r in results if r.get("success", False))
        total_turns = sum(r.get("turns_played", 0) for r in results)
        total_errors = sum(len(r.get("errors", [])) for r in results)
        
        print(f"\nGames simulated: {len(results)}")
        print(f"Successful games: {successful}/{len(results)}")
        print(f"Total turns played: {total_turns}")
        print(f"Total errors: {total_errors}")
        
        if total_errors > 0:
            print(f"\n⚠️  Games with errors:")
            for i, result in enumerate(results, 1):
                if result.get("errors"):
                    print(f"  Game {i}: {len(result['errors'])} error(s)")
                    for error in result["errors"][:3]:
                        print(f"    - {error}")
        
        print(f"\n{'='*60}")
        if successful == len(results) and total_errors == 0:
            print("✅ ALL GAMES PASSED - No errors detected!")
        elif successful == len(results):
            print("⚠️  All games completed but some had errors")
        else:
            print("❌ Some games failed - check errors above")
        print(f"{'='*60}\n")
        
        return 0 if successful == len(results) and total_errors == 0 else 1
        
    finally:
        client.close()


if __name__ == "__main__":
    exit(asyncio.run(main()))
