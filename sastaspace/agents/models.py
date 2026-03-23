# sastaspace/agents/models.py
"""Pydantic models for the Agno multi-agent redesign pipeline."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator


def _coerce_int(v: object) -> object:
    """Round floats to int — open-source models often return 4.5 instead of 4."""
    if isinstance(v, float):
        return round(v)
    return v


def _coerce_str(v: object) -> object:
    """Coerce None to empty string — LLMs often return null for optional strings."""
    if v is None:
        return ""
    return v


def _is_str_dict_field(field_info) -> bool:
    """Check if a Pydantic field is annotated as dict[str, str]."""
    ann = str(field_info.annotation or "")
    return "dict[str, str]" in ann or "Dict[str, str]" in ann


def _is_str_list_field(field_info) -> bool:
    """Check if a Pydantic field is annotated as list[str]."""
    ann = str(field_info.annotation or "")
    return "list[str]" in ann or "List[str]" in ann


def _flatten_to_str(v: object) -> str:
    """Flatten non-string values to string. LLMs return dicts/lists where str is expected."""
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, list):
        # e.g. [{"text": "Product", "url": "/product"}, ...] → "Product, ..."
        parts = []
        for item in v:
            if isinstance(item, dict):
                parts.append(item.get("text", item.get("name", str(item))))
            else:
                parts.append(str(item))
        return ", ".join(parts)
    if isinstance(v, dict):
        # e.g. {"Product": [...], "Company": [...]} → "Product, Company"
        return ", ".join(str(k) for k in v.keys())
    return str(v)


class _NullSafeModel(BaseModel):
    """Base model that coerces null values to defaults for all str fields.

    LLMs (especially Gemini) frequently return null instead of "" for
    optional string fields. This base class handles it globally.
    """

    @model_validator(mode="before")
    @classmethod
    def coerce_nulls_to_defaults(cls, data: dict) -> dict:
        if not isinstance(data, dict):
            return data
        for field_name, field_info in cls.model_fields.items():
            if field_name not in data:
                continue
            val = data[field_name]
            # Coerce None → default for simple fields
            if val is None:
                data[field_name] = field_info.default if field_info.default is not None else ""
            # Coerce values inside dict[str, str] fields (e.g. content_map)
            elif isinstance(val, dict) and _is_str_dict_field(field_info):
                data[field_name] = {
                    k: (_flatten_to_str(v) if not isinstance(v, str) else v) for k, v in val.items()
                }
            # Coerce None items inside list[str] fields (e.g. content_warnings)
            # Only coerce None→"", leave dicts for field_validators (e.g. animations)
            elif isinstance(val, list) and _is_str_list_field(field_info):
                data[field_name] = [(item if item is not None else "") for item in val]
        return data


# --- Crawl Analyst output ---


class BrandProfile(_NullSafeModel):
    """Extracted brand identity from the crawled site."""

    name: str = ""
    tagline: str = ""
    voice_tone: str = ""  # e.g. "professional", "playful", "corporate"
    industry: str = ""
    personality: str = ""  # deeper brand character for design decisions


class ContentSection(_NullSafeModel):
    """A logical content section identified on the page."""

    heading: str = ""
    content_summary: str = ""
    content_type: str = ""  # e.g. "hero", "features", "testimonials", "pricing", "footer"
    importance: int = Field(default=5, ge=1, le=10)
    exact_text: str = ""  # verbatim text from the page for anti-hallucination binding

    @field_validator("importance", mode="before")
    @classmethod
    def coerce_importance(cls, v: object) -> object:
        return _coerce_int(v)


class SiteAnalysis(_NullSafeModel):
    """Complete analysis of a crawled website — output of the CrawlAnalyst agent."""

    brand: BrandProfile = Field(default_factory=BrandProfile)
    primary_goal: str = ""  # e.g. "lead generation", "e-commerce", "portfolio"
    target_audience: str = ""
    visual_identity: str = ""  # descriptive: "minimal dark theme", "bold corporate", etc.
    content_sections: list[ContentSection] = Field(default_factory=list)
    content_absent: list[str] = Field(default_factory=list)  # what the site does NOT have
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    key_content: str = ""  # important text that must be preserved
    existing_colors: list[str] = Field(default_factory=list)
    existing_fonts: list[str] = Field(default_factory=list)


# --- Design Strategist output ---


class ColorPalette(_NullSafeModel):
    """Color palette recommendation for the redesign."""

    primary: str = ""
    secondary: str = ""
    accent: str = ""
    background: str = ""
    text: str = ""
    rationale: str = ""


class DesignTokens(_NullSafeModel):
    """Exact design tokens ensuring visual consistency without a normalizer pass."""

    spacing_unit: str = "8px"
    border_radius_sm: str = "4px"
    border_radius_md: str = "8px"
    border_radius_lg: str = "16px"
    shadow_sm: str = ""
    shadow_md: str = ""
    shadow_lg: str = ""
    transition_speed: str = "200ms"
    max_content_width: str = "1200px"


class TypographyPlan(_NullSafeModel):
    """Typography choices for the redesign."""

    heading_font: str = "Inter"
    body_font: str = "Inter"
    google_fonts_import: str = ""
    rationale: str = ""


class Component(_NullSafeModel):
    """A UI component to include in the redesign."""

    name: str = ""  # e.g. "hero-section", "feature-grid", "testimonial-carousel"
    description: str = ""
    layout_hint: str = ""  # e.g. "CSS Grid 3-col", "Flexbox centered"


class DesignBrief(_NullSafeModel):
    """Design strategy and plan — output of the DesignStrategist agent."""

    design_direction: str = ""  # overall design approach
    layout_archetype: str = ""  # bento, editorial, split-hero, asymmetric, etc.
    colors: ColorPalette = Field(default_factory=ColorPalette)
    typography: TypographyPlan = Field(default_factory=TypographyPlan)
    design_tokens: DesignTokens = Field(default_factory=DesignTokens)
    layout_strategy: str = ""  # e.g. "single-page scroll with sticky nav"
    components: list[Component] = Field(default_factory=list)
    conversion_strategy: str = ""  # how to optimize for the site's goal
    responsive_approach: str = ""
    animations: list[str] = Field(default_factory=list)
    anti_patterns: list[str] = Field(default_factory=list)  # site-specific things to avoid

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


class CopywriterCTA(_NullSafeModel):
    """A call-to-action written by the copywriter."""

    text: str = ""
    context: str = ""  # where this CTA appears on the page


class CopywriterSection(_NullSafeModel):
    """A rewritten content section."""

    original_heading: str = ""
    new_heading: str = ""
    new_body: str = ""
    section_type: str = ""  # features, testimonials, pricing, about, etc.


class CopywriterOutput(_NullSafeModel):
    """Conversion-optimized copy — output of the Copywriter agent."""

    headline: str = ""
    subheadline: str = ""
    cta_primary: CopywriterCTA = Field(default_factory=CopywriterCTA)
    cta_secondary: CopywriterCTA = Field(default_factory=CopywriterCTA)
    sections: list[CopywriterSection] = Field(default_factory=list)
    # Strict key→text binding: HTMLGenerator can ONLY use these strings
    content_map: dict[str, str] = Field(default_factory=dict)
    content_warnings: list[str] = Field(default_factory=list)
    meta_title: str = ""
    meta_description: str = ""


# --- Component Selector output ---


class SelectedComponent(_NullSafeModel):
    """A component selected from the library for use in the redesign."""

    category: str = ""  # e.g. "heroes", "testimonials", "pricing-sections"
    name: str = ""  # component name from the catalog
    file: str = ""  # path to the JSON file containing the source code
    rationale: str = ""  # why this component was selected for this business
    conversion_impact: str = ""  # how it helps sell/convert


class ComponentSelection(_NullSafeModel):
    """Selected components from the library — output of the ComponentSelector agent."""

    selected: list[SelectedComponent] = Field(default_factory=list)
    strategy: str = ""  # overall component selection strategy
    # what was considered but not chosen
    rejected_alternatives: list[str] = Field(default_factory=list)


# --- Quality Reviewer output ---


class QualityIssue(_NullSafeModel):
    """A quality issue found in the generated HTML."""

    severity: str = "warning"  # "critical", "warning", "info"
    category: str = ""  # e.g. "accessibility", "responsive", "content", "performance"
    description: str = ""
    suggestion: str = ""


class QualityReport(_NullSafeModel):
    """Quality review of generated HTML — output of the QualityReviewer agent."""

    passed: bool = False
    overall_score: int = Field(default=5, ge=1, le=10)
    uniqueness_score: int = Field(default=5, ge=1, le=10)
    brand_adherence_score: int = Field(default=5, ge=1, le=10)

    @field_validator("overall_score", "uniqueness_score", "brand_adherence_score", mode="before")
    @classmethod
    def coerce_scores(cls, v: object) -> object:
        return _coerce_int(v)

    hallucinated_content: list[str] = Field(default_factory=list)
    issues: list[QualityIssue] = Field(default_factory=list)
    feedback_for_regeneration: str = ""  # specific instructions if passed=False
    strengths: list[str] = Field(default_factory=list)
