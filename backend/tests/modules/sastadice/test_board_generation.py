"""Tests for BoardGenerationService."""
import pytest
from app.modules.sastadice.services.board_generation_service import BoardGenerationService
from app.modules.sastadice.schemas import Tile, TileType


class TestBoardGenerationService:
    """Test suite for BoardGenerationService."""

    def test_calculate_dimensions_two_players(self):
        """Test board dimension calculation for 2 players."""
        service = BoardGenerationService()
        width, height, padding = service.calculate_dimensions(2)

        # 2 players * 5 tiles = 10 tiles
        # Perimeter = 4W - 4 = 12 (for W=4)
        # So we need 4x4 board with 2 padding tiles
        assert width == 4
        assert height == 4
        assert padding == 2

    def test_calculate_dimensions_three_players(self):
        """Test board dimension calculation for 3 players."""
        service = BoardGenerationService()
        width, height, padding = service.calculate_dimensions(3)

        # 3 players * 5 tiles = 15 tiles
        # Perimeter = 4W - 4 = 16 (for W=5)
        # So we need 5x5 board with 1 padding tile
        assert width == 5
        assert height == 5
        assert padding == 1

    def test_calculate_dimensions_four_players(self):
        """Test board dimension calculation for 4 players."""
        service = BoardGenerationService()
        width, height, padding = service.calculate_dimensions(4)

        # 4 players * 5 tiles = 20 tiles
        # Perimeter = 4W - 4 = 20 (for W=6)
        # So we need 6x6 board with 0 padding tiles
        assert width == 6
        assert height == 6
        assert padding == 0

    def test_calculate_dimensions_five_players(self):
        """Test board dimension calculation for 5 players."""
        service = BoardGenerationService()
        width, height, padding = service.calculate_dimensions(5)

        # 5 players * 5 tiles = 25 tiles
        # Perimeter = 4W - 4 = 28 (for W=8)
        # So we need 8x8 board with 3 padding tiles
        assert width == 8
        assert height == 8
        assert padding == 3

    def test_calculate_dimensions_minimum_board(self):
        """Test that minimum board size is 4x4."""
        service = BoardGenerationService()
        width, height, padding = service.calculate_dimensions(1)

        # Even for 1 player, minimum should be 4x4
        assert width >= 4
        assert height >= 4

    def test_generate_board_creates_closed_loop(self):
        """Test that generated board forms a closed loop."""
        service = BoardGenerationService()
        player_tiles = [
            Tile(type=TileType.PROPERTY, name=f"Property {i}", id=f"tile-{i}")
            for i in range(10)
        ]
        board_size = 4

        board = service.generate_board(player_tiles, board_size, padding=2)

        # Should have 12 tiles total (10 player + 2 padding)
        assert len(board) == 12

        # Check that all tiles are on the perimeter
        for tile in board:
            assert service._is_on_perimeter(tile.x, tile.y, board_size)

    def test_generate_board_tiles_have_valid_coordinates(self):
        """Test that all tiles have valid (x, y) coordinates."""
        service = BoardGenerationService()
        player_tiles = [
            Tile(type=TileType.PROPERTY, name=f"Property {i}", id=f"tile-{i}")
            for i in range(15)
        ]
        board_size = 5

        board = service.generate_board(player_tiles, board_size, padding=1)

        for tile in board:
            assert 0 <= tile.x < board_size
            assert 0 <= tile.y < board_size
            assert tile.position >= 0

    def test_generate_board_continuous_positions(self):
        """Test that tile positions are continuous (0 to N-1)."""
        service = BoardGenerationService()
        player_tiles = [
            Tile(type=TileType.PROPERTY, name=f"Property {i}", id=f"tile-{i}")
            for i in range(10)
        ]
        board_size = 4

        board = service.generate_board(player_tiles, board_size, padding=2)

        positions = sorted([tile.position for tile in board])
        assert positions == list(range(len(board)))

    def test_generate_board_padding_tiles_are_neutral(self):
        """Test that padding tiles are of type NEUTRAL."""
        service = BoardGenerationService()
        player_tiles = [
            Tile(type=TileType.PROPERTY, name=f"Property {i}", id=f"tile-{i}")
            for i in range(10)
        ]
        board_size = 4

        board = service.generate_board(player_tiles, board_size, padding=2)

        neutral_tiles = [tile for tile in board if tile.type == TileType.NEUTRAL]
        assert len(neutral_tiles) == 2
