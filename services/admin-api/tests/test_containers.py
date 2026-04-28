"""Tests for containers endpoint."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SPACETIME_TOKEN", "test-token")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("OWNER_EMAIL", "owner@example.com")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://admin.sastaspace.com")

    from sastaspace_admin_api.main import app

    with TestClient(app) as c:
        yield c


def _make_container(name: str, status: str = "running"):
    c = MagicMock()
    c.name = name
    c.attrs = {
        "State": {"Status": status, "StartedAt": "2026-04-20T10:12:00.000000000Z"},
        "RestartCount": 0,
    }
    img = MagicMock()
    img.tags = [f"sastaspace-{name}:local"]
    c.image = img
    c.stats = MagicMock(
        return_value={
            "memory_stats": {
                "usage": 130_023_424,
                "limit": 2_147_483_648,
            }
        }
    )
    return c


def test_containers_shape(client):
    fake = [_make_container("sastaspace-stdb"), _make_container("sastaspace-auth")]

    with patch("docker.from_env") as mock_docker:
        mock_docker.return_value.containers.list.return_value = fake
        resp = client.get("/containers")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2

    row = data[0]
    assert row["name"] == "sastaspace-stdb"
    assert row["status"] == "running"
    assert "uptime_s" in row
    assert "mem_usage_mb" in row
    assert "mem_limit_mb" in row
    assert "restart_count" in row
    assert "started_at" in row
    assert "image" in row
