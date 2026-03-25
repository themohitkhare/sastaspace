# sastaspace/quality_scorer.py
"""Post-generation quality scoring engine.

Evaluates AI-generated HTML against the original crawl data to ensure
redesigns are objectively better — not worse — than the source site.
Scores are 0-100 per dimension; overall score gates deployment.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

logger = logging.getLogger(__name__)

# Minimum overall score to accept a redesign (0-100).
# Below this, the pipeline should retry or reject.
MINIMUM_SCORE = 40


@dataclass
class QualityScore:
    """Breakdown of redesign quality across multiple dimensions."""

    # Individual dimension scores (0-100 each)
    structure: int = 0  # Semantic HTML: sections, headings, nav, footer
    content_preservation: int = 0  # How much original content survived
    image_integrity: int = 0  # Images present and using real URLs
    visual_richness: int = 0  # CSS, animations, interactivity
    interactivity: int = 0  # Hover states, transitions, JS counters
    anti_slop: int = 0  # Penalizes AI tells: placeholder text, lorem ipsum, broken refs

    # Metadata
    overall: int = 0
    grade: str = "F"
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "overall": self.overall,
            "grade": self.grade,
            "structure": self.structure,
            "content_preservation": self.content_preservation,
            "image_integrity": self.image_integrity,
            "visual_richness": self.visual_richness,
            "interactivity": self.interactivity,
            "anti_slop": self.anti_slop,
            "issues": self.issues,
            "warnings": self.warnings,
        }


class _HTMLAnalyzer(HTMLParser):
    """Lightweight HTML structure analyzer — no external deps."""

    def __init__(self):
        super().__init__()
        self.tag_counts: dict[str, int] = {}
        self.img_srcs: list[str] = []
        self.link_hrefs: list[str] = []
        self.text_chunks: list[str] = []
        self.style_content: str = ""
        self.script_content: str = ""
        self._in_style = False
        self._in_script = False
        self.has_viewport_meta = False
        self.total_elements = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tag_counts[tag] = self.tag_counts.get(tag, 0) + 1
        self.total_elements += 1
        attr_dict = dict(attrs)

        if tag == "img":
            src = attr_dict.get("src", "")
            if src:
                self.img_srcs.append(src)
        elif tag == "a":
            href = attr_dict.get("href", "")
            if href:
                self.link_hrefs.append(href)
        elif tag == "style":
            self._in_style = True
        elif tag == "script":
            self._in_script = True
        elif tag == "meta":
            if attr_dict.get("name", "").lower() == "viewport":
                self.has_viewport_meta = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "style":
            self._in_style = False
        elif tag == "script":
            self._in_script = False

    def handle_data(self, data: str) -> None:
        if self._in_style:
            self.style_content += data
        elif self._in_script:
            self.script_content += data
        else:
            stripped = data.strip()
            if stripped:
                self.text_chunks.append(stripped)


def _analyze_html(html: str) -> _HTMLAnalyzer:
    """Parse HTML and return structural analysis."""
    analyzer = _HTMLAnalyzer()
    try:
        analyzer.feed(html)
    except Exception:  # noqa: BLE001
        pass
    return analyzer


# --- Slop detection patterns ---

_PLACEHOLDER_PATTERNS = re.compile(
    r"lorem ipsum|dolor sit amet|placeholder\.com|via\.placeholder|"
    r"unsplash\.com/photos/\w+|picsum\.photos|"
    r"example\.jpg|example\.png|image-placeholder|"
    r"your (?:company|brand|name|website|tagline) here|"
    r"insert .*? here|coming soon|todo:|fixme:|"
    r"sample text|dummy text|filler text",
    re.IGNORECASE,
)

_BROKEN_IMAGE_PATTERNS = re.compile(
    r"^data:image/svg\+xml|^#$|^javascript:|^about:blank|^\s*$",
    re.IGNORECASE,
)


def score_structure(analyzer: _HTMLAnalyzer) -> tuple[int, list[str]]:
    """Score semantic HTML structure (0-100)."""
    score = 0
    issues = []
    tc = analyzer.tag_counts

    # Has basic document structure
    if tc.get("html", 0) >= 1:
        score += 5
    if tc.get("head", 0) >= 1:
        score += 5
    if tc.get("body", 0) >= 1:
        score += 5

    # Semantic landmarks
    if tc.get("header", 0) >= 1 or tc.get("nav", 0) >= 1:
        score += 10
    else:
        issues.append("Missing header/nav element")

    if tc.get("main", 0) >= 1:
        score += 10
    elif tc.get("article", 0) >= 1:
        score += 5

    if tc.get("footer", 0) >= 1:
        score += 10
    else:
        issues.append("Missing footer element")

    # Content sections
    section_count = tc.get("section", 0) + tc.get("article", 0) + tc.get("div", 0)
    if section_count >= 5:
        score += 15
    elif section_count >= 3:
        score += 10
    elif section_count >= 1:
        score += 5
    else:
        issues.append("Very few content sections")

    # Heading hierarchy
    h_count = sum(tc.get(f"h{i}", 0) for i in range(1, 7))
    if tc.get("h1", 0) >= 1:
        score += 10
    else:
        issues.append("Missing h1 heading")
    if h_count >= 5:
        score += 10
    elif h_count >= 3:
        score += 5

    # Links
    if len(analyzer.link_hrefs) >= 3:
        score += 10
    elif len(analyzer.link_hrefs) >= 1:
        score += 5

    # Responsive meta
    if analyzer.has_viewport_meta:
        score += 10
    else:
        issues.append("Missing viewport meta tag")

    return min(score, 100), issues


def score_content_preservation(
    analyzer: _HTMLAnalyzer,
    original_headings: list[str],
    original_text: str,
) -> tuple[int, list[str]]:
    """Score how well original content was preserved (0-100)."""
    issues = []

    if not original_headings and not original_text:
        return 50, ["No original content to compare against"]

    score = 0
    generated_text = " ".join(analyzer.text_chunks).lower()

    # Check heading preservation
    if original_headings:
        matched = 0
        for heading in original_headings[:10]:  # Check top 10 headings
            # Fuzzy match: check if key words from heading appear
            words = [w for w in heading.lower().split() if len(w) > 3]
            if words and sum(1 for w in words if w in generated_text) >= len(words) * 0.5:
                matched += 1
        if original_headings:
            heading_ratio = matched / min(len(original_headings), 10)
            score += int(heading_ratio * 40)
            if heading_ratio < 0.3:
                issues.append(
                    f"Only {matched}/{min(len(original_headings), 10)} original headings preserved"
                )

    # Check key content words preservation
    if original_text:
        # Extract significant words from original (skip common words)
        orig_words = set(
            w
            for w in re.findall(r"\b\w{4,}\b", original_text.lower())
            if w
            not in {
                "this",
                "that",
                "with",
                "from",
                "your",
                "have",
                "been",
                "will",
                "more",
                "they",
                "their",
                "about",
                "what",
                "when",
                "which",
                "there",
                "would",
                "could",
                "should",
                "these",
                "those",
                "other",
                "some",
                "than",
                "then",
            }
        )
        if orig_words:
            gen_words = set(re.findall(r"\b\w{4,}\b", generated_text))
            overlap = len(orig_words & gen_words)
            ratio = overlap / len(orig_words) if orig_words else 0
            score += int(min(ratio * 2, 1.0) * 40)  # Cap at 40 points, generous threshold
            if ratio < 0.15:
                issues.append(f"Low content overlap: {ratio:.0%} of original words preserved")

    # Bonus: has meaningful text content (not mostly empty)
    if len(generated_text) > 500:
        score += 20
    elif len(generated_text) > 200:
        score += 10
    else:
        issues.append(f"Very little text content ({len(generated_text)} chars)")

    return min(score, 100), issues


def score_image_integrity(
    analyzer: _HTMLAnalyzer,
    original_images: list[dict],
) -> tuple[int, list[str]]:
    """Score image usage and integrity (0-100)."""
    issues = []
    img_srcs = analyzer.img_srcs

    if not img_srcs:
        if original_images:
            issues.append(f"Original had {len(original_images)} images, redesign has 0")
            return 10, issues
        return 50, ["No images in original or redesign"]

    score = 0
    total = len(img_srcs)
    broken = 0
    placeholder = 0
    real = 0

    for src in img_srcs:
        if _BROKEN_IMAGE_PATTERNS.match(src):
            broken += 1
        elif "placeholder" in src.lower() or "picsum" in src.lower():
            placeholder += 1
        elif src.startswith(("http://", "https://", "/")):
            real += 1
        else:
            broken += 1

    # Score based on ratio of real images
    if total > 0:
        real_ratio = real / total
        score += int(real_ratio * 50)

        if broken > 0:
            issues.append(f"{broken}/{total} images have broken/empty URLs")
        if placeholder > 0:
            issues.append(f"{placeholder}/{total} images use placeholder services")

    # Compare count with original
    if original_images:
        orig_count = len(original_images)
        if total >= orig_count * 0.5:
            score += 25
        elif total >= orig_count * 0.25:
            score += 15
        else:
            issues.append(f"Image count dropped significantly: {orig_count} → {total}")
            score += 5

        # Check if original image URLs are preserved
        orig_urls = {img.get("src", "") for img in original_images if img.get("src")}
        preserved = sum(1 for src in img_srcs if src in orig_urls)
        if orig_urls and preserved > 0:
            score += int((preserved / len(orig_urls)) * 25)
    else:
        # No original images — bonus for having any
        score += 25

    return min(score, 100), issues


def score_visual_richness(analyzer: _HTMLAnalyzer) -> tuple[int, list[str]]:
    """Score CSS sophistication and visual design (0-100)."""
    issues = []
    css = analyzer.style_content.lower()
    score = 0

    if not css:
        issues.append("No inline CSS found")
        return 5, issues

    # CSS length as proxy for sophistication
    css_len = len(css)
    if css_len > 10000:
        score += 15
    elif css_len > 5000:
        score += 10
    elif css_len > 1000:
        score += 5

    # Custom properties (design system)
    if "--" in css:
        custom_props = len(re.findall(r"--[\w-]+", css))
        if custom_props >= 10:
            score += 15
        elif custom_props >= 5:
            score += 10
        elif custom_props >= 1:
            score += 5

    # Responsive design
    media_queries = len(re.findall(r"@media", css))
    if media_queries >= 3:
        score += 15
    elif media_queries >= 1:
        score += 10
    else:
        issues.append("No @media queries — may not be responsive")

    # Gradients (visual depth)
    if "gradient" in css:
        score += 10

    # Shadows (depth)
    if "box-shadow" in css or "text-shadow" in css:
        score += 10

    # Transitions/animations
    anim_count = css.count("transition") + css.count("animation") + css.count("@keyframes")
    if anim_count >= 5:
        score += 15
    elif anim_count >= 2:
        score += 10
    elif anim_count >= 1:
        score += 5
    else:
        issues.append("No CSS transitions or animations")

    # Modern features
    if "grid" in css or "flexbox" in css or "flex" in css:
        score += 10

    # Google Fonts or custom fonts
    if "@import" in css or "font-face" in css or "fonts.googleapis" in css:
        score += 5

    return min(score, 100), issues


def score_interactivity(analyzer: _HTMLAnalyzer) -> tuple[int, list[str]]:
    """Score JavaScript interactivity (0-100)."""
    issues = []
    js = analyzer.script_content.lower()
    score = 0

    # Has any JS at all
    if not js:
        issues.append("No JavaScript — static page only")
        return 20, issues  # Static is OK but not great

    js_len = len(js)
    if js_len > 5000:
        score += 15
    elif js_len > 1000:
        score += 10
    else:
        score += 5

    # Scroll-based interactions
    if "intersectionobserver" in js or "scroll" in js:
        score += 20

    # Animation/counter logic
    if "animate" in js or "counter" in js or "setinterval" in js:
        score += 15

    # Mobile menu toggle
    if "toggle" in js or "classlist" in js:
        score += 15

    # Smooth scroll
    if "scrollinto" in js or "scrollto" in js or "smooth" in js:
        score += 10

    # Event listeners
    listener_count = js.count("addeventlistener") + js.count("onclick")
    if listener_count >= 3:
        score += 15
    elif listener_count >= 1:
        score += 10

    # DOM manipulation
    if "queryselector" in js or "getelementby" in js:
        score += 10

    return min(score, 100), issues


def score_anti_slop(analyzer: _HTMLAnalyzer) -> tuple[int, list[str]]:
    """Penalize AI-generated junk: placeholders, lorem ipsum, broken refs (0-100).

    100 = clean, no slop detected. 0 = full of junk.
    """
    issues = []
    all_text = " ".join(analyzer.text_chunks)
    score = 100  # Start at 100, deduct for problems

    # Check for placeholder text
    placeholder_matches = _PLACEHOLDER_PATTERNS.findall(all_text)
    if placeholder_matches:
        deduction = min(len(placeholder_matches) * 10, 40)
        score -= deduction
        unique = set(m.lower() for m in placeholder_matches[:5])
        issues.append(f"Placeholder text detected: {', '.join(unique)}")

    # Check for broken/empty links
    broken_links = sum(
        1 for href in analyzer.link_hrefs if href in ("#", "", "javascript:void(0)", "javascript:;")
    )
    if broken_links > 3:
        score -= 20
        issues.append(f"{broken_links} broken/empty links")
    elif broken_links > 0:
        score -= 10
        issues.append(f"{broken_links} broken/empty links")

    # Check for generic AI headlines
    ai_headlines = [
        "welcome to our website",
        "about our company",
        "our services",
        "get in touch",
        "contact us today",
    ]
    text_lower = all_text.lower()
    generic_count = sum(1 for h in ai_headlines if h in text_lower)
    # Only penalize if the original didn't have these
    if generic_count > 3:
        score -= 10
        issues.append("Multiple generic AI-style headings")

    # Check for empty sections (elements with no text children)
    if len(all_text) < 100 and analyzer.total_elements > 50:
        score -= 30
        issues.append("Many elements but very little text — likely invisible/empty sections")

    # Check for repeated dummy text
    if all_text.count("Portitor aptent") > 1 or all_text.count("Lorem") > 1:
        score -= 20
        issues.append("Repeated dummy/filler text blocks")

    return max(score, 0), issues


def score_redesign(
    html: str,
    original_headings: list[str] | None = None,
    original_text: str = "",
    original_images: list[dict] | None = None,
) -> QualityScore:
    """Score a redesign across all quality dimensions.

    Args:
        html: The generated HTML string.
        original_headings: Headings from the original CrawlResult.
        original_text: Text content from the original CrawlResult.
        original_images: Image list from the original CrawlResult.

    Returns:
        QualityScore with per-dimension scores and overall grade.
    """
    analyzer = _analyze_html(html)
    result = QualityScore()

    # Score each dimension
    result.structure, s_issues = score_structure(analyzer)
    result.content_preservation, c_issues = score_content_preservation(
        analyzer,
        original_headings or [],
        original_text,
    )
    result.image_integrity, i_issues = score_image_integrity(
        analyzer,
        original_images or [],
    )
    result.visual_richness, v_issues = score_visual_richness(analyzer)
    result.interactivity, x_issues = score_interactivity(analyzer)
    result.anti_slop, a_issues = score_anti_slop(analyzer)

    # Collect all issues
    result.issues = s_issues + c_issues + i_issues + v_issues + x_issues + a_issues

    # Weighted overall score
    result.overall = int(
        result.structure * 0.15
        + result.content_preservation * 0.25
        + result.image_integrity * 0.20
        + result.visual_richness * 0.15
        + result.interactivity * 0.10
        + result.anti_slop * 0.15
    )

    # Letter grade
    if result.overall >= 80:
        result.grade = "A"
    elif result.overall >= 65:
        result.grade = "B"
    elif result.overall >= 50:
        result.grade = "C"
    elif result.overall >= 35:
        result.grade = "D"
    else:
        result.grade = "F"

    # Log the result
    logger.info(
        "QUALITY SCORE | overall=%d grade=%s | structure=%d content=%d images=%d "
        "visual=%d interactivity=%d anti_slop=%d | issues=%d",
        result.overall,
        result.grade,
        result.structure,
        result.content_preservation,
        result.image_integrity,
        result.visual_richness,
        result.interactivity,
        result.anti_slop,
        len(result.issues),
    )
    for issue in result.issues:
        logger.info("QUALITY ISSUE | %s", issue)

    return result
