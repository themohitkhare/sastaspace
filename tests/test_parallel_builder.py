# tests/test_parallel_builder.py
"""Tests for parallel builder — section splitting, HTML merging, and fallback."""

from unittest.mock import patch

from sastaspace.agents.models import ContentSection, RedesignPlan
from sastaspace.agents.pipeline import (
    _classify_sections,
    _merge_parallel_html,
    _run_parallel_builder,
)
from sastaspace.config import Settings
from sastaspace.crawler import CrawlResult

# ---------------------------------------------------------------------------
# _classify_sections
# ---------------------------------------------------------------------------


class TestClassifySections:
    """_classify_sections splits plan content_sections into 3 groups."""

    def test_empty_sections_have_placeholders(self):
        plan = RedesignPlan()
        above, content, below = _classify_sections(plan)
        assert above == ["hero + navigation"]
        assert content == ["main content sections from content_map"]
        assert below == ["CTA + footer"]

    def test_hero_goes_above_fold(self):
        plan = RedesignPlan(
            content_sections=[
                ContentSection(heading="Welcome Hero", content_type="hero"),
                ContentSection(heading="Nav Bar", content_type="navigation"),
            ]
        )
        above, content, below = _classify_sections(plan)
        assert "Welcome Hero" in above
        assert "Nav Bar" in above
        # content and below get placeholders
        assert content == ["main content sections from content_map"]
        assert below == ["CTA + footer"]

    def test_footer_goes_below_fold(self):
        plan = RedesignPlan(
            content_sections=[
                ContentSection(heading="Get Started", content_type="cta"),
                ContentSection(heading="Site Footer", content_type="footer"),
            ]
        )
        above, content, below = _classify_sections(plan)
        assert "Get Started" in below
        assert "Site Footer" in below
        assert above == ["hero + navigation"]

    def test_features_go_to_content(self):
        plan = RedesignPlan(
            content_sections=[
                ContentSection(heading="Our Features", content_type="features"),
                ContentSection(heading="Testimonials", content_type="testimonials"),
                ContentSection(heading="About Us", content_type="about"),
            ]
        )
        above, content, below = _classify_sections(plan)
        assert "Our Features" in content
        assert "Testimonials" in content
        assert "About Us" in content

    def test_full_page_classification(self):
        plan = RedesignPlan(
            content_sections=[
                ContentSection(heading="Hero", content_type="hero"),
                ContentSection(heading="Features", content_type="features"),
                ContentSection(heading="Stats", content_type="stats"),
                ContentSection(heading="CTA", content_type="cta"),
                ContentSection(heading="Footer", content_type="footer"),
            ]
        )
        above, content, below = _classify_sections(plan)
        assert "Hero" in above
        assert "Features" in content
        assert "Stats" in content
        assert "CTA" in below
        assert "Footer" in below


# ---------------------------------------------------------------------------
# _merge_parallel_html
# ---------------------------------------------------------------------------


class TestMergeParallelHtml:
    """_merge_parallel_html assembles 3 fragments into valid HTML."""

    def test_basic_merge(self):
        above = "<!DOCTYPE html><html><head><style>body{}</style></head><body><header>Nav</header>"
        content = "<section>Features</section><section>Stats</section>"
        below = "<footer>Footer</footer></body></html>"
        result = _merge_parallel_html(above, content, below)

        assert result.startswith("<!DOCTYPE html>")
        assert "</body>" in result
        assert "</html>" in result
        assert "<header>Nav</header>" in result
        assert "<section>Features</section>" in result
        assert "<footer>Footer</footer>" in result

    def test_strips_accidental_closing_from_above(self):
        above = "<!DOCTYPE html><html><head></head><body><nav>Nav</nav></body></html>"
        content = "<section>Content</section>"
        below = "<footer>F</footer></body></html>"
        result = _merge_parallel_html(above, content, below)

        # Should not have double </body></html>
        assert result.count("</body>") == 1
        assert result.count("</html>") == 1
        assert "<nav>Nav</nav>" in result
        assert "<section>Content</section>" in result

    def test_strips_document_wrapper_from_middle(self):
        above = "<!DOCTYPE html><html><head></head><body><nav>Nav</nav>"
        content = "<!DOCTYPE html><html><head><style>x</style></head><body><section>X</section>"
        below = "<footer>F</footer></body></html>"
        result = _merge_parallel_html(above, content, below)

        # The middle's DOCTYPE/head should be stripped
        assert result.count("<!DOCTYPE") == 1
        assert "<section>X</section>" in result

    def test_adds_missing_closing_tags_to_below(self):
        above = "<!DOCTYPE html><html><head></head><body><nav>Nav</nav>"
        content = "<section>Content</section>"
        below = "<footer>Footer</footer>"
        result = _merge_parallel_html(above, content, below)

        assert "</body>" in result
        assert "</html>" in result

    def test_handles_markdown_fences(self):
        above = "```html\n<!DOCTYPE html><html><head></head><body><nav>N</nav>\n```"
        content = "```\n<section>S</section>\n```"
        below = "```html\n<footer>F</footer></body></html>\n```"
        result = _merge_parallel_html(above, content, below)

        assert "```" not in result
        assert "<nav>N</nav>" in result
        assert "<section>S</section>" in result
        assert "<footer>F</footer>" in result


# ---------------------------------------------------------------------------
# _run_parallel_builder (integration — mocked LLM calls)
# ---------------------------------------------------------------------------


class TestRunParallelBuilder:
    """_run_parallel_builder orchestrates 3 concurrent calls and merges results."""

    def _settings(self) -> Settings:
        return Settings(
            claude_code_api_url="http://claude:8000/v1",
            claude_code_api_key="key",
            html_generator_model="claude-sonnet-4-6-20250514",
        )

    def _crawl_result(self) -> CrawlResult:
        return CrawlResult(
            url="https://example.com",
            title="Example",
            meta_description="desc",
            favicon_url="",
            html_source="<html></html>",
            screenshot_base64="",
            colors=["#fff"],
            fonts=["Inter"],
        )

    def _plan(self) -> RedesignPlan:
        return RedesignPlan(
            content_sections=[
                ContentSection(heading="Hero", content_type="hero"),
                ContentSection(heading="Features", content_type="features"),
                ContentSection(heading="Footer", content_type="footer"),
            ],
            content_map={"hero_headline": "Welcome", "features_heading": "Our Features"},
        )

    @patch("sastaspace.agents.pipeline._run_agent")
    def test_parallel_produces_valid_html(self, mock_agent):
        """Three concurrent calls produce valid merged HTML."""
        above = "<!DOCTYPE html><html><head><style>body{}</style></head><body><nav>Nav</nav>"
        content = '<section class="reveal">Features</section>'
        below = "<footer>Footer</footer></body></html>"
        mock_agent.side_effect = [above, content, below]

        result = _run_parallel_builder(self._plan(), self._crawl_result(), self._settings())

        assert "<!doctype html" in result.lower() or "<!DOCTYPE html>" in result
        assert "</html>" in result.lower()
        assert "<nav>Nav</nav>" in result
        assert "Features" in result
        assert "<footer>Footer</footer>" in result
        assert mock_agent.call_count == 3

    @patch("sastaspace.agents.pipeline._run_agent")
    def test_parallel_calls_use_section_names(self, mock_agent):
        """Each call uses a distinct agent name for logging."""
        above = "<!DOCTYPE html><html><head></head><body><nav>N</nav>"
        content = "<section>C</section>"
        below = "<footer>F</footer></body></html>"
        mock_agent.side_effect = [above, content, below]

        _run_parallel_builder(self._plan(), self._crawl_result(), self._settings())

        agent_names = [call.args[0] for call in mock_agent.call_args_list]
        assert "builder_above_fold" in agent_names
        assert "builder_content" in agent_names
        assert "builder_below_fold" in agent_names

    @patch("sastaspace.agents.pipeline._run_builder")
    @patch("sastaspace.agents.pipeline._run_agent")
    def test_falls_back_on_failure(self, mock_agent, mock_single_builder):
        """If parallel fails, falls back to single-call _run_builder."""
        mock_agent.side_effect = Exception("LLM timeout")
        mock_single_builder.return_value = (
            "<!DOCTYPE html><html><head></head><body>Fallback</body></html>"
        )

        result = _run_parallel_builder(self._plan(), self._crawl_result(), self._settings())

        assert "Fallback" in result
        mock_single_builder.assert_called_once()

    @patch("sastaspace.agents.pipeline._run_builder")
    @patch("sastaspace.agents.pipeline._run_agent")
    def test_falls_back_on_invalid_html(self, mock_agent, mock_single_builder):
        """If merged HTML fails validation, falls back to single-call builder."""
        # Return fragments that when merged produce invalid HTML (no DOCTYPE)
        mock_agent.side_effect = [
            "<div>broken above</div>",
            "<section>content</section>",
            "<footer>footer</footer>",
        ]
        mock_single_builder.return_value = (
            "<!DOCTYPE html><html><head></head><body>Good</body></html>"
        )

        result = _run_parallel_builder(self._plan(), self._crawl_result(), self._settings())

        assert "Good" in result
        mock_single_builder.assert_called_once()


# ---------------------------------------------------------------------------
# Config toggle
# ---------------------------------------------------------------------------


class TestParallelBuilderConfig:
    """enable_parallel_builder setting controls parallel vs single path."""

    def test_default_is_false(self):
        s = Settings()
        assert s.enable_parallel_builder is False

    def test_can_enable(self):
        s = Settings(enable_parallel_builder=True)
        assert s.enable_parallel_builder is True
