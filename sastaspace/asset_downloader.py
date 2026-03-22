# sastaspace/asset_downloader.py
from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup

from sastaspace.models import AssetManifest, DownloadedAsset

logger = logging.getLogger(__name__)

ALLOWED_MIMES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
    "image/svg+xml",
    "image/x-icon",
    "image/vnd.microsoft.icon",
}

STOCK_PHOTO_DOMAINS = {"unsplash.com", "pexels.com", "shutterstock.com", "istockphoto.com"}

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_TOTAL_SIZE = 25 * 1024 * 1024  # 25MB
MAX_ASSETS_PER_PAGE = 10
MAX_TOTAL_ASSETS = 30
DOWNLOAD_TIMEOUT = 10


def _extract_asset_urls(html: str, base_url: str) -> list[dict]:
    """Extract image/asset URLs from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    assets = []
    seen_urls = set()

    def _add(url: str, source_type: str = "image"):
        if not url or url.startswith(("data:", "blob:", "#")):
            return
        full_url = urljoin(base_url, url)
        parsed = urlparse(full_url)
        # Skip stock photo domains
        if any(domain in parsed.hostname for domain in STOCK_PHOTO_DOMAINS if parsed.hostname):
            return
        # Normalize: strip common cache-busting params
        clean_url = re.sub(r"[?&](v|t|ver|rev|cb)=[^&]*", "", full_url)
        if clean_url not in seen_urls:
            seen_urls.add(clean_url)
            assets.append({"url": full_url, "type": source_type})

    # <img src>
    for img in soup.find_all("img", src=True):
        _add(img["src"], "image")

    # Favicons
    for link in soup.find_all("link", rel=True, href=True):
        rel = " ".join(link["rel"]).lower()
        if "icon" in rel:
            _add(link["href"], "favicon")

    # OG image
    og = soup.find("meta", attrs={"property": "og:image"})
    if og and og.get("content"):
        _add(og["content"], "og-image")

    # Apple touch icon
    for link in soup.find_all("link", rel="apple-touch-icon", href=True):
        _add(link["href"], "apple-icon")

    return assets[:MAX_ASSETS_PER_PAGE]


def _slugify_filename(url: str, source_type: str = "image") -> str:
    """Generate a clean filename from URL."""
    parsed = urlparse(url)
    filename = Path(parsed.path).name or "asset"
    # Remove query params from filename
    filename = re.sub(r"\?.*$", "", filename)
    # Slugify
    name, ext = (filename.rsplit(".", 1) + [""])[:2]
    name = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "asset"
    ext = ext.lower() if ext else "png"
    # Prefix with source type
    prefix = ""
    if source_type in ("favicon", "og-image", "apple-icon"):
        prefix = f"{source_type}-"
    return f"{prefix}{name}.{ext}"


async def download_and_validate_assets(
    asset_urls: list[dict],
    tmp_dir: Path,
    source_page: str = "",
    skip_clamav: bool = False,
) -> AssetManifest:
    """Download and validate assets. Returns an AssetManifest.

    Args:
        asset_urls: List of {"url": str, "type": str} dicts.
        tmp_dir: Temp directory to store downloaded files.
        source_page: URL of the source page.
        skip_clamav: If True, skip ClamAV scanning.
    """
    tmp_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = tmp_dir / "assets"
    assets_dir.mkdir(exist_ok=True)

    downloaded: list[DownloadedAsset] = []
    seen_hashes: dict[str, DownloadedAsset] = {}
    total_size = 0
    used_filenames: set[str] = set()
    semaphore = asyncio.Semaphore(5)

    async def _download_one(item: dict) -> DownloadedAsset | None:
        nonlocal total_size
        url = item["url"]
        source_type = item.get("type", "image")

        async with semaphore:
            try:
                timeout = aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url) as resp:
                        if resp.status != 200:
                            return None
                        content_type = resp.content_type or ""
                        if content_type not in ALLOWED_MIMES:
                            return None

                        data = await resp.read()
                        size = len(data)

                        if size == 0 or size > MAX_FILE_SIZE:
                            return None
                        if total_size + size > MAX_TOTAL_SIZE:
                            return None

                        # Content dedup via hash
                        file_hash = hashlib.sha256(data).hexdigest()
                        if file_hash in seen_hashes:
                            return seen_hashes[file_hash]

                        # Generate unique filename
                        filename = _slugify_filename(url, source_type)
                        base, ext = filename.rsplit(".", 1)
                        counter = 2
                        while filename in used_filenames:
                            filename = f"{base}-{counter}.{ext}"
                            counter += 1
                        used_filenames.add(filename)

                        local_path = f"assets/{filename}"
                        tmp_path = assets_dir / filename
                        tmp_path.write_bytes(data)

                        total_size += size

                        asset = DownloadedAsset(
                            original_url=url,
                            local_path=local_path,
                            content_type=content_type,
                            size_bytes=size,
                            file_hash=file_hash,
                            source_page=source_page,
                            tmp_path=tmp_path,
                        )
                        seen_hashes[file_hash] = asset
                        return asset

            except Exception:
                logger.debug("Failed to download asset: %s", url)
                return None

    # Download all (capped at MAX_TOTAL_ASSETS)
    tasks = [_download_one(item) for item in asset_urls[:MAX_TOTAL_ASSETS]]
    results = await asyncio.gather(*tasks)

    for result in results:
        if result is not None and result not in downloaded:
            downloaded.append(result)

    return AssetManifest(assets=downloaded, total_size_bytes=total_size)
