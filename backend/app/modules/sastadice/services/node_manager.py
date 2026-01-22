"""Node manager for Server Node (railroad) rent calculation."""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.sastadice.schemas import GameSession, Player

from app.modules.sastadice.schemas import TileType


class NodeManager:
    """Handles Server Node (railroad) rent calculation."""

    @staticmethod
    def calculate_node_rent(owner: "Player", game: "GameSession") -> int:
        """
        Rent = $50 * 2^(n-1) where n = nodes owned.
        Applies rent_multiplier from game state (for Market Crash/Bull Market).

        Returns:
            1 node = $50, 2 = $100, 3 = $200, 4 = $400 (before multiplier)
        """
        nodes_owned = sum(
            1
            for t in game.board
            if t.type == TileType.NODE and t.owner_id == owner.id
        )
        if nodes_owned == 0:
            return 0

        base_rent = 50 * (2 ** (nodes_owned - 1))
        return int(base_rent * game.rent_multiplier)
