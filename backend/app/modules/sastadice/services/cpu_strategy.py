"""CPU strategy - decision thresholds and logic."""
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.sastadice.schemas import Player, Tile


class CpuStrategy:
    """Decision-making logic for CPU players."""

    @staticmethod
    def should_buy_property(
        cpu_player: "Player", price: int, cash_buffer: int = 200
    ) -> bool:
        return cpu_player.cash >= price + cash_buffer

    @staticmethod
    def should_bid_in_auction(
        cpu_player: "Player", current_bid: int, property_price: int
    ) -> bool:
        max_bid = int(property_price * 0.8)
        return cpu_player.cash >= current_bid + 10 and current_bid < max_bid

    @staticmethod
    def should_upgrade_property(
        cpu_player: "Player", tile: "Tile", upgrade_cost: int, cash_buffer: int = 300
    ) -> bool:
        if tile.upgrade_level >= 2:
            return False
        return cpu_player.cash >= upgrade_cost + cash_buffer

    @staticmethod
    def calculate_upgrade_cost(tile: "Tile") -> int:
        return tile.price * (2 if tile.upgrade_level == 1 else 1)

    @staticmethod
    def should_accept_trade(
        cpu_player: "Player", offer_cash: int, request_cash: int, offer_props: list, request_props: list
    ) -> bool:
        net_cash = offer_cash - request_cash
        if net_cash > 50:
            return True
        if len(offer_props) > len(request_props) and net_cash >= 0:
            return True
        return random.random() < 0.3

    @staticmethod
    def should_propose_trade(cpu_player: "Player") -> bool:
        return random.random() < 0.1

    @staticmethod
    def get_bid_amount(
        cpu_player: "Player", current_bid: int, min_increment: int = 10
    ) -> int:
        max_bid = min(cpu_player.cash - 100, current_bid + min_increment)
        return max(current_bid + min_increment, max_bid)
