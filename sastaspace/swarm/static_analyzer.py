# sastaspace/swarm/static_analyzer.py
"""Programmatic quality gates — no LLM, deterministic checks."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

_PLACEHOLDER_PATTERNS = re.compile(
    r"(placeholder\.com|via\.placeholder|unsplash\.com|images\.unsplash|"
    r"picsum\.photos|lorempixel|dummyimage\.com|placehold\.co|"
    r"example\.com/.*\.(jpg|png|gif|svg|webp))",
    re.IGNORECASE,
)

_EXTERNAL_CDN_RE = re.compile(
    r'(?:href|src)=["\']https?://(?!fonts\.googleapis\.com|fonts\.gstatic\.com)([^"\']+)',
    re.IGNORECASE,
)

_CDN_HOSTS = (
    "cdn.jsdelivr.net",
    "cdnjs.cloudflare.com",
    "unpkg.com",
    "cdn.tailwindcss.com",
    "stackpath.bootstrapcdn.com",
    "maxcdn.bootstrapcdn.com",
)

_FONT_NO_FALLBACK_RE = re.compile(
    r"font-family\s*:\s*['\"][^'\"]+['\"](?:\s*;|\s*})",
    re.IGNORECASE,
)

_CSS_VAR_USE_RE = re.compile(r"var\(\s*(--[a-zA-Z0-9_-]+)\s*\)")
_CSS_VAR_DEF_RE = re.compile(r"(--[a-zA-Z0-9_-]+)\s*:")

_MAX_HTML_SIZE = 500_000


@dataclass
class StaticAnalyzerResult:
    passed: bool
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class _AnchorIDParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.internal_anchors: list[str] = []
        self.element_ids: set[str] = set()
        self.img_srcs: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if "id" in attrs_dict:
            self.element_ids.add(attrs_dict["id"])
        if tag == "a":
            href = attrs_dict.get("href", "")
            if href.startswith("#") and len(href) > 1:
                self.internal_anchors.append(href[1:])
        if tag == "img":
            src = attrs_dict.get("src", "")
            if src:
                self.img_srcs.append(src)


class StaticAnalyzer:
    @staticmethod
    def analyze(html: str) -> StaticAnalyzerResult:
        failures: list[str] = []
        warnings: list[str] = []

        # 1. DOCTYPE check
        if not html.strip().startswith("<!DOCTYPE html>") and not html.strip().startswith(
            "<!doctype html>"
        ):
            failures.append("Missing <!DOCTYPE html> declaration")

        # 2. Closing </html> tag
        if "</html>" not in html.lower():
            failures.append("Missing </html> closing tag")

        # 3. File size
        size = len(html.encode("utf-8"))
        if size > _MAX_HTML_SIZE:
            failures.append(f"File size {size:,} bytes exceeds {_MAX_HTML_SIZE:,} byte limit")

        # 4. Placeholder URLs
        placeholder_matches = _PLACEHOLDER_PATTERNS.findall(html)
        if placeholder_matches:
            unique = set(m if isinstance(m, str) else m[0] for m in placeholder_matches)
            for url in list(unique)[:5]:
                failures.append(f"Placeholder/stock URL detected: {url}")

        # 5. Parse HTML
        parser = _AnchorIDParser()
        try:
            parser.feed(html)
        except Exception:
            warnings.append("HTML parsing encountered errors")

        # 6. Internal anchor targets
        for anchor in parser.internal_anchors:
            if anchor not in parser.element_ids:
                failures.append(f"Internal anchor #{anchor} has no matching id attribute")

        # 7. console.log
        if re.search(r"\bconsole\.(log|debug|warn|info|error)\s*\(", html):
            failures.append("console.log or debug statements found in output")

        # 8. External CDN
        for match in _EXTERNAL_CDN_RE.finditer(html):
            url = match.group(1)
            if any(host in url for host in _CDN_HOSTS):
                failures.append(f"External CDN dependency detected: {url[:80]}")

        # 9. Font fallback
        font_no_fallback = _FONT_NO_FALLBACK_RE.findall(html)
        for decl in font_no_fallback:
            if "," not in decl:
                failures.append(f"Font declaration without web-safe fallback: {decl.strip()[:60]}")

        # 10. CSS variable references vs definitions
        used_vars = set(_CSS_VAR_USE_RE.findall(html))
        defined_vars = set(_CSS_VAR_DEF_RE.findall(html))
        undefined = used_vars - defined_vars
        for var in sorted(undefined):
            failures.append(f"CSS custom property {var} is used but never defined")

        return StaticAnalyzerResult(passed=len(failures) == 0, failures=failures, warnings=warnings)
