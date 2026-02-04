"""Board generation service - backward compatibility wrapper."""

from typing import Any

from app.modules.sastadice.schemas import Tile, TileCreate
from app.modules.sastadice.services.board_generator import BoardGenerator, GameConfig
from app.modules.sastadice.services.board_layout import BoardLayout

__all__ = ["BoardGenerationService", "GameConfig"]


class BoardGenerationService:
    """Service for generating game boards - backward compatibility wrapper."""

    def __init__(self) -> None:
        """Initialize board generation service."""
        self.layout = BoardLayout()
        self.generator = BoardGenerator(self.layout)

    def calculate_dimensions(self, num_players: int) -> tuple[int, int, int]:
        """Calculate board dimensions for a given number of players."""
        return self.layout.calculate_dimensions(num_players)

    def generate_seeded_tiles_for_player(
        self, player_name: str, existing_players: list[Any]
    ) -> list[TileCreate]:
        """Generate 5 seeded tiles for a player joining the game."""
        return self.generator.generate_seeded_tiles_for_player(player_name, existing_players)

    def generate_additional_tiles(self, needed: int, player_tiles: list[Tile]) -> list[Tile]:
        """Generate additional tiles to supplement player tiles."""
        return self.generator.generate_additional_tiles(needed, player_tiles)

    def generate_board(
        self,
        player_tiles: list[Tile],
        board_size: int,
        padding: int,
        game_config: GameConfig | None = None,
    ) -> list[Tile]:
        """Generate a closed loop board from player tiles."""
        return self.generator.generate_board(player_tiles, board_size, padding, game_config)

    def _is_on_perimeter(self, x: int, y: int, board_size: int) -> bool:
        """Check if coordinates are on the board perimeter (backward compatibility)."""
        return self.layout.is_on_perimeter(x, y, board_size)

    def _interleave_tiles(self, player_tiles: list[Tile], padding_tiles: list[Tile]) -> list[Tile]:
        """Interleave padding tiles evenly among player tiles (backward compatibility)."""
        return self.generator._interleave_tiles(player_tiles, padding_tiles)
