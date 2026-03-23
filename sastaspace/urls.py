# sastaspace/urls.py
"""URL normalization, hashing, and dedup for redesign jobs."""

from __future__ import annotations

import hashlib
import ipaddress
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


_MAX_URL_LENGTH = 2048

_LOCALHOST_NAMES = frozenset({"localhost", "127.0.0.1", "0.0.0.0", "::1", "localhost.localdomain"})

_PRIVATE_IP_PREFIXES = ("192.168.", "10.", "172.")


def _ensure_scheme(url: str) -> str:
    """Add https:// if no scheme is present."""
    if not re.match(r"^https?://", url, re.IGNORECASE):
        return f"https://{url}"
    return url


def _validate_hostname(hostname: str) -> str | None:
    """Return an error message if the hostname is disallowed, or None if OK."""
    if not hostname:
        return "Please enter a valid website address"

    if hostname in _LOCALHOST_NAMES:
        return "Cannot redesign localhost"

    try:
        addr = ipaddress.ip_address(hostname)
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
            return "Cannot redesign internal network addresses"
    except ValueError:
        pass

    if hostname.startswith(_PRIVATE_IP_PREFIXES):
        return "Cannot redesign internal network addresses"

    return None


def is_valid_url(raw: str) -> tuple[bool, str]:
    """Validate and normalize a URL input.

    Returns (is_valid, normalized_url_or_error_message).
    Accepts: domains, http://, https://, with paths, ports, etc.
    Rejects: empty, no TLD, localhost, internal IPs, overly long URLs,
    non-http(s) schemes, and raw IP addresses pointing to internal networks.
    """
    raw = raw.strip()
    if not raw:
        return False, "Please enter a website address"

    if len(raw) > _MAX_URL_LENGTH:
        return False, f"URL too long (max {_MAX_URL_LENGTH} characters)"

    url = _ensure_scheme(raw)

    try:
        parsed = urlparse(url)
    except (ValueError, TypeError):
        return False, "Please enter a valid website address"

    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        return False, "Only http and https URLs are supported"

    hostname = (parsed.hostname or "").lower()
    hostname_err = _validate_hostname(hostname)
    if hostname_err:
        return False, hostname_err

    ext = tldextract.extract(url)
    if not ext.suffix and "." not in hostname:
        return False, "Please enter a valid website address (e.g. example.com)"

    normalized = normalize_url(raw)
    return True, normalized
