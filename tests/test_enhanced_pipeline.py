# tests/test_enhanced_pipeline.py
"""Integration tests for the full enhanced crawl pipeline.

All external services are mocked: Playwright, LLM calls, aiohttp downloads.
No real network calls.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from sastaspace.crawler import CrawlResult
from sastaspace.deployer import deploy
from sastaspace.models import (
    AssetManifest,
    BusinessProfile,
    DownloadedAsset,
    EnhancedCrawlResult,
)
from sastaspace.redesigner import run_redesign

# --- Constants ---

SAMPLE_HTML = """<html>
<head>
    <title>Bright Smile Dental</title>
    <meta name="description" content="Family dentistry in Austin">
    <link rel="icon" href="/favicon.ico">
    <meta property="og:image" content="https://example.com/og.png">
</head>
<body>
    <nav>
        <a href="/">Home</a>
        <a href="/about">About Us</a>
        <a href="/services">Services</a>
        <a href="/contact">Contact</a>
    </nav>
    <h1>Welcome to Bright Smile Dental</h1>
    <section>
        <h2>Our Services</h2>
        <p>General dentistry, cosmetic procedures, and Invisalign.</p>
        <img src="/images/hero.jpg" alt="Office photo">
        <img src="/images/team.jpg" alt="Team photo">
    </section>
</body>
</html>"""

SAMPLE_REDESIGNED_HTML = """<!DOCTYPE html>
<html lang="en">
<head><title>Redesigned</title></head>
<body><h1>Redesigned Site</h1></body>
</html>"""

FAKE_PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50


# --- Test 1: Deploy with enhanced assets ---


def test_deploy_with_enhanced_assets(tmp_path):
    """deploy() with assets creates assets/ directory and writes files."""
    tmp_dir = tmp_path / "tmp_assets"
    tmp_dir.mkdir()
    logo_path = tmp_dir / "logo.png"
    logo_path.write_bytes(FAKE_PNG_BYTES)
    hero_path = tmp_dir / "hero.jpg"
    hero_path.write_bytes(FAKE_PNG_BYTES * 2)

    assets = [
        DownloadedAsset(
            original_url="https://example.com/logo.png",
            local_path="assets/logo.png",
            content_type="image/png",
            size_bytes=len(FAKE_PNG_BYTES),
            file_hash="abc123",
            source_page="https://example.com",
            tmp_path=logo_path,
        ),
        DownloadedAsset(
            original_url="https://example.com/hero.jpg",
            local_path="assets/hero.jpg",
            content_type="image/jpeg",
            size_bytes=len(FAKE_PNG_BYTES) * 2,
            file_hash="def456",
            source_page="https://example.com",
            tmp_path=hero_path,
        ),
    ]

    sites_dir = tmp_path / "sites"
    sites_dir.mkdir()

    result = deploy(
        url="https://example.com", html=SAMPLE_REDESIGNED_HTML, sites_dir=sites_dir, assets=assets
    )

    # Verify index.html
    assert (sites_dir / result.subdomain / "index.html").exists()

    # Verify assets directory and files
    assets_dir = sites_dir / result.subdomain / "assets"
    assert assets_dir.exists()
    assert (assets_dir / "logo.png").exists()
    assert (assets_dir / "hero.jpg").exists()

    # Verify metadata includes assets_count
    metadata = json.loads((sites_dir / result.subdomain / "metadata.json").read_text())
    assert metadata["assets_count"] == 2
    assert metadata["total_assets_size"] == len(FAKE_PNG_BYTES) + len(FAKE_PNG_BYTES) * 2


# --- Test 2: run_redesign with enhanced context ---


def test_run_redesign_with_enhanced_context():
    """run_redesign() with enhanced arg includes Business Profile and Available Assets."""
    settings = MagicMock()
    settings.claude_code_api_url = "http://localhost:8000/v1"
    settings.claude_model = "test-model"
    settings.claude_code_api_key = "test-key"
    settings.use_agno_pipeline = False

    homepage = CrawlResult(
        url="https://example.com",
        title="Example",
        meta_description="A site",
        favicon_url="",
        html_source=SAMPLE_HTML,
        screenshot_base64="c2NyZWVuc2hvdA==",
        headings=["h1: Welcome"],
        navigation_links=[],
        text_content="Welcome to our site",
        images=[],
        colors=[],
        fonts=[],
        sections=[],
        error="",
    )

    profile = BusinessProfile(
        business_name="Bright Smile Dental",
        industry="dental",
        services=["General dentistry"],
        target_audience="Families in Austin",
        tone="friendly",
    )

    assets = AssetManifest(
        assets=[
            DownloadedAsset(
                original_url="https://example.com/logo.png",
                local_path="assets/logo.png",
                content_type="image/png",
                size_bytes=1024,
                file_hash="abc",
                source_page="https://example.com",
            )
        ],
        total_size_bytes=1024,
    )

    enhanced = EnhancedCrawlResult(
        homepage=homepage,
        internal_pages=[],
        assets=assets,
        business_profile=profile,
    )

    # Verify the enhanced prompt context contains expected sections
    ctx = enhanced.to_prompt_context()
    assert "Business Profile" in ctx
    assert "Bright Smile Dental" in ctx
    assert "Available Assets" in ctx
    assert "assets/logo.png" in ctx

    # Verify run_redesign passes enhanced context through
    with patch("sastaspace.redesigner._redesign_with_prompts", return_value=SAMPLE_REDESIGNED_HTML):
        result = run_redesign(homepage, settings, tier="free", enhanced=enhanced)

    assert "<!DOCTYPE html>" in result


# --- Test 3: EnhancedCrawlResult prompt context with no assets ---


def test_enhanced_result_no_assets_prompt():
    """When no assets, prompt context says 'No downloadable assets found'."""
    homepage = CrawlResult(
        url="https://example.com",
        title="Text Only",
        meta_description="",
        favicon_url="",
        html_source="<html></html>",
        screenshot_base64="",
        headings=[],
        navigation_links=[],
        text_content="Just text.",
        images=[],
        colors=[],
        fonts=[],
        sections=[],
        error="",
    )

    enhanced = EnhancedCrawlResult(
        homepage=homepage,
        internal_pages=[],
        assets=AssetManifest(assets=[], total_size_bytes=0),
        business_profile=BusinessProfile.minimal("Text Only"),
    )

    ctx = enhanced.to_prompt_context()
    assert "No downloadable assets found" in ctx
    assert "Available Assets" not in ctx


# --- Test 4: EnhancedCrawlResult with homepage error ---


def test_enhanced_result_homepage_error():
    """EnhancedCrawlResult with homepage error has empty pages/assets/profile."""
    homepage = CrawlResult(
        url="https://broken.com",
        title="",
        meta_description="",
        favicon_url="",
        html_source="",
        screenshot_base64="",
        headings=[],
        navigation_links=[],
        text_content="",
        images=[],
        colors=[],
        fonts=[],
        sections=[],
        error="Connection refused",
    )

    enhanced = EnhancedCrawlResult(homepage=homepage)
    assert enhanced.homepage.error == "Connection refused"
    assert enhanced.internal_pages == []
    assert enhanced.assets.assets == []
    assert enhanced.business_profile.business_name == ""


# --- Test 5: Business profile feeds into prompt context ---


def test_business_profile_in_prompt_context():
    """Business profile fields appear in the enhanced prompt context."""
    homepage = CrawlResult(
        url="https://example.com",
        title="Acme",
        meta_description="",
        favicon_url="",
        html_source="",
        screenshot_base64="",
        headings=[],
        navigation_links=[],
        text_content="Hello",
        images=[],
        colors=[],
        fonts=[],
        sections=[],
        error="",
    )

    profile = BusinessProfile(
        business_name="Acme Corp",
        industry="saas",
        services=["API platform", "Analytics"],
        target_audience="Developers",
        tone="technical",
        differentiators=["99.9% uptime"],
        social_proof=["Trusted by 1000+ companies"],
        cta_primary="Start Free Trial",
        brand_personality="Technical but approachable.",
    )

    enhanced = EnhancedCrawlResult(
        homepage=homepage,
        business_profile=profile,
        assets=AssetManifest(assets=[], total_size_bytes=0),
    )

    ctx = enhanced.to_prompt_context()
    assert "Acme Corp" in ctx
    assert "saas" in ctx
    assert "API platform" in ctx
    assert "Developers" in ctx
    assert "99.9% uptime" in ctx
    assert "Start Free Trial" in ctx
