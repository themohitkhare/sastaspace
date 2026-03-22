# sastaspace/asset_downloader.py
"""Asset discovery, download, deduplication, and validation for crawled web pages."""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse

import aiohttp
from bs4 import BeautifulSoup

from sastaspace.asset_validator import file_hash, validate_asset
from sastaspace.models import AssetManifest, DownloadedAsset

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_PER_PAGE = 10
MAX_TOTAL = 30
MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_SITE_BYTES = 25 * 1024 * 1024  # 25 MB
DOWNLOAD_TIMEOUT = 10  # seconds

STOCK_PHOTO_DOMAINS: set[str] = {
    "unsplash.com",
    "images.unsplash.com",
    "pexels.com",
    "images.pexels.com",
    "shutterstock.com",
    "image.shutterstock.com",
    "istockphoto.com",
    "media.istockphoto.com",
    "gettyimages.com",
    "media.gettyimages.com",
    "pixabay.com",
    "cdn.pixabay.com",
    "stock.adobe.com",
}

_BG_IMAGE_RE = re.compile(r"background-image\s*:\s*url\(\s*['\"]?([^'\")\s]+)['\"]?\s*\)")


# ---------------------------------------------------------------------------
# URL extraction
# ---------------------------------------------------------------------------


def extract_asset_urls(html: str, base_url: str, max_per_page: int = MAX_PER_PAGE) -> list[str]:
    """Extract asset URLs from HTML using BeautifulSoup.

    Discovers: img src/srcset, link rel=icon, meta og:image, apple-touch-icon,
    inline style background-image.
    Skips data: and blob: URIs. Deduplicates and limits count.
    """
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    urls: list[str] = []

    def _add(raw_url: str) -> None:
        if not raw_url:
            return
        raw_url = raw_url.strip()
        if raw_url.startswith("data:") or raw_url.startswith("blob:"):
            return
        resolved = urljoin(base_url, raw_url)
        normalized = normalize_url(resolved)
        if normalized not in seen:
            seen.add(normalized)
            urls.append(resolved)

    # <img src>
    for img in soup.find_all("img", src=True):
        _add(img["src"])

    # <img srcset>
    for img in soup.find_all("img", srcset=True):
        for entry in img["srcset"].split(","):
            parts = entry.strip().split()
            if parts:
                _add(parts[0])

    # <meta property="og:image">
    for meta in soup.find_all("meta", attrs={"property": "og:image"}):
        content = meta.get("content", "")
        _add(content)

    # <link rel="icon">, <link rel="shortcut icon">, <link rel="apple-touch-icon">
    icon_rels = {"icon", "shortcut icon", "apple-touch-icon"}
    for link in soup.find_all("link", rel=True):
        rel_values = {r.lower() for r in link.get("rel", [])}
        if rel_values & icon_rels:
            href = link.get("href", "")
            _add(href)

    # Inline style background-image: url(...)
    for elem in soup.find_all(style=True):
        style = elem.get("style", "")
        for match in _BG_IMAGE_RE.findall(style):
            _add(match)

    return urls[:max_per_page]


# ---------------------------------------------------------------------------
# Filename helpers
# ---------------------------------------------------------------------------


def slugify_filename(name: str) -> str:
    """Slugify a filename: lowercase, replace non-alnum with hyphens, max 60 char stem."""
    # Split extension
    dot_idx = name.rfind(".")
    if dot_idx > 0:
        stem = name[:dot_idx]
        ext = name[dot_idx:].lower()
    else:
        stem = name
        ext = ""

    # Lowercase and replace non-alphanumeric with hyphens
    slug = re.sub(r"[^a-z0-9]", "-", stem.lower())
    # Collapse consecutive hyphens
    slug = re.sub(r"-{2,}", "-", slug)
    # Strip leading/trailing hyphens
    slug = slug.strip("-")
    # Truncate stem to 60 chars
    slug = slug[:60]
    # Strip trailing hyphens after truncation
    slug = slug.rstrip("-")

    return slug + ext if slug else ("asset" + ext)


def normalize_url(url: str) -> str:
    """Strip query params and fragments for URL deduplication."""
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


# ---------------------------------------------------------------------------
# Stock photo detection
# ---------------------------------------------------------------------------


def is_stock_photo(url: str) -> bool:
    """Check if URL belongs to a known stock photo CDN."""
    hostname = urlparse(url).hostname or ""
    for domain in STOCK_PHOTO_DOMAINS:
        if hostname == domain or hostname.endswith("." + domain):
            return True
    return False


# ---------------------------------------------------------------------------
# Download and validate
# ---------------------------------------------------------------------------


async def _download_one(
    session: aiohttp.ClientSession,
    url: str,
    tmp_dir: Path,
    semaphore: asyncio.Semaphore,
    seen_filenames: dict[str, int],
    skip_clamav: bool = False,
) -> DownloadedAsset | None:
    """Download a single asset to tmp_dir. Returns DownloadedAsset or None on failure."""
    async with semaphore:
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT)
            ) as resp:
                if resp.status != 200:
                    logger.info("Non-200 status %d for %s", resp.status, url)
                    return None

                content_type = resp.headers.get("Content-Type", "").split(";")[0].strip()

                # Derive filename from URL path
                url_path = urlparse(url).path
                raw_name = Path(url_path).name or "asset"
                slug = slugify_filename(raw_name)

                # Handle filename collisions
                if slug in seen_filenames:
                    seen_filenames[slug] += 1
                    stem_dot = slug.rfind(".")
                    if stem_dot > 0:
                        slug = f"{slug[:stem_dot]}-{seen_filenames[slug]}{slug[stem_dot:]}"
                    else:
                        slug = f"{slug}-{seen_filenames[slug]}"
                else:
                    seen_filenames[slug] = 1

                file_path = tmp_dir / slug
                total_bytes = 0

                with open(file_path, "wb") as f:
                    while True:
                        chunk = await resp.content.read(8192)
                        if not chunk:
                            break
                        total_bytes += len(chunk)
                        if total_bytes > MAX_FILE_BYTES:
                            logger.info("File %s exceeds 5MB limit, skipping", url)
                            f.close()
                            file_path.unlink(missing_ok=True)
                            return None
                        f.write(chunk)

                if total_bytes == 0:
                    file_path.unlink(missing_ok=True)
                    return None

                return DownloadedAsset(
                    original_url=url,
                    local_path=f"assets/{slug}",
                    content_type=content_type,
                    size_bytes=total_bytes,
                    file_hash="",  # filled after download
                    source_page="",
                    tmp_path=file_path,
                )

        except TimeoutError:
            logger.info("Timeout downloading %s", url)
            return None
        except Exception:
            logger.info("Failed to download %s", url, exc_info=True)
            return None


async def download_and_validate_assets(
    all_urls: list[str],
    tmp_dir: Path,
    skip_clamav: bool = False,
    max_total: int = MAX_TOTAL,
    max_site_bytes: int = MAX_SITE_BYTES,
) -> AssetManifest:
    """Download, deduplicate, and validate assets.

    Creates an asyncio.Semaphore(5) INSIDE this function to avoid event loop binding issues.
    Downloads concurrently with aiohttp, streams to disk, deduplicates by SHA-256 content hash,
    and validates each asset via validate_asset().
    """
    if not all_urls:
        return AssetManifest(assets=[], total_size_bytes=0)

    # Filter out stock photos and deduplicate by normalized URL
    seen_normalized: set[str] = set()
    filtered: list[str] = []
    for url in all_urls:
        if is_stock_photo(url):
            continue
        n = normalize_url(url)
        if n not in seen_normalized:
            seen_normalized.add(n)
            filtered.append(url)

    # Enforce total limit
    filtered = filtered[:max_total]

    if not filtered:
        return AssetManifest(assets=[], total_size_bytes=0)

    # Ensure tmp_dir exists
    tmp_dir.mkdir(parents=True, exist_ok=True)

    semaphore = asyncio.Semaphore(5)
    seen_filenames: dict[str, int] = {}

    async with aiohttp.ClientSession() as session:
        tasks = [
            _download_one(session, url, tmp_dir, semaphore, seen_filenames, skip_clamav)
            for url in filtered
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results: validate and deduplicate by content hash
    content_hashes: dict[str, DownloadedAsset] = {}
    validated_assets: list[DownloadedAsset] = []
    total_size = 0

    for result in results:
        if isinstance(result, BaseException) or result is None:
            continue

        asset: DownloadedAsset = result
        tmp_path = Path(asset.tmp_path)

        if not tmp_path.exists():
            continue

        # Compute content hash for dedup
        h = file_hash(tmp_path)
        asset.file_hash = h

        if h in content_hashes:
            # Duplicate content — discard this copy
            tmp_path.unlink(missing_ok=True)
            continue

        # Check site-wide size budget
        if total_size + asset.size_bytes > max_site_bytes:
            tmp_path.unlink(missing_ok=True)
            continue

        # Validate asset
        if not validate_asset(tmp_path, skip_clamav=skip_clamav):
            tmp_path.unlink(missing_ok=True)
            continue

        content_hashes[h] = asset
        validated_assets.append(asset)
        total_size += asset.size_bytes

    return AssetManifest(assets=validated_assets, total_size_bytes=total_size)
