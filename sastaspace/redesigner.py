# sastaspace/redesigner.py
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from openai import OpenAI

from sastaspace.agents.pipeline import run_redesign_pipeline
from sastaspace.circuit_breaker import CircuitBreaker
from sastaspace.crawler import CrawlResult
from sastaspace.html_utils import (
    RedesignError,  # noqa: F401
    RedesignResult,  # noqa: F401
)
from sastaspace.html_utils import clean_html as _clean_html  # noqa: F401
from sastaspace.html_utils import validate_html as _validate_html  # noqa: F401

_logger = logging.getLogger(__name__)


# Module-level circuit breaker shared across all redesign calls
_circuit_breaker = CircuitBreaker(failure_threshold=5, reset_timeout=60.0)


@dataclass
class LLMConfig:
    """Configuration for the LLM API connection used in redesign calls."""

    api_url: str = "http://localhost:8000/v1"
    model: str = "claude-sonnet-4-5-20250929"
    api_key: str = "claude-code"
    max_tokens: int = 16000


if TYPE_CHECKING:
    # ProgressCallback matches the type alias in sastaspace.agents.pipeline
    ProgressCallback = Callable[[str, dict], None] | None

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


def _redesign_with_prompts(
    crawl_result: CrawlResult,
    system_prompt: str,
    user_template: str,
    llm: LLMConfig,
    crawl_context: str | None = None,
) -> str:
    """Internal: call the claude-code-api gateway with the given prompts.

    Args:
        crawl_context: Pre-built prompt context string. When provided, used instead of
            crawl_result.to_prompt_context(). Allows enhanced crawl data to feed through.

    Raises:
        RedesignError: if crawl_result.error is set or Claude's output is invalid.
    """
    if crawl_result.error:
        raise RedesignError(f"Cannot redesign — crawl failed: {crawl_result.error}")

    client = OpenAI(base_url=llm.api_url, api_key=llm.api_key)

    user_text = user_template.format(
        crawl_context=crawl_context
        if crawl_context is not None
        else crawl_result.to_prompt_context(),
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

    response = _circuit_breaker.call(
        client.chat.completions.create,
        model=llm.model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        max_tokens=llm.max_tokens,
    )

    raw = response.choices[0].message.content or ""
    html = _clean_html(raw)
    _validate_html(html)
    return html


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
    return _redesign_with_prompts(
        crawl_result,
        SYSTEM_PROMPT,
        USER_PROMPT_TEMPLATE,
        LLMConfig(api_url=api_url, model=model, api_key=api_key, max_tokens=16000),
    )


# ---------------------------------------------------------------------------
# Agno multi-agent pipeline redesign
# ---------------------------------------------------------------------------


def agno_redesign(
    crawl_result: CrawlResult,
    settings,
    tier: str = "free",
    progress_callback: Callable[[str, dict], None] | None = None,
    checkpoint: dict | None = None,
    checkpoint_callback: Callable[[str, dict], None] | None = None,
    model_provider: str = "claude",
    user_prompt: str = "",
) -> str:
    """Redesign using Agno multi-agent pipeline.

    Uses a sequential pipeline of specialized agents:
    CrawlAnalyst -> DesignStrategist -> HTMLGenerator -> QualityReviewer

    Args:
        crawl_result: The crawled website data.
        settings: Application settings (sastaspace.config.Settings).
        tier: Redesign tier (standard or premium).
        progress_callback: Optional callable(event, data) fired before each agent stage.
        checkpoint: Optional checkpoint dict to resume from.
        checkpoint_callback: Optional callable(step_name, checkpoint_data) fired after each step.

    Returns:
        The final redesigned HTML string.

    Raises:
        RedesignError: if crawl_result.error is set or pipeline fails.
    """
    result = run_redesign_pipeline(
        crawl_result,
        settings,
        progress_callback=progress_callback,
        tier=tier,
        checkpoint=checkpoint,
        checkpoint_callback=checkpoint_callback,
        model_provider=model_provider,
        user_prompt=user_prompt,
    )
    # Pipeline now returns RedesignResult
    if isinstance(result, RedesignResult):
        return result
    # Backwards compat: if somehow returns str
    return RedesignResult(html=result)


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
    return _redesign_with_prompts(
        crawl_result,
        PREMIUM_SYSTEM_PROMPT,
        PREMIUM_USER_PROMPT_TEMPLATE,
        LLMConfig(api_url=api_url, model=model, api_key=api_key, max_tokens=20000),
    )


# ---------------------------------------------------------------------------
# Unified redesign dispatcher
# ---------------------------------------------------------------------------


ENHANCED_SYSTEM_ADDENDUM = (
    "\n\nAdditional context — you have access to the business's actual assets:\n"
    "- You have access to the business's actual images. Use them. "
    "Never use placeholder URLs or stock photo services.\n"
    "- The business profile tells you who they are. "
    "Tailor the copy, layout, and emphasis to their industry and audience.\n"
    "- Use the primary CTA prominently — it's what the business wants visitors to do."
)


@dataclass
class RedesignOptions:
    """Groups pipeline control options for run_redesign to reduce parameter count."""

    tier: str = "free"
    progress_callback: Callable[[str, dict], None] | None = None
    checkpoint: dict | None = None
    checkpoint_callback: Callable[[str, dict], None] | None = None
    enhanced: object = None  # EnhancedCrawlResult | None
    model_provider: str = "claude"
    user_prompt: str = ""


def _run_agno_path(
    crawl_result: CrawlResult,
    settings,
    tier: str,
    progress_callback,
    checkpoint,
    checkpoint_callback,
    model_provider: str,
    user_prompt: str = "",
) -> RedesignResult:
    """Run the Agno multi-agent pipeline path."""
    result = agno_redesign(
        crawl_result,
        settings,
        tier,
        progress_callback,
        checkpoint,
        checkpoint_callback,
        model_provider=model_provider,
        user_prompt=user_prompt,
    )
    if isinstance(result, RedesignResult):
        return result
    return RedesignResult(html=result)


def _run_prompt_path(
    crawl_result: CrawlResult,
    settings,
    tier: str,
    enhanced,
    crawl_context: str | None,
) -> RedesignResult:
    """Run the direct prompt-based redesign path (premium or standard)."""
    if tier == "premium":
        system_prompt = PREMIUM_SYSTEM_PROMPT
        user_template = PREMIUM_USER_PROMPT_TEMPLATE
        max_tokens = 20000
    else:
        system_prompt = SYSTEM_PROMPT
        user_template = USER_PROMPT_TEMPLATE
        max_tokens = 16000

    if enhanced is not None:
        system_prompt += ENHANCED_SYSTEM_ADDENDUM

    llm = LLMConfig(
        api_url=settings.claude_code_api_url,
        model=settings.claude_model,
        api_key=settings.claude_code_api_key,
        max_tokens=max_tokens,
    )
    html = _redesign_with_prompts(
        crawl_result, system_prompt, user_template, llm, crawl_context=crawl_context
    )
    return RedesignResult(html=html)


def run_redesign(
    crawl_result: CrawlResult,
    settings,
    tier: str = "free",
    progress_callback: Callable[[str, dict], None] | None = None,
    checkpoint: dict | None = None,
    checkpoint_callback: Callable[[str, dict], None] | None = None,
    enhanced=None,  # EnhancedCrawlResult | None
    model_provider: str = "claude",
    *,
    options: RedesignOptions | None = None,
    user_prompt: str = "",
) -> RedesignResult:
    """Dispatch to the appropriate redesign function based on settings and tier.

    Accepts either individual keyword args (backward-compatible) or a single
    ``options`` RedesignOptions dataclass that groups the pipeline control
    parameters.

    Returns:
        RedesignResult with HTML and optional build directory.
    """
    if options is not None:
        tier = options.tier
        progress_callback = options.progress_callback
        checkpoint = options.checkpoint
        checkpoint_callback = options.checkpoint_callback
        enhanced = options.enhanced
        model_provider = options.model_provider
        user_prompt = options.user_prompt

    crawl_context = enhanced.to_prompt_context() if enhanced is not None else None

    if settings.use_agno_pipeline:
        return _run_agno_path(
            crawl_result,
            settings,
            tier,
            progress_callback,
            checkpoint,
            checkpoint_callback,
            model_provider,
            user_prompt=user_prompt,
        )

    return _run_prompt_path(crawl_result, settings, tier, enhanced, crawl_context)
