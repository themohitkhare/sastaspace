# sastaspace/asset_validator.py
"""Layered asset validation: magic bytes, Pillow integrity, defusedxml SVG sanitization,
YARA threat scanning, and optional ClamAV antivirus scanning."""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path

import defusedxml.ElementTree as ET
import magic
import yara
from PIL import Image

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALLOWED_MIMES: set[str] = {
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "image/svg+xml",
    "image/avif",
    "image/bmp",
}

DEFAULT_MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

SVG_UNSAFE_TAGS: set[str] = {
    "script",
    "foreignobject",
    "set",
    "animate",
    "iframe",
    "embed",
    "object",
}

_SVG_NS_RE = re.compile(r"\{[^}]*\}")

_yara_rules: yara.Rules | None = None


# ---------------------------------------------------------------------------
# YARA rules — lazy singleton
# ---------------------------------------------------------------------------


def _get_yara_rules() -> yara.Rules:
    """Load YARA rules from the yara_rules/ directory once and cache."""
    global _yara_rules  # noqa: PLW0603
    if _yara_rules is None:
        rules_dir = Path(__file__).parent / "yara_rules"
        rule_files: dict[str, str] = {}
        for rule_file in rules_dir.glob("*.yar"):
            rule_files[rule_file.stem] = str(rule_file)
        _yara_rules = yara.compile(filepaths=rule_files)
    return _yara_rules


# ---------------------------------------------------------------------------
# Validation layers
# ---------------------------------------------------------------------------


def validate_mime_type(path: Path) -> str | None:
    """Check file magic bytes and return the MIME type if it is in ALLOWED_MIMES, else None."""
    try:
        mime = magic.from_file(str(path), mime=True)
    except Exception:
        logger.warning("Failed to detect MIME type for %s", path)
        return None
    if not mime or mime not in ALLOWED_MIMES:
        return None
    return mime


def validate_image_integrity(path: Path) -> bool:
    """Verify image can be decoded by Pillow. Returns False for corrupt or unreadable files."""
    try:
        with Image.open(path) as img:
            img.verify()
        return True
    except Exception:
        return False


def sanitize_svg(svg_content: str) -> str:
    """Parse SVG via defusedxml and strip unsafe tags and attributes.

    Does NOT pass through nh3.clean() — that strips valid SVG elements.
    """
    import xml.etree.ElementTree as StdET

    # Register common SVG/XLink namespaces so serialization doesn't mangle prefixes
    _SVG_NAMESPACES = {
        "http://www.w3.org/2000/svg": "",
        "http://www.w3.org/1999/xlink": "xlink",
        "http://www.w3.org/XML/1998/namespace": "xml",
    }
    for uri, prefix in _SVG_NAMESPACES.items():
        StdET.register_namespace(prefix, uri)

    try:
        root = ET.fromstring(svg_content)
    except ET.ParseError:
        logger.warning("Failed to parse SVG content")
        return svg_content

    _strip_unsafe_elements(root)
    _strip_unsafe_attrs(root)

    # Re-serialize. ET.tostring produces bytes; decode to str.
    result = ET.tostring(root, encoding="unicode")
    return result


def _strip_unsafe_elements(element: ET.Element) -> None:  # type: ignore[name-defined]
    """Recursively remove unsafe child elements in-place."""
    to_remove = []
    for child in element:
        tag_local = _SVG_NS_RE.sub("", child.tag).lower()
        if tag_local in SVG_UNSAFE_TAGS:
            to_remove.append(child)
        else:
            _strip_unsafe_elements(child)
    for child in to_remove:
        element.remove(child)


def _strip_unsafe_attrs(element: ET.Element) -> None:  # type: ignore[name-defined]
    """Recursively remove event handler attributes and javascript: URLs."""
    attrs_to_remove = []
    for attr, value in element.attrib.items():
        attr_local = _SVG_NS_RE.sub("", attr).lower()
        if attr_local.startswith("on"):
            attrs_to_remove.append(attr)
        elif "javascript:" in value.lower():
            attrs_to_remove.append(attr)
    for attr in attrs_to_remove:
        del element.attrib[attr]
    for child in element:
        _strip_unsafe_attrs(child)


def scan_yara(path: Path) -> bool:
    """Scan file with YARA rules. Returns True if clean (no matches), False if threats found."""
    try:
        rules = _get_yara_rules()
        matches = rules.match(str(path))
        if matches:
            logger.warning("YARA matches for %s: %s", path, [m.rule for m in matches])
            return False
        return True
    except Exception:
        logger.exception("YARA scan failed for %s", path)
        return False


def scan_clamav(path: Path, host: str = "localhost", port: int = 3310, timeout: int = 10) -> bool:
    """Scan file with ClamAV via network socket. Returns True if clean or if ClamAV is unreachable
    (graceful fallback)."""
    try:
        import pyclamd

        cd = pyclamd.ClamdNetworkSocket(host=host, port=port, timeout=timeout)
        if not cd.ping():
            logger.info("ClamAV not reachable — skipping scan for %s", path)
            return True
        result = cd.scan_file(str(path))
        if result is None:
            return True
        logger.warning("ClamAV detection for %s: %s", path, result)
        return False
    except ImportError:
        logger.info("pyclamd not installed — skipping ClamAV scan")
        return True
    except Exception:
        logger.info("ClamAV unavailable — skipping scan for %s", path)
        return True


def file_hash(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Full validation chain
# ---------------------------------------------------------------------------


def validate_asset(
    path: Path,
    max_size_bytes: int = DEFAULT_MAX_SIZE_BYTES,
    skip_clamav: bool = False,
) -> bool:
    """Run the full asset validation chain. Returns True if the asset passes all checks."""
    path = Path(path)

    # 1. Size check
    try:
        if path.stat().st_size > max_size_bytes:
            logger.warning("File %s exceeds max size %d bytes", path, max_size_bytes)
            return False
        if path.stat().st_size == 0:
            logger.warning("File %s is empty", path)
            return False
    except OSError:
        return False

    # 2. MIME type validation
    mime = validate_mime_type(path)
    if mime is None:
        logger.warning("File %s has disallowed or undetectable MIME type", path)
        return False

    # 3. Image integrity (skip for SVG — Pillow doesn't handle SVG)
    if mime != "image/svg+xml":
        if not validate_image_integrity(path):
            logger.warning("File %s failed image integrity check", path)
            return False

    # 4. YARA scan
    if not scan_yara(path):
        logger.warning("File %s failed YARA scan", path)
        return False

    # 5. ClamAV scan (optional)
    if not skip_clamav:
        if not scan_clamav(path):
            logger.warning("File %s failed ClamAV scan", path)
            return False

    return True
