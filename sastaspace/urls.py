# sastaspace/urls.py
"""URL normalization, hashing, and dedup for redesign jobs."""

from __future__ import annotations

import hashlib
import re
from urllib.parse import urlparse

import tldextract


def normalize_url(raw: str) -> str:
    """Normalize a raw URL input into a canonical form for dedup.

    Handles:
    - Bare domains: example.com → https://example.com
    - HTTP: http://example.com → https://example.com
    - www prefix: www.example.com → example.com
    - Trailing slashes: example.com/ → example.com
    - Mixed case: Example.COM → example.com
    - Paths: example.com/about → https://example.com/about
    - Ports: example.com:8080 → https://example.com:8080
    - Query strings stripped (for dedup, we care about the domain+path)
    - Fragments stripped

    Returns a canonical URL string.
    """
    raw = raw.strip()
    if not raw:
        return raw

    # Add protocol if missing
    if not re.match(r"^https?://", raw, re.IGNORECASE):
        raw = f"https://{raw}"

    try:
        parsed = urlparse(raw)
    except (ValueError, TypeError):
        return raw

    # Normalize hostname
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return raw

    # Strip www.
    if hostname.startswith("www."):
        hostname = hostname[4:]

    # Rebuild with normalized parts
    port = f":{parsed.port}" if parsed.port and parsed.port not in (80, 443) else ""
    path = parsed.path.rstrip("/") or ""

    return f"https://{hostname}{port}{path}"


def url_hash(url: str) -> str:
    """Generate a stable hash for a normalized URL.

    Use this for dedup lookups — same domain always produces the same hash.
    """
    normalized = normalize_url(url)
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def extract_domain(raw: str) -> str:
    """Extract the registered domain from any URL input.

    Uses tldextract for robust TLD handling:
    - blog.example.co.uk → example.co.uk
    - sub.domain.example.com → example.com
    - example.com/path → example.com

    Returns the registered domain (no subdomain, no path).
    """
    # Add protocol if needed for parsing
    if not re.match(r"^https?://", raw, re.IGNORECASE):
        raw = f"https://{raw}"

    ext = tldextract.extract(raw)
    if ext.registered_domain:
        return ext.registered_domain
    # Fallback to hostname
    parsed = urlparse(raw)
    return (parsed.hostname or raw).lower().lstrip("www.")


def is_valid_url(raw: str) -> tuple[bool, str]:
    """Validate and normalize a URL input.

    Returns (is_valid, normalized_url_or_error_message).
    Accepts: domains, http://, https://, with paths, ports, etc.
    Rejects: empty, no TLD, localhost, internal IPs.
    """
    raw = raw.strip()
    if not raw:
        return False, "Please enter a website address"

    # Add protocol if missing
    url = raw
    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = f"https://{url}"

    try:
        parsed = urlparse(url)
    except (ValueError, TypeError):
        return False, "Please enter a valid website address"

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return False, "Please enter a valid website address"

    # Reject localhost and internal IPs
    if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
        return False, "Cannot redesign localhost"
    if hostname.startswith("192.168.") or hostname.startswith("10.") or hostname.startswith("172."):
        return False, "Cannot redesign internal network addresses"

    # Use tldextract to validate it's a real domain with TLD
    ext = tldextract.extract(url)
    if not ext.suffix:
        # No TLD found — might be a bare hostname
        if "." not in hostname:
            return False, "Please enter a valid website address (e.g. example.com)"

    normalized = normalize_url(raw)
    return True, normalized
