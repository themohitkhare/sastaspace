"""Tests for SastaDice API endpoints."""
import pytest
from fastapi.testclient import TestClient
from contextlib import contextmanager
from app.main import app
from app.db.session import get_db
from app.modules.sastadice.schemas import TileType, TileCreate


class TestSastaDiceAPI:
    """Test suite for SastaDice API endpoints."""

    @pytest.fixture(autouse=True)
    def setup_test_db(self, db_cursor):
        """Override database dependency for all tests in this class."""
        def override_get_db():
            yield db_cursor
        app.dependency_overrides[get_db] = override_get_db
        yield
        app.dependency_overrides.clear()

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    def test_create_game(self, db_cursor, client):
        """Test creating a new game."""
        response = client.post("/api/v1/sastadice/games")
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["status"] == "LOBBY"

    def test_get_game(self, db_cursor, client):
        """Test getting a game by ID."""
        # Create game first
        create_response = client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

        # Get game
        response = client.get(f"/api/v1/sastadice/games/{game_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == game_id

    def test_get_nonexistent_game(self, client):
        """Test getting a non-existent game returns 404."""
        response = client.get("/api/v1/sastadice/games/nonexistent-id")
        assert response.status_code == 404

    def test_join_game(self, db_cursor, client):
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

    def test_join_game_invalid_tiles(self, db_cursor, client):
        """Test joining with invalid number of tiles returns 400."""
        create_response = client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

        # Try with wrong number of tiles
        tiles = [{"type": "PROPERTY", "name": "Property 1", "effect_config": {}}]
        response = client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Test Player", "tiles": tiles},
        )

        # Returns 400 Bad Request due to ValueError in service
        assert response.status_code == 400

    def test_start_game(self, db_cursor, client):
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

    def test_get_game_state(self, db_cursor, client):
        """Test getting game state with version."""
        # Create and start game
        create_response = client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

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
        client.post(f"/api/v1/sastadice/games/{game_id}/start")

        # Get game state
        response = client.get(f"/api/v1/sastadice/games/{game_id}/state")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "game" in data
        assert data["game"]["id"] == game_id

    def test_get_game_state_with_version(self, db_cursor, client):
        """Test getting game state with version parameter."""
        create_response = client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

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
        client.post(f"/api/v1/sastadice/games/{game_id}/start")

        # Get initial state
        response = client.get(f"/api/v1/sastadice/games/{game_id}/state")
        assert response.status_code == 200
        version = response.json()["version"]

        # Request with same version - should return 304
        response = client.get(f"/api/v1/sastadice/games/{game_id}/state?version={version}")
        assert response.status_code == 304

    def test_join_game_error_cases(self, db_cursor, client):
        """Test error cases for joining a game."""
        create_response = client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

        # Try to join non-existent game
        tiles = [
            {"type": "PROPERTY", "name": f"Property {i}", "effect_config": {}}
            for i in range(5)
        ]
        response = client.post(
            "/api/v1/sastadice/games/nonexistent/join",
            json={"name": "Test Player", "tiles": tiles},
        )
        assert response.status_code == 400

    def test_start_game_with_cpu_players(self, db_cursor, client):
        """Test starting a game with less than 2 players adds CPU players."""
        # Start game with no players - CPU players will be added
        create_response = client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

        # Add one player
        tiles = [
            {"type": "PROPERTY", "name": f"Property {i}", "effect_config": {}}
            for i in range(5)
        ]
        client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Player 1", "tiles": tiles},
        )

        # Start game - should add CPU player automatically
        response = client.post(f"/api/v1/sastadice/games/{game_id}/start")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ACTIVE"
        # Should have at least 2 players (1 human + 1 CPU)
        assert len(data["players"]) >= 2

    def test_perform_action_roll_dice(self, db_cursor, client):
        """Test performing roll dice action."""
        # Create and start game
        create_response = client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

        tiles = [
            {"type": "PROPERTY", "name": f"Property {i}", "effect_config": {}}
            for i in range(5)
        ]
        join_response = client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Player 1", "tiles": tiles},
        )
        player1_id = join_response.json()["id"]

        client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Player 2", "tiles": tiles},
        )
        client.post(f"/api/v1/sastadice/games/{game_id}/start")

        # Roll dice
        response = client.post(
            f"/api/v1/sastadice/games/{game_id}/action",
            params={"player_id": player1_id},
            json={"type": "ROLL_DICE", "payload": {}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    def test_perform_action_end_turn(self, db_cursor, client):
        """Test performing end turn action after rolling dice."""
        # Create and start game
        create_response = client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

        tiles = [
            {"type": "PROPERTY", "name": f"Property {i}", "effect_config": {}}
            for i in range(5)
        ]
        join_response1 = client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Player 1", "tiles": tiles},
        )
        player1_id = join_response1.json()["id"]

        join_response2 = client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Player 2", "tiles": tiles},
        )
        player2_id = join_response2.json()["id"]

        client.post(f"/api/v1/sastadice/games/{game_id}/start")

        # First roll dice to advance phase
        roll_response = client.post(
            f"/api/v1/sastadice/games/{game_id}/action",
            params={"player_id": player1_id},
            json={"type": "ROLL_DICE", "payload": {}},
        )
        assert roll_response.status_code == 200

        # Check game state to see if we need to pass on property
        state_response = client.get(f"/api/v1/sastadice/games/{game_id}/state")
        game_state = state_response.json()["game"]
        
        if game_state["turn_phase"] == "DECISION" and game_state.get("pending_decision"):
            # Pass on property
            pass_response = client.post(
                f"/api/v1/sastadice/games/{game_id}/action",
                params={"player_id": player1_id},
                json={"type": "PASS_PROPERTY", "payload": {}},
            )
            assert pass_response.status_code == 200

        # Now end turn
        response = client.post(
            f"/api/v1/sastadice/games/{game_id}/action",
            params={"player_id": player1_id},
            json={"type": "END_TURN", "payload": {}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_perform_action_buy_property(self, db_cursor, client):
        """Test performing buy property action requires proper phase."""
        # Create and start game
        create_response = client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

        tiles = [
            {"type": "PROPERTY", "name": f"Property {i}", "effect_config": {}}
            for i in range(5)
        ]
        join_response = client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Player 1", "tiles": tiles},
        )
        player1_id = join_response.json()["id"]

        client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Player 2", "tiles": tiles},
        )
        client.post(f"/api/v1/sastadice/games/{game_id}/start")

        # Try to buy property without rolling first - should fail
        response = client.post(
            f"/api/v1/sastadice/games/{game_id}/action",
            params={"player_id": player1_id},
            json={"type": "BUY_PROPERTY", "payload": {}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    def test_perform_action_error_cases(self, db_cursor, client):
        """Test error cases for perform action."""
        # Try action on non-existent game
        response = client.post(
            "/api/v1/sastadice/games/nonexistent/action",
            params={"player_id": "player1"},
            json={"type": "ROLL_DICE", "payload": {}},
        )
        assert response.status_code == 400

    def test_get_game_state_not_found(self, db_cursor, client):
        """Test getting game state for non-existent game."""
        response = client.get("/api/v1/sastadice/games/nonexistent-id/state")
        assert response.status_code == 404

    def test_turn_phase_in_game_state(self, db_cursor, client):
        """Test that turn_phase is included in game state."""
        create_response = client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

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
        client.post(f"/api/v1/sastadice/games/{game_id}/start")

        response = client.get(f"/api/v1/sastadice/games/{game_id}/state")
        assert response.status_code == 200
        data = response.json()
        assert "turn_phase" in data["game"]
        assert data["game"]["turn_phase"] == "PRE_ROLL"

    def test_dynamic_economy_in_game_state(self, db_cursor, client):
        """Test that dynamic economy fields are in game state."""
        create_response = client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

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
        client.post(f"/api/v1/sastadice/games/{game_id}/start")

        response = client.get(f"/api/v1/sastadice/games/{game_id}/state")
        assert response.status_code == 200
        data = response.json()["game"]
        
        # Verify economy fields
        assert "starting_cash" in data
        assert "go_bonus" in data
        assert data["starting_cash"] > 0
        assert data["go_bonus"] > 0
        
        # Verify players have cash
        for player in data["players"]:
            assert player["cash"] > 0

    def test_player_colors_assigned(self, db_cursor, client):
        """Test that players are assigned unique colors."""
        create_response = client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

        tiles = [
            {"type": "PROPERTY", "name": f"Property {i}", "effect_config": {}}
            for i in range(5)
        ]
        
        # Add multiple players
        join_response1 = client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Player 1", "tiles": tiles},
        )
        join_response2 = client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Player 2", "tiles": tiles},
        )

        # Verify colors are assigned and different
        player1 = join_response1.json()
        player2 = join_response2.json()
        
        assert "color" in player1
        assert "color" in player2
        assert player1["color"].startswith("#")
        assert player2["color"].startswith("#")
        assert player1["color"] != player2["color"]
