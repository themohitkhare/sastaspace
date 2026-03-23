# tests/test_pipeline_callback.py
"""Tests for pipeline progress callback."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sastaspace.agents.pipeline import AGENT_MESSAGES, run_redesign_pipeline
from sastaspace.config import Settings
from sastaspace.crawler import CrawlResult
from sastaspace.database import create_job, update_job
from sastaspace.deployer import DeployResult
from sastaspace.jobs import JobService, redesign_handler


@pytest.fixture
def job_service():
    """Create a JobService with mocked Redis for callback tests."""
    service = JobService(redis_url="redis://localhost:6379")
    redis = AsyncMock()
    redis.xgroup_create = AsyncMock()
    redis.xadd = AsyncMock()
    redis.xreadgroup = AsyncMock(return_value=[])
    redis.xack = AsyncMock()
    redis.publish = AsyncMock()
    redis.aclose = AsyncMock()
    service._redis = redis
    service._pubsub_redis = redis
    return service


def _crawl():
    return CrawlResult(
        url="https://example.com",
        title="Example",
        meta_description="",
        favicon_url="",
        html_source="<html></html>",
        screenshot_base64="",
        headings=[],
        navigation_links=[],
        text_content="Hello",
        images=[],
        colors=[],
        fonts=[],
        sections=[],
        error="",
    )


def test_progress_callback_called_for_each_agent():
    """progress_callback fires once per agent stage."""
    callback = MagicMock()
    mock_html = "<!DOCTYPE html><html><body>Test</body></html>"

    with (
        patch("sastaspace.agents.pipeline._run_crawl_analyst", return_value=MagicMock()),
        patch("sastaspace.agents.pipeline._run_design_strategist", return_value=MagicMock()),
        patch("sastaspace.agents.pipeline._run_copywriter", return_value=MagicMock()),
        patch("sastaspace.agents.pipeline._run_html_generator", return_value=mock_html),
        patch(
            "sastaspace.agents.pipeline._run_quality_reviewer",
            return_value=MagicMock(passed=True, overall_score=8, issues=[]),
        ),
    ):
        result = run_redesign_pipeline(_crawl(), Settings(), progress_callback=callback)

    assert isinstance(result, str)
    assert callback.call_count == 5
    event, data = callback.call_args_list[0][0]
    assert event == "agent_activity"
    assert "agent" in data and "message" in data and "step_progress" in data


def test_agent_messages_covers_all_agents():
    expected = {
        "crawl_analyst",
        "design_strategist",
        "copywriter",
        "html_generator",
        "quality_reviewer",
    }
    assert set(AGENT_MESSAGES.keys()) == expected


def test_progress_callback_none_is_safe():
    mock_html = "<!DOCTYPE html><html><body>Test</body></html>"
    with (
        patch("sastaspace.agents.pipeline._run_crawl_analyst", return_value=MagicMock()),
        patch("sastaspace.agents.pipeline._run_design_strategist", return_value=MagicMock()),
        patch("sastaspace.agents.pipeline._run_copywriter", return_value=MagicMock()),
        patch("sastaspace.agents.pipeline._run_html_generator", return_value=mock_html),
        patch(
            "sastaspace.agents.pipeline._run_quality_reviewer",
            return_value=MagicMock(passed=True, overall_score=8, issues=[]),
        ),
    ):
        result = run_redesign_pipeline(_crawl(), Settings(), progress_callback=None)
    assert result == mock_html


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


async def test_redesign_handler_passes_progress_callback(job_service, tmp_path):
    """redesign_handler passes a progress_callback to agno_redesign."""
    job_id = "callback-wiring-test"
    await create_job(job_id=job_id, url="https://example.com", client_ip="1.1.1.1")

    crawl_result = CrawlResult(
        url="https://example.com",
        title="Example",
        meta_description="",
        favicon_url="",
        html_source="<html></html>",
        screenshot_base64="",
        headings=[],
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
    mock_html = "<!DOCTYPE html><html><body>Done</body></html>"
    enhanced_mock = _mock_enhanced(crawl_result)

    with (
        patch(
            "sastaspace.jobs.enhanced_crawl",
            create=True,
            new_callable=AsyncMock,
            return_value=enhanced_mock,
        ),
        patch("sastaspace.jobs.update_job", side_effect=_update_job_compat),
        patch(
            "sastaspace.jobs.run_redesign",
            return_value=mock_html,
        ) as mock_run,
        patch("sastaspace.jobs.deploy", return_value=deploy_result),
        patch("sastaspace.jobs.Settings.use_agno_pipeline", new=True, create=True),
    ):
        await redesign_handler(job_id, "https://example.com", "free", job_service)

    # run_redesign should have been called
    mock_run.assert_called_once()


async def test_redesign_handler_emits_discovery(job_service, tmp_path):
    """redesign_handler emits discovery event with real crawl data."""
    job_id = "discovery-test-1"
    await create_job(job_id=job_id, url="https://example.com", client_ip="1.1.1.1")

    crawl_result = CrawlResult(
        url="https://example.com",
        title="Acme Corp",
        meta_description="We build things",
        favicon_url="",
        html_source="<html></html>",
        screenshot_base64="",
        headings=[],
        navigation_links=[],
        text_content="",
        images=[],
        colors=["#ff0000", "#0000ff"],
        fonts=["Inter"],
        sections=["hero", "footer"],
        error="",
    )
    deploy_result = DeployResult(
        subdomain="example-com",
        index_path=tmp_path / "example-com" / "index.html",
        sites_dir=tmp_path,
    )
    mock_html = "<!DOCTYPE html><html><body>Done</body></html>"
    discovery_events = []

    original_publish = job_service.publish_status

    async def capture(jid, event, data):
        if event == "discovery":
            discovery_events.append(data)
        return await original_publish(jid, event, data)

    job_service.publish_status = capture

    enhanced_mock = _mock_enhanced(crawl_result)
    with (
        patch(
            "sastaspace.jobs.enhanced_crawl",
            create=True,
            new_callable=AsyncMock,
            return_value=enhanced_mock,
        ),
        patch("sastaspace.jobs.update_job", side_effect=_update_job_compat),
        patch("sastaspace.jobs.run_redesign", return_value=mock_html),
        patch("sastaspace.jobs.deploy", return_value=deploy_result),
    ):
        await redesign_handler(job_id, "https://example.com", "free", job_service)

    assert len(discovery_events) == 1
    labels = [i["label"] for i in discovery_events[0]["items"]]
    assert "Title" in labels
    assert "Colors" in labels


async def test_redesign_handler_emits_screenshot(job_service, tmp_path):
    """Emits screenshot event when screenshot is present and not too large."""
    job_id = "screenshot-test-1"
    await create_job(job_id=job_id, url="https://example.com", client_ip="1.1.1.1")

    crawl_result = CrawlResult(
        url="https://example.com",
        title="Example",
        meta_description="",
        favicon_url="",
        html_source="<html></html>",
        screenshot_base64="iVBORw0KGgo=",  # small fake base64
        headings=[],
        navigation_links=[],
        text_content="",
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
    mock_html = "<!DOCTYPE html><html><body>Done</body></html>"
    screenshot_events = []

    original_publish = job_service.publish_status

    async def capture(jid, event, data):
        if event == "screenshot":
            screenshot_events.append(data)
        return await original_publish(jid, event, data)

    job_service.publish_status = capture

    enhanced_mock = _mock_enhanced(crawl_result)
    with (
        patch(
            "sastaspace.jobs.enhanced_crawl",
            create=True,
            new_callable=AsyncMock,
            return_value=enhanced_mock,
        ),
        patch("sastaspace.jobs.update_job", side_effect=_update_job_compat),
        patch("sastaspace.jobs.run_redesign", return_value=mock_html),
        patch("sastaspace.jobs.deploy", return_value=deploy_result),
    ):
        await redesign_handler(job_id, "https://example.com", "free", job_service)

    assert len(screenshot_events) == 1
    assert screenshot_events[0]["screenshot_base64"] == "iVBORw0KGgo="


async def test_redesign_handler_skips_large_screenshot(job_service, tmp_path):
    """Does not emit screenshot if base64 exceeds 500KB."""
    job_id = "screenshot-test-2"
    await create_job(job_id=job_id, url="https://example.com", client_ip="1.1.1.1")

    crawl_result = CrawlResult(
        url="https://example.com",
        title="Example",
        meta_description="",
        favicon_url="",
        html_source="<html></html>",
        screenshot_base64="A" * (500_001),  # 500KB+ — too large
        headings=[],
        navigation_links=[],
        text_content="",
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
    mock_html = "<!DOCTYPE html><html><body>Done</body></html>"
    screenshot_events = []

    original_publish = job_service.publish_status

    async def capture(jid, event, data):
        if event == "screenshot":
            screenshot_events.append(data)
        return await original_publish(jid, event, data)

    job_service.publish_status = capture

    enhanced_mock = _mock_enhanced(crawl_result)
    with (
        patch(
            "sastaspace.jobs.enhanced_crawl",
            create=True,
            new_callable=AsyncMock,
            return_value=enhanced_mock,
        ),
        patch("sastaspace.jobs.update_job", side_effect=_update_job_compat),
        patch("sastaspace.jobs.run_redesign", return_value=mock_html),
        patch("sastaspace.jobs.deploy", return_value=deploy_result),
    ):
        await redesign_handler(job_id, "https://example.com", "free", job_service)

    assert len(screenshot_events) == 0  # skipped — too large
