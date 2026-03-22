# tests/test_asset_validator.py
"""Tests for the layered asset validation module."""

from __future__ import annotations

import struct
import tempfile
import zlib
from pathlib import Path

from sastaspace.asset_validator import (
    sanitize_svg,
    validate_asset,
    validate_image_integrity,
    validate_mime_type,
)

# ---------------------------------------------------------------------------
# Helpers to create minimal valid PNG files
# ---------------------------------------------------------------------------


def _make_png_bytes() -> bytes:
    """Create a minimal valid 1x1 white PNG in memory."""
    signature = b"\x89PNG\r\n\x1a\n"

    # IHDR chunk: width=1, height=1, bit_depth=8, color_type=2 (RGB)
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr_crc = struct.pack(">I", zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF)
    ihdr = struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data + ihdr_crc

    # IDAT chunk: single row, filter byte 0, then 3 bytes (white pixel)
    raw_row = b"\x00\xff\xff\xff"
    compressed = zlib.compress(raw_row)
    idat_crc = struct.pack(">I", zlib.crc32(b"IDAT" + compressed) & 0xFFFFFFFF)
    idat = struct.pack(">I", len(compressed)) + b"IDAT" + compressed + idat_crc

    # IEND chunk
    iend_crc = struct.pack(">I", zlib.crc32(b"IEND") & 0xFFFFFFFF)
    iend = struct.pack(">I", 0) + b"IEND" + iend_crc

    return signature + ihdr + idat + iend


def _write_tmp(data: bytes, suffix: str = ".png") -> Path:
    """Write bytes to a named temp file and return its Path."""
    f = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    f.write(data)
    f.close()
    return Path(f.name)


# ---------------------------------------------------------------------------
# TestValidateMimeType
# ---------------------------------------------------------------------------


class TestValidateMimeType:
    def test_valid_png_magic_bytes(self):

        path = _write_tmp(_make_png_bytes(), suffix=".png")
        try:
            result = validate_mime_type(path)
            assert result is not None
            assert "png" in result.lower() or "image" in result.lower()
        finally:
            path.unlink(missing_ok=True)

    def test_reject_text_file(self):

        path = _write_tmp(b"Hello, I am plain text", suffix=".png")
        try:
            result = validate_mime_type(path)
            # text/plain is not in ALLOWED_MIMES, so should return None or a non-image type
            assert result is None or "image" not in result.lower()
        finally:
            path.unlink(missing_ok=True)

    def test_reject_empty_file(self):

        path = _write_tmp(b"", suffix=".png")
        try:
            result = validate_mime_type(path)
            assert result is None
        finally:
            path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# TestValidateImageIntegrity
# ---------------------------------------------------------------------------


class TestValidateImageIntegrity:
    def test_valid_png_via_pillow(self):

        path = _write_tmp(_make_png_bytes(), suffix=".png")
        try:
            assert validate_image_integrity(path) is True
        finally:
            path.unlink(missing_ok=True)

    def test_corrupt_image(self):

        # PNG signature followed by garbage
        path = _write_tmp(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50, suffix=".png")
        try:
            assert validate_image_integrity(path) is False
        finally:
            path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# TestSanitizeSvg
# ---------------------------------------------------------------------------


class TestSanitizeSvg:
    def test_strips_script_tag(self):

        svg = '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script><rect/></svg>'
        result = sanitize_svg(svg)
        assert "<script" not in result.lower()
        assert "<rect" in result.lower()

    def test_strips_event_handlers(self):

        svg = '<svg xmlns="http://www.w3.org/2000/svg"><rect onclick="alert(1)" width="10"/></svg>'
        result = sanitize_svg(svg)
        assert "onclick" not in result.lower()
        assert "<rect" in result.lower()

    def test_strips_foreign_object(self):

        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            "<foreignObject><body>hi</body></foreignObject>"
            '<circle r="5"/>'
            "</svg>"
        )
        result = sanitize_svg(svg)
        assert "<foreignobject" not in result.lower()
        assert "<circle" in result.lower()


# ---------------------------------------------------------------------------
# TestValidateAsset
# ---------------------------------------------------------------------------


class TestValidateAsset:
    def test_full_chain_valid_png(self):

        path = _write_tmp(_make_png_bytes(), suffix=".png")
        try:
            assert validate_asset(path, skip_clamav=True) is True
        finally:
            path.unlink(missing_ok=True)

    def test_oversized_file_rejected(self):

        path = _write_tmp(_make_png_bytes(), suffix=".png")
        try:
            # Set max_size to 1 byte — file is bigger than that
            assert validate_asset(path, max_size_bytes=1, skip_clamav=True) is False
        finally:
            path.unlink(missing_ok=True)

    def test_text_file_rejected_by_mime(self):

        path = _write_tmp(b"not an image at all", suffix=".png")
        try:
            assert validate_asset(path, skip_clamav=True) is False
        finally:
            path.unlink(missing_ok=True)
