# tests/test_orchestrator.py
"""Tests for SwarmOrchestrator state machine."""

from unittest.mock import MagicMock, patch

from sastaspace.crawler import CrawlResult
from sastaspace.swarm.orchestrator import SwarmOrchestrator


def _crawl_result():
    return CrawlResult(
        url="https://example-site.com",
        title="Example Site",
        meta_description="A test site",
        favicon_url="https://example-site.com/favicon.ico",
        html_source="<html><body><h1>Hello</h1></body></html>",
        screenshot_base64="",
        headings=["Hello"],
        text_content="Hello world, this is a test site with features.",
        images=[{"src": "https://example-site.com/logo.png", "alt": "logo"}],
        colors=["#1a1a2e", "#e94560"],
        fonts=["Inter"],
        sections=[],
        navigation_links=[],
    )


# --- Mock data for each agent role ---

_CLASSIFIER = {
    "site_type": "saas",
    "industry": "dev tools",
    "complexity_score": 6,
    "output_format": "html",
    "output_format_reasoning": "simple site",
    "sections_detected": ["hero", "features"],
    "conversion_goals": ["sign up"],
}

_CONTENT = {
    "texts": [{"location": "hero.heading", "content": "Hello"}],
    "image_urls": [{"url": "https://example-site.com/logo.png", "context": "logo"}],
    "ctas": ["Sign Up"],
    "nav_items": ["Home"],
    "forms": [],
    "pricing_tables": [],
}

_BUSINESS = {
    "industry": "dev tools",
    "target_audience": "developers",
    "value_proposition": "Simple tools",
    "revenue_model": "SaaS subscription",
    "key_differentiators": ["easy to use"],
    "brand_voice": "professional",
    "competitive_positioning": "mid-market",
}

_CHALLENGER_APPROVED = {"approved": True, "issues": []}

_PALETTE = {
    "primary": "#1a1a2e",
    "secondary": "#16213e",
    "accent": "#e94560",
    "background": "#ffffff",
    "text": "#333333",
    "headline_font": "Inter, sans-serif",
    "body_font": "Inter, sans-serif",
    "color_mode": "light",
    "roundness": "8px",
    "rationale": "Modern SaaS palette",
}

_WIREFRAME = {
    "layout_pattern": "F-pattern",
    "section_order": ["hero", "features", "pricing", "cta"],
    "conversion_funnel": ["attention", "interest", "desire", "action"],
    "mobile_strategy": "stack-and-simplify",
    "sticky_header": True,
    "industry_patterns": ["social proof", "feature grid"],
}

_KISS = {
    "cognitive_load": 4,
    "visual_noise_budget": 3,
    "interaction_cost_limit": 5,
    "content_density_target": 4,
    "animation_budget": "minimal",
}

_MANIFEST = {
    "sections": [
        {
            "section_name": "hero",
            "component_id": "hero-001",
            "component_path": "components/hero/001.html",
            "slot_definitions": {"heading": "string", "subheading": "string"},
            "placement_order": 0,
        }
    ]
}

_COPY = {
    "slots": {"hero.heading": "Welcome to Example", "hero.subheading": "The best"},
    "unmapped_content": [],
}

_CONTENT_QA = {
    "passed": True,
    "feedback": "",
    "hallucinated_content": [],
    "missing_sections": [],
    "broken_links": [],
}

_A11Y_QA = {
    "passed": True,
    "feedback": "",
    "contrast_issues": [],
    "heading_issues": [],
    "missing_meta": [],
    "missing_alt_text": 0,
}


def _make_role_dispatcher(role_map, call_log=None):
    """Create a side_effect function that dispatches based on the 'role' kwarg."""

    def dispatch(*args, **kwargs):
        role = kwargs.get("role") or (args[0] if args else None)
        if call_log is not None:
            call_log.append(role)
        if role in role_map:
            val = role_map[role]
            if callable(val):
                return val()
            return val
        raise ValueError(f"Unexpected role in mock: {role}")

    return dispatch


# --- Phase 1 Tests ---


class TestSwarmOrchestratorPhase1:
    """Test Phase 1: Analysis agents."""

    @patch("sastaspace.swarm.orchestrator.AgentCaller")
    def test_phase1_runs_three_agents_and_challenger(self, mock_caller_cls):
        caller = MagicMock()
        mock_caller_cls.return_value = caller

        caller.call.side_effect = _make_role_dispatcher(
            {
                "site-classifier": _CLASSIFIER,
                "content-extractor": _CONTENT,
                "business-analyzer": _BUSINESS,
                "spec-challenger": _CHALLENGER_APPROVED,
            }
        )

        orchestrator = SwarmOrchestrator(
            api_url="http://localhost:8000/v1",
            api_key="test",
        )
        result = orchestrator._run_phase1(_crawl_result())
        assert result["classification"]["site_type"] == "saas"
        assert result["content_map"]["ctas"] == ["Sign Up"]
        assert result["business_profile"]["industry"] == "dev tools"
        assert result["spec_approved"]

    @patch("sastaspace.swarm.orchestrator.AgentCaller")
    def test_phase1_retries_on_spec_rejection(self, mock_caller_cls):
        caller = MagicMock()
        mock_caller_cls.return_value = caller

        classifier_blog = {
            "site_type": "blog",
            "industry": "tech",
            "complexity_score": 3,
            "output_format": "html",
            "output_format_reasoning": "simple",
            "sections_detected": ["hero"],
            "conversion_goals": [],
        }

        # Track classifier call count to return different results on retry
        classifier_calls = []

        def classifier_dispatch():
            classifier_calls.append(1)
            if len(classifier_calls) == 1:
                return classifier_blog
            return {**classifier_blog, "site_type": "saas"}

        challenger_calls = []

        def challenger_dispatch():
            challenger_calls.append(1)
            if len(challenger_calls) == 1:
                return {
                    "approved": False,
                    "issues": [
                        {
                            "category": "wrong_classification",
                            "severity": "blocking",
                            "description": "This is actually a SaaS site",
                            "recommendation": "Re-run classifier",
                        }
                    ],
                }
            return {"approved": True, "issues": []}

        caller.call.side_effect = _make_role_dispatcher(
            {
                "site-classifier": classifier_dispatch,
                "content-extractor": _CONTENT,
                "business-analyzer": _BUSINESS,
                "spec-challenger": challenger_dispatch,
            }
        )

        orchestrator = SwarmOrchestrator(api_url="http://localhost:8000/v1", api_key="test")
        result = orchestrator._run_phase1(_crawl_result())
        assert result["spec_approved"]
        assert result["classification"]["site_type"] == "saas"
        # Classifier should have been called twice (initial + retry)
        assert len(classifier_calls) == 2
        # Challenger should have been called twice (reject + approve)
        assert len(challenger_calls) == 2


# --- Static Analysis Tests ---


class TestSwarmOrchestratorStaticAnalysis:
    """Test that static analysis blocks bad output."""

    def test_orchestrator_blocks_placeholder_urls(self):
        from sastaspace.swarm.static_analyzer import StaticAnalyzer

        bad_html = (
            '<!DOCTYPE html><html><body><img src="https://via.placeholder.com/300"></body></html>'
        )
        result = StaticAnalyzer.analyze(bad_html)
        assert not result.passed


# --- Phase 2 Tests ---


class TestSwarmOrchestratorPhase2:
    """Test Phase 2: Design Strategy agents."""

    @patch("sastaspace.swarm.orchestrator.AgentCaller")
    def test_phase2_runs_three_parallel_design_agents(self, mock_caller_cls):
        caller = MagicMock()
        mock_caller_cls.return_value = caller

        caller.call.side_effect = _make_role_dispatcher(
            {
                "color-palette": _PALETTE,
                "ux-expert": _WIREFRAME,
                "kiss-metrics": _KISS,
            }
        )

        orchestrator = SwarmOrchestrator(api_url="http://localhost:8000/v1", api_key="test")
        phase1 = {
            "classification": {"site_type": "saas", "industry": "dev tools"},
            "content_map": {"texts": [], "ctas": []},
            "business_profile": {"industry": "dev tools"},
        }
        result = orchestrator._run_phase2(phase1)
        assert result["palette"]["color_mode"] == "light"
        assert result["wireframe"]["layout_pattern"] == "F-pattern"
        assert result["kiss"]["animation_budget"] == "minimal"


# --- Phase 3 Tests ---


class TestSwarmOrchestratorPhase3:
    """Test Phase 3: Selection (sequential)."""

    @patch("sastaspace.swarm.orchestrator.AgentCaller")
    def test_phase3_runs_component_selector_then_copywriter(self, mock_caller_cls):
        caller = MagicMock()
        mock_caller_cls.return_value = caller

        call_log = []
        caller.call.side_effect = _make_role_dispatcher(
            {
                "component-selector": _MANIFEST,
                "copywriter": _COPY,
            },
            call_log=call_log,
        )

        orchestrator = SwarmOrchestrator(api_url="http://localhost:8000/v1", api_key="test")
        phase1 = {
            "classification": {"site_type": "saas"},
            "content_map": {"texts": [], "ctas": []},
            "business_profile": {"industry": "dev tools"},
        }
        phase2 = {
            "palette": {"primary": "#000"},
            "wireframe": {"section_order": ["hero"]},
            "kiss": {"animation_budget": "minimal"},
        }
        result = orchestrator._run_phase3(phase1, phase2)
        assert result["manifest"]["sections"][0]["section_name"] == "hero"
        assert result["copy"]["slots"]["hero.heading"] == "Welcome to Example"
        # Verify sequential: component selector called first, then copywriter
        assert call_log == ["component-selector", "copywriter"]


# --- Progress Callback Tests ---


class TestSwarmOrchestratorProgressCallback:
    """Test progress callback emissions."""

    @patch("sastaspace.swarm.orchestrator.AgentCaller")
    def test_progress_callback_fires_on_phase_events(self, mock_caller_cls):
        caller = MagicMock()
        mock_caller_cls.return_value = caller

        caller.call.side_effect = _make_role_dispatcher(
            {
                "site-classifier": _CLASSIFIER,
                "content-extractor": _CONTENT,
                "business-analyzer": _BUSINESS,
                "spec-challenger": _CHALLENGER_APPROVED,
            }
        )

        events = []

        def capture(phase, data):
            events.append(phase)

        orchestrator = SwarmOrchestrator(
            api_url="http://localhost:8000/v1",
            api_key="test",
            progress_callback=capture,
        )
        orchestrator._run_phase1(_crawl_result())
        assert "phase1_start" in events
        assert "phase1_done" in events


# --- Model Tier Tests ---


class TestSwarmOrchestratorModelTiers:
    """Test model tier assignment."""

    @patch("sastaspace.swarm.orchestrator.AgentCaller")
    def test_model_tiers_assign_correctly(self, mock_caller_cls):
        orchestrator = SwarmOrchestrator(api_url="http://localhost:8000/v1", api_key="test")

        # Haiku agents
        assert "haiku" in orchestrator._model_for("site-classifier")
        assert "haiku" in orchestrator._model_for("content-extractor")
        assert "haiku" in orchestrator._model_for("business-analyzer")
        assert "haiku" in orchestrator._model_for("content-qa")
        assert "haiku" in orchestrator._model_for("a11y-seo")

        # Sonnet agents
        assert "sonnet" in orchestrator._model_for("spec-challenger")
        assert "sonnet" in orchestrator._model_for("color-palette")
        assert "sonnet" in orchestrator._model_for("ux-expert")
        assert "sonnet" in orchestrator._model_for("copywriter")
        assert "sonnet" in orchestrator._model_for("animation")

        # Builder uses sonnet during rate-limit mitigation
        assert "sonnet" in orchestrator._model_for("builder")

    @patch("sastaspace.swarm.orchestrator.AgentCaller")
    def test_model_override(self, mock_caller_cls):
        orchestrator = SwarmOrchestrator(
            api_url="http://localhost:8000/v1",
            api_key="test",
            models={"builder": "custom-model-v1"},
        )
        assert orchestrator._model_for("builder") == "custom-model-v1"


# --- Full Pipeline Tests ---


class TestSwarmOrchestratorFullPipeline:
    """Test the full run() method."""

    @patch("sastaspace.swarm.orchestrator.AgentCaller")
    def test_full_pipeline_happy_path(self, mock_caller_cls):
        caller = MagicMock()
        mock_caller_cls.return_value = caller

        valid_html = (
            '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
            "<title>Test</title><style>:root { --color-primary: #1a1a2e; "
            "--color-secondary: #16213e; --color-accent: #e94560; "
            "--color-background: #fff; --color-text: #333; "
            "--font-headline: Inter, sans-serif; --font-body: Inter, sans-serif; "
            "--radius: 8px; }</style></head><body><h1>Hello</h1></body></html>"
        )

        caller.call.side_effect = _make_role_dispatcher(
            {
                "site-classifier": _CLASSIFIER,
                "content-extractor": _CONTENT,
                "business-analyzer": _BUSINESS,
                "spec-challenger": _CHALLENGER_APPROVED,
                "color-palette": _PALETTE,
                "ux-expert": _WIREFRAME,
                "kiss-metrics": _KISS,
                "component-selector": _MANIFEST,
                "copywriter": _COPY,
                "content-qa": _CONTENT_QA,
                "a11y-seo": _A11Y_QA,
            }
        )

        caller.call_raw.side_effect = _make_role_dispatcher(
            {
                "builder": "<section><h1>Hello</h1></section>",
                "animation": valid_html,
            }
        )

        orchestrator = SwarmOrchestrator(api_url="http://localhost:8000/v1", api_key="test")
        result = orchestrator.run(_crawl_result())

        assert result.html  # Non-empty HTML output
        assert "analysis" in result.phases_completed
        assert "design" in result.phases_completed
        assert "selection" in result.phases_completed
        assert "build_iter1" in result.phases_completed
        assert "qa_iter1" in result.phases_completed
        assert result.iterations == 1
