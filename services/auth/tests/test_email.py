"""Tests for the Resend email sender wrapper."""

from unittest.mock import patch

from sastaspace_auth.email import EmailResult, Sender, render_html, render_text


def test_render_html_includes_link():
    out = render_html("https://auth.example/verify?t=abc")
    assert "https://auth.example/verify?t=abc" in out
    assert "<!doctype html>" in out.lower()
    assert "sign in" in out.lower()


def test_render_text_includes_link():
    out = render_text("https://auth.example/verify?t=abc")
    assert "https://auth.example/verify?t=abc" in out
    assert "sign in" in out.lower()


def test_sender_calls_resend_with_correct_envelope():
    with patch("sastaspace_auth.email.resend") as resend_mod:
        resend_mod.Emails.send.return_value = {"id": "msg_123"}
        s = Sender(api_key="re_test", from_address="hi@test.com")
        result = s.send_magic_link("you@example.com", "https://auth.test/verify?t=z")
        assert isinstance(result, EmailResult)
        assert result.sent is True
        assert result.detail == "msg_123"
        sent_envelope = resend_mod.Emails.send.call_args.args[0]
        assert sent_envelope["from"] == "hi@test.com"
        assert sent_envelope["to"] == ["you@example.com"]
        assert "https://auth.test/verify?t=z" in sent_envelope["html"]
        assert "https://auth.test/verify?t=z" in sent_envelope["text"]


def test_sender_returns_failed_on_resend_exception():
    with patch("sastaspace_auth.email.resend") as resend_mod:
        resend_mod.Emails.send.side_effect = RuntimeError("API unreachable")
        s = Sender(api_key="re_test")
        result = s.send_magic_link("a@b.com", "https://x")
        assert result.sent is False
        assert "API unreachable" in result.detail
