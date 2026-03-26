# tests/test_static_analyzer.py
from sastaspace.swarm.static_analyzer import StaticAnalyzer

VALID_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Test</title>
  <style>
    :root { --color-primary: #1a1a2e; }
    body { font-family: 'Inter', sans-serif; color: var(--color-primary); }
    .hero { background: #fff; }
    @media (max-width: 768px) { .hero { padding: 1rem; } }
  </style>
</head>
<body>
  <header><nav><a href="#features">Features</a></nav></header>
  <section id="features">
    <h1>Features</h1>
    <img src="https://example-real-site.com/logo.png" alt="Logo">
  </section>
  <footer>Footer</footer>
</body>
</html>"""


class TestStaticAnalyzer:
    def test_valid_html_passes(self):
        result = StaticAnalyzer.analyze(VALID_HTML)
        assert result.passed
        assert len(result.failures) == 0

    def test_missing_doctype_fails(self):
        html = "<html><body>No doctype</body></html>"
        result = StaticAnalyzer.analyze(html)
        assert not result.passed
        assert any("DOCTYPE" in f for f in result.failures)

    def test_missing_closing_html_fails(self):
        html = "<!DOCTYPE html><html><body>No closing tag"
        result = StaticAnalyzer.analyze(html)
        assert not result.passed
        assert any("</html>" in f for f in result.failures)

    def test_placeholder_url_detected(self):
        html = VALID_HTML.replace(
            "https://example-real-site.com/logo.png", "https://via.placeholder.com/300x200"
        )
        result = StaticAnalyzer.analyze(html)
        assert not result.passed
        assert any("placeholder" in f.lower() for f in result.failures)

    def test_unsplash_url_detected(self):
        html = VALID_HTML.replace(
            "https://example-real-site.com/logo.png", "https://images.unsplash.com/photo-123"
        )
        result = StaticAnalyzer.analyze(html)
        assert not result.passed
        assert any("unsplash" in f.lower() for f in result.failures)

    def test_missing_font_fallback_detected(self):
        html = VALID_HTML.replace("font-family: 'Inter', sans-serif;", "font-family: 'Inter';")
        result = StaticAnalyzer.analyze(html)
        assert not result.passed
        assert any("fallback" in f.lower() for f in result.failures)

    def test_broken_internal_anchor_detected(self):
        html = VALID_HTML.replace('id="features"', 'id="pricing"')
        result = StaticAnalyzer.analyze(html)
        assert not result.passed
        assert any("features" in f for f in result.failures)

    def test_console_log_detected(self):
        html = VALID_HTML.replace("</body>", "<script>console.log('debug')</script></body>")
        result = StaticAnalyzer.analyze(html)
        assert not result.passed
        assert any("console.log" in f for f in result.failures)

    def test_undefined_css_variable_detected(self):
        html = VALID_HTML.replace("color: var(--color-primary)", "color: var(--color-missing)")
        result = StaticAnalyzer.analyze(html)
        assert not result.passed
        assert any("--color-missing" in f for f in result.failures)

    def test_file_size_limit(self):
        huge = "<!DOCTYPE html><html><body>" + "x" * 600_000 + "</body></html>"
        result = StaticAnalyzer.analyze(huge)
        assert not result.passed
        assert any("size" in f.lower() for f in result.failures)

    def test_external_cdn_detected(self):
        html = VALID_HTML.replace(
            "</head>",
            '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5/dist/css/bootstrap.min.css"></head>',
        )
        result = StaticAnalyzer.analyze(html)
        assert not result.passed
        assert any("external" in f.lower() or "cdn" in f.lower() for f in result.failures)
