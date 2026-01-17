"""Tests for SastaDice API endpoints."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.modules.sastadice.schemas import TileType, TileCreate

client = TestClient(app)


class TestSastaDiceAPI:
    """Test suite for SastaDice API endpoints."""

    def test_create_game(self, db_cursor):
        """Test creating a new game."""
        response = client.post("/api/v1/sastadice/games")
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["status"] == "LOBBY"

    def test_get_game(self, db_cursor):
        """Test getting a game by ID."""
        # Create game first
        create_response = client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

        # Get game
        response = client.get(f"/api/v1/sastadice/games/{game_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == game_id

    def test_get_nonexistent_game(self):
        """Test getting a non-existent game returns 404."""
        response = client.get("/api/v1/sastadice/games/nonexistent-id")
        assert response.status_code == 404

    def test_join_game(self, db_cursor):
        """Test joining a game."""
        # Create game
        create_response = client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

        # Join game
        tiles = [
            {"type": "PROPERTY", "name": f"Property {i}", "effect_config": {}}
            for i in range(5)
        ]
        join_response = client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Test Player", "tiles": tiles},
        )

        assert join_response.status_code == 201
        data = join_response.json()
        assert data["name"] == "Test Player"

    def test_join_game_invalid_tiles(self, db_cursor):
        """Test joining with invalid number of tiles."""
        create_response = client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

        # Try with wrong number of tiles
        tiles = [{"type": "PROPERTY", "name": "Property 1", "effect_config": {}}]
        response = client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Test Player", "tiles": tiles},
        )

        assert response.status_code == 422  # Validation error

    def test_start_game(self, db_cursor):
        """Test starting a game."""
        # Create game
        create_response = client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

        # Add 2 players
        tiles = [
            {"type": "PROPERTY", "name": f"Property {i}", "effect_config": {}}
            for i in range(5)
        ]
        client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Player 1", "tiles": tiles},
        )
        client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Player 2", "tiles": tiles},
        )

        # Start game
        response = client.post(f"/api/v1/sastadice/games/{game_id}/start")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ACTIVE"
        assert len(data["board"]) > 0
