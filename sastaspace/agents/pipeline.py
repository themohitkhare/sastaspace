# sastaspace/agents/pipeline.py
"""Agno multi-agent redesign pipeline.

Sequential pipeline: CrawlAnalyst -> DesignStrategist -> HTMLGenerator -> QualityReviewer
With retry logic: if QualityReviewer fails, retry HTMLGenerator with feedback (max 2 retries).
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Callable

from agno.agent import Agent
from agno.models.openai import OpenAILike

from sastaspace.agents.metrics import (
    redesign_agent_duration_seconds,
    redesign_agent_tokens_total,
    redesign_guardrail_triggers_total,
    redesign_pipeline_duration_seconds,
    redesign_pipeline_total,
)
from sastaspace.agents.models import (
    ComponentSelection,
    CopywriterOutput,
    DesignBrief,
    QualityReport,
    SiteAnalysis,
)
from sastaspace.agents.prompts import (
    COMPONENT_SELECTOR_SYSTEM,
    COMPONENT_SELECTOR_USER_TEMPLATE,
    COPYWRITER_SYSTEM,
    COPYWRITER_USER_TEMPLATE,
    CRAWL_ANALYST_SYSTEM,
    CRAWL_ANALYST_USER_TEMPLATE,
    DESIGN_STRATEGIST_SYSTEM,
    DESIGN_STRATEGIST_USER_TEMPLATE,
    HTML_GENERATOR_SYSTEM,
    HTML_GENERATOR_USER_TEMPLATE,
    HTML_GENERATOR_USER_TEMPLATE_WITH_FEEDBACK,
    QUALITY_REVIEWER_SYSTEM,
    QUALITY_REVIEWER_USER_TEMPLATE,
)
from sastaspace.config import Settings
from sastaspace.crawler import CrawlResult
from sastaspace.redesigner import RedesignError, _clean_html, _validate_html

logger = logging.getLogger(__name__)

_RETRY_DELAYS = (5, 15, 30)  # seconds before each retry on empty response (rate limited)

ProgressCallback = Callable[[str, dict], None] | None

AGENT_MESSAGES: dict[str, dict] = {
    "crawl_analyst": {
        "message": "Analyzing your site's content and structure",
        "step_progress": 42,
    },
    "design_strategist": {"message": "Crafting your new design direction", "step_progress": 50},
    "copywriter": {"message": "Rewriting your copy for conversion", "step_progress": 57},
    "component_selector": {
        "message": "Selecting UI components for your industry",
        "step_progress": 63,
    },
    "html_generator": {"message": "Building your new page", "step_progress": 68},
    "quality_reviewer": {"message": "Reviewing design quality", "step_progress": 74},
    "normalizer": {"message": "Finalizing your redesign", "step_progress": 78},
}

MAX_QUALITY_RETRIES = 2


def _extract_json(text: str) -> dict:
    """Extract a JSON object from agent response text.

    Handles markdown fences, preamble text, and trailing text after the JSON.
    """
    text = text.strip()
    # Strip markdown code fences if present
    text = re.sub(r"^```(?:json)?\s*\n?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\n?```\s*$", "", text, flags=re.IGNORECASE)
    text = text.strip()
    # Find the first { to skip any preamble text the model may have added
    start = text.find("{")
    if start == -1:
        raise json.JSONDecodeError("No JSON object found", text, 0)
    # raw_decode parses the first valid JSON value and ignores any trailing text
    obj, _ = json.JSONDecoder().raw_decode(text, start)
    return obj


def _create_model(model_id: str, settings: Settings, *, use_ollama: bool = False) -> OpenAILike:
    """Create an Agno OpenAILike model instance.

    Args:
        model_id: The model identifier string.
        settings: Application settings with API credentials.
        use_ollama: If True, route to the local Ollama endpoint (free tier).
    """
    return OpenAILike(
        id=model_id,
        api_key=settings.ollama_api_key if use_ollama else settings.claude_code_api_key,
        base_url=settings.ollama_url if use_ollama else settings.claude_code_api_url,
    )


def _run_agent(
    name: str,
    system_prompt: str,
    user_prompt: str,
    model: OpenAILike,
) -> str:
    """Run a single agent and return the response content string."""
    start = time.monotonic()
    status = "success"
    input_tokens = 0
    output_tokens = 0

    # Log what we're sending
    prompt_len = len(user_prompt)
    system_len = len(system_prompt)
    logger.info(
        "AGENT START | agent=%s model=%s system_prompt_len=%d user_prompt_len=%d",
        name,
        model.id,
        system_len,
        prompt_len,
    )
    # Log first 200 chars of user prompt for context (truncated)
    logger.info(
        "AGENT INPUT | agent=%s prompt_preview=%.200s",
        name,
        user_prompt.replace("\n", " ")[:200],
    )

    try:
        content = ""
        for attempt, delay in enumerate([0, *_RETRY_DELAYS]):
            if delay:
                logger.warning(
                    "AGENT RETRY | agent=%s attempt=%d waiting=%ds (empty response — rate limit?)",
                    name,
                    attempt,
                    delay,
                )
                time.sleep(delay)
            agent = Agent(model=model, instructions=system_prompt, tools=[])
            response = agent.run(user_prompt)
            content = response.content or ""
            if content:
                break
        if not content:
            n = len(_RETRY_DELAYS) + 1
            raise RedesignError(f"{name} empty after {n} attempts — rate limit?")

        # Extract token metrics
        if response.metrics:
            if hasattr(response.metrics, "get"):
                input_tokens = response.metrics.get("input_tokens", 0)
                output_tokens = response.metrics.get("output_tokens", 0)
            elif hasattr(response.metrics, "input_tokens"):
                input_tokens = getattr(response.metrics, "input_tokens", 0) or 0
                output_tokens = getattr(response.metrics, "output_tokens", 0) or 0

            if input_tokens:
                redesign_agent_tokens_total.labels(agent_name=name, direction="input").inc(
                    input_tokens
                )
            if output_tokens:
                redesign_agent_tokens_total.labels(agent_name=name, direction="output").inc(
                    output_tokens
                )

        # Log response summary
        duration = time.monotonic() - start
        logger.info(
            "AGENT DONE | agent=%s status=success duration=%.1fs "
            "tokens_in=%d tokens_out=%d response_len=%d",
            name,
            duration,
            input_tokens,
            output_tokens,
            len(content),
        )
        # Log first 300 chars of response for debugging
        logger.info(
            "AGENT OUTPUT | agent=%s preview=%.300s",
            name,
            content.replace("\n", " ")[:300],
        )

        return content
    except Exception as exc:
        status = "error"
        duration = time.monotonic() - start
        logger.error(
            "AGENT FAILED | agent=%s error=%s duration=%.1fs",
            name,
            str(exc)[:200],
            duration,
        )
        raise
    finally:
        duration = time.monotonic() - start
        redesign_agent_duration_seconds.labels(agent_name=name, status=status).observe(duration)


def _run_crawl_analyst(
    crawl_result: CrawlResult, settings: Settings, tier: str = "premium"
) -> SiteAnalysis:
    """Run the CrawlAnalyst agent to produce a SiteAnalysis."""
    use_ollama = tier == "free"
    model_id = settings.free_crawl_analyst_model if use_ollama else settings.crawl_analyst_model
    model = _create_model(model_id, settings, use_ollama=use_ollama)
    user_prompt = CRAWL_ANALYST_USER_TEMPLATE.format(
        crawl_context=crawl_result.to_prompt_context(),
        title=crawl_result.title,
        meta_description=crawl_result.meta_description,
        colors=", ".join(crawl_result.colors[:10]) or "not detected",
        fonts=", ".join(crawl_result.fonts[:5]) or "not detected",
    )
    raw = _run_agent("crawl_analyst", CRAWL_ANALYST_SYSTEM, user_prompt, model)
    try:
        data = _extract_json(raw)
        result = SiteAnalysis.model_validate(data)
        logger.info(
            "AGENT RESULT | agent=crawl_analyst brand=%s goal=%s audience=%s sections=%d",
            result.brand.name,
            result.primary_goal,
            result.target_audience[:50],
            len(result.content_sections),
        )
        return result
    except (json.JSONDecodeError, ValueError) as exc:
        redesign_guardrail_triggers_total.labels(guardrail_name="json_parse", action="fail").inc()
        if raw:
            logger.error(
                "PARSE FAIL | agent=crawl_analyst full_content=%.500s", raw.replace("\n", " ")
            )
        raise RedesignError(f"CrawlAnalyst returned invalid JSON: {exc}") from exc


def _run_design_strategist(
    site_analysis: SiteAnalysis,
    crawl_result: CrawlResult,
    settings: Settings,
    tier: str = "premium",
) -> DesignBrief:
    """Run the DesignStrategist agent to produce a DesignBrief."""
    use_ollama = tier == "free"
    model_id = (
        settings.free_design_strategist_model if use_ollama else settings.design_strategist_model
    )
    model = _create_model(model_id, settings, use_ollama=use_ollama)
    user_prompt = DESIGN_STRATEGIST_USER_TEMPLATE.format(
        site_analysis_json=site_analysis.model_dump_json(indent=2),
        colors=", ".join(crawl_result.colors[:10]) or "not detected",
        fonts=", ".join(crawl_result.fonts[:5]) or "not detected",
    )
    raw = _run_agent("design_strategist", DESIGN_STRATEGIST_SYSTEM, user_prompt, model)
    try:
        data = _extract_json(raw)
        result = DesignBrief.model_validate(data)
        logger.info(
            "AGENT RESULT | agent=design_strategist direction=%s colors=%s/%s "
            "fonts=%s/%s components=%d",
            result.design_direction[:50],
            result.colors.primary,
            result.colors.accent,
            result.typography.heading_font,
            result.typography.body_font,
            len(result.components),
        )
        return result
    except (json.JSONDecodeError, ValueError) as exc:
        redesign_guardrail_triggers_total.labels(guardrail_name="json_parse", action="fail").inc()
        if raw:
            logger.error(
                "PARSE FAIL | agent=design_strategist full_content=%.500s", raw.replace("\n", " ")
            )
        raise RedesignError(f"DesignStrategist returned invalid JSON: {exc}") from exc


def _run_copywriter(
    site_analysis: SiteAnalysis,
    design_brief: DesignBrief,
    settings: Settings,
    tier: str = "premium",
) -> CopywriterOutput:
    """Run the Copywriter agent to produce conversion-optimized copy."""
    use_ollama = tier == "free"
    model_id = settings.free_copywriter_model if use_ollama else settings.design_strategist_model
    model = _create_model(model_id, settings, use_ollama=use_ollama)

    # Format content sections for the copywriter
    sections_text = (
        "\n".join(
            f"### {s.heading or s.content_type}\n{s.content_summary}"
            for s in site_analysis.content_sections
        )
        or "No sections extracted"
    )

    user_prompt = COPYWRITER_USER_TEMPLATE.format(
        brand_name=site_analysis.brand.name or "Unknown",
        industry=site_analysis.brand.industry or "Unknown",
        primary_goal=site_analysis.primary_goal or "conversion",
        target_audience=site_analysis.target_audience or "general",
        brand_voice=site_analysis.brand.voice_tone or "professional",
        content_sections=sections_text,
        conversion_strategy=design_brief.conversion_strategy,
        key_ctas=", ".join(design_brief.animations[:3]) if design_brief.animations else "N/A",
    )
    raw = _run_agent("copywriter", COPYWRITER_SYSTEM, user_prompt, model)
    try:
        data = _extract_json(raw)
        copy = CopywriterOutput.model_validate(data)
        logger.info("Copywriter produced headline: %s", copy.headline[:50])
        return copy
    except (json.JSONDecodeError, ValueError) as exc:
        if raw:
            logger.error(
                "PARSE FAIL | agent=copywriter full_content=%.500s", raw.replace("\n", " ")
            )
        logger.warning("Copywriter returned invalid JSON, continuing without: %s", exc)
        return CopywriterOutput()


def _prefilter_catalog(catalog_json: str, site_analysis: SiteAnalysis) -> str:
    """Pre-filter the component catalog based on site type to reduce context size."""
    import json as _json

    try:
        catalog = _json.loads(catalog_json)
    except _json.JSONDecodeError:
        return catalog_json

    # Determine relevant categories based on site analysis
    goal = (site_analysis.primary_goal or "").lower()
    industry = (site_analysis.brand.industry or "").lower()
    section_types = {s.content_type.lower() for s in site_analysis.content_sections}

    # Always include these core categories
    relevant = {"heroes", "calls-to-action", "footers", "navigation-menus"}

    # Add based on content
    if any(t in section_types for t in ("testimonials", "reviews")):
        relevant.add("testimonials")
        relevant.add("clients")
    if any(t in section_types for t in ("features", "services")):
        relevant.add("features")
        relevant.add("cards")
    if any(t in section_types for t in ("pricing", "plans")):
        relevant.add("pricing-sections")
    if "saas" in goal or "software" in industry or "tech" in industry:
        relevant.update({"features", "pricing-sections", "clients", "comparisons"})
    if "ecommerce" in goal or "shop" in industry:
        relevant.update({"cards", "testimonials"})

    # Always include backgrounds and announcements (small, high impact)
    relevant.update({"backgrounds", "announcements"})

    filtered = {k: v for k, v in catalog.items() if k in relevant}
    return _json.dumps(filtered, indent=1)


def _run_component_selector(
    site_analysis: SiteAnalysis,
    design_brief: DesignBrief,
    settings: Settings,
    tier: str = "premium",
) -> ComponentSelection:
    """Run the ComponentSelector agent to pick the best UI components."""
    import os

    use_ollama = tier == "free"
    model_id = (
        settings.free_component_selector_model if use_ollama else settings.design_strategist_model
    )
    model = _create_model(model_id, settings, use_ollama=use_ollama)

    # Load the marketing component catalog
    catalog_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "components", "marketing-catalog.json"
    )
    try:
        with open(catalog_path) as f:
            raw_catalog = f.read()
        # Pre-filter catalog based on site type to reduce context
        catalog = _prefilter_catalog(raw_catalog, site_analysis)
        logger.info("Pre-filtered catalog for component selection")
    except FileNotFoundError:
        logger.warning(
            "Component catalog not found at %s, skipping component selection", catalog_path
        )
        return ComponentSelection(strategy="No catalog available")

    user_prompt = COMPONENT_SELECTOR_USER_TEMPLATE.format(
        brand_name=site_analysis.brand.name or "Unknown",
        industry=site_analysis.brand.industry or "Unknown",
        primary_goal=site_analysis.primary_goal or "conversion",
        target_audience=site_analysis.target_audience or "general",
        section_count=len(site_analysis.content_sections),
        strengths=", ".join(site_analysis.strengths[:5]) or "N/A",
        weaknesses=", ".join(site_analysis.weaknesses[:5]) or "N/A",
        design_direction=design_brief.design_direction,
        primary_color=design_brief.colors.primary,
        accent_color=design_brief.colors.accent,
        heading_font=design_brief.typography.heading_font,
        body_font=design_brief.typography.body_font,
        layout_strategy=design_brief.layout_strategy,
        conversion_strategy=design_brief.conversion_strategy,
        component_catalog=catalog,
    )
    raw = _run_agent("component_selector", COMPONENT_SELECTOR_SYSTEM, user_prompt, model)
    try:
        data = _extract_json(raw)
        selection = ComponentSelection.model_validate(data)
        logger.info(
            "ComponentSelector selected %d components: %s",
            len(selection.selected),
            ", ".join(c.name for c in selection.selected),
        )
        return selection
    except (json.JSONDecodeError, ValueError) as exc:
        if raw:
            logger.error(
                "PARSE FAIL | agent=component_selector full_content=%.500s",
                raw.replace("\n", " "),
            )
        logger.warning("ComponentSelector returned invalid JSON, continuing without: %s", exc)
        return ComponentSelection(strategy="Parse failed, continuing without components")


def _load_component_source(file_path: str) -> str:
    """Load the source code from a component JSON file."""
    import os

    full_path = os.path.join(os.path.dirname(__file__), "..", "..", "components", file_path)
    try:
        with open(full_path) as f:
            data = json.load(f)
        # Extract source from files[].content
        sources = []
        for file_entry in data.get("files", []):
            content = file_entry.get("content", "")
            if content:
                sources.append(f"// File: {file_entry.get('path', 'unknown')}\n{content}")
        return "\n\n".join(sources) if sources else ""
    except (FileNotFoundError, json.JSONDecodeError):
        return ""


def _run_html_generator(
    design_brief: DesignBrief,
    crawl_result: CrawlResult,
    settings: Settings,
    quality_feedback: str = "",
    component_selection: ComponentSelection | None = None,
    copywriter_output: CopywriterOutput | None = None,
    tier: str = "premium",
) -> str:
    """Run the HTMLGenerator agent to produce HTML."""
    use_ollama = tier == "free"
    model_id = settings.free_html_generator_model if use_ollama else settings.html_generator_model
    model = _create_model(model_id, settings, use_ollama=use_ollama)

    feedback_section = ""
    if quality_feedback:
        feedback_section = HTML_GENERATOR_USER_TEMPLATE_WITH_FEEDBACK.format(
            feedback=quality_feedback,
        )

    # Load selected component source code
    component_context = ""
    if component_selection and component_selection.selected:
        comp_sources = []
        for comp in component_selection.selected:
            source = _load_component_source(comp.file)
            if source:
                comp_sources.append(
                    f"### Component: {comp.name} ({comp.category})\n"
                    f"Rationale: {comp.rationale}\n"
                    f"Source code:\n```tsx\n{source[:3000]}\n```"
                )
        if comp_sources:
            component_context = (
                "\n\n## Reference UI Components (adapt these patterns for the HTML output)\n"
                + "\n\n".join(comp_sources)
            )

    # Add copywriter-optimized copy
    copy_context = ""
    if copywriter_output and copywriter_output.headline:
        copy_sections = "\n".join(
            f'- {s.section_type}: "{s.new_heading}" — {s.new_body[:200]}'
            for s in copywriter_output.sections
        )
        copy_context = (
            f"\n\n## Optimized Copy (USE THIS TEXT instead of generic placeholders)\n"
            f'Headline: "{copywriter_output.headline}"\n'
            f'Subheadline: "{copywriter_output.subheadline}"\n'
            f'Primary CTA: "{copywriter_output.cta_primary.text}"\n'
            f'Secondary CTA: "{copywriter_output.cta_secondary.text}"\n'
            f"Sections:\n{copy_sections}\n"
            f'Meta title: "{copywriter_output.meta_title}"\n'
        )

    user_prompt = (
        HTML_GENERATOR_USER_TEMPLATE.format(
            design_brief_json=design_brief.model_dump_json(indent=2),
            crawl_context=crawl_result.to_prompt_context(),
            title=crawl_result.title,
            meta_description=crawl_result.meta_description,
            quality_feedback=feedback_section,
        )
        + copy_context
        + component_context
    )
    raw = _run_agent("html_generator", HTML_GENERATOR_SYSTEM, user_prompt, model)
    html = _clean_html(raw)
    _validate_html(html)
    has_doctype = "<!doctype" in html.lower()
    has_style = "<style" in html.lower()
    has_media = "@media" in html.lower()
    logger.info(
        "AGENT RESULT | agent=html_generator html_len=%d has_doctype=%s "
        "has_style=%s has_media_queries=%s",
        len(html),
        has_doctype,
        has_style,
        has_media,
    )
    return html


def _run_quality_reviewer(
    html: str,
    design_brief: DesignBrief,
    site_analysis: SiteAnalysis,
    settings: Settings,
    tier: str = "premium",
) -> QualityReport:
    """Run the QualityReviewer agent to evaluate the HTML."""
    use_ollama = tier == "free"
    model_id = (
        settings.free_quality_reviewer_model if use_ollama else settings.quality_reviewer_model
    )
    model = _create_model(model_id, settings, use_ollama=use_ollama)
    html_lower = html.lower()

    user_prompt = QUALITY_REVIEWER_USER_TEMPLATE.format(
        design_brief_json=design_brief.model_dump_json(indent=2),
        title=site_analysis.brand.name or "Unknown",
        section_count=len(site_analysis.content_sections),
        key_content_preview=(
            site_analysis.key_content[:200] if site_analysis.key_content else "N/A"
        ),
        html_preview=html[:16000],
        html_length=len(html),
        has_doctype="<!doctype html" in html_lower,
        has_closing_html="</html>" in html_lower,
        has_style="<style" in html_lower,
        has_google_fonts="@import" in html_lower,
        has_media_queries="@media" in html_lower,
        has_custom_properties="--" in html,
    )
    raw = _run_agent("quality_reviewer", QUALITY_REVIEWER_SYSTEM, user_prompt, model)
    try:
        data = _extract_json(raw)
        result = QualityReport.model_validate(data)
        issues_summary = ", ".join(f"[{i.severity}]{i.description[:40]}" for i in result.issues[:5])
        logger.info(
            "AGENT RESULT | agent=quality_reviewer passed=%s score=%d issues=%d details=%s",
            result.passed,
            result.overall_score,
            len(result.issues),
            issues_summary[:200] or "none",
        )
        return result
    except (json.JSONDecodeError, ValueError) as exc:
        redesign_guardrail_triggers_total.labels(guardrail_name="json_parse", action="fail").inc()
        if raw:
            logger.error(
                "PARSE FAIL | agent=quality_reviewer full_content=%.500s", raw.replace("\n", " ")
            )
        logger.warning("QualityReviewer returned invalid JSON, assuming pass: %s", exc)
        return QualityReport(passed=True, overall_score=7, strengths=["Could not parse review"])


def _run_normalizer(
    html: str, design_brief: DesignBrief, settings: Settings, tier: str = "premium"
) -> str:
    """Normalize the HTML for cohesive design + apply premium psychology principles.

    Combines two concepts:
    1. ANF "Normalize" — unify typography, colors, spacing from assembled components
    2. Premium Psychology — engineer the halo effect, reduce cognitive load, add micro-interactions
    """
    from sastaspace.agents.prompts import NORMALIZER_SYSTEM, NORMALIZER_USER_TEMPLATE

    use_ollama = tier == "free"
    model_id = settings.free_html_generator_model if use_ollama else settings.html_generator_model
    model = _create_model(model_id, settings, use_ollama=use_ollama)

    user_prompt = NORMALIZER_USER_TEMPLATE.format(
        heading_font=design_brief.typography.heading_font,
        body_font=design_brief.typography.body_font,
        primary_color=design_brief.colors.primary,
        accent_color=design_brief.colors.accent,
        background_color=design_brief.colors.background,
        html=html,
    )
    raw = _run_agent("normalizer", NORMALIZER_SYSTEM, user_prompt, model)
    normalized = _clean_html(raw)

    try:
        _validate_html(normalized)
        return normalized
    except RedesignError:
        logger.warning("Normalizer output invalid, keeping original HTML")
        return html


def run_redesign_pipeline(
    crawl_result: CrawlResult,
    settings: Settings,
    progress_callback: ProgressCallback = None,
    tier: str = "premium",
) -> str:
    """
    Execute the full Agno multi-agent redesign pipeline.

    Pipeline: CrawlAnalyst -> DesignStrategist -> HTMLGenerator -> QualityReviewer
    With retry: if quality review fails, retry HTMLGenerator with feedback (max 2 retries).

    Args:
        crawl_result: The crawled website data.
        settings: Application settings with model config.
        progress_callback: Optional callable(event, data) fired before each agent stage.
        tier: Redesign tier — "free" (Ollama) or "premium" (Claude).

    Returns:
        The final redesigned HTML string.

    Raises:
        RedesignError: If the pipeline fails.
    """

    def _emit(agent_name: str) -> None:
        if progress_callback is None:
            return
        meta = AGENT_MESSAGES.get(agent_name, {"message": agent_name, "step_progress": 50})
        try:
            progress_callback(
                "agent_activity",
                {
                    "agent": agent_name,
                    "message": meta["message"],
                    "step_progress": meta["step_progress"],
                },
            )
        except Exception:
            pass  # never let UI callback crash the pipeline

    if crawl_result.error:
        raise RedesignError(f"Cannot redesign — crawl failed: {crawl_result.error}")

    pipeline_start = time.monotonic()
    status = "success"

    try:
        # Step 1: Crawl Analyst
        logger.info("Pipeline step 1/7: CrawlAnalyst (tier=%s)", tier)
        _emit("crawl_analyst")
        site_analysis = _run_crawl_analyst(crawl_result, settings, tier)

        # Step 2: Design Strategist
        logger.info("Pipeline step 2/7: DesignStrategist (tier=%s)", tier)
        _emit("design_strategist")
        design_brief = _run_design_strategist(site_analysis, crawl_result, settings, tier)

        # Step 3: Copywriter — writes conversion-optimized copy
        logger.info("Pipeline step 3/7: Copywriter (tier=%s)", tier)
        _emit("copywriter")
        copywriter_output = _run_copywriter(site_analysis, design_brief, settings, tier)

        # Step 4: Component Selector — picks best UI components for this business
        logger.info("Pipeline step 4/7: ComponentSelector (tier=%s)", tier)
        _emit("component_selector")
        component_selection = _run_component_selector(site_analysis, design_brief, settings, tier)

        # Step 5 & 6: HTMLGenerator + QualityReviewer with retry loop
        html = ""
        quality_report = None
        quality_feedback = ""

        for attempt in range(1, MAX_QUALITY_RETRIES + 2):  # max retries + 1 initial
            logger.info(
                "Pipeline step 5/7: HTMLGenerator (attempt %d/%d)",
                attempt,
                MAX_QUALITY_RETRIES + 1,
            )
            _emit("html_generator")
            html = _run_html_generator(
                design_brief,
                crawl_result,
                settings,
                quality_feedback,
                component_selection,
                copywriter_output,
                tier,
            )

            logger.info("Pipeline step 6/7: QualityReviewer (attempt %d)", attempt)
            _emit("quality_reviewer")
            quality_report = _run_quality_reviewer(
                html, design_brief, site_analysis, settings, tier
            )

            if quality_report.passed:
                logger.info(
                    "Quality review passed (score=%d) on attempt %d",
                    quality_report.overall_score,
                    attempt,
                )
                break

            if attempt <= MAX_QUALITY_RETRIES:
                quality_feedback = quality_report.feedback_for_regeneration
                issues_text = "; ".join(
                    f"[{i.severity}] {i.description}" for i in quality_report.issues
                )
                logger.warning(
                    "Quality review failed (score=%d), retrying: %s",
                    quality_report.overall_score,
                    issues_text,
                )
                redesign_guardrail_triggers_total.labels(
                    guardrail_name="quality_review", action="retry"
                ).inc()
            else:
                logger.warning(
                    "Quality review failed after %d attempts (score=%d), using last HTML",
                    MAX_QUALITY_RETRIES + 1,
                    quality_report.overall_score,
                )
                redesign_guardrail_triggers_total.labels(
                    guardrail_name="quality_review", action="accept_low_quality"
                ).inc()

        # Step 7: Normalizer — ensure cohesive design
        logger.info("Pipeline step 7/7: Normalizer (tier=%s)", tier)
        _emit("normalizer")
        html = _run_normalizer(html, design_brief, settings, tier)

        return html

    except RedesignError:
        status = "failure"
        raise
    except Exception as exc:
        status = "failure"
        raise RedesignError(f"Agno pipeline failed: {exc}") from exc
    finally:
        duration = time.monotonic() - pipeline_start
        redesign_pipeline_duration_seconds.labels(tier=tier, status=status).observe(duration)
        redesign_pipeline_total.labels(tier=tier, status=status).inc()
        logger.info("Pipeline completed in %.1fs (status=%s)", duration, status)
