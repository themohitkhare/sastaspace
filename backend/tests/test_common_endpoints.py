"""Tests for common API endpoints."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app


class TestHealthCheck:
    """Test health check endpoint."""

    def test_health_check_success(self):
        """Test health check when database is connected."""
        mock_db = AsyncMock()
        mock_db.command = AsyncMock(return_value={"ok": 1})
        
        # Patch the dependency
        async def override_get_db():
            yield mock_db
        
        app.dependency_overrides = {}
        from app.db.session import get_db
        app.dependency_overrides[get_db] = override_get_db
        
        try:
            client = TestClient(app)
            response = client.get("/api/v1/common/health")
            
            assert response.status_code == 200
            assert response.json() == {"status": "healthy", "database": "connected"}
        finally:
            app.dependency_overrides.clear()

    def test_health_check_database_error(self):
        """Test health check when database connection fails."""
        mock_db = AsyncMock()
        mock_db.command = AsyncMock(side_effect=Exception("Connection failed"))
        
        # Patch the dependency
        async def override_get_db():
            yield mock_db
        
        app.dependency_overrides = {}
        from app.db.session import get_db
        app.dependency_overrides[get_db] = override_get_db
        
        try:
            client = TestClient(app)
            response = client.get("/api/v1/common/health")
            
            assert response.status_code == 200
            assert response.json() == {"status": "unhealthy", "database": "disconnected"}
        finally:
            app.dependency_overrides.clear()
