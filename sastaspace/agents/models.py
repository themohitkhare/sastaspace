# sastaspace/agents/models.py
"""Pydantic models for the Agno multi-agent redesign pipeline."""

from __future__ import annotations

from pydantic import BaseModel, Field

# --- Crawl Analyst output ---


class BrandProfile(BaseModel):
    """Extracted brand identity from the crawled site."""

    name: str = ""
    tagline: str = ""
    voice_tone: str = ""  # e.g. "professional", "playful", "corporate"
    industry: str = ""


class ContentSection(BaseModel):
    """A logical content section identified on the page."""

    heading: str = ""
    content_summary: str = ""
    content_type: str = ""  # e.g. "hero", "features", "testimonials", "pricing", "footer"
    importance: int = Field(default=5, ge=1, le=10)


class SiteAnalysis(BaseModel):
    """Complete analysis of a crawled website — output of the CrawlAnalyst agent."""

    brand: BrandProfile = Field(default_factory=BrandProfile)
    primary_goal: str = ""  # e.g. "lead generation", "e-commerce", "portfolio"
    target_audience: str = ""
    content_sections: list[ContentSection] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    key_content: str = ""  # important text that must be preserved
    existing_colors: list[str] = Field(default_factory=list)
    existing_fonts: list[str] = Field(default_factory=list)


# --- Design Strategist output ---


class ColorPalette(BaseModel):
    """Color palette recommendation for the redesign."""

    primary: str = "#0066cc"
    secondary: str = "#444444"
    accent: str = "#ff6600"
    background: str = "#ffffff"
    text: str = "#333333"
    rationale: str = ""


class TypographyPlan(BaseModel):
    """Typography choices for the redesign."""

    heading_font: str = "Inter"
    body_font: str = "Inter"
    google_fonts_import: str = ""
    rationale: str = ""


class Component(BaseModel):
    """A UI component to include in the redesign."""

    name: str = ""  # e.g. "hero-section", "feature-grid", "testimonial-carousel"
    description: str = ""
    layout_hint: str = ""  # e.g. "CSS Grid 3-col", "Flexbox centered"


class DesignBrief(BaseModel):
    """Design strategy and plan — output of the DesignStrategist agent."""

    design_direction: str = ""  # overall design approach
    colors: ColorPalette = Field(default_factory=ColorPalette)
    typography: TypographyPlan = Field(default_factory=TypographyPlan)
    layout_strategy: str = ""  # e.g. "single-page scroll with sticky nav"
    components: list[Component] = Field(default_factory=list)
    conversion_strategy: str = ""  # how to optimize for the site's goal
    responsive_approach: str = ""
    animations: list[str] = Field(default_factory=list)


# --- Quality Reviewer output ---


class QualityIssue(BaseModel):
    """A quality issue found in the generated HTML."""

    severity: str = "warning"  # "critical", "warning", "info"
    category: str = ""  # e.g. "accessibility", "responsive", "content", "performance"
    description: str = ""
    suggestion: str = ""


class QualityReport(BaseModel):
    """Quality review of generated HTML — output of the QualityReviewer agent."""

    passed: bool = False
    overall_score: int = Field(default=5, ge=1, le=10)
    issues: list[QualityIssue] = Field(default_factory=list)
    feedback_for_regeneration: str = ""  # specific instructions if passed=False
    strengths: list[str] = Field(default_factory=list)


# --- Pipeline result wrapper ---


class AgnoRedesignResult(BaseModel):
    """Final result from the Agno multi-agent pipeline."""

    html: str
    site_analysis: SiteAnalysis | None = None
    design_brief: DesignBrief | None = None
    quality_report: QualityReport | None = None
    retry_count: int = 0
