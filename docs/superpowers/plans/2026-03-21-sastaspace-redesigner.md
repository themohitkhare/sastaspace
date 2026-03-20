# SastaSpace AI Website Redesigner — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI tool that crawls any website URL, feeds it to Claude AI, and serves a beautiful redesigned version at `http://localhost:8080/{subdomain}/`.

**Architecture:** Six focused modules: `config` (settings), `crawler` (Playwright), `redesigner` (Claude API), `deployer` (filesystem + registry), `server` (FastAPI preview server), `cli` (Click entry point). TDD throughout — write tests first, implement to make them pass, commit after each task.

**Tech Stack:** Python 3.11+, uv, Playwright (Chromium), Anthropic SDK, BeautifulSoup4, FastAPI, Uvicorn, Click, Rich, pydantic-settings.

> **Prerequisites (already done in scaffold commit):** `pyproject.toml`, `sastaspace/__init__.py`, `tests/__init__.py`, `.gitignore`, `.env.example`, `Makefile` are already committed. `uv sync` has been run. Start at Task 1.

---

## File Map

| File | Responsibility |
|------|---------------|
| `sastaspace/config.py` | Load settings from `.env` via pydantic-settings |
| `sastaspace/crawler.py` | `CrawlResult` dataclass + async `crawl(url)` function |
| `sastaspace/redesigner.py` | `RedesignError` + `redesign(crawl_result)` → HTML string |
| `sastaspace/deployer.py` | `derive_subdomain()`, `deploy()`, registry management |
| `sastaspace/server.py` | FastAPI app + `ensure_running()` detached subprocess helper |
| `sastaspace/cli.py` | Click command group: redesign, serve, list, open, remove |
| `tests/test_config.py` | Settings load, defaults, missing key |
| `tests/test_crawler.py` | CrawlResult fields, to_prompt_context(), error handling |
| `tests/test_redesigner.py` | HTML cleaning, validity checks, RedesignError |
| `tests/test_deployer.py` | Subdomain derivation, collision, deploy(), registry |
| `tests/test_server.py` | FastAPI routes, index listing |
| `tests/test_cli.py` | CLI commands via Click CliRunner |

---

## Task 1: Configuration (`config.py`)

**Files:**
- Create: `sastaspace/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1.1: Write failing tests**

```python
# tests/test_config.py
import os
import pytest
from sastaspace.config import Settings


def test_settings_load_from_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    s = Settings()
    assert s.anthropic_api_key == "sk-ant-test"


def test_settings_defaults(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    s = Settings()
    assert s.server_port == 8080
    assert s.claude_model == "claude-sonnet-4-20250514"
    assert s.sites_dir.name == "sites"


def test_settings_missing_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(Exception):
        Settings()


def test_settings_override_port(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("SERVER_PORT", "9090")
    s = Settings()
    assert s.server_port == 9090
```

- [ ] **Step 1.2: Run tests — verify they fail**

```bash
uv run pytest tests/test_config.py -v
```
Expected: `ImportError: cannot import name 'Settings'`

- [ ] **Step 1.3: Implement `config.py`**

```python
# sastaspace/config.py
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    anthropic_api_key: str
    sites_dir: Path = Path("./sites")
    server_port: int = 8080
    claude_model: str = "claude-sonnet-4-20250514"
```

- [ ] **Step 1.4: Run tests — verify they pass**

```bash
uv run pytest tests/test_config.py -v
```
Expected: 4 passed

- [ ] **Step 1.5: Commit**

```bash
git add sastaspace/config.py tests/test_config.py
git commit -m "feat: add Settings config via pydantic-settings"
```

---

## Task 2: Crawler (`crawler.py`)

**Files:**
- Create: `sastaspace/crawler.py`
- Create: `tests/test_crawler.py`

- [ ] **Step 2.1: Write failing tests**

We mock Playwright entirely — no real browser needed in tests.

```python
# tests/test_crawler.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
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
    """crawl() should return CrawlResult with error set on failure, containing the exception message."""
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
        url="https://acme.com", title="Acme", meta_description="", favicon_url="",
        html_source="", screenshot_base64="", headings=[], navigation_links=[],
        text_content="", images=[], colors=[], fonts=[], sections=[], error="",
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
        url="https://acme.com", title="Acme", meta_description="", favicon_url="",
        html_source="", screenshot_base64="", headings=[], navigation_links=[],
        text_content=long_text, images=[], colors=[], fonts=[], sections=[], error="",
    )
    ctx = r.to_prompt_context()
    # The text section should not contain more than 5000 x's
    assert ctx.count("x") <= 5000
```

- [ ] **Step 2.2: Run tests — verify they fail**

```bash
uv run pytest tests/test_crawler.py -v
```
Expected: `ImportError: cannot import name 'CrawlResult'`

- [ ] **Step 2.3: Implement `crawler.py`**

```python
# sastaspace/crawler.py
from __future__ import annotations

import asyncio
import base64
import re
import subprocess
import sys
from dataclasses import dataclass, field

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


def _ensure_chromium() -> None:
    """Auto-install Chromium if not present. Runs once, transparent to user."""
    try:
        import playwright._impl._driver as _driver  # noqa: F401
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium", "--dry-run"],
            capture_output=True,
            timeout=10,
        )
        if result.returncode != 0 and b"chromium" in result.stdout.lower():
            # Chromium not found — install it
            subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                check=True,
            )
    except Exception:
        # Best-effort; let Playwright raise its own error if it can't find Chromium
        pass


@dataclass
class CrawlResult:
    url: str
    title: str
    meta_description: str
    favicon_url: str
    html_source: str
    screenshot_base64: str
    headings: list[str] = field(default_factory=list)
    navigation_links: list[dict] = field(default_factory=list)
    text_content: str = ""
    images: list[dict] = field(default_factory=list)
    colors: list[str] = field(default_factory=list)
    fonts: list[str] = field(default_factory=list)
    sections: list[dict] = field(default_factory=list)
    error: str = ""

    def to_prompt_context(self) -> str:
        lines = [
            f"## Page Title\n{self.title}",
            f"## URL\n{self.url}",
        ]
        if self.meta_description:
            lines.append(f"## Meta Description\n{self.meta_description}")
        if self.headings:
            lines.append("## Headings\n" + "\n".join(f"- {h}" for h in self.headings))
        if self.navigation_links:
            nav = "\n".join(f"- {n['text']} → {n['href']}" for n in self.navigation_links)
            lines.append(f"## Navigation\n{nav}")
        if self.text_content:
            lines.append(f"## Main Text Content\n{self.text_content[:5000]}")
        if self.images:
            img_lines = "\n".join(
                f"- src={i['src']} alt={i.get('alt', '')}" for i in self.images[:10]
            )
            lines.append(f"## Images\n{img_lines}")
        if self.colors:
            lines.append("## Detected Colors\n" + ", ".join(self.colors[:10]))
        if self.fonts:
            lines.append("## Detected Fonts\n" + ", ".join(self.fonts[:5]))
        if self.sections:
            for s in self.sections[:5]:
                lines.append(f"## Section: {s.get('heading', 'unnamed')}\n{s.get('content', '')[:500]}")
        return "\n\n".join(lines)


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "iframe"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text[:5000]


def _extract_headings(soup: BeautifulSoup) -> list[str]:
    headings = []
    for tag in soup.find_all(["h1", "h2", "h3", "h4"]):
        text = tag.get_text(strip=True)
        if text:
            headings.append(f"{tag.name}: {text}")
    return headings[:20]


def _extract_nav_links(soup: BeautifulSoup) -> list[dict]:
    links = []
    for nav in soup.find_all(["nav", "header"]):
        for a in nav.find_all("a", href=True):
            text = a.get_text(strip=True)
            href = a["href"]
            if text and href:
                links.append({"text": text, "href": href})
    return links[:15]


def _extract_images(soup: BeautifulSoup) -> list[dict]:
    images = []
    for img in soup.find_all("img", src=True)[:10]:
        images.append({
            "src": img["src"],
            "alt": img.get("alt", ""),
            "width": img.get("width", ""),
            "height": img.get("height", ""),
        })
    return images


def _extract_sections(soup: BeautifulSoup) -> list[dict]:
    sections = []
    for tag in soup.find_all(["section", "article", "main"])[:5]:
        heading_tag = tag.find(["h1", "h2", "h3"])
        heading = heading_tag.get_text(strip=True) if heading_tag else ""
        content = tag.get_text(separator=" ", strip=True)[:500]
        sections.append({"heading": heading, "content": content, "classes": tag.get("class", [])})
    return sections


async def crawl(url: str) -> CrawlResult:
    """Crawl a URL and return a CrawlResult. Sets result.error on failure."""
    _ensure_chromium()

    empty = CrawlResult(
        url=url, title="", meta_description="", favicon_url="",
        html_source="", screenshot_base64="", error=""
    )

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            try:
                ctx = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1280, "height": 800},
                )
                page = await ctx.new_page()

                await page.goto(url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(2)

                title = await page.title()
                html = await page.content()
                screenshot_bytes = await page.screenshot(
                    type="png", clip={"x": 0, "y": 0, "width": 1280, "height": 800}
                )
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode()

                soup = BeautifulSoup(html, "html.parser")

                # Meta description
                meta_desc = ""
                meta_tag = soup.find("meta", attrs={"name": "description"})
                if meta_tag and meta_tag.get("content"):
                    meta_desc = meta_tag["content"]

                # Favicon
                favicon = ""
                link_tag = soup.find("link", rel=lambda r: r and "icon" in r)
                if link_tag and link_tag.get("href"):
                    favicon = link_tag["href"]

                # Colors + fonts via JS evaluation
                try:
                    colors = await page.evaluate("""
                        () => {
                            const els = document.querySelectorAll('*');
                            const colors = new Set();
                            for (let i = 0; i < Math.min(els.length, 50); i++) {
                                const s = window.getComputedStyle(els[i]);
                                if (s.color) colors.add(s.color);
                                if (s.backgroundColor) colors.add(s.backgroundColor);
                            }
                            return Array.from(colors).slice(0, 10);
                        }
                    """) or []
                    fonts = await page.evaluate("""
                        () => {
                            const els = document.querySelectorAll('*');
                            const fonts = new Set();
                            for (let i = 0; i < Math.min(els.length, 30); i++) {
                                const s = window.getComputedStyle(els[i]);
                                if (s.fontFamily) fonts.add(s.fontFamily.split(',')[0].trim());
                            }
                            return Array.from(fonts).slice(0, 5);
                        }
                    """) or []
                except Exception:
                    colors, fonts = [], []

                return CrawlResult(
                    url=url,
                    title=title,
                    meta_description=meta_desc,
                    favicon_url=favicon,
                    html_source=html,
                    screenshot_base64=screenshot_b64,
                    headings=_extract_headings(soup),
                    navigation_links=_extract_nav_links(soup),
                    text_content=_extract_text(html),
                    images=_extract_images(soup),
                    colors=list(colors),
                    fonts=list(fonts),
                    sections=_extract_sections(soup),
                    error="",
                )
            finally:
                await browser.close()

    except Exception as exc:
        empty.error = str(exc)
        return empty
```

- [ ] **Step 2.4: Run tests — verify they pass**

```bash
uv run pytest tests/test_crawler.py -v
```
Expected: All tests pass

- [ ] **Step 2.5: Lint**

```bash
uv run ruff check sastaspace/crawler.py tests/test_crawler.py --fix
uv run ruff format sastaspace/crawler.py tests/test_crawler.py
```

- [ ] **Step 2.6: Commit**

```bash
git add sastaspace/crawler.py tests/test_crawler.py
git commit -m "feat: add Playwright crawler with CrawlResult dataclass"
```

---

## Task 3: Redesigner (`redesigner.py`)

**Files:**
- Create: `sastaspace/redesigner.py`
- Create: `tests/test_redesigner.py`

- [ ] **Step 3.1: Write failing tests**

```python
# tests/test_redesigner.py
import pytest
from unittest.mock import MagicMock, patch
from sastaspace.crawler import CrawlResult
from sastaspace.redesigner import RedesignError, redesign

SAMPLE_HTML = """<!DOCTYPE html>
<html lang="en">
<head><title>Test</title></head>
<body><h1>Hello</h1></body>
</html>"""


def make_crawl_result(url="https://acme.com", title="Acme"):
    return CrawlResult(
        url=url, title=title, meta_description="", favicon_url="",
        html_source="<html></html>", screenshot_base64="abc",
        headings=["h1: Hello"], navigation_links=[], text_content="Hello",
        images=[], colors=[], fonts=[], sections=[], error="",
    )


def make_mock_anthropic(response_text: str):
    mock_client = MagicMock()
    mock_msg = MagicMock()
    mock_content = MagicMock()
    mock_content.text = response_text
    mock_msg.content = [mock_content]
    mock_client.messages.create.return_value = mock_msg
    return mock_client


# --- HTML cleaning tests (no API call needed) ---

def test_strips_markdown_fences():
    """redesign() strips ```html ... ``` wrapping."""
    wrapped = f"```html\n{SAMPLE_HTML}\n```"
    mock_client = make_mock_anthropic(wrapped)

    with patch("sastaspace.redesigner.anthropic.Anthropic", return_value=mock_client):
        result = redesign(make_crawl_result(), api_key="sk-test")

    assert result.startswith("<!DOCTYPE html>")
    assert "```" not in result


def test_strips_generic_fences():
    wrapped = f"```\n{SAMPLE_HTML}\n```"
    mock_client = make_mock_anthropic(wrapped)

    with patch("sastaspace.redesigner.anthropic.Anthropic", return_value=mock_client):
        result = redesign(make_crawl_result(), api_key="sk-test")

    assert "```" not in result


def test_valid_html_passes_through():
    mock_client = make_mock_anthropic(SAMPLE_HTML)

    with patch("sastaspace.redesigner.anthropic.Anthropic", return_value=mock_client):
        result = redesign(make_crawl_result(), api_key="sk-test")

    assert "<!DOCTYPE html>" in result
    assert "</html>" in result


# --- Validity check tests ---

def test_raises_on_empty_response():
    mock_client = make_mock_anthropic("")

    with patch("sastaspace.redesigner.anthropic.Anthropic", return_value=mock_client):
        with pytest.raises(RedesignError, match="empty"):
            redesign(make_crawl_result(), api_key="sk-test")


def test_raises_on_missing_doctype():
    mock_client = make_mock_anthropic("<html><body>Hi</body></html>")

    with patch("sastaspace.redesigner.anthropic.Anthropic", return_value=mock_client):
        with pytest.raises(RedesignError, match="DOCTYPE"):
            redesign(make_crawl_result(), api_key="sk-test")


def test_raises_on_missing_closing_html_tag():
    truncated = "<!DOCTYPE html>\n<html><body>Cut off mid way..."

    mock_client = make_mock_anthropic(truncated)

    with patch("sastaspace.redesigner.anthropic.Anthropic", return_value=mock_client):
        with pytest.raises(RedesignError, match="</html>"):
            redesign(make_crawl_result(), api_key="sk-test")


def test_raises_on_crawl_error():
    """redesign() raises before calling the API when CrawlResult.error is set."""
    bad_result = make_crawl_result()
    bad_result.error = "Timeout"

    mock_client = MagicMock()
    with patch("sastaspace.redesigner.anthropic.Anthropic", return_value=mock_client):
        with pytest.raises(RedesignError, match="crawl failed"):
            redesign(bad_result, api_key="sk-test")

    mock_client.messages.create.assert_not_called()


# --- API call shape tests ---

def test_api_call_includes_image_and_text_blocks():
    mock_client = make_mock_anthropic(SAMPLE_HTML)

    with patch("sastaspace.redesigner.anthropic.Anthropic", return_value=mock_client):
        redesign(make_crawl_result(), api_key="sk-test")

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["max_tokens"] == 16000
    content = call_kwargs["messages"][0]["content"]
    types = [block["type"] for block in content]
    assert "image" in types
    assert "text" in types


def test_api_call_skips_image_block_when_no_screenshot():
    """When screenshot_base64 is empty, only a text block is sent."""
    crawl_no_screenshot = make_crawl_result()
    crawl_no_screenshot.screenshot_base64 = ""

    mock_client = make_mock_anthropic(SAMPLE_HTML)

    with patch("sastaspace.redesigner.anthropic.Anthropic", return_value=mock_client):
        redesign(crawl_no_screenshot, api_key="sk-test")

    content = mock_client.messages.create.call_args.kwargs["messages"][0]["content"]
    types = [block["type"] for block in content]
    assert "image" not in types
    assert "text" in types
```

- [ ] **Step 3.2: Run tests — verify they fail**

```bash
uv run pytest tests/test_redesigner.py -v
```
Expected: `ImportError: cannot import name 'RedesignError'`

- [ ] **Step 3.3: Implement `redesigner.py`**

```python
# sastaspace/redesigner.py
from __future__ import annotations

import re

import anthropic

from sastaspace.crawler import CrawlResult

SYSTEM_PROMPT = """You are SastaSpace AI — the world's best website redesigner.

Design Principles:
1. Modern & Clean — generous whitespace, clear typography, subtle shadows, smooth gradients
2. Preserve Content — keep ALL original text, links, messaging. Don't invent copy.
3. Preserve Brand — use original color palette (improve subtly). Keep personality.
4. Mobile-First — fully responsive design
5. Performance — single HTML file, inline CSS, no external deps except Google Fonts
6. Professional — output should look like a $5,000 website

Technical Requirements:
- Single complete HTML file with all CSS in a <style> tag
- Google Fonts via @import (1-2 fonts max)
- CSS Grid + Flexbox for layout
- Smooth scroll, subtle animations (fade-in, hover effects)
- Responsive hamburger menu for mobile
- Semantic HTML5 (header, nav, main, section, footer)
- CSS custom properties for theming
- Keep original image URLs from source site
- Include a "Redesigned by SastaSpace.com" badge in footer with link

Do NOT:
- Add fake content not on the original site
- Use Bootstrap, Tailwind CDN, or any CSS framework
- Use external JS libraries
- Output anything except the raw HTML"""

USER_PROMPT_TEMPLATE = """Redesign this website into a modern, beautiful single-page HTML file.

## Original Website Data:
{crawl_context}

## Original Page Title: {title}
## Original Meta Description: {meta_description}
## Detected Color Palette: {colors}
## Detected Fonts: {fonts}

Instructions:
1. Analyze the content structure from the screenshot and extracted data
2. Create a complete modern redesign as a SINGLE HTML file
3. Keep all original content but reorganize it beautifully
4. Output ONLY the HTML code — no explanations, just raw HTML starting with <!DOCTYPE html>"""


class RedesignError(Exception):
    """Raised when Claude returns invalid or unexpected output."""


def _clean_html(raw: str) -> str:
    """Strip markdown code fences and leading/trailing whitespace."""
    raw = raw.strip()
    # Strip ```html ... ``` or ``` ... ```
    raw = re.sub(r"^```(?:html)?\s*\n?", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\n?```\s*$", "", raw, flags=re.IGNORECASE)
    return raw.strip()


def _validate_html(html: str) -> None:
    """Raise RedesignError if the HTML looks truncated or malformed."""
    if not html:
        raise RedesignError("Claude returned an empty response")
    if "<!doctype html" not in html.lower():
        raise RedesignError(
            "Response missing <!DOCTYPE html> declaration — output may not be valid HTML"
        )
    if "</html>" not in html.lower():
        raise RedesignError(
            "Response missing closing </html> tag — output appears to be truncated"
        )


def redesign(crawl_result: CrawlResult, api_key: str, model: str = "claude-sonnet-4-20250514") -> str:
    """
    Call Claude API with screenshot + crawl data and return a redesigned HTML string.

    Raises:
        RedesignError: if crawl_result.error is set or Claude's output is invalid.
    """
    if crawl_result.error:
        raise RedesignError(f"Cannot redesign — crawl failed: {crawl_result.error}")

    client = anthropic.Anthropic(api_key=api_key)

    user_text = USER_PROMPT_TEMPLATE.format(
        crawl_context=crawl_result.to_prompt_context(),
        title=crawl_result.title,
        meta_description=crawl_result.meta_description,
        colors=", ".join(crawl_result.colors[:10]) or "not detected",
        fonts=", ".join(crawl_result.fonts[:5]) or "not detected",
    )

    content: list[dict] = []

    if crawl_result.screenshot_base64:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": crawl_result.screenshot_base64,
            },
        })

    content.append({"type": "text", "text": user_text})

    message = client.messages.create(
        model=model,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
    )

    raw = message.content[0].text
    html = _clean_html(raw)
    _validate_html(html)
    return html
```

- [ ] **Step 3.4: Run tests — verify they pass**

```bash
uv run pytest tests/test_redesigner.py -v
```
Expected: All tests pass

- [ ] **Step 3.5: Lint**

```bash
uv run ruff check sastaspace/redesigner.py tests/test_redesigner.py --fix
uv run ruff format sastaspace/redesigner.py tests/test_redesigner.py
```

- [ ] **Step 3.6: Commit**

```bash
git add sastaspace/redesigner.py tests/test_redesigner.py
git commit -m "feat: add Claude API redesign engine with HTML validation"
```

---

## Task 4: Deployer (`deployer.py`)

**Files:**
- Create: `sastaspace/deployer.py`
- Create: `tests/test_deployer.py`

- [ ] **Step 4.1: Write failing tests**

```python
# tests/test_deployer.py
import json
import pytest
from pathlib import Path
from sastaspace.deployer import (
    DeployResult,
    derive_subdomain,
    deploy,
    load_registry,
)

SAMPLE_HTML = "<!DOCTYPE html><html><body>hi</body></html>"


# --- derive_subdomain tests ---

def test_derive_subdomain_simple():
    assert derive_subdomain("https://acme.com") == "acme-com"


def test_derive_subdomain_strips_www():
    assert derive_subdomain("https://www.acme.com") == "acme-com"


def test_derive_subdomain_complex():
    result = derive_subdomain("https://www.acme-corp.co.uk/shop")
    assert result == "acme-corp-co-uk"


def test_derive_subdomain_lowercase():
    assert derive_subdomain("https://MYSITE.COM") == "mysite-com"


def test_derive_subdomain_truncates_long():
    long_url = "https://this-is-a-very-long-domain-name-that-exceeds-fifty-characters.com"
    result = derive_subdomain(long_url)
    assert len(result) <= 50


def test_derive_subdomain_no_trailing_hyphens():
    result = derive_subdomain("https://acme.com/")
    assert not result.endswith("-")
    assert not result.startswith("-")


# --- deploy() tests ---

def test_deploy_creates_index_html(tmp_path):
    result = deploy(
        url="https://acme.com",
        html=SAMPLE_HTML,
        sites_dir=tmp_path,
    )
    index = tmp_path / result.subdomain / "index.html"
    assert index.exists()
    assert index.read_text() == SAMPLE_HTML


def test_deploy_creates_metadata_json(tmp_path):
    result = deploy(url="https://acme.com", html=SAMPLE_HTML, sites_dir=tmp_path)
    meta_path = tmp_path / result.subdomain / "metadata.json"
    assert meta_path.exists()
    meta = json.loads(meta_path.read_text())
    assert meta["original_url"] == "https://acme.com"
    assert meta["subdomain"] == result.subdomain
    assert "timestamp" in meta


def test_deploy_updates_registry(tmp_path):
    deploy(url="https://acme.com", html=SAMPLE_HTML, sites_dir=tmp_path)
    deploy(url="https://beta.com", html=SAMPLE_HTML, sites_dir=tmp_path)
    registry = load_registry(tmp_path)
    subdomains = [e["subdomain"] for e in registry]
    assert "acme-com" in subdomains
    assert "beta-com" in subdomains


def test_deploy_collision_appends_suffix(tmp_path):
    r1 = deploy(url="https://acme.com", html=SAMPLE_HTML, sites_dir=tmp_path)
    r2 = deploy(url="https://acme.com", html=SAMPLE_HTML, sites_dir=tmp_path)
    assert r1.subdomain != r2.subdomain
    assert r2.subdomain.startswith("acme-com")


def test_deploy_returns_deploy_result(tmp_path):
    result = deploy(url="https://acme.com", html=SAMPLE_HTML, sites_dir=tmp_path)
    assert hasattr(result, "subdomain")
    assert hasattr(result, "index_path")
    assert result.index_path.exists()


def test_deploy_atomic_registry_no_tmp_leftover(tmp_path):
    deploy(url="https://acme.com", html=SAMPLE_HTML, sites_dir=tmp_path)
    tmp_registry = tmp_path / "_registry.json.tmp"
    assert not tmp_registry.exists()


# --- load_registry tests ---

def test_load_registry_returns_empty_list_when_missing(tmp_path):
    registry = load_registry(tmp_path)
    assert registry == []


def test_load_registry_returns_list(tmp_path):
    deploy(url="https://acme.com", html=SAMPLE_HTML, sites_dir=tmp_path)
    registry = load_registry(tmp_path)
    assert isinstance(registry, list)
    assert len(registry) == 1
```

- [ ] **Step 4.2: Run tests — verify they fail**

```bash
uv run pytest tests/test_deployer.py -v
```
Expected: `ImportError: cannot import name 'derive_subdomain'`

- [ ] **Step 4.3: Implement `deployer.py`**

```python
# sastaspace/deployer.py
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


@dataclass
class DeployResult:
    subdomain: str
    index_path: Path
    sites_dir: Path


def derive_subdomain(url: str) -> str:
    """
    Derive a filesystem-safe subdomain slug from a URL.

    https://www.acme-corp.co.uk/shop → acme-corp-co-uk
    """
    parsed = urlparse(url)
    hostname = parsed.hostname or url

    # Strip www. prefix
    if hostname.startswith("www."):
        hostname = hostname[4:]

    # Replace dots and non-alphanumeric chars with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", hostname.lower())

    # Collapse multiple hyphens, strip leading/trailing hyphens
    slug = re.sub(r"-+", "-", slug).strip("-")

    return slug[:50]


def _unique_subdomain(base: str, sites_dir: Path) -> str:
    """Return `base` if available, else `base--2`, `base--3`, ..."""
    candidate = base
    counter = 2
    while (sites_dir / candidate).exists():
        candidate = f"{base}--{counter}"
        counter += 1
    return candidate


def load_registry(sites_dir: Path) -> list[dict]:
    """Load the _registry.json or return empty list."""
    registry_path = sites_dir / "_registry.json"
    if not registry_path.exists():
        return []
    try:
        return json.loads(registry_path.read_text())
    except (json.JSONDecodeError, OSError):
        return []


def save_registry(sites_dir: Path, registry: list[dict]) -> None:
    """Atomically write _registry.json via write-then-rename."""
    tmp_path = sites_dir / "_registry.json.tmp"
    tmp_path.write_text(json.dumps(registry, indent=2))
    os.replace(tmp_path, sites_dir / "_registry.json")


def deploy(url: str, html: str, sites_dir: Path, subdomain: str | None = None) -> DeployResult:
    """
    Write redesigned HTML to sites/{subdomain}/ and update registry.

    Returns DeployResult with final subdomain and path.
    """
    sites_dir.mkdir(parents=True, exist_ok=True)

    base = subdomain if subdomain else derive_subdomain(url)
    final_subdomain = _unique_subdomain(base, sites_dir)

    site_dir = sites_dir / final_subdomain
    site_dir.mkdir(parents=True, exist_ok=True)

    index_path = site_dir / "index.html"
    index_path.write_text(html, encoding="utf-8")

    metadata = {
        "subdomain": final_subdomain,
        "original_url": url,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "deployed",
    }
    (site_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

    registry = load_registry(sites_dir)
    # Upsert by subdomain
    registry = [e for e in registry if e.get("subdomain") != final_subdomain]
    registry.append(metadata)
    save_registry(sites_dir, registry)

    return DeployResult(subdomain=final_subdomain, index_path=index_path, sites_dir=sites_dir)
```

- [ ] **Step 4.4: Run tests — verify they pass**

```bash
uv run pytest tests/test_deployer.py -v
```
Expected: All tests pass

- [ ] **Step 4.5: Lint**

```bash
uv run ruff check sastaspace/deployer.py tests/test_deployer.py --fix
uv run ruff format sastaspace/deployer.py tests/test_deployer.py
```

- [ ] **Step 4.6: Commit**

```bash
git add sastaspace/deployer.py tests/test_deployer.py
git commit -m "feat: add deployer with subdomain derivation and atomic registry"
```

---

## Task 5: Preview Server (`server.py`)

**Files:**
- Create: `sastaspace/server.py`
- Create: `tests/test_server.py`

- [ ] **Step 5.1: Write failing tests**

```python
# tests/test_server.py
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


SAMPLE_HTML = "<!DOCTYPE html><html><body><h1>Acme</h1></body></html>"


def make_test_sites(tmp_path: Path) -> Path:
    """Create a minimal sites/ directory for testing."""
    sites = tmp_path / "sites"
    sites.mkdir()

    # Create one site
    (sites / "acme-com").mkdir()
    (sites / "acme-com" / "index.html").write_text(SAMPLE_HTML)

    # Write registry
    registry = [
        {"subdomain": "acme-com", "original_url": "https://acme.com", "timestamp": "2026-01-01T00:00:00Z", "status": "deployed"},
    ]
    (sites / "_registry.json").write_text(json.dumps(registry))

    return sites


def make_test_client(sites_dir: Path):
    from sastaspace.server import make_app
    app = make_app(sites_dir)
    return TestClient(app)


def test_root_returns_html_listing(tmp_path):
    sites = make_test_sites(tmp_path)
    client = make_test_client(sites)

    resp = client.get("/")
    assert resp.status_code == 200
    assert "acme-com" in resp.text
    assert "text/html" in resp.headers["content-type"]


def test_root_shows_link_to_site(tmp_path):
    sites = make_test_sites(tmp_path)
    client = make_test_client(sites)

    resp = client.get("/")
    assert "https://acme.com" in resp.text or "acme-com" in resp.text


def test_site_route_serves_index_html(tmp_path):
    sites = make_test_sites(tmp_path)
    client = make_test_client(sites)

    resp = client.get("/acme-com/")
    assert resp.status_code == 200
    assert "<h1>Acme</h1>" in resp.text


def test_site_route_without_trailing_slash(tmp_path):
    sites = make_test_sites(tmp_path)
    client = make_test_client(sites)

    # Should redirect or serve correctly
    resp = client.get("/acme-com/", follow_redirects=True)
    assert resp.status_code == 200


def test_unknown_site_returns_404(tmp_path):
    sites = make_test_sites(tmp_path)
    client = make_test_client(sites)

    resp = client.get("/nonexistent/")
    assert resp.status_code == 404


def test_root_with_empty_registry(tmp_path):
    sites = tmp_path / "sites"
    sites.mkdir()
    client = make_test_client(sites)

    resp = client.get("/")
    assert resp.status_code == 200
    assert "No sites" in resp.text


# --- ensure_running() tests ---

def test_ensure_running_returns_port_when_already_listening(tmp_path):
    sites = tmp_path / "sites"
    sites.mkdir()

    with patch("sastaspace.server._is_port_listening", return_value=True):
        # Write existing port file
        (sites / ".server_port").write_text("8080")
        from sastaspace.server import ensure_running
        port = ensure_running(sites, preferred_port=8080)

    assert port == 8080


def test_ensure_running_spawns_subprocess_when_not_listening(tmp_path):
    sites = tmp_path / "sites"
    sites.mkdir()

    call_count = {"n": 0}

    def mock_listening(port):
        # Not listening initially; listening after subprocess is spawned
        call_count["n"] += 1
        return call_count["n"] > 2  # False twice, then True

    mock_popen = MagicMock()

    with (
        patch("sastaspace.server._is_port_listening", side_effect=mock_listening),
        patch("sastaspace.server.subprocess.Popen", return_value=mock_popen) as mock_popen_cls,
        patch("sastaspace.server.time.sleep"),
        patch("sastaspace.server.time.time", side_effect=[0.0, 0.5, 1.0, 10.0]),
    ):
        from sastaspace.server import ensure_running
        port = ensure_running(sites, preferred_port=8080)

    assert mock_popen_cls.called
    port_file = sites / ".server_port"
    assert port_file.exists()
    assert int(port_file.read_text()) == port


def test_ensure_running_tries_next_port_when_in_use(tmp_path):
    sites = tmp_path / "sites"
    sites.mkdir()

    def mock_listening(port):
        # Port 8080 is in use (returns True = listening), 8081 is free
        return port == 8080

    with (
        patch("sastaspace.server._is_port_listening", side_effect=mock_listening),
        patch("sastaspace.server.subprocess.Popen"),
        patch("sastaspace.server.time.sleep"),
        patch("sastaspace.server.time.time", return_value=10.0),  # instant timeout
    ):
        from sastaspace.server import ensure_running
        port = ensure_running(sites, preferred_port=8080)

    # Should have chosen 8081 (8080 was already occupied)
    assert port == 8081
```

- [ ] **Step 5.2: Run tests — verify they fail**

```bash
uv run pytest tests/test_server.py -v
```
Expected: `ImportError: cannot import name 'make_app'`

- [ ] **Step 5.3: Implement `server.py`**

```python
# sastaspace/server.py
from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from starlette.responses import Response

_SITES_DIR: Path = Path("./sites")


def make_app(sites_dir: Path) -> FastAPI:
    """Create the FastAPI app bound to a specific sites directory."""
    app = FastAPI(title="SastaSpace Preview Server")

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        registry_path = sites_dir / "_registry.json"
        registry: list[dict] = []
        if registry_path.exists():
            try:
                registry = json.loads(registry_path.read_text())
            except (json.JSONDecodeError, OSError):
                registry = []

        rows = ""
        for entry in sorted(registry, key=lambda e: e.get("timestamp", ""), reverse=True):
            sub = entry["subdomain"]
            orig = entry.get("original_url", "")
            ts = entry.get("timestamp", "")[:19].replace("T", " ")
            rows += (
                f"<tr>"
                f"<td><a href='/{sub}/'>{sub}</a></td>"
                f"<td><a href='{orig}' target='_blank'>{orig}</a></td>"
                f"<td>{ts}</td>"
                f"</tr>"
            )

        if not rows:
            body = "<p>No sites redesigned yet. Run <code>sastaspace redesign &lt;url&gt;</code></p>"
        else:
            body = f"""
            <table>
              <thead><tr><th>Preview</th><th>Original URL</th><th>Created</th></tr></thead>
              <tbody>{rows}</tbody>
            </table>"""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>SastaSpace — Redesigned Sites</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; }}
    h1 {{ font-size: 1.8rem; margin-bottom: 4px; }}
    p.tagline {{ color: #666; margin-top: 0; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 24px; }}
    th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid #eee; }}
    th {{ background: #f5f5f5; font-weight: 600; }}
    a {{ color: #0066cc; }}
    code {{ background: #f0f0f0; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }}
  </style>
</head>
<body>
  <h1>SastaSpace</h1>
  <p class="tagline">AI Website Redesigner — local preview server</p>
  {body}
</body>
</html>"""

    @app.get("/{subdomain}/")
    async def serve_site(subdomain: str) -> Response:
        index_path = sites_dir / subdomain / "index.html"
        if not index_path.exists():
            return HTMLResponse(
                f"<h1>404</h1><p>No redesign found for <code>{subdomain}</code></p>",
                status_code=404,
            )
        return FileResponse(str(index_path), media_type="text/html")

    @app.get("/{subdomain}/{path:path}")
    async def serve_site_asset(subdomain: str, path: str) -> Response:
        asset_path = sites_dir / subdomain / path
        if asset_path.exists() and asset_path.is_file():
            return FileResponse(str(asset_path))
        # Fall back to index.html for SPA-style routing
        index_path = sites_dir / subdomain / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path), media_type="text/html")
        return HTMLResponse("<h1>404</h1>", status_code=404)

    return app


def _is_port_listening(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def ensure_running(sites_dir: Path, preferred_port: int = 8080) -> int:
    """
    Ensure the preview server is running. Returns the resolved port.

    If not running, spawns a detached uvicorn subprocess.
    Saves the resolved port to sites_dir/.server_port.
    """
    sites_dir.mkdir(parents=True, exist_ok=True)

    # Check if already running on preferred port
    port_file = sites_dir / ".server_port"
    if port_file.exists():
        try:
            existing_port = int(port_file.read_text().strip())
            if _is_port_listening(existing_port):
                return existing_port
        except (ValueError, OSError):
            pass

    # Find a free port
    port = preferred_port
    for candidate in [preferred_port, preferred_port + 1, preferred_port + 2]:
        if not _is_port_listening(candidate):
            port = candidate
            break

    log_file = sites_dir / ".server.log"
    env = {
        "SASTASPACE_SITES_DIR": str(sites_dir.resolve()),
    }

    import os
    full_env = {**os.environ, **env}

    subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "sastaspace.server:app",
            "--host", "127.0.0.1",
            "--port", str(port),
        ],
        stdout=open(log_file, "a"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
        env=full_env,
    )

    # Poll until ready (max 5s)
    deadline = time.time() + 5.0
    while time.time() < deadline:
        if _is_port_listening(port):
            break
        time.sleep(0.2)

    port_file.write_text(str(port))
    return port


# Default app instance (used by uvicorn when spawned as subprocess)
# Sites dir can be overridden via SASTASPACE_SITES_DIR env var
import os as _os

_default_sites_dir = Path(_os.environ.get("SASTASPACE_SITES_DIR", "./sites"))
app = make_app(_default_sites_dir)
```

- [ ] **Step 5.4: Run tests — verify they pass**

```bash
uv run pytest tests/test_server.py -v
```
Expected: All tests pass

- [ ] **Step 5.5: Lint**

```bash
uv run ruff check sastaspace/server.py tests/test_server.py --fix
uv run ruff format sastaspace/server.py tests/test_server.py
```

- [ ] **Step 5.6: Commit**

```bash
git add sastaspace/server.py tests/test_server.py
git commit -m "feat: add FastAPI preview server with ensure_running()"
```

---

## Task 6: CLI (`cli.py`)

**Files:**
- Create: `sastaspace/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 6.1: Write failing tests**

```python
# tests/test_cli.py
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from click.testing import CliRunner
from sastaspace.cli import main

SAMPLE_HTML = "<!DOCTYPE html><html><body><h1>Hi</h1></body></html>"


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def sites_dir(tmp_path):
    d = tmp_path / "sites"
    d.mkdir()
    return d


def make_mock_crawl_result(url="https://acme.com"):
    from sastaspace.crawler import CrawlResult
    return CrawlResult(
        url=url, title="Acme", meta_description="", favicon_url="",
        html_source="<html></html>", screenshot_base64="abc",
        headings=[], navigation_links=[], text_content="Hello",
        images=[], colors=[], fonts=[], sections=[], error="",
    )


# --- list command ---

def test_list_empty(runner, sites_dir):
    result = runner.invoke(main, ["list", "--sites-dir", str(sites_dir)])
    assert result.exit_code == 0
    assert "No sites" in result.output or result.output.strip()


def test_list_shows_deployed_sites(runner, sites_dir):
    # Manually create a site entry
    (sites_dir / "acme-com").mkdir()
    registry = [{"subdomain": "acme-com", "original_url": "https://acme.com", "timestamp": "2026-01-01T00:00:00Z", "status": "deployed"}]
    (sites_dir / "_registry.json").write_text(json.dumps(registry))

    result = runner.invoke(main, ["list", "--sites-dir", str(sites_dir)])
    assert result.exit_code == 0
    assert "acme-com" in result.output


# --- remove command ---

def test_remove_existing_site(runner, sites_dir):
    (sites_dir / "acme-com").mkdir()
    registry = [{"subdomain": "acme-com", "original_url": "https://acme.com", "timestamp": "T", "status": "deployed"}]
    (sites_dir / "_registry.json").write_text(json.dumps(registry))

    result = runner.invoke(main, ["remove", "acme-com", "--sites-dir", str(sites_dir)], input="y\n")
    assert result.exit_code == 0
    assert not (sites_dir / "acme-com").exists()


def test_remove_nonexistent_site(runner, sites_dir):
    result = runner.invoke(main, ["remove", "ghost", "--sites-dir", str(sites_dir)], input="y\n")
    assert result.exit_code != 0
    assert "not found" in result.output.lower() or "ghost" in result.output


def test_open_command(runner, sites_dir, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    with (
        patch("sastaspace.cli.ensure_running", return_value=8080),
        patch("sastaspace.cli.webbrowser.open") as mock_open,
    ):
        result = runner.invoke(main, ["open", "acme-com", "--sites-dir", str(sites_dir)])

    assert result.exit_code == 0
    mock_open.assert_called_once()
    assert "acme-com" in mock_open.call_args[0][0]


def test_serve_command_calls_subprocess(runner, sites_dir, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    with patch("sastaspace.cli.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = runner.invoke(main, ["serve", "--sites-dir", str(sites_dir)])

    assert mock_run.called
    cmd = " ".join(mock_run.call_args[0][0])
    assert "uvicorn" in cmd


# --- redesign command ---

def test_redesign_full_pipeline(runner, sites_dir, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    mock_crawl = AsyncMock(return_value=make_mock_crawl_result())
    mock_redesign = MagicMock(return_value=SAMPLE_HTML)
    mock_ensure = MagicMock(return_value=8080)

    with (
        patch("sastaspace.cli.crawl", mock_crawl),
        patch("sastaspace.cli.redesign", mock_redesign),
        patch("sastaspace.cli.ensure_running", mock_ensure),
        patch("sastaspace.cli.webbrowser.open"),
    ):
        result = runner.invoke(
            main,
            ["redesign", "https://acme.com", "--sites-dir", str(sites_dir), "--no-open"],
        )

    assert result.exit_code == 0, result.output
    assert (sites_dir / "acme-com" / "index.html").exists()


def test_redesign_shows_error_on_crawl_failure(runner, sites_dir, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    from sastaspace.crawler import CrawlResult
    failed_result = CrawlResult(
        url="https://bad.com", title="", meta_description="", favicon_url="",
        html_source="", screenshot_base64="", headings=[], navigation_links=[],
        text_content="", images=[], colors=[], fonts=[], sections=[],
        error="Could not connect",
    )
    mock_crawl = AsyncMock(return_value=failed_result)

    with patch("sastaspace.cli.crawl", mock_crawl):
        result = runner.invoke(
            main,
            ["redesign", "https://bad.com", "--sites-dir", str(sites_dir)],
        )

    assert result.exit_code != 0
    assert "Could not connect" in result.output


def test_redesign_custom_subdomain(runner, sites_dir, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    mock_crawl = AsyncMock(return_value=make_mock_crawl_result())
    mock_redesign = MagicMock(return_value=SAMPLE_HTML)
    mock_ensure = MagicMock(return_value=8080)

    with (
        patch("sastaspace.cli.crawl", mock_crawl),
        patch("sastaspace.cli.redesign", mock_redesign),
        patch("sastaspace.cli.ensure_running", mock_ensure),
        patch("sastaspace.cli.webbrowser.open"),
    ):
        result = runner.invoke(
            main,
            ["redesign", "https://acme.com", "-s", "myacme", "--sites-dir", str(sites_dir), "--no-open"],
        )

    assert result.exit_code == 0, result.output
    assert (sites_dir / "myacme" / "index.html").exists()
```

- [ ] **Step 6.2: Run tests — verify they fail**

```bash
uv run pytest tests/test_cli.py -v
```
Expected: `ImportError: cannot import name 'main'`

- [ ] **Step 6.3: Implement `cli.py`**

```python
# sastaspace/cli.py
from __future__ import annotations

import asyncio
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from sastaspace.crawler import crawl
from sastaspace.deployer import deploy, load_registry, save_registry
from sastaspace.redesigner import RedesignError, redesign
from sastaspace.server import ensure_running

console = Console()

DEFAULT_SITES_DIR = Path("./sites")


@click.group()
def main() -> None:
    """SastaSpace — AI Website Redesigner"""


@main.command()
@click.argument("url")
@click.option("-s", "--subdomain", default=None, help="Custom subdomain slug")
@click.option("--no-open", is_flag=True, default=False, help="Skip opening browser")
@click.option("--sites-dir", type=click.Path(), default=None)
def redesign_cmd(url: str, subdomain: str | None, no_open: bool, sites_dir: str | None) -> None:
    """Crawl, redesign, and deploy a website. Opens a local preview."""
    sites = Path(sites_dir) if sites_dir else DEFAULT_SITES_DIR

    try:
        cfg = _load_config()
    except Exception as e:
        console.print(Panel(f"[red]Configuration error:[/red] {e}\n\nCreate a .env file with ANTHROPIC_API_KEY=sk-ant-...", title="Error"))
        raise SystemExit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Step 1: Crawl
        task = progress.add_task("Crawling website...", total=None)
        try:
            crawl_result = asyncio.run(crawl(url))
        except Exception as e:
            progress.stop()
            console.print(Panel(f"[red]Crawl failed:[/red] {e}", title="Error"))
            raise SystemExit(1)

        if crawl_result.error:
            progress.stop()
            console.print(Panel(
                f"[red]Could not crawl {url}[/red]\n\n{crawl_result.error}\n\nIs the site accessible?",
                title="Crawl Error",
            ))
            raise SystemExit(1)

        progress.update(task, description=f"Crawled [bold]{crawl_result.title or url}[/bold] ✓")

        # Step 2: Redesign
        progress.update(task, description="Redesigning with Claude AI (this takes ~30s)...")
        try:
            html = redesign(crawl_result, api_key=cfg.anthropic_api_key, model=cfg.claude_model)
        except RedesignError as e:
            progress.stop()
            console.print(Panel(f"[red]Redesign failed:[/red] {e}", title="Error"))
            raise SystemExit(1)
        except Exception as e:
            progress.stop()
            console.print(Panel(
                f"[red]Claude API error:[/red] {e}\n\nCheck your ANTHROPIC_API_KEY in .env",
                title="API Error",
            ))
            raise SystemExit(1)

        progress.update(task, description="Redesign complete ✓")

        # Step 3: Deploy
        progress.update(task, description="Deploying to local preview...")
        result = deploy(url=url, html=html, sites_dir=sites, subdomain=subdomain)
        progress.update(task, description=f"Deployed → {result.subdomain} ✓")

        # Step 4: Start server
        progress.update(task, description="Starting preview server...")
        port = ensure_running(sites_dir=sites, preferred_port=cfg.server_port)
        preview_url = f"http://localhost:{port}/{result.subdomain}/"
        progress.update(task, description="Server ready ✓")

    console.print()
    console.print(Panel(
        f"[bold green]Redesign complete![/bold green]\n\n"
        f"Preview: [link={preview_url}]{preview_url}[/link]\n"
        f"Original: {url}",
        title="SastaSpace",
    ))

    if not no_open:
        webbrowser.open(preview_url)


# Register redesign_cmd as "redesign"
main.add_command(redesign_cmd, name="redesign")


@main.command("list")
@click.option("--sites-dir", type=click.Path(), default=None)
def list_cmd(sites_dir: str | None) -> None:
    """List all deployed redesigns."""
    sites = Path(sites_dir) if sites_dir else DEFAULT_SITES_DIR
    registry = load_registry(sites)

    if not registry:
        console.print("[dim]No sites redesigned yet. Run:[/dim] sastaspace redesign <url>")
        return

    table = Table(title="Deployed Redesigns", show_header=True)
    table.add_column("Subdomain", style="bold cyan")
    table.add_column("Original URL")
    table.add_column("Created")
    table.add_column("Status")

    for entry in sorted(registry, key=lambda e: e.get("timestamp", ""), reverse=True):
        table.add_row(
            entry["subdomain"],
            entry.get("original_url", ""),
            entry.get("timestamp", "")[:19].replace("T", " "),
            entry.get("status", ""),
        )

    console.print(table)


@main.command("open")
@click.argument("subdomain")
@click.option("--sites-dir", type=click.Path(), default=None)
def open_cmd(subdomain: str, sites_dir: str | None) -> None:
    """Open a deployed site in the browser."""
    sites = Path(sites_dir) if sites_dir else DEFAULT_SITES_DIR
    cfg = _load_config()
    port = ensure_running(sites_dir=sites, preferred_port=cfg.server_port)
    url = f"http://localhost:{port}/{subdomain}/"
    console.print(f"Opening [link={url}]{url}[/link]")
    webbrowser.open(url)


@main.command("remove")
@click.argument("subdomain")
@click.option("--sites-dir", type=click.Path(), default=None)
def remove_cmd(subdomain: str, sites_dir: str | None) -> None:
    """Remove a deployed site."""
    sites = Path(sites_dir) if sites_dir else DEFAULT_SITES_DIR
    site_path = sites / subdomain

    if not site_path.exists():
        console.print(f"[red]Not found:[/red] {subdomain}")
        raise SystemExit(1)

    click.confirm(f"Remove {subdomain}?", abort=True)

    shutil.rmtree(site_path)

    # Update registry (save_registry imported at top of module)
    registry = load_registry(sites)
    registry = [e for e in registry if e.get("subdomain") != subdomain]
    save_registry(sites, registry)

    console.print(f"[green]Removed:[/green] {subdomain}")


@main.command("serve")
@click.option("--sites-dir", type=click.Path(), default=None)
def serve_cmd(sites_dir: str | None) -> None:
    """Start the preview server in the foreground (streams logs)."""
    sites = Path(sites_dir) if sites_dir else DEFAULT_SITES_DIR
    sites.mkdir(parents=True, exist_ok=True)
    cfg = _load_config()

    import os
    env = {**os.environ, "SASTASPACE_SITES_DIR": str(sites.resolve())}

    console.print(f"Starting preview server at [bold]http://localhost:{cfg.server_port}[/bold]")
    console.print("Press Ctrl+C to stop.\n")

    subprocess.run(
        [
            sys.executable, "-m", "uvicorn",
            "sastaspace.server:app",
            "--host", "127.0.0.1",
            "--port", str(cfg.server_port),
            "--reload",
        ],
        env=env,
    )


def _load_config():
    from sastaspace.config import Settings

    return Settings()
```

- [ ] **Step 6.4: Run tests — verify they pass**

```bash
uv run pytest tests/test_cli.py -v
```
Expected: All tests pass

- [ ] **Step 6.5: Lint**

```bash
uv run ruff check sastaspace/cli.py tests/test_cli.py --fix
uv run ruff format sastaspace/cli.py tests/test_cli.py
```

- [ ] **Step 6.6: Commit**

```bash
git add sastaspace/cli.py tests/test_cli.py
git commit -m "feat: add Click CLI with redesign, list, open, remove, serve commands"
```

---

## Task 7: Full Test Suite + README

**Files:**
- Modify: `Makefile`
- Create: `README.md`

- [ ] **Step 7.1: Run full test suite**

```bash
uv run pytest tests/ -v
```
Expected: All tests pass (no failures)

- [ ] **Step 7.2: Run lint across all files**

```bash
uv run ruff check sastaspace/ tests/
uv run ruff format --check sastaspace/ tests/
```

Fix any issues before proceeding.

- [ ] **Step 7.3: Update Makefile**

Update `Makefile` to remove the "allow empty tests" workaround now that tests exist:

```makefile
.PHONY: ci install lint test

install:
	uv sync
	uv run playwright install chromium

lint:
	uv run ruff check sastaspace/ tests/
	uv run ruff format --check sastaspace/ tests/

test:
	uv run pytest tests/ -v

ci: lint test
```

- [ ] **Step 7.4: Write README**

Create `README.md`:

```markdown
# SastaSpace — AI Website Redesigner

Enter any website URL → get a beautiful AI-redesigned version in your browser in under 60 seconds.

## Quick Start

```bash
# 1. Install dependencies
uv sync
uv run playwright install chromium

# 2. Configure
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 3. Redesign a website
sastaspace redesign https://example.com
```

## Commands

| Command | Description |
|---------|-------------|
| `sastaspace redesign <url>` | Full pipeline: crawl → AI redesign → preview |
| `sastaspace redesign <url> -s myname` | Use custom subdomain |
| `sastaspace redesign <url> --no-open` | Skip auto-opening browser |
| `sastaspace list` | List all redesigned sites |
| `sastaspace open <subdomain>` | Open a site in browser |
| `sastaspace remove <subdomain>` | Remove a site |
| `sastaspace serve` | Start preview server (foreground) |

## How It Works

1. **Crawl** — Playwright headless browser renders the target site, extracts content + screenshot
2. **Redesign** — Claude AI analyzes screenshot + content, generates a modern single-file HTML redesign
3. **Deploy** — HTML saved to `sites/{subdomain}/index.html`
4. **Serve** — FastAPI server at `http://localhost:8080` serves all redesigns

## Configuration (.env)

```env
ANTHROPIC_API_KEY=sk-ant-...  # Required
SITES_DIR=./sites             # Where to save redesigns (default: ./sites)
SERVER_PORT=8080              # Preview server port (default: 8080)
CLAUDE_MODEL=claude-sonnet-4-20250514  # Claude model (default)
```
```

- [ ] **Step 7.5: Run `make ci` to verify everything passes**

```bash
make ci
```
Expected: lint passes, all tests pass

- [ ] **Step 7.6: Final commit**

```bash
git add Makefile README.md
git commit -m "chore: finalize Makefile, add README"
```

---

## Task 8: End-to-End Smoke Test (Manual)

This task verifies the CLI works for real. Requires a valid `ANTHROPIC_API_KEY` in `.env`.

- [ ] **Step 8.1: Create `.env`**

```bash
cp .env.example .env
# Edit .env — add your real ANTHROPIC_API_KEY
```

- [ ] **Step 8.2: Install CLI in editable mode**

```bash
uv pip install -e .
```

- [ ] **Step 8.3: Run a real redesign**

```bash
sastaspace redesign https://example.com --no-open
```

Expected:
- Spinner shows "Crawling...", "Redesigning...", "Deploying...", "Server ready ✓"
- Panel shows preview URL

- [ ] **Step 8.4: Verify the output file**

```bash
ls sites/
cat sites/example-com/index.html | head -5
```

Expected: `sites/example-com/index.html` starts with `<!DOCTYPE html>`

- [ ] **Step 8.5: Check the list command**

```bash
sastaspace list
```

Expected: table showing `example-com` with original URL and timestamp

- [ ] **Step 8.6: Open the preview**

```bash
sastaspace open example-com
```

Expected: browser opens to `http://localhost:8080/example-com/` showing the redesigned page

- [ ] **Step 8.7: Remove the test site**

```bash
sastaspace remove example-com
```

Expected: confirms deletion, `sites/example-com/` no longer exists

- [ ] **Step 8.8: Commit if any fixes were needed**

```bash
git add -A && git commit -m "fix: address issues found during e2e smoke test"
```

---

## Definition of Done

- [ ] `make ci` passes (lint + all unit tests)
- [ ] `sastaspace redesign https://example.com` runs end-to-end without error
- [ ] Generated HTML starts with `<!DOCTYPE html>` and renders correctly in browser
- [ ] `sastaspace list` shows the deployed site
- [ ] `sastaspace remove example-com` cleans up files and registry
- [ ] No unhandled exceptions on bad input
