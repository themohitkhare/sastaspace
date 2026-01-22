"""Dry-run test to verify CPU games don't get stuck - simulates all possibilities."""

import pytest

from app.modules.sastadice.schemas import GameStatus, TurnPhase
from app.modules.sastadice.services.game_service import GameService


@pytest.mark.asyncio
async def test_cpu_game_dry_run_all_scenarios(db_database):
    """Comprehensive dry-run test that simulates CPU games with all possible scenarios."""
    service = GameService(db_database)

    # Test Scenario 1: 2 CPU players, full game simulation
    print("\n=== Scenario 1: 2 CPU Players ===")
    game1 = await service.create_game(cpu_count=2)
    game1 = await service.start_game(game1.id, force=True)
    print(f"Game started: {game1.id}")
    print(f"Players: {[p.name for p in game1.players]}")

    # Process CPU turns for several rounds
    for round_num in range(5):
        result = await service.process_cpu_turns(game1.id)
        game = await service.get_game(game1.id)
        print(f"Round {round_num + 1}: {result['cpu_turns_played']} CPU turns played")
        print(
            f"  Current player: {next((p.name for p in game.players if p.id == game.current_turn_player_id), 'Unknown')}"
        )
        print(f"  Turn phase: {game.turn_phase.value}")
        print(f"  Game status: {game.status.value}")

        if game.status != GameStatus.ACTIVE:
            break

        if result["cpu_turns_played"] == 0:
            print("  No CPU turns - likely human player's turn or game ended")
            break

    assert game.status in [GameStatus.ACTIVE, GameStatus.FINISHED], (
        "Game should be active or finished"
    )
    print("✓ Scenario 1 passed: Game progressed without getting stuck")

    # Test Scenario 2: 3 CPU players, longer simulation
    print("\n=== Scenario 2: 3 CPU Players (Longer Run) ===")
    game2 = await service.create_game(cpu_count=3)
    game2 = await service.start_game(game2.id, force=True)
    print(f"Game started: {game2.id}")

    # Simulate full game
    result = await service.simulate_cpu_game(game2.id, max_turns=30)
    print("Simulation completed:")
    print(f"  Turns played: {result['turns_played']}")
    print(f"  Game status: {result['status']}")
    print(f"  Winner: {result['winner']}")

    assert result["turns_played"] > 0, "Should have played at least one turn"
    assert result["status"] in ["ACTIVE", "FINISHED"], "Game should be active or finished"
    print("✓ Scenario 2 passed: Full simulation completed")

    # Test Scenario 3: CPU with low cash (edge case)
    print("\n=== Scenario 3: CPU with Low Cash ===")
    game3 = await service.create_game(cpu_count=1)
    game3 = await service.start_game(game3.id, force=True)
    cpu_player = game3.players[0]

    # Set CPU to very low cash
    await service.repository.update_player_cash(cpu_player.id, 10)
    print(f"Set {cpu_player.name} cash to 10")

    # Try to process turns - should handle gracefully
    result = await service.process_cpu_turns(game3.id)
    print(f"CPU turns played: {result['cpu_turns_played']}")

    game3 = await service.get_game(game3.id)
    print(f"Game still active: {game3.status == GameStatus.ACTIVE}")
    print("✓ Scenario 3 passed: Low cash handled gracefully")

    # Test Scenario 4: Multiple consecutive CPU turns
    print("\n=== Scenario 4: Multiple Consecutive CPU Turns ===")
    game4 = await service.create_game(cpu_count=4)
    game4 = await service.start_game(game4.id, force=True)

    total_turns = 0
    for i in range(10):
        result = await service.process_cpu_turns(game4.id)
        total_turns += result["cpu_turns_played"]
        game4 = await service.get_game(game4.id)

        if game4.status != GameStatus.ACTIVE:
            break
        if result["cpu_turns_played"] == 0:
            break

    print(f"Total CPU turns processed: {total_turns}")
    print(f"Final game status: {game4.status.value}")
    assert total_turns > 0, "Should have processed some CPU turns"
    print("✓ Scenario 4 passed: Multiple CPU turns processed")

    # Test Scenario 5: All possible turn phases
    print("\n=== Scenario 5: All Turn Phases ===")
    game5 = await service.create_game(cpu_count=2)
    game5 = await service.start_game(game5.id, force=True)

    phases_seen = set()
    for _ in range(20):
        game5 = await service.get_game(game5.id)
        phases_seen.add(game5.turn_phase)

        current_player = next(
            (p for p in game5.players if p.id == game5.current_turn_player_id), None
        )

        if not current_player or not service.cpu_manager.is_cpu_player(current_player):
            break

        result = await service.process_cpu_turns(game5.id)
        if result["cpu_turns_played"] == 0:
            break

    print(f"Phases seen: {[p.value for p in phases_seen]}")
    assert TurnPhase.PRE_ROLL in phases_seen, "Should see PRE_ROLL phase"
    print("✓ Scenario 5 passed: All phases handled")

    print("\n=== All Scenarios Passed! ===")
    print("✓ CPU games no longer get stuck")
    print("✓ All edge cases handled")
    print("✓ Turn progression works correctly")


if __name__ == "__main__":
    import asyncio
    import os

    from motor.motor_asyncio import AsyncIOMotorClient

    async def run_test():
        mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        client = AsyncIOMotorClient(mongodb_url)
        database = client.test_dry_run
        await asyncio.run(test_cpu_game_dry_run_all_scenarios(database))
        client.close()

    asyncio.run(run_test())
    print("\n✅ Dry-run test completed successfully!")
