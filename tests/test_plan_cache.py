# tests/test_plan_cache.py
"""Tests for plan caching: store, retrieve, merge, and key generation."""

from sastaspace.plan_cache import (
    _CONTENT_KEYS,
    _SKELETON_KEYS,
    _cache_key,
    _extract_skeleton,
    cache_plan,
    get_cached_plan,
    merge_cached_plan,
)

# --- Sample data ---

SAMPLE_PLAN = {
    # Structural keys (cacheable)
    "layout_archetype": "bento",
    "site_type": "saas",
    "design_direction": "Dark editorial with sharp geometric accents",
    "colors": {"primary": "#c8a55a", "background": "#1a1a2e"},
    "typography": {"heading": "Space Grotesk", "body": "Plus Jakarta Sans"},
    "animations": ["blur-fade", "gradient-text"],
    "components": ["hero-bento", "features-grid"],
    # Content keys (never cached)
    "brand": {"name": "Acme Corp", "tagline": "Build better"},
    "content_sections": ["hero", "features", "pricing"],
    "content_map": {"hero_title": "Build Better Products"},
    "headline": "Build Better Products",
    "meta_title": "Acme Corp — Build Better",
}


# --- _cache_key tests ---


class TestCacheKey:
    def test_basic(self):
        assert _cache_key("saas", "bento") == "saas_bento"

    def test_normalizes_case(self):
        assert _cache_key("SaaS", "Bento") == "saas_bento"

    def test_normalizes_spaces(self):
        assert _cache_key("e commerce", "split hero") == "e-commerce_split-hero"

    def test_strips_whitespace(self):
        assert _cache_key("  saas  ", "  bento  ") == "saas_bento"


# --- _extract_skeleton tests ---


class TestExtractSkeleton:
    def test_extracts_structural_keys(self):
        skeleton = _extract_skeleton(SAMPLE_PLAN)
        assert "layout_archetype" in skeleton
        assert "colors" in skeleton
        assert "typography" in skeleton

    def test_excludes_content_keys(self):
        skeleton = _extract_skeleton(SAMPLE_PLAN)
        assert "brand" not in skeleton
        assert "content_sections" not in skeleton
        assert "content_map" not in skeleton
        assert "headline" not in skeleton

    def test_missing_keys_ignored(self):
        skeleton = _extract_skeleton({"layout_archetype": "bento"})
        assert skeleton == {"layout_archetype": "bento"}

    def test_empty_plan(self):
        assert _extract_skeleton({}) == {}


# --- merge_cached_plan tests ---


class TestMergeCachedPlan:
    def test_structural_from_skeleton(self):
        skeleton = {"layout_archetype": "bento", "colors": {"primary": "#000"}}
        live = {"brand": {"name": "Live Corp"}, "layout_archetype": "editorial"}
        merged = merge_cached_plan(skeleton, live)
        # Structural key from skeleton (not overwritten by live)
        assert merged["layout_archetype"] == "bento"

    def test_content_from_live(self):
        skeleton = {"layout_archetype": "bento"}
        live = {
            "brand": {"name": "Live Corp"},
            "content_map": {"hero": "Hello"},
            "headline": "Live Headline",
        }
        merged = merge_cached_plan(skeleton, live)
        assert merged["brand"] == {"name": "Live Corp"}
        assert merged["content_map"] == {"hero": "Hello"}
        assert merged["headline"] == "Live Headline"

    def test_extra_keys_pass_through(self):
        skeleton = {"layout_archetype": "bento"}
        live = {"unknown_key": "some_value"}
        merged = merge_cached_plan(skeleton, live)
        assert merged["unknown_key"] == "some_value"

    def test_content_overwrites_skeleton(self):
        # If somehow skeleton has a content key, live always wins
        skeleton = {"headline": "Old"}
        live = {"headline": "New"}
        merged = merge_cached_plan(skeleton, live)
        assert merged["headline"] == "New"

    def test_empty_inputs(self):
        assert merge_cached_plan({}, {}) == {}


# --- File-based cache tests ---


class TestCachePlanAndRetrieve:
    def test_round_trip(self, tmp_path, monkeypatch):
        monkeypatch.setattr("sastaspace.plan_cache._CACHE_DIR", tmp_path)
        cache_plan("saas", "bento", SAMPLE_PLAN)
        result = get_cached_plan("saas", "bento")
        assert result is not None
        assert result["layout_archetype"] == "bento"
        assert "brand" not in result  # Content stripped

    def test_miss_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr("sastaspace.plan_cache._CACHE_DIR", tmp_path)
        assert get_cached_plan("nonexistent", "type") is None

    def test_corrupted_file_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr("sastaspace.plan_cache._CACHE_DIR", tmp_path)
        cache_file = tmp_path / "saas_bento.json"
        cache_file.write_text("not valid json{{{", encoding="utf-8")
        assert get_cached_plan("saas", "bento") is None

    def test_creates_cache_dir(self, tmp_path, monkeypatch):
        cache_dir = tmp_path / "new_subdir"
        monkeypatch.setattr("sastaspace.plan_cache._CACHE_DIR", cache_dir)
        assert not cache_dir.exists()
        cache_plan("saas", "bento", SAMPLE_PLAN)
        assert cache_dir.exists()

    def test_case_insensitive_retrieval(self, tmp_path, monkeypatch):
        monkeypatch.setattr("sastaspace.plan_cache._CACHE_DIR", tmp_path)
        cache_plan("SaaS", "Bento", SAMPLE_PLAN)
        result = get_cached_plan("saas", "bento")
        assert result is not None


# --- Key separation tests ---


class TestKeySeparation:
    """Ensure skeleton and content key lists don't overlap."""

    def test_no_overlap(self):
        overlap = set(_SKELETON_KEYS) & set(_CONTENT_KEYS)
        assert overlap == set(), f"Keys in both lists: {overlap}"
