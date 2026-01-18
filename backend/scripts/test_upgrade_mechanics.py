
import asyncio
import os
import sys
sys.path.append(os.getcwd())

try:
    from motor.motor_asyncio import AsyncIOMotorClient
    from app.modules.sastadice.services.game_service import GameService
    from app.modules.sastadice.schemas import ActionType, TileType, GameSettings
except ImportError:
    sys.path.append("/app")
    from motor.motor_asyncio import AsyncIOMotorClient
    from app.modules.sastadice.services.game_service import GameService
    from app.modules.sastadice.schemas import ActionType, TileType, GameSettings

async def test_upgrade_logic():
    client = AsyncIOMotorClient("mongodb://mongodb:27017")
    db = client["sastadice_db"]
    service = GameService(db)

    print("--- Testing Upgrade Logic ---")

    # 1. Setup Game
    game = await service.create_game()
    
    # Join Player
    p1 = await service.join_game(game.id, "UpgradeTester")
        
    await service.start_game(game.id, force=True)
    
    game = await service.get_game(game.id) # Refresh state
    
    # Get Player 1
    p1 = game.players[0]
    
    # Give P1 properties (Color: BROWN usually has 2 properties: ID 1 and 3? index 1 and 3)
    # Find any property set
    properties = [t for t in game.board if t.type == TileType.PROPERTY]
    if not properties:
        print("❌ No properties found in board")
        return
        
    target_color = properties[0].color
    target_set = [t for t in properties if t.color == target_color]
    
    print(f"Found {len(target_set)} properties with color {target_color}")
    
    # Assign to P1
    for t in target_set:
        t.owner_id = p1.id
        
    await service.repository.save_board(game.id, game.board)
    game = await service.get_game(game.id) # Refresh
    
    target_tile = target_set[0]
    print(f"Target Tile: {target_tile.name} (ID: {target_tile.id})")
    print(f"Price: {target_tile.price}")
    
    # Give Cash
    initial_cash = 2000
    p1.cash = initial_cash
    await service.repository.update_player_cash(p1.id, initial_cash)
    
    # Ensure it's P1 turn
    game.current_turn_player_id = p1.id
    await service.repository.update(game)
    
    # Test 1: Upgrade to Level 1
    print(f"Testing Upgrade {target_tile.name} to Level 1...")
    result = await service.perform_action(game.id, p1.id, ActionType.UPGRADE, {"tile_id": target_tile.id})
    if not result.success:
        print(f"❌ Upgrade Failed: {result.message}")
    else:
        print("✅ Upgrade to Level 1 Success")
    
    game = await service.get_game(game.id)
    tile = next(t for t in game.board if t.id == target_tile.id)
    p1 = next(p for p in game.players if p.id == p1.id)
    
    if tile.upgrade_level != 1:
        print(f"❌ Level mismatch. Expected 1, got {tile.upgrade_level}")
    
    msgs = [game.last_event_message]
    
    # Test 2: Upgrade to Level 2
    print(f"Testing Upgrade {target_tile.name} to Level 2...")
    result = await service.perform_action(game.id, p1.id, ActionType.UPGRADE, {"tile_id": target_tile.id})
    if result.success:
        print("✅ Upgrade to Level 2 Success")
    else:
        print(f"❌ Upgrade Failed: {result.message}")
        
    game = await service.get_game(game.id)
    tile = next(t for t in game.board if t.id == target_tile.id)
    p1 = next(p for p in game.players if p.id == p1.id)
    
    if tile.upgrade_level != 2:
        print(f"❌ Level mismatch. Expected 2, got {tile.upgrade_level}")

    # Test 3: Upgrade Max Level (Fail)
    print(f"Testing Upgrade beyond Max Level...")
    result = await service.perform_action(game.id, p1.id, ActionType.UPGRADE, {"tile_id": target_tile.id})
    if not result.success:
        print(f"✅ Correctly rejected: {result.message}")
    else:
        print("❌ Unexpected success for Max Level")

    # Calculation Verification: Cost
    # Level 1 cost = Price. Level 2 cost = Price * 2. Total = 3 * Price.
    total_cost = target_tile.price * 3
    expected_cash = initial_cash - total_cost
    if p1.cash == expected_cash:
        print(f"✅ Cash verification successful: {p1.cash}")
    else:
        print(f"❌ Cash mismatch. Expected {expected_cash}, got {p1.cash}")

if __name__ == "__main__":
    asyncio.run(test_upgrade_logic())
