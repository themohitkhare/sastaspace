"""Trade manager for player-to-player trading with validation."""
import time
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.sastadice.schemas import GameSession, Player, TradeOffer

from app.modules.sastadice.schemas import TradeOffer


class TradeManager:
    """Manages player-to-player trading with validation."""

    @staticmethod
    def create_trade_offer(
        game: "GameSession", initiator: "Player", payload: dict
    ) -> tuple[Optional["TradeOffer"], Optional[str]]:
        """Create a trade offer. Returns (offer, error_message)."""
        target_id = payload.get("target_id")
        if not target_id or target_id == initiator.id:
            return None, "Invalid trade target"

        target_player = next((p for p in game.players if p.id == target_id), None)
        if not target_player:
            return None, "Target player not found"

        offer_cash = int(payload.get("offer_cash", 0))
        req_cash = int(payload.get("req_cash", 0))
        offer_props = payload.get("offer_props", [])
        req_props = payload.get("req_props", [])

        if offer_cash < 0 or req_cash < 0:
            return None, "Negative cash invalid"

        if initiator.cash < offer_cash:
            return None, "Insufficient cash for offer"

        for pid in offer_props:
            tile = next((t for t in game.board if t.id == pid), None)
            if not tile or tile.owner_id != initiator.id:
                return None, f"You don't own property {pid}"

        for pid in req_props:
            tile = next((t for t in game.board if t.id == pid), None)
            if not tile or tile.owner_id != target_id:
                return None, f"Target doesn't own property {pid}"

        offer = TradeOffer(
            initiator_id=initiator.id,
            target_id=target_id,
            offering_cash=offer_cash,
            offering_properties=offer_props,
            requesting_cash=req_cash,
            requesting_properties=req_props,
            created_at=time.time(),
        )

        return offer, None

    @staticmethod
    def validate_trade_assets(
        game: "GameSession",
        offer: "TradeOffer",
        initiator: "Player",
        target: "Player",
    ) -> Optional[str]:
        """Validate that trade assets are still available. Returns error if invalid."""
        if initiator.cash < offer.offering_cash:
            return "Initiator cannot afford trade anymore"
        if target.cash < offer.requesting_cash:
            return "You cannot afford trade"

        for pid in offer.offering_properties:
            tile = next((t for t in game.board if t.id == pid), None)
            if not tile or tile.owner_id != initiator.id:
                return "Initiator lost offer properties"

        for pid in offer.requesting_properties:
            tile = next((t for t in game.board if t.id == pid), None)
            if not tile or tile.owner_id != target.id:
                return "You lost requested properties"

        return None

    @staticmethod
    def execute_trade_transfer(
        game: "GameSession",
        offer: "TradeOffer",
        initiator: "Player",
        target: "Player",
    ) -> dict:
        """Execute the trade transfer. Returns dict with cash and property changes."""
        initiator_new_cash = initiator.cash - offer.offering_cash + offer.requesting_cash
        target_new_cash = target.cash + offer.offering_cash - offer.requesting_cash

        property_transfers = {
            "initiator_to_target": offer.offering_properties,
            "target_to_initiator": offer.requesting_properties,
        }

        return {
            "initiator_cash": initiator_new_cash,
            "target_cash": target_new_cash,
            "property_transfers": property_transfers,
        }
