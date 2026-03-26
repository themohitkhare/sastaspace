# sastaspace/swarm/schemas.py
"""Pydantic models for swarm agent inputs and outputs."""

from __future__ import annotations

from pydantic import BaseModel, Field

# --- Phase 1: Analysis ---


class SiteClassification(BaseModel):
    site_type: str = Field(
        description="blog|ecommerce|portfolio|saas|agency|restaurant|nonprofit|other"
    )
    industry: str
    complexity_score: int = Field(ge=1, le=10)
    output_format: str = Field(description="html|react", pattern=r"^(html|react)$")
    output_format_reasoning: str
    sections_detected: list[str]
    conversion_goals: list[str]


class ContentSlot(BaseModel):
    location: str = Field(description="Dot-notation location, e.g. 'hero.heading'")
    content: str


class ContentMap(BaseModel):
    texts: list[ContentSlot]
    image_urls: list[dict]
    ctas: list[str]
    nav_items: list[str]
    forms: list[dict] = Field(default_factory=list)
    pricing_tables: list[dict] = Field(default_factory=list)


class BusinessProfile(BaseModel):
    industry: str
    target_audience: str
    value_proposition: str
    revenue_model: str
    key_differentiators: list[str]
    brand_voice: str
    competitive_positioning: str = ""


class SpecIssue(BaseModel):
    category: str = Field(
        description="missing_content|wrong_classification|business_assumption|edge_case"
    )
    severity: str = Field(description="blocking|warning", pattern=r"^(blocking|warning)$")
    description: str
    recommendation: str


class SpecChallengerResult(BaseModel):
    approved: bool
    issues: list[SpecIssue] = Field(default_factory=list)


# --- Phase 2: Design Strategy ---


class ColorPalette(BaseModel):
    primary: str
    secondary: str
    accent: str
    background: str
    text: str
    headline_font: str = Field(description="Must include web-safe fallback stack")
    body_font: str = Field(description="Must include web-safe fallback stack")
    color_mode: str = Field(description="light|dark", pattern=r"^(light|dark)$")
    roundness: str
    rationale: str = ""


class UXWireframe(BaseModel):
    layout_pattern: str = Field(description="F-pattern|Z-pattern|single-column|dashboard")
    section_order: list[str] = Field(description="Ordered list of section names")
    conversion_funnel: list[str] = Field(description="AIDA stages mapped to sections")
    mobile_strategy: str = Field(default="stack-and-simplify")
    sticky_header: bool = True
    industry_patterns: list[str] = Field(default_factory=list)


class KISSMetrics(BaseModel):
    cognitive_load: int = Field(ge=1, le=10)
    visual_noise_budget: int = Field(ge=1, le=10)
    interaction_cost_limit: int = Field(ge=1, le=10)
    content_density_target: int = Field(ge=1, le=10)
    animation_budget: str = Field(description="none|minimal|moderate|rich")


# --- Phase 3: Selection ---


class ComponentSlot(BaseModel):
    section_name: str
    component_id: str
    component_path: str
    slot_definitions: dict[str, str] = Field(description="slot_name -> type (string, list, etc.)")
    placement_order: int


class ComponentManifest(BaseModel):
    sections: list[ComponentSlot]


class SlotMappedCopy(BaseModel):
    slots: dict[str, str] = Field(description="Dot-notation slot -> polished copy text")
    unmapped_content: list[str] = Field(
        default_factory=list,
        description="Original content that couldn't be mapped to any slot",
    )


# --- Phase 4: Build ---


class SectionFragment(BaseModel):
    section_name: str
    html: str
    css: str = ""
    js: str = ""


class AnimationEnhancement(BaseModel):
    enhanced_html: str
    animations_added: list[str] = Field(default_factory=list)
    kiss_score_respected: bool = True


# --- Phase 5: QA ---


class VisualQAResult(BaseModel):
    layout_alignment: int = Field(ge=1, le=10)
    whitespace_balance: int = Field(ge=1, le=10)
    typography_hierarchy: int = Field(ge=1, le=10)
    color_harmony: int = Field(ge=1, le=10)
    image_rendering: int = Field(ge=1, le=10)
    passed: bool
    feedback: str = ""


class ContentQAResult(BaseModel):
    hallucinated_content: list[str] = Field(default_factory=list)
    missing_sections: list[str] = Field(default_factory=list)
    broken_links: list[str] = Field(default_factory=list)
    passed: bool
    feedback: str = ""


class A11ySEOResult(BaseModel):
    contrast_issues: list[str] = Field(default_factory=list)
    heading_issues: list[str] = Field(default_factory=list)
    missing_meta: list[str] = Field(default_factory=list)
    missing_alt_text: int = 0
    passed: bool
    feedback: str = ""
