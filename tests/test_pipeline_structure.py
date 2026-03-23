# tests/test_pipeline_structure.py
"""Structural / routing tests for sastaspace/agents/pipeline.py -- NO LLM calls."""

import json
from unittest.mock import patch

import pytest

from sastaspace.agents.models import (
    RedesignPlan,
)
from sastaspace.agents.pipeline import (
    PIPELINE_STEPS,
    _create_model,
    _extract_json,
    _restore_from_checkpoint,
    _run_planner,
)
from sastaspace.config import Settings
from sastaspace.crawler import CrawlResult

# ---------------------------------------------------------------------------
# _extract_json
# ---------------------------------------------------------------------------


class TestExtractJson:
    """_extract_json parses JSON from various agent output formats."""

    def test_clean_json(self):
        raw = '{"key": "value", "n": 42}'
        assert _extract_json(raw) == {"key": "value", "n": 42}

    def test_markdown_fenced_json(self):
        raw = '```json\n{"a": 1}\n```'
        assert _extract_json(raw) == {"a": 1}

    def test_markdown_fenced_no_lang(self):
        raw = '```\n{"a": 1}\n```'
        assert _extract_json(raw) == {"a": 1}

    def test_json_with_preamble(self):
        raw = 'Here is the analysis:\n{"result": true}'
        assert _extract_json(raw) == {"result": True}

    def test_json_with_trailing_text(self):
        raw = '{"result": true}\n\nI hope this helps!'
        assert _extract_json(raw) == {"result": True}

    def test_json_with_preamble_and_trailing(self):
        raw = 'Sure, here you go:\n{"x": 1}\nLet me know if you need more.'
        assert _extract_json(raw) == {"x": 1}

    def test_non_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _extract_json("This is just text with no JSON at all")

    def test_empty_string_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _extract_json("")

    def test_nested_json(self):
        raw = '{"outer": {"inner": [1, 2, 3]}}'
        result = _extract_json(raw)
        assert result["outer"]["inner"] == [1, 2, 3]


# ---------------------------------------------------------------------------
# _create_model
# ---------------------------------------------------------------------------


class TestCreateModel:
    """_create_model routes to ollama or claude-code-api based on use_ollama flag."""

    def _settings(self) -> Settings:
        """Construct a minimal Settings bypassing env file."""
        return Settings(
            claude_code_api_url="http://claude:8000/v1",
            claude_code_api_key="claude-key",
            ollama_url="http://ollama:11434/v1",
            ollama_api_key="ollama-key",
        )

    @patch("sastaspace.agents.pipeline.OpenAILike")
    def test_premium_uses_claude_url(self, MockOAI):
        s = self._settings()
        _create_model("claude-sonnet-4-6-20250514", s, use_ollama=False)
        MockOAI.assert_called_once_with(
            id="claude-sonnet-4-6-20250514",
            api_key="claude-key",
            base_url="http://claude:8000/v1",
        )

    @patch("sastaspace.agents.pipeline.OpenAILike")
    def test_free_uses_ollama_url(self, MockOAI):
        s = self._settings()
        _create_model("glm-4.7-flash:latest", s, use_ollama=True)
        MockOAI.assert_called_once_with(
            id="glm-4.7-flash:latest",
            api_key="ollama-key",
            base_url="http://ollama:11434/v1",
        )


# ---------------------------------------------------------------------------
# Model routing by tier -- _run_planner
# ---------------------------------------------------------------------------


class TestModelRoutingByTier:
    """_run_planner picks free vs premium model based on tier arg."""

    def _crawl_result(self) -> CrawlResult:
        return CrawlResult(
            url="https://example.com",
            title="Example",
            meta_description="desc",
            favicon_url="",
            html_source="<html></html>",
            screenshot_base64="",
            colors=["#fff"],
            fonts=["Inter"],
        )

    def _settings(self) -> Settings:
        return Settings(
            crawl_analyst_model="claude-sonnet-4-6-20250514",
            free_crawl_analyst_model="glm-4.7-flash:latest",
            claude_code_api_url="http://claude:8000/v1",
            ollama_url="http://ollama:11434/v1",
        )

    @patch("sastaspace.agents.pipeline._run_agent")
    def test_premium_tier_uses_premium_model(self, mock_agent):
        mock_agent.return_value = json.dumps(RedesignPlan().model_dump())
        s = self._settings()
        _run_planner(self._crawl_result(), s, tier="premium")

        # The model passed to _run_agent should have the claude model id
        call_model = mock_agent.call_args.args[3]  # 4th positional arg is model
        assert call_model.id == "claude-sonnet-4-6-20250514"

    @patch("sastaspace.agents.pipeline._run_agent")
    def test_free_tier_uses_free_model(self, mock_agent):
        mock_agent.return_value = json.dumps(RedesignPlan().model_dump())
        s = self._settings()
        _run_planner(self._crawl_result(), s, tier="free")

        call_model = mock_agent.call_args.args[3]
        assert call_model.id == "glm-4.7-flash:latest"


# ---------------------------------------------------------------------------
# PIPELINE_STEPS ordering
# ---------------------------------------------------------------------------


class TestPipelineSteps:
    """Verify the PIPELINE_STEPS constant is correct and complete."""

    def test_expected_steps(self):
        assert PIPELINE_STEPS == [
            "planner",
            "builder",
        ]

    def test_no_duplicates(self):
        assert len(PIPELINE_STEPS) == len(set(PIPELINE_STEPS))

    def test_step_count(self):
        assert len(PIPELINE_STEPS) == 2


# ---------------------------------------------------------------------------
# _restore_from_checkpoint
# ---------------------------------------------------------------------------


class TestRestoreFromCheckpoint:
    """_restore_from_checkpoint deserializes checkpoint data back into Pydantic models."""

    def test_empty_checkpoint_returns_zero_index(self):
        idx, data = _restore_from_checkpoint({})
        assert idx == 0
        assert data == {}

    def test_unknown_step_returns_zero_index(self):
        idx, data = _restore_from_checkpoint({"completed_step": "nonexistent"})
        assert idx == 0
        assert data == {}

    def test_planner_completed_resumes_at_index_1(self):
        plan = RedesignPlan(primary_goal="lead gen", target_audience="developers")
        checkpoint = {
            "completed_step": "planner",
            "data": {"plan": plan.model_dump_json()},
        }
        idx, restored = _restore_from_checkpoint(checkpoint)
        assert idx == 1  # resume at builder
        assert "plan" in restored
        assert restored["plan"].primary_goal == "lead gen"

    def test_builder_completed_preserves_html(self):
        checkpoint = {
            "completed_step": "builder",
            "data": {"html": "<html><body>Test</body></html>"},
        }
        idx, restored = _restore_from_checkpoint(checkpoint)
        assert idx == PIPELINE_STEPS.index("builder") + 1
        assert restored["html"] == "<html><body>Test</body></html>"

    def test_full_checkpoint_restores_all(self):
        """A checkpoint with all data keys restores all models."""
        plan = RedesignPlan(primary_goal="ecommerce", design_direction="bold")
        checkpoint = {
            "completed_step": "builder",
            "data": {
                "plan": plan.model_dump_json(),
                "html": "<html></html>",
            },
        }
        idx, restored = _restore_from_checkpoint(checkpoint)
        assert idx == PIPELINE_STEPS.index("builder") + 1
        assert restored["plan"].primary_goal == "ecommerce"
        assert restored["plan"].design_direction == "bold"
        assert restored["html"] == "<html></html>"
