# sastaspace/redesigner.py
from __future__ import annotations

import re

from openai import OpenAI

from sastaspace.crawler import CrawlResult

SYSTEM_PROMPT = """You are SastaSpace AI — the world's best website redesigner.

Design Principles:
1. Modern & Clean — generous whitespace, clear typography, subtle shadows, smooth gradients
2. Preserve Content — keep ALL original text, links, messaging. Don't invent copy.
3. Preserve Brand — use original color palette (improve subtly). Keep personality.
4. Mobile-First — fully responsive design
5. Performance — single HTML file, inline CSS, no external deps except Google Fonts
6. Professional — output should look like a $5,000 website

Technical Requirements:
- Single complete HTML file with all CSS in a <style> tag
- Google Fonts via @import (1-2 fonts max)
- CSS Grid + Flexbox for layout
- Smooth scroll, subtle animations (fade-in, hover effects)
- Responsive hamburger menu for mobile
- Semantic HTML5 (header, nav, main, section, footer)
- CSS custom properties for theming
- Keep original image URLs from source site
- Include a "Redesigned by SastaSpace.com" badge in footer with link

Do NOT:
- Add fake content not on the original site
- Use Bootstrap, Tailwind CDN, or any CSS framework
- Use external JS libraries
- Output anything except the raw HTML"""

USER_PROMPT_TEMPLATE = """Redesign this website into a modern, beautiful single-page HTML file.

## Original Website Data:
{crawl_context}

## Original Page Title: {title}
## Original Meta Description: {meta_description}
## Detected Color Palette: {colors}
## Detected Fonts: {fonts}

Instructions:
1. Analyze the content structure from the screenshot and extracted data
2. Create a complete modern redesign as a SINGLE HTML file
3. Keep all original content but reorganize it beautifully
4. Output ONLY the HTML code — no explanations, just raw HTML starting with <!DOCTYPE html>"""


class RedesignError(Exception):
    """Raised when Claude returns invalid or unexpected output."""


def _clean_html(raw: str) -> str:
    """Strip markdown code fences and leading/trailing whitespace."""
    raw = raw.strip()
    raw = re.sub(r"^```(?:html)?\s*\n?", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\n?```\s*$", "", raw, flags=re.IGNORECASE)
    return raw.strip()


def _validate_html(html: str) -> None:
    """Raise RedesignError if the HTML looks truncated or malformed."""
    if not html:
        raise RedesignError("Claude returned an empty response")
    if "<!doctype html" not in html.lower():
        raise RedesignError(
            "Response missing <!DOCTYPE html> declaration — output may not be valid HTML"
        )
    if "</html>" not in html.lower():
        raise RedesignError("Response missing closing </html> tag — output appears to be truncated")


def redesign(
    crawl_result: CrawlResult,
    api_url: str = "http://localhost:8000/v1",
    model: str = "claude-sonnet-4-5-20250929",
    api_key: str = "claude-code",
) -> str:
    """
    Use the claude-code-api gateway to redesign a crawled website into a single HTML file.

    Raises:
        RedesignError: if crawl_result.error is set or Claude's output is invalid.
    """
    if crawl_result.error:
        raise RedesignError(f"Cannot redesign — crawl failed: {crawl_result.error}")

    client = OpenAI(base_url=api_url, api_key=api_key)

    user_text = USER_PROMPT_TEMPLATE.format(
        crawl_context=crawl_result.to_prompt_context(),
        title=crawl_result.title,
        meta_description=crawl_result.meta_description,
        colors=", ".join(crawl_result.colors[:10]) or "not detected",
        fonts=", ".join(crawl_result.fonts[:5]) or "not detected",
    )

    user_content: list = []
    if crawl_result.screenshot_base64:
        user_content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{crawl_result.screenshot_base64}"},
            }
        )
    user_content.append({"type": "text", "text": user_text})

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        max_tokens=16000,
    )

    raw = response.choices[0].message.content or ""
    html = _clean_html(raw)
    _validate_html(html)
    return html


# ---------------------------------------------------------------------------
# Agno multi-agent pipeline redesign
# ---------------------------------------------------------------------------


def agno_redesign(crawl_result: CrawlResult, settings, tier: str = "standard") -> str:
    """Redesign using Agno multi-agent pipeline.

    Uses a sequential pipeline of specialized agents:
    CrawlAnalyst -> DesignStrategist -> HTMLGenerator -> QualityReviewer

    Args:
        crawl_result: The crawled website data.
        settings: Application settings (sastaspace.config.Settings).

    Returns:
        The final redesigned HTML string.

    Raises:
        RedesignError: if crawl_result.error is set or pipeline fails.
    """
    from sastaspace.agents.pipeline import run_redesign_pipeline

    return run_redesign_pipeline(crawl_result, settings)


# ---------------------------------------------------------------------------
# Premium redesign — sales psychology & conversion-optimized
# ---------------------------------------------------------------------------

PREMIUM_SYSTEM_PROMPT = """You are SastaSpace AI Premium — an elite website redesigner who combines
world-class web design with deep expertise in sales psychology, conversion rate optimization,
and neuromarketing.

## Your Dual Expertise

**Design Mastery:**
1. Modern & Clean — generous whitespace, clear typography, subtle shadows, smooth gradients
2. Preserve Content — keep ALL original text, links, messaging. Don't invent copy.
3. Preserve Brand — use original color palette (improve subtly). Keep personality.
4. Mobile-First — fully responsive design
5. Performance — single HTML file, inline CSS, no external deps except Google Fonts
6. Professional — output should look like a $10,000+ premium website

**Sales & Conversion Psychology (apply ALL of these):**

1. **Visual Hierarchy & F-Pattern/Z-Pattern Layout**
   - Guide the eye through headline → subheadline → key benefit → CTA using size, color, contrast
   - Place the most important CTA above the fold in the primary visual path
   - Use the Gestalt principles (proximity, similarity, continuity) to group related elements

2. **Color Psychology**
   - Use the brand's existing palette but optimize emotional impact
   - Warm colors (orange, red) for urgency and CTAs
   - Cool colors (blue, green) for trust and credibility sections
   - High contrast between background and CTA buttons (minimum 4.5:1 ratio)

3. **Social Proof & Authority Signals**
   - If testimonials exist, make them visually prominent with photos, names, and titles
   - If logos/partner badges exist, create a trust bar near the top
   - If numbers/stats exist, make them large and bold with counter-style presentation

4. **Cognitive Biases to Leverage**
   - **Anchoring**: If pricing exists, show the highest tier first or crossed-out original price
   - **Scarcity/Urgency**: Subtly emphasize limited-time aspects if they exist in the content
   - **Loss Aversion**: Frame benefits as "Don't miss out" rather than "Get access"
   - **Halo Effect**: Make the overall design so polished that every element feels premium
   - **Von Restorff Effect**: Make CTAs and key offers visually distinct from everything else

5. **Micro-Interactions & Engagement**
   - Subtle hover effects on interactive elements (scale, color shift, shadow lift)
   - Smooth scroll behavior with CSS scroll-snap for section-based layouts
   - Fade-in animations on scroll for content sections (CSS-only, using @keyframes)
   - Button hover states that feel tactile (slight scale + shadow change)

6. **Typography for Persuasion**
   - Headlines: Bold, large, high-contrast — emotionally compelling
   - Body: Readable, comfortable line-height (1.6+), max-width 70ch
   - Use font weight and size variation to create clear information hierarchy
   - Serif fonts for authority/tradition, Sans-serif for modern/clean

7. **Whitespace as a Selling Tool**
   - Generous padding around CTAs to draw attention (isolation effect)
   - Section spacing that creates breathing room and prevents cognitive overload
   - Empty space signals premium quality and confidence

8. **CTA Optimization**
   - Action-oriented button text (keep original text but style prominently)
   - High-contrast, rounded buttons with generous padding
   - Primary CTA should be the most visually dominant element on the page
   - Sticky header with CTA for long pages

Technical Requirements:
- Single complete HTML file with all CSS in a <style> tag
- Google Fonts via @import (2-3 fonts for hierarchy)
- CSS Grid + Flexbox for layout
- CSS scroll-snap for section navigation
- @keyframes animations for scroll reveals (IntersectionObserver via inline JS OK)
- Responsive hamburger menu for mobile
- Semantic HTML5 (header, nav, main, section, footer)
- CSS custom properties for theming
- Keep original image URLs from source site
- Include a "Premium Redesign by SastaSpace.com" badge in footer with link
- Minimal inline JavaScript is allowed for scroll animations and mobile menu toggle

Do NOT:
- Add fake content, testimonials, or stats not on the original site
- Use Bootstrap, Tailwind CDN, or any CSS framework
- Use external JS libraries (jQuery, GSAP, etc.)
- Output anything except the raw HTML"""

PREMIUM_USER_PROMPT_TEMPLATE = """Create a PREMIUM conversion-optimized redesign of this website.

## Sales & Marketing Analysis:
Before redesigning, mentally analyze the site's:
- **Value Proposition**: What is the core offer? How can the layout make it instantly clear?
- **Target Audience**: Who visits this site? What emotional triggers matter to them?
- **Conversion Goals**: What action should visitors take? (buy, sign up, contact, etc.)
- **Trust Signals**: What existing credibility elements can be amplified?
- **Content Flow**: What's the ideal narrative arc from awareness → interest → desire → action?

## Original Website Data:
{crawl_context}

## Original Page Title: {title}
## Original Meta Description: {meta_description}
## Detected Color Palette: {colors}
## Detected Fonts: {fonts}

## Premium Redesign Instructions:
1. Analyze the screenshot and data through a sales psychology lens
2. Identify the primary conversion goal and optimize the entire layout around it
3. Apply visual hierarchy, color psychology, and cognitive biases listed in your system prompt
4. Create a SINGLE HTML file with premium design quality
5. Ensure every section serves the conversion funnel: Attention → Interest → Desire → Action
6. Make CTAs impossible to miss — high contrast, generous whitespace, sticky header
7. Add scroll-reveal animations for engagement (CSS @keyframes + minimal inline JS)
8. Output ONLY the HTML code — no explanations, just raw HTML starting with <!DOCTYPE html>"""


def redesign_premium(
    crawl_result: CrawlResult,
    api_url: str = "http://localhost:8000/v1",
    model: str = "claude-sonnet-4-5-20250929",
    api_key: str = "claude-code",
) -> str:
    """
    Premium redesign with sales psychology, neuromarketing, and conversion optimization.

    Uses enhanced prompts that guide Claude to apply cognitive biases,
    color psychology, visual hierarchy, and CRO best practices.

    Raises:
        RedesignError: if crawl_result.error is set or Claude's output is invalid.
    """
    if crawl_result.error:
        raise RedesignError(f"Cannot redesign — crawl failed: {crawl_result.error}")

    client = OpenAI(base_url=api_url, api_key=api_key)

    user_text = PREMIUM_USER_PROMPT_TEMPLATE.format(
        crawl_context=crawl_result.to_prompt_context(),
        title=crawl_result.title,
        meta_description=crawl_result.meta_description,
        colors=", ".join(crawl_result.colors[:10]) or "not detected",
        fonts=", ".join(crawl_result.fonts[:5]) or "not detected",
    )

    user_content: list = []
    if crawl_result.screenshot_base64:
        user_content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{crawl_result.screenshot_base64}"},
            }
        )
    user_content.append({"type": "text", "text": user_text})

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": PREMIUM_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        max_tokens=20000,
    )

    raw = response.choices[0].message.content or ""
    html = _clean_html(raw)
    _validate_html(html)
    return html
