"""Board generation service for creating game boards from player tiles."""
import math
import random
from typing import Tuple
from app.modules.sastadice.schemas import Tile, TileType


class BoardGenerationService:
    """Service for generating game boards with closed loop topology."""

    def calculate_dimensions(self, num_players: int) -> Tuple[int, int, int]:
        """
        Calculate board dimensions for a given number of players.

        Args:
            num_players: Number of players in the game

        Returns:
            Tuple of (width, height, padding_tiles_needed)
        """
        total_tiles = num_players * 5  # Each player submits 5 tiles

        # Solve: 4W - 4 = T → W = (T + 4) / 4
        # For a square perimeter: Perimeter = 4W - 4 (where W = side length)
        width = math.ceil((total_tiles + 4) / 4)

        # Ensure minimum 4x4 board (perimeter = 12)
        width = max(width, 4)

        actual_perimeter = 4 * width - 4
        padding_tiles = actual_perimeter - total_tiles

        return width, width, padding_tiles

    def generate_board(
        self, player_tiles: list[Tile], board_size: int, padding: int
    ) -> list[Tile]:
        """
        Generate a closed loop board from player tiles.

        Args:
            player_tiles: List of tiles submitted by players
            board_size: Size of the square board (width = height)
            padding: Number of neutral tiles to add for padding

        Returns:
            List of tiles positioned on the board perimeter
        """
        # Shuffle player tiles for random distribution
        shuffled_tiles = player_tiles.copy()
        random.shuffle(shuffled_tiles)

        # Create padding tiles
        padding_tiles = [
            Tile(
                type=TileType.NEUTRAL,
                name="Empty Space",
                effect_config={},
                id=f"neutral-{i}",
            )
            for i in range(padding)
        ]

        # Interleave padding tiles evenly
        all_tiles = shuffled_tiles + padding_tiles
        if padding > 0:
            interleaved = self._interleave_tiles(shuffled_tiles, padding_tiles)
        else:
            interleaved = shuffled_tiles

        # Map tiles to perimeter positions in clockwise order
        board = self._map_tiles_to_perimeter(interleaved, board_size)

        return board

    def _interleave_tiles(
        self, player_tiles: list[Tile], padding_tiles: list[Tile]
    ) -> list[Tile]:
        """Interleave padding tiles evenly among player tiles."""
        result = []
        player_idx = 0
        padding_idx = 0
        total_tiles = len(player_tiles) + len(padding_tiles)

        # Calculate spacing: insert padding every N tiles
        if len(padding_tiles) > 0:
            spacing = len(player_tiles) // len(padding_tiles)
        else:
            spacing = total_tiles

        for i in range(total_tiles):
            # Insert padding at calculated intervals
            if padding_idx < len(padding_tiles) and i > 0 and i % (spacing + 1) == 0:
                result.append(padding_tiles[padding_idx])
                padding_idx += 1
            elif player_idx < len(player_tiles):
                result.append(player_tiles[player_idx])
                player_idx += 1

        # Add any remaining tiles
        while player_idx < len(player_tiles):
            result.append(player_tiles[player_idx])
            player_idx += 1
        while padding_idx < len(padding_tiles):
            result.append(padding_tiles[padding_idx])
            padding_idx += 1

        return result

    def _map_tiles_to_perimeter(
        self, tiles: list[Tile], board_size: int
    ) -> list[Tile]:
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

        # Top row: (0,0) to (W-1, 0)
        for x in range(board_size):
            if position < len(tiles):
                tile = tiles[position].model_copy()
                tile.x = x
                tile.y = 0
                tile.position = position
                board.append(tile)
                position += 1

        # Right column: (W-1, 1) to (W-1, H-1)
        for y in range(1, board_size):
            if position < len(tiles):
                tile = tiles[position].model_copy()
                tile.x = board_size - 1
                tile.y = y
                tile.position = position
                board.append(tile)
                position += 1

        # Bottom row: (W-2, H-1) to (0, H-1)
        for x in range(board_size - 2, -1, -1):
            if position < len(tiles):
                tile = tiles[position].model_copy()
                tile.x = x
                tile.y = board_size - 1
                tile.position = position
                board.append(tile)
                position += 1

        # Left column: (0, H-2) to (0, 1)
        for y in range(board_size - 2, 0, -1):
            if position < len(tiles):
                tile = tiles[position].model_copy()
                tile.x = 0
                tile.y = y
                tile.position = position
                board.append(tile)
                position += 1

        return board

    def _is_on_perimeter(self, x: int, y: int, board_size: int) -> bool:
        """Check if coordinates are on the board perimeter."""
        return (
            x == 0
            or x == board_size - 1
            or y == 0
            or y == board_size - 1
        )
