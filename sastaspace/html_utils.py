# sastaspace/html_utils.py
"""Shared HTML validation and cleaning utilities.

Extracted from redesigner.py to break circular imports between
redesigner ↔ agents.pipeline.
"""

from __future__ import annotations

import re


class RedesignError(Exception):
    """Raised when Claude returns invalid or unexpected output."""


def clean_html(raw: str) -> str:
    """Strip markdown code fences and leading/trailing whitespace."""
    raw = raw.strip()
    raw = re.sub(r"^```(?:html)?\s*\n?", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\n?```\s*$", "", raw, flags=re.IGNORECASE)
    return raw.strip()


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
