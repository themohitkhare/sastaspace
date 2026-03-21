# tests/test_pipeline_callback.py
"""Tests for pipeline progress callback."""

from unittest.mock import MagicMock, patch

from sastaspace.agents.pipeline import AGENT_MESSAGES, run_redesign_pipeline
from sastaspace.crawler import CrawlResult


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
