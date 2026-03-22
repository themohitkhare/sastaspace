# tests/test_models_enhanced.py
"""Tests for enhanced crawl pipeline data models."""

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
        title="About Us",
        headings=["h1: About"],
        text_content="We are Acme Corp.",
        navigation_links=[],
    )
    assert p.url == "https://acme.com/about"
    assert p.title == "About Us"
    assert p.headings == ["h1: About"]
    assert p.text_content == "We are Acme Corp."
    assert p.error == ""


def test_page_crawl_result_defaults():
    p = PageCrawlResult(url="https://acme.com", title="Acme")
    assert p.headings == []
    assert p.text_content == ""
    assert p.navigation_links == []
    assert p.error == ""


def test_page_crawl_result_with_error():
    p = PageCrawlResult(url="https://acme.com/404", title="", error="404 Not Found")
    assert p.error == "404 Not Found"


def test_page_crawl_result_to_prompt_context():
    p = PageCrawlResult(
        url="https://acme.com/about",
        title="About Us",
        headings=["h1: About", "h2: Team"],
        text_content="We are Acme Corp. Founded in 2020.",
        navigation_links=[{"text": "Home", "href": "/"}],
    )
    ctx = p.to_prompt_context()
    assert "About Us" in ctx
    assert "https://acme.com/about" in ctx
    assert "h1: About" in ctx
    assert "h2: Team" in ctx
    assert "We are Acme Corp." in ctx
    assert "Home" in ctx


def test_page_crawl_result_to_prompt_context_truncates_text():
    long_text = "x" * 6000
    p = PageCrawlResult(
        url="https://acme.com",
        title="Acme",
        text_content=long_text,
    )
    ctx = p.to_prompt_context()
    # text_content should be truncated (not all 6000 chars)
    assert len(ctx) < 6000


# --- DownloadedAsset tests ---


def test_downloaded_asset_basic():
    a = DownloadedAsset(
        original_url="https://acme.com/logo.png",
        local_path="/tmp/assets/logo.png",
        asset_type="image",
        size_bytes=10240,
    )
    assert a.original_url == "https://acme.com/logo.png"
    assert a.local_path == "/tmp/assets/logo.png"
    assert a.asset_type == "image"
    assert a.size_bytes == 10240
    assert a.is_logo is False
    assert a.is_favicon is False


def test_downloaded_asset_logo_favicon():
    a = DownloadedAsset(
        original_url="https://acme.com/favicon.ico",
        local_path="/tmp/assets/favicon.ico",
        asset_type="image",
        size_bytes=1024,
        is_logo=False,
        is_favicon=True,
    )
    assert a.is_favicon is True
    assert a.is_logo is False


# --- AssetManifest tests ---


def test_asset_manifest_empty():
    m = AssetManifest(assets=[])
    assert m.assets == []


def test_asset_manifest_to_prompt_context_empty():
    m = AssetManifest(assets=[])
    ctx = m.to_prompt_context()
    assert "No downloadable assets found" in ctx


def test_asset_manifest_to_prompt_context_with_assets():
    assets = [
        DownloadedAsset(
            original_url="https://acme.com/hero.jpg",
            local_path="/tmp/hero.jpg",
            asset_type="image",
            size_bytes=50000,
        ),
        DownloadedAsset(
            original_url="https://acme.com/logo.png",
            local_path="/tmp/logo.png",
            asset_type="image",
            size_bytes=5000,
            is_logo=True,
        ),
    ]
    m = AssetManifest(assets=assets)
    ctx = m.to_prompt_context()
    assert "logo.png" in ctx
    assert "hero.jpg" in ctx


def test_asset_manifest_prioritizes_logo_and_favicon():
    """Logo and favicon should appear before other assets regardless of size."""
    assets = [
        DownloadedAsset(
            original_url="https://acme.com/huge-bg.jpg",
            local_path="/tmp/huge-bg.jpg",
            asset_type="image",
            size_bytes=500000,
        ),
        DownloadedAsset(
            original_url="https://acme.com/logo.svg",
            local_path="/tmp/logo.svg",
            asset_type="image",
            size_bytes=2000,
            is_logo=True,
        ),
        DownloadedAsset(
            original_url="https://acme.com/favicon.ico",
            local_path="/tmp/favicon.ico",
            asset_type="image",
            size_bytes=500,
            is_favicon=True,
        ),
    ]
    m = AssetManifest(assets=assets)
    ctx = m.to_prompt_context()
    # Logo and favicon should come before huge-bg in the output
    logo_pos = ctx.index("logo.svg")
    favicon_pos = ctx.index("favicon.ico")
    bg_pos = ctx.index("huge-bg.jpg")
    assert logo_pos < bg_pos
    assert favicon_pos < bg_pos


def test_asset_manifest_truncates_to_max_assets():
    """to_prompt_context(max_assets=N) should limit the number of assets shown."""
    assets = [
        DownloadedAsset(
            original_url=f"https://acme.com/img{i}.jpg",
            local_path=f"/tmp/img{i}.jpg",
            asset_type="image",
            size_bytes=1000 * (20 - i),
        )
        for i in range(20)
    ]
    m = AssetManifest(assets=assets)
    ctx = m.to_prompt_context(max_assets=5)
    # Should only include 5 assets
    count = sum(1 for i in range(20) if f"img{i}.jpg" in ctx)
    assert count == 5


# --- BusinessProfile tests ---


def test_business_profile_basic():
    bp = BusinessProfile(
        business_name="Acme Corp",
        industry="Technology",
        description="A tech company.",
        target_audience="Developers",
        brand_voice="Professional",
        primary_colors=["#000", "#fff"],
        contact_email="hello@acme.com",
        phone="555-1234",
        address="123 Main St",
    )
    assert bp.business_name == "Acme Corp"
    assert bp.industry == "Technology"
    assert bp.primary_colors == ["#000", "#fff"]


def test_business_profile_minimal_classmethod():
    bp = BusinessProfile.minimal("Acme Corp")
    assert bp.business_name == "Acme Corp"
    assert bp.industry == "unknown"
    assert bp.description == "unknown"
    assert bp.target_audience == "unknown"
    assert bp.brand_voice == "unknown"
    assert bp.primary_colors == []
    assert bp.contact_email == "unknown"
    assert bp.phone == "unknown"
    assert bp.address == "unknown"


def test_business_profile_to_prompt_context():
    bp = BusinessProfile(
        business_name="Acme Corp",
        industry="Technology",
        description="A tech company.",
        target_audience="Developers",
        brand_voice="Professional",
        primary_colors=["#000", "#fff"],
        contact_email="hello@acme.com",
        phone="555-1234",
        address="123 Main St",
    )
    ctx = bp.to_prompt_context()
    assert "Acme Corp" in ctx
    assert "Technology" in ctx
    assert "A tech company." in ctx
    assert "Developers" in ctx
    assert "Professional" in ctx
    assert "#000" in ctx
    assert "hello@acme.com" in ctx


def test_business_profile_minimal_to_prompt_context():
    bp = BusinessProfile.minimal("Acme Corp")
    ctx = bp.to_prompt_context()
    assert "Acme Corp" in ctx
    assert "unknown" in ctx


# --- EnhancedCrawlResult tests ---


def _make_fake_homepage():
    """Create a mock homepage object with to_prompt_context()."""
    from dataclasses import dataclass

    @dataclass
    class FakeHomepage:
        def to_prompt_context(self) -> str:
            return "## Page Title\nAcme Home\n\n## URL\nhttps://acme.com"

    return FakeHomepage()


def test_enhanced_crawl_result_basic():
    homepage = _make_fake_homepage()
    ecr = EnhancedCrawlResult(
        homepage=homepage,
        internal_pages=[],
        asset_manifest=AssetManifest(assets=[]),
        business_profile=BusinessProfile.minimal("Acme Corp"),
    )
    assert ecr.homepage is homepage
    assert ecr.internal_pages == []
    assert ecr.asset_manifest.assets == []
    assert ecr.business_profile.business_name == "Acme Corp"


def test_enhanced_crawl_result_to_prompt_context_no_assets():
    homepage = _make_fake_homepage()
    ecr = EnhancedCrawlResult(
        homepage=homepage,
        internal_pages=[],
        asset_manifest=AssetManifest(assets=[]),
        business_profile=BusinessProfile.minimal("Acme Corp"),
    )
    ctx = ecr.to_prompt_context()
    assert "No downloadable assets found" in ctx
    assert "Acme Corp" in ctx
    assert "Acme Home" in ctx


def test_enhanced_crawl_result_to_prompt_context_with_assets():
    homepage = _make_fake_homepage()
    assets = [
        DownloadedAsset(
            original_url="https://acme.com/logo.png",
            local_path="/tmp/logo.png",
            asset_type="image",
            size_bytes=5000,
            is_logo=True,
        ),
    ]
    ecr = EnhancedCrawlResult(
        homepage=homepage,
        internal_pages=[],
        asset_manifest=AssetManifest(assets=assets),
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
            title="About",
            headings=["h1: About Us"],
            text_content="About Acme.",
        ),
        PageCrawlResult(
            url="https://acme.com/contact",
            title="Contact",
            headings=["h1: Contact Us"],
            text_content="Reach us here.",
        ),
    ]
    ecr = EnhancedCrawlResult(
        homepage=homepage,
        internal_pages=pages,
        asset_manifest=AssetManifest(assets=[]),
        business_profile=BusinessProfile.minimal("Acme Corp"),
    )
    ctx = ecr.to_prompt_context()
    assert "About" in ctx
    assert "Contact" in ctx
    assert "About Acme." in ctx
