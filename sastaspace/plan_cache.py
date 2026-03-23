# sastaspace/plan_cache.py
"""Cache Planner outputs by site_type + layout_archetype for faster redesigns."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_CACHE_DIR = Path(__file__).parent.parent / "plan_cache"

# Structural keys worth caching — these are layout/design decisions, not content.
_SKELETON_KEYS = (
    "layout_archetype",
    "site_type",
    "design_direction",
    "design_tokens",
    "typography",
    "colors",
    "animations",
    "components",
    "conversion_strategy",
    "responsive_approach",
    "anti_patterns",
)

# Content keys that must ALWAYS come from the live crawl, never cached.
_CONTENT_KEYS = (
    "brand",
    "primary_goal",
    "target_audience",
    "visual_identity",
    "content_sections",
    "content_absent",
    "key_content",
    "headline",
    "subheadline",
    "cta_primary",
    "cta_secondary",
    "content_map",
    "content_warnings",
    "meta_title",
    "meta_description",
)


def _cache_key(site_type: str, archetype: str) -> str:
    """Generate cache key from site type and archetype."""
    # Normalise to lowercase, strip whitespace, replace spaces with hyphens
    st = site_type.strip().lower().replace(" ", "-")
    ar = archetype.strip().lower().replace(" ", "-")
    return f"{st}_{ar}"


def get_cached_plan(site_type: str, archetype: str) -> dict | None:
    """Retrieve a cached plan skeleton if available.

    Returns the structural skeleton dict, or None on miss / parse error.
    """
    key = _cache_key(site_type, archetype)
    cache_file = _CACHE_DIR / f"{key}.json"
    if cache_file.exists():
        try:
            plan = json.loads(cache_file.read_text(encoding="utf-8"))
            logger.info("PERF | plan_cache=HIT site_type=%s archetype=%s", site_type, archetype)
            return plan
        except (json.JSONDecodeError, OSError):
            return None
    return None


def cache_plan(site_type: str, archetype: str, plan: dict) -> None:
    """Cache a successful plan for future reuse.

    Only stores structural/design fields — content is stripped.
    """
    _CACHE_DIR.mkdir(exist_ok=True)
    key = _cache_key(site_type, archetype)
    cache_file = _CACHE_DIR / f"{key}.json"
    try:
        skeleton = _extract_skeleton(plan)
        cache_file.write_text(json.dumps(skeleton, indent=2), encoding="utf-8")
        logger.info("PERF | plan_cache=STORE site_type=%s archetype=%s", site_type, archetype)
    except OSError as e:
        logger.warning("Failed to cache plan: %s", e)


def merge_cached_plan(skeleton: dict, live_plan: dict) -> dict:
    """Merge a cached skeleton with content from a live Planner run.

    Structural keys come from the skeleton; content keys come from live_plan.
    Any key present in live_plan but not in either allow-list passes through.
    """
    merged = dict(skeleton)
    # Content ALWAYS comes from the live crawl
    for key in _CONTENT_KEYS:
        if key in live_plan:
            merged[key] = live_plan[key]
    # Pass through any extra keys from live_plan that we don't categorise
    for key in live_plan:
        if key not in merged:
            merged[key] = live_plan[key]
    return merged


def _extract_skeleton(plan: dict) -> dict:
    """Extract reusable structural elements, strip site-specific content."""
    skeleton = {}
    for key in _SKELETON_KEYS:
        if key in plan:
            skeleton[key] = plan[key]
    return skeleton
