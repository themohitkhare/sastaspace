# tests/test_jobs_crawl_data.py
"""Tests for site_colors / site_title persistence after crawl."""

from unittest.mock import AsyncMock, patch

import pytest

from sastaspace.database import JobUpdate, update_job


@pytest.mark.asyncio
async def test_update_job_accepts_site_colors_and_title():
    """update_job() must accept site_colors and site_title kwargs without error."""
    with patch("sastaspace.database._get_db") as mock_db:
        mock_collection = AsyncMock()
        mock_db.return_value.__getitem__ = lambda self, key: mock_collection
        mock_collection.update_one = AsyncMock()

        # Should not raise
        await update_job(
            "job-123",
            updates=JobUpdate(
                site_colors=["#ff0000", "#00ff00"],
                site_title="Test Site",
            ),
        )

        # update_one was called with the new fields
        update_one_call = mock_collection.update_one.call_args
        set_doc = update_one_call[0][1]["$set"]
        assert set_doc["site_colors"] == ["#ff0000", "#00ff00"]
        assert set_doc["site_title"] == "Test Site"


@pytest.mark.asyncio
async def test_update_job_site_fields_optional():
    """site_colors and site_title are optional — omitting them must not add them."""
    with patch("sastaspace.database._get_db") as mock_db:
        mock_collection = AsyncMock()
        mock_db.return_value.__getitem__ = lambda self, key: mock_collection
        mock_collection.update_one = AsyncMock()

        await update_job("job-123", status="crawling")

        set_doc = mock_collection.update_one.call_args[0][1]["$set"]
        assert "site_colors" not in set_doc
        assert "site_title" not in set_doc
