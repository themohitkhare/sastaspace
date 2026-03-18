"""API endpoint tests for the Sudoku module.

These tests use FastAPI dependency overrides so no real database is needed.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.modules.sudoku.models import Difficulty


@pytest.fixture
def mock_db() -> MagicMock:
    return MagicMock()


@pytest.fixture
def client(mock_db: MagicMock) -> TestClient:  # type: ignore[type-arg]
    app.dependency_overrides[get_db] = lambda: mock_db
    yield TestClient(app, raise_server_exceptions=True)  # type: ignore[misc]
    app.dependency_overrides.clear()


class TestStartMatch:
    @patch("app.modules.sudoku.services.SudokuService.start_match")
    def test_creates_match(self, mock_start: AsyncMock, client: TestClient) -> None:
        mock_start.return_value = {
            "match_id": "abc123",
            "starting_board": [0] * 81,
            "grid_size": 9,
        }
        resp = client.post("/api/v1/sudoku/matches", json={"difficulty": "medium", "grid_size": 9})
        assert resp.status_code == 201
        data = resp.json()
        assert data["match_id"] == "abc123"
        assert data["grid_size"] == 9
        assert len(data["starting_board"]) == 81

    @patch("app.modules.sudoku.services.SudokuService.start_match")
    def test_creates_match_with_custom_board(
        self, mock_start: AsyncMock, client: TestClient
    ) -> None:
        custom_board = [0] * 81
        custom_board[0] = 5
        mock_start.return_value = {
            "match_id": "def456",
            "starting_board": custom_board,
            "grid_size": 9,
        }
        resp = client.post(
            "/api/v1/sudoku/matches",
            json={"difficulty": "medium", "grid_size": 9, "custom_board": custom_board},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["match_id"] == "def456"
        assert data["starting_board"][0] == 5
        mock_start.assert_called_once_with(Difficulty.MEDIUM, 9, custom_board)


class TestGetMatch:
    @patch("app.modules.sudoku.services.SudokuService.get_match")
    def test_returns_state(self, mock_get: AsyncMock, client: TestClient) -> None:
        mock_get.return_value = {
            "match_id": "abc123",
            "difficulty": "medium",
            "status": "in_progress",
            "starting_board": [0] * 81,
            "grid_size": 9,
            "player_board": [0] * 81,
            "ai": {
                "generation_count": 5,
                "fitness_score": 0.85,
                "heatmap_data": [0.0] * 81,
                "best_board": [0] * 81,
                "status": "in_progress",
            },
        }
        resp = client.get("/api/v1/sudoku/matches/abc123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ai"]["generation_count"] == 5

    @patch("app.modules.sudoku.services.SudokuService.get_match")
    def test_not_found(self, mock_get: AsyncMock, client: TestClient) -> None:
        mock_get.side_effect = ValueError("Match xxx not found")
        resp = client.get("/api/v1/sudoku/matches/xxx")
        assert resp.status_code == 404


class TestUpdateBoard:
    @patch("app.modules.sudoku.services.SudokuService.player_update_board")
    def test_ok(self, mock_update: AsyncMock, client: TestClient) -> None:
        mock_update.return_value = None
        resp = client.put("/api/v1/sudoku/matches/abc123/board", json={"board": [0] * 81})
        assert resp.status_code == 200


class TestClaimVictory:
    @patch("app.modules.sudoku.services.SudokuService.claim_victory")
    def test_valid(self, mock_claim: AsyncMock, client: TestClient) -> None:
        mock_claim.return_value = {"valid": True, "status": "player_won"}
        resp = client.post("/api/v1/sudoku/matches/abc123/claim-victory")
        assert resp.status_code == 200
        assert resp.json()["valid"] is True

    @patch("app.modules.sudoku.services.SudokuService.claim_victory")
    def test_invalid(self, mock_claim: AsyncMock, client: TestClient) -> None:
        mock_claim.return_value = {"valid": False, "status": "in_progress"}
        resp = client.post("/api/v1/sudoku/matches/abc123/claim-victory")
        assert resp.status_code == 200
        assert resp.json()["valid"] is False


class TestAiTick:
    @patch("app.modules.sudoku.services.SudokuService.ai_tick")
    def test_runs(self, mock_tick: AsyncMock, client: TestClient) -> None:
        mock_tick.return_value: dict[str, Any] = {
            "status": "in_progress",
            "fitness_score": 0.9,
            "generation_count": 1,
        }
        resp = client.post("/api/v1/sudoku/matches/abc123/ai-tick")
        assert resp.status_code == 200
        assert resp.json()["fitness_score"] == 0.9


class TestExtractBoard:
    @patch("app.modules.sudoku.router.extract_sudoku_board")
    def test_ok(self, mock_extract: MagicMock, client: TestClient) -> None:
        mock_extract.return_value = [0] * 81
        resp = client.post(
            "/api/v1/sudoku/extract-board",
            files={"file": ("test.png", b"fakeimage", "image/png")},
        )
        assert resp.status_code == 200
        assert len(resp.json()["board"]) == 81

    def test_not_image(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/sudoku/extract-board",
            files={"file": ("test.txt", b"faketext", "text/plain")},
        )
        assert resp.status_code == 400
