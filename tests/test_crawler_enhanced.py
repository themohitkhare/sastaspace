# tests/test_crawler_enhanced.py
"""Tests for enhanced crawl pipeline: link extraction, filtering, internal page crawl,
LLM page selection, and enhanced_crawl() orchestration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sastaspace.asset_downloader import AssetManifest
from sastaspace.crawler import (
    CrawlResult,
    _crawl_internal_page,
    _crawl_page,
    _extract_all_internal_links,
    _filter_noise_links,
    _llm_select_pages,
    crawl,
    enhanced_crawl,
)
from sastaspace.models import BusinessProfile, EnhancedCrawlResult, PageCrawlResult

# --- Helper ---


def make_mock_page(
    title="Test Site",
    html="<html><body><h1>Hello</h1></body></html>",
    screenshot_bytes=b"\x89PNG\r\n",
    final_url="https://example.com",
):
    page = AsyncMock()
    page.title = AsyncMock(return_value=title)
    page.content = AsyncMock(return_value=html)
    page.screenshot = AsyncMock(return_value=screenshot_bytes)
    page.evaluate = AsyncMock(return_value=[])
    page.goto = AsyncMock()
    page.url = final_url
    page.close = AsyncMock()
    return page


# --- _extract_all_internal_links tests ---


class TestExtractAllInternalLinks:
    def test_extracts_internal_links(self):
        html = """
        <html><body>
            <a href="/about">About</a>
            <a href="/services">Services</a>
            <a href="https://example.com/contact">Contact</a>
        </body></html>
        """
        links = _extract_all_internal_links(html, "https://example.com")
        urls = [link["url"] for link in links]
        assert "https://example.com/about" in urls
        assert "https://example.com/services" in urls
        assert "https://example.com/contact" in urls

    def test_skips_external_links(self):
        html = """
        <html><body>
            <a href="https://other.com/page">External</a>
            <a href="/local">Local</a>
        </body></html>
        """
        links = _extract_all_internal_links(html, "https://example.com")
        urls = [link["url"] for link in links]
        assert len(links) == 1
        assert "https://example.com/local" in urls

    def test_skips_javascript_mailto_tel(self):
        html = """
        <html><body>
            <a href="javascript:void(0)">JS</a>
            <a href="mailto:test@test.com">Email</a>
            <a href="tel:+1234567890">Phone</a>
            <a href="/real">Real</a>
        </body></html>
        """
        links = _extract_all_internal_links(html, "https://example.com")
        assert len(links) == 1
        assert links[0]["url"] == "https://example.com/real"

    def test_skips_fragment_only(self):
        html = """
        <html><body>
            <a href="#section">Section</a>
            <a href="/page#section">Page with fragment</a>
        </body></html>
        """
        links = _extract_all_internal_links(html, "https://example.com")
        # Fragment-only skipped; page with fragment kept (fragment stripped)
        assert len(links) == 1
        assert links[0]["url"] == "https://example.com/page"

    def test_skips_base_url(self):
        html = """
        <html><body>
            <a href="https://example.com">Home</a>
            <a href="https://example.com/">Home2</a>
            <a href="/">Root</a>
            <a href="/about">About</a>
        </body></html>
        """
        links = _extract_all_internal_links(html, "https://example.com")
        # Only /about should remain — home links are the base URL
        urls = [link["url"] for link in links]
        assert "https://example.com/about" in urls

    def test_deduplicates(self):
        html = """
        <html><body>
            <a href="/about">About</a>
            <a href="/about">About Again</a>
            <a href="/about#team">About Team</a>
        </body></html>
        """
        links = _extract_all_internal_links(html, "https://example.com")
        # All three resolve to the same URL after fragment strip
        assert len(links) == 1

    def test_caps_at_50(self):
        anchors = "".join(f'<a href="/page-{i}">Page {i}</a>' for i in range(100))
        html = f"<html><body>{anchors}</body></html>"
        links = _extract_all_internal_links(html, "https://example.com")
        assert len(links) == 50

    def test_captures_link_text(self):
        html = '<html><body><a href="/about">About Us</a></body></html>'
        links = _extract_all_internal_links(html, "https://example.com")
        assert links[0]["text"] == "About Us"

    def test_resolves_relative_urls(self):
        html = '<html><body><a href="blog/post-1">Post 1</a></body></html>'
        links = _extract_all_internal_links(html, "https://example.com/news/")
        assert links[0]["url"] == "https://example.com/news/blog/post-1"


# --- _filter_noise_links tests ---


class TestFilterNoiseLinks:
    def test_keeps_clean_links(self):
        links = [
            {"url": "https://example.com/about", "text": "About"},
            {"url": "https://example.com/services", "text": "Services"},
        ]
        result = _filter_noise_links(links, "https://example.com")
        assert len(result) == 2

    def test_filters_download_extensions(self):
        links = [
            {"url": "https://example.com/doc.pdf", "text": "Download PDF"},
            {"url": "https://example.com/file.zip", "text": "Download ZIP"},
            {"url": "https://example.com/report.docx", "text": "Report"},
            {"url": "https://example.com/about", "text": "About"},
        ]
        result = _filter_noise_links(links, "https://example.com")
        assert len(result) == 1
        assert result[0]["url"] == "https://example.com/about"

    def test_filters_auth_utility_paths(self):
        links = [
            {"url": "https://example.com/login", "text": "Login"},
            {"url": "https://example.com/cart", "text": "Cart"},
            {"url": "https://example.com/search", "text": "Search"},
            {"url": "https://example.com/wp-admin", "text": "Admin"},
            {"url": "https://example.com/about", "text": "About"},
        ]
        result = _filter_noise_links(links, "https://example.com")
        assert len(result) == 1
        assert result[0]["url"] == "https://example.com/about"

    def test_filters_pagination(self):
        links = [
            {"url": "https://example.com/blog/page/2", "text": "Page 2"},
            {"url": "https://example.com/blog/page/3", "text": "Page 3"},
            {"url": "https://example.com/blog", "text": "Blog"},
        ]
        result = _filter_noise_links(links, "https://example.com")
        assert len(result) == 1
        assert result[0]["url"] == "https://example.com/blog"

    def test_filters_long_query_strings(self):
        long_query = "a" * 300
        links = [
            {"url": f"https://example.com/page?{long_query}", "text": "Tracked"},
            {"url": "https://example.com/about?ref=home", "text": "About"},
        ]
        result = _filter_noise_links(links, "https://example.com")
        assert len(result) == 1
        assert result[0]["text"] == "About"

    def test_filters_nested_auth_paths(self):
        links = [
            {"url": "https://example.com/user/login", "text": "Login"},
            {"url": "https://example.com/members/signup", "text": "Sign Up"},
            {"url": "https://example.com/about", "text": "About"},
        ]
        result = _filter_noise_links(links, "https://example.com")
        assert len(result) == 1


# --- _crawl_page (refactored) tests ---


class TestCrawlPage:
    @pytest.mark.asyncio
    async def test_crawl_page_returns_crawl_result(self):
        html = (
            "<html><head>"
            '<meta name="description" content="Test desc">'
            '<link rel="icon" href="/favicon.ico">'
            "</head><body><h1>Hello</h1></body></html>"
        )
        page = make_mock_page(title="Test", html=html)

        result = await _crawl_page(page, "https://example.com")

        assert isinstance(result, CrawlResult)
        assert result.title == "Test"
        assert result.meta_description == "Test desc"
        assert result.favicon_url == "/favicon.ico"
        assert result.error == ""
        assert result.screenshot_base64 != ""

    @pytest.mark.asyncio
    async def test_crawl_still_works_after_refactor(self):
        """crawl() public API unchanged — still returns CrawlResult."""
        mock_page = make_mock_page()

        with patch("sastaspace.crawler.async_playwright") as mock_pw:
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_pw.return_value.__aenter__ = AsyncMock(return_value=mock_pw.return_value)
            mock_pw.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_pw.return_value.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_browser.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)
            mock_browser.close = AsyncMock()

            result = await crawl("https://example.com")

        assert isinstance(result, CrawlResult)
        assert result.error == ""


# --- _crawl_internal_page tests ---


class TestCrawlInternalPage:
    @pytest.mark.asyncio
    async def test_extracts_title_headings_text(self):
        html = """
        <html><body>
            <h1>About Us</h1>
            <h2>Our Mission</h2>
            <p>We are a great company that does amazing things for our customers.
            We have been in business for 20 years and have served thousands of clients.
            Our mission is to deliver excellence in everything we do. We pride ourselves
            on our dedication to quality and customer satisfaction. Our team of experts
            works tirelessly to ensure the best outcomes for every project. We believe
            in transparency, integrity, and innovation. Join us on our journey to
            make the world a better place through technology and service.</p>
        </body></html>
        """
        page = make_mock_page(
            title="About - Example", html=html, final_url="https://example.com/about"
        )
        result = await _crawl_internal_page(page, "https://example.com/about")

        assert isinstance(result, PageCrawlResult)
        assert result.title == "About - Example"
        assert result.error == ""
        assert any("About Us" in h for h in result.headings)
        assert any("Our Mission" in h for h in result.headings)
        assert "great company" in result.text_content

    @pytest.mark.asyncio
    async def test_detects_auth_redirect(self):
        page = make_mock_page(final_url="https://example.com/login?redirect=/about")
        result = await _crawl_internal_page(page, "https://example.com/about")
        assert "Auth redirect" in result.error

    @pytest.mark.asyncio
    async def test_detects_bot_protection(self):
        # Very short content suggests a challenge page
        html = "<html><body><p>Checking your browser...</p></body></html>"
        page = make_mock_page(html=html, final_url="https://example.com/about")
        result = await _crawl_internal_page(page, "https://example.com/about")
        assert "Bot protection" in result.error

    @pytest.mark.asyncio
    async def test_extracts_testimonials_from_blockquote(self):
        filler = "We are dedicated to providing the best service possible. " * 20
        html = f"""
        <html><body>
            <h1>Testimonials</h1>
            <p>{filler}</p>
            <blockquote>Great service, would recommend to anyone!</blockquote>
            <blockquote>Best experience I've ever had with a company.</blockquote>
        </body></html>
        """
        page = make_mock_page(html=html, final_url="https://example.com/testimonials")
        result = await _crawl_internal_page(page, "https://example.com/testimonials")
        assert len(result.testimonials) >= 2
        assert "Great service" in result.testimonials[0]

    @pytest.mark.asyncio
    async def test_extracts_testimonials_from_class(self):
        filler = "Our customers love working with us and always come back. " * 20
        html = f"""
        <html><body>
            <h1>Reviews</h1>
            <p>{filler}</p>
            <div class="testimonial-card">Amazing work on my website!</div>
            <div class="review-item">Five stars, absolutely stunning results.</div>
        </body></html>
        """
        page = make_mock_page(html=html, final_url="https://example.com/reviews")
        result = await _crawl_internal_page(page, "https://example.com/reviews")
        assert any("Amazing work" in t for t in result.testimonials)
        assert any("Five stars" in t for t in result.testimonials)

    @pytest.mark.asyncio
    async def test_extracts_images(self):
        filler = "Welcome to our gallery of amazing design work and projects. " * 20
        html = f"""
        <html><body>
            <h1>Gallery</h1>
            <p>{filler}</p>
            <img src="/img/photo1.jpg" alt="Photo 1">
            <img src="/img/photo2.jpg" alt="Photo 2">
        </body></html>
        """
        page = make_mock_page(html=html, final_url="https://example.com/gallery")
        result = await _crawl_internal_page(page, "https://example.com/gallery")
        assert len(result.images) == 2
        assert result.images[0]["src"] == "/img/photo1.jpg"

    @pytest.mark.asyncio
    async def test_handles_exception(self):
        page = AsyncMock()
        page.goto = AsyncMock(side_effect=OSError("Connection refused"))
        page.url = "https://example.com/broken"
        result = await _crawl_internal_page(page, "https://example.com/broken")
        assert "Connection refused" in result.error

    @pytest.mark.asyncio
    async def test_limits_headings_to_15(self):
        headings_html = "".join(f"<h2>Heading {i}</h2>" for i in range(25))
        # Need enough text content to pass bot protection check
        text_content = "<p>" + ("Lorem ipsum dolor sit amet. " * 50) + "</p>"
        html = f"<html><body>{headings_html}{text_content}</body></html>"
        page = make_mock_page(html=html, final_url="https://example.com/many-headings")
        result = await _crawl_internal_page(page, "https://example.com/many-headings")
        assert len(result.headings) <= 15

    @pytest.mark.asyncio
    async def test_text_capped_at_3000(self):
        long_text = "<p>" + ("x " * 5000) + "</p>"
        html = f"<html><body><h1>Test</h1>{long_text}</body></html>"
        page = make_mock_page(html=html, final_url="https://example.com/long")
        result = await _crawl_internal_page(page, "https://example.com/long")
        assert len(result.text_content) <= 3000


# --- _llm_select_pages tests ---


class TestLlmSelectPages:
    def test_returns_all_when_3_or_fewer(self):
        links = [
            {"url": "https://example.com/about", "text": "About"},
            {"url": "https://example.com/services", "text": "Services"},
        ]
        result = _llm_select_pages(links, "http://localhost:8000/v1", "test-model", "test-key")
        assert result == ["https://example.com/about", "https://example.com/services"]

    def test_returns_all_three_when_exactly_3(self):
        links = [
            {"url": "https://example.com/about", "text": "About"},
            {"url": "https://example.com/services", "text": "Services"},
            {"url": "https://example.com/contact", "text": "Contact"},
        ]
        result = _llm_select_pages(links, "http://localhost:8000/v1", "test-model", "test-key")
        assert len(result) == 3

    @patch("sastaspace.crawler.OpenAI")
    def test_calls_llm_for_more_than_3(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            '["https://example.com/about", "https://example.com/services", '
            '"https://example.com/portfolio"]'
        )
        mock_client.chat.completions.create.return_value = mock_response

        links = [
            {"url": "https://example.com/about", "text": "About"},
            {"url": "https://example.com/services", "text": "Services"},
            {"url": "https://example.com/portfolio", "text": "Portfolio"},
            {"url": "https://example.com/blog", "text": "Blog"},
            {"url": "https://example.com/contact", "text": "Contact"},
        ]

        result = _llm_select_pages(links, "http://localhost:8000/v1", "test-model", "test-key")

        assert len(result) == 3
        assert "https://example.com/about" in result
        mock_client.chat.completions.create.assert_called_once()

    @patch("sastaspace.crawler.OpenAI")
    def test_fallback_on_llm_error(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = ValueError("API error")

        links = [
            {"url": "https://example.com/about", "text": "About"},
            {"url": "https://example.com/services", "text": "Services"},
            {"url": "https://example.com/portfolio", "text": "Portfolio"},
            {"url": "https://example.com/blog", "text": "Blog"},
        ]

        result = _llm_select_pages(links, "http://localhost:8000/v1", "test-model", "test-key")

        # Should fallback to first 3
        assert len(result) == 3
        assert result[0] == "https://example.com/about"

    @patch("sastaspace.crawler.OpenAI")
    def test_fallback_on_invalid_json(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "I think you should crawl about and services"
        mock_client.chat.completions.create.return_value = mock_response

        links = [
            {"url": "https://example.com/about", "text": "About"},
            {"url": "https://example.com/services", "text": "Services"},
            {"url": "https://example.com/portfolio", "text": "Portfolio"},
            {"url": "https://example.com/blog", "text": "Blog"},
        ]

        result = _llm_select_pages(links, "http://localhost:8000/v1", "test-model", "test-key")

        # Fallback to first 3
        assert len(result) == 3

    @patch("sastaspace.crawler.OpenAI")
    def test_validates_returned_urls_against_input(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        # LLM returns URLs not in the original list
        mock_response.choices[0].message.content = (
            '["https://example.com/about", "https://example.com/fake", '
            '"https://example.com/services"]'
        )
        mock_client.chat.completions.create.return_value = mock_response

        links = [
            {"url": "https://example.com/about", "text": "About"},
            {"url": "https://example.com/services", "text": "Services"},
            {"url": "https://example.com/portfolio", "text": "Portfolio"},
            {"url": "https://example.com/blog", "text": "Blog"},
        ]

        result = _llm_select_pages(links, "http://localhost:8000/v1", "test-model", "test-key")

        # Only valid URLs returned, "fake" excluded
        assert "https://example.com/fake" not in result
        assert "https://example.com/about" in result
        assert "https://example.com/services" in result


# --- enhanced_crawl tests ---


class TestEnhancedCrawl:
    @pytest.mark.asyncio
    async def test_returns_enhanced_crawl_result(self):
        """enhanced_crawl returns an EnhancedCrawlResult with homepage."""
        homepage_html = """
        <html><head><meta name="description" content="Test"></head>
        <body>
            <h1>Example Corp</h1>
            <nav><a href="/about">About</a><a href="/services">Services</a></nav>
            <p>We do great stuff for people.</p>
        </body></html>
        """
        mock_page = make_mock_page(title="Example Corp", html=homepage_html)

        settings = MagicMock()
        settings.claude_code_api_url = "http://localhost:8000/v1"
        settings.claude_model = "test-model"
        settings.claude_code_api_key = "test-key"

        with (
            patch("sastaspace.crawler.async_playwright") as mock_pw,
            patch("sastaspace.crawler._llm_select_pages", return_value=[]),
            patch(
                "sastaspace.crawler.download_and_validate_assets",
                new_callable=AsyncMock,
            ) as mock_download,
            patch("sastaspace.crawler.build_business_profile") as mock_profile,
        ):
            mock_download.return_value = AssetManifest()
            mock_profile.return_value = BusinessProfile(business_name="Example Corp")

            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_pw.return_value.__aenter__ = AsyncMock(return_value=mock_pw.return_value)
            mock_pw.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_pw.return_value.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_browser.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)
            mock_browser.close = AsyncMock()

            result = await enhanced_crawl("https://example.com", settings)

        assert isinstance(result, EnhancedCrawlResult)
        assert result.homepage.title == "Example Corp"
        assert result.homepage.error == ""

    @pytest.mark.asyncio
    async def test_returns_early_on_homepage_error(self):
        """If homepage crawl fails, enhanced_crawl returns early."""
        settings = MagicMock()
        settings.claude_code_api_url = "http://localhost:8000/v1"
        settings.claude_model = "test-model"
        settings.claude_code_api_key = "test-key"

        with patch("sastaspace.crawler.async_playwright") as mock_pw:
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()
            mock_page.goto = AsyncMock(side_effect=OSError("Timeout"))
            mock_pw.return_value.__aenter__ = AsyncMock(return_value=mock_pw.return_value)
            mock_pw.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_pw.return_value.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_browser.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)
            mock_browser.close = AsyncMock()

            result = await enhanced_crawl("https://broken.com", settings)

        assert isinstance(result, EnhancedCrawlResult)
        assert result.homepage.error != ""
        assert result.internal_pages == []

    @pytest.mark.asyncio
    async def test_crawls_internal_pages(self):
        """enhanced_crawl crawls internal pages selected by LLM."""
        homepage_html = """
        <html><body>
            <h1>Example</h1>
            <a href="/about">About</a>
            <a href="/services">Services</a>
            <p>Welcome to Example Corp. We provide amazing services.</p>
        </body></html>
        """
        # Make enough text to pass bot protection (>500 chars)
        about_html = (
            "<html><body><h1>About Us</h1>"
            "<p>" + ("About page content with lots of text. " * 30) + "</p>"
            "</body></html>"
        )

        call_count = {"n": 0}

        async def mock_new_page():
            call_count["n"] += 1
            if call_count["n"] == 1:
                return make_mock_page(title="Example", html=homepage_html)
            return make_mock_page(
                title="About Us",
                html=about_html,
                final_url="https://example.com/about",
            )

        settings = MagicMock()
        settings.claude_code_api_url = "http://localhost:8000/v1"
        settings.claude_model = "test-model"
        settings.claude_code_api_key = "test-key"

        with (
            patch("sastaspace.crawler.async_playwright") as mock_pw,
            patch(
                "sastaspace.crawler._llm_select_pages",
                return_value=["https://example.com/about"],
            ),
            patch(
                "sastaspace.crawler.download_and_validate_assets",
                new_callable=AsyncMock,
            ) as mock_download,
            patch("sastaspace.crawler.build_business_profile") as mock_profile,
        ):
            mock_download.return_value = AssetManifest()
            mock_profile.return_value = BusinessProfile(business_name="Test")

            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_context.new_page = mock_new_page
            mock_pw.return_value.__aenter__ = AsyncMock(return_value=mock_pw.return_value)
            mock_pw.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_pw.return_value.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_browser.new_context = AsyncMock(return_value=mock_context)
            mock_browser.close = AsyncMock()

            result = await enhanced_crawl("https://example.com", settings)

        assert len(result.internal_pages) == 1

    @pytest.mark.asyncio
    async def test_handles_browser_launch_failure(self):
        """enhanced_crawl handles total browser failure gracefully."""
        settings = MagicMock()
        settings.claude_code_api_url = "http://localhost:8000/v1"
        settings.claude_model = "test-model"
        settings.claude_code_api_key = "test-key"

        with patch("sastaspace.crawler.async_playwright") as mock_pw:
            mock_pw.return_value.__aenter__ = AsyncMock(return_value=mock_pw.return_value)
            mock_pw.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_pw.return_value.chromium.launch = AsyncMock(side_effect=OSError("Browser crashed"))

            result = await enhanced_crawl("https://example.com", settings)

        assert isinstance(result, EnhancedCrawlResult)
        assert "Browser crashed" in result.homepage.error

    @pytest.mark.asyncio
    async def test_asset_download_skips_clamav(self):
        """enhanced_crawl must pass skip_clamav=True to download_and_validate_assets."""
        settings = MagicMock()
        settings.claude_code_api_url = "http://localhost:8000/v1"
        settings.claude_model = "test-model"
        settings.claude_code_api_key = "test-key"
        settings.browserless_url = None

        homepage = CrawlResult(
            url="https://example.com",
            title="Test",
            meta_description="",
            favicon_url="",
            html_source="<html><body><img src='/logo.png'></body></html>",
            screenshot_base64="",
            error="",
            images=[{"src": "/logo.png"}],
        )

        with (
            patch("sastaspace.crawler.async_playwright") as mock_pw,
            patch("sastaspace.crawler._crawl_page", return_value=homepage),
            patch("sastaspace.crawler._extract_all_internal_links", return_value=[]),
            patch("sastaspace.crawler._filter_noise_links", return_value=[]),
            patch("sastaspace.crawler._llm_select_pages", return_value=[]),
            patch(
                "sastaspace.crawler.download_and_validate_assets",
                new_callable=AsyncMock,
            ) as mock_download,
            patch("sastaspace.crawler.build_business_profile") as mock_profile,
        ):
            mock_download.return_value = AssetManifest(assets=[], total_size_bytes=0)
            mock_profile.return_value = BusinessProfile(business_name="Test")

            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_pw.return_value.__aenter__ = AsyncMock(return_value=mock_pw.return_value)
            mock_pw.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_pw.return_value.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_browser.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=AsyncMock())
            mock_browser.close = AsyncMock()

            await enhanced_crawl("https://example.com", settings)

        # Verify skip_clamav=True was passed
        mock_download.assert_called_once()
        call_kwargs = mock_download.call_args
        assert call_kwargs.kwargs.get("skip_clamav") is True or (
            len(call_kwargs.args) >= 3 and call_kwargs.args[2] is True
        ), "download_and_validate_assets must be called with skip_clamav=True"
