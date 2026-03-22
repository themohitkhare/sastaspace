# tests/test_pipeline_structure.py
"""Structural / routing tests for sastaspace/agents/pipeline.py — NO LLM calls."""

import json
from unittest.mock import patch

import pytest

from sastaspace.agents.models import (
    BrandProfile,
    ComponentSelection,
    ContentSection,
    CopywriterOutput,
    DesignBrief,
    SiteAnalysis,
)
from sastaspace.agents.pipeline import (
    PIPELINE_STEPS,
    _create_model,
    _extract_json,
    _prefilter_catalog,
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
            crawl_analyst_model="claude-haiku-4-5-20251001",
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
        assert call_model.id == "claude-haiku-4-5-20251001"

    @patch("sastaspace.agents.pipeline._run_agent")
    def test_free_tier_uses_free_model(self, mock_agent):
        mock_agent.return_value = json.dumps(SiteAnalysis().model_dump())
        s = self._settings()
        _run_crawl_analyst(self._crawl_result(), s, tier="free")

        call_model = mock_agent.call_args.args[3]
        assert call_model.id == "glm-4.7-flash:latest"


# ---------------------------------------------------------------------------
# _prefilter_catalog
# ---------------------------------------------------------------------------


class TestPrefilterCatalog:
    """_prefilter_catalog keeps relevant categories and drops the rest."""

    def _catalog(self) -> str:
        return json.dumps(
            {
                "heroes": [{"name": "hero-1"}],
                "calls-to-action": [{"name": "cta-1"}],
                "footers": [{"name": "footer-1"}],
                "navigation-menus": [{"name": "nav-1"}],
                "pricing-sections": [{"name": "price-1"}],
                "cards": [{"name": "card-1"}],
                "testimonials": [{"name": "testi-1"}],
                "features": [{"name": "feat-1"}],
                "backgrounds": [{"name": "bg-1"}],
                "announcements": [{"name": "ann-1"}],
                "clients": [{"name": "client-1"}],
                "comparisons": [{"name": "comp-1"}],
                "random-other": [{"name": "other-1"}],
            }
        )

    def _analysis(self, **kw) -> SiteAnalysis:
        defaults = dict(
            primary_goal="",
            content_sections=[],
        )
        defaults.update(kw)
        return SiteAnalysis(
            brand=BrandProfile(industry=kw.get("industry", "")),
            primary_goal=defaults["primary_goal"],
            content_sections=defaults["content_sections"],
        )

    def test_core_categories_always_included(self):
        """heroes, calls-to-action, footers, navigation-menus, backgrounds, announcements."""
        analysis = self._analysis()
        result = json.loads(_prefilter_catalog(self._catalog(), analysis))
        for cat in (
            "heroes",
            "calls-to-action",
            "footers",
            "navigation-menus",
            "backgrounds",
            "announcements",
        ):
            assert cat in result, f"Core category '{cat}' should always be included"

    def test_saas_goal_includes_pricing_and_features(self):
        analysis = self._analysis(primary_goal="SaaS lead generation")
        result = json.loads(_prefilter_catalog(self._catalog(), analysis))
        assert "pricing-sections" in result
        assert "features" in result
        assert "clients" in result
        assert "comparisons" in result

    def test_ecommerce_goal_includes_cards_testimonials(self):
        analysis = self._analysis(primary_goal="ecommerce")
        result = json.loads(_prefilter_catalog(self._catalog(), analysis))
        assert "cards" in result
        assert "testimonials" in result

    def test_testimonials_section_type_includes_testimonials(self):
        sections = [ContentSection(content_type="testimonials", heading="Reviews")]
        analysis = self._analysis(content_sections=sections)
        result = json.loads(_prefilter_catalog(self._catalog(), analysis))
        assert "testimonials" in result
        assert "clients" in result

    def test_features_section_type_includes_features(self):
        sections = [ContentSection(content_type="features", heading="Features")]
        analysis = self._analysis(content_sections=sections)
        result = json.loads(_prefilter_catalog(self._catalog(), analysis))
        assert "features" in result
        assert "cards" in result

    def test_unrelated_categories_excluded(self):
        """random-other should be filtered out."""
        analysis = self._analysis()
        result = json.loads(_prefilter_catalog(self._catalog(), analysis))
        assert "random-other" not in result

    def test_invalid_json_catalog_returns_as_is(self):
        analysis = self._analysis()
        result = _prefilter_catalog("not valid json", analysis)
        assert result == "not valid json"

    def test_tech_industry_includes_saas_categories(self):
        analysis = self._analysis(industry="tech")
        result = json.loads(_prefilter_catalog(self._catalog(), analysis))
        assert "pricing-sections" in result
        assert "features" in result


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
            "component_selector",
            "html_generator",
            "quality_reviewer",
            "normalizer",
        ]

    def test_no_duplicates(self):
        assert len(PIPELINE_STEPS) == len(set(PIPELINE_STEPS))

    def test_step_count(self):
        assert len(PIPELINE_STEPS) == 7


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

    def test_component_selection_restored(self):
        cs = ComponentSelection(strategy="test strategy")
        checkpoint = {
            "completed_step": "component_selector",
            "data": {"component_selection": cs.model_dump_json()},
        }
        idx, restored = _restore_from_checkpoint(checkpoint)
        assert idx == PIPELINE_STEPS.index("component_selector") + 1
        assert restored["component_selection"].strategy == "test strategy"

    def test_all_models_restored_from_full_checkpoint(self):
        """A checkpoint with all data keys restores all models."""
        sa = SiteAnalysis(primary_goal="ecommerce")
        db = DesignBrief(design_direction="bold")
        co = CopywriterOutput(headline="Buy Now")
        cs = ComponentSelection(strategy="hero + pricing")
        checkpoint = {
            "completed_step": "quality_reviewer",
            "data": {
                "site_analysis": sa.model_dump_json(),
                "design_brief": db.model_dump_json(),
                "copywriter_output": co.model_dump_json(),
                "component_selection": cs.model_dump_json(),
                "html": "<html></html>",
            },
        }
        idx, restored = _restore_from_checkpoint(checkpoint)
        assert idx == PIPELINE_STEPS.index("quality_reviewer") + 1
        assert restored["site_analysis"].primary_goal == "ecommerce"
        assert restored["design_brief"].design_direction == "bold"
        assert restored["copywriter_output"].headline == "Buy Now"
        assert restored["component_selection"].strategy == "hero + pricing"
        assert restored["html"] == "<html></html>"
