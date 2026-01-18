
import asyncio
import sys
import os
sys.path.append(os.getcwd())

try:
    from motor.motor_asyncio import AsyncIOMotorClient
    from app.modules.sastadice.services.game_service import GameService
    from app.modules.sastadice.schemas import GameSettings
except ImportError:
    sys.path.append("/app")
    from motor.motor_asyncio import AsyncIOMotorClient
    from app.modules.sastadice.services.game_service import GameService
    from app.modules.sastadice.schemas import GameSettings

async def test_settings_persistence():
    print("--- Testing Settings Persistence ---")
    try:
        client = AsyncIOMotorClient("mongodb://mongodb:27017", serverSelectionTimeoutMS=2000)
        db = client["sastadice_db"]
        service = GameService(db)
        
        # 1. Create Game
        game = await service.create_game()
        
        # 2. Join Host
        host = await service.join_game(game.id, "HostPlayer")
        print(f"Game: {game.id}, Host: {host.name} ({host.id})")
        
        # Verify default
        if not game.settings.enable_auctions:
            print("⚠️ Default enable_auctions is False? Expected True.")
        
        # 3. Update Settings (Disable Auctions)
        new_settings = {"enable_auctions": False}
        print("Disabling Auctions...")
        result = await service.update_settings(game.id, host.id, new_settings)
        if not result.get("updated"):
            print(f"❌ Update Failed: {result}")
            return
            
        # Verify Update
        game = await service.get_game(game.id)
        if game.settings.enable_auctions is not False:
             print(f"❌ Immediate Check Failed. Value: {game.settings.enable_auctions}")
             return
        else:
             print("✅ Settings Updated in DB (Immediate Check)")

        # 4. Add CPUs (Simulate Launch flow)
        print("Adding 3 CPU players...")
        await service.add_cpu_players_to_game(game.id, 3)
        
        # 5. Fetch Game
        game = await service.get_game(game.id)
        print(f"Post-CPU Auctions: {game.settings.enable_auctions}")
        
        if game.settings.enable_auctions is False:
            print("✅ Settings Persisted after CPU Add")
        else:
            print("❌ Settings Reverted/Lost!")

    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_settings_persistence())
