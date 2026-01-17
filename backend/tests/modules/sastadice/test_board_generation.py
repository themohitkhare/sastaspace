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

    def test_generate_board_no_padding(self):
        """Test board generation with no padding needed."""
        service = BoardGenerationService()
        player_tiles = [
            Tile(type=TileType.PROPERTY, name=f"Property {i}", id=f"tile-{i}")
            for i in range(20)  # 4 players * 5 tiles = 20
        ]
        board_size = 6

        board = service.generate_board(player_tiles, board_size, padding=0)

        # Should have 20 tiles total (no padding)
        assert len(board) == 20

    def test_interleave_no_padding_tiles(self):
        """Test interleaving when there are no padding tiles."""
        service = BoardGenerationService()
        player_tiles = [
            Tile(type=TileType.PROPERTY, name=f"Property {i}", id=f"tile-{i}")
            for i in range(10)
        ]
        padding_tiles = []

        result = service._interleave_tiles(player_tiles, padding_tiles)
        assert len(result) == 10
        assert all(tile.type == TileType.PROPERTY for tile in result)

    def test_interleave_remaining_tiles(self):
        """Test interleaving handles remaining tiles correctly."""
        service = BoardGenerationService()
        # Create scenario where some tiles remain after interleaving
        # Use numbers that will cause remaining tiles after main loop
        player_tiles = [
            Tile(type=TileType.PROPERTY, name=f"Property {i}", id=f"tile-{i}")
            for i in range(10)
        ]
        padding_tiles = [
            Tile(type=TileType.NEUTRAL, name="Padding", id=f"pad-{i}")
            for i in range(3)
        ]

        result = service._interleave_tiles(player_tiles, padding_tiles)
        # Should have all tiles (10 + 3 = 13)
        assert len(result) == 13
        # Should have all player tiles and padding tiles
        player_count = sum(1 for tile in result if tile.type == TileType.PROPERTY)
        padding_count = sum(1 for tile in result if tile.type == TileType.NEUTRAL)
        assert player_count == 10
        assert padding_count == 3
        # Verify all original tiles are in result
        result_ids = {tile.id for tile in result}
        assert all(tile.id in result_ids for tile in player_tiles)
        assert all(tile.id in result_ids for tile in padding_tiles)

    def test_interleave_remaining_padding_tiles(self):
        """Test interleaving handles remaining padding tiles correctly."""
        service = BoardGenerationService()
        # Create scenario where padding tiles remain after main loop
        player_tiles = [
            Tile(type=TileType.PROPERTY, name=f"Property {i}", id=f"tile-{i}")
            for i in range(5)
        ]
        padding_tiles = [
            Tile(type=TileType.NEUTRAL, name="Padding", id=f"pad-{i}")
            for i in range(8)  # More padding than can be evenly interleaved
        ]

        result = service._interleave_tiles(player_tiles, padding_tiles)
        # Should have all tiles
        assert len(result) == 13
        player_count = sum(1 for tile in result if tile.type == TileType.PROPERTY)
        padding_count = sum(1 for tile in result if tile.type == TileType.NEUTRAL)
        assert player_count == 5
        assert padding_count == 8
        # Verify all original tiles are in result
        result_ids = {tile.id for tile in result}
        assert all(tile.id in result_ids for tile in player_tiles)
        assert all(tile.id in result_ids for tile in padding_tiles)

    def test_interleave_remaining_player_tiles(self):
        """Test interleaving handles remaining player tiles correctly."""
        service = BoardGenerationService()
        # Create scenario where player tiles remain after main loop
        # With high spacing, padding is inserted infrequently, leaving player tiles unadded
        player_tiles = [
            Tile(type=TileType.PROPERTY, name=f"Property {i}", id=f"tile-{i}")
            for i in range(20)
        ]
        padding_tiles = [
            Tile(type=TileType.NEUTRAL, name="Padding", id=f"pad-{i}")
            for i in range(2)  # Few padding tiles with many players = high spacing
        ]

        result = service._interleave_tiles(player_tiles, padding_tiles)
        # Should have all tiles (20 + 2 = 22)
        assert len(result) == 22
        player_count = sum(1 for tile in result if tile.type == TileType.PROPERTY)
        padding_count = sum(1 for tile in result if tile.type == TileType.NEUTRAL)
        assert player_count == 20
        assert padding_count == 2
        # Verify all original tiles are in result
        result_ids = {tile.id for tile in result}
        assert all(tile.id in result_ids for tile in player_tiles)
        assert all(tile.id in result_ids for tile in padding_tiles)
