# tests/test_html_utils.py
"""Tests for HTML validation, sanitization, and badge injection."""

import pytest

from sastaspace.html_utils import (
    RedesignError,
    RedesignResult,
    clean_html,
    inject_badge,
    sanitize_html,
    validate_html,
)

# --- clean_html tests ---


class TestCleanHtml:
    def test_strips_markdown_fences(self):
        raw = "```html\n<p>Hello</p>\n```"
        assert clean_html(raw) == "<p>Hello</p>"

    def test_strips_plain_fences(self):
        raw = "```\n<p>Hello</p>\n```"
        assert clean_html(raw) == "<p>Hello</p>"

    def test_strips_whitespace(self):
        assert clean_html("  <p>Hello</p>  ") == "<p>Hello</p>"

    def test_case_insensitive_fence(self):
        raw = "```HTML\n<div>test</div>\n```"
        assert clean_html(raw) == "<div>test</div>"

    def test_no_fences_passthrough(self):
        assert clean_html("<p>Hello</p>") == "<p>Hello</p>"


# --- validate_html tests ---


class TestValidateHtml:
    def test_valid_html_passes(self):
        validate_html("<!DOCTYPE html><html><body></body></html>")

    def test_empty_raises(self):
        with pytest.raises(RedesignError, match="empty"):
            validate_html("")

    def test_missing_doctype_raises(self):
        with pytest.raises(RedesignError, match="DOCTYPE"):
            validate_html("<html><body></body></html>")

    def test_missing_closing_html_raises(self):
        with pytest.raises(RedesignError, match="truncated"):
            validate_html("<!DOCTYPE html><html><body></body>")

    def test_case_insensitive_doctype(self):
        validate_html("<!doctype HTML><html><body></body></html>")


# --- sanitize_html tests ---


class TestSanitizeHtml:
    def test_strips_onclick(self):
        html = '<button onclick="alert(1)">Click</button>'
        result = sanitize_html(html)
        assert "onclick" not in result
        assert "Click" in result

    def test_strips_onerror(self):
        html = '<img onerror="alert(1)" src="x">'
        result = sanitize_html(html)
        assert "onerror" not in result

    def test_strips_onload_single_quotes(self):
        html = "<body onload='stealCookies()'>"
        result = sanitize_html(html)
        assert "onload" not in result

    def test_strips_javascript_href(self):
        html = '<a href="javascript:alert(1)">Link</a>'
        result = sanitize_html(html)
        assert "javascript:" not in result

    def test_strips_javascript_src(self):
        html = '<iframe src="javascript:alert(1)"></iframe>'
        result = sanitize_html(html)
        assert "javascript:" not in result

    def test_preserves_normal_href(self):
        html = '<a href="https://example.com">Link</a>'
        result = sanitize_html(html)
        assert 'href="https://example.com"' in result

    def test_strips_javascript_href_single_quotes(self):
        html = "<a href='javascript:void(0)'>Link</a>"
        result = sanitize_html(html)
        assert "javascript:" not in result


# --- inject_badge tests ---


class TestInjectBadge:
    def test_injects_before_body(self):
        html = "<html><body><p>Hello</p></body></html>"
        result = inject_badge(html)
        assert "Redesigned by SastaSpace" in result
        assert result.index("SastaSpace") < result.index("</body>")

    def test_fallback_before_html(self):
        html = "<html><p>Hello</p></html>"
        result = inject_badge(html)
        assert "Redesigned by SastaSpace" in result
        assert result.index("SastaSpace") < result.index("</html>")

    def test_appends_when_no_closing_tags(self):
        html = "<p>Hello</p>"
        result = inject_badge(html)
        assert result.endswith("</a></div>")

    def test_case_insensitive_body(self):
        html = "<html><BODY><p>Hello</p></BODY></html>"
        result = inject_badge(html)
        assert "Redesigned by SastaSpace" in result


# --- RedesignResult tests ---


class TestRedesignResult:
    def test_defaults(self):
        r = RedesignResult(html="<p>Test</p>")
        assert r.html == "<p>Test</p>"
        assert r.build_dir is None

    def test_with_build_dir(self):
        from pathlib import Path

        r = RedesignResult(html="<p>Test</p>", build_dir=Path("/tmp/dist"))
        assert r.build_dir == Path("/tmp/dist")
