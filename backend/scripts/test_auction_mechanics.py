#!/usr/bin/env python3
"""Test script for Auction mechanics."""
import sys
import asyncio
import time
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.modules.sastadice.services.game_service import GameService
from app.modules.sastadice.schemas import (
    GameSettings, TurnPhase, ActionType, TileType, AuctionState
)

async def test_auction_flow():
    print("="*60)
    print("TESTING AUCTION MECHANICS")
    print("="*60)

    # Connect to DB
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.test_auctions
    service = GameService(db)
    
    try:
        # 1. Create Game (Need 3 players for full scenario)
        game = await service.create_game(cpu_count=3)
        p1 = game.players[0]
        p2 = game.players[1]
        p3 = game.players[2]
        
        print(f"Game created: {game.id}")
        
        # 2. Start Game (Generates Board)
        game = await service.start_game(game.id, force=True)
        print(f"Game started. Board size: {len(game.board)}")
        
        # 3. Setup Property
        prop = next(t for t in game.board if t.type == TileType.PROPERTY)
        
        # 3. Simulate PASS_PROPERTY triggering Auction
        # Need to fake pending decision
        from app.modules.sastadice.schemas import PendingDecision
        game.status = "ACTIVE"
        game.current_turn_player_id = p1.id
        game.turn_phase = TurnPhase.DECISION
        game.pending_decision = PendingDecision(type="BUY", tile_id=prop.id, price=prop.price)
        game.settings.enable_auctions = True
        await service.repository.update(game)
        
        print("-> Player 1 passing property...")
        res = await service.perform_action(game.id, p1.id, ActionType.PASS_PROPERTY, {})
        assert res.success
        assert "Auction started" in res.message
        
        game = await service.get_game(game.id)
        assert game.turn_phase == TurnPhase.AUCTION
        assert game.auction_state is not None
        assert game.auction_state.property_id == prop.id
        print("✓ Auction started successfully")
        
        # 4. Simulate Bid from P2
        print("-> Player 2 bidding...")
        res = await service.perform_action(game.id, p2.id, ActionType.BID, {"amount": 50}) # Assuming start 0
        assert res.success
        game = await service.get_game(game.id)
        assert game.auction_state.highest_bid == 50
        assert game.auction_state.highest_bidder_id == p2.id
        print("✓ Bid accepted")
        
        # 5. Simulate Snipe (Extension)
        # Force time to near end
        game.auction_state.end_time = time.time() + 2
        await service.repository.update(game)
        
        print("-> Player 3 Sniping...")
        res = await service.perform_action(game.id, p3.id, ActionType.BID, {"amount": 100})
        assert res.success
        
        game = await service.get_game(game.id)
        assert game.auction_state.end_time > time.time() + 4 # Should extend
        print(f"✓ Snipe detected. Expiry extended to: {game.auction_state.end_time}")
        
        # 6. Resolve Auction
        # Force expiry
        game.auction_state.end_time = time.time() - 1
        await service.repository.update(game)
        
        print("-> Resolving auction...")
        res = await service.perform_action(game.id, p1.id, ActionType.RESOLVE_AUCTION, {})
        assert res.success
        assert "SOLD" in res.message
        
        game = await service.get_game(game.id)
        assert game.turn_phase == TurnPhase.POST_TURN
        assert game.auction_state is None
        
        p3_updated = next(p for p in game.players if p.id == p3.id)
        assert prop.id in p3_updated.properties
        print("✓ Auction resolved. Property transferred.")
        
        print("\n✅ AUCTION TESTS PASSED")
        return 0

    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        client.close()

if __name__ == "__main__":
    sys.exit(asyncio.run(test_auction_flow()))
