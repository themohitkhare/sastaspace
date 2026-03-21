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
    DesignBrief,
    QualityReport,
    SiteAnalysis,
)
from sastaspace.agents.prompts import (
    COMPONENT_SELECTOR_SYSTEM,
    COMPONENT_SELECTOR_USER_TEMPLATE,
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

MAX_QUALITY_RETRIES = 2


def _extract_json(text: str) -> dict:
    """Extract a JSON object from agent response text, handling markdown fences."""
    text = text.strip()
    # Strip markdown code fences if present
    text = re.sub(r"^```(?:json)?\s*\n?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\n?```\s*$", "", text, flags=re.IGNORECASE)
    text = text.strip()
    return json.loads(text)


def _create_model(model_id: str, settings: Settings) -> OpenAILike:
    """Create an Agno OpenAILike model instance."""
    return OpenAILike(
        id=model_id,
        api_key=settings.claude_code_api_key,
        base_url=settings.claude_code_api_url,
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
    try:
        agent = Agent(model=model, instructions=system_prompt)
        response = agent.run(user_prompt)
        content = response.content or ""

        # Record token metrics if available
        if response.metrics and hasattr(response.metrics, "get"):
            input_tokens = response.metrics.get("input_tokens", 0)
            output_tokens = response.metrics.get("output_tokens", 0)
            if input_tokens:
                redesign_agent_tokens_total.labels(agent_name=name, direction="input").inc(
                    input_tokens
                )
            if output_tokens:
                redesign_agent_tokens_total.labels(agent_name=name, direction="output").inc(
                    output_tokens
                )

        return content
    except Exception:
        status = "error"
        raise
    finally:
        duration = time.monotonic() - start
        redesign_agent_duration_seconds.labels(agent_name=name, status=status).observe(duration)
        logger.info("Agent %s completed in %.1fs (status=%s)", name, duration, status)


def _run_crawl_analyst(crawl_result: CrawlResult, settings: Settings) -> SiteAnalysis:
    """Run the CrawlAnalyst agent to produce a SiteAnalysis."""
    model = _create_model(settings.crawl_analyst_model, settings)
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
        return SiteAnalysis.model_validate(data)
    except (json.JSONDecodeError, ValueError) as exc:
        redesign_guardrail_triggers_total.labels(guardrail_name="json_parse", action="fail").inc()
        raise RedesignError(f"CrawlAnalyst returned invalid JSON: {exc}") from exc


def _run_design_strategist(
    site_analysis: SiteAnalysis, crawl_result: CrawlResult, settings: Settings
) -> DesignBrief:
    """Run the DesignStrategist agent to produce a DesignBrief."""
    model = _create_model(settings.design_strategist_model, settings)
    user_prompt = DESIGN_STRATEGIST_USER_TEMPLATE.format(
        site_analysis_json=site_analysis.model_dump_json(indent=2),
        colors=", ".join(crawl_result.colors[:10]) or "not detected",
        fonts=", ".join(crawl_result.fonts[:5]) or "not detected",
    )
    raw = _run_agent("design_strategist", DESIGN_STRATEGIST_SYSTEM, user_prompt, model)
    try:
        data = _extract_json(raw)
        return DesignBrief.model_validate(data)
    except (json.JSONDecodeError, ValueError) as exc:
        redesign_guardrail_triggers_total.labels(guardrail_name="json_parse", action="fail").inc()
        raise RedesignError(f"DesignStrategist returned invalid JSON: {exc}") from exc


def _run_component_selector(
    site_analysis: SiteAnalysis, design_brief: DesignBrief, settings: Settings
) -> ComponentSelection:
    """Run the ComponentSelector agent to pick the best UI components."""
    import os

    model = _create_model(settings.design_strategist_model, settings)  # Use same model as strategist

    # Load the marketing component catalog
    catalog_path = os.path.join(os.path.dirname(__file__), "..", "..", "components", "marketing-catalog.json")
    try:
        with open(catalog_path) as f:
            catalog = f.read()
    except FileNotFoundError:
        logger.warning("Component catalog not found at %s, skipping component selection", catalog_path)
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
) -> str:
    """Run the HTMLGenerator agent to produce HTML."""
    model = _create_model(settings.html_generator_model, settings)

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

    user_prompt = HTML_GENERATOR_USER_TEMPLATE.format(
        design_brief_json=design_brief.model_dump_json(indent=2),
        crawl_context=crawl_result.to_prompt_context(),
        title=crawl_result.title,
        meta_description=crawl_result.meta_description,
        quality_feedback=feedback_section,
    ) + component_context
    raw = _run_agent("html_generator", HTML_GENERATOR_SYSTEM, user_prompt, model)
    html = _clean_html(raw)
    _validate_html(html)
    return html


def _run_quality_reviewer(
    html: str,
    design_brief: DesignBrief,
    site_analysis: SiteAnalysis,
    settings: Settings,
) -> QualityReport:
    """Run the QualityReviewer agent to evaluate the HTML."""
    model = _create_model(settings.quality_reviewer_model, settings)
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
        return QualityReport.model_validate(data)
    except (json.JSONDecodeError, ValueError) as exc:
        redesign_guardrail_triggers_total.labels(guardrail_name="json_parse", action="fail").inc()
        # If we can't parse the quality report, assume it passed to avoid blocking
        logger.warning("QualityReviewer returned invalid JSON, assuming pass: %s", exc)
        return QualityReport(passed=True, overall_score=7, strengths=["Could not parse review"])


def _run_normalizer(
    html: str, design_brief: DesignBrief, settings: Settings
) -> str:
    """Normalize the HTML for cohesive design + apply premium psychology principles.

    Combines two concepts:
    1. ANF "Normalize" — unify typography, colors, spacing from assembled components
    2. Premium Psychology — engineer the halo effect, reduce cognitive load, add micro-interactions
    """
    from sastaspace.agents.prompts import NORMALIZER_SYSTEM, NORMALIZER_USER_TEMPLATE

    model = _create_model(settings.html_generator_model, settings)

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


def run_redesign_pipeline(crawl_result: CrawlResult, settings: Settings) -> str:
    """
    Execute the full Agno multi-agent redesign pipeline.

    Pipeline: CrawlAnalyst -> DesignStrategist -> HTMLGenerator -> QualityReviewer
    With retry: if quality review fails, retry HTMLGenerator with feedback (max 2 retries).

    Args:
        crawl_result: The crawled website data.
        settings: Application settings with model config.

    Returns:
        The final redesigned HTML string.

    Raises:
        RedesignError: If the pipeline fails.
    """
    if crawl_result.error:
        raise RedesignError(f"Cannot redesign — crawl failed: {crawl_result.error}")

    tier = "agno"
    pipeline_start = time.monotonic()
    status = "success"

    try:
        # Step 1: Crawl Analyst
        logger.info("Pipeline step 1/4: CrawlAnalyst")
        site_analysis = _run_crawl_analyst(crawl_result, settings)

        # Step 2: Design Strategist
        logger.info("Pipeline step 2/5: DesignStrategist")
        design_brief = _run_design_strategist(site_analysis, crawl_result, settings)

        # Step 3: Component Selector — picks best UI components for this business
        logger.info("Pipeline step 3/5: ComponentSelector")
        component_selection = _run_component_selector(site_analysis, design_brief, settings)

        # Step 4 & 5: HTMLGenerator + QualityReviewer with retry loop
        html = ""
        quality_report = None
        quality_feedback = ""

        for attempt in range(1, MAX_QUALITY_RETRIES + 2):  # max retries + 1 initial
            logger.info(
                "Pipeline step 3/4: HTMLGenerator (attempt %d/%d)",
                attempt,
                MAX_QUALITY_RETRIES + 1,
            )
            html = _run_html_generator(
                design_brief, crawl_result, settings, quality_feedback, component_selection
            )

            logger.info("Pipeline step 4/4: QualityReviewer (attempt %d)", attempt)
            quality_report = _run_quality_reviewer(html, design_brief, site_analysis, settings)

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

        # Step 6: Normalizer — ensure cohesive design
        logger.info("Pipeline step 6/6: Normalizer")
        html = _run_normalizer(html, design_brief, settings)

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
