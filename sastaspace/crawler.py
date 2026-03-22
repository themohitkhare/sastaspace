# sastaspace/crawler.py
from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import logging
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup
from openai import OpenAI
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

# Lazy imports inside enhanced_crawl() to avoid circular import with business_profiler

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# File extensions to skip when filtering links
_DOWNLOAD_EXTENSIONS = frozenset(
    {
        ".pdf",
        ".zip",
        ".tar",
        ".gz",
        ".rar",
        ".7z",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".csv",
        ".exe",
        ".dmg",
        ".iso",
        ".mp3",
        ".mp4",
        ".avi",
        ".mov",
        ".wmv",
        ".flv",
    }
)

# URL path segments to skip (auth/utility pages)
_NOISE_PATH_SEGMENTS = frozenset(
    {
        "/login",
        "/signin",
        "/signup",
        "/register",
        "/logout",
        "/cart",
        "/checkout",
        "/search",
        "/wp-admin",
        "/wp-login",
        "/admin",
        "/auth",
        "/account",
        "/reset-password",
        "/forgot-password",
    }
)


def _ensure_chromium() -> None:
    """Auto-install Chromium if not present. Runs once, transparent to user."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium", "--dry-run"],
            capture_output=True,
            timeout=10,
        )
        if result.returncode != 0 and b"chromium" in result.stdout.lower():
            subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                check=True,
            )
    except Exception:
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
            lines.append(f"## Main Text Content\n{self.text_content[:4999]}")
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
                lines.append(
                    f"## Section: {s.get('heading', 'unnamed')}\n{s.get('content', '')[:500]}"
                )
        return "\n\n".join(lines)


@contextlib.asynccontextmanager
async def _browser_context(browserless_url: str | None = None):
    """Connect to remote Browserless via CDP. Falls back to local launch for dev."""
    async with async_playwright() as pw:
        if browserless_url:
            browser = await pw.chromium.connect_over_cdp(browserless_url)
        else:
            browser = await pw.chromium.launch(headless=True)
        try:
            ctx = await browser.new_context(
                user_agent=_USER_AGENT,
                viewport={"width": 1280, "height": 800},
            )
            page = await ctx.new_page()
            yield browser, ctx, page
        finally:
            await browser.close()


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "iframe"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
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
        images.append(
            {
                "src": img["src"],
                "alt": img.get("alt", ""),
                "width": img.get("width", ""),
                "height": img.get("height", ""),
            }
        )
    return images


def _extract_sections(soup: BeautifulSoup) -> list[dict]:
    sections = []
    for tag in soup.find_all(["section", "article", "main"])[:5]:
        heading_tag = tag.find(["h1", "h2", "h3"])
        heading = heading_tag.get_text(strip=True) if heading_tag else ""
        content = tag.get_text(separator=" ", strip=True)[:500]
        sections.append({"heading": heading, "content": content, "classes": tag.get("class", [])})
    return sections


# --- Part A: Link extraction + filtering ---


def _extract_all_internal_links(html: str, base_url: str) -> list[dict]:
    """Extract all internal links from HTML, deduplicated and capped at 50.

    Returns [{"url": absolute_url, "text": link_text}].
    Skips external links, javascript:, mailto:, tel:, and the base_url itself.
    """
    soup = BeautifulSoup(html, "html.parser")
    parsed_base = urlparse(base_url)
    base_hostname = parsed_base.hostname or ""

    # Normalize the base URL (strip fragment)
    base_normalized = urlunparse(parsed_base._replace(fragment=""))
    # Also normalize without trailing slash for comparison
    base_variants = {base_normalized, base_normalized.rstrip("/")}

    seen_urls: set[str] = set()
    links: list[dict] = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()

        # Skip non-http schemes
        if href.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue

        # Resolve relative URLs
        absolute_url = urljoin(base_url, href)
        parsed = urlparse(absolute_url)

        # Skip external links (different hostname)
        link_hostname = parsed.hostname or ""
        if link_hostname and link_hostname != base_hostname:
            continue

        # Normalize: strip fragment
        normalized = urlunparse(parsed._replace(fragment=""))

        # Skip the base_url itself
        if normalized in base_variants or normalized.rstrip("/") in base_variants:
            continue

        # Deduplicate
        if normalized in seen_urls:
            continue
        seen_urls.add(normalized)

        text = a.get_text(strip=True)
        links.append({"url": normalized, "text": text})

        # Cap at 50
        if len(links) >= 50:
            break

    return links


def _filter_noise_links(links: list[dict], base_url: str) -> list[dict]:
    """Filter out noise links: downloads, auth/utility, pagination, long queries."""
    filtered = []
    for link in links:
        url = link["url"]
        parsed = urlparse(url)
        path = parsed.path.lower()

        # Skip fragment-only (should already be handled, but belt-and-suspenders)
        if not parsed.scheme and not parsed.netloc and url.startswith("#"):
            continue

        # Skip file downloads
        if any(path.endswith(ext) for ext in _DOWNLOAD_EXTENSIONS):
            continue

        # Skip auth/utility paths
        if any(segment in path for segment in _NOISE_PATH_SEGMENTS):
            continue

        # Skip pagination patterns: /page/N or ?page=N
        if re.search(r"/page/\d+", path):
            continue

        # Skip long query strings (tracking URLs)
        if parsed.query and len(parsed.query) > 256:
            continue

        filtered.append(link)

    return filtered


# --- Part B: Refactored _crawl_page ---


async def _crawl_page(page, url: str) -> CrawlResult:
    """Core page extraction logic. Accepts an existing Playwright Page object."""
    await page.goto(url, wait_until="networkidle", timeout=30000)
    await asyncio.sleep(2)

    title = await page.title()
    html = await page.content()
    screenshot_bytes = await page.screenshot(
        type="png", clip={"x": 0, "y": 0, "width": 1280, "height": 800}
    )
    screenshot_b64 = base64.b64encode(screenshot_bytes).decode()

    soup = BeautifulSoup(html, "html.parser")

    meta_desc = ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag and meta_tag.get("content"):
        meta_desc = meta_tag["content"]

    favicon = ""
    link_tag = soup.find("link", rel=lambda r: r and "icon" in r)
    if link_tag and link_tag.get("href"):
        favicon = link_tag["href"]

    try:
        colors = (
            await page.evaluate("""
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
        """)
            or []
        )
        fonts = (
            await page.evaluate("""
            () => {
                const els = document.querySelectorAll('*');
                const fonts = new Set();
                for (let i = 0; i < Math.min(els.length, 30); i++) {
                    const s = window.getComputedStyle(els[i]);
                    if (s.fontFamily) fonts.add(s.fontFamily.split(',')[0].trim());
                }
                return Array.from(fonts).slice(0, 5);
            }
        """)
            or []
        )
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


async def crawl(url: str, browserless_url: str | None = None) -> CrawlResult:
    """Crawl a URL and return a CrawlResult. Sets result.error on failure."""
    if not browserless_url:
        _ensure_chromium()

    empty = CrawlResult(
        url=url,
        title="",
        meta_description="",
        favicon_url="",
        html_source="",
        screenshot_base64="",
        error="",
    )

    try:
        async with _browser_context(browserless_url=browserless_url) as (_browser, _ctx, page):
            return await _crawl_page(page, url)

    except Exception as exc:
        empty.error = str(exc)
        return empty


# --- Part C: Internal page crawl ---


async def _crawl_internal_page(page, url: str):
    """Lightweight crawl for an internal page. No screenshot."""
    from sastaspace.models import PageCrawlResult

    try:
        await page.goto(url, wait_until="networkidle", timeout=30000)

        # Detect auth redirect
        final_url = page.url.lower()
        if any(kw in final_url for kw in ("login", "signin", "auth")):
            return PageCrawlResult(url=url, error="Auth redirect detected")

        title = await page.title()
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        # Extract text (3000 chars max for internal pages)
        for tag in soup(["script", "style", "noscript", "iframe"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text).strip()[:3000]

        # Detect bot protection: very little text content
        if len(text) < 500:
            return PageCrawlResult(url=url, error="Bot protection detected (text < 500 chars)")

        # Extract headings (h1-h4, max 15)
        headings = []
        for tag in soup.find_all(["h1", "h2", "h3", "h4"]):
            h_text = tag.get_text(strip=True)
            if h_text:
                headings.append(f"{tag.name}: {h_text}")
            if len(headings) >= 15:
                break

        # Extract images (first 10)
        images = _extract_images(soup)

        # Extract testimonials
        testimonials = []
        # From <blockquote> tags
        for bq in soup.find_all("blockquote"):
            bq_text = bq.get_text(strip=True)
            if bq_text:
                testimonials.append(bq_text)
        # From elements with testimonial/review/quote classes
        for el in soup.find_all(attrs={"class": True}):
            classes = " ".join(el.get("class", []))
            if any(kw in classes.lower() for kw in ("testimonial", "review", "quote")):
                el_text = el.get_text(strip=True)
                if el_text and el_text not in testimonials:
                    testimonials.append(el_text)

        return PageCrawlResult(
            url=url,
            title=title,
            headings=headings,
            text_content=text,
            images=images,
            testimonials=testimonials,
        )

    except Exception as exc:
        return PageCrawlResult(url=url, error=str(exc))


# --- Part D: LLM page selection ---


def _llm_select_pages(links: list[dict], api_url: str, model: str, api_key: str) -> list[str]:
    """Select the best internal pages to crawl using LLM. Sync function.

    If <= 3 links, returns all URLs. Otherwise asks LLM to pick best 3.
    Falls back to first 3 URLs on any exception.
    """
    urls = [link["url"] for link in links]

    if len(urls) <= 3:
        return urls

    try:
        client = OpenAI(base_url=api_url, api_key=api_key)

        link_list = "\n".join(f"- {link['url']} (text: {link.get('text', '')})" for link in links)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a web analyst. Given a list of internal links from a website, "
                        "pick the 3 pages that would give the most insight into what the business "
                        "does, who they serve, and what makes them unique. "
                        "Return ONLY a JSON array of 3 URLs, nothing else."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Internal links:\n{link_list}",
                },
            ],
            temperature=0,
        )

        content = response.choices[0].message.content or ""
        # Parse JSON array from response
        # Try to find a JSON array in the response
        match = re.search(r"\[.*\]", content, re.DOTALL)
        if match:
            selected = json.loads(match.group())
            # Validate that returned URLs are in the original list
            valid = [u for u in selected if u in urls]
            if valid:
                return valid[:3]

        return urls[:3]

    except Exception:
        return urls[:3]


# --- Part E: enhanced_crawl ---


async def enhanced_crawl(url: str, settings):
    """Crawl homepage + up to 3 internal pages, download assets, build business profile."""
    from sastaspace.asset_downloader import download_and_validate_assets
    from sastaspace.business_profiler import build_business_profile
    from sastaspace.models import EnhancedCrawlResult, PageCrawlResult

    _raw = getattr(settings, "browserless_url", None)
    browserless_url = _raw if isinstance(_raw, str) else None
    if not browserless_url:
        _ensure_chromium()

    try:
        async with _browser_context(browserless_url=browserless_url) as (browser, ctx, page):
            # 1. Crawl homepage
            homepage = await _crawl_page(page, url)

            # If homepage failed, return early
            if homepage.error:
                return EnhancedCrawlResult(homepage=homepage)

            # 2. Extract + filter links
            all_links = _extract_all_internal_links(homepage.html_source, url)
            filtered_links = _filter_noise_links(all_links, url)

            # 3. LLM picks best pages (sync call via to_thread)
            selected_urls = await asyncio.to_thread(
                _llm_select_pages,
                filtered_links,
                settings.claude_code_api_url,
                settings.claude_model,
                settings.claude_code_api_key,
            )

            # 4. Crawl internal pages in parallel with per-page timeout
            async def _safe_crawl_internal(link_url: str) -> PageCrawlResult:
                try:
                    internal_page = await ctx.new_page()
                    try:
                        return await asyncio.wait_for(
                            _crawl_internal_page(internal_page, link_url),
                            timeout=30.0,
                        )
                    finally:
                        await internal_page.close()
                except TimeoutError:
                    return PageCrawlResult(url=link_url, error="Timeout after 30s")
                except Exception as e:
                    return PageCrawlResult(url=link_url, error=str(e))

            internal_pages = list(
                await asyncio.gather(*[_safe_crawl_internal(u) for u in selected_urls])
            )

            # 5. Collect asset URLs from homepage + internal pages
            asset_urls = []
            # From homepage images
            for img in homepage.images:
                src = img.get("src", "")
                if src:
                    asset_urls.append({"url": urljoin(url, src), "source_page": url})
            # From internal page images
            for ipage in internal_pages:
                if hasattr(ipage, "error") and not ipage.error and hasattr(ipage, "images"):
                    for img in ipage.images:
                        src = img.get("src", "")
                        if src:
                            asset_urls.append(
                                {
                                    "url": urljoin(ipage.url, src),
                                    "source_page": ipage.url,
                                }
                            )

            # 6. Download and validate assets
            asset_url_strings = [a["url"] for a in asset_urls]
            tmp_dir = Path(tempfile.mkdtemp(prefix="sastaspace-assets-"))
            try:
                assets = await download_and_validate_assets(
                    asset_url_strings, tmp_dir, skip_clamav=True
                )
            except Exception:
                logger.warning("Asset download failed, continuing without assets", exc_info=True)
                from sastaspace.asset_downloader import AssetManifest

                assets = AssetManifest(assets=[], total_size_bytes=0)

            # 7. Build business profile via LLM (sync call via to_thread)
            homepage_text = homepage.text_content if hasattr(homepage, "text_content") else ""
            internal_texts = [
                p.text_content
                for p in internal_pages
                if hasattr(p, "text_content")
                and hasattr(p, "error")
                and not p.error
                and p.text_content
            ]
            business_profile = await asyncio.to_thread(
                build_business_profile,
                homepage_text,
                internal_texts,
                settings.claude_code_api_url,
                settings.claude_model,
                settings.claude_code_api_key,
            )

            return EnhancedCrawlResult(
                homepage=homepage,
                internal_pages=internal_pages,
                assets=assets,
                business_profile=business_profile,
            )

    except Exception as exc:
        # Return a minimal result with homepage error
        empty_homepage = CrawlResult(
            url=url,
            title="",
            meta_description="",
            favicon_url="",
            html_source="",
            screenshot_base64="",
            error=str(exc),
        )
        return EnhancedCrawlResult(homepage=empty_homepage)
