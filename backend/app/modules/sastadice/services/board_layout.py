"""Board layout utilities - perimeter mapping and positioning."""

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.sastadice.schemas import Tile


class BoardLayout:
    """Handles board layout and perimeter mapping."""

    @staticmethod
    def calculate_dimensions(num_players: int) -> tuple[int, int, int]:
        """
        Calculate board dimensions for a given number of players.

        Args:
            num_players: Number of players in the game

        Returns:
            Tuple of (width, height, padding_tiles_needed)
        """
        total_tiles = num_players * 5
        width = math.ceil((total_tiles + 4) / 4)
        width = max(width, 4)

        actual_perimeter = 4 * width - 4
        padding_tiles = actual_perimeter - total_tiles

        return width, width, padding_tiles

    @staticmethod
    def map_tiles_to_perimeter(tiles: list["Tile"], board_size: int) -> list["Tile"]:
        """
        Map tiles to perimeter positions in clockwise order.

        Perimeter path:
        - Top row: (0,0) to (W-1, 0)
        - Right col: (W-1, 1) to (W-1, H-1)
        - Bottom row: (W-2, H-1) to (0, H-1)
        - Left col: (0, H-2) to (0, 1)
        """
        board = []
        position = 0

        for x in range(board_size):
            if position < len(tiles):
                tile = tiles[position].model_copy()
                tile.x = x
                tile.y = 0
                tile.position = position
                board.append(tile)
                position += 1

        for y in range(1, board_size):
            if position < len(tiles):
                tile = tiles[position].model_copy()
                tile.x = board_size - 1
                tile.y = y
                tile.position = position
                board.append(tile)
                position += 1

        for x in range(board_size - 2, -1, -1):
            if position < len(tiles):
                tile = tiles[position].model_copy()
                tile.x = x
                tile.y = board_size - 1
                tile.position = position
                board.append(tile)
                position += 1

        for y in range(board_size - 2, 0, -1):
            if position < len(tiles):
                tile = tiles[position].model_copy()
                tile.x = 0
                tile.y = y
                tile.position = position
                board.append(tile)
                position += 1

        return board

    @staticmethod
    def is_on_perimeter(x: int, y: int, board_size: int) -> bool:
        """Check if coordinates are on the board perimeter."""
        return x == 0 or x == board_size - 1 or y == 0 or y == board_size - 1

    @staticmethod
    def get_protected_positions(total_tiles: int) -> set[int]:
        """Returns positions reserved for corner tiles."""
        return {
            0,  # GO (0%)
            total_tiles // 4,  # The Glitch (25%)
            total_tiles // 2,  # Server Downtime (50%)
            (total_tiles * 3) // 4,  # Black Market (75%)
        }
