# tests/test_models_enhanced.py
"""Tests for enhanced crawl pipeline data models."""

from dataclasses import dataclass

from sastaspace.models import (
    AssetManifest,
    BusinessProfile,
    DownloadedAsset,
    EnhancedCrawlResult,
    PageCrawlResult,
)

# --- PageCrawlResult tests ---


def test_page_crawl_result_basic():
    p = PageCrawlResult(
        url="https://acme.com/about",
        page_type="about",
        title="About Us",
        headings=["Our Story"],
        text_content="We are Acme Corp.",
        images=[],
        testimonials=["Great service!"],
    )
    assert p.url == "https://acme.com/about"
    assert p.page_type == "about"
    assert p.title == "About Us"
    assert p.error == ""


def test_page_crawl_result_defaults():
    p = PageCrawlResult(url="https://acme.com")
    assert p.page_type == "other"
    assert p.title == ""
    assert p.headings == []
    assert p.images == []
    assert p.testimonials == []
    assert p.error == ""


def test_page_crawl_result_with_error():
    p = PageCrawlResult(url="https://acme.com/404", error="404 Not Found")
    assert p.error == "404 Not Found"


# --- DownloadedAsset tests ---


def test_downloaded_asset_basic():
    a = DownloadedAsset(
        original_url="https://acme.com/logo.png",
        local_path="assets/logo.png",
        content_type="image/png",
        size_bytes=10240,
        file_hash="abc123",
        source_page="https://acme.com",
    )
    assert a.original_url == "https://acme.com/logo.png"
    assert a.local_path == "assets/logo.png"
    assert a.content_type == "image/png"


# --- AssetManifest tests ---


def test_asset_manifest_empty():
    m = AssetManifest(assets=[])
    assert m.assets == []


def test_asset_manifest_to_prompt_context_empty():
    m = AssetManifest(assets=[])
    ctx = m.to_prompt_context()
    assert ctx == ""


def test_asset_manifest_to_prompt_context_with_assets():
    assets = [
        DownloadedAsset("https://acme.com/hero.jpg", "assets/hero.jpg", "image/jpeg", 50000),
        DownloadedAsset("https://acme.com/logo.png", "assets/logo.png", "image/png", 5000),
    ]
    m = AssetManifest(assets=assets, total_size_bytes=55000)
    ctx = m.to_prompt_context()
    assert "logo.png" in ctx
    assert "hero.jpg" in ctx
    assert "Available Assets" in ctx


def test_asset_manifest_prioritizes_logo_and_favicon():
    """Logo and favicon should appear before other assets regardless of size."""
    assets = [
        DownloadedAsset("https://acme.com/huge-bg.jpg", "assets/huge-bg.jpg", "image/jpeg", 500000),
        DownloadedAsset("https://acme.com/logo.svg", "assets/logo.svg", "image/svg+xml", 2000),
        DownloadedAsset("https://acme.com/fav.ico", "assets/favicon.ico", "image/x-icon", 500),
    ]
    m = AssetManifest(assets=assets, total_size_bytes=502500)
    ctx = m.to_prompt_context()
    logo_pos = ctx.index("logo.svg")
    favicon_pos = ctx.index("favicon.ico")
    bg_pos = ctx.index("huge-bg.jpg")
    assert logo_pos < bg_pos
    assert favicon_pos < bg_pos


def test_asset_manifest_truncates_to_max_assets():
    assets = [
        DownloadedAsset(
            f"https://acme.com/img{i}.jpg", f"assets/img{i}.jpg", "image/jpeg", 1000 * (20 - i)
        )
        for i in range(20)
    ]
    m = AssetManifest(assets=assets, total_size_bytes=sum(a.size_bytes for a in assets))
    ctx = m.to_prompt_context(max_assets=5)
    count = sum(1 for i in range(20) if f"img{i}.jpg" in ctx)
    assert count == 5


# --- BusinessProfile tests ---


def test_business_profile_basic():
    bp = BusinessProfile(
        business_name="Acme Corp",
        industry="Technology",
        services=["Consulting", "Development"],
        target_audience="Developers",
        tone="professional",
        differentiators=["Fast delivery"],
        social_proof=["500+ clients"],
        pricing_model="contact-based",
        cta_primary="Get a Quote",
        brand_personality="Reliable and efficient.",
    )
    assert bp.business_name == "Acme Corp"
    assert bp.services == ["Consulting", "Development"]


def test_business_profile_minimal_classmethod():
    bp = BusinessProfile.minimal("Acme Corp")
    assert bp.business_name == "Acme Corp"
    assert bp.industry == "unknown"
    assert bp.services == []
    assert bp.target_audience == "unknown"
    assert bp.tone == "unknown"


def test_business_profile_to_prompt_context():
    bp = BusinessProfile(
        business_name="Acme Corp",
        industry="Technology",
        services=["Consulting"],
        target_audience="Developers",
        tone="professional",
        brand_personality="Reliable.",
        cta_primary="Get Started",
    )
    ctx = bp.to_prompt_context()
    assert "Acme Corp" in ctx
    assert "Technology" in ctx
    assert "Consulting" in ctx
    assert "Get Started" in ctx


def test_business_profile_minimal_to_prompt_context():
    bp = BusinessProfile.minimal("Acme Corp")
    ctx = bp.to_prompt_context()
    assert "Acme Corp" in ctx
    assert "unknown" in ctx


# --- EnhancedCrawlResult tests ---


def _make_fake_homepage():
    @dataclass
    class FakeHomepage:
        def to_prompt_context(self) -> str:
            return "Homepage content here"

    return FakeHomepage()


def test_enhanced_crawl_result_basic():
    homepage = _make_fake_homepage()
    ecr = EnhancedCrawlResult(
        homepage=homepage,
        internal_pages=[],
        assets=AssetManifest(assets=[]),
        business_profile=BusinessProfile.minimal("Acme Corp"),
    )
    assert ecr.homepage is homepage
    assert ecr.internal_pages == []
    assert ecr.business_profile.business_name == "Acme Corp"


def test_enhanced_crawl_result_to_prompt_context_no_assets():
    homepage = _make_fake_homepage()
    ecr = EnhancedCrawlResult(
        homepage=homepage,
        internal_pages=[],
        assets=AssetManifest(assets=[]),
        business_profile=BusinessProfile.minimal("Acme Corp"),
    )
    ctx = ecr.to_prompt_context()
    assert "No downloadable assets found" in ctx
    assert "Acme Corp" in ctx
    assert "Homepage content here" in ctx


def test_enhanced_crawl_result_to_prompt_context_with_assets():
    homepage = _make_fake_homepage()
    assets = [
        DownloadedAsset("https://acme.com/logo.png", "assets/logo.png", "image/png", 5000),
    ]
    ecr = EnhancedCrawlResult(
        homepage=homepage,
        internal_pages=[],
        assets=AssetManifest(assets=assets, total_size_bytes=5000),
        business_profile=BusinessProfile.minimal("Acme Corp"),
    )
    ctx = ecr.to_prompt_context()
    assert "logo.png" in ctx
    assert "No downloadable assets found" not in ctx


def test_enhanced_crawl_result_to_prompt_context_with_internal_pages():
    homepage = _make_fake_homepage()
    pages = [
        PageCrawlResult(
            url="https://acme.com/about",
            page_type="about",
            title="About",
            headings=["Our Story"],
            text_content="About Acme.",
        ),
    ]
    ecr = EnhancedCrawlResult(
        homepage=homepage,
        internal_pages=pages,
        assets=AssetManifest(assets=[]),
        business_profile=BusinessProfile.minimal("Acme Corp"),
    )
    ctx = ecr.to_prompt_context()
    assert "About" in ctx
    assert "Our Story" in ctx
    assert "About Acme." in ctx
