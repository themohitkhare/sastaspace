"""Tests for the STDB write proxy endpoints."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SPACETIME_TOKEN", "test-token")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
    monkeypatch.setenv("OWNER_EMAIL", "owner@example.com")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://admin.sastaspace.com")

    from sastaspace_admin_api.main import app

    with TestClient(app) as c:
        yield c


def _good_id_info(email: str = "owner@example.com") -> dict:
    return {"email": email, "sub": "12345"}


def test_set_status_ok(client):
    with (
        patch("google.oauth2.id_token.verify_oauth2_token", return_value=_good_id_info()),
        patch.object(client.app.state, "stdb", create=True) as stdb,
    ):
        stdb.set_comment_status = MagicMock()
        resp = client.post(
            "/stdb/comments/42/status",
            json={"status": "approved"},
            headers={"Authorization": "Bearer fake-token"},
        )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_set_status_invalid_status(client):
    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=_good_id_info()):
        resp = client.post(
            "/stdb/comments/42/status",
            json={"status": "banana"},
            headers={"Authorization": "Bearer fake-token"},
        )
    assert resp.status_code == 422


def test_set_status_wrong_email(client):
    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=_good_id_info("other@example.com")):
        resp = client.post(
            "/stdb/comments/42/status",
            json={"status": "approved"},
            headers={"Authorization": "Bearer fake-token"},
        )
    assert resp.status_code == 403


def test_set_status_no_token(client):
    resp = client.post("/stdb/comments/42/status", json={"status": "approved"})
    assert resp.status_code == 422  # missing required Header


def test_set_status_bad_token(client):
    with patch("google.oauth2.id_token.verify_oauth2_token", side_effect=ValueError("bad")):
        resp = client.post(
            "/stdb/comments/42/status",
            json={"status": "approved"},
            headers={"Authorization": "Bearer invalid"},
        )
    assert resp.status_code == 401


def test_delete_ok(client):
    with (
        patch("google.oauth2.id_token.verify_oauth2_token", return_value=_good_id_info()),
        patch.object(client.app.state, "stdb", create=True) as stdb,
    ):
        stdb.delete_comment = MagicMock()
        resp = client.delete(
            "/stdb/comments/42",
            headers={"Authorization": "Bearer fake-token"},
        )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
