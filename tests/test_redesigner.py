# tests/test_redesigner.py
import base64
from unittest.mock import MagicMock, patch

import pytest

from sastaspace.crawler import CrawlResult
from sastaspace.redesigner import RedesignError, redesign

SAMPLE_HTML = """<!DOCTYPE html>
<html lang="en">
<head><title>Test</title></head>
<body><h1>Hello</h1></body>
</html>"""

# Minimal valid base64-encoded PNG (1x1 pixel)
FAKE_PNG_B64 = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 20).decode()


def make_crawl_result(url="https://acme.com", title="Acme", screenshot_b64=None):
    return CrawlResult(
        url=url,
        title=title,
        meta_description="",
        favicon_url="",
        html_source="<html></html>",
        screenshot_base64=screenshot_b64 if screenshot_b64 is not None else FAKE_PNG_B64,
        headings=["h1: Hello"],
        navigation_links=[],
        text_content="Hello",
        images=[],
        colors=[],
        fonts=[],
        sections=[],
        error="",
    )


def make_mock_agent(response_text: str):
    """Return a mock Agno Agent whose .run() returns a RunOutput-like object."""
    mock_response = MagicMock()
    mock_response.content = response_text
    mock_agent = MagicMock()
    mock_agent.run.return_value = mock_response
    return mock_agent


# --- HTML cleaning tests ---


def test_strips_markdown_fences():
    """redesign() strips ```html ... ``` wrapping."""
    wrapped = f"```html\n{SAMPLE_HTML}\n```"
    mock_agent = make_mock_agent(wrapped)

    with patch("sastaspace.redesigner.Agent", return_value=mock_agent):
        result = redesign(make_crawl_result(), api_key="sk-test")

    assert result.startswith("<!DOCTYPE html>")
    assert "```" not in result


def test_strips_generic_fences():
    wrapped = f"```\n{SAMPLE_HTML}\n```"
    mock_agent = make_mock_agent(wrapped)

    with patch("sastaspace.redesigner.Agent", return_value=mock_agent):
        result = redesign(make_crawl_result(), api_key="sk-test")

    assert "```" not in result


def test_valid_html_passes_through():
    mock_agent = make_mock_agent(SAMPLE_HTML)

    with patch("sastaspace.redesigner.Agent", return_value=mock_agent):
        result = redesign(make_crawl_result(), api_key="sk-test")

    assert "<!DOCTYPE html>" in result
    assert "</html>" in result


# --- Validity check tests ---


def test_raises_on_empty_response():
    mock_agent = make_mock_agent("")

    with patch("sastaspace.redesigner.Agent", return_value=mock_agent):
        with pytest.raises(RedesignError, match="empty"):
            redesign(make_crawl_result(), api_key="sk-test")


def test_raises_on_missing_doctype():
    mock_agent = make_mock_agent("<html><body>Hi</body></html>")

    with patch("sastaspace.redesigner.Agent", return_value=mock_agent):
        with pytest.raises(RedesignError, match="DOCTYPE"):
            redesign(make_crawl_result(), api_key="sk-test")


def test_raises_on_missing_closing_html_tag():
    truncated = "<!DOCTYPE html>\n<html><body>Cut off mid way..."
    mock_agent = make_mock_agent(truncated)

    with patch("sastaspace.redesigner.Agent", return_value=mock_agent):
        with pytest.raises(RedesignError, match="</html>"):
            redesign(make_crawl_result(), api_key="sk-test")


def test_raises_on_crawl_error():
    """redesign() raises before calling the API when CrawlResult.error is set."""
    bad_result = make_crawl_result()
    bad_result.error = "Timeout"

    mock_agent = make_mock_agent("")
    with patch("sastaspace.redesigner.Agent", return_value=mock_agent):
        with pytest.raises(RedesignError, match="crawl failed"):
            redesign(bad_result, api_key="sk-test")

    mock_agent.run.assert_not_called()


# --- Agno agent call tests ---


def test_agent_run_called_with_images_when_screenshot_present():
    """When screenshot_base64 is set, agent.run() receives images=[...]."""
    mock_agent = make_mock_agent(SAMPLE_HTML)

    with patch("sastaspace.redesigner.Agent", return_value=mock_agent):
        redesign(make_crawl_result(screenshot_b64=FAKE_PNG_B64), api_key="sk-test")

    call_kwargs = mock_agent.run.call_args.kwargs
    assert call_kwargs.get("images") is not None
    assert len(call_kwargs["images"]) == 1


def test_agent_run_called_without_images_when_no_screenshot():
    """When screenshot_base64 is empty, agent.run() receives images=None."""
    mock_agent = make_mock_agent(SAMPLE_HTML)

    with patch("sastaspace.redesigner.Agent", return_value=mock_agent):
        redesign(make_crawl_result(screenshot_b64=""), api_key="sk-test")

    call_kwargs = mock_agent.run.call_args.kwargs
    assert call_kwargs.get("images") is None
