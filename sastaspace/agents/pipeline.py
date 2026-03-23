# sastaspace/agents/pipeline.py
"""Redesign pipeline: Planner -> (Builder | Component Composer + React Build).

Planner: Analyze site + design brief + copy in ONE LLM call.
Builder: Generate the final HTML from the plan in ONE LLM call (legacy path).
Component path: Select components → Compose React page → Vite build.
"""

from __future__ import annotations

import concurrent.futures
import json
import logging
import re
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

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
    COMPOSER_SYSTEM,
    COMPOSER_USER_TEMPLATE,
    PARALLEL_ABOVE_FOLD_SYSTEM,
    PARALLEL_BELOW_FOLD_SYSTEM,
    PARALLEL_CONTENT_SYSTEM,
    PARALLEL_SECTION_USER_TEMPLATE,
    PLANNER_SYSTEM,
    PLANNER_USER_TEMPLATE,
)
from sastaspace.component_selector import ComponentManifest, select_components
from sastaspace.config import Settings
from sastaspace.crawler import CrawlResult
from sastaspace.html_utils import RedesignError, RedesignResult
from sastaspace.html_utils import clean_html as _clean_html
from sastaspace.html_utils import validate_html as _validate_html
from sastaspace.plan_cache import cache_plan, get_cached_plan, merge_cached_plan
from sastaspace.react_builder import BuildError, build_react_page, parse_composer_output

logger = logging.getLogger(__name__)

_RETRY_DELAYS = (5, 15, 30)  # seconds before each retry on empty response (rate limited)

ProgressCallback = Callable[[str, dict], None] | None
CheckpointCallback = Callable[[str, dict], None] | None

PIPELINE_STEPS = [
    "planner",
    "builder",
]

# Component pipeline has additional steps
COMPONENT_PIPELINE_STEPS = [
    "planner",
    "component_selector",
    "composer",
    "react_build",
]

AGENT_MESSAGES: dict[str, dict] = {
    "planner": {
        "message": "Analyzing your site and crafting the redesign plan",
        "step_progress": 35,
    },
    "component_selector": {
        "message": "Selecting premium components for your site",
        "step_progress": 50,
    },
    "composer": {
        "message": "Composing your page from premium React components",
        "step_progress": 65,
    },
    "react_build": {
        "message": "Building your interactive React page",
        "step_progress": 80,
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
    except Exception as exc:  # noqa: BLE001 — re-raises after logging
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


def _resolve_step_provider(step: str, settings: Settings, global_provider: str) -> str:
    """Resolve the model provider for a pipeline step.

    Checks for a per-step override in settings (e.g. planner_model_provider),
    falling back to the global model_provider passed to the pipeline.
    """
    override = getattr(settings, f"{step}_model_provider", "")
    provider = override if override else global_provider
    logger.info("PERF | step=%s model_provider=%s", step, provider)
    return provider


def _run_planner(
    crawl_result: CrawlResult,
    settings: Settings,
    tier: str = "premium",
    model_provider: str = "claude",
    user_prompt: str = "",
) -> RedesignPlan:
    """Run the Planner -- analyze, design, and write copy in one shot."""
    model_provider = _resolve_step_provider("planner", settings, model_provider)
    # Ollama only for free tier when no explicit provider (claude/gemini)
    use_ollama = tier == "free" and model_provider not in ("claude", "gemini")
    model_id = settings.free_crawl_analyst_model if use_ollama else settings.crawl_analyst_model
    model = _create_model(model_id, settings, use_ollama=use_ollama, model_provider=model_provider)
    planner_system = PLANNER_SYSTEM
    if user_prompt:
        planner_system += (
            "\n\n## User Instructions\n"
            "The user has provided the following specific instructions for this redesign:\n"
            f"{user_prompt}\n\n"
            "Honor these instructions while maintaining design quality standards."
        )
    planner_user_text = PLANNER_USER_TEMPLATE.format(
        crawl_context=crawl_result.to_prompt_context(),
        title=crawl_result.title,
        meta_description=crawl_result.meta_description,
        colors=", ".join(crawl_result.colors[:10]) or "not detected",
        fonts=", ".join(crawl_result.fonts[:5]) or "not detected",
    )
    raw = _run_agent("planner", planner_system, planner_user_text, model)
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
    model_provider = _resolve_step_provider("builder", settings, model_provider)
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


# ---------------------------------------------------------------------------
# Parallel builder — split HTML generation into concurrent section calls
# ---------------------------------------------------------------------------

_ABOVE_FOLD_TYPES = {"hero", "navigation", "nav", "header"}
_BELOW_FOLD_TYPES = {"footer", "cta", "contact", "call-to-action"}


def _classify_sections(
    plan: RedesignPlan,
) -> tuple[list[str], list[str], list[str]]:
    """Split plan content_sections into above-fold, content, and below-fold groups.

    Returns three lists of section heading strings (or "hero"/"cta"/"footer"
    placeholders when no explicit heading exists).
    """
    above: list[str] = []
    content: list[str] = []
    below: list[str] = []

    for cs in plan.content_sections:
        ctype = (cs.content_type or "").lower().strip()
        heading = cs.heading or ctype or "section"
        if ctype in _ABOVE_FOLD_TYPES:
            above.append(heading)
        elif ctype in _BELOW_FOLD_TYPES:
            below.append(heading)
        else:
            content.append(heading)

    # Ensure each group has at least a placeholder so the LLM knows what to do
    if not above:
        above = ["hero + navigation"]
    if not below:
        below = ["CTA + footer"]
    if not content:
        content = ["main content sections from content_map"]

    return above, content, below


def _merge_parallel_html(
    above_fold: str,
    content_sections: str,
    below_fold: str,
) -> str:
    """Merge three HTML fragments into a single valid HTML document.

    above_fold: starts with <!DOCTYPE html>...<body>, NO closing tags
    content_sections: raw <section> elements
    below_fold: closing sections + </body></html>
    """
    above = _clean_html(above_fold)
    middle = _clean_html(content_sections)
    below = _clean_html(below_fold)

    # Strip any accidental closing tags from above-fold
    for tag in ("</body>", "</html>"):
        idx = above.lower().rfind(tag)
        if idx != -1:
            above = above[:idx]

    # Strip any accidental opening document tags from middle
    for pattern in (r"<!DOCTYPE[^>]*>", r"<html[^>]*>", r"<head[\s\S]*?</head>", r"<body[^>]*>"):
        middle = re.sub(pattern, "", middle, flags=re.IGNORECASE)

    # Strip accidental document wrapper from below-fold (but keep </body></html>)
    for pattern in (r"<!DOCTYPE[^>]*>", r"<html[^>]*>", r"<head[\s\S]*?</head>", r"<body[^>]*>"):
        below = re.sub(pattern, "", below, flags=re.IGNORECASE)

    # Ensure below-fold closes the document
    lower_below = below.lower()
    if "</body>" not in lower_below:
        below += "\n</body>"
    if "</html>" not in lower_below:
        below += "\n</html>"

    merged = above + "\n\n" + middle + "\n\n" + below
    return merged


def _run_parallel_builder(
    plan: RedesignPlan,
    crawl_result: CrawlResult,
    settings: Settings,
    tier: str = "premium",
    model_provider: str = "claude",
) -> str:
    """Run Builder in parallel — 3 concurrent LLM calls for page sections.

    Splits the page into above-fold, content, and below-fold and generates
    each concurrently. Falls back to single-call _run_builder on any failure.
    """
    start = time.monotonic()
    model_provider = _resolve_step_provider("builder", settings, model_provider)
    use_ollama = tier == "free" and model_provider not in ("claude", "gemini")
    model_id = settings.free_html_generator_model if use_ollama else settings.html_generator_model

    above_sections, content_sections_list, below_sections = _classify_sections(plan)

    plan_json = plan.model_dump_json(indent=2)
    crawl_context = crawl_result.to_prompt_context()
    title = crawl_result.title
    meta_desc = crawl_result.meta_description

    section_configs = [
        (
            "builder_above_fold",
            PARALLEL_ABOVE_FOLD_SYSTEM,
            PARALLEL_SECTION_USER_TEMPLATE.format(
                section_name="above-fold section (navigation + hero)",
                plan_json=plan_json,
                crawl_context=crawl_context,
                title=title,
                meta_description=meta_desc,
                assigned_sections=", ".join(above_sections),
            ),
        ),
        (
            "builder_content",
            PARALLEL_CONTENT_SYSTEM,
            PARALLEL_SECTION_USER_TEMPLATE.format(
                section_name="content sections (middle of page)",
                plan_json=plan_json,
                crawl_context=crawl_context,
                title=title,
                meta_description=meta_desc,
                assigned_sections=", ".join(content_sections_list),
            ),
        ),
        (
            "builder_below_fold",
            PARALLEL_BELOW_FOLD_SYSTEM,
            PARALLEL_SECTION_USER_TEMPLATE.format(
                section_name="below-fold section (CTA + footer)",
                plan_json=plan_json,
                crawl_context=crawl_context,
                title=title,
                meta_description=meta_desc,
                assigned_sections=", ".join(below_sections),
            ),
        ),
    ]

    def _call_section(args: tuple[str, str, str]) -> str:
        name, system, user = args
        model = _create_model(
            model_id, settings, use_ollama=use_ollama, model_provider=model_provider
        )
        return _run_agent(name, system, user, model)

    n_sections = len(section_configs)

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=n_sections) as executor:
            futures = [executor.submit(_call_section, cfg) for cfg in section_configs]
            results = [f.result() for f in futures]

        above_html, content_html, below_html = results
        html = _merge_parallel_html(above_html, content_html, below_html)
        _validate_html(html)

        duration_ms = int((time.monotonic() - start) * 1000)
        logger.info(
            "PERF | parallel_builder=true sections=%d duration_ms=%d",
            n_sections,
            duration_ms,
        )
        logger.info(
            "PARALLEL BUILDER RESULT | html_len=%d has_doctype=%s has_style=%s has_media=%s",
            len(html),
            "<!doctype" in html.lower(),
            "<style" in html.lower(),
            "@media" in html.lower(),
        )
        return html

    except Exception as exc:  # noqa: BLE001 — fall back to single-call builder
        duration_ms = int((time.monotonic() - start) * 1000)
        logger.warning(
            "PERF | parallel_builder=true sections=%d duration_ms=%d status=fallback error=%s",
            n_sections,
            duration_ms,
            str(exc)[:200],
        )
        logger.warning("Parallel builder failed, falling back to single-call builder: %s", exc)
        return _run_builder(plan, crawl_result, settings, tier, model_provider)


def _run_composer(
    plan: RedesignPlan,
    manifest: ComponentManifest,
    crawl_result: CrawlResult,
    settings: Settings,
    tier: str = "premium",
    model_provider: str = "claude",
) -> dict[str, str]:
    """Run the Composer — compose React components into a page."""
    model_provider = _resolve_step_provider("composer", settings, model_provider)
    use_ollama = tier == "free" and model_provider not in ("claude", "gemini")
    model_id = settings.free_html_generator_model if use_ollama else settings.html_generator_model
    model = _create_model(model_id, settings, use_ollama=use_ollama, model_provider=model_provider)

    user_prompt = COMPOSER_USER_TEMPLATE.format(
        plan_json=plan.model_dump_json(indent=2),
        component_source=manifest.to_prompt_context(),
        crawl_context=crawl_result.to_prompt_context(),
        title=crawl_result.title,
        meta_description=crawl_result.meta_description,
    )
    raw = _run_agent("composer", COMPOSER_SYSTEM, user_prompt, model)

    files = parse_composer_output(raw)
    if not files:
        raise RedesignError("Composer returned no parseable files")
    if "src/App.tsx" not in files:
        raise RedesignError("Composer output missing src/App.tsx")

    logger.info(
        "COMPOSER RESULT | files=%d total_size=%d",
        len(files),
        sum(len(v) for v in files.values()),
    )
    return files


def _normalize_component_path(path: str) -> str:
    """Normalize a component file path to a src-relative path.

    /components/ui/foo.tsx    → src/components/foo.tsx
    /components/blocks/bar.tsx → src/components/bar.tsx
    /components/baz.tsx        → src/components/baz.tsx
    other/file.tsx             → src/components/file.tsx
    """
    if path.startswith("/components/ui/"):
        return "src/components/" + path.split("/components/ui/")[-1]
    if path.startswith("/components/blocks/"):
        return "src/components/" + path.split("/components/blocks/")[-1]
    if path.startswith("/components/"):
        return "src" + path
    return "src/components/" + path.split("/")[-1]


def _run_react_build(
    files: dict[str, str],
    manifest: ComponentManifest,
    settings: Settings,
) -> RedesignResult:
    """Build the composed React page using Vite and return a RedesignResult."""
    template_dir = settings.redesign_template_dir.resolve()
    if not template_dir.exists():
        raise RedesignError(f"Redesign template not found at {template_dir}")

    # Write selected component source files that weren't modified by Composer
    all_files = dict(files)
    for comp in manifest.components:
        for f in comp.files:
            path = f.get("path", "")
            content = f.get("content", "")
            if not path or not content:
                continue
            rel_path = _normalize_component_path(path)
            # Don't overwrite Composer-modified files
            if rel_path not in all_files:
                all_files[rel_path] = content

    # Use a persistent temp dir (caller is responsible for cleanup after deploy)
    output_dir = Path(tempfile.mkdtemp(prefix="sastaspace-build-"))
    build_start = time.monotonic()

    try:
        build_react_page(all_files, template_dir, output_dir)
    except BuildError as exc:
        raise RedesignError(f"React build failed: {exc}") from exc

    build_duration = time.monotonic() - build_start
    logger.info("React build completed in %.1fs", build_duration)

    # Read the built index.html
    index_html = (output_dir / "index.html").read_text(encoding="utf-8")

    return RedesignResult(html=index_html, build_dir=output_dir)


def _restore_from_checkpoint(checkpoint: dict, steps: list[str]) -> tuple[int, dict]:
    """Determine resume index from checkpoint."""
    completed = checkpoint.get("completed_step", "")
    data = checkpoint.get("data", {})

    if completed not in steps:
        return 0, {}

    resume_idx = steps.index(completed) + 1
    restored: dict = {}

    if "plan" in data:
        restored["plan"] = RedesignPlan.model_validate_json(data["plan"])
    if "html" in data:
        restored["html"] = data["html"]

    return resume_idx, restored


# --- Plan cache helpers ---


_SITE_TYPE_KEYWORDS: dict[str, list[str]] = {
    "restaurant": ["menu", "reservation", "dining", "food", "cuisine", "chef"],
    "portfolio": ["portfolio", "projects", "work", "gallery", "showcase", "designer"],
    "saas": ["pricing", "features", "signup", "sign up", "free trial", "demo", "platform"],
    "ecommerce": ["shop", "cart", "buy", "product", "store", "checkout", "price"],
    "agency": ["agency", "services", "clients", "case studies", "hire us", "our work"],
    "blog": ["blog", "article", "post", "author", "read more", "published"],
}

_SITE_TYPE_ARCHETYPES: dict[str, str] = {
    "restaurant": "split-hero",
    "portfolio": "editorial",
    "saas": "bento",
    "ecommerce": "asymmetric",
    "agency": "editorial",
    "blog": "editorial",
}


def _guess_site_type(crawl_result: CrawlResult) -> str:
    """Heuristic site_type detection from crawl data for cache lookup."""
    text = (
        f"{crawl_result.title} {crawl_result.meta_description} "
        f"{' '.join(crawl_result.headings[:20])} {crawl_result.text_content[:2000]}"
    ).lower()
    scores: dict[str, int] = {}
    for stype, keywords in _SITE_TYPE_KEYWORDS.items():
        scores[stype] = sum(1 for kw in keywords if kw in text)
    best = max(scores, key=scores.get)  # type: ignore[arg-type]
    if scores[best] >= 2:
        return best
    return ""


def _try_plan_cache(crawl_result: CrawlResult) -> dict | None:
    """Attempt to find a cached plan skeleton for the crawl result.

    Uses heuristic site_type detection + default archetype mapping.
    Returns the cached skeleton dict, or None on miss.
    """
    site_type = _guess_site_type(crawl_result)
    if not site_type:
        return None
    archetype = _SITE_TYPE_ARCHETYPES.get(site_type, "")
    if not archetype:
        return None
    return get_cached_plan(site_type, archetype)


def _content_from_crawl(crawl_result: CrawlResult) -> dict:
    """Build plan content fields from crawl data.

    These fields represent the site-specific content that must NEVER be cached.
    They are derived from the live crawl to populate the plan on a cache hit.
    """
    # Build a content_map from headings and text
    content_map: dict[str, str] = {}
    for section in crawl_result.sections:
        heading = section.get("heading", "")
        text = section.get("text", "")
        if heading:
            content_map[heading] = text[:500] if text else ""

    # Build content_sections from crawl sections
    content_sections = []
    for section in crawl_result.sections:
        content_sections.append(
            {
                "heading": section.get("heading", ""),
                "content_summary": (section.get("text", "") or "")[:300],
                "content_type": section.get("type", ""),
                "importance": 5,
                "exact_text": (section.get("text", "") or "")[:500],
            }
        )

    return {
        "brand": {
            "name": crawl_result.title or "",
            "tagline": crawl_result.meta_description or "",
            "voice_tone": "",
            "industry": "",
            "personality": "",
        },
        "primary_goal": "",
        "target_audience": "",
        "visual_identity": "",
        "content_sections": content_sections,
        "content_absent": [],
        "key_content": crawl_result.text_content[:2000] if crawl_result.text_content else "",
        "headline": crawl_result.title or "",
        "subheadline": crawl_result.meta_description or "",
        "cta_primary": {"text": "", "context": ""},
        "cta_secondary": {"text": "", "context": ""},
        "content_map": content_map,
        "content_warnings": [],
        "meta_title": crawl_result.title or "",
        "meta_description": crawl_result.meta_description or "",
    }


def run_redesign_pipeline(
    crawl_result: CrawlResult,
    settings: Settings,
    progress_callback: ProgressCallback = None,
    tier: str = "premium",
    checkpoint: dict | None = None,
    checkpoint_callback: CheckpointCallback = None,
    model_provider: str = "claude",
    user_prompt: str = "",
) -> str:
    """
    Execute the redesign pipeline.

    If use_component_pipeline is enabled and components are available, uses:
        Planner → Component Selector → Composer → React Build

    Otherwise falls back to:
        Planner → Builder (HTML generation)

    Args:
        crawl_result: The crawled website data.
        settings: Application settings with model config.
        progress_callback: Optional callable(event, data) fired before each step.
        tier: "free" (Ollama) or "premium" (Claude/Gemini).
        checkpoint: Optional checkpoint dict to resume from.
        checkpoint_callback: Optional callable(step_name, data) fired after each step.
        model_provider: "claude" or "gemini".

    Returns:
        RedesignResult with HTML and optional build directory.
    """
    # Determine if we should use the component pipeline
    use_components = (
        settings.use_component_pipeline
        and settings.components_dir.exists()
        and settings.redesign_template_dir.exists()
    )
    if use_components:
        try:
            from sastaspace.react_builder import is_node_available  # noqa: I001 — optional module, guarded by try/except ImportError

            if not is_node_available():
                logger.warning("Node.js not available — falling back to HTML pipeline")
                use_components = False
        except ImportError:
            use_components = False

    steps = COMPONENT_PIPELINE_STEPS if use_components else PIPELINE_STEPS
    pipeline_label = "component" if use_components else "html"

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
        except Exception:  # noqa: BLE001
            pass

    def _checkpoint(step_name: str, accumulated: dict) -> None:
        if checkpoint_callback is None:
            return
        try:
            checkpoint_callback(step_name, {"completed_step": step_name, "data": accumulated})
        except Exception:  # noqa: BLE001
            pass

    if crawl_result.error:
        raise RedesignError(f"Cannot redesign -- crawl failed: {crawl_result.error}")

    resume_idx = 0
    restored: dict = {}
    if checkpoint:
        resume_idx, restored = _restore_from_checkpoint(checkpoint, steps)
        if resume_idx > 0:
            logger.info("Resuming pipeline from step %d/%d", resume_idx + 1, len(steps))

    def _should_run(step_name: str) -> bool:
        return steps.index(step_name) >= resume_idx

    pipeline_start = time.monotonic()
    status = "success"
    cp_data: dict = {}

    try:
        # Step 1: Planner -- analyze + design + copy (shared by both paths)
        if _should_run("planner"):
            n_steps = len(steps)
            logger.info(
                "Pipeline step 1/%d: Planner (tier=%s, provider=%s, mode=%s)",
                n_steps,
                tier,
                model_provider,
                pipeline_label,
            )
            _emit("planner")

            # Check plan cache — skip the LLM call if we have a cached skeleton
            # and the user hasn't provided custom instructions (which need a fresh plan)
            cached_skeleton = None
            if settings.enable_plan_cache and not user_prompt:
                cached_skeleton = _try_plan_cache(crawl_result)

            if cached_skeleton is not None:
                # Cache HIT — build plan from cached skeleton + live crawl content
                live_content = _content_from_crawl(crawl_result)
                merged = merge_cached_plan(cached_skeleton, live_content)
                plan = RedesignPlan.model_validate(merged)
                logger.info(
                    "PLANNER RESULT (cached) | brand=%s layout=%s",
                    plan.brand.name,
                    plan.layout_archetype,
                )
            else:
                # Cache MISS — run Planner LLM normally
                plan = _run_planner(crawl_result, settings, tier, model_provider, user_prompt)

                # Cache the structural skeleton for future reuse
                if settings.enable_plan_cache and plan.site_type and plan.layout_archetype:
                    try:
                        cache_plan(plan.site_type, plan.layout_archetype, plan.model_dump())
                    except Exception:  # noqa: BLE001 — caching is best-effort
                        logger.debug("Plan cache store failed (non-fatal)")

            cp_data["plan"] = plan.model_dump_json()
            _checkpoint("planner", cp_data)
        else:
            plan = restored.get("plan", RedesignPlan())

        if use_components:
            # --- Component Pipeline ---

            # Step 2: Select components
            if _should_run("component_selector"):
                logger.info("Pipeline step 2/%d: Component Selector", len(steps))
                _emit("component_selector")
                manifest = select_components(plan.model_dump(), settings.components_dir)
                logger.info(
                    "Selected %d components: %s",
                    len(manifest.components),
                    [c.title for c in manifest.components],
                )
                _checkpoint("component_selector", cp_data)
            else:
                manifest = ComponentManifest()

            # Step 3: Compose React page
            if _should_run("composer"):
                logger.info(
                    "Pipeline step 3/%d: Composer (provider=%s)", len(steps), model_provider
                )
                _emit("composer")
                react_files = _run_composer(
                    plan, manifest, crawl_result, settings, tier, model_provider
                )
                _checkpoint("composer", cp_data)
            else:
                react_files = {}

            # Step 4: Build with Vite
            if _should_run("react_build"):
                logger.info("Pipeline step 4/%d: React Build", len(steps))
                _emit("react_build")
                result = _run_react_build(react_files, manifest, settings)
                cp_data["html"] = result.html
                _checkpoint("react_build", cp_data)
            else:
                result = RedesignResult(html=restored.get("html", ""))

            return result

        else:
            # --- Legacy HTML Pipeline ---

            # Step 2: Builder -- generate HTML
            if _should_run("builder"):
                use_parallel = settings.enable_parallel_builder
                logger.info(
                    "Pipeline step 2/%d: Builder (tier=%s, provider=%s, parallel=%s)",
                    len(steps),
                    tier,
                    model_provider,
                    use_parallel,
                )
                _emit("builder")
                if use_parallel:
                    html = _run_parallel_builder(plan, crawl_result, settings, tier, model_provider)
                else:
                    html = _run_builder(plan, crawl_result, settings, tier, model_provider)
                cp_data["html"] = html
                _checkpoint("builder", cp_data)
            else:
                html = restored.get("html", "")

            return RedesignResult(html=html)

    except RedesignError:
        status = "failure"
        raise
    except Exception as exc:  # noqa: BLE001 — top-level handler
        status = "failure"
        raise RedesignError(f"Pipeline failed: {exc}") from exc
    finally:
        duration = time.monotonic() - pipeline_start
        redesign_pipeline_duration_seconds.labels(tier=tier, status=status).observe(duration)
        redesign_pipeline_total.labels(tier=tier, status=status).inc()
        logger.info(
            "Pipeline completed in %.1fs (status=%s, mode=%s)", duration, status, pipeline_label
        )
