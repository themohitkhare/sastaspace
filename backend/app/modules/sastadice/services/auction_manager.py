"""Auction manager for handling auction state machine with race-condition safety."""

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.sastadice.schemas import AuctionState, GameSession, Player, Tile

from app.modules.sastadice.schemas import AuctionState, TurnPhase


class AuctionManager:
    """Handles auction lifecycle, bid validation, and timer extension."""

    @staticmethod
    def start_auction(
        game: "GameSession", tile: "Tile", auction_duration: int = 30
    ) -> "AuctionState":
        """Start an auction for a property tile."""
        participants = [p.id for p in game.players if not p.is_bankrupt]

        auction_state = AuctionState(
            property_id=tile.id,
            highest_bid=0,
            highest_bidder_id=None,
            start_time=time.time(),
            end_time=time.time() + auction_duration,
            participants=participants,
            min_bid_increment=10,
        )

        game.turn_phase = TurnPhase.AUCTION
        game.auction_state = auction_state
        game.pending_decision = None
        game.last_event_message = f"🔨 Auction started for {tile.name}!"

        return auction_state

    @staticmethod
    def validate_bid(auction: "AuctionState", player: "Player", amount: int) -> str | None:
        """Validate a bid. Returns error message if invalid, None if valid."""
        if time.time() > auction.end_time:
            return "Auction has ended"

        min_bid = auction.highest_bid + auction.min_bid_increment
        if amount < min_bid:
            return f"Bid too low. Min: {min_bid}"

        if player.cash < amount:
            return "Insufficient funds"

        if player.id not in auction.participants:
            return "Not a participant"

        return None

    @staticmethod
    def place_bid(game: "GameSession", player_id: str, amount: int) -> tuple[bool, str]:
        """Place a bid in the auction. Returns (success, message)."""
        if game.turn_phase != TurnPhase.AUCTION or not game.auction_state:
            return False, "No active auction"

        player = next((p for p in game.players if p.id == player_id), None)
        if not player:
            return False, "Player not found"

        error = AuctionManager.validate_bid(game.auction_state, player, amount)
        if error:
            return False, error

        game.auction_state.highest_bid = amount
        game.auction_state.highest_bidder_id = player_id

        remaining = game.auction_state.end_time - time.time()
        if remaining < 5:
            game.auction_state.end_time = time.time() + 5
            game.last_event_message = f"🔨 {player.name} bid ${amount}! Timer extended!"
        else:
            game.last_event_message = f"🔨 {player.name} bid ${amount}!"

        return True, f"Bid accepted: ${amount}"

    @staticmethod
    def check_auction_timeout(auction: "AuctionState") -> bool:
        """Check if auction has timed out."""
        return time.time() > auction.end_time

    @staticmethod
    def extend_auction_timer(auction: "AuctionState", seconds: int) -> None:
        """Extend auction timer by specified seconds."""
        auction.end_time = time.time() + seconds

    @staticmethod
    def resolve_auction(game: "GameSession") -> tuple[bool, str, str | None, int, str | None]:
        """Resolve a finished auction. Returns (success, message, winner_id, amount, prop_id)."""
        if not game.auction_state:
            return False, "No auction state", None, 0, None

        state = game.auction_state
        winner_id = state.highest_bidder_id
        amount = state.highest_bid
        prop_id = state.property_id

        tile = next((t for t in game.board if t.id == prop_id), None)
        tile_name = tile.name if tile else "Property"

        if winner_id:
            winner = next((p for p in game.players if p.id == winner_id), None)
            if winner:
                game.last_event_message = f"🔨 SOLD! {tile_name} to {winner.name} for ${amount}!"
                game.auction_state = None
                game.turn_phase = TurnPhase.POST_TURN
                return True, f"Sold to {winner.name} for ${amount}", winner_id, amount, prop_id

        game.last_event_message = f"🔨 Auction ended. No bids for {tile_name}."
        game.auction_state = None
        game.turn_phase = TurnPhase.POST_TURN
        return True, "Auction ended with no bids", None, 0, prop_id
