# sastaspace/agents/pipeline.py
"""Agno multi-agent redesign pipeline.

Pipeline: CrawlAnalyst -> DesignStrategist -> Copywriter -> HTMLGenerator -> QualityReviewer
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
    CopywriterOutput,
    DesignBrief,
    QualityReport,
    SiteAnalysis,
)
from sastaspace.agents.prompts import (
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
from sastaspace.html_utils import RedesignError
from sastaspace.html_utils import clean_html as _clean_html
from sastaspace.html_utils import validate_html as _validate_html

logger = logging.getLogger(__name__)

_RETRY_DELAYS = (5, 15, 30)  # seconds before each retry on empty response (rate limited)

ProgressCallback = Callable[[str, dict], None] | None
CheckpointCallback = Callable[[str, dict], None] | None

PIPELINE_STEPS = [
    "crawl_analyst",
    "design_strategist",
    "copywriter",
    "html_generator",
    "quality_reviewer",
]

AGENT_MESSAGES: dict[str, dict] = {
    "crawl_analyst": {
        "message": "Analyzing your site's content and structure",
        "step_progress": 42,
    },
    "design_strategist": {"message": "Crafting your new design direction", "step_progress": 52},
    "copywriter": {"message": "Writing conversion-optimized copy", "step_progress": 62},
    "html_generator": {"message": "Building your new page", "step_progress": 72},
    "quality_reviewer": {"message": "Reviewing design quality and uniqueness", "step_progress": 85},
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


def _create_model(
    model_id: str, settings: Settings, *, use_ollama: bool = False, model_provider: str = "claude"
) -> OpenAILike:
    """Create an Agno OpenAILike model instance.

    Args:
        model_id: The model identifier string.
        settings: Application settings with API credentials.
        use_ollama: If True, route to the local Ollama endpoint (free tier).
        model_provider: "claude" or "gemini" — selects API credentials and endpoint.
    """
    if model_provider == "gemini":
        return OpenAILike(
            id=settings.gemini_model,
            api_key=settings.gemini_api_key,
            base_url=settings.gemini_api_url,
        )
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
                    "AGENT RETRY | agent=%s attempt=%d waiting=%ds",
                    name,
                    attempt,
                    delay,
                )
                time.sleep(delay)
            agent = Agent(model=model, instructions=system_prompt, tools=[])
            response = agent.run(user_prompt)
            content = response.content or ""
            # Treat rate limit error text as empty (trigger retry)
            if content and "rate limit" not in content.lower():
                break
            if content:
                logger.warning("AGENT RATE LIMITED | agent=%s content=%.100s", name, content)
                content = ""
        if not content:
            n = len(_RETRY_DELAYS) + 1
            raise RedesignError(f"{name} failed after {n} attempts — rate limited")

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
    except Exception as exc:  # noqa: pycodegate[no-broad-exception] — re-raises after logging
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
    crawl_result: CrawlResult,
    settings: Settings,
    tier: str = "premium",
    model_provider: str = "claude",
) -> SiteAnalysis:
    """Run the CrawlAnalyst agent to produce a SiteAnalysis."""
    use_ollama = tier == "free"
    model_id = settings.free_crawl_analyst_model if use_ollama else settings.crawl_analyst_model
    model = _create_model(model_id, settings, use_ollama=use_ollama, model_provider=model_provider)
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
    model_provider: str = "claude",
) -> DesignBrief:
    """Run the DesignStrategist agent to produce a DesignBrief."""
    use_ollama = tier == "free"
    model_id = (
        settings.free_design_strategist_model if use_ollama else settings.design_strategist_model
    )
    model = _create_model(model_id, settings, use_ollama=use_ollama, model_provider=model_provider)
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
    model_provider: str = "claude",
) -> CopywriterOutput:
    """Run the Copywriter agent to produce conversion-optimized copy.

    The copywriter is MANDATORY — its content_map is the binding contract
    for what the HTMLGenerator can use. This prevents content hallucination.
    """
    use_ollama = tier == "free"
    model_id = settings.free_copywriter_model if use_ollama else settings.design_strategist_model
    model = _create_model(model_id, settings, use_ollama=use_ollama, model_provider=model_provider)

    # Format content sections for the copywriter
    sections_text = (
        "\n".join(
            f"### {s.heading or s.content_type}\n{s.content_summary}"
            + (f"\nExact text: {s.exact_text}" if s.exact_text else "")
            for s in site_analysis.content_sections
        )
        or "No sections extracted"
    )

    # Format absent content list
    absent_text = (
        "\n".join(f"- {item}" for item in site_analysis.content_absent)
        if site_analysis.content_absent
        else "No specific absent content noted"
    )

    user_prompt = COPYWRITER_USER_TEMPLATE.format(
        brand_name=site_analysis.brand.name or "Unknown",
        industry=site_analysis.brand.industry or "Unknown",
        primary_goal=site_analysis.primary_goal or "conversion",
        target_audience=site_analysis.target_audience or "general",
        brand_voice=site_analysis.brand.voice_tone or "professional",
        content_sections=sections_text,
        content_absent=absent_text,
        conversion_strategy=design_brief.conversion_strategy,
    )
    raw = _run_agent("copywriter", COPYWRITER_SYSTEM, user_prompt, model)
    try:
        data = _extract_json(raw)
        copy = CopywriterOutput.model_validate(data)
        logger.info(
            "Copywriter produced headline: %s, content_map keys: %d",
            copy.headline[:50],
            len(copy.content_map),
        )
        if copy.content_warnings:
            for warning in copy.content_warnings:
                logger.warning("Copywriter warning: %s", warning)
        return copy
    except (json.JSONDecodeError, ValueError) as exc:
        redesign_guardrail_triggers_total.labels(guardrail_name="json_parse", action="fail").inc()
        if raw:
            logger.error(
                "PARSE FAIL | agent=copywriter full_content=%.500s", raw.replace("\n", " ")
            )
        raise RedesignError(f"Copywriter returned invalid JSON: {exc}") from exc


def _run_html_generator(
    design_brief: DesignBrief,
    crawl_result: CrawlResult,
    copywriter_output: CopywriterOutput,
    settings: Settings,
    quality_feedback: str = "",
    tier: str = "premium",
    model_provider: str = "claude",
) -> str:
    """Run the HTMLGenerator agent to produce HTML.

    Uses strict content binding from the copywriter's content_map.
    """
    use_ollama = tier == "free"
    model_id = settings.free_html_generator_model if use_ollama else settings.html_generator_model
    model = _create_model(model_id, settings, use_ollama=use_ollama, model_provider=model_provider)

    feedback_section = ""
    if quality_feedback:
        feedback_section = HTML_GENERATOR_USER_TEMPLATE_WITH_FEEDBACK.format(
            feedback=quality_feedback,
        )

    # Build content map JSON for strict binding
    content_map_json = (
        json.dumps(copywriter_output.content_map, indent=2)
        if copywriter_output.content_map
        else "{}"
    )

    # Build content warnings
    content_warnings = (
        "\n".join(f"- {w}" for w in copywriter_output.content_warnings)
        if copywriter_output.content_warnings
        else "None"
    )

    # Build design tokens JSON
    design_tokens_json = (
        json.dumps(design_brief.design_tokens.model_dump(), indent=2)
        if design_brief.design_tokens
        else "{}"
    )

    user_prompt = HTML_GENERATOR_USER_TEMPLATE.format(
        design_brief_json=design_brief.model_dump_json(indent=2),
        layout_archetype=design_brief.layout_archetype or "editorial",
        design_tokens_json=design_tokens_json,
        content_map_json=content_map_json,
        crawl_context=crawl_result.to_prompt_context(),
        title=crawl_result.title,
        meta_description=crawl_result.meta_description,
        quality_feedback=feedback_section,
        content_warnings=content_warnings,
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
    model_provider: str = "claude",
) -> QualityReport:
    """Run the QualityReviewer agent to evaluate the HTML."""
    use_ollama = tier == "free"
    model_id = (
        settings.free_quality_reviewer_model if use_ollama else settings.quality_reviewer_model
    )
    model = _create_model(model_id, settings, use_ollama=use_ollama, model_provider=model_provider)
    html_lower = html.lower()

    # Format absent content for hallucination checking
    content_absent = (
        ", ".join(site_analysis.content_absent) if site_analysis.content_absent else "none noted"
    )

    html_preview = html[:24000]
    user_prompt = QUALITY_REVIEWER_USER_TEMPLATE.format(
        design_brief_json=design_brief.model_dump_json(indent=2),
        layout_archetype=design_brief.layout_archetype or "not specified",
        title=site_analysis.brand.name or "Unknown",
        section_count=len(site_analysis.content_sections),
        key_content_preview=(
            site_analysis.key_content[:200] if site_analysis.key_content else "N/A"
        ),
        content_absent=content_absent,
        html_preview=html_preview,
        html_preview_len=len(html_preview),
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
            "AGENT RESULT | agent=quality_reviewer passed=%s score=%d "
            "uniqueness=%d brand=%d hallucinations=%d issues=%d details=%s",
            result.passed,
            result.overall_score,
            result.uniqueness_score,
            result.brand_adherence_score,
            len(result.hallucinated_content),
            len(result.issues),
            issues_summary[:200] or "none",
        )
        if result.hallucinated_content:
            for h in result.hallucinated_content:
                logger.warning("HALLUCINATION DETECTED: %s", h[:200])
        return result
    except (json.JSONDecodeError, ValueError) as exc:
        redesign_guardrail_triggers_total.labels(guardrail_name="json_parse", action="fail").inc()
        if raw:
            logger.error(
                "PARSE FAIL | agent=quality_reviewer full_content=%.500s", raw.replace("\n", " ")
            )
        logger.warning("QualityReviewer returned invalid JSON, assuming pass: %s", exc)
        return QualityReport(
            passed=True,
            overall_score=7,
            uniqueness_score=5,
            brand_adherence_score=5,
            strengths=["Could not parse review"],
        )


def _restore_from_checkpoint(checkpoint: dict) -> tuple[int, dict]:
    """Determine resume index and restore intermediate data from checkpoint.

    Returns:
        (resume_from_index, restored_data) where resume_from_index is the index
        in PIPELINE_STEPS to start executing from (the step *after* completed_step).
        restored_data holds deserialized Pydantic model outputs keyed by data name.
    """
    completed = checkpoint.get("completed_step", "")
    data = checkpoint.get("data", {})

    if completed not in PIPELINE_STEPS:
        return 0, {}

    resume_idx = PIPELINE_STEPS.index(completed) + 1
    restored: dict = {}

    # Deserialize any saved intermediate results
    if "site_analysis" in data:
        restored["site_analysis"] = SiteAnalysis.model_validate_json(data["site_analysis"])
    if "design_brief" in data:
        restored["design_brief"] = DesignBrief.model_validate_json(data["design_brief"])
    if "copywriter_output" in data:
        restored["copywriter_output"] = CopywriterOutput.model_validate_json(
            data["copywriter_output"]
        )
    if "html" in data:
        restored["html"] = data["html"]

    return resume_idx, restored


def run_redesign_pipeline(
    crawl_result: CrawlResult,
    settings: Settings,
    progress_callback: ProgressCallback = None,
    tier: str = "premium",
    checkpoint: dict | None = None,
    checkpoint_callback: CheckpointCallback = None,
    model_provider: str = "claude",
) -> str:
    """
    Execute the full Agno multi-agent redesign pipeline.

    Pipeline: CrawlAnalyst -> DesignStrategist -> Copywriter -> HTMLGenerator -> QualityReviewer
    With retry: if quality review fails, retry HTMLGenerator with feedback (max 2 retries).

    Args:
        crawl_result: The crawled website data.
        settings: Application settings with model config.
        progress_callback: Optional callable(event, data) fired before each agent stage.
        tier: Redesign tier — "free" (Ollama) or "premium" (Claude).
        checkpoint: Optional checkpoint dict to resume from. Contains completed_step and data.
        checkpoint_callback: Optional callable(step_name, checkpoint_data) fired after each step.

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
        except Exception:  # noqa: pycodegate[no-broad-exception]
            pass  # never let UI callback crash the pipeline

    def _checkpoint(step_name: str, accumulated: dict) -> None:
        """Fire checkpoint callback with accumulated data."""
        if checkpoint_callback is None:
            return
        try:
            checkpoint_callback(step_name, {"completed_step": step_name, "data": accumulated})
        except Exception:  # noqa: pycodegate[no-broad-exception]
            pass  # never crash the pipeline over a checkpoint save

    if crawl_result.error:
        raise RedesignError(f"Cannot redesign — crawl failed: {crawl_result.error}")

    # Determine resume point from checkpoint
    resume_idx = 0
    restored: dict = {}
    if checkpoint:
        resume_idx, restored = _restore_from_checkpoint(checkpoint)
        if resume_idx > 0:
            logger.info(
                "Resuming pipeline from step %d/%d (%s)",
                resume_idx + 1,
                len(PIPELINE_STEPS),
                PIPELINE_STEPS[resume_idx] if resume_idx < len(PIPELINE_STEPS) else "done",
            )

    def _should_run(step_name: str) -> bool:
        return PIPELINE_STEPS.index(step_name) >= resume_idx

    pipeline_start = time.monotonic()
    status = "success"

    # Accumulated checkpoint data (JSON strings for Pydantic models, raw for HTML)
    cp_data: dict = {}

    try:
        # Step 1: Crawl Analyst
        if _should_run("crawl_analyst"):
            logger.info("Pipeline step 1/5: CrawlAnalyst (tier=%s)", tier)
            _emit("crawl_analyst")
            site_analysis = _run_crawl_analyst(
                crawl_result, settings, tier, model_provider=model_provider
            )
            cp_data["site_analysis"] = site_analysis.model_dump_json()
            _checkpoint("crawl_analyst", cp_data)
        else:
            site_analysis = restored.get("site_analysis", SiteAnalysis())

        # Step 2: Design Strategist
        if _should_run("design_strategist"):
            logger.info("Pipeline step 2/5: DesignStrategist (tier=%s)", tier)
            _emit("design_strategist")
            design_brief = _run_design_strategist(
                site_analysis,
                crawl_result,
                settings,
                tier,
                model_provider=model_provider,
            )
            cp_data["design_brief"] = design_brief.model_dump_json()
            _checkpoint("design_strategist", cp_data)
        else:
            design_brief = restored.get("design_brief", DesignBrief())

        # Step 3: Copywriter (MANDATORY) — writes conversion-optimized copy
        if _should_run("copywriter"):
            logger.info("Pipeline step 3/5: Copywriter (tier=%s)", tier)
            _emit("copywriter")
            copywriter_output = _run_copywriter(
                site_analysis,
                design_brief,
                settings,
                tier,
                model_provider=model_provider,
            )
            cp_data["copywriter_output"] = copywriter_output.model_dump_json()
            _checkpoint("copywriter", cp_data)
        else:
            copywriter_output = restored.get("copywriter_output", CopywriterOutput())

        # Step 4 & 5: HTMLGenerator + QualityReviewer with retry loop
        html = ""
        quality_report = None
        quality_feedback = ""

        for attempt in range(1, MAX_QUALITY_RETRIES + 2):  # max retries + 1 initial
            if _should_run("html_generator"):
                logger.info(
                    "Pipeline step 4/5: HTMLGenerator (attempt %d/%d)",
                    attempt,
                    MAX_QUALITY_RETRIES + 1,
                )
                _emit("html_generator")
                html = _run_html_generator(
                    design_brief,
                    crawl_result,
                    copywriter_output,
                    settings,
                    quality_feedback,
                    tier,
                    model_provider=model_provider,
                )
                cp_data["html"] = html
                _checkpoint("html_generator", cp_data)

            if _should_run("quality_reviewer"):
                logger.info("Pipeline step 5/5: QualityReviewer (attempt %d)", attempt)
                _emit("quality_reviewer")
                quality_report = _run_quality_reviewer(
                    html, design_brief, site_analysis, settings, tier, model_provider=model_provider
                )
                _checkpoint("quality_reviewer", cp_data)

            if quality_report and quality_report.passed:
                logger.info(
                    "Quality review passed (score=%d) on attempt %d",
                    quality_report.overall_score,
                    attempt,
                )
                break

            if quality_report and attempt <= MAX_QUALITY_RETRIES:
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
            elif quality_report:
                logger.warning(
                    "Quality review failed after %d attempts (score=%d), using last HTML",
                    MAX_QUALITY_RETRIES + 1,
                    quality_report.overall_score,
                )
                redesign_guardrail_triggers_total.labels(
                    guardrail_name="quality_review", action="accept_low_quality"
                ).inc()
                break

        return html

    except RedesignError:
        status = "failure"
        raise
    except Exception as exc:  # noqa: pycodegate[no-broad-exception] — top-level pipeline handler
        status = "failure"
        raise RedesignError(f"Agno pipeline failed: {exc}") from exc
    finally:
        duration = time.monotonic() - pipeline_start
        redesign_pipeline_duration_seconds.labels(tier=tier, status=status).observe(duration)
        redesign_pipeline_total.labels(tier=tier, status=status).inc()
        logger.info("Pipeline completed in %.1fs (status=%s)", duration, status)
