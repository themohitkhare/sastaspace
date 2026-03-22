# tests/test_business_profiler.py
import json
from unittest.mock import patch

from sastaspace.business_profiler import _deduplicate_text, build_business_profile
from sastaspace.crawler import CrawlResult
from sastaspace.models import PageCrawlResult


def _make_homepage(**overrides):
    defaults = dict(
        url="https://example.com",
        title="Acme Corp",
        meta_description="Best widgets",
        favicon_url="",
        html_source="",
        screenshot_base64="",
        headings=["Welcome to Acme"],
        navigation_links=[],
        text_content="We make widgets.",
        images=[],
        colors=[],
        fonts=[],
        sections=[],
    )
    defaults.update(overrides)
    return CrawlResult(**defaults)


def _make_page(**overrides):
    defaults = dict(
        url="https://example.com/about",
        page_type="about",
        title="About",
        headings=["Our Story"],
        text_content="Founded in 2020.",
        images=[],
        testimonials=[],
    )
    defaults.update(overrides)
    return PageCrawlResult(**defaults)


class TestDeduplicateText:
    def test_removes_duplicate_sentences(self):
        texts = ["Header text. We make widgets.", "Header text. About our team."]
        result = _deduplicate_text(texts)
        assert result.count("Header text.") == 1

    def test_preserves_unique_content(self):
        texts = ["Unique content A.", "Unique content B."]
        result = _deduplicate_text(texts)
        assert "Unique content A." in result
        assert "Unique content B." in result

    def test_handles_no_newlines(self):
        """Crawler output is single-line — splitting on newlines would fail."""
        texts = ["Welcome to Acme. We build widgets. Contact us today."]
        result = _deduplicate_text(texts)
        assert "Welcome to Acme." in result
        assert "We build widgets." in result


class TestBuildBusinessProfile:
    @patch("sastaspace.business_profiler._call_llm")
    def test_returns_profile_from_llm(self, mock_llm):
        mock_llm.return_value = json.dumps(
            {
                "business_name": "Acme Corp",
                "industry": "manufacturing",
                "services": ["Widget production"],
                "target_audience": "B2B companies",
                "tone": "professional",
                "differentiators": ["Fastest delivery"],
                "social_proof": ["500+ clients"],
                "pricing_model": "contact-based",
                "cta_primary": "Get a Quote",
                "brand_personality": "Reliable and efficient.",
            }
        )
        homepage = _make_homepage()
        result = build_business_profile(homepage, [], api_url="http://x", model="m", api_key="k")
        assert result.business_name == "Acme Corp"
        assert result.industry == "manufacturing"

    @patch("sastaspace.business_profiler._call_llm")
    def test_fallback_on_llm_failure(self, mock_llm):
        mock_llm.side_effect = ValueError("API down")
        homepage = _make_homepage()
        result = build_business_profile(homepage, [], api_url="http://x", model="m", api_key="k")
        assert result.business_name == "Acme Corp"
        assert result.industry == "unknown"

    @patch("sastaspace.business_profiler._call_llm")
    def test_fallback_on_invalid_json(self, mock_llm):
        mock_llm.return_value = "not valid json at all"
        homepage = _make_homepage()
        result = build_business_profile(homepage, [], api_url="http://x", model="m", api_key="k")
        assert result.business_name == "Acme Corp"
        assert result.industry == "unknown"
