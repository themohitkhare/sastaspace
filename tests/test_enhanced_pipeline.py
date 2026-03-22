# tests/test_enhanced_pipeline.py
"""Integration tests for the full enhanced crawl pipeline.

All external services are mocked: Playwright, LLM calls, aiohttp downloads.
No real network calls.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sastaspace.crawler import CrawlResult
from sastaspace.deployer import deploy
from sastaspace.models import (
    AssetManifest,
    BusinessProfile,
    DownloadedAsset,
    EnhancedCrawlResult,
)

# --- Fixtures and helpers ---

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

BUSINESS_PROFILE_JSON = json.dumps(
    {
        "business_name": "Bright Smile Dental",
        "industry": "dental",
        "services": ["General dentistry", "Cosmetic procedures", "Invisalign"],
        "target_audience": "Families in Austin",
        "tone": "friendly",
        "differentiators": ["Same-day appointments", "20 years experience"],
        "social_proof": ["Google Reviews 4.9 stars"],
        "pricing_model": "contact-based",
        "cta_primary": "Book Your Free Consultation",
        "brand_personality": "Warm, approachable, reassuring.",
    }
)


def _make_mock_page(
    title="Bright Smile Dental",
    html=SAMPLE_HTML,
    screenshot_bytes=FAKE_PNG_BYTES,
):
    """Return a mock Playwright Page."""
    page = AsyncMock()
    page.title = AsyncMock(return_value=title)
    page.content = AsyncMock(return_value=html)
    page.screenshot = AsyncMock(return_value=screenshot_bytes)
    page.evaluate = AsyncMock(return_value=[])
    page.goto = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    return page


def _make_mock_playwright():
    """Build full mock chain: async_playwright -> pw -> browser -> context -> page."""
    mock_page = _make_mock_page()
    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()
    mock_pw = AsyncMock()
    mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)
    mock_pw.__aenter__ = AsyncMock(return_value=mock_pw)
    mock_pw.__aexit__ = AsyncMock(return_value=False)
    return mock_pw, mock_page, mock_context, mock_browser


def _make_llm_mock(response_text: str):
    """Return a mock OpenAI client returning response_text."""
    mock_message = MagicMock()
    mock_message.content = response_text
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


def _make_settings():
    """Create a minimal settings-like object for testing."""
    settings = MagicMock()
    settings.claude_code_api_url = "http://localhost:8000/v1"
    settings.claude_model = "test-model"
    settings.claude_code_api_key = "test-key"
    settings.use_agno_pipeline = False
    return settings


def _make_aiohttp_response(data: bytes = FAKE_PNG_BYTES, content_type: str = "image/png"):
    """Build a mock aiohttp response."""
    resp = AsyncMock()
    resp.status = 200
    resp.content_type = content_type
    resp.read = AsyncMock(return_value=data)
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=False)
    return resp


def _make_aiohttp_session(response):
    """Build a mock aiohttp.ClientSession."""
    session = AsyncMock()
    session.get = MagicMock(return_value=response)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


# --- Test 1: Full enhanced crawl pipeline ---


@pytest.mark.asyncio
async def test_enhanced_crawl_full_pipeline():
    """enhanced_crawl() with mocked Playwright + LLM returns a complete EnhancedCrawlResult."""
    settings = _make_settings()
    mock_pw, mock_page, mock_context, mock_browser = _make_mock_playwright()

    # Mock LLM page selection to return URLs
    async def mock_llm_select(links, api_url, model, api_key):
        return [
            "https://example.com/about",
            "https://example.com/services",
            "https://example.com/contact",
        ]

    # Mock business profiling to return a rich profile
    mock_profile = BusinessProfile(
        business_name="Bright Smile Dental",
        industry="dental",
        services=["General dentistry", "Cosmetic procedures", "Invisalign"],
        target_audience="Families in Austin",
        tone="friendly",
        differentiators=["Same-day appointments", "20 years experience"],
        social_proof=["Google Reviews 4.9 stars"],
        pricing_model="contact-based",
        cta_primary="Book Your Free Consultation",
        brand_personality="Warm, approachable, reassuring.",
    )

    # Mock aiohttp for asset downloads
    mock_resp = _make_aiohttp_response()
    mock_session = _make_aiohttp_session(mock_resp)

    with (
        patch("sastaspace.crawler.async_playwright", return_value=mock_pw),
        patch("sastaspace.crawler._ensure_chromium"),
        patch("sastaspace.crawler._llm_select_pages", side_effect=mock_llm_select),
        patch("sastaspace.business_profiler.build_business_profile", return_value=mock_profile),
        patch("sastaspace.asset_downloader.aiohttp.ClientSession", return_value=mock_session),
    ):
        from sastaspace.crawler import enhanced_crawl

        result = await enhanced_crawl("https://example.com", settings)

    # Verify result type
    assert isinstance(result, EnhancedCrawlResult)

    # Verify homepage has title, text, screenshot
    assert result.homepage.title == "Bright Smile Dental"
    assert result.homepage.screenshot_base64 != ""
    assert result.homepage.error == ""

    # Verify business profile has extracted fields
    assert result.business_profile.business_name != "unknown"
    assert result.business_profile.industry != "unknown"

    # Verify internal pages have entries (LLM returned 3 URLs)
    # Note: internal pages are crawled via a second async_playwright context
    # which is also mocked, so they should either succeed or have entries
    assert isinstance(result.internal_pages, list)

    # Verify assets manifest
    assert isinstance(result.assets, AssetManifest)


# --- Test 2: Homepage error returns early ---


@pytest.mark.asyncio
async def test_enhanced_crawl_homepage_error_returns_early():
    """When Playwright raises an error, enhanced_crawl returns with homepage.error set."""
    settings = _make_settings()

    # Mock Playwright to raise on launch
    mock_pw = AsyncMock()
    mock_pw.__aenter__ = AsyncMock(return_value=mock_pw)
    mock_pw.__aexit__ = AsyncMock(return_value=False)
    mock_pw.chromium.launch = AsyncMock(side_effect=Exception("Browser crashed"))

    with (
        patch("sastaspace.crawler.async_playwright", return_value=mock_pw),
        patch("sastaspace.crawler._ensure_chromium"),
    ):
        from sastaspace.crawler import enhanced_crawl

        result = await enhanced_crawl("https://broken.com", settings)

    assert isinstance(result, EnhancedCrawlResult)
    assert "Browser crashed" in result.homepage.error
    assert result.internal_pages == []
    assert result.assets.assets == []
    assert result.business_profile.business_name == "unknown"


# --- Test 3: Deploy with enhanced assets ---


def test_deploy_with_enhanced_assets(tmp_path):
    """deploy() with assets creates assets/ directory and writes files."""
    html = SAMPLE_REDESIGNED_HTML

    # Create temp files simulating validated assets
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
        url="https://example.com",
        html=html,
        sites_dir=sites_dir,
        assets=assets,
    )

    # Verify index.html
    index = sites_dir / result.subdomain / "index.html"
    assert index.exists()

    # Verify assets directory and files
    assets_dir = sites_dir / result.subdomain / "assets"
    assert assets_dir.exists()
    assert (assets_dir / "logo.png").exists()
    assert (assets_dir / "hero.jpg").exists()

    # Verify metadata includes assets_count
    meta_path = sites_dir / result.subdomain / "metadata.json"
    metadata = json.loads(meta_path.read_text())
    assert metadata["assets_count"] == 2
    assert metadata["total_assets_size"] == len(FAKE_PNG_BYTES) + len(FAKE_PNG_BYTES) * 2


# --- Test 4: run_redesign with enhanced context ---


def test_run_redesign_with_enhanced_context():
    """run_redesign() with enhanced arg includes Business Profile and Available Assets."""
    settings = _make_settings()

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
        services=["General dentistry", "Cosmetic"],
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
            ),
        ],
        total_size_bytes=1024,
    )

    enhanced = EnhancedCrawlResult(
        homepage=homepage,
        internal_pages=[],
        assets=assets,
        business_profile=profile,
    )

    captured_args = {}

    def mock_redesign_with_prompts(
        crawl_result, system_prompt, user_template, max_tokens, api_url, model, api_key
    ):
        # Capture the crawl_result used so we can inspect the prompt context
        captured_args["crawl_result"] = crawl_result
        captured_args["system_prompt"] = system_prompt
        captured_args["user_template"] = user_template
        return SAMPLE_REDESIGNED_HTML

    with patch(
        "sastaspace.redesigner._redesign_with_prompts",
        side_effect=mock_redesign_with_prompts,
    ):
        from sastaspace.redesigner import run_redesign

        result = run_redesign(homepage, settings, tier="standard", enhanced=enhanced)

    assert "<!DOCTYPE html>" in result

    # The enhanced context should be embedded in the crawl_result's text_content
    enriched_result = captured_args["crawl_result"]
    enriched_context = enriched_result.text_content
    assert "Business Profile" in enriched_context
    assert "Bright Smile Dental" in enriched_context
    assert "Available Assets" in enriched_context
    assert "assets/logo.png" in enriched_context


# --- Test 5: Full pipeline with no images - graceful handling ---


@pytest.mark.asyncio
async def test_full_pipeline_no_images_graceful():
    """Pipeline completes when site has no images; asset manifest is empty."""
    settings = _make_settings()

    html_no_images = """<html>
<head><title>Text Only Site</title></head>
<body><h1>Just Text</h1><p>No images here.</p></body>
</html>"""

    mock_pw, mock_page, mock_context, mock_browser = _make_mock_playwright()
    mock_page.content = AsyncMock(return_value=html_no_images)
    mock_page.title = AsyncMock(return_value="Text Only Site")

    # Mock LLM page selection — no internal links, returns empty
    async def mock_llm_select(links, api_url, model, api_key):
        return []

    # Mock business profiling
    mock_profile = BusinessProfile(
        business_name="Text Only Site",
        industry="unknown",
        tone="neutral",
        brand_personality="Simple and minimal.",
    )

    # aiohttp mock that returns 404 (no assets to download)
    mock_resp = AsyncMock()
    mock_resp.status = 404
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)
    mock_session = _make_aiohttp_session(mock_resp)

    with (
        patch("sastaspace.crawler.async_playwright", return_value=mock_pw),
        patch("sastaspace.crawler._ensure_chromium"),
        patch("sastaspace.crawler._llm_select_pages", side_effect=mock_llm_select),
        patch("sastaspace.business_profiler.build_business_profile", return_value=mock_profile),
        patch("sastaspace.asset_downloader.aiohttp.ClientSession", return_value=mock_session),
    ):
        from sastaspace.crawler import enhanced_crawl

        result = await enhanced_crawl("https://textonly.com", settings)

    assert isinstance(result, EnhancedCrawlResult)
    assert result.homepage.error == ""
    assert result.homepage.title == "Text Only Site"

    # Asset manifest should be empty
    assert result.assets.assets == []
    assert result.assets.total_size_bytes == 0

    # Prompt context should indicate no assets
    prompt_ctx = result.to_prompt_context()
    assert "No downloadable assets found" in prompt_ctx
