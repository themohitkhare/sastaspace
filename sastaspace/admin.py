# sastaspace/admin.py
"""Admin operations — site management and webhook handling."""

from __future__ import annotations

import hashlib
import hmac
import logging
import shutil
import time
from pathlib import Path

from sastaspace.database import _get_db

logger = logging.getLogger(__name__)


def verify_webhook_signature(
    body: bytes, signature: str, timestamp: str, secret: str, max_age_seconds: int = 300
) -> bool:
    """Verify Twenty webhook HMAC SHA256 signature with replay protection."""
    # Check timestamp age
    try:
        ts = int(timestamp)
        if abs(time.time() - ts) > max_age_seconds:
            return False
    except (ValueError, TypeError):
        return False

    # Verify HMAC
    expected = hmac.new(
        secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def delete_site_files(subdomain: str, sites_dir: Path) -> None:
    """Delete site files from disk. Idempotent — no-op if already deleted."""
    site_dir = sites_dir / subdomain
    if site_dir.exists():
        shutil.rmtree(site_dir)
        logger.info("Deleted site files: %s", subdomain)


async def find_site_by_subdomain(subdomain: str) -> dict | None:
    """Find a site record in MongoDB by subdomain."""
    db = _get_db()
    doc = await db["sites"].find_one({"subdomain": subdomain})
    if doc:
        doc.pop("_id", None)
    return doc


async def get_original_url_from_db(subdomain: str) -> str | None:
    """Read original URL from MongoDB site record."""
    site = await find_site_by_subdomain(subdomain)
    return site.get("original_url") if site else None


async def delete_site_db_record(subdomain: str) -> None:
    """Remove site record from MongoDB."""
    db = _get_db()
    await db["sites"].delete_one({"subdomain": subdomain})
    logger.info("Deleted site DB record: %s", subdomain)
