# sastaspace/agents/pipeline.py
"""2-step redesign pipeline: Planner -> Builder.

Planner: Analyze site + design brief + copy in ONE LLM call.
Builder: Generate the final HTML from the plan in ONE LLM call.
No quality review loop -- quality constraints are in the Builder prompt.
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Callable

from agno.agent import Agent
from agno.models.google import Gemini
from agno.models.openai import OpenAILike

from sastaspace.agents.metrics import (
    redesign_agent_duration_seconds,
    redesign_agent_tokens_total,
    redesign_guardrail_triggers_total,
    redesign_pipeline_duration_seconds,
    redesign_pipeline_total,
)
from sastaspace.agents.models import (
    RedesignPlan,
)
from sastaspace.agents.prompts import (
    BUILDER_SYSTEM,
    BUILDER_USER_TEMPLATE,
    PLANNER_SYSTEM,
    PLANNER_USER_TEMPLATE,
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
    "planner",
    "builder",
]

AGENT_MESSAGES: dict[str, dict] = {
    "planner": {
        "message": "Analyzing your site and crafting the redesign plan",
        "step_progress": 45,
    },
    "builder": {
        "message": "Building your redesigned page",
        "step_progress": 75,
    },
}


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
    model_id: str,
    settings: Settings,
    *,
    use_ollama: bool = False,
    model_provider: str = "claude",
) -> OpenAILike | Gemini:
    """Create an Agno model instance.

    Args:
        model_id: The model identifier string.
        settings: Application settings with API credentials.
        use_ollama: If True, route to the local Ollama endpoint (free tier).
        model_provider: "claude" or "gemini" — selects API credentials and endpoint.
    """
    if model_provider == "gemini":
        return Gemini(
            id=settings.gemini_model,
            api_key=settings.gemini_api_key,
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


def _run_planner(
    crawl_result: CrawlResult,
    settings: Settings,
    tier: str = "premium",
    model_provider: str = "claude",
) -> RedesignPlan:
    """Run the Planner -- analyze, design, and write copy in one shot."""
    # Ollama only for free tier when no explicit provider (claude/gemini)
    use_ollama = tier == "free" and model_provider not in ("claude", "gemini")
    model_id = settings.free_crawl_analyst_model if use_ollama else settings.crawl_analyst_model
    model = _create_model(model_id, settings, use_ollama=use_ollama, model_provider=model_provider)
    user_prompt = PLANNER_USER_TEMPLATE.format(
        crawl_context=crawl_result.to_prompt_context(),
        title=crawl_result.title,
        meta_description=crawl_result.meta_description,
        colors=", ".join(crawl_result.colors[:10]) or "not detected",
        fonts=", ".join(crawl_result.fonts[:5]) or "not detected",
    )
    raw = _run_agent("planner", PLANNER_SYSTEM, user_prompt, model)
    try:
        data = _extract_json(raw)
        result = RedesignPlan.model_validate(data)
        logger.info(
            "PLANNER RESULT | brand=%s layout=%s content_map_keys=%d",
            result.brand.name,
            result.layout_archetype,
            len(result.content_map),
        )
        if result.content_warnings:
            for w in result.content_warnings:
                logger.warning("Planner content warning: %s", w)
        return result
    except (json.JSONDecodeError, ValueError) as exc:
        redesign_guardrail_triggers_total.labels(guardrail_name="json_parse", action="fail").inc()
        if raw:
            logger.error("PARSE FAIL | agent=planner full_content=%.500s", raw.replace("\n", " "))
        raise RedesignError(f"Planner returned invalid JSON: {exc}") from exc


def _run_builder(
    plan: RedesignPlan,
    crawl_result: CrawlResult,
    settings: Settings,
    tier: str = "premium",
    model_provider: str = "claude",
) -> str:
    """Run the Builder -- generate HTML from the plan in one shot."""
    use_ollama = tier == "free" and model_provider not in ("claude", "gemini")
    model_id = settings.free_html_generator_model if use_ollama else settings.html_generator_model
    model = _create_model(model_id, settings, use_ollama=use_ollama, model_provider=model_provider)

    user_prompt = BUILDER_USER_TEMPLATE.format(
        plan_json=plan.model_dump_json(indent=2),
        crawl_context=crawl_result.to_prompt_context(),
        title=crawl_result.title,
        meta_description=crawl_result.meta_description,
    )
    raw = _run_agent("builder", BUILDER_SYSTEM, user_prompt, model)
    html = _clean_html(raw)
    _validate_html(html)
    logger.info(
        "BUILDER RESULT | html_len=%d has_doctype=%s has_style=%s has_media=%s",
        len(html),
        "<!doctype" in html.lower(),
        "<style" in html.lower(),
        "@media" in html.lower(),
    )
    return html


def _restore_from_checkpoint(checkpoint: dict) -> tuple[int, dict]:
    """Determine resume index from checkpoint."""
    completed = checkpoint.get("completed_step", "")
    data = checkpoint.get("data", {})

    if completed not in PIPELINE_STEPS:
        return 0, {}

    resume_idx = PIPELINE_STEPS.index(completed) + 1
    restored: dict = {}

    if "plan" in data:
        restored["plan"] = RedesignPlan.model_validate_json(data["plan"])
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
    Execute the 2-step redesign pipeline: Planner -> Builder.

    Args:
        crawl_result: The crawled website data.
        settings: Application settings with model config.
        progress_callback: Optional callable(event, data) fired before each step.
        tier: "free" (Ollama) or "premium" (Claude/Gemini).
        checkpoint: Optional checkpoint dict to resume from.
        checkpoint_callback: Optional callable(step_name, data) fired after each step.
        model_provider: "claude" or "gemini".

    Returns:
        The final redesigned HTML string.
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
            pass

    def _checkpoint(step_name: str, accumulated: dict) -> None:
        if checkpoint_callback is None:
            return
        try:
            checkpoint_callback(step_name, {"completed_step": step_name, "data": accumulated})
        except Exception:  # noqa: pycodegate[no-broad-exception]
            pass

    if crawl_result.error:
        raise RedesignError(f"Cannot redesign -- crawl failed: {crawl_result.error}")

    resume_idx = 0
    restored: dict = {}
    if checkpoint:
        resume_idx, restored = _restore_from_checkpoint(checkpoint)
        if resume_idx > 0:
            logger.info("Resuming pipeline from step %d/%d", resume_idx + 1, len(PIPELINE_STEPS))

    def _should_run(step_name: str) -> bool:
        return PIPELINE_STEPS.index(step_name) >= resume_idx

    pipeline_start = time.monotonic()
    status = "success"
    cp_data: dict = {}

    try:
        # Step 1: Planner -- analyze + design + copy
        if _should_run("planner"):
            logger.info("Pipeline step 1/2: Planner (tier=%s, provider=%s)", tier, model_provider)
            _emit("planner")
            plan = _run_planner(crawl_result, settings, tier, model_provider)
            cp_data["plan"] = plan.model_dump_json()
            _checkpoint("planner", cp_data)
        else:
            plan = restored.get("plan", RedesignPlan())

        # Step 2: Builder -- generate HTML
        if _should_run("builder"):
            logger.info("Pipeline step 2/2: Builder (tier=%s, provider=%s)", tier, model_provider)
            _emit("builder")
            html = _run_builder(plan, crawl_result, settings, tier, model_provider)
            cp_data["html"] = html
            _checkpoint("builder", cp_data)
        else:
            html = restored.get("html", "")

        return html

    except RedesignError:
        status = "failure"
        raise
    except Exception as exc:  # noqa: pycodegate[no-broad-exception] — top-level handler
        status = "failure"
        raise RedesignError(f"Pipeline failed: {exc}") from exc
    finally:
        duration = time.monotonic() - pipeline_start
        redesign_pipeline_duration_seconds.labels(tier=tier, status=status).observe(duration)
        redesign_pipeline_total.labels(tier=tier, status=status).inc()
        logger.info("Pipeline completed in %.1fs (status=%s)", duration, status)
