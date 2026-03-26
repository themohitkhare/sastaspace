# sastaspace/post_deploy_verify.py
"""Post-deploy verification: check all images and links in generated HTML.

Runs as a non-blocking fire-and-forget task after deployment.  Makes async
HEAD requests to verify that image src and link href URLs are reachable.
Reports broken URLs as structured warnings in the worker logs.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Max concurrent HTTP checks to avoid hammering external servers
_MAX_CONCURRENCY = 10

# Timeout per request (seconds)
_REQUEST_TIMEOUT = 10

# URLs that are expected to not resolve (anchors, javascript, mailto, tel)
_SKIP_SCHEMES = {"javascript", "mailto", "tel", "data", "blob"}
_SKIP_PREFIXES = ("#", "javascript:", "mailto:", "tel:", "data:", "blob:")


@dataclass
class VerifyResult:
    """Results from post-deploy URL verification."""

    total_images: int = 0
    broken_images: list[str] = field(default_factory=list)
    total_links: int = 0
    broken_links: list[str] = field(default_factory=list)
    skipped: int = 0

    @property
    def ok(self) -> bool:
        return len(self.broken_images) == 0 and len(self.broken_links) == 0

    def summary(self) -> str:
        parts = [
            f"images={self.total_images} (broken={len(self.broken_images)})",
            f"links={self.total_links} (broken={len(self.broken_links)})",
        ]
        if self.skipped:
            parts.append(f"skipped={self.skipped}")
        return " | ".join(parts)


class _URLExtractor(HTMLParser):
    """Extract image src and link href from HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.img_srcs: list[str] = []
        self.link_hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = dict(attrs)
        if tag == "img":
            src = attr_dict.get("src", "")
            if src:
                self.img_srcs.append(src)
        elif tag == "a":
            href = attr_dict.get("href", "")
            if href:
                self.link_hrefs.append(href)


def _should_check(url: str) -> bool:
    """Decide if a URL should be checked for reachability."""
    if not url or len(url) > 2000:
        return False
    if any(url.startswith(p) for p in _SKIP_PREFIXES):
        return False
    parsed = urlparse(url)
    if parsed.scheme and parsed.scheme.lower() in _SKIP_SCHEMES:
        return False
    # Only check absolute HTTP(S) URLs — relative paths can't be HEAD-checked
    if not parsed.scheme or parsed.scheme.lower() not in ("http", "https"):
        return False
    return True


async def _check_url(url: str, semaphore: asyncio.Semaphore) -> tuple[str, int | None]:
    """HEAD-check a single URL. Returns (url, status_code_or_None)."""
    import aiohttp

    async with semaphore:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(
                    url,
                    timeout=aiohttp.ClientTimeout(total=_REQUEST_TIMEOUT),
                    allow_redirects=True,
                    ssl=False,
                ) as resp:
                    # Some servers reject HEAD — fall back to GET with small read
                    if resp.status == 405:
                        async with session.get(
                            url,
                            timeout=aiohttp.ClientTimeout(total=_REQUEST_TIMEOUT),
                            allow_redirects=True,
                            ssl=False,
                        ) as get_resp:
                            return url, get_resp.status
                    return url, resp.status
        except Exception:  # noqa: BLE001
            return url, None


async def verify_urls(html: str) -> VerifyResult:
    """Verify all image and link URLs in the generated HTML.

    Makes async HEAD requests to check reachability. Returns a VerifyResult
    with lists of broken URLs.
    """
    extractor = _URLExtractor()
    try:
        extractor.feed(html)
    except Exception:  # noqa: BLE001
        pass

    result = VerifyResult()
    result.total_images = len(extractor.img_srcs)
    result.total_links = len(extractor.link_hrefs)

    # Deduplicate and filter
    img_urls = {src for src in extractor.img_srcs if _should_check(src)}
    link_urls = {href for href in extractor.link_hrefs if _should_check(href)}
    all_urls = img_urls | link_urls
    result.skipped = (result.total_images + result.total_links) - len(all_urls)

    if not all_urls:
        return result

    semaphore = asyncio.Semaphore(_MAX_CONCURRENCY)
    tasks = [_check_url(url, semaphore) for url in all_urls]
    responses = await asyncio.gather(*tasks)

    # Build a map of url -> status
    url_status: dict[str, int | None] = dict(responses)

    for url in img_urls:
        status = url_status.get(url)
        if status is None or status >= 400:
            result.broken_images.append(url)

    for url in link_urls:
        status = url_status.get(url)
        if status is None or status >= 400:
            result.broken_links.append(url)

    return result


def _truncate(url: str, max_len: int = 80) -> str:
    """Truncate a URL for logging."""
    return url[:max_len] + "..." if len(url) > max_len else url


def log_verify_result(result: VerifyResult, job_id: str) -> None:
    """Log verification results."""
    if result.ok:
        logger.info(
            "POST-DEPLOY VERIFY | job=%s ALL OK | %s",
            job_id,
            result.summary(),
        )
        return

    logger.warning(
        "POST-DEPLOY VERIFY | job=%s ISSUES FOUND | %s",
        job_id,
        result.summary(),
    )
    for url in result.broken_images[:10]:
        logger.warning("BROKEN IMAGE | job=%s url=%s", job_id, _truncate(url))
    for url in result.broken_links[:10]:
        logger.warning("BROKEN LINK | job=%s url=%s", job_id, _truncate(url))
