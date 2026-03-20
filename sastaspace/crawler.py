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
                lines.append(
                    f"## Section: {s.get('heading', 'unnamed')}\n{s.get('content', '')[:500]}"
                )
        return "\n\n".join(lines)


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


async def crawl(url: str) -> CrawlResult:
    """Crawl a URL and return a CrawlResult. Sets result.error on failure."""
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
            finally:
                await browser.close()

    except Exception as exc:
        empty.error = str(exc)
        return empty
