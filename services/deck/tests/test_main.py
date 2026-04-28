"""End-to-end tests for the deck FastAPI app, using TestClient."""

import sys

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("OLLAMA_URL", "")  # force local fallback
    # Placeholder renderer was removed (2026-04-27); /generate now returns
    # 503 unless musicgen is wired. Tests assert that contract.
    monkeypatch.setenv("PREFER_MUSICGEN", "0")
    sys.modules.pop("sastaspace_deck.main", None)
    from sastaspace_deck.main import app

    return TestClient(app)


def test_healthz_ok(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_plan_returns_track_list(client):
    r = client.post("/plan", json={"description": "A meditation app", "count": 3})
    assert r.status_code == 200
    body = r.json()
    assert "tracks" in body
    assert len(body["tracks"]) == 3
    first = body["tracks"][0]
    for k in ("name", "type", "length", "desc", "tempo", "instruments", "mood", "musicgen_prompt"):
        assert k in first


def test_plan_rejects_short_description(client):
    r = client.post("/plan", json={"description": "ab", "count": 3})
    assert r.status_code == 422


def test_plan_clamps_count_at_validation(client):
    r = client.post("/plan", json={"description": "A meditation app", "count": 99})
    assert r.status_code == 422


def test_generate_without_musicgen_returns_503(client):
    """No real renderer wired up → /generate must refuse, not synth a placeholder zip."""
    r = client.post("/generate", json={"description": "A meditation app", "count": 3})
    assert r.status_code == 503
    body = r.json()
    detail = body["detail"].lower()
    assert "musicgen" in detail or "render" in detail


def test_generate_with_user_tracks_without_musicgen_returns_503(client):
    r = client.post(
        "/generate",
        json={
            "description": "Anything",
            "count": 1,
            "tracks": [
                {
                    "name": "Custom Bell",
                    "type": "one-shot",
                    "length": 2,
                    "desc": "test",
                    "tempo": "free",
                    "instruments": "bell",
                    "mood": "calm",
                }
            ],
        },
    )
    assert r.status_code == 503
