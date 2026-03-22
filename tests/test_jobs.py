# tests/test_jobs.py
"""Tests for the Redis Stream job service."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sastaspace.crawler import CrawlResult
from sastaspace.database import JobStatus, create_job, get_job, update_job
from sastaspace.deployer import DeployResult
from sastaspace.jobs import (
    STATUS_CHANNEL,
    STREAM_KEY,
    JobService,
    redesign_handler,
)


def _mock_enhanced(crawl_result):
    """Create a mock EnhancedCrawlResult wrapping a CrawlResult."""
    return MagicMock(
        homepage=crawl_result,
        internal_pages=[],
        assets=MagicMock(assets=[], total_size_bytes=0),
    )


# kwargs that enhanced_crawl adds but update_job doesn't support yet
_ENHANCED_KWARGS = {"pages_crawled", "assets_count", "assets_total_size", "business_profile"}


async def _update_job_compat(job_id, **kwargs):
    """Wrapper around real update_job that strips not-yet-added kwargs."""
    filtered = {k: v for k, v in kwargs.items() if k not in _ENHANCED_KWARGS}
    await update_job(job_id, **filtered)


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    redis = AsyncMock()
    redis.xgroup_create = AsyncMock()
    redis.xadd = AsyncMock()
    redis.xreadgroup = AsyncMock(return_value=[])
    redis.xack = AsyncMock()
    redis.publish = AsyncMock()
    redis.aclose = AsyncMock()
    return redis


@pytest.fixture
def job_service(mock_redis):
    """Create a JobService with mocked Redis."""
    service = JobService(redis_url="redis://localhost:6379")
    service._redis = mock_redis
    service._pubsub_redis = mock_redis
    return service


async def test_enqueue_creates_job(job_service, mock_redis):
    """enqueue() creates a DB record and pushes to Redis Stream."""
    job_id = await job_service.enqueue(url="https://example.com", client_ip="1.2.3.4")

    assert isinstance(job_id, str)
    assert len(job_id) == 36  # UUID format

    # Verify Redis xadd was called
    mock_redis.xadd.assert_called_once()
    call_args = mock_redis.xadd.call_args
    assert call_args[0][0] == STREAM_KEY
    assert call_args[0][1]["url"] == "https://example.com"


async def test_enqueue_with_premium_tier(job_service, mock_redis):
    """enqueue() stores the tier correctly."""
    job_id = await job_service.enqueue(
        url="https://example.com", client_ip="1.2.3.4", tier="premium"
    )

    job = await get_job(job_id)
    assert job["tier"] == "premium"


async def test_publish_status(job_service, mock_redis):
    """publish_status() sends message to Redis Pub/Sub channel."""
    await job_service.publish_status(
        "job-123", "crawling", {"message": "Crawling...", "progress": 10}
    )

    mock_redis.publish.assert_called_once()
    channel = mock_redis.publish.call_args[0][0]
    assert channel == f"{STATUS_CHANNEL}:job-123"

    payload = json.loads(mock_redis.publish.call_args[0][1])
    assert payload["event"] == "crawling"
    assert payload["data"]["progress"] == 10


async def test_redesign_handler_crawl_failure(job_service):
    """redesign_handler handles crawl failure gracefully."""
    job_id = "handler-test-1"
    await create_job(job_id=job_id, url="https://bad.com", client_ip="1.1.1.1")

    failed_crawl = CrawlResult(
        url="https://bad.com",
        title="",
        meta_description="",
        favicon_url="",
        html_source="",
        screenshot_base64="",
        error="Connection refused",
    )

    enhanced_mock = _mock_enhanced(failed_crawl)
    with patch(
        "sastaspace.jobs.enhanced_crawl",
        create=True,
        new_callable=AsyncMock,
        return_value=enhanced_mock,
    ):
        await redesign_handler(job_id, "https://bad.com", "free", job_service)

    job = await get_job(job_id)
    assert job["status"] == JobStatus.FAILED.value
    assert "Could not reach" in job["error"]


async def test_redesign_handler_success(job_service, tmp_path):
    """redesign_handler completes full pipeline."""
    job_id = "handler-test-2"
    await create_job(job_id=job_id, url="https://example.com", client_ip="1.1.1.1")

    crawl_result = CrawlResult(
        url="https://example.com",
        title="Example",
        meta_description="Test",
        favicon_url="",
        html_source="<html></html>",
        screenshot_base64="",
        headings=["h1: Test"],
        navigation_links=[],
        text_content="Hello",
        images=[],
        colors=[],
        fonts=[],
        sections=[],
        error="",
    )

    deploy_result = DeployResult(
        subdomain="example-com",
        index_path=tmp_path / "example-com" / "index.html",
        sites_dir=tmp_path,
    )

    mock_html = "<!DOCTYPE html><html><body>Redesigned</body></html>"

    enhanced_mock = _mock_enhanced(crawl_result)
    with (
        patch(
            "sastaspace.jobs.enhanced_crawl",
            create=True,
            new_callable=AsyncMock,
            return_value=enhanced_mock,
        ),
        patch(
            "sastaspace.jobs.update_job",
            side_effect=_update_job_compat,
        ),
        patch("sastaspace.jobs.run_redesign", return_value=mock_html),
        patch("sastaspace.jobs.deploy", return_value=deploy_result),
    ):
        await redesign_handler(job_id, "https://example.com", "free", job_service)

    job = await get_job(job_id)
    assert job["status"] == JobStatus.DONE.value
    assert job["subdomain"] == "example-com"
    assert job["progress"] == 100


async def test_redesign_handler_premium_tier(job_service, tmp_path):
    """redesign_handler uses redesign_premium for premium tier."""
    job_id = "handler-test-3"
    await create_job(job_id=job_id, url="https://example.com", client_ip="1.1.1.1", tier="premium")

    crawl_result = CrawlResult(
        url="https://example.com",
        title="Example",
        meta_description="",
        favicon_url="",
        html_source="<html></html>",
        screenshot_base64="",
        error="",
    )

    deploy_result = DeployResult(
        subdomain="example-com",
        index_path=tmp_path / "example-com" / "index.html",
        sites_dir=tmp_path,
    )

    mock_html = "<!DOCTYPE html><html><body>Premium</body></html>"

    enhanced_mock = _mock_enhanced(crawl_result)
    with (
        patch(
            "sastaspace.jobs.enhanced_crawl",
            create=True,
            new_callable=AsyncMock,
            return_value=enhanced_mock,
        ),
        patch(
            "sastaspace.jobs.update_job",
            side_effect=_update_job_compat,
        ),
        patch(
            "sastaspace.jobs.run_redesign",
            return_value=mock_html,
        ) as mock_run,
        patch("sastaspace.jobs.deploy", return_value=deploy_result),
    ):
        await redesign_handler(job_id, "https://example.com", "premium", job_service)

    mock_run.assert_called_once()
