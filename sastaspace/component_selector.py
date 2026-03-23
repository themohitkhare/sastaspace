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
    # Navigation
    "navigation": ("navigation-menus", "marketing-blocks"),
    "nav": ("navigation-menus", "marketing-blocks"),
    "header": ("navigation-menus", "marketing-blocks"),
    "menu": ("navigation-menus", "marketing-blocks"),
    "navbar": ("navigation-menus", "marketing-blocks"),
    # Hero
    "hero": ("heroes", "marketing-blocks"),
    "banner": ("heroes", "marketing-blocks"),
    # Features / Services / About
    "features": ("features", "marketing-blocks"),
    "feature": ("features", "marketing-blocks"),
    "about": ("features", "marketing-blocks"),
    "services": ("features", "marketing-blocks"),
    "stats": ("features", "marketing-blocks"),
    "benefits": ("features", "marketing-blocks"),
    "how-it-works": ("features", "marketing-blocks"),
    # Pricing
    "pricing": ("pricing-sections", "marketing-blocks"),
    "plans": ("pricing-sections", "marketing-blocks"),
    # Social proof
    "testimonials": ("testimonials", "marketing-blocks"),
    "testimonial": ("testimonials", "marketing-blocks"),
    "reviews": ("testimonials", "marketing-blocks"),
    "clients": ("clients", "marketing-blocks"),
    "logos": ("clients", "marketing-blocks"),
    "partners": ("clients", "marketing-blocks"),
    "brands": ("clients", "marketing-blocks"),
    "team": ("clients", "marketing-blocks"),
    # Footer
    "footer": ("footers", "marketing-blocks"),
    # CTA
    "cta": ("calls-to-action", "marketing-blocks"),
    "call-to-action": ("calls-to-action", "marketing-blocks"),
    # Comparison / FAQ
    "comparison": ("comparisons", "marketing-blocks"),
    "faq": ("accordions", "ui-components"),
    "accordion": ("accordions", "ui-components"),
    # Media
    "gallery": ("images", "marketing-blocks"),
    "images": ("images", "marketing-blocks"),
    "photos": ("images", "marketing-blocks"),
    "video": ("videos", "marketing-blocks"),
    "videos": ("videos", "marketing-blocks"),
    # Content blocks
    "announcement": ("announcements", "marketing-blocks"),
    "announcements": ("announcements", "marketing-blocks"),
    "text": ("texts", "marketing-blocks"),
    "content": ("texts", "marketing-blocks"),
    "copy": ("texts", "marketing-blocks"),
    # Interactive / UI
    "carousel": ("carousels", "ui-components"),
    "slider": ("carousels", "ui-components"),
    "tabs": ("tabs", "ui-components"),
    "cards": ("cards", "ui-components"),
    "contact": ("forms", "ui-components"),
    "form": ("forms", "ui-components"),
    "signup": ("sign-ups", "ui-components"),
    "sign-up": ("sign-ups", "ui-components"),
    "login": ("sign-ins", "ui-components"),
    "sign-in": ("sign-ins", "ui-components"),
    # Blog / Articles
    "blog": ("cards", "ui-components"),
    "articles": ("cards", "ui-components"),
    "posts": ("cards", "ui-components"),
    # Decorative
    "background": ("backgrounds", "marketing-blocks"),
    "scroll": ("scroll-areas", "marketing-blocks"),
    "dock": ("docks", "marketing-blocks"),
    "map": ("maps", "marketing-blocks"),
    "location": ("maps", "marketing-blocks"),
}

# Default sections every page should have (in order)
DEFAULT_SECTIONS = ["navigation", "hero", "features", "cta", "footer"]

# Archetype → keyword affinities for scoring
ARCHETYPE_KEYWORDS: dict[str, list[str]] = {
    "bento": ["bento", "grid", "card", "mosaic", "mixed", "tile"],
    "editorial": ["editorial", "magazine", "typography", "serif", "column", "article"],
    "split-hero": ["split", "side-by-side", "two-column", "50/50", "left-right"],
    "minimal": ["minimal", "clean", "simple", "whitespace", "typography", "elegant"],
    "scroll-story": ["scroll", "narrative", "story", "parallax", "full-width", "cinematic"],
    "dashboard": ["dashboard", "compact", "data", "metric", "stat", "dense"],
    "asymmetric": ["asymmetric", "creative", "offset", "overlap", "off-center", "dynamic"],
}

# Site type → keyword affinities for scoring
SITE_TYPE_KEYWORDS: dict[str, list[str]] = {
    "saas": ["saas", "app", "dashboard", "product", "startup", "pricing", "feature", "platform"],
    "portfolio": ["portfolio", "gallery", "showcase", "work", "project", "creative", "design"],
    "ecommerce": ["product", "shop", "store", "price", "cart", "buy", "ecommerce", "commerce"],
    "restaurant": ["menu", "food", "restaurant", "reservation", "chef", "dish", "dining"],
    "agency": ["agency", "studio", "creative", "services", "client", "work", "team"],
    "blog": ["blog", "article", "post", "content", "read", "write", "editorial"],
    "landing": ["landing", "launch", "waitlist", "coming-soon", "signup", "conversion"],
    "other": [],
}

# Tier bonus: gold components get a base score boost over silver and bronze
_TIER_BONUS = {"gold": 5.0, "silver": 2.0, "bronze": 0.0}


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
    tier_name: str = "gold",
) -> float:
    """Score a component candidate against the plan. Higher = better match."""
    score = 0.0
    title = component_meta.get("title", "").lower()
    reason = component_meta.get("reason", "").lower()
    desc = f"{title} {reason}"

    # Tier bonus — prefer gold over silver over bronze
    score += _TIER_BONUS.get(tier_name, 0.0)

    # Archetype match (most important for layout coherence)
    archetype = plan.get("layout_archetype", "")
    if archetype and archetype in ARCHETYPE_KEYWORDS:
        score += _keyword_match_score(desc, ARCHETYPE_KEYWORDS[archetype]) * 20

    # Site type match
    site_type = plan.get("site_type", "other")
    if site_type and site_type in SITE_TYPE_KEYWORDS:
        score += _keyword_match_score(desc, SITE_TYPE_KEYWORDS[site_type]) * 12

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

# Cache loaded tiers.json to avoid re-reading within a single selection run
_tiers_cache: dict[str, dict] = {}


def _load_tiers(category: str, category_group: str, components_dir: Path) -> dict:
    """Load the tiers.json for a category. Returns {gold: [...], silver: [...], bronze: [...]}."""
    cache_key = f"{category_group}/{category}"
    if cache_key in _tiers_cache:
        return _tiers_cache[cache_key]

    tiers_path = components_dir / category_group / category / "tiers.json"
    if not tiers_path.exists():
        logger.warning("No tiers.json found for %s/%s", category_group, category)
        _tiers_cache[cache_key] = {}
        return {}
    try:
        data = json.loads(tiers_path.read_text())
        _tiers_cache[cache_key] = data
        return data
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load tiers.json for %s: %s", category, e)
        _tiers_cache[cache_key] = {}
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
        if not content_type or content_type in seen_types:
            continue

        if content_type in SECTION_TO_CATEGORY:
            sections.append(content_type)
            seen_types.add(content_type)
        else:
            # Fuzzy match: try singular/plural and partial matching
            matched = _fuzzy_match_section(content_type)
            if matched and matched not in seen_types:
                sections.append(matched)
                seen_types.add(matched)
                logger.info(
                    "Fuzzy-matched content_type '%s' to section '%s'", content_type, matched
                )
            else:
                logger.warning("Unmapped content_type '%s' from Planner — skipping", content_type)

    # Ensure we have features if not already present
    if "features" not in seen_types and "feature" not in seen_types:
        sections.append("features")

    # Always include footer
    if "footer" not in seen_types:
        sections.append("footer")

    return sections


def _fuzzy_match_section(content_type: str) -> str | None:
    """Try to fuzzy-match a content_type to a known section mapping.

    Handles common variations like plurals, hyphenation, and partial matches.
    """
    ct = content_type.lower().strip()

    # Try removing trailing 's' for plural → singular
    if ct.endswith("s") and ct[:-1] in SECTION_TO_CATEGORY:
        return ct[:-1]

    # Try adding trailing 's' for singular → plural
    if ct + "s" in SECTION_TO_CATEGORY:
        return ct + "s"

    # Try replacing spaces with hyphens
    hyphenated = ct.replace(" ", "-")
    if hyphenated in SECTION_TO_CATEGORY:
        return hyphenated

    # Try substring match — if content_type contains a known key
    for key in SECTION_TO_CATEGORY:
        if key in ct or ct in key:
            return key

    return None


def _try_load_candidate(
    comp_meta: dict,
    category: str,
    category_group: str,
    tier_name: str,
    components_dir: Path,
) -> SelectedComponent | None:
    """Try to load a single candidate component. Returns None if invalid."""
    file_ref = comp_meta.get("file", "")
    if not file_ref:
        return None

    comp_json = _load_component_json(file_ref, category_group, category, components_dir)
    if comp_json is None:
        return None

    files = comp_json.get("files", [])
    if not files or not any(f.get("content") for f in files):
        return None

    return _make_selected(comp_json, comp_meta, category, category_group, tier_name)


def _pick_best_for_category(
    category: str,
    category_group: str,
    plan: dict,
    components_dir: Path,
    max_candidates: int = 3,
) -> SelectedComponent | None:
    """Pick the best component for a given category.

    Tries gold tier first, then silver, then bronze as fallback.
    Bronze is only used if gold and silver yield no loadable candidates.
    """
    tiers_data = _load_tiers(category, category_group, components_dir)
    if not tiers_data:
        return None

    # Try gold first, then silver, then bronze as last resort
    for tier_name in ("gold", "silver", "bronze"):
        candidates = tiers_data.get(tier_name, [])
        if not candidates:
            continue

        scored = [(_score_component(m, plan, category, tier_name), m) for m in candidates]
        scored.sort(key=lambda x: x[0], reverse=True)

        for score, comp_meta in scored[:max_candidates]:
            selected = _try_load_candidate(
                comp_meta, category, category_group, tier_name, components_dir
            )
            if selected is None:
                continue
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


def _select_for_sections(
    sections: list[str], plan: dict, components_dir: Path
) -> tuple[list[SelectedComponent], set[str]]:
    """Select the best component for each section, collecting dependencies."""
    selected: list[SelectedComponent] = []
    all_deps: set[str] = set()
    seen_categories: set[str] = set()

    for section_type in sections:
        mapping = SECTION_TO_CATEGORY.get(section_type)
        if not mapping:
            logger.debug("No category mapping for section type: %s", section_type)
            continue

        category, category_group = mapping
        cache_key = f"{category_group}/{category}"
        if cache_key in seen_categories:
            continue
        seen_categories.add(cache_key)

        component = _pick_best_for_category(category, category_group, plan, components_dir)
        if component:
            selected.append(component)
            all_deps.update(component.dependencies)
        else:
            logger.warning(
                "No viable component found for %s/%s — section will be skipped by Composer",
                category_group,
                category,
            )

    return selected, all_deps


def _merge_tailwind_configs(components: list[SelectedComponent]) -> dict:
    """Merge tailwind configs from all selected components."""
    merged: dict = {}
    for comp in components:
        if comp.tailwind_config:
            _deep_merge(merged, comp.tailwind_config)
    return merged


def select_components(plan: dict, components_dir: Path) -> ComponentManifest:
    """Select the best components for each section of the redesign plan.

    Args:
        plan: The RedesignPlan as a dict (from plan.model_dump()).
        components_dir: Path to the components/ directory.

    Returns:
        ComponentManifest with selected components and aggregated dependencies.
    """
    import time as _time

    t0 = _time.monotonic()

    # Clear the tiers cache at the start of each selection run
    _tiers_cache.clear()

    sections = _determine_sections(plan)
    logger.info("Determined %d sections needed: %s", len(sections), sections)

    selected, all_deps = _select_for_sections(sections, plan, components_dir)
    merged_tw = _merge_tailwind_configs(selected)

    manifest = ComponentManifest(
        components=selected,
        all_dependencies=all_deps,
        all_tailwind_extensions=merged_tw,
    )

    duration = _time.monotonic() - t0
    logger.info(
        "PERF | component_selection=%.2fs components=%d dependencies=%d",
        duration,
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
