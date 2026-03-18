"""Tests for the 24-tile UGC board generator."""

from app.modules.sastadice.schemas import TileType
from app.modules.sastadice.services.board_generation_service import (
    BoardGenerationService,
    GameConfig,
)


class TestUgc24Board:
    """Test suite for the 24-tile UGC board path."""

    def test_ugc_24_board_counts_and_corners(self):
        """Board has correct tile counts and fixed corner positions."""
        service = BoardGenerationService()
        game_config = GameConfig(num_tiles=24, num_players=2)

        ugc_names = [f"UGC Property {i}" for i in range(14)]
        board = service.generate_ugc_24_board(ugc_names, game_config)

        assert len(board) == 24

        types = [t.type for t in board]
        assert types.count(TileType.GO) == 1
        assert types.count(TileType.TELEPORT) == 1
        assert types.count(TileType.JAIL) == 1
        assert types.count(TileType.MARKET) == 1
        assert types.count(TileType.CHANCE) == 6
        assert types.count(TileType.PROPERTY) == 14

        # Corner positions are fixed
        assert board[0].type == TileType.GO
        assert board[6].type == TileType.TELEPORT
        assert board[12].type == TileType.JAIL
        assert board[18].type == TileType.MARKET

    def test_ugc_24_board_chance_spacing(self):
        """No three CHANCE tiles appear consecutively around the loop."""
        service = BoardGenerationService()
        game_config = GameConfig(num_tiles=24, num_players=2)

        ugc_names = [f"UGC Property {i}" for i in range(14)]
        board = service.generate_ugc_24_board(ugc_names, game_config)

        types = [t.type for t in board]
        n = len(types)

        # Verify there is no run of 3 consecutive CHANCE tiles (circularly)
        for i in range(n):
            trio = [types[(i + k) % n] for k in range(3)]
            assert not all(t == TileType.CHANCE for t in trio)

    def test_ugc_24_board_property_names_and_fallback(self):
        """UGC names are used first, then fallback names to reach 14 properties."""
        service = BoardGenerationService()
        game_config = GameConfig(num_tiles=24, num_players=2)

        ugc_names = ["Alpha Hub", "Beta Bunker", "Gamma Garage"]
        board = service.generate_ugc_24_board(ugc_names, game_config)

        property_tiles = [t for t in board if t.type == TileType.PROPERTY]
        property_names = [t.name for t in property_tiles]

        assert len(property_tiles) == 14
        # First names come from UGC input
        assert property_names[0:3] == ugc_names
        # At least one property name should not be from the UGC list (fallback used)
        assert any(name not in ugc_names for name in property_names)
