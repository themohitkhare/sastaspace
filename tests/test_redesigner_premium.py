# tests/test_redesigner_premium.py
"""Tests for the premium (psychology-based) redesigner."""

import base64
from unittest.mock import MagicMock, patch

import pytest

from sastaspace.crawler import CrawlResult
from sastaspace.redesigner import (
    PREMIUM_SYSTEM_PROMPT,
    PREMIUM_USER_PROMPT_TEMPLATE,
    RedesignError,
    redesign_premium,
)

SAMPLE_HTML = """<!DOCTYPE html>
<html lang="en">
<head><title>Premium Test</title></head>
<body><h1>Hello Premium</h1></body>
</html>"""

FAKE_PNG_B64 = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 20).decode()


def make_crawl_result(url="https://acme.com", title="Acme", screenshot_b64=None):
    return CrawlResult(
        url=url,
        title=title,
        meta_description="Best widgets",
        favicon_url="",
        html_source="<html></html>",
        screenshot_base64=screenshot_b64 if screenshot_b64 is not None else FAKE_PNG_B64,
        headings=["h1: Hello"],
        navigation_links=[],
        text_content="Hello",
        images=[],
        colors=["#ff0000", "#0000ff"],
        fonts=["Arial"],
        sections=[],
        error="",
    )


def make_mock_client(response_text: str):
    mock_message = MagicMock()
    mock_message.content = response_text
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


def test_premium_redesign_returns_valid_html():
    mock_client = make_mock_client(SAMPLE_HTML)

    with patch("sastaspace.redesigner.OpenAI", return_value=mock_client):
        result = redesign_premium(make_crawl_result())

    assert "<!DOCTYPE html>" in result
    assert "</html>" in result


def test_premium_uses_premium_system_prompt():
    mock_client = make_mock_client(SAMPLE_HTML)

    with patch("sastaspace.redesigner.OpenAI", return_value=mock_client):
        redesign_premium(make_crawl_result())

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    system_msg = call_kwargs["messages"][0]["content"]
    assert "Sales & Conversion Psychology" in system_msg
    assert "Cognitive Biases" in system_msg
    assert "Color Psychology" in system_msg


def test_premium_uses_higher_token_limit():
    mock_client = make_mock_client(SAMPLE_HTML)

    with patch("sastaspace.redesigner.OpenAI", return_value=mock_client):
        redesign_premium(make_crawl_result())

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["max_tokens"] == 20000


def test_premium_raises_on_crawl_error():
    bad_result = make_crawl_result()
    bad_result.error = "Timeout"

    with pytest.raises(RedesignError, match="crawl failed"):
        redesign_premium(bad_result)


def test_premium_raises_on_empty_response():
    mock_client = make_mock_client("")

    with patch("sastaspace.redesigner.OpenAI", return_value=mock_client):
        with pytest.raises(RedesignError, match="empty"):
            redesign_premium(make_crawl_result())


def test_premium_prompt_mentions_conversion():
    """The premium user prompt template includes conversion-focused language."""
    assert "conversion-optimized" in PREMIUM_USER_PROMPT_TEMPLATE.lower()
    assert "Value Proposition" in PREMIUM_USER_PROMPT_TEMPLATE
    # AIDA framework: Attention → Interest → Desire → Action
    assert "Attention" in PREMIUM_USER_PROMPT_TEMPLATE
    assert "Action" in PREMIUM_USER_PROMPT_TEMPLATE


def test_premium_system_prompt_has_psychology_principles():
    """Premium system prompt includes key psychology concepts."""
    assert "Anchoring" in PREMIUM_SYSTEM_PROMPT
    assert "Scarcity" in PREMIUM_SYSTEM_PROMPT
    assert "Loss Aversion" in PREMIUM_SYSTEM_PROMPT
    assert "Von Restorff" in PREMIUM_SYSTEM_PROMPT
    assert "Halo Effect" in PREMIUM_SYSTEM_PROMPT
    assert "Social Proof" in PREMIUM_SYSTEM_PROMPT
