# tests/test_pipeline_callback.py
"""Tests for pipeline progress callback."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sastaspace.agents.pipeline import AGENT_MESSAGES, run_redesign_pipeline
from sastaspace.crawler import CrawlResult


@pytest.fixture
def job_service():
    """Create a JobService with mocked Redis for callback tests."""
    from sastaspace.jobs import JobService

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
        patch("sastaspace.agents.pipeline._run_component_selector", return_value=MagicMock()),
        patch("sastaspace.agents.pipeline._run_html_generator", return_value=mock_html),
        patch(
            "sastaspace.agents.pipeline._run_quality_reviewer",
            return_value=MagicMock(passed=True, overall_score=8, issues=[]),
        ),
        patch("sastaspace.agents.pipeline._run_normalizer", return_value=mock_html),
    ):
        from sastaspace.config import Settings

        result = run_redesign_pipeline(_crawl(), Settings(), progress_callback=callback)

    assert isinstance(result, str)
    assert callback.call_count == 7
    event, data = callback.call_args_list[0][0]
    assert event == "agent_activity"
    assert "agent" in data and "message" in data and "step_progress" in data


def test_agent_messages_covers_all_agents():
    expected = {
        "crawl_analyst",
        "design_strategist",
        "copywriter",
        "component_selector",
        "html_generator",
        "quality_reviewer",
        "normalizer",
    }
    assert set(AGENT_MESSAGES.keys()) == expected


def test_progress_callback_none_is_safe():
    mock_html = "<!DOCTYPE html><html><body>Test</body></html>"
    with (
        patch("sastaspace.agents.pipeline._run_crawl_analyst", return_value=MagicMock()),
        patch("sastaspace.agents.pipeline._run_design_strategist", return_value=MagicMock()),
        patch("sastaspace.agents.pipeline._run_copywriter", return_value=MagicMock()),
        patch("sastaspace.agents.pipeline._run_component_selector", return_value=MagicMock()),
        patch("sastaspace.agents.pipeline._run_html_generator", return_value=mock_html),
        patch(
            "sastaspace.agents.pipeline._run_quality_reviewer",
            return_value=MagicMock(passed=True, overall_score=8, issues=[]),
        ),
        patch("sastaspace.agents.pipeline._run_normalizer", return_value=mock_html),
    ):
        from sastaspace.config import Settings

        result = run_redesign_pipeline(_crawl(), Settings(), progress_callback=None)
    assert result == mock_html


async def test_redesign_handler_passes_progress_callback(job_service, tmp_path):
    """redesign_handler passes a progress_callback to agno_redesign."""
    from sastaspace.crawler import CrawlResult
    from sastaspace.database import create_job
    from sastaspace.deployer import DeployResult

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

    with (
        patch("sastaspace.crawler.crawl", new_callable=AsyncMock, return_value=crawl_result),
        patch("sastaspace.redesigner.agno_redesign", return_value=mock_html) as mock_agno,
        patch("sastaspace.deployer.deploy", return_value=deploy_result),
        patch("sastaspace.config.Settings.use_agno_pipeline", new=True, create=True),
    ):
        from sastaspace.jobs import redesign_handler

        await redesign_handler(job_id, "https://example.com", "standard", job_service)

    # agno_redesign should have been called with a progress_callback keyword arg
    call_kwargs = mock_agno.call_args
    assert call_kwargs is not None
    assert "progress_callback" in call_kwargs.kwargs or (
        len(call_kwargs.args) >= 4 and callable(call_kwargs.args[3])
    )


async def test_redesign_handler_emits_discovery(job_service, tmp_path):
    """redesign_handler emits discovery event with real crawl data."""
    from unittest.mock import AsyncMock, patch

    from sastaspace.crawler import CrawlResult
    from sastaspace.database import create_job
    from sastaspace.deployer import DeployResult

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

    with (
        patch("sastaspace.crawler.crawl", new_callable=AsyncMock, return_value=crawl_result),
        patch("sastaspace.redesigner.agno_redesign", return_value=mock_html),
        patch("sastaspace.deployer.deploy", return_value=deploy_result),
    ):
        from sastaspace.jobs import redesign_handler

        await redesign_handler(job_id, "https://example.com", "standard", job_service)

    assert len(discovery_events) == 1
    labels = [i["label"] for i in discovery_events[0]["items"]]
    assert "Title" in labels
    assert "Colors" in labels


async def test_redesign_handler_emits_screenshot(job_service, tmp_path):
    """Emits screenshot event when screenshot is present and not too large."""
    from unittest.mock import AsyncMock, patch

    from sastaspace.crawler import CrawlResult
    from sastaspace.database import create_job
    from sastaspace.deployer import DeployResult

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

    with (
        patch("sastaspace.crawler.crawl", new_callable=AsyncMock, return_value=crawl_result),
        patch("sastaspace.redesigner.agno_redesign", return_value=mock_html),
        patch("sastaspace.deployer.deploy", return_value=deploy_result),
    ):
        from sastaspace.jobs import redesign_handler

        await redesign_handler(job_id, "https://example.com", "standard", job_service)

    assert len(screenshot_events) == 1
    assert screenshot_events[0]["screenshot_base64"] == "iVBORw0KGgo="


async def test_redesign_handler_skips_large_screenshot(job_service, tmp_path):
    """Does not emit screenshot if base64 exceeds 500KB."""
    from unittest.mock import AsyncMock, patch

    from sastaspace.crawler import CrawlResult
    from sastaspace.database import create_job
    from sastaspace.deployer import DeployResult

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

    with (
        patch("sastaspace.crawler.crawl", new_callable=AsyncMock, return_value=crawl_result),
        patch("sastaspace.redesigner.agno_redesign", return_value=mock_html),
        patch("sastaspace.deployer.deploy", return_value=deploy_result),
    ):
        from sastaspace.jobs import redesign_handler

        await redesign_handler(job_id, "https://example.com", "standard", job_service)

    assert len(screenshot_events) == 0  # skipped — too large
