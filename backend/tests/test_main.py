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
    async def test_startup_event(self):
        """Test startup event handler."""
        with patch("app.main._get_db_manager") as mock_get_manager:
            mock_manager = AsyncMock()
            mock_get_manager.return_value = mock_manager

            # Simulate startup
            from app.main import startup_event

            await startup_event()

            mock_manager.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_event(self):
        """Test shutdown event handler."""
        with patch("app.main._get_db_manager") as mock_get_manager:
            mock_manager = AsyncMock()
            mock_get_manager.return_value = mock_manager

            # Simulate shutdown
            from app.main import shutdown_event

            await shutdown_event()

            mock_manager.close.assert_called_once()

    def test_cors_middleware_configured(self):
        """Test that CORS middleware is configured."""
        # Check that middleware is added
        assert len(app.user_middleware) > 0
        # CORS middleware should be present - check by looking at middleware class names
        middleware_info = [str(middleware) for middleware in app.user_middleware]
        # CORS middleware will be in the middleware stack
        assert any("CORS" in str(mid) or "cors" in str(mid).lower() for mid in middleware_info)

    def test_api_router_included(self):
        """Test that API router is included."""
        # Check that routes are registered
        routes = [route.path for route in app.routes]
        assert any("/api/v1" in route for route in routes)
