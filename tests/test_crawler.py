# tests/test_crawler.py
from unittest.mock import AsyncMock, patch

import pytest

from sastaspace.crawler import CrawlResult, crawl


def make_mock_page(
    title="Test Site",
    meta_desc="A test site",
    html="<html><body><h1>Hello</h1></body></html>",
    screenshot_bytes=b"\x89PNG\r\n",
):
    page = AsyncMock()
    page.title = AsyncMock(return_value=title)
    page.content = AsyncMock(return_value=html)
    page.screenshot = AsyncMock(return_value=screenshot_bytes)
    page.evaluate = AsyncMock(return_value=[])
    page.query_selector = AsyncMock(return_value=None)
    page.query_selector_all = AsyncMock(return_value=[])
    page.goto = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    return page


# --- CrawlResult dataclass tests ---


def test_crawl_result_fields():
    r = CrawlResult(
        url="https://acme.com",
        title="Acme",
        meta_description="",
        favicon_url="",
        html_source="<html></html>",
        screenshot_base64="abc123",
        headings=["h1: Hello"],
        navigation_links=[],
        text_content="Hello world",
        images=[],
        colors=["rgb(0,0,0)"],
        fonts=["Arial"],
        sections=[],
        error="",
    )
    assert r.url == "https://acme.com"
    assert r.title == "Acme"
    assert r.error == ""


def test_crawl_result_to_prompt_context():
    r = CrawlResult(
        url="https://acme.com",
        title="Acme Corp",
        meta_description="We sell widgets",
        favicon_url="",
        html_source="<html></html>",
        screenshot_base64="",
        headings=["h1: Welcome", "h2: Products"],
        navigation_links=[{"text": "Home", "href": "/"}],
        text_content="We sell widgets to businesses.",
        images=[],
        colors=["rgb(0,0,0)"],
        fonts=["Arial"],
        sections=[],
        error="",
    )
    ctx = r.to_prompt_context()
    assert "Acme Corp" in ctx
    assert "We sell widgets" in ctx
    assert "h1: Welcome" in ctx
    assert "Home" in ctx


def test_crawl_result_error_field():
    r = CrawlResult(
        url="https://bad.com",
        title="",
        meta_description="",
        favicon_url="",
        html_source="",
        screenshot_base64="",
        headings=[],
        navigation_links=[],
        text_content="",
        images=[],
        colors=[],
        fonts=[],
        sections=[],
        error="Timeout after 30s",
    )
    assert r.error == "Timeout after 30s"


# --- crawl() function tests ---


@pytest.mark.asyncio
async def test_crawl_returns_crawl_result():
    """crawl() should return a CrawlResult with title and screenshot populated."""
    mock_page = make_mock_page(title="Acme Inc", html="<html><body><h1>Acme</h1></body></html>")

    with patch("sastaspace.crawler.async_playwright") as mock_pw:
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_pw.return_value.__aenter__ = AsyncMock(return_value=mock_pw.return_value)
        mock_pw.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_pw.return_value.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser.close = AsyncMock()

        result = await crawl("https://acme.com")

    assert isinstance(result, CrawlResult)
    assert result.url == "https://acme.com"
    assert result.title == "Acme Inc"
    assert result.error == ""
    assert result.screenshot_base64 != ""


@pytest.mark.asyncio
async def test_crawl_handles_timeout_error():
    """crawl() should return CrawlResult with error set containing exception message."""
    with patch("sastaspace.crawler.async_playwright") as mock_pw:
        mock_pw.return_value.__aenter__ = AsyncMock(return_value=mock_pw.return_value)
        mock_pw.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_pw.return_value.chromium.launch = AsyncMock(
            side_effect=Exception("Timeout connecting to browser")
        )

        result = await crawl("https://acme.com")

    assert "Timeout connecting to browser" in result.error


def test_to_prompt_context_empty_optional_fields():
    """to_prompt_context() skips sections for empty optional fields."""
    r = CrawlResult(
        url="https://acme.com",
        title="Acme",
        meta_description="",
        favicon_url="",
        html_source="",
        screenshot_base64="",
        headings=[],
        navigation_links=[],
        text_content="",
        images=[],
        colors=[],
        fonts=[],
        sections=[],
        error="",
    )
    ctx = r.to_prompt_context()
    assert "## Headings" not in ctx
    assert "## Navigation" not in ctx
    assert "## Images" not in ctx
    assert "## Detected Colors" not in ctx
    assert "Acme" in ctx  # title is always included


def test_to_prompt_context_truncates_text_at_5000():
    """to_prompt_context() truncates text content to 5000 chars."""
    long_text = "x" * 6000
    r = CrawlResult(
        url="https://acme.com",
        title="Acme",
        meta_description="",
        favicon_url="",
        html_source="",
        screenshot_base64="",
        headings=[],
        navigation_links=[],
        text_content=long_text,
        images=[],
        colors=[],
        fonts=[],
        sections=[],
        error="",
    )
    ctx = r.to_prompt_context()
    assert ctx.count("x") <= 5000
