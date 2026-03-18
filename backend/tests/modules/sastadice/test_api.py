"""Tests for SastaDice API endpoints."""

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.main import app


async def ready_and_start_game(client, game_id, player_ids):
    """Helper to toggle ready for all players and start game."""
    for pid in player_ids:
        await client.post(f"/api/v1/sastadice/games/{game_id}/ready/{pid}")
    return await client.post(f"/api/v1/sastadice/games/{game_id}/start")


class TestSastaDiceAPI:
    """Test suite for SastaDice API endpoints."""

    @pytest.fixture(autouse=True)
    async def setup_test_db(self, db_database):
        """Override database dependency for all tests in this class."""

        async def override_get_db():
            yield db_database

        app.dependency_overrides[get_db] = override_get_db
        yield
        app.dependency_overrides.clear()

    @pytest.fixture
    async def client(self):
        """Create an async test client."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    async def test_create_game(self, db_database, client):
        """Test creating a new game."""
        response = await client.post("/api/v1/sastadice/games")
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["status"] == "LOBBY"

    async def test_get_game(self, db_database, client):
        """Test getting a game by ID."""
        create_response = await client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

        response = await client.get(f"/api/v1/sastadice/games/{game_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == game_id

    async def test_get_nonexistent_game(self, client):
        """Test getting a non-existent game returns 404."""
        response = await client.get("/api/v1/sastadice/games/nonexistent-id")
        assert response.status_code == 404

    async def test_join_game(self, db_database, client):
        """Test joining a game."""
        create_response = await client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

        tiles = [
            {"type": "PROPERTY", "name": f"Property {i}", "effect_config": {}} for i in range(5)
        ]
        join_response = await client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Test Player", "tiles": tiles},
        )

        assert join_response.status_code == 201
        data = join_response.json()
        assert data["name"] == "Test Player"

    async def test_join_game_invalid_tiles(self, db_database, client):
        """Test joining with invalid number of tiles returns 400."""
        create_response = await client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

        # Try with wrong number of tiles
        tiles = [{"type": "PROPERTY", "name": "Property 1", "effect_config": {}}]
        response = await client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Test Player", "tiles": tiles},
        )

        # Returns 400 Bad Request due to ValueError in service
        assert response.status_code == 400

    async def test_start_game(self, db_database, client):
        """Test starting a game (force=True endpoint bypasses ready check)."""
        create_response = await client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

        tiles = [
            {"type": "PROPERTY", "name": f"Property {i}", "effect_config": {}} for i in range(5)
        ]
        await client.post(
            f"/api/v1/sastadice/games/{game_id}/join", json={"name": "Player 1", "tiles": tiles}
        )
        await client.post(
            f"/api/v1/sastadice/games/{game_id}/join", json={"name": "Player 2", "tiles": tiles}
        )

        response = await client.post(f"/api/v1/sastadice/games/{game_id}/start")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ACTIVE"
        assert len(data["board"]) > 0

    async def test_get_game_state(self, db_database, client):
        """Test getting game state with version."""
        create_response = await client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

        tiles = [
            {"type": "PROPERTY", "name": f"Property {i}", "effect_config": {}} for i in range(5)
        ]
        await client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Player 1", "tiles": tiles},
        )
        await client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Player 2", "tiles": tiles},
        )
        await client.post(f"/api/v1/sastadice/games/{game_id}/start")

        response = await client.get(f"/api/v1/sastadice/games/{game_id}/state")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "game" in data
        assert data["game"]["id"] == game_id

    async def test_get_game_state_with_version(self, db_database, client):
        """Test getting game state with version parameter."""
        create_response = await client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

        tiles = [
            {"type": "PROPERTY", "name": f"Property {i}", "effect_config": {}} for i in range(5)
        ]
        await client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Player 1", "tiles": tiles},
        )
        await client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Player 2", "tiles": tiles},
        )
        await client.post(f"/api/v1/sastadice/games/{game_id}/start")

        response = await client.get(f"/api/v1/sastadice/games/{game_id}/state")
        assert response.status_code == 200
        version = response.json()["version"]

        # Request with same version - should return 304
        response = await client.get(f"/api/v1/sastadice/games/{game_id}/state?version={version}")
        assert response.status_code == 304

    async def test_join_game_error_cases(self, db_database, client):
        """Test error cases for joining a game."""
        create_response = await client.post("/api/v1/sastadice/games")
        create_response.json()["id"]

        # Try to join non-existent game
        tiles = [
            {"type": "PROPERTY", "name": f"Property {i}", "effect_config": {}} for i in range(5)
        ]
        response = await client.post(
            "/api/v1/sastadice/games/nonexistent/join",
            json={"name": "Test Player", "tiles": tiles},
        )
        assert response.status_code == 400

    async def test_start_game_with_cpu_players(self, db_database, client):
        """Test starting a game with less than 2 players adds CPU players."""
        create_response = await client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

        tiles = [
            {"type": "PROPERTY", "name": f"Property {i}", "effect_config": {}} for i in range(5)
        ]
        await client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Player 1", "tiles": tiles},
        )

        response = await client.post(f"/api/v1/sastadice/games/{game_id}/start")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ACTIVE"
        # Should have at least 2 players (1 human + 1 CPU)
        assert len(data["players"]) >= 2

    async def test_perform_action_roll_dice(self, db_database, client):
        """Test performing roll dice action."""
        create_response = await client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

        tiles = [
            {"type": "PROPERTY", "name": f"Property {i}", "effect_config": {}} for i in range(5)
        ]
        join_response = await client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Player 1", "tiles": tiles},
        )
        player1_id = join_response.json()["id"]

        await client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Player 2", "tiles": tiles},
        )
        await client.post(f"/api/v1/sastadice/games/{game_id}/start")

        # Roll dice
        response = await client.post(
            f"/api/v1/sastadice/games/{game_id}/action",
            params={"player_id": player1_id},
            json={"type": "ROLL_DICE", "payload": {}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    async def test_perform_action_end_turn(self, db_database, client):
        """Test performing end turn action after rolling dice."""
        # Create and start game
        create_response = await client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

        tiles = [
            {"type": "PROPERTY", "name": f"Property {i}", "effect_config": {}} for i in range(5)
        ]
        join_response1 = await client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Player 1", "tiles": tiles},
        )
        player1_id = join_response1.json()["id"]

        join_response2 = await client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Player 2", "tiles": tiles},
        )
        join_response2.json()["id"]

        await client.post(f"/api/v1/sastadice/games/{game_id}/start")

        # First roll dice to advance phase
        with patch(
            "app.modules.sastadice.services.movement_handler.random.randint", side_effect=[1, 2]
        ):
            roll_response = await client.post(
                f"/api/v1/sastadice/games/{game_id}/action",
                params={"player_id": player1_id},
                json={"type": "ROLL_DICE", "payload": {}},
            )
        assert roll_response.status_code == 200

        state_response = await client.get(f"/api/v1/sastadice/games/{game_id}/state")
        game_state = state_response.json()["game"]

        if game_state["turn_phase"] == "DECISION" and game_state.get("pending_decision"):
            pass_response = await client.post(
                f"/api/v1/sastadice/games/{game_id}/action",
                params={"player_id": player1_id},
                json={"type": "BUY_PROPERTY", "payload": {}},
            )
            assert pass_response.status_code == 200

        # Now end turn
        response = await client.post(
            f"/api/v1/sastadice/games/{game_id}/action",
            params={"player_id": player1_id},
            json={"type": "END_TURN", "payload": {}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_trade_actions_do_not_reset_turn_timer(self, db_database, client):
        """Trade-related actions must not pause or reset the turn timer."""
        # Create and start game
        create_response = await client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

        tiles = [
            {"type": "PROPERTY", "name": f"Property {i}", "effect_config": {}} for i in range(5)
        ]
        join_response1 = await client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Player 1", "tiles": tiles},
        )
        player1_id = join_response1.json()["id"]

        join_response2 = await client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Player 2", "tiles": tiles},
        )
        player2_id = join_response2.json()["id"]

        start_response = await client.post(f"/api/v1/sastadice/games/{game_id}/start")
        assert start_response.status_code == 200

        # Fetch initial state and record turn_start_time
        state_response = await client.get(f"/api/v1/sastadice/games/{game_id}/state")
        initial_state = state_response.json()["game"]
        initial_turn_start_time = initial_state["turn_start_time"]

        # Propose a trade from current turn player to the other player
        current_turn_player_id = initial_state["current_turn_player_id"]
        target_id = player2_id if current_turn_player_id == player1_id else player1_id
        trade_payload = {
            "target_id": target_id,
            "offer_cash": 10,
            "req_cash": 0,
            "offer_props": [],
            "req_props": [],
        }
        trade_response = await client.post(
            f"/api/v1/sastadice/games/{game_id}/action",
            params={"player_id": current_turn_player_id},
            json={"type": "PROPOSE_TRADE", "payload": trade_payload},
        )
        assert trade_response.status_code == 200

        # Turn start time should be unchanged after trade
        updated_state_response = await client.get(f"/api/v1/sastadice/games/{game_id}/state")
        updated_state = updated_state_response.json()["game"]
        assert updated_state["turn_start_time"] == initial_turn_start_time

    async def test_perform_action_buy_property(self, db_database, client):
        """Test performing buy property action requires proper phase."""
        create_response = await client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

        tiles = [
            {"type": "PROPERTY", "name": f"Property {i}", "effect_config": {}} for i in range(5)
        ]
        join_response = await client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Player 1", "tiles": tiles},
        )
        player1_id = join_response.json()["id"]

        await client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Player 2", "tiles": tiles},
        )
        await client.post(f"/api/v1/sastadice/games/{game_id}/start")

        response = await client.post(
            f"/api/v1/sastadice/games/{game_id}/action",
            params={"player_id": player1_id},
            json={"type": "BUY_PROPERTY", "payload": {}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    async def test_perform_action_error_cases(self, db_database, client):
        """Test error cases for perform action."""
        # Try action on non-existent game
        response = await client.post(
            "/api/v1/sastadice/games/nonexistent/action",
            params={"player_id": "player1"},
            json={"type": "ROLL_DICE", "payload": {}},
        )
        assert response.status_code == 400

    async def test_get_game_state_not_found(self, db_database, client):
        """Test getting game state for non-existent game."""
        response = await client.get("/api/v1/sastadice/games/nonexistent-id/state")
        assert response.status_code == 404

    async def test_turn_phase_in_game_state(self, db_database, client):
        """Test that turn_phase is included in game state."""
        create_response = await client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

        tiles = [
            {"type": "PROPERTY", "name": f"Property {i}", "effect_config": {}} for i in range(5)
        ]
        await client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Player 1", "tiles": tiles},
        )
        await client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Player 2", "tiles": tiles},
        )
        await client.post(f"/api/v1/sastadice/games/{game_id}/start")

        response = await client.get(f"/api/v1/sastadice/games/{game_id}/state")
        assert response.status_code == 200
        data = response.json()
        assert "turn_phase" in data["game"]
        assert data["game"]["turn_phase"] == "PRE_ROLL"

    async def test_timeout_cancels_trades_and_auto_advances(self, db_database, client, monkeypatch):
        """When a turn times out, all active trades are cancelled and the turn auto-advances."""
        create_response = await client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

        tiles = [
            {"type": "PROPERTY", "name": f"Property {i}", "effect_config": {}} for i in range(5)
        ]
        join_response1 = await client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Player 1", "tiles": tiles},
        )
        player1_id = join_response1.json()["id"]

        join_response2 = await client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Player 2", "tiles": tiles},
        )
        player2_id = join_response2.json()["id"]

        start_response = await client.post(f"/api/v1/sastadice/games/{game_id}/start")
        assert start_response.status_code == 200
        started_state = start_response.json()

        # Ensure we are in PRE_ROLL with a running timer
        assert started_state["turn_phase"] == "PRE_ROLL"
        initial_turn_start_time = started_state["turn_start_time"]
        current_turn_player_id = started_state["current_turn_player_id"]

        # Create an active trade offer
        target_id = player2_id if current_turn_player_id == player1_id else player1_id
        trade_payload = {
            "target_id": target_id,
            "offer_cash": 10,
            "req_cash": 0,
            "offer_props": [],
            "req_props": [],
        }
        trade_response = await client.post(
            f"/api/v1/sastadice/games/{game_id}/action",
            params={"player_id": current_turn_player_id},
            json={"type": "PROPOSE_TRADE", "payload": trade_payload},
        )
        assert trade_response.status_code == 200

        # Confirm trade exists
        state_response = await client.get(f"/api/v1/sastadice/games/{game_id}/state")
        state = state_response.json()["game"]

        # Force timeout by advancing time beyond turn_timer_seconds
        from app.modules.sastadice.services import game_orchestrator as go_module

        timeout_seconds = state["settings"]["turn_timer_seconds"]
        fake_now = initial_turn_start_time + timeout_seconds + 1
        monkeypatch.setattr(go_module.time, "time", lambda: fake_now)

        # Hitting state endpoint will trigger check_timeout
        timeout_state_response = await client.get(f"/api/v1/sastadice/games/{game_id}/state")
        timeout_state = timeout_state_response.json()["game"]

        # All trades should be cleared
        assert timeout_state["active_trade_offers"] == []

        # And the game should have auto-advanced according to existing movement rules:
        # PRE_ROLL -> ROLL_DICE, DECISION -> PASS_PROPERTY, POST_TURN -> END_TURN
        # We only assert that either the turn_phase or current_turn_player_id changed.
        assert (
            timeout_state["turn_phase"] != started_state["turn_phase"]
            or timeout_state["current_turn_player_id"] != started_state["current_turn_player_id"]
        )

    async def test_dynamic_economy_in_game_state(self, db_database, client):
        """Test that dynamic economy fields are in game state."""
        create_response = await client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

        tiles = [
            {"type": "PROPERTY", "name": f"Property {i}", "effect_config": {}} for i in range(5)
        ]
        await client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Player 1", "tiles": tiles},
        )
        await client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Player 2", "tiles": tiles},
        )
        await client.post(f"/api/v1/sastadice/games/{game_id}/start")

        response = await client.get(f"/api/v1/sastadice/games/{game_id}/state")
        assert response.status_code == 200
        data = response.json()["game"]

        assert "starting_cash" in data
        assert "go_bonus" in data
        assert data["starting_cash"] > 0
        assert data["go_bonus"] > 0

        for player in data["players"]:
            assert player["cash"] > 0

    async def test_player_colors_assigned(self, db_database, client):
        """Test that players get assigned different colors."""
        tiles = [
            {"type": "PROPERTY", "name": f"Property {i}", "effect_config": {}} for i in range(5)
        ]
        create_response = await client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

        player1_response = await client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Player 1", "tiles": tiles},
        )
        player2_response = await client.post(
            f"/api/v1/sastadice/games/{game_id}/join",
            json={"name": "Player 2", "tiles": tiles},
        )

        assert player1_response.status_code == 201
        assert player2_response.status_code == 201
        player1 = player1_response.json()
        player2 = player2_response.json()

        assert player1["color"] != player2["color"]

    async def test_toggle_ready_error(self, db_database, client):
        """Test toggle_ready endpoint error handling."""
        create_response = await client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

        response = await client.post(f"/api/v1/sastadice/games/{game_id}/ready/invalid_player_id")
        assert response.status_code == 400

    async def test_kick_player_error(self, db_database, client):
        """Test kick_player endpoint error handling."""
        create_response = await client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

        response = await client.delete(
            f"/api/v1/sastadice/games/{game_id}/players/invalid_player_id",
            params={"host_id": "invalid_host"},
        )
        assert response.status_code == 400

    async def test_update_settings_error(self, db_database, client):
        """Test update_settings endpoint error handling."""
        create_response = await client.post("/api/v1/sastadice/games")
        game_id = create_response.json()["id"]

        response = await client.patch(
            f"/api/v1/sastadice/games/{game_id}/settings", json={"settings": {"round_limit": 20}}
        )
        assert response.status_code == 400

        response = await client.patch(
            f"/api/v1/sastadice/games/{game_id}/settings",
            json={"host_id": 123, "settings": {"round_limit": 20}},
        )
        assert response.status_code == 400

    async def test_start_game_error(self, db_database, client):
        """Test start_game endpoint error handling."""
        response = await client.post("/api/v1/sastadice/games/invalid_game_id/start")
        assert response.status_code == 400

    async def test_simulate_game_error(self, db_database, client):
        """Test simulate_game endpoint error handling."""
        # Try to simulate non-existent game
        response = await client.post("/api/v1/sastadice/games/invalid_game_id/simulate")
        assert response.status_code == 400

    async def test_process_cpu_turns_error(self, db_database, client):
        """Test process_cpu_turns endpoint error handling."""
        # Try to process CPU turns for non-existent game
        response = await client.post("/api/v1/sastadice/games/invalid_game_id/cpu-turn")
        assert response.status_code == 400
