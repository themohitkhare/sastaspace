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


def make_mock_client(response_text: str):
    """Return a mock OpenAI client whose chat.completions.create() returns response_text."""
    mock_message = MagicMock()
    mock_message.content = response_text
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


# --- HTML cleaning tests ---


def test_strips_markdown_fences():
    """redesign() strips ```html ... ``` wrapping."""
    wrapped = f"```html\n{SAMPLE_HTML}\n```"
    mock_client = make_mock_client(wrapped)

    with patch("sastaspace.redesigner.OpenAI", return_value=mock_client):
        result = redesign(make_crawl_result())

    assert result.startswith("<!DOCTYPE html>")
    assert "```" not in result


def test_strips_generic_fences():
    wrapped = f"```\n{SAMPLE_HTML}\n```"
    mock_client = make_mock_client(wrapped)

    with patch("sastaspace.redesigner.OpenAI", return_value=mock_client):
        result = redesign(make_crawl_result())

    assert "```" not in result


def test_valid_html_passes_through():
    mock_client = make_mock_client(SAMPLE_HTML)

    with patch("sastaspace.redesigner.OpenAI", return_value=mock_client):
        result = redesign(make_crawl_result())

    assert "<!DOCTYPE html>" in result
    assert "</html>" in result


# --- Validity check tests ---


def test_raises_on_empty_response():
    mock_client = make_mock_client("")

    with patch("sastaspace.redesigner.OpenAI", return_value=mock_client):
        with pytest.raises(RedesignError, match="empty"):
            redesign(make_crawl_result())


def test_raises_on_missing_doctype():
    mock_client = make_mock_client("<html><body>Hi</body></html>")

    with patch("sastaspace.redesigner.OpenAI", return_value=mock_client):
        with pytest.raises(RedesignError, match="DOCTYPE"):
            redesign(make_crawl_result())


def test_raises_on_missing_closing_html_tag():
    truncated = "<!DOCTYPE html>\n<html><body>Cut off mid way..."
    mock_client = make_mock_client(truncated)

    with patch("sastaspace.redesigner.OpenAI", return_value=mock_client):
        with pytest.raises(RedesignError, match="</html>"):
            redesign(make_crawl_result())


def test_raises_on_crawl_error():
    """redesign() raises before calling the API when CrawlResult.error is set."""
    bad_result = make_crawl_result()
    bad_result.error = "Timeout"

    mock_client = make_mock_client("")
    with patch("sastaspace.redesigner.OpenAI", return_value=mock_client):
        with pytest.raises(RedesignError, match="crawl failed"):
            redesign(bad_result)

    mock_client.chat.completions.create.assert_not_called()


# --- OpenAI client call tests ---


def test_client_called_with_image_when_screenshot_present():
    """When screenshot_base64 is set, messages include an image_url content block."""
    mock_client = make_mock_client(SAMPLE_HTML)

    with patch("sastaspace.redesigner.OpenAI", return_value=mock_client):
        redesign(make_crawl_result(screenshot_b64=FAKE_PNG_B64))

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    user_content = call_kwargs["messages"][-1]["content"]
    image_blocks = [c for c in user_content if c.get("type") == "image_url"]
    assert len(image_blocks) == 1
    assert "base64" in image_blocks[0]["image_url"]["url"]


def test_client_called_without_image_when_no_screenshot():
    """When screenshot_base64 is empty, messages contain only the text block."""
    mock_client = make_mock_client(SAMPLE_HTML)

    with patch("sastaspace.redesigner.OpenAI", return_value=mock_client):
        redesign(make_crawl_result(screenshot_b64=""))

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    user_content = call_kwargs["messages"][-1]["content"]
    image_blocks = [c for c in user_content if c.get("type") == "image_url"]
    assert len(image_blocks) == 0
