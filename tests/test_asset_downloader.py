# tests/test_asset_downloader.py
"""Tests for the asset downloader module."""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sastaspace.asset_downloader import (
    _is_safe_url,
    download_and_validate_assets,
    extract_asset_urls,
    is_stock_photo,
    normalize_url,
    slugify_filename,
)

# --- TestExtractAssetUrls ---


class TestExtractAssetUrls:
    """Tests for extract_asset_urls()."""

    def test_extracts_img_src(self):
        html = '<html><body><img src="/images/logo.png"></body></html>'
        urls = extract_asset_urls(html, "https://example.com")
        assert "https://example.com/images/logo.png" in urls

    def test_extracts_img_srcset(self):
        html = '<html><body><img srcset="/img/hero-2x.jpg 2x, /img/hero.jpg 1x"></body></html>'
        urls = extract_asset_urls(html, "https://example.com")
        assert "https://example.com/img/hero-2x.jpg" in urls
        assert "https://example.com/img/hero.jpg" in urls

    def test_extracts_meta_og_image(self):
        html = '<html><head><meta property="og:image" content="https://example.com/og.jpg"></head></html>'
        urls = extract_asset_urls(html, "https://example.com")
        assert "https://example.com/og.jpg" in urls

    def test_extracts_link_icon(self):
        html = '<html><head><link rel="icon" href="/favicon.ico"></head></html>'
        urls = extract_asset_urls(html, "https://example.com")
        assert "https://example.com/favicon.ico" in urls

    def test_extracts_shortcut_icon(self):
        html = '<html><head><link rel="shortcut icon" href="/favicon.ico"></head></html>'
        urls = extract_asset_urls(html, "https://example.com")
        assert "https://example.com/favicon.ico" in urls

    def test_extracts_apple_touch_icon(self):
        html = '<html><head><link rel="apple-touch-icon" href="/apple-icon.png"></head></html>'
        urls = extract_asset_urls(html, "https://example.com")
        assert "https://example.com/apple-icon.png" in urls

    def test_extracts_background_image(self):
        html = '<html><body><div style="background-image: url(/bg.jpg)"></div></body></html>'
        urls = extract_asset_urls(html, "https://example.com")
        assert "https://example.com/bg.jpg" in urls

    def test_skips_data_uris(self):
        html = '<html><body><img src="data:image/png;base64,abc123"></body></html>'
        urls = extract_asset_urls(html, "https://example.com")
        assert len(urls) == 0

    def test_skips_blob_uris(self):
        html = '<html><body><img src="blob:https://example.com/abc"></body></html>'
        urls = extract_asset_urls(html, "https://example.com")
        assert len(urls) == 0

    def test_deduplicates(self):
        html = """<html><body>
        <img src="/logo.png">
        <img src="/logo.png">
        <img src="/logo.png">
        </body></html>"""
        urls = extract_asset_urls(html, "https://example.com")
        assert urls.count("https://example.com/logo.png") == 1

    def test_limits_count(self):
        imgs = "".join(f'<img src="/img{i}.png">' for i in range(20))
        html = f"<html><body>{imgs}</body></html>"
        urls = extract_asset_urls(html, "https://example.com", max_per_page=10)
        assert len(urls) == 10

    def test_resolves_relative_urls(self):
        html = '<html><body><img src="images/photo.jpg"></body></html>'
        urls = extract_asset_urls(html, "https://example.com/about/")
        assert "https://example.com/about/images/photo.jpg" in urls

    def test_handles_absolute_urls(self):
        html = '<html><body><img src="https://cdn.example.com/pic.png"></body></html>'
        urls = extract_asset_urls(html, "https://example.com")
        assert "https://cdn.example.com/pic.png" in urls


# --- TestSlugifyFilename ---


class TestSlugifyFilename:
    """Tests for slugify_filename()."""

    def test_basic_slugification(self):
        assert slugify_filename("My Image.png") == "my-image.png"

    def test_preserves_extension(self):
        result = slugify_filename("photo.JPG")
        assert result.endswith(".jpg")

    def test_replaces_special_chars(self):
        result = slugify_filename("Hero Banner (1).PNG")
        assert result == "hero-banner-1.png"

    def test_truncates_long_names(self):
        long_name = "a" * 100 + ".png"
        result = slugify_filename(long_name)
        assert len(result) <= 64  # 60 stem + extension
        assert result.endswith(".png")

    def test_collapses_consecutive_hyphens(self):
        result = slugify_filename("img---test---file.jpg")
        assert "--" not in result

    def test_strips_leading_trailing_hyphens(self):
        result = slugify_filename("-image-.png")
        assert not result.startswith("-")
        # The extension portion may start right after the stem

    def test_handles_no_extension(self):
        result = slugify_filename("imagefile")
        assert result == "imagefile"


# --- TestNormalizeUrl ---


class TestNormalizeUrl:
    """Tests for normalize_url()."""

    def test_strips_cache_busting_params(self):
        assert normalize_url("https://example.com/logo.png?v=123") == (
            "https://example.com/logo.png"
        )

    def test_strips_fragment(self):
        assert normalize_url("https://example.com/logo.png#section") == (
            "https://example.com/logo.png"
        )

    def test_strips_timestamp_param(self):
        assert normalize_url("https://example.com/img.jpg?t=1234567890") == (
            "https://example.com/img.jpg"
        )

    def test_preserves_meaningful_path(self):
        url = "https://example.com/images/hero.jpg"
        assert normalize_url(url) == url

    def test_strips_all_query_params(self):
        url = "https://example.com/pic.png?w=100&h=200&v=5"
        assert normalize_url(url) == "https://example.com/pic.png"


# --- TestIsStockPhoto ---


class TestIsStockPhoto:
    """Tests for is_stock_photo()."""

    def test_detects_unsplash(self):
        assert is_stock_photo("https://images.unsplash.com/photo-abc123") is True

    def test_detects_pexels(self):
        assert is_stock_photo("https://images.pexels.com/photos/123/large.jpg") is True

    def test_detects_shutterstock(self):
        assert is_stock_photo("https://image.shutterstock.com/img-456.jpg") is True

    def test_detects_istockphoto(self):
        assert is_stock_photo("https://media.istockphoto.com/photo.jpg") is True

    def test_detects_gettyimages(self):
        assert is_stock_photo("https://media.gettyimages.com/photo.jpg") is True

    def test_detects_pixabay(self):
        assert is_stock_photo("https://cdn.pixabay.com/photo/pic.jpg") is True

    def test_detects_stock_adobe(self):
        assert is_stock_photo("https://stock.adobe.com/images/123") is True

    def test_allows_own_domain(self):
        assert is_stock_photo("https://example.com/logo.png") is False

    def test_allows_cdn_subdomain(self):
        assert is_stock_photo("https://cdn.mysite.com/image.jpg") is False


# --- TestDownloadAndValidateAssets ---


def _make_mock_session(mock_response):
    """Create a properly structured mock aiohttp.ClientSession.

    aiohttp.ClientSession() is a regular constructor (not async), but the
    returned object is an async context manager. Each session.get() call
    also returns an async context manager wrapping the response.
    """

    class _FakeResponse:
        """Async context manager wrapping a mock response."""

        def __init__(self):
            self._resp = mock_response

        async def __aenter__(self):
            return self._resp

        async def __aexit__(self, *args):
            pass

    class _FakeSession:
        """Async context manager wrapping a mock session."""

        def get(self, *args, **kwargs):
            return _FakeResponse()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    def _constructor(*args, **kwargs):
        return _FakeSession()

    return _constructor


class TestDownloadAndValidateAssets:
    """Tests for download_and_validate_assets()."""

    @pytest.fixture
    def tmp_dir(self):
        with tempfile.TemporaryDirectory() as d:
            yield Path(d)

    @pytest.fixture
    def _fake_png_bytes(self):
        """Minimal valid-ish bytes for a fake PNG."""
        return b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

    async def test_downloads_and_returns_manifest(self, tmp_dir, _fake_png_bytes):
        """Test basic download flow with mocked HTTP and validation."""
        urls = ["https://example.com/logo.png"]

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {"Content-Type": "image/png"}
        mock_response.content = MagicMock()

        chunks = [_fake_png_bytes, b""]
        call_count = [0]

        async def read_chunk(size):
            if call_count[0] < len(chunks):
                chunk = chunks[call_count[0]]
                call_count[0] += 1
                return chunk
            return b""

        mock_response.content.read = read_chunk

        with (
            patch(
                "sastaspace.asset_downloader.aiohttp.ClientSession",
                _make_mock_session(mock_response),
            ),
            patch("sastaspace.asset_downloader.validate_asset", return_value=True),
            patch(
                "sastaspace.asset_downloader.file_hash",
                return_value=hashlib.sha256(_fake_png_bytes).hexdigest(),
            ),
        ):
            manifest = await download_and_validate_assets(urls, tmp_dir, skip_clamav=True)

        assert manifest.total_size_bytes > 0
        assert len(manifest.assets) == 1
        assert manifest.assets[0].original_url == "https://example.com/logo.png"

    async def test_skips_stock_photos(self, tmp_dir):
        """Stock photo URLs should be filtered out before download."""
        urls = ["https://images.unsplash.com/photo-abc"]
        manifest = await download_and_validate_assets(urls, tmp_dir, skip_clamav=True)
        assert len(manifest.assets) == 0

    async def test_respects_total_limit(self, tmp_dir, _fake_png_bytes):
        """Should not download more than max_total assets."""
        urls = [f"https://example.com/img{i}.png" for i in range(40)]

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {"Content-Type": "image/png"}
        mock_response.content = MagicMock()

        counter = [0]

        async def read_chunk(size):
            # Each "file" gets unique content so dedup doesn't collapse them
            counter[0] += 1
            if counter[0] % 2 == 1:
                return _fake_png_bytes + counter[0].to_bytes(4, "big")
            return b""

        mock_response.content.read = read_chunk

        with (
            patch(
                "sastaspace.asset_downloader.aiohttp.ClientSession",
                _make_mock_session(mock_response),
            ),
            patch("sastaspace.asset_downloader.validate_asset", return_value=True),
            patch("sastaspace.asset_downloader.file_hash", side_effect=lambda p: str(p)),
        ):
            manifest = await download_and_validate_assets(
                urls, tmp_dir, skip_clamav=True, max_total=30
            )

        # At most 30 URLs attempted (total limit)
        assert len(manifest.assets) <= 30

    async def test_content_hash_dedup(self, tmp_dir, _fake_png_bytes):
        """Two different URLs with same content should produce one asset."""
        urls = [
            "https://example.com/logo.png",
            "https://cdn.example.com/logo.png",
        ]
        the_hash = hashlib.sha256(_fake_png_bytes).hexdigest()

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {"Content-Type": "image/png"}
        mock_response.content = MagicMock()

        counter = [0]

        async def read_chunk(size):
            counter[0] += 1
            if counter[0] % 2 == 1:
                return _fake_png_bytes
            return b""

        mock_response.content.read = read_chunk

        with (
            patch(
                "sastaspace.asset_downloader.aiohttp.ClientSession",
                _make_mock_session(mock_response),
            ),
            patch("sastaspace.asset_downloader.validate_asset", return_value=True),
            patch("sastaspace.asset_downloader.file_hash", return_value=the_hash),
        ):
            manifest = await download_and_validate_assets(urls, tmp_dir, skip_clamav=True)

        # Content-hash dedup means only 1 unique asset
        assert len(manifest.assets) == 1

    async def test_skips_failed_validation(self, tmp_dir, _fake_png_bytes):
        """Assets that fail validation should not appear in manifest."""
        urls = ["https://example.com/bad.png"]

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {"Content-Type": "image/png"}
        mock_response.content = MagicMock()

        chunks = [_fake_png_bytes, b""]
        idx = [0]

        async def read_chunk(size):
            if idx[0] < len(chunks):
                c = chunks[idx[0]]
                idx[0] += 1
                return c
            return b""

        mock_response.content.read = read_chunk

        with (
            patch(
                "sastaspace.asset_downloader.aiohttp.ClientSession",
                _make_mock_session(mock_response),
            ),
            patch("sastaspace.asset_downloader.validate_asset", return_value=False),
            patch("sastaspace.asset_downloader.file_hash", return_value="abc"),
        ):
            manifest = await download_and_validate_assets(urls, tmp_dir, skip_clamav=True)

        assert len(manifest.assets) == 0

    async def test_empty_urls_returns_empty_manifest(self, tmp_dir):
        """Empty URL list should return empty manifest."""
        manifest = await download_and_validate_assets([], tmp_dir)
        assert len(manifest.assets) == 0
        assert manifest.total_size_bytes == 0


# --- TestIsSafeUrl (SSRF protection) ---


class TestIsSafeUrl:
    """Tests for _is_safe_url() SSRF protection."""

    def test_blocks_localhost(self):
        assert _is_safe_url("http://localhost/secret") is False

    def test_blocks_127_0_0_1(self):
        assert _is_safe_url("http://127.0.0.1/admin") is False

    def test_blocks_127_x_x_x(self):
        assert _is_safe_url("http://127.0.0.2:8080/") is False

    @patch(
        "sastaspace.asset_downloader.socket.getaddrinfo",
        return_value=[
            (2, 1, 6, "", ("10.0.0.1", 0)),
        ],
    )
    def test_blocks_10_x_x_x(self, _mock):
        assert _is_safe_url("http://internal.corp/data") is False

    @patch(
        "sastaspace.asset_downloader.socket.getaddrinfo",
        return_value=[
            (2, 1, 6, "", ("192.168.1.1", 0)),
        ],
    )
    def test_blocks_192_168_x_x(self, _mock):
        assert _is_safe_url("http://router.local/config") is False

    @patch(
        "sastaspace.asset_downloader.socket.getaddrinfo",
        return_value=[
            (2, 1, 6, "", ("172.16.0.5", 0)),
        ],
    )
    def test_blocks_172_16_x_x(self, _mock):
        assert _is_safe_url("http://private.net/api") is False

    @patch(
        "sastaspace.asset_downloader.socket.getaddrinfo",
        return_value=[
            (2, 1, 6, "", ("169.254.169.254", 0)),
        ],
    )
    def test_blocks_link_local_169_254(self, _mock):
        assert _is_safe_url("http://metadata.google/v1") is False

    def test_blocks_file_scheme(self):
        assert _is_safe_url("file:///etc/passwd") is False

    def test_blocks_ftp_scheme(self):
        assert _is_safe_url("ftp://evil.com/payload") is False

    def test_blocks_gopher_scheme(self):
        assert _is_safe_url("gopher://evil.com/exploit") is False

    def test_blocks_data_scheme(self):
        assert _is_safe_url("data:text/html,<h1>hi</h1>") is False

    def test_blocks_empty_hostname(self):
        assert _is_safe_url("http:///no-host") is False

    def test_blocks_ipv6_loopback(self):
        assert _is_safe_url("http://[::1]/admin") is False

    @patch(
        "sastaspace.asset_downloader.socket.getaddrinfo",
        return_value=[
            (2, 1, 6, "", ("93.184.216.34", 0)),
        ],
    )
    def test_allows_valid_https(self, _mock):
        assert _is_safe_url("https://example.com/image.png") is True

    @patch(
        "sastaspace.asset_downloader.socket.getaddrinfo",
        return_value=[
            (2, 1, 6, "", ("93.184.216.34", 0)),
        ],
    )
    def test_allows_valid_http(self, _mock):
        assert _is_safe_url("http://example.com/page") is True

    def test_blocks_dns_failure(self):
        """Unresolvable hostnames should be blocked by default."""
        assert _is_safe_url("http://this-domain-definitely-does-not-exist-xyz.invalid/") is False
