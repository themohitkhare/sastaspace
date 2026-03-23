# tests/test_pipeline_structure.py
"""Structural / routing tests for sastaspace/agents/pipeline.py — NO LLM calls."""

import json
from unittest.mock import patch

import pytest

from sastaspace.agents.models import (
    CopywriterOutput,
    DesignBrief,
    SiteAnalysis,
)
from sastaspace.agents.pipeline import (
    PIPELINE_STEPS,
    _create_model,
    _extract_json,
    _restore_from_checkpoint,
    _run_crawl_analyst,
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
# Model routing by tier — _run_crawl_analyst
# ---------------------------------------------------------------------------


class TestModelRoutingByTier:
    """_run_crawl_analyst picks free vs premium model based on tier arg."""

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
        mock_agent.return_value = json.dumps(SiteAnalysis().model_dump())
        s = self._settings()
        _run_crawl_analyst(self._crawl_result(), s, tier="premium")

        # The model passed to _run_agent should have the claude model id
        call_model = mock_agent.call_args.args[3]  # 4th positional arg is model
        assert call_model.id == "claude-sonnet-4-6-20250514"

    @patch("sastaspace.agents.pipeline._run_agent")
    def test_free_tier_uses_free_model(self, mock_agent):
        mock_agent.return_value = json.dumps(SiteAnalysis().model_dump())
        s = self._settings()
        _run_crawl_analyst(self._crawl_result(), s, tier="free")

        call_model = mock_agent.call_args.args[3]
        assert call_model.id == "glm-4.7-flash:latest"


# ---------------------------------------------------------------------------
# PIPELINE_STEPS ordering
# ---------------------------------------------------------------------------


class TestPipelineSteps:
    """Verify the PIPELINE_STEPS constant is correct and complete."""

    def test_expected_steps(self):
        assert PIPELINE_STEPS == [
            "crawl_analyst",
            "design_strategist",
            "copywriter",
            "html_generator",
            "quality_reviewer",
        ]

    def test_no_duplicates(self):
        assert len(PIPELINE_STEPS) == len(set(PIPELINE_STEPS))

    def test_step_count(self):
        assert len(PIPELINE_STEPS) == 5


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

    def test_crawl_analyst_completed_resumes_at_index_1(self):
        sa = SiteAnalysis(primary_goal="lead gen", target_audience="developers")
        checkpoint = {
            "completed_step": "crawl_analyst",
            "data": {"site_analysis": sa.model_dump_json()},
        }
        idx, restored = _restore_from_checkpoint(checkpoint)
        assert idx == 1  # resume at design_strategist
        assert "site_analysis" in restored
        assert restored["site_analysis"].primary_goal == "lead gen"

    def test_design_strategist_completed_resumes_at_index_2(self):
        sa = SiteAnalysis()
        db = DesignBrief(design_direction="modern minimal")
        checkpoint = {
            "completed_step": "design_strategist",
            "data": {
                "site_analysis": sa.model_dump_json(),
                "design_brief": db.model_dump_json(),
            },
        }
        idx, restored = _restore_from_checkpoint(checkpoint)
        assert idx == 2  # resume at copywriter
        assert restored["design_brief"].design_direction == "modern minimal"

    def test_html_generator_completed_preserves_html(self):
        checkpoint = {
            "completed_step": "html_generator",
            "data": {"html": "<html><body>Test</body></html>"},
        }
        idx, restored = _restore_from_checkpoint(checkpoint)
        assert idx == PIPELINE_STEPS.index("html_generator") + 1
        assert restored["html"] == "<html><body>Test</body></html>"

    def test_copywriter_output_restored(self):
        co = CopywriterOutput(headline="Amazing Headline", subheadline="Sub")
        checkpoint = {
            "completed_step": "copywriter",
            "data": {"copywriter_output": co.model_dump_json()},
        }
        idx, restored = _restore_from_checkpoint(checkpoint)
        assert idx == PIPELINE_STEPS.index("copywriter") + 1
        assert restored["copywriter_output"].headline == "Amazing Headline"

    def test_all_models_restored_from_full_checkpoint(self):
        """A checkpoint with all data keys restores all models."""
        sa = SiteAnalysis(primary_goal="ecommerce")
        db = DesignBrief(design_direction="bold")
        co = CopywriterOutput(headline="Buy Now")
        checkpoint = {
            "completed_step": "quality_reviewer",
            "data": {
                "site_analysis": sa.model_dump_json(),
                "design_brief": db.model_dump_json(),
                "copywriter_output": co.model_dump_json(),
                "html": "<html></html>",
            },
        }
        idx, restored = _restore_from_checkpoint(checkpoint)
        assert idx == PIPELINE_STEPS.index("quality_reviewer") + 1
        assert restored["site_analysis"].primary_goal == "ecommerce"
        assert restored["design_brief"].design_direction == "bold"
        assert restored["copywriter_output"].headline == "Buy Now"
        assert restored["html"] == "<html></html>"
