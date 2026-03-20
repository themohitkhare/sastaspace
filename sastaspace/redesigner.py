# sastaspace/redesigner.py
from __future__ import annotations

import base64
import os
import re

from agno.agent import Agent
from agno.media import Image
from agno.models.anthropic import Claude

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
        raise RedesignError("Response missing closing </html> tag — output appears to be truncated")


def redesign(
    crawl_result: CrawlResult, api_key: str, model: str = "claude-sonnet-4-20250514"
) -> str:
    """
    Use Agno + Claude to redesign a crawled website into a single HTML file.

    Uses Agno's Agent with Claude vision model for screenshot analysis.

    Raises:
        RedesignError: if crawl_result.error is set or Claude's output is invalid.
    """
    if crawl_result.error:
        raise RedesignError(f"Cannot redesign — crawl failed: {crawl_result.error}")

    os.environ["ANTHROPIC_API_KEY"] = api_key

    agent = Agent(
        model=Claude(id=model, max_tokens=16000),
        instructions=SYSTEM_PROMPT,
        markdown=False,
    )

    user_text = USER_PROMPT_TEMPLATE.format(
        crawl_context=crawl_result.to_prompt_context(),
        title=crawl_result.title,
        meta_description=crawl_result.meta_description,
        colors=", ".join(crawl_result.colors[:10]) or "not detected",
        fonts=", ".join(crawl_result.fonts[:5]) or "not detected",
    )

    images: list[Image] = []
    if crawl_result.screenshot_base64:
        screenshot_bytes = base64.b64decode(crawl_result.screenshot_base64)
        images.append(Image(content=screenshot_bytes))

    response = agent.run(user_text, images=images if images else None)
    raw = response.content or ""

    html = _clean_html(raw)
    _validate_html(html)
    return html
