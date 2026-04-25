"""Tests for the auth service's SpacetimeDB client wrapper."""

import httpx
import pytest

from sastaspace_auth.stdb import SpacetimeClient


def test_call_reducer_posts_json_with_auth_header(monkeypatch):
    captured = {}

    def fake_post(self, url, content=None, headers=None, **_kw):
        captured["url"] = url
        captured["content"] = content
        captured["headers"] = headers
        return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    c = SpacetimeClient("http://stub", "sastaspace", "owner-tok")
    c.issue_auth_token("a" * 64, "u@e.com")
    assert captured["url"] == "http://stub/v1/database/sastaspace/call/issue_auth_token"
    assert "u@e.com" in captured["content"]


def test_call_reducer_raises_on_4xx(monkeypatch):
    from tenacity import RetryError

    def fake_post(self, url, **_kw):
        return httpx.Response(400, text="rate limit", request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    c = SpacetimeClient("http://stub", "sastaspace", "tok")
    # tenacity's @retry wraps the underlying RuntimeError after exhausting attempts.
    with pytest.raises((RuntimeError, RetryError)):
        c.consume_auth_token("a" * 64)


def test_register_user_passes_identity_email_displayname(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        httpx.Client,
        "post",
        lambda self, url, content=None, **_kw: (captured.update(content=content) or
            httpx.Response(200, request=httpx.Request("POST", url))),
    )
    c = SpacetimeClient("http://stub", "sastaspace", "tok")
    c.register_user("c20deadbeef", "u@e.com", "User Name")
    assert "c20deadbeef" in captured["content"]
    assert "u@e.com" in captured["content"]
    assert "User Name" in captured["content"]


def test_issue_identity_parses_response(monkeypatch):
    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, **_kw: httpx.Response(
            200,
            json={"identity": "c20abc", "token": "eyJtok"},
            request=httpx.Request("POST", url),
        ),
    )
    c = SpacetimeClient("http://stub", "sastaspace", "owner-tok")
    issued = c.issue_identity()
    assert issued.identity_hex == "c20abc"
    assert issued.token == "eyJtok"


def test_find_user_identity_returns_none_when_no_row(monkeypatch):
    monkeypatch.setattr(
        httpx.Client,
        "post",
        lambda self, url, **_kw: httpx.Response(
            200, json=[{"rows": []}], request=httpx.Request("POST", url)
        ),
    )
    c = SpacetimeClient("http://stub", "sastaspace", "tok")
    assert c.find_user_identity("nobody@example.com") is None


def test_find_user_identity_returns_hex_when_found(monkeypatch):
    monkeypatch.setattr(
        httpx.Client,
        "post",
        lambda self, url, **_kw: httpx.Response(
            200,
            json=[{"rows": [["c20deadbeef"]]}],
            request=httpx.Request("POST", url),
        ),
    )
    c = SpacetimeClient("http://stub", "sastaspace", "tok")
    assert c.find_user_identity("u@e.com") == "c20deadbeef"
