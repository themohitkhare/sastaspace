"""Tests for logs SSE endpoint."""

from unittest.mock import patch

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


def test_logs_unknown_container(client):
    with patch("sastaspace_admin_api.main.known_container_names", return_value=["sastaspace-stdb"]):
        resp = client.get("/logs/nonexistent-xyz")
    assert resp.status_code == 404


def test_logs_known_container_streams(client):
    import json

    async def _fake_stream(name: str, tail: int = 200):
        line = '{"ts":"14:31:58.124","text":"INFO hello","level":"info"}'
        yield f"data: {line}\n\n"

    with (
        patch("sastaspace_admin_api.main.known_container_names", return_value=["sastaspace-stdb"]),
        patch("sastaspace_admin_api.main.stream_logs", side_effect=_fake_stream),
    ):
        with client.stream("GET", "/logs/sastaspace-stdb") as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]
            chunk = next(resp.iter_lines())
            assert chunk.startswith("data: ")
            payload = json.loads(chunk[6:])
            assert "ts" in payload
            assert "text" in payload
            assert "level" in payload
