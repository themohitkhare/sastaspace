# tests/test_models.py
"""Tests for Pydantic model coercions — catches OSS model type quirks."""

import pytest

from sastaspace.agents.models import (
    ContentSection,
    DesignBrief,
    QualityReport,
    SiteAnalysis,
)


# --- ContentSection.importance coercion ---


def test_content_section_importance_float_rounds():
    """GLM4 returns 4.5 for importance; must round to int without crashing."""
    s = ContentSection(importance=4.5)
    assert s.importance == 4  # round(4.5) == 4 (banker's rounding)


def test_content_section_importance_float_rounds_up():
    s = ContentSection(importance=7.6)
    assert s.importance == 8


def test_content_section_importance_int_passthrough():
    s = ContentSection(importance=6)
    assert s.importance == 6


def test_content_section_importance_default():
    s = ContentSection()
    assert s.importance == 5


# --- QualityReport.overall_score coercion ---


def test_quality_report_score_float_rounds():
    r = QualityReport(overall_score=7.5)
    assert r.overall_score == 8


def test_quality_report_score_int_passthrough():
    r = QualityReport(overall_score=9)
    assert r.overall_score == 9


# --- DesignBrief.animations coercion (pre-existing) ---


def test_design_brief_animations_list_of_dicts():
    """Claude/GLM4 may return list[dict] for animations."""
    brief = DesignBrief(
        animations=[
            {"element": "Hero", "animation": "fade-in", "duration": "0.5s"},
            "scroll-reveal",
        ]
    )
    assert len(brief.animations) == 2
    assert "fade-in" in brief.animations[0]
    assert brief.animations[1] == "scroll-reveal"


def test_design_brief_animations_non_list_becomes_empty():
    brief = DesignBrief(animations="fade-in")  # type: ignore[arg-type]
    assert brief.animations == []


# --- SiteAnalysis with float importance survives full parse ---


def test_site_analysis_with_float_importance():
    """Full integration: GLM4 JSON with float importance must parse cleanly."""
    data = {
        "brand": {"name": "Test Co", "tagline": "", "voice_tone": "pro", "industry": "Tech"},
        "primary_goal": "leads",
        "target_audience": "SMBs",
        "content_sections": [
            {
                "heading": "Hero",
                "content_summary": "Main hero",
                "content_type": "hero",
                "importance": 9.0,
            },
            {
                "heading": "Features",
                "content_summary": "Feature list",
                "content_type": "features",
                "importance": 4.5,
            },
        ],
        "strengths": [],
        "weaknesses": [],
        "key_content": "",
        "existing_colors": [],
        "existing_fonts": [],
    }
    analysis = SiteAnalysis.model_validate(data)
    assert analysis.content_sections[0].importance == 9
    assert analysis.content_sections[1].importance == 4
