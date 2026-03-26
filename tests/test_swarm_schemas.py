# tests/test_swarm_schemas.py
import pytest

from sastaspace.swarm.schemas import (
    ColorPalette,
    ComponentManifest,
    ComponentSlot,
    ContentMap,
    ContentSlot,
    KISSMetrics,
    SiteClassification,
    SpecChallengerResult,
    SpecIssue,
)


class TestSiteClassification:
    def test_valid_classification(self):
        sc = SiteClassification(
            site_type="saas",
            industry="developer tools",
            complexity_score=7,
            output_format="react",
            output_format_reasoning="5+ sections with pricing table",
            sections_detected=["hero", "features", "pricing", "testimonials", "footer"],
            conversion_goals=["sign up for free trial"],
        )
        assert sc.site_type == "saas"
        assert sc.output_format in ("html", "react")

    def test_complexity_score_bounds(self):
        with pytest.raises(Exception):
            SiteClassification(
                site_type="blog",
                industry="tech",
                complexity_score=11,
                output_format="html",
                output_format_reasoning="simple",
                sections_detected=["hero"],
                conversion_goals=[],
            )


class TestContentMap:
    def test_content_map_with_slots(self):
        cm = ContentMap(
            texts=[ContentSlot(location="hero.heading", content="Welcome to Acme")],
            image_urls=[{"url": "https://acme.com/logo.png", "context": "logo"}],
            ctas=["Sign Up Free"],
            nav_items=["Home", "About", "Pricing"],
            forms=[],
            pricing_tables=[],
        )
        assert len(cm.texts) == 1
        assert cm.texts[0].location == "hero.heading"


class TestSpecChallenger:
    def test_approved(self):
        r = SpecChallengerResult(approved=True, issues=[])
        assert r.approved

    def test_blocking_issue(self):
        r = SpecChallengerResult(
            approved=False,
            issues=[
                SpecIssue(
                    category="missing_content",
                    severity="blocking",
                    description="No pricing data extracted",
                    recommendation="Re-run content extractor with pricing focus",
                )
            ],
        )
        assert not r.approved
        assert r.issues[0].severity == "blocking"


class TestColorPalette:
    def test_requires_fallback_fonts(self):
        cp = ColorPalette(
            primary="#1a1a2e",
            secondary="#16213e",
            accent="#e94560",
            background="#0f3460",
            text="#eee",
            headline_font="'Inter', 'Helvetica Neue', Arial, sans-serif",
            body_font="'Source Sans 3', 'Segoe UI', sans-serif",
            color_mode="dark",
            roundness="8px",
            rationale="Dark theme for developer tools",
        )
        assert "sans-serif" in cp.headline_font
        assert "sans-serif" in cp.body_font


class TestKISSMetrics:
    def test_scores_in_range(self):
        k = KISSMetrics(
            cognitive_load=6,
            visual_noise_budget=4,
            interaction_cost_limit=3,
            content_density_target=5,
            animation_budget="moderate",
        )
        assert 1 <= k.cognitive_load <= 10


class TestComponentManifest:
    def test_slot_definitions(self):
        m = ComponentManifest(
            sections=[
                ComponentSlot(
                    section_name="hero",
                    component_id="hero-001",
                    component_path="marketing-blocks/heroes/aceternity__lamp.json",
                    slot_definitions={"heading": "string", "subheading": "string", "cta": "string"},
                    placement_order=0,
                )
            ]
        )
        assert m.sections[0].slot_definitions["heading"] == "string"
