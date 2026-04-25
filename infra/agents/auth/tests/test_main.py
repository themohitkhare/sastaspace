"""End-to-end tests for the auth FastAPI app, using TestClient + mocks."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch):
    # Required env before importing the app
    monkeypatch.setenv("SPACETIME_TOKEN", "test-token")
    monkeypatch.setenv("RESEND_API_KEY", "re_test_x")
    monkeypatch.setenv("PUBLIC_BASE", "https://auth.test")
    monkeypatch.setenv("NOTES_CALLBACK", "https://notes.test/auth/callback")

    from sastaspace_auth.main import app

    fake_stdb = MagicMock()
    fake_stdb.issue_auth_token.return_value = None
    fake_stdb.consume_auth_token.return_value = None
    fake_stdb.register_user.return_value = None
    fake_stdb.find_user_identity.return_value = None
    fake_stdb.issue_identity.return_value = MagicMock(
        identity_hex="c20012345abcdef", token="eyJtest"
    )
    fake_sender = MagicMock()
    fake_sender.send_magic_link.return_value = MagicMock(
        sent=True, detail="msg-id-123"
    )

    # Override startup state with mocks
    app.state.stdb = fake_stdb
    app.state.sender = fake_sender

    yield TestClient(app), fake_stdb, fake_sender


def test_healthz_ok(client):
    c, *_ = client
    r = c.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_request_validates_email(client):
    c, *_ = client
    r = c.post("/auth/request", json={"email": "not-an-email"})
    assert r.status_code == 422  # pydantic EmailStr rejects


def test_request_happy_path_calls_stdb_and_sends_email(client):
    c, stdb, sender = client
    r = c.post("/auth/request", json={"email": "user@example.com"})
    assert r.status_code == 200
    assert r.json()["sent"] is True

    stdb.issue_auth_token.assert_called_once()
    args = stdb.issue_auth_token.call_args.args
    assert len(args[0]) >= 32  # token has entropy
    assert args[1] == "user@example.com"

    sender.send_magic_link.assert_called_once()
    sent_to, link = sender.send_magic_link.call_args.args
    assert sent_to == "user@example.com"
    assert link.startswith("https://auth.test/auth/verify?t=")


def test_request_normalises_email_to_lowercase(client):
    c, stdb, _ = client
    c.post("/auth/request", json={"email": "MIxedCase@Example.com"})
    args = stdb.issue_auth_token.call_args.args
    assert args[1] == "mixedcase@example.com"


def test_request_502s_on_stdb_failure(client):
    c, stdb, _ = client
    stdb.issue_auth_token.side_effect = RuntimeError("stdb down")
    r = c.post("/auth/request", json={"email": "u@example.com"})
    assert r.status_code == 502
    assert "stdb error" in r.json()["detail"]


def test_request_502s_on_email_send_failure(client):
    c, _, sender = client
    sender.send_magic_link.return_value = MagicMock(sent=False, detail="DNS unverified")
    r = c.post("/auth/request", json={"email": "u@example.com"})
    assert r.status_code == 502
    assert "email send failed" in r.json()["detail"]


def test_verify_rejects_short_token(client):
    c, *_ = client
    r = c.get("/auth/verify?t=tooshort")
    assert r.status_code == 400
    assert "Invalid sign-in link" in r.text


def test_verify_returns_404_on_missing_token(client):
    c, *_ = client
    r = c.get("/auth/verify")
    assert r.status_code == 400


def test_verify_happy_path_renders_redirect_html(client, monkeypatch):
    c, stdb, _ = client

    # Patch _email_for_token to return a known email (bypasses the SQL query)
    monkeypatch.setattr(
        "sastaspace_auth.main._email_for_token",
        lambda *_a, **_kw: "user@example.com",
    )

    long_token = "a" * 64
    r = c.get(f"/auth/verify?t={long_token}")
    assert r.status_code == 200
    body = r.text
    assert "signed in" in body.lower()
    assert "user@example.com" in body
    # JWT and callback are passed to JS which assembles the redirect URL
    assert "eyJtest" in body
    assert "https://notes.test/auth/callback" in body
    stdb.consume_auth_token.assert_called_once_with(long_token)
    stdb.register_user.assert_called_once()
    args = stdb.register_user.call_args.args
    assert args[0] == "c20012345abcdef"
    assert args[1] == "user@example.com"
    assert args[2] == "user"  # display_name = local-part of email


def test_verify_400s_when_token_lookup_fails(client, monkeypatch):
    c, stdb, _ = client
    stdb.consume_auth_token.side_effect = RuntimeError("token already used")
    r = c.get("/auth/verify?t=" + "a" * 64)
    assert r.status_code == 400
    # The friendly mapper rewrites the raw reducer error
    assert "already been used" in r.text


def test_verify_friendly_message_for_expired(client):
    c, stdb, _ = client
    stdb.consume_auth_token.side_effect = RuntimeError("token expired")
    r = c.get("/auth/verify?t=" + "a" * 64)
    assert r.status_code == 400
    assert "expired" in r.text
    assert "request a new one" in r.text.lower()
