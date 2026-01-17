"""Board generation service for creating game boards from player tiles."""
import math
import random
import uuid
from typing import Tuple
from app.modules.sastadice.schemas import Tile, TileType, TileCreate


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
        total_tiles = num_players * 5
        width = math.ceil((total_tiles + 4) / 4)
        width = max(width, 4)

        actual_perimeter = 4 * width - 4
        padding_tiles = actual_perimeter - total_tiles

        return width, width, padding_tiles

    def generate_seeded_tiles_for_player(
        self, player_name: str, existing_players: list
    ) -> list[TileCreate]:
        """
        Generate 5 seeded tiles for a player joining the game.
        
        Args:
            player_name: Name of the player
            existing_players: List of existing players to avoid duplicates
            
        Returns:
            List of 5 TileCreate objects
        """
        existing_names = set()
        for player in existing_players:
            for tile in getattr(player, 'submitted_tiles', []):
                existing_names.add(tile.name.lower())
        
        seeded_tiles = [
            TileCreate(type=TileType.PROPERTY, name=f"{player_name}'s Property 1"),
            TileCreate(type=TileType.PROPERTY, name=f"{player_name}'s Property 2"),
            TileCreate(type=TileType.CHANCE, name=f"{player_name}'s Chance"),
            TileCreate(type=TileType.TAX, name=f"{player_name}'s Tax"),
            TileCreate(type=TileType.BUFF, name=f"{player_name}'s Buff"),
        ]
        
        return seeded_tiles

    def generate_additional_tiles(self, needed: int, player_tiles: list[Tile]) -> list[Tile]:
        """
        Generate additional tiles to supplement player tiles for a better game experience.
        
        Args:
            needed: Number of additional tiles to generate
            player_tiles: Existing player tiles to avoid duplicates
            
        Returns:
            List of generated tiles
        """
        generated_tiles = []
        player_names = {tile.name.lower() for tile in player_tiles}
        
        tile_templates = {
            TileType.PROPERTY: [
                "Park Avenue", "Broadway", "Fifth Avenue", "Times Square",
                "Central Park", "Wall Street", "Madison Avenue", "Lexington Avenue",
                "Park Place", "Marvin Gardens", "Ventnor Avenue", "Atlantic Avenue",
                "Pacific Avenue", "North Carolina", "Pennsylvania Avenue", "Illinois Avenue",
            ],
            TileType.CHANCE: [
                "Community Chest", "Lucky Draw", "Free Parking", "Go to Go",
                "Collect $200", "Advance to Boardwalk", "Bank Dividend", "Life Insurance Matures",
                "Holiday Fund", "Income Tax Refund", "Beauty Contest", "Stock Sale",
            ],
            TileType.TAX: [
                "Income Tax", "Luxury Tax", "Property Tax", "Sales Tax",
                "City Tax", "Federal Tax", "State Tax", "Inheritance Tax",
            ],
            TileType.TRAP: [
                "Go to Jail", "Speeding Fine", "Parking Violation", "Court Fee",
                "Medical Bill", "Repair Bill", "School Tax", "Hospital Fee",
            ],
            TileType.BUFF: [
                "Pass Go Bonus", "Birthday Gift", "Stock Dividend", "Insurance Payout",
                "Lottery Win", "Bonus Pay", "Tax Refund", "Cash Advance",
            ],
        }
        
        available_types = [t for t in TileType if t != TileType.NEUTRAL]
        
        for i in range(needed):
            tile_type = available_types[i % len(available_types)]
            templates = tile_templates.get(tile_type, [])
            
            name = None
            attempts = 0
            while name is None or name.lower() in player_names:
                if templates and attempts < len(templates):
                    name = f"{templates[attempts % len(templates)]} {i // len(templates) + 1}"
                else:
                    name = f"{tile_type.value} Tile {i + 1}"
                attempts += 1
                if attempts > 50:
                    name = f"{tile_type.value} {i + 1000}"
                    break
            
            generated_tiles.append(
                Tile(
                    type=tile_type,
                    name=name,
                    effect_config={},
                    id=str(uuid.uuid4()),
                )
            )
            player_names.add(name.lower())
        
        return generated_tiles

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
        shuffled_tiles = player_tiles.copy()
        random.shuffle(shuffled_tiles)

        padding_tiles = [
            Tile(
                type=TileType.NEUTRAL,
                name="Empty Space",
                effect_config={},
                id=f"neutral-{i}",
            )
            for i in range(padding)
        ]

        if padding > 0:
            interleaved = self._interleave_tiles(shuffled_tiles, padding_tiles)
        else:
            interleaved = shuffled_tiles

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

        if len(padding_tiles) > 0:
            spacing = len(player_tiles) // len(padding_tiles)
        else:
            spacing = total_tiles

        for i in range(total_tiles):
            if padding_idx < len(padding_tiles) and i > 0 and i % (spacing + 1) == 0:
                result.append(padding_tiles[padding_idx])
                padding_idx += 1
            elif player_idx < len(player_tiles):
                result.append(player_tiles[player_idx])
                player_idx += 1

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

    def _is_on_perimeter(self, x: int, y: int, board_size: int) -> bool:
        """Check if coordinates are on the board perimeter."""
        return (
            x == 0
            or x == board_size - 1
            or y == 0
            or y == board_size - 1
        )
