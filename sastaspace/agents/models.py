# sastaspace/agents/models.py
"""Pydantic models for the Agno multi-agent redesign pipeline."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

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

    @field_validator("animations", mode="before")
    @classmethod
    def coerce_animations(cls, v: object) -> list[str]:
        """Accept list[str] or list[dict] — Claude sometimes returns dicts."""
        if not isinstance(v, list):
            return []
        result = []
        for item in v:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                # e.g. {"element": "Hero", "animation": "fade-in", "duration": "15s"}
                parts = [str(val) for val in item.values() if val]
                result.append(": ".join(parts))
            else:
                result.append(str(item))
        return result


# --- Copywriter output ---


class CopywriterCTA(BaseModel):
    """A call-to-action written by the copywriter."""

    text: str = ""
    context: str = ""  # where this CTA appears on the page


class CopywriterSection(BaseModel):
    """A rewritten content section."""

    original_heading: str = ""
    new_heading: str = ""
    new_body: str = ""
    section_type: str = ""  # features, testimonials, pricing, about, etc.


class CopywriterOutput(BaseModel):
    """Conversion-optimized copy — output of the Copywriter agent."""

    headline: str = ""
    subheadline: str = ""
    cta_primary: CopywriterCTA = Field(default_factory=CopywriterCTA)
    cta_secondary: CopywriterCTA = Field(default_factory=CopywriterCTA)
    sections: list[CopywriterSection] = Field(default_factory=list)
    meta_title: str = ""
    meta_description: str = ""


# --- Component Selector output ---


class SelectedComponent(BaseModel):
    """A component selected from the library for use in the redesign."""

    category: str = ""  # e.g. "heroes", "testimonials", "pricing-sections"
    name: str = ""  # component name from the catalog
    file: str = ""  # path to the JSON file containing the source code
    rationale: str = ""  # why this component was selected for this business
    conversion_impact: str = ""  # how it helps sell/convert


class ComponentSelection(BaseModel):
    """Selected components from the library — output of the ComponentSelector agent."""

    selected: list[SelectedComponent] = Field(default_factory=list)
    strategy: str = ""  # overall component selection strategy
    # what was considered but not chosen
    rejected_alternatives: list[str] = Field(default_factory=list)


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
