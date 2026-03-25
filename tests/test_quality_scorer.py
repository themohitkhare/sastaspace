# tests/test_quality_scorer.py
"""Tests for the redesign quality scoring engine."""

from sastaspace.quality_scorer import (
    MINIMUM_SCORE,
    QualityScore,
    _analyze_html,
    score_anti_slop,
    score_content_preservation,
    score_image_integrity,
    score_interactivity,
    score_redesign,
    score_structure,
    score_visual_richness,
)

# --- Sample HTML fixtures ---

GOOD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Test Site</title>
<style>
:root { --primary: #c8a55a; --bg: #1a1a2e; }
body { font-family: 'Space Grotesk', sans-serif; margin: 0; }
.hero { background: linear-gradient(135deg, var(--bg), #16213e); }
.card { box-shadow: 0 4px 20px rgba(0,0,0,0.2); transition: transform 0.3s ease; }
.card:hover { transform: translateY(-4px); }
@media (max-width: 768px) { .hero { padding: 2rem; } }
@media (max-width: 480px) { .grid { grid-template-columns: 1fr; } }
@media (min-width: 1024px) { .container { max-width: 1200px; } }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
.fade-in { animation: fadeIn 0.6s ease; }
</style>
</head>
<body>
<header>
<nav><a href="/">Impex Lift</a><a href="/services">Services</a><a href="/about">About</a></nav>
</header>
<main>
<section class="hero">
<h1>Vertical Mobility: Engineered for Your Vision</h1>
<p>Reliable, innovative lift solutions for residential and commercial needs.</p>
<a href="/contact">Get Your Quote</a>
</section>
<section>
<h2>Our Services</h2>
<div class="grid">
<div class="card">
<img src="https://impexlift.com/images/e1.jpg" alt="Capsule">
<h3>Capsule Elevator</h3></div>
<div class="card">
<img src="https://impexlift.com/images/e2.jpg" alt="Home">
<h3>Home Elevator</h3></div>
<div class="card">
<img src="https://impexlift.com/images/e3.jpg" alt="Hospital">
<h3>Hospital Elevator</h3></div>
</div>
</section>
<section>
<h2>25+ Years of Excellence</h2>
<p>Welcome to Impex Lift, your trusted lift manufacturer in Lucknow. 3654+ satisfied customers.</p>
</section>
</main>
<footer>
<p>&copy; 2023 Impex Lift. All rights reserved.</p>
<a href="/privacy">Privacy</a>
</footer>
<script>
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
    }
  });
});
document.querySelectorAll('.fade-in').forEach(el => observer.observe(el));
document.querySelector('.menu-toggle')?.addEventListener('click', () => {
  document.querySelector('.nav').classList.toggle('open');
});
</script>
</body>
</html>"""

BAD_HTML = """<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
<div>
<h1>Vertical Mobility: Engineered for Your Vision</h1>
<p>Lorem ipsum dolor sit amet, consectetur adipiscing elit.</p>
<img src="">
<img src="placeholder.com/400x300">
<a href="#">Link</a>
<a href="#">Link</a>
<a href="#">Link</a>
<a href="#">Link</a>
<p>Portitor aptent sociosqu per etiam inceptos posuere lobortis</p>
<p>Portitor aptent sociosqu per etiam inceptos posuere lobortis</p>
</div>
</body>
</html>"""

MINIMAL_HTML = "<p>Hello</p>"

ORIGINAL_HEADINGS = [
    "Imagination Meets Reality In Design",
    "Engineering That Drives Progress",
    "Comprehensive Lifts Design Services",
    "Working Easy Process",
]

ORIGINAL_TEXT = (
    "Welcome to Impex Lift, trusted lift manufacturer in Lucknow. "
    "We specialize in designing and manufacturing state-of-the-art lifts "
    "and elevators for residential, commercial, and industrial needs. "
    "Capsule Elevator Home Elevator Hospital Elevator Car Elevator "
    "3654+ satisfied customers 100+ expert team 168+ modern equipment"
)

ORIGINAL_IMAGES = [
    {"src": "https://impexlift.com/images/elevator1.jpg"},
    {"src": "https://impexlift.com/images/elevator2.jpg"},
    {"src": "https://impexlift.com/images/elevator3.jpg"},
    {"src": "https://impexlift.com/images/team1.jpg"},
    {"src": "https://impexlift.com/images/team2.jpg"},
]


# --- Structure tests ---


class TestScoreStructure:
    def test_good_html_scores_high(self):
        analyzer = _analyze_html(GOOD_HTML)
        score, issues = score_structure(analyzer)
        assert score >= 70
        assert not any("Missing h1" in i for i in issues)

    def test_bad_html_scores_lower(self):
        analyzer = _analyze_html(BAD_HTML)
        score, issues = score_structure(analyzer)
        assert score < 70
        assert any("Missing" in i for i in issues)

    def test_minimal_html_scores_very_low(self):
        analyzer = _analyze_html(MINIMAL_HTML)
        score, _ = score_structure(analyzer)
        assert score < 30

    def test_detects_missing_viewport(self):
        analyzer = _analyze_html(BAD_HTML)
        _, issues = score_structure(analyzer)
        assert any("viewport" in i for i in issues)


# --- Content preservation tests ---


class TestScoreContentPreservation:
    def test_good_preservation(self):
        analyzer = _analyze_html(GOOD_HTML)
        score, _ = score_content_preservation(analyzer, ORIGINAL_HEADINGS, ORIGINAL_TEXT)
        assert score >= 40

    def test_bad_preservation(self):
        html = "<!DOCTYPE html><html><body><p>Completely unrelated content</p></body></html>"
        analyzer = _analyze_html(html)
        score, issues = score_content_preservation(analyzer, ORIGINAL_HEADINGS, ORIGINAL_TEXT)
        assert score < 40
        assert len(issues) > 0

    def test_no_original_content(self):
        analyzer = _analyze_html(GOOD_HTML)
        score, _ = score_content_preservation(analyzer, [], "")
        assert score == 50  # Neutral when nothing to compare


# --- Image integrity tests ---


class TestScoreImageIntegrity:
    def test_real_images_score_high(self):
        analyzer = _analyze_html(GOOD_HTML)
        score, issues = score_image_integrity(analyzer, ORIGINAL_IMAGES)
        assert score >= 50
        assert not any("broken" in i.lower() for i in issues)

    def test_broken_images_score_low(self):
        analyzer = _analyze_html(BAD_HTML)
        score, issues = score_image_integrity(analyzer, ORIGINAL_IMAGES)
        assert score < 50
        assert len(issues) > 0

    def test_no_images_when_original_had_them(self):
        html = "<!DOCTYPE html><html><body><p>No images</p></body></html>"
        analyzer = _analyze_html(html)
        score, issues = score_image_integrity(analyzer, ORIGINAL_IMAGES)
        assert score <= 20
        assert any("0" in i for i in issues)


# --- Visual richness tests ---


class TestScoreVisualRichness:
    def test_rich_css_scores_high(self):
        analyzer = _analyze_html(GOOD_HTML)
        score, _ = score_visual_richness(analyzer)
        assert score >= 50

    def test_no_css_scores_low(self):
        analyzer = _analyze_html(BAD_HTML)
        score, issues = score_visual_richness(analyzer)
        assert score < 20
        assert any("No inline CSS" in i for i in issues)


# --- Interactivity tests ---


class TestScoreInteractivity:
    def test_js_scores_higher(self):
        analyzer = _analyze_html(GOOD_HTML)
        score, _ = score_interactivity(analyzer)
        assert score >= 40

    def test_no_js_scores_low(self):
        analyzer = _analyze_html(BAD_HTML)
        score, issues = score_interactivity(analyzer)
        assert score <= 30
        assert any("No JavaScript" in i for i in issues)


# --- Anti-slop tests ---


class TestScoreAntiSlop:
    def test_clean_html_scores_high(self):
        analyzer = _analyze_html(GOOD_HTML)
        score, _ = score_anti_slop(analyzer)
        assert score >= 80

    def test_lorem_ipsum_detected(self):
        analyzer = _analyze_html(BAD_HTML)
        score, issues = score_anti_slop(analyzer)
        assert score < 80
        assert any("Placeholder" in i or "lorem" in i.lower() for i in issues)

    def test_broken_links_detected(self):
        analyzer = _analyze_html(BAD_HTML)
        _, issues = score_anti_slop(analyzer)
        assert any("broken" in i.lower() or "empty" in i.lower() for i in issues)

    def test_repeated_filler_detected(self):
        analyzer = _analyze_html(BAD_HTML)
        _, issues = score_anti_slop(analyzer)
        assert any("dummy" in i.lower() or "filler" in i.lower() for i in issues)


# --- Overall scoring tests ---


class TestScoreRedesign:
    def test_good_redesign_passes_threshold(self):
        result = score_redesign(
            GOOD_HTML,
            original_headings=ORIGINAL_HEADINGS,
            original_text=ORIGINAL_TEXT,
            original_images=ORIGINAL_IMAGES,
        )
        assert result.overall >= MINIMUM_SCORE
        assert result.grade in ("A", "B", "C")

    def test_bad_redesign_fails_threshold(self):
        result = score_redesign(
            BAD_HTML,
            original_headings=ORIGINAL_HEADINGS,
            original_text=ORIGINAL_TEXT,
            original_images=ORIGINAL_IMAGES,
        )
        assert result.grade in ("D", "F")

    def test_minimal_html_fails_hard(self):
        result = score_redesign(MINIMAL_HTML)
        assert result.overall <= MINIMUM_SCORE
        assert result.grade in ("D", "F")

    def test_returns_quality_score_dataclass(self):
        result = score_redesign(GOOD_HTML)
        assert isinstance(result, QualityScore)
        assert 0 <= result.overall <= 100
        assert result.grade in ("A", "B", "C", "D", "F")

    def test_to_dict(self):
        result = score_redesign(GOOD_HTML)
        d = result.to_dict()
        assert "overall" in d
        assert "grade" in d
        assert "issues" in d
        assert isinstance(d["issues"], list)

    def test_all_dimensions_present(self):
        result = score_redesign(GOOD_HTML)
        assert result.structure >= 0
        assert result.content_preservation >= 0
        assert result.image_integrity >= 0
        assert result.visual_richness >= 0
        assert result.interactivity >= 0
        assert result.anti_slop >= 0
