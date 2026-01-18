#!/usr/bin/env python3
"""Generate detailed game logs with game structures and tile types for review."""
import sys
import random
import json
import duckdb
from pathlib import Path
from datetime import datetime

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.modules.sastadice.models import init_tables
from app.modules.sastadice.services.game_service import GameService
from app.modules.sastadice.schemas import TileType


def get_tile_type_distribution(board):
    """Get distribution of tile types on the board."""
    distribution = {}
    for tile in board:
        tile_type = tile.type.value if hasattr(tile.type, 'value') else str(tile.type)
        distribution[tile_type] = distribution.get(tile_type, 0) + 1
    return distribution


def get_board_structure(game):
    """Get detailed board structure information."""
    board_info = {
        "board_size": game.board_size,
        "total_tiles": len(game.board),
        "tile_types": get_tile_type_distribution(game.board),
        "tiles": []
    }
    
    # Sample tiles from different types
    seen_types = set()
    for tile in game.board:
        tile_type = tile.type.value if hasattr(tile.type, 'value') else str(tile.type)
        if tile_type not in seen_types or len(board_info["tiles"]) < 20:  # Include up to 20 tiles
            seen_types.add(tile_type)
            tile_info = {
                "id": tile.id,
                "name": tile.name,
                "type": tile_type,
                "position": tile.position,
                "coordinates": {"x": tile.x, "y": tile.y},
                "price": tile.price if hasattr(tile, 'price') else 0,
                "rent": tile.rent if hasattr(tile, 'rent') else 0,
                "owner_id": tile.owner_id if hasattr(tile, 'owner_id') else None,
            }
            board_info["tiles"].append(tile_info)
    
    return board_info


def simulate_and_log_game(service: GameService, game_num: int, cpu_count: int, output_dir: Path) -> dict:
    """Simulate a single game and generate detailed log."""
    log_data = {
        "game_number": game_num,
        "timestamp": datetime.now().isoformat(),
        "cpu_count": cpu_count,
        "game_id": None,
        "status": None,
        "turns_played": 0,
        "errors": [],
        "game_structure": {},
        "final_state": {},
        "turn_log": []
    }
    
    try:
        # Create game
        game = service.create_game(cpu_count=cpu_count)
        log_data["game_id"] = game.id
        
        # Capture initial game structure
        log_data["game_structure"] = {
            "game_id": game.id,
            "status": game.status.value if hasattr(game.status, 'value') else str(game.status),
            "board_size": game.board_size,
            "starting_cash": game.starting_cash,
            "go_bonus": game.go_bonus,
            "players": [
                {
                    "id": p.id,
                    "name": p.name,
                    "cash": p.cash,
                    "position": p.position,
                    "ready": p.ready if hasattr(p, 'ready') else False,
                }
                for p in game.players
            ],
            "board": get_board_structure(game)
        }
        
        # Start game
        game = service.start_game(game.id, force=True)
        
        # Capture board after start
        log_data["game_structure"]["board_after_start"] = get_board_structure(game)
        
        # Simulate game
        result = service.simulate_cpu_game(game.id, max_turns=200)
        
        # Get final game state
        final_game = service.get_game(game.id)
        
        log_data["status"] = result.get("status")
        log_data["turns_played"] = result.get("turns_played", 0)
        log_data["turn_log"] = result.get("turn_log", [])
        log_data["winner"] = result.get("winner")
        log_data["final_standings"] = result.get("final_standings", [])
        
        # Capture final game structure
        log_data["final_state"] = {
            "status": final_game.status.value if hasattr(final_game.status, 'value') else str(final_game.status),
            "board": get_board_structure(final_game),
            "players": [
                {
                    "id": p.id,
                    "name": p.name,
                    "cash": p.cash,
                    "position": p.position,
                    "properties": len(p.properties) if hasattr(p, 'properties') else 0,
                }
                for p in final_game.players
            ],
            "tile_ownership": {}
        }
        
        # Get tile ownership distribution
        owned_tiles = {}
        for tile in final_game.board:
            if hasattr(tile, 'owner_id') and tile.owner_id:
                owner_name = next((p.name for p in final_game.players if p.id == tile.owner_id), "Unknown")
                if owner_name not in owned_tiles:
                    owned_tiles[owner_name] = []
                owned_tiles[owner_name].append({
                    "name": tile.name,
                    "type": tile.type.value if hasattr(tile.type, 'value') else str(tile.type),
                    "position": tile.position
                })
        log_data["final_state"]["tile_ownership"] = owned_tiles
        
        # Check for errors
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
        
        log_data["errors"] = errors
        log_data["success"] = len(errors) == 0 and result.get("status") in ["ACTIVE", "FINISHED"]
        
        # Save log file
        log_file = output_dir / f"game_{game_num:02d}_log.json"
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2, default=str)
        
        print(f"✓ Game {game_num} completed and logged to {log_file.name}")
        print(f"  Status: {log_data['status']}")
        print(f"  Turns: {log_data['turns_played']}")
        print(f"  Tile types: {', '.join(log_data['game_structure']['board']['tile_types'].keys())}")
        if log_data.get("winner"):
            print(f"  Winner: {log_data['winner'].get('name', 'N/A')} (${log_data['winner'].get('cash', 0)})")
        
        return log_data
        
    except Exception as e:
        import traceback
        error_msg = f"Exception: {str(e)}"
        log_data["errors"] = [error_msg]
        log_data["success"] = False
        log_data["traceback"] = traceback.format_exc()
        
        # Save error log
        log_file = output_dir / f"game_{game_num:02d}_log.json"
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2, default=str)
        
        print(f"✗ Game {game_num} failed: {error_msg}")
        return log_data


def main():
    """Generate 10 detailed game logs."""
    print("="*60)
    print("SASTADICE GAME LOG GENERATOR")
    print("Generating 10 detailed game logs for review")
    print("="*60)
    
    # Create output directory
    output_dir = Path(__file__).parent.parent / "data" / "game_logs"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput directory: {output_dir}")
    
    conn = duckdb.connect(":memory:")
    cursor = conn.cursor()
    init_tables(cursor)
    
    try:
        service = GameService(cursor)
        
        results = []
        # Use different seeds for variety
        seeds = [42, 123, 456, 789, 101, 202, 303, 404, 505, 606]
        cpu_counts = [2, 3, 4, 2, 3, 4, 2, 3, 4, 2]  # Vary CPU counts
        
        for i in range(10):
            random.seed(seeds[i])
            cpu_count = cpu_counts[i]
            result = simulate_and_log_game(service, i + 1, cpu_count, output_dir)
            results.append(result)
        
        # Summary
        print(f"\n{'='*60}")
        print("GENERATION SUMMARY")
        print(f"{'='*60}")
        
        successful = sum(1 for r in results if r.get("success", False))
        total_turns = sum(r.get("turns_played", 0) for r in results)
        total_errors = sum(len(r.get("errors", [])) for r in results)
        
        # Collect all tile types seen
        all_tile_types = set()
        for result in results:
            if "game_structure" in result and "board" in result["game_structure"]:
                tile_types = result["game_structure"]["board"].get("tile_types", {})
                all_tile_types.update(tile_types.keys())
        
        print(f"\nGames generated: {len(results)}")
        print(f"Successful games: {successful}/{len(results)}")
        print(f"Total turns played: {total_turns}")
        print(f"Total errors: {total_errors}")
        print(f"Tile types observed: {', '.join(sorted(all_tile_types))}")
        print(f"\nLog files saved to: {output_dir}")
        
        if total_errors > 0:
            print(f"\n⚠️  Games with errors:")
            for i, result in enumerate(results, 1):
                if result.get("errors"):
                    print(f"  Game {i}: {len(result['errors'])} error(s)")
        
        print(f"\n{'='*60}")
        if successful == len(results) and total_errors == 0:
            print("✅ ALL GAMES GENERATED SUCCESSFULLY!")
        elif successful == len(results):
            print("⚠️  All games completed but some had errors")
        else:
            print("❌ Some games failed - check logs above")
        print(f"{'='*60}\n")
        
        return 0 if successful == len(results) and total_errors == 0 else 1
        
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    exit(main())
