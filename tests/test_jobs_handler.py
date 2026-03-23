# tests/test_jobs_handler.py
"""Tests for redesign_handler in sastaspace/jobs.py — checkpoint, status, and serialization."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sastaspace.crawler import CrawlResult
from sastaspace.database import JobStatus
from sastaspace.deployer import DeployResult
from sastaspace.jobs import (
    _CRAWL_FIELDS,
    _deserialize_crawl_result,
    _serialize_crawl_result,
    redesign_handler,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_crawl_result(**overrides) -> CrawlResult:
    """Create a CrawlResult with sensible defaults."""
    defaults = dict(
        url="https://example.com",
        title="Example Site",
        meta_description="A test description",
        favicon_url="https://example.com/favicon.ico",
        html_source="<html><body>Hello</body></html>",
        screenshot_base64="abc123",
        headings=["H1 Heading"],
        navigation_links=[{"text": "Home", "href": "/"}],
        text_content="Some text",
        images=[{"src": "/img.png", "alt": "pic"}],
        colors=["#ff0000", "#00ff00"],
        fonts=["Inter"],
        sections=[{"type": "hero", "content": "Welcome"}],
        error="",
    )
    defaults.update(overrides)
    return CrawlResult(**defaults)


def _make_enhanced_result(crawl_result: CrawlResult) -> MagicMock:
    """Create a mock EnhancedCrawlResult wrapping a CrawlResult."""
    enhanced = MagicMock()
    enhanced.homepage = crawl_result
    enhanced.internal_pages = []
    enhanced.assets = MagicMock(assets=[], total_size_bytes=0)
    enhanced.business_profile = None
    return enhanced


def _make_deploy_result() -> DeployResult:
    return DeployResult(
        subdomain="example-com",
        index_path=Path("/data/sites/example-com/index.html"),
        sites_dir=Path("/data/sites"),
    )


@pytest.fixture
def job_service():
    """A mock JobService with a trackable publish_status."""
    svc = MagicMock()
    svc.publish_status = AsyncMock()
    return svc


def _settings_mock():
    """Return a Settings-like mock without touching env."""
    m = MagicMock()
    m.use_agno_pipeline = True
    m.sites_dir = Path("/data/sites")
    m.espocrm_url = ""  # Disabled — uses NoopEspoCRMClient
    m.espocrm_api_key = ""
    return m


# ---------------------------------------------------------------------------
# _serialize / _deserialize roundtrip
# ---------------------------------------------------------------------------


class TestSerializeDeserializeRoundtrip:
    """Verify CrawlResult survives a serialize→deserialize cycle."""

    def test_roundtrip_preserves_all_fields(self):
        cr = _make_crawl_result()
        data = _serialize_crawl_result(cr)
        restored = _deserialize_crawl_result(data)
        for f in _CRAWL_FIELDS:
            assert getattr(restored, f) == getattr(cr, f), f"Mismatch on field '{f}'"

    def test_deserialize_fills_missing_with_empty(self):
        """If the stored dict is missing a field, default to empty string."""
        restored = _deserialize_crawl_result({"url": "https://x.com"})
        assert restored.url == "https://x.com"
        assert restored.title == ""
        assert restored.error == ""

    def test_serialize_keys_match_crawl_fields(self):
        cr = _make_crawl_result()
        data = _serialize_crawl_result(cr)
        assert set(data.keys()) == set(_CRAWL_FIELDS)


# ---------------------------------------------------------------------------
# redesign_handler — happy path
# ---------------------------------------------------------------------------


class TestRedesignHandlerHappyPath:
    """Full run: crawl → redesign → deploy, no checkpoint."""

    @pytest.mark.asyncio
    async def test_emits_correct_status_progression(self, job_service):
        cr = _make_crawl_result()
        er = _make_enhanced_result(cr)
        dr = _make_deploy_result()

        with (
            patch("sastaspace.jobs.Settings", return_value=_settings_mock()),
            patch(
                "sastaspace.jobs.enhanced_crawl",
                create=True,
                new_callable=AsyncMock,
                return_value=er,
            ),
            patch("sastaspace.jobs.update_job", new_callable=AsyncMock) as mock_update,
            patch(
                "sastaspace.jobs.run_redesign",
                return_value="<!DOCTYPE html><html><head></head><body>test</body></html>",
            ) as _mock_rr,
            patch("sastaspace.jobs.deploy", return_value=dr),
            patch("sastaspace.jobs.register_site", new_callable=AsyncMock),
            patch("sastaspace.jobs.url_hash", return_value="fakehash"),
        ):
            await redesign_handler("job-1", "https://example.com", "premium", job_service)

        # Collect the status values from update_job calls
        statuses = [
            call.kwargs.get("status") or (call.args[1] if len(call.args) > 1 else None)
            for call in mock_update.call_args_list
            if "status" in (call.kwargs or {})
        ]
        assert JobStatus.CRAWLING.value in statuses
        assert JobStatus.REDESIGNING.value in statuses
        assert JobStatus.DEPLOYING.value in statuses
        assert JobStatus.DONE.value in statuses

    @pytest.mark.asyncio
    async def test_checkpoint_cleared_on_done(self, job_service):
        cr = _make_crawl_result()
        er = _make_enhanced_result(cr)
        dr = _make_deploy_result()

        with (
            patch("sastaspace.jobs.Settings", return_value=_settings_mock()),
            patch(
                "sastaspace.jobs.enhanced_crawl",
                create=True,
                new_callable=AsyncMock,
                return_value=er,
            ),
            patch("sastaspace.jobs.update_job", new_callable=AsyncMock) as mock_update,
            patch(
                "sastaspace.jobs.run_redesign",
                return_value="<!DOCTYPE html><html><head></head><body>test</body></html>",
            ),
            patch("sastaspace.jobs.deploy", return_value=dr),
            patch("sastaspace.jobs.register_site", new_callable=AsyncMock),
            patch("sastaspace.jobs.url_hash", return_value="fakehash"),
        ):
            await redesign_handler("job-1", "https://example.com", "premium", job_service)

        # The final update_job call (done) should pass checkpoint=None
        final_call = mock_update.call_args_list[-1]
        assert final_call.kwargs.get("checkpoint") is None

    @pytest.mark.asyncio
    async def test_publish_done_event(self, job_service):
        cr = _make_crawl_result()
        er = _make_enhanced_result(cr)
        dr = _make_deploy_result()

        with (
            patch("sastaspace.jobs.Settings", return_value=_settings_mock()),
            patch(
                "sastaspace.jobs.enhanced_crawl",
                create=True,
                new_callable=AsyncMock,
                return_value=er,
            ),
            patch("sastaspace.jobs.update_job", new_callable=AsyncMock),
            patch(
                "sastaspace.jobs.run_redesign",
                return_value="<!DOCTYPE html><html><head></head><body>test</body></html>",
            ),
            patch("sastaspace.jobs.deploy", return_value=dr),
            patch("sastaspace.jobs.register_site", new_callable=AsyncMock),
            patch("sastaspace.jobs.url_hash", return_value="fakehash"),
        ):
            await redesign_handler("job-1", "https://example.com", "premium", job_service)

        # Last publish should be "done"
        done_calls = [c for c in job_service.publish_status.call_args_list if c.args[1] == "done"]
        assert len(done_calls) == 1
        assert done_calls[0].args[2]["subdomain"] == "example-com"


# ---------------------------------------------------------------------------
# redesign_handler — checkpoint: skip crawl
# ---------------------------------------------------------------------------


class TestRedesignHandlerCheckpoint:
    """When a checkpoint with completed_step='crawl' is provided, crawling is skipped."""

    @pytest.mark.asyncio
    async def test_skip_crawl_from_checkpoint(self, job_service):
        cr = _make_crawl_result()
        crawl_data = _serialize_crawl_result(cr)
        checkpoint = {
            "completed_step": "crawl",
            "crawl_result": crawl_data,
            "pipeline_data": {},
        }

        mock_crawl = AsyncMock()
        dr = _make_deploy_result()

        with (
            patch("sastaspace.jobs.Settings", return_value=_settings_mock()),
            patch("sastaspace.jobs.enhanced_crawl", mock_crawl, create=True),
            patch("sastaspace.jobs.update_job", new_callable=AsyncMock),
            patch(
                "sastaspace.jobs.run_redesign",
                return_value="<!DOCTYPE html><html><head></head><body>test</body></html>",
            ),
            patch("sastaspace.jobs.deploy", return_value=dr),
            patch("sastaspace.jobs.register_site", new_callable=AsyncMock),
            patch("sastaspace.jobs.url_hash", return_value="fakehash"),
        ):
            await redesign_handler(
                "job-cp", "https://example.com", "premium", job_service, checkpoint=checkpoint
            )

        # enhanced_crawl() should NOT have been called
        mock_crawl.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_crawl_with_pipeline_data(self, job_service):
        """pipeline_data present also triggers skip_crawl."""
        cr = _make_crawl_result()
        crawl_data = _serialize_crawl_result(cr)
        checkpoint = {
            "completed_step": "redesigning",
            "crawl_result": crawl_data,
            "pipeline_data": {"some_key": "some_val"},
        }

        mock_crawl = AsyncMock()
        dr = _make_deploy_result()

        with (
            patch("sastaspace.jobs.Settings", return_value=_settings_mock()),
            patch("sastaspace.jobs.enhanced_crawl", mock_crawl, create=True),
            patch("sastaspace.jobs.update_job", new_callable=AsyncMock),
            patch(
                "sastaspace.jobs.run_redesign",
                return_value="<!DOCTYPE html><html><head></head><body>test</body></html>",
            ),
            patch("sastaspace.jobs.deploy", return_value=dr),
            patch("sastaspace.jobs.register_site", new_callable=AsyncMock),
            patch("sastaspace.jobs.url_hash", return_value="fakehash"),
        ):
            await redesign_handler(
                "job-cp2", "https://example.com", "premium", job_service, checkpoint=checkpoint
            )

        mock_crawl.assert_not_called()


# ---------------------------------------------------------------------------
# redesign_handler — crawl failure
# ---------------------------------------------------------------------------


class TestRedesignHandlerCrawlFailure:
    """When crawl returns an error, the handler sets FAILED status and stops."""

    @pytest.mark.asyncio
    async def test_failed_crawl_sets_error_status(self, job_service):
        bad_cr = _make_crawl_result(error="Connection timeout")
        bad_er = _make_enhanced_result(bad_cr)

        with (
            patch("sastaspace.jobs.Settings", return_value=_settings_mock()),
            patch(
                "sastaspace.jobs.enhanced_crawl",
                create=True,
                new_callable=AsyncMock,
                return_value=bad_er,
            ),
            patch("sastaspace.jobs.update_job", new_callable=AsyncMock) as mock_update,
        ):
            await redesign_handler("job-fail", "https://bad.example.com", "free", job_service)

        # Should have set status=FAILED
        failed_calls = [
            c
            for c in mock_update.call_args_list
            if c.kwargs.get("status") == JobStatus.FAILED.value
        ]
        assert len(failed_calls) >= 1

        # Should have published an error event
        error_publishes = [
            c for c in job_service.publish_status.call_args_list if c.args[1] == "error"
        ]
        assert len(error_publishes) >= 1

    @pytest.mark.asyncio
    async def test_failed_crawl_does_not_deploy(self, job_service):
        bad_cr = _make_crawl_result(error="DNS resolution failed")
        bad_er = _make_enhanced_result(bad_cr)
        mock_deploy = MagicMock()

        with (
            patch("sastaspace.jobs.Settings", return_value=_settings_mock()),
            patch(
                "sastaspace.jobs.enhanced_crawl",
                create=True,
                new_callable=AsyncMock,
                return_value=bad_er,
            ),
            patch("sastaspace.jobs.update_job", new_callable=AsyncMock),
            patch("sastaspace.jobs.deploy", mock_deploy),
        ):
            await redesign_handler("job-fail2", "https://bad.example.com", "free", job_service)

        mock_deploy.assert_not_called()
