"""Tests for main application."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


class TestMainApp:
    """Test main FastAPI application."""

    def test_root_endpoint(self):
        """Test root endpoint."""
        client = TestClient(app)
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert data["message"] == "Welcome to SastaSpace API"

    @pytest.mark.asyncio
    async def test_startup_initializes_db_and_redis(self):
        """Test that startup initializes MongoDB and Redis."""
        with (
            patch("app.main._get_db_manager") as mock_db,
            patch("app.main._get_redis_manager") as mock_redis,
        ):
            mock_db_manager = AsyncMock()
            mock_db.return_value = mock_db_manager
            mock_redis_manager = AsyncMock()
            mock_redis.return_value = mock_redis_manager

            # Trigger startup handlers via TestClient context
            with TestClient(app):
                pass

            mock_db_manager.initialize.assert_called()
            mock_redis_manager.initialize.assert_called()

    @pytest.mark.asyncio
    async def test_shutdown_closes_db_and_redis(self):
        """Test that shutdown closes MongoDB and Redis."""
        with (
            patch("app.main._get_db_manager") as mock_db,
            patch("app.main._get_redis_manager") as mock_redis,
        ):
            mock_db_manager = AsyncMock()
            mock_db.return_value = mock_db_manager
            mock_redis_manager = AsyncMock()
            mock_redis.return_value = mock_redis_manager

            with TestClient(app):
                pass

            mock_db_manager.close.assert_called()
            mock_redis_manager.close.assert_called()

    def test_cors_middleware_configured(self):
        """Test that CORS middleware is configured."""
        assert len(app.user_middleware) > 0
        middleware_info = [str(middleware) for middleware in app.user_middleware]
        assert any("CORS" in str(mid) or "cors" in str(mid).lower() for mid in middleware_info)

    def test_api_router_included(self):
        """Test that API router is included."""
        routes = [route.path for route in app.routes]
        assert any("/api/v1" in route for route in routes)
