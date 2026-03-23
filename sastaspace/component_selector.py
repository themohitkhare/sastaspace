# sastaspace/component_selector.py
"""Component matching algorithm for the React-based redesign pipeline.

Given a RedesignPlan, selects the best components from the component library
for each page section. Uses tier rankings, site type affinity, and layout
archetype matching to produce a ComponentManifest.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class SelectedComponent:
    """A component selected for use in a redesign."""

    category: str  # e.g., "heroes"
    category_group: str  # "marketing-blocks" or "ui-components"
    name: str  # e.g., "aceternity__lamp"
    title: str  # human-readable title
    tier: str  # gold / silver / bronze
    files: list[dict] = field(default_factory=list)  # [{path, content}]
    dependencies: list[str] = field(default_factory=list)
    registry_dependencies: list[str] = field(default_factory=list)
    tailwind_config: dict = field(default_factory=dict)
    description: str = ""
    downloads: int = 0
    likes: int = 0


@dataclass
class ComponentManifest:
    """Complete set of selected components for a redesign."""

    components: list[SelectedComponent] = field(default_factory=list)
    all_dependencies: set[str] = field(default_factory=set)
    all_tailwind_extensions: dict = field(default_factory=dict)

    def to_prompt_context(self) -> str:
        """Serialize selected components for the Composer LLM prompt."""
        parts = []
        for c in self.components:
            parts.append(f"### {c.category.upper()}: {c.title} ({c.name})")
            parts.append(f"Tier: {c.tier} | Downloads: {c.downloads}")
            if c.description:
                parts.append(f"Description: {c.description[:200]}")
            parts.append(f"Dependencies: {', '.join(c.dependencies) or 'none'}")
            for f in c.files:
                path = f.get("path", "unknown")
                content = f.get("content", "")
                parts.append(f"\n```tsx\n// {path}\n{content}\n```")
            parts.append("")
        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Section → Category mapping
# ---------------------------------------------------------------------------

# Maps content_type values (from Planner output) to component category directories
SECTION_TO_CATEGORY: dict[str, tuple[str, str]] = {
    # (category_dir, category_group)
    "navigation": ("navigation-menus", "marketing-blocks"),
    "nav": ("navigation-menus", "marketing-blocks"),
    "header": ("navigation-menus", "marketing-blocks"),
    "hero": ("heroes", "marketing-blocks"),
    "features": ("features", "marketing-blocks"),
    "feature": ("features", "marketing-blocks"),
    "pricing": ("pricing-sections", "marketing-blocks"),
    "testimonials": ("testimonials", "marketing-blocks"),
    "testimonial": ("testimonials", "marketing-blocks"),
    "clients": ("clients", "marketing-blocks"),
    "logos": ("clients", "marketing-blocks"),
    "partners": ("clients", "marketing-blocks"),
    "footer": ("footers", "marketing-blocks"),
    "cta": ("calls-to-action", "marketing-blocks"),
    "call-to-action": ("calls-to-action", "marketing-blocks"),
    "comparison": ("comparisons", "marketing-blocks"),
    "faq": ("accordions", "ui-components"),
    "gallery": ("images", "marketing-blocks"),
    "images": ("images", "marketing-blocks"),
    "video": ("videos", "marketing-blocks"),
    "about": ("features", "marketing-blocks"),
    "services": ("features", "marketing-blocks"),
    "team": ("clients", "marketing-blocks"),
    "contact": ("forms", "ui-components"),
    "stats": ("features", "marketing-blocks"),
    "blog": ("cards", "ui-components"),
}

# Default sections every page should have (in order)
DEFAULT_SECTIONS = ["navigation", "hero", "features", "cta", "footer"]

# Archetype → keyword affinities for scoring
ARCHETYPE_KEYWORDS: dict[str, list[str]] = {
    "bento": ["bento", "grid", "card", "mosaic", "mixed"],
    "editorial": ["editorial", "magazine", "typography", "serif", "column"],
    "split-hero": ["split", "side-by-side", "two-column", "50/50"],
    "minimal": ["minimal", "clean", "simple", "whitespace", "typography"],
    "scroll-story": ["scroll", "narrative", "story", "parallax", "full-width"],
    "dashboard": ["dashboard", "compact", "data", "metric", "stat"],
    "asymmetric": ["asymmetric", "creative", "offset", "overlap", "off-center"],
}

# Site type → keyword affinities for scoring
SITE_TYPE_KEYWORDS: dict[str, list[str]] = {
    "saas": ["saas", "app", "dashboard", "product", "startup", "pricing", "feature"],
    "portfolio": ["portfolio", "gallery", "showcase", "work", "project", "creative"],
    "ecommerce": ["product", "shop", "store", "price", "cart", "buy", "ecommerce"],
    "restaurant": ["menu", "food", "restaurant", "reservation", "chef", "dish"],
    "agency": ["agency", "studio", "creative", "services", "client", "work"],
    "blog": ["blog", "article", "post", "content", "read", "write"],
    "other": [],
}


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def _keyword_match_score(text: str, keywords: list[str]) -> float:
    """Score how well a text matches a set of keywords."""
    text_lower = text.lower()
    matches = sum(1 for kw in keywords if kw in text_lower)
    return matches / max(len(keywords), 1)


def _score_component(
    component_meta: dict,
    plan: dict,
    category: str,
) -> float:
    """Score a component candidate against the plan. Higher = better match."""
    score = 0.0
    title = component_meta.get("title", "").lower()
    reason = component_meta.get("reason", "").lower()
    desc = f"{title} {reason}"

    # Archetype match (most important for layout coherence)
    archetype = plan.get("layout_archetype", "")
    if archetype and archetype in ARCHETYPE_KEYWORDS:
        score += _keyword_match_score(desc, ARCHETYPE_KEYWORDS[archetype]) * 15

    # Site type match
    site_type = plan.get("site_type", "other")
    if site_type and site_type in SITE_TYPE_KEYWORDS:
        score += _keyword_match_score(desc, SITE_TYPE_KEYWORDS[site_type]) * 10

    # Popularity as tiebreaker (normalize to 0-5 range)
    # Downloads are typically 100-10000
    downloads = component_meta.get("downloads", 0)
    if isinstance(downloads, (int, float)):
        score += min(downloads / 2000, 5.0)

    # Likes as additional signal
    likes = component_meta.get("likes", 0)
    if isinstance(likes, (int, float)):
        score += min(likes / 20, 3.0)

    return score


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def _load_tiers(category: str, category_group: str, components_dir: Path) -> dict:
    """Load the tiers.json for a category. Returns {gold: [...], silver: [...], bronze: [...]}."""
    tiers_path = components_dir / category_group / category / "tiers.json"
    if not tiers_path.exists():
        logger.warning("No tiers.json found for %s/%s", category_group, category)
        return {}
    try:
        return json.loads(tiers_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load tiers.json for %s: %s", category, e)
        return {}


def _load_component_json(
    file_ref: str, category_group: str, category: str, components_dir: Path
) -> dict | None:
    """Load the full component JSON file."""
    # file_ref is like "aceternity__lamp.json"
    full_path = components_dir / category_group / category / file_ref
    if not full_path.exists():
        logger.warning("Component file not found: %s", full_path)
        return None
    try:
        return json.loads(full_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load component %s: %s", file_ref, e)
        return None


def _make_selected(
    comp_json: dict,
    comp_meta: dict,
    category: str,
    category_group: str,
    tier: str,
) -> SelectedComponent:
    """Build a SelectedComponent from a loaded component JSON and its tier metadata."""
    meta = comp_json.get("_meta", {})
    return SelectedComponent(
        category=category,
        category_group=category_group,
        name=comp_meta.get("file", "").replace(".json", ""),
        title=meta.get("title", comp_meta.get("title", "")),
        tier=tier,
        files=comp_json.get("files", []),
        dependencies=comp_json.get("dependencies", []),
        registry_dependencies=comp_json.get("registryDependencies", []),
        tailwind_config=comp_json.get("tailwind", {}).get("config", {}),
        description=meta.get("description", "")[:300],
        downloads=meta.get("downloads", 0),
        likes=meta.get("likes", 0),
    )


# ---------------------------------------------------------------------------
# Main selection logic
# ---------------------------------------------------------------------------


def _determine_sections(plan: dict) -> list[str]:
    """Determine which page sections are needed based on the plan."""
    sections = []

    # Always include navigation
    sections.append("navigation")

    # Always include hero
    sections.append("hero")

    # Parse content_sections from plan
    content_sections = plan.get("content_sections", [])
    seen_types = {"navigation", "hero"}

    for section in content_sections:
        content_type = section.get("content_type", "").lower().strip()
        if content_type and content_type not in seen_types:
            # Map to our section types
            if content_type in SECTION_TO_CATEGORY:
                sections.append(content_type)
                seen_types.add(content_type)

    # Ensure we have features if not already present
    if "features" not in seen_types and "feature" not in seen_types:
        sections.append("features")

    # Always include footer
    if "footer" not in seen_types:
        sections.append("footer")

    return sections


def _pick_best_for_category(
    category: str,
    category_group: str,
    plan: dict,
    components_dir: Path,
    max_candidates: int = 3,
) -> SelectedComponent | None:
    """Pick the best component for a given category."""
    tiers_data = _load_tiers(category, category_group, components_dir)
    if not tiers_data:
        return None

    # Try gold first, then silver. Skip bronze.
    for tier_name in ("gold", "silver"):
        candidates = tiers_data.get(tier_name, [])
        if not candidates:
            continue

        # Score each candidate
        scored = []
        for comp_meta in candidates:
            score = _score_component(comp_meta, plan, category)
            scored.append((score, comp_meta))

        scored.sort(key=lambda x: x[0], reverse=True)

        # Try loading the top candidates until we find one that works
        for score, comp_meta in scored[:max_candidates]:
            file_ref = comp_meta.get("file", "")
            if not file_ref:
                continue

            comp_json = _load_component_json(file_ref, category_group, category, components_dir)
            if comp_json is None:
                continue

            # Skip components with no files/content
            files = comp_json.get("files", [])
            if not files or not any(f.get("content") for f in files):
                continue

            selected = _make_selected(comp_json, comp_meta, category, category_group, tier_name)
            logger.info(
                "Selected %s/%s: %s (tier=%s, score=%.1f, downloads=%d)",
                category_group,
                category,
                selected.title,
                tier_name,
                score,
                selected.downloads,
            )
            return selected

    return None


def select_components(plan: dict, components_dir: Path) -> ComponentManifest:
    """Select the best components for each section of the redesign plan.

    Args:
        plan: The RedesignPlan as a dict (from plan.model_dump()).
        components_dir: Path to the components/ directory.

    Returns:
        ComponentManifest with selected components and aggregated dependencies.
    """
    sections = _determine_sections(plan)
    logger.info("Determined %d sections needed: %s", len(sections), sections)

    selected: list[SelectedComponent] = []
    all_deps: set[str] = set()
    seen_categories: set[str] = set()

    for section_type in sections:
        mapping = SECTION_TO_CATEGORY.get(section_type)
        if not mapping:
            logger.debug("No category mapping for section type: %s", section_type)
            continue

        category, category_group = mapping

        # Avoid duplicate category selections
        cache_key = f"{category_group}/{category}"
        if cache_key in seen_categories:
            continue
        seen_categories.add(cache_key)

        component = _pick_best_for_category(category, category_group, plan, components_dir)
        if component:
            selected.append(component)
            all_deps.update(component.dependencies)

    # Merge tailwind configs
    merged_tw: dict = {}
    for comp in selected:
        if comp.tailwind_config:
            _deep_merge(merged_tw, comp.tailwind_config)

    manifest = ComponentManifest(
        components=selected,
        all_dependencies=all_deps,
        all_tailwind_extensions=merged_tw,
    )

    logger.info(
        "Component selection complete: %d components, %d unique dependencies",
        len(selected),
        len(all_deps),
    )
    return manifest


def _deep_merge(base: dict, override: dict) -> None:
    """Deep merge override into base (mutates base)."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
