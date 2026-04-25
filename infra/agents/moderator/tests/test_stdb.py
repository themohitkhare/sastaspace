import httpx
import pytest
from tenacity import RetryError

from sastaspace_moderator.stdb import PendingComment, SpacetimeClient, _micros, _parse_pending


def test_parse_pending_handles_empty_payload():
    assert _parse_pending([]) == []
    assert _parse_pending(None) == []
    assert _parse_pending([{"rows": []}]) == []


def test_parse_pending_extracts_rows():
    payload = [
        {
            "rows": [
                [
                    1,
                    "2026-04-25-hello",
                    "Alice",
                    "Nice post.",
                    {"__timestamp_micros_since_unix_epoch__": 1777_000_000_000_000},
                ],
                [2, "x", "Bob", "hi", 1777_000_000_001_000],
            ]
        }
    ]
    parsed = _parse_pending(payload)
    assert len(parsed) == 2
    assert parsed[0] == PendingComment(
        id=1,
        post_slug="2026-04-25-hello",
        author_name="Alice",
        body="Nice post.",
        created_at_micros=1777_000_000_000_000,
    )
    assert parsed[1].id == 2


def test_micros_handles_both_encodings():
    assert _micros(123) == 123
    assert _micros({"__timestamp_micros_since_unix_epoch__": 456}) == 456
    assert _micros("nope") == 0
    assert _micros({}) == 0


def test_set_status_calls_correct_endpoint(monkeypatch):
    captured = {}

    def fake_post(self, url, content=None, headers=None, **_kw):
        captured["url"] = url
        captured["content"] = content
        captured["headers"] = headers
        return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    client = SpacetimeClient("http://stdb", "sastaspace", "tok")
    client.set_status(7, "approved")
    assert captured["url"] == "http://stdb/v1/database/sastaspace/call/set_comment_status"
    assert "7" in captured["content"]
    assert "approved" in captured["content"]


def test_set_status_retries_on_5xx(monkeypatch):
    calls = {"n": 0}

    def fake_post(self, url, content=None, headers=None, **_kw):
        calls["n"] += 1
        if calls["n"] < 2:
            return httpx.Response(500, request=httpx.Request("POST", url))
        return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    client = SpacetimeClient("http://stdb", "sastaspace", "tok", timeout=1.0)
    client.set_status(1, "approved")
    assert calls["n"] >= 2


def test_set_status_gives_up_after_max_attempts(monkeypatch):
    monkeypatch.setattr(
        httpx.Client,
        "post",
        lambda self, url, **_kw: httpx.Response(500, request=httpx.Request("POST", url)),
    )
    client = SpacetimeClient("http://stdb", "sastaspace", "tok", timeout=1.0)
    # tenacity wraps the underlying HTTPStatusError in its RetryError after
    # the configured stop_after_attempt(3) is exhausted.
    with pytest.raises(RetryError):
        client.set_status(1, "approved")


def test_fetch_pending_returns_parsed_rows(monkeypatch):
    captured = {}

    def fake_post(self, url, content=None, headers=None, **_kw):
        captured["url"] = url
        captured["content"] = content
        body = {
            "rows": [[1, "x", "Alice", "hi", 12345]],
            "schema": {},
        }
        # SpacetimeDB SQL response is a JSON array with one statement result.
        return httpx.Response(
            200, json=[body], request=httpx.Request("POST", url)
        )

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    client = SpacetimeClient("http://stdb", "sastaspace", "tok")
    rows = client.fetch_pending(limit=10)
    assert len(rows) == 1
    assert rows[0].body == "hi"
    assert "SELECT" in captured["content"]
    assert "LIMIT 10" in captured["content"]


def test_close_releases_underlying_client(monkeypatch):
    closed = {"n": 0}
    monkeypatch.setattr(httpx.Client, "close", lambda self: closed.update(n=closed["n"] + 1))
    with SpacetimeClient("http://stdb", "sastaspace", "tok") as c:
        assert c is not None
    assert closed["n"] == 1
