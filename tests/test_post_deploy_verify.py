# tests/test_post_deploy_verify.py
"""Tests for sastaspace.post_deploy_verify — post-deploy URL verification."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from sastaspace.post_deploy_verify import (
    VerifyResult,
    _should_check,
    verify_urls,
)

# --- _should_check ---


class TestShouldCheck:
    def test_http_url(self):
        assert _should_check("https://example.com/image.jpg") is True

    def test_empty_string(self):
        assert _should_check("") is False

    def test_hash_anchor(self):
        assert _should_check("#section") is False

    def test_javascript_url(self):
        assert _should_check("javascript:void(0)") is False

    def test_mailto(self):
        assert _should_check("mailto:test@example.com") is False

    def test_tel(self):
        assert _should_check("tel:+1234567890") is False

    def test_data_uri(self):
        assert _should_check("data:image/svg+xml,...") is False

    def test_relative_path(self):
        assert _should_check("/images/logo.png") is False

    def test_very_long_url(self):
        assert _should_check("https://example.com/" + "a" * 2000) is False


# --- VerifyResult ---


class TestVerifyResult:
    def test_ok_when_no_broken(self):
        r = VerifyResult(total_images=5, total_links=10)
        assert r.ok is True

    def test_not_ok_with_broken_images(self):
        r = VerifyResult(broken_images=["https://example.com/404.jpg"])
        assert r.ok is False

    def test_not_ok_with_broken_links(self):
        r = VerifyResult(broken_links=["https://example.com/missing"])
        assert r.ok is False

    def test_summary_format(self):
        r = VerifyResult(
            total_images=3,
            broken_images=["https://x.com/broken.jpg"],
            total_links=5,
            broken_links=[],
            skipped=2,
        )
        s = r.summary()
        assert "images=3" in s
        assert "broken=1" in s
        assert "links=5" in s
        assert "skipped=2" in s


# --- verify_urls ---


def _make_check_url_mock(status_map: dict[str, int | None]):
    """Create a mock for _check_url that returns statuses from a map."""

    async def mock_check_url(url, semaphore):
        return url, status_map.get(url)

    return mock_check_url


class TestVerifyUrls:
    @pytest.mark.asyncio
    async def test_empty_html(self):
        result = await verify_urls("")
        assert result.ok is True
        assert result.total_images == 0
        assert result.total_links == 0

    @pytest.mark.asyncio
    async def test_only_anchors_and_relative_links(self):
        html = """
        <html><body>
            <a href="#top">Top</a>
            <a href="/about">About</a>
            <img src="/local/image.png">
        </body></html>
        """
        result = await verify_urls(html)
        assert result.total_images == 1
        assert result.total_links == 2
        assert result.ok is True
        assert result.skipped == 3

    @pytest.mark.asyncio
    async def test_broken_image_detected(self):
        html = '<html><body><img src="https://fake.com/missing.jpg"></body></html>'
        mock = _make_check_url_mock({"https://fake.com/missing.jpg": 404})

        with patch("sastaspace.post_deploy_verify._check_url", side_effect=mock):
            result = await verify_urls(html)

        assert result.total_images == 1
        assert len(result.broken_images) == 1
        assert "fake.com/missing.jpg" in result.broken_images[0]

    @pytest.mark.asyncio
    async def test_healthy_image_passes(self):
        html = '<html><body><img src="https://example.com/logo.png"></body></html>'
        mock = _make_check_url_mock({"https://example.com/logo.png": 200})

        with patch("sastaspace.post_deploy_verify._check_url", side_effect=mock):
            result = await verify_urls(html)

        assert result.total_images == 1
        assert result.ok is True

    @pytest.mark.asyncio
    async def test_mixed_images_and_links(self):
        html = """
        <html><body>
            <img src="https://good.com/image.png">
            <img src="https://bad.com/missing.jpg">
            <a href="https://good.com/page">Good</a>
            <a href="https://bad.com/404">Bad</a>
            <a href="#anchor">Anchor</a>
            <a href="mailto:x@y.com">Email</a>
        </body></html>
        """
        mock = _make_check_url_mock(
            {
                "https://good.com/image.png": 200,
                "https://bad.com/missing.jpg": 404,
                "https://good.com/page": 200,
                "https://bad.com/404": 404,
            }
        )

        with patch("sastaspace.post_deploy_verify._check_url", side_effect=mock):
            result = await verify_urls(html)

        assert result.total_images == 2
        assert result.total_links == 4
        assert len(result.broken_images) == 1
        assert "bad.com/missing.jpg" in result.broken_images[0]
        assert len(result.broken_links) == 1
        assert "bad.com/404" in result.broken_links[0]
        assert result.skipped == 2  # #anchor and mailto

    @pytest.mark.asyncio
    async def test_connection_error_treated_as_broken(self):
        html = '<html><body><img src="https://unreachable.invalid/x.png"></body></html>'
        # None status = connection error
        mock = _make_check_url_mock({"https://unreachable.invalid/x.png": None})

        with patch("sastaspace.post_deploy_verify._check_url", side_effect=mock):
            result = await verify_urls(html)

        assert result.total_images == 1
        assert len(result.broken_images) == 1

    @pytest.mark.asyncio
    async def test_deduplicates_urls(self):
        html = """
        <html><body>
            <img src="https://example.com/img.png">
            <img src="https://example.com/img.png">
            <img src="https://example.com/img.png">
        </body></html>
        """
        call_count = 0

        async def counting_mock(url, semaphore):
            nonlocal call_count
            call_count += 1
            return url, 200

        with patch("sastaspace.post_deploy_verify._check_url", side_effect=counting_mock):
            result = await verify_urls(html)

        assert result.total_images == 3
        assert call_count == 1  # Only 1 unique URL checked
        assert result.ok is True
