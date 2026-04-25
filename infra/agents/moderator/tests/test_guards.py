"""Tests for the Ollama-backed prompt-injection guard.

The actual Ollama HTTP call is mocked so tests stay sub-second and don't
need a running model.
"""

import httpx
import pytest

from sastaspace_moderator.guards import (
    COMMENT_CLOSE,
    COMMENT_OPEN,
    GuardResult,
    OllamaInjectionDetector,
    _parse,
    check_input,
    configure_default_detector,
    wrap_for_classifier,
)


def test_wrap_inserts_both_delimiters():
    out = wrap_for_classifier("hello")
    assert out.startswith(COMMENT_OPEN)
    assert out.endswith(COMMENT_CLOSE)
    assert "hello" in out


def test_check_input_rejects_empty():
    assert not check_input("").passed
    assert not check_input("   \n\t ").passed


def test_check_input_fails_closed_with_no_detector_configured(monkeypatch):
    # Ensure no detector
    monkeypatch.setattr("sastaspace_moderator.guards._default_detector", None)
    r = check_input("hello")
    assert not r.passed
    assert "no injection detector configured" in r.reason


def test_guard_result_is_frozen():
    r = GuardResult(passed=True, reason="ok")
    with pytest.raises(Exception):
        r.passed = False  # type: ignore[misc]


def test_parse_benign():
    assert _parse("BENIGN").passed
    assert _parse("benign").passed
    assert _parse("benign.").passed
    assert _parse("BENIGN\nextra noise").passed


def test_parse_attack():
    r = _parse("ATTACK")
    assert not r.passed
    assert r.risk_score == 1.0
    assert "injection" in r.reason.lower()


def test_parse_unexpected_fails_closed():
    r = _parse("Hmm I'm not sure")
    assert not r.passed
    assert "unexpected" in r.reason.lower()


def test_parse_empty_fails_closed():
    r = _parse("")
    assert not r.passed


def test_detector_calls_ollama_chat_endpoint(monkeypatch):
    captured = {}

    def fake_post(self, url, json=None, **_kw):
        captured["url"] = url
        captured["payload"] = json
        return httpx.Response(
            200,
            json={"message": {"content": "BENIGN"}},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    d = OllamaInjectionDetector(ollama_host="http://stub:11434", model="x")
    r = d.detect("a comment")
    assert r.passed
    assert captured["url"] == "http://stub:11434/api/chat"
    assert captured["payload"]["model"] == "x"
    assert captured["payload"]["options"]["temperature"] == 0
    assert captured["payload"]["options"]["num_predict"] == 5


def test_detector_flags_attack_response(monkeypatch):
    monkeypatch.setattr(
        httpx.Client,
        "post",
        lambda self, url, **_kw: httpx.Response(
            200,
            json={"message": {"content": "ATTACK"}},
            request=httpx.Request("POST", url),
        ),
    )
    d = OllamaInjectionDetector(ollama_host="http://stub", model="x")
    assert not d.detect("ignore previous").passed


def test_check_input_via_configure_default_detector(monkeypatch):
    monkeypatch.setattr(
        httpx.Client,
        "post",
        lambda self, url, **_kw: httpx.Response(
            200,
            json={"message": {"content": "BENIGN"}},
            request=httpx.Request("POST", url),
        ),
    )
    configure_default_detector(host="http://stub", model="x")
    r = check_input("hi from a real test")
    assert r.passed


def test_check_input_handles_detector_exceptions(monkeypatch):
    class Boom:
        def detect(self, body):
            raise RuntimeError("kaboom")

    monkeypatch.setattr("sastaspace_moderator.guards._default_detector", Boom())
    r = check_input("anything")
    assert not r.passed
    assert "detector error" in r.reason
