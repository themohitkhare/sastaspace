# tests/test_pipeline_checkpoint.py
"""Tests for pipeline checkpointing -- resume from last completed step."""

from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sastaspace.agents.models import (
    RedesignPlan,
)
from sastaspace.agents.pipeline import PIPELINE_STEPS, run_redesign_pipeline
from sastaspace.database import JobUpdate, get_job, update_job

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@dataclass
class FakeCrawlResult:
    url: str = "https://example.com"
    title: str = "Example"
    meta_description: str = "An example site"
    favicon_url: str = ""
    html_source: str = "<html></html>"
    screenshot_base64: str = ""
    headings: list[str] = field(default_factory=list)
    navigation_links: list[dict] = field(default_factory=list)
    text_content: str = ""
    images: list[dict] = field(default_factory=list)
    colors: list[str] = field(default_factory=lambda: ["#000"])
    fonts: list[str] = field(default_factory=lambda: ["Arial"])
    sections: list[dict] = field(default_factory=list)
    error: str = ""

    def to_prompt_context(self) -> str:
        return "fake context"


@pytest.fixture()
def fake_crawl():
    return FakeCrawlResult()


@pytest.fixture()
def fake_settings():
    s = MagicMock()
    s.use_agno_pipeline = True
    s.use_component_pipeline = False  # disable React pipeline in tests
    s.claude_code_api_url = "http://localhost:8000/v1"
    s.claude_code_api_key = "test"
    s.claude_model = "test-model"
    return s


def _make_checkpoint(completed_step: str, data: dict | None = None) -> dict:
    """Helper to build a checkpoint dict."""
    return {
        "completed_step": completed_step,
        "data": data or {},
    }


# Shared mock return values
_PLAN = RedesignPlan(primary_goal="lead gen", target_audience="devs", design_direction="modern")
_HTML = "<!DOCTYPE html><html><body>hi</body></html>"


# ---------------------------------------------------------------------------
# Test 1: checkpoint at planner skips planner, runs builder
# ---------------------------------------------------------------------------


@patch("sastaspace.agents.pipeline._run_builder", return_value=_HTML)
@patch("sastaspace.agents.pipeline._run_planner", return_value=_PLAN)
def test_checkpoint_skips_completed_steps(
    mock_planner,
    mock_builder,
    fake_crawl,
    fake_settings,
):
    """With checkpoint at planner, skip planner, run builder."""
    checkpoint = _make_checkpoint(
        "planner",
        {
            "plan": _PLAN.model_dump_json(),
        },
    )

    result = run_redesign_pipeline(
        fake_crawl,
        fake_settings,
        checkpoint=checkpoint,
    )

    assert result.html == _HTML
    mock_planner.assert_not_called()
    mock_builder.assert_called_once()


# ---------------------------------------------------------------------------
# Test 2: no checkpoint runs all steps (backward compat)
# ---------------------------------------------------------------------------


@patch("sastaspace.agents.pipeline._run_builder", return_value=_HTML)
@patch("sastaspace.agents.pipeline._run_planner", return_value=_PLAN)
def test_no_checkpoint_runs_all_steps(
    mock_planner,
    mock_builder,
    fake_crawl,
    fake_settings,
):
    """Without checkpoint every step runs."""
    result = run_redesign_pipeline(fake_crawl, fake_settings)

    assert result.html == _HTML
    mock_planner.assert_called_once()
    mock_builder.assert_called_once()


# ---------------------------------------------------------------------------
# Test 3: checkpoint_callback is called after each step
# ---------------------------------------------------------------------------


@patch("sastaspace.agents.pipeline._run_builder", return_value=_HTML)
@patch("sastaspace.agents.pipeline._run_planner", return_value=_PLAN)
def test_checkpoint_callback_fires(
    mock_planner,
    mock_builder,
    fake_crawl,
    fake_settings,
):
    """checkpoint_callback receives step name and accumulated data after each step."""
    cb = MagicMock()

    run_redesign_pipeline(fake_crawl, fake_settings, checkpoint_callback=cb)

    # Should be called once per pipeline step (2 total)
    assert cb.call_count == len(PIPELINE_STEPS)

    # First call should be for planner
    first_call_step = cb.call_args_list[0][0][0]
    assert first_call_step == "planner"

    # Last call should be for builder
    last_call_step = cb.call_args_list[-1][0][0]
    assert last_call_step == "builder"

    # Each call's data dict should have completed_step matching the step name
    for call in cb.call_args_list:
        step_name, data = call[0]
        assert data["completed_step"] == step_name


# ---------------------------------------------------------------------------
# Test 4: update_job with checkpoint persists and get_job returns it
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_job_checkpoint_persists(tmp_path):
    """update_job with checkpoint dict persists it, get_job returns it."""
    # We test via mocking the MongoDB collection since we don't want a real DB
    mock_collection = AsyncMock()
    mock_collection.update_one = AsyncMock()
    mock_collection.find_one = AsyncMock(
        return_value={
            "_id": "job-1",
            "status": "redesigning",
            "checkpoint": {"completed_step": "planner", "data": {"plan": "{}"}},
        }
    )

    with patch("sastaspace.database._get_db") as mock_db:
        mock_db.return_value.__getitem__ = MagicMock(return_value=mock_collection)

        checkpoint_data = {
            "completed_step": "planner",
            "data": {"plan": "{}"},
        }
        await update_job("job-1", updates=JobUpdate(checkpoint=checkpoint_data))

        # Verify update_one was called with $set containing checkpoint
        call_args = mock_collection.update_one.call_args
        set_dict = call_args[0][1]["$set"]
        assert "checkpoint" in set_dict
        assert set_dict["checkpoint"]["completed_step"] == "planner"

        # Verify get_job returns checkpoint
        job = await get_job("job-1")
        assert job is not None
        assert "checkpoint" in job
        assert job["checkpoint"]["completed_step"] == "planner"
