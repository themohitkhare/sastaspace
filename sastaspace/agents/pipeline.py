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
    AgnoRedesignResult,
    DesignBrief,
    QualityReport,
    SiteAnalysis,
)
from sastaspace.agents.prompts import (
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
        agent = Agent(model=model, system_prompt=system_prompt)
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
        redesign_guardrail_triggers_total.labels(
            guardrail_name="json_parse", action="fail"
        ).inc()
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
        redesign_guardrail_triggers_total.labels(
            guardrail_name="json_parse", action="fail"
        ).inc()
        raise RedesignError(f"DesignStrategist returned invalid JSON: {exc}") from exc


def _run_html_generator(
    design_brief: DesignBrief,
    crawl_result: CrawlResult,
    settings: Settings,
    quality_feedback: str = "",
) -> str:
    """Run the HTMLGenerator agent to produce HTML."""
    model = _create_model(settings.html_generator_model, settings)

    feedback_section = ""
    if quality_feedback:
        feedback_section = HTML_GENERATOR_USER_TEMPLATE_WITH_FEEDBACK.format(
            feedback=quality_feedback,
        )

    user_prompt = HTML_GENERATOR_USER_TEMPLATE.format(
        design_brief_json=design_brief.model_dump_json(indent=2),
        crawl_context=crawl_result.to_prompt_context(),
        title=crawl_result.title,
        meta_description=crawl_result.meta_description,
        quality_feedback=feedback_section,
    )
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
        key_content_preview=(site_analysis.key_content[:200] if site_analysis.key_content else "N/A"),
        html_preview=html[:8000],
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
        redesign_guardrail_triggers_total.labels(
            guardrail_name="json_parse", action="fail"
        ).inc()
        # If we can't parse the quality report, assume it passed to avoid blocking
        logger.warning("QualityReviewer returned invalid JSON, assuming pass: %s", exc)
        return QualityReport(passed=True, overall_score=7, strengths=["Could not parse review"])


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
        logger.info("Pipeline step 2/4: DesignStrategist")
        design_brief = _run_design_strategist(site_analysis, crawl_result, settings)

        # Step 3 & 4: HTMLGenerator + QualityReviewer with retry loop
        html = ""
        quality_report = None
        quality_feedback = ""

        for attempt in range(1, MAX_QUALITY_RETRIES + 2):  # max retries + 1 initial
            logger.info(
                "Pipeline step 3/4: HTMLGenerator (attempt %d/%d)",
                attempt,
                MAX_QUALITY_RETRIES + 1,
            )
            html = _run_html_generator(design_brief, crawl_result, settings, quality_feedback)

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
