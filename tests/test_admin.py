# tests/test_admin.py
"""Tests for admin operations and webhook handling."""

from __future__ import annotations

import hashlib
import hmac
import time
from unittest.mock import AsyncMock, patch

import pytest


class TestWebhookVerification:
    def test_valid_signature_passes(self):
        from sastaspace.admin import verify_webhook_signature

        secret = "test-secret"
        body = b'{"event":"redesignJob.updated"}'
        timestamp = str(int(time.time()))
        sig = hmac.new(
            secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256
        ).hexdigest()
        assert verify_webhook_signature(body, sig, timestamp, secret) is True

    def test_invalid_signature_fails(self):
        from sastaspace.admin import verify_webhook_signature

        assert verify_webhook_signature(b"body", "badsig", str(int(time.time())), "secret") is False

    def test_expired_timestamp_fails(self):
        from sastaspace.admin import verify_webhook_signature

        old_timestamp = str(int(time.time()) - 600)  # 10 min ago
        body = b"body"
        sig = hmac.new(b"secret", old_timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
        assert verify_webhook_signature(body, sig, old_timestamp, "secret") is False


class TestDeleteSiteFiles:
    @pytest.mark.asyncio
    async def test_deletes_site_directory(self, tmp_path):
        from sastaspace.admin import delete_site_files

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
        from sastaspace.admin import delete_site_files

        # Should not raise
        await delete_site_files("nonexistent", sites_dir=tmp_path / "sites")


class TestGetOriginalUrl:
    @pytest.mark.asyncio
    async def test_returns_url_from_db(self):
        from sastaspace.admin import get_original_url_from_db

        with patch("sastaspace.admin.find_site_by_subdomain", new_callable=AsyncMock) as mock:
            mock.return_value = {"original_url": "https://example.com"}
            url = await get_original_url_from_db("example-com")
            assert url == "https://example.com"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        from sastaspace.admin import get_original_url_from_db

        with patch("sastaspace.admin.find_site_by_subdomain", new_callable=AsyncMock) as mock:
            mock.return_value = None
            url = await get_original_url_from_db("nonexistent")
            assert url is None
