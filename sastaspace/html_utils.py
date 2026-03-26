# sastaspace/html_utils.py
"""Shared HTML validation, cleaning utilities, and result types.

Extracted from redesigner.py to break circular imports between
redesigner ↔ agents.pipeline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


class RedesignError(Exception):
    """Raised when Claude returns invalid or unexpected output."""


@dataclass
class RedesignResult:
    """Result of a redesign operation — HTML string plus optional build directory."""

    html: str
    build_dir: Path | None = None  # Vite dist/ directory (React pipeline only)


def clean_html(raw: str) -> str:
    """Strip markdown code fences and leading/trailing whitespace."""
    raw = raw.strip()
    raw = re.sub(r"^```(?:html)?\s*\n?", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\n?```\s*$", "", raw, flags=re.IGNORECASE)
    return raw.strip()


SASTASPACE_BADGE = (
    '<div style="position:fixed;bottom:12px;right:12px;z-index:9999;'
    'font-family:system-ui,-apple-system,sans-serif;">'
    '<a href="https://sastaspace.com" target="_blank" rel="noopener" '
    'style="display:inline-flex;align-items:center;gap:6px;padding:6px 12px;'
    "background:rgba(0,0,0,0.75);color:#fff;font-size:11px;border-radius:20px;"
    'text-decoration:none;backdrop-filter:blur(8px);transition:opacity 0.2s;opacity:0.7" '
    'title="Get your free AI website redesign">'
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M12 2L2 7l10 5 10-5-10-5z"/>'
    '<path d="M2 17l10 5 10-5"/>'
    '<path d="M2 12l10 5 10-5"/></svg>'
    "Redesigned by SastaSpace"
    "</a></div>"
)


def inject_badge(html: str) -> str:
    """Insert the SastaSpace badge just before </body> (or </html> as fallback)."""
    # Try </body> first (case-insensitive)
    body_match = re.search(r"</body\s*>", html, re.IGNORECASE)
    if body_match:
        pos = body_match.start()
        return html[:pos] + SASTASPACE_BADGE + "\n" + html[pos:]

    # Fallback: before </html>
    html_match = re.search(r"</html\s*>", html, re.IGNORECASE)
    if html_match:
        pos = html_match.start()
        return html[:pos] + SASTASPACE_BADGE + "\n" + html[pos:]

    # No closing tags found — append at end
    return html + "\n" + SASTASPACE_BADGE


def sanitize_html(html_str: str) -> str:
    """Strip inline event handlers and javascript: URLs from AI-generated HTML.

    This MUST be applied to all AI-generated HTML before writing to disk,
    regardless of code path (SSE inline or Redis worker).
    """
    # Strip inline event handlers (on*="...")
    html_str = re.sub(
        r'\s+on\w+\s*=\s*"[^"]*"',
        "",
        html_str,
        flags=re.IGNORECASE,
    )
    html_str = re.sub(
        r"\s+on\w+\s*=\s*'[^']*'",
        "",
        html_str,
        flags=re.IGNORECASE,
    )
    # Strip javascript: URLs in href/src attributes
    html_str = re.sub(
        r'(href|src)\s*=\s*"javascript:[^"]*"',
        r'\1=""',
        html_str,
        flags=re.IGNORECASE,
    )
    html_str = re.sub(
        r"(href|src)\s*=\s*'javascript:[^']*'",
        r"\1=''",
        html_str,
        flags=re.IGNORECASE,
    )
    return html_str


# Domains that the LLM hallucinates image URLs for — these return 404s
_HALLUCINATED_IMAGE_DOMAINS = re.compile(
    r"https?://(?:images\.)?unsplash\.com/photo-[^\s\"']+|"
    r"https?://(?:via\.)?placeholder\.com/[^\s\"']+|"
    r"https?://picsum\.photos/[^\s\"']+|"
    r"https?://placehold\.(?:co|it)/[^\s\"']+"
)

# Transparent 1x1 pixel data URI — renders as invisible, won't break layout
_TRANSPARENT_PIXEL = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
    "width='800' height='400' viewBox='0 0 800 400'%3E"
    "%3Crect width='800' height='400' fill='%23e5e7eb'/%3E"
    "%3Ctext x='400' y='200' text-anchor='middle' dy='.35em' "
    "fill='%239ca3af' font-family='system-ui' font-size='14'%3E"
    "Image%3C/text%3E%3C/svg%3E"
)


def strip_hallucinated_images(html: str) -> tuple[str, int]:
    """Replace hallucinated stock photo URLs with a neutral SVG placeholder.

    Returns the cleaned HTML and the count of URLs replaced.
    """
    count = 0

    def _replace(m: re.Match) -> str:
        nonlocal count
        count += 1
        return _TRANSPARENT_PIXEL

    cleaned = _HALLUCINATED_IMAGE_DOMAINS.sub(_replace, html)
    return cleaned, count


def validate_html(html: str) -> None:
    """Raise RedesignError if the HTML looks truncated or malformed."""
    if not html:
        raise RedesignError("Claude returned an empty response")
    if "<!doctype html" not in html.lower():
        raise RedesignError(
            "Response missing <!DOCTYPE html> declaration — output may not be valid HTML"
        )
    if "</html>" not in html.lower():
        raise RedesignError("Response missing closing </html> tag — output appears to be truncated")
