# tests/test_crawler.py
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sastaspace.crawler import (
    CrawlResult,
    _ensure_chromium,
    _extract_images,
    _extract_nav_links,
    _extract_sections,
    _extract_text,
    crawl,
)

from bs4 import BeautifulSoup


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


# --- to_prompt_context() images and sections branches ---


def test_to_prompt_context_with_images():
    """Lines 64-67: images section in to_markdown."""
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
        images=[{"src": "logo.png", "alt": "Logo"}],
        colors=[],
        fonts=[],
        sections=[],
        error="",
    )
    ctx = r.to_prompt_context()
    assert "## Images" in ctx
    assert "logo.png" in ctx


def test_to_prompt_context_with_sections():
    """Lines 73-74: sections in to_markdown."""
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
        sections=[{"heading": "About", "content": "We are a company."}],
        error="",
    )
    ctx = r.to_prompt_context()
    assert "Section: About" in ctx
    assert "We are a company" in ctx


# --- _extract_text ---


def test_extract_text():
    """Line 83: _extract_text function."""
    html = "<html><body><script>var x=1;</script><p>Hello world</p><style>.x{}</style></body></html>"
    result = _extract_text(html)
    assert "Hello world" in result
    assert "var x" not in result


# --- _extract_nav_links ---


def test_extract_nav_links():
    """Lines 101-105: _extract_nav_links function."""
    html = '<html><body><nav><a href="/home">Home</a><a href="/about">About</a></nav></body></html>'
    soup = BeautifulSoup(html, "html.parser")
    links = _extract_nav_links(soup)
    assert len(links) == 2
    assert links[0]["text"] == "Home"
    assert links[0]["href"] == "/home"


# --- _extract_images ---


def test_extract_images():
    """Line 112: _extract_images function."""
    html = '<html><body><img src="logo.png" alt="Logo" width="100" height="50"></body></html>'
    soup = BeautifulSoup(html, "html.parser")
    images = _extract_images(soup)
    assert len(images) == 1
    assert images[0]["src"] == "logo.png"
    assert images[0]["alt"] == "Logo"


# --- _extract_sections ---


def test_extract_sections():
    """Lines 126-129: _extract_sections function."""
    html = '<html><body><section class="hero"><h2>Welcome</h2><p>Content here.</p></section></body></html>'
    soup = BeautifulSoup(html, "html.parser")
    sections = _extract_sections(soup)
    assert len(sections) == 1
    assert sections[0]["heading"] == "Welcome"
    assert "Content here" in sections[0]["content"]


# --- _ensure_chromium ---


def test_ensure_chromium_runs_install_when_needed():
    """Lines 24-29: _ensure_chromium installs chromium when dry-run fails."""
    mock_dry_run = MagicMock()
    mock_dry_run.returncode = 1
    mock_dry_run.stdout = b"chromium not installed"

    with patch("sastaspace.crawler.subprocess.run") as mock_run:
        mock_run.side_effect = [mock_dry_run, MagicMock()]
        _ensure_chromium()

    assert mock_run.call_count == 2


def test_ensure_chromium_skips_install_when_ok():
    """_ensure_chromium skips install when dry-run succeeds."""
    mock_dry_run = MagicMock()
    mock_dry_run.returncode = 0
    mock_dry_run.stdout = b""

    with patch("sastaspace.crawler.subprocess.run", return_value=mock_dry_run) as mock_run:
        _ensure_chromium()

    assert mock_run.call_count == 1


def test_ensure_chromium_handles_exception():
    """Lines 28-29: _ensure_chromium swallows exceptions."""
    with patch("sastaspace.crawler.subprocess.run", side_effect=Exception("oops")):
        _ensure_chromium()  # Should not raise


# --- crawl() with meta_description and favicon ---


@pytest.mark.asyncio
async def test_crawl_extracts_meta_and_favicon():
    """Lines 176, 181: meta_description and favicon extraction."""
    html_with_meta = (
        '<html><head>'
        '<meta name="description" content="A great site">'
        '<link rel="icon" href="/favicon.ico">'
        '</head><body><h1>Test</h1></body></html>'
    )
    mock_page = make_mock_page(html=html_with_meta)
    mock_page.evaluate = AsyncMock(return_value=["rgb(0,0,0)"])

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

    assert result.meta_description == "A great site"
    assert result.favicon_url == "/favicon.ico"


# --- crawl() colors/fonts evaluation failure ---


@pytest.mark.asyncio
async def test_crawl_handles_evaluate_exception():
    """Lines 213-214: Exception handler for colors/fonts evaluation."""
    html_simple = "<html><body><h1>Hello</h1></body></html>"
    mock_page = make_mock_page(html=html_simple)

    call_count = {"n": 0}

    async def evaluate_side_effect(js):
        call_count["n"] += 1
        raise Exception("evaluate failed")

    mock_page.evaluate = evaluate_side_effect

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

    assert result.error == ""
    assert result.colors == []
    assert result.fonts == []
