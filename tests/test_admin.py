# tests/test_admin.py
"""Tests for admin operations and webhook handling."""

from __future__ import annotations

import hashlib
import hmac
import time
from unittest.mock import AsyncMock, patch

import pytest

from sastaspace.admin import delete_site_files, get_original_url_from_db, verify_webhook_signature


class TestWebhookVerification:
    def test_valid_signature_passes(self):
        hmac_key = "test-hmac-value"
        body = b'{"event":"redesignJob.updated"}'
        # Timestamps in milliseconds
        timestamp = str(int(time.time() * 1000))
        string_to_sign = f"{timestamp}:{body.decode()}"
        sig = hmac.new(hmac_key.encode(), string_to_sign.encode(), hashlib.sha256).hexdigest()
        assert verify_webhook_signature(body, sig, timestamp, hmac_key) is True

    def test_invalid_signature_fails(self):
        ts = str(int(time.time() * 1000))
        assert verify_webhook_signature(b"body", "badsig", ts, "some-value") is False

    def test_expired_timestamp_fails(self):
        # 10 min ago in milliseconds
        old_timestamp = str(int((time.time() - 600) * 1000))
        body = b"body"
        string_to_sign = f"{old_timestamp}:{body.decode()}"
        sig = hmac.new(b"some-value", string_to_sign.encode(), hashlib.sha256).hexdigest()
        assert verify_webhook_signature(body, sig, old_timestamp, "some-value") is False


class TestDeleteSiteFiles:
    @pytest.mark.asyncio
    async def test_deletes_site_directory(self, tmp_path):
        site_dir = tmp_path / "sites" / "test-site"
        site_dir.mkdir(parents=True)
        (site_dir / "index.html").write_text("<html></html>")
        (site_dir / "metadata.json").write_text("{}")
        assets_dir = site_dir / "assets"
        assets_dir.mkdir()
        (assets_dir / "logo.png").write_bytes(b"fake")

        await delete_site_files("test-site", sites_dir=tmp_path / "sites")
        assert not site_dir.exists()

    @pytest.mark.asyncio
    async def test_noop_on_missing_site(self, tmp_path):
        # Should not raise
        await delete_site_files("nonexistent", sites_dir=tmp_path / "sites")


class TestGetOriginalUrl:
    @pytest.mark.asyncio
    async def test_returns_url_from_db(self):
        with patch("sastaspace.admin.find_site_by_subdomain", new_callable=AsyncMock) as mock:
            mock.return_value = {"original_url": "https://example.com"}
            url = await get_original_url_from_db("example-com")
            assert url == "https://example.com"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        with patch("sastaspace.admin.find_site_by_subdomain", new_callable=AsyncMock) as mock:
            mock.return_value = None
            url = await get_original_url_from_db("nonexistent")
            assert url is None
