# sastaspace/swarm/orchestrator.py
"""Python state machine orchestrating the 6-phase swarm pipeline."""

from __future__ import annotations

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from sastaspace.crawler import CrawlResult
from sastaspace.swarm.agent_caller import AgentCaller
from sastaspace.swarm.prompts import (
    A11Y_SEO_SYSTEM,
    BUILDER_SECTION_SYSTEM,
    BUSINESS_ANALYZER_SYSTEM,
    COLOR_PALETTE_ARCHITECT_SYSTEM,
    COMPONENT_SELECTOR_SYSTEM,
    CONTENT_EXTRACTOR_SYSTEM,
    CONTENT_QA_SYSTEM,
    COPYWRITER_SYSTEM,
    KISS_METRIC_EXPERT_SYSTEM,
    SITE_CLASSIFIER_SYSTEM,
    SPEC_CHALLENGER_SYSTEM,
    UX_EXPERT_SYSTEM,
)
from sastaspace.swarm.schemas import (
    ColorPalette,
    SectionFragment,
    SpecChallengerResult,
)
from sastaspace.swarm.static_analyzer import StaticAnalyzer
from sastaspace.swarm.stitcher import stitch_page

_logger = logging.getLogger(__name__)

# Per-agent model tier assignments (spec Section 9)
_MODEL_TIERS = {
    "site-classifier": "haiku",
    "content-extractor": "haiku",
    "business-analyzer": "haiku",
    "spec-challenger": "sonnet",
    "color-palette": "sonnet",
    "ux-expert": "sonnet",
    "kiss-metrics": "haiku",
    "component-selector": "sonnet",
    "copywriter": "sonnet",
    "builder": "sonnet",  # Use sonnet until rate limits are resolved; switch to opus later
    "animation": "sonnet",
    "visual-qa": "sonnet",
    "content-qa": "haiku",
    "a11y-seo": "haiku",
}

# Per-agent timeout in seconds (spec Section 5)
_TIMEOUTS = {
    "site-classifier": 120,
    "content-extractor": 120,
    "business-analyzer": 120,
    "spec-challenger": 120,
    "color-palette": 120,
    "ux-expert": 120,
    "kiss-metrics": 120,
    "component-selector": 120,
    "copywriter": 120,
    "builder": 120,
    "animation": 300,
    "visual-qa": 60,
    "content-qa": 60,
    "a11y-seo": 60,
}

ProgressCallback = Callable[[str, dict], None] | None


@dataclass
class SwarmResult:
    html: str
    quality_report: dict = field(default_factory=dict)
    iterations: int = 1
    phases_completed: list[str] = field(default_factory=list)


class SwarmOrchestrator:
    """Drives the 6-phase swarm redesign pipeline.

    Each phase makes focused calls to claude-code-api via AgentCaller.
    The orchestrator controls sequencing, parallelism, retries, and quality gates.
    """

    def __init__(
        self,
        api_url: str = "http://localhost:8000/v1",
        api_key: str = "claude-code",
        models: dict[str, str] | None = None,
        progress_callback: ProgressCallback = None,
    ):
        self._caller = AgentCaller(api_url=api_url, api_key=api_key)
        self._models = models or {}
        self._progress = progress_callback

    def _model_for(self, role: str) -> str:
        """Resolve model ID for a given agent role."""
        if role in self._models:
            return self._models[role]
        tier = _MODEL_TIERS.get(role, "sonnet")
        # Default model IDs per tier — override via models dict
        return {
            "haiku": "claude-haiku-4-5-20251001",
            "sonnet": "claude-sonnet-4-6-20250514",
            "opus": "claude-opus-4-6-20250514",
        }.get(tier, "claude-sonnet-4-6-20250514")

    def _emit(self, phase: str, data: dict | None = None):
        if self._progress:
            self._progress(phase, data or {})

    # --- Phase 1: Analysis ---

    def _run_phase1(self, crawl: CrawlResult) -> dict:
        """Run analysis agents: classifier + extractor + analyzer (parallel), then challenger."""
        self._emit("phase1_start")
        crawl_context = crawl.to_prompt_context()

        # Parallel: 3 analysis agents (max 2 concurrent to avoid rate limits)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {
                pool.submit(
                    self._caller.call,
                    role="site-classifier",
                    system_prompt=SITE_CLASSIFIER_SYSTEM,
                    context=crawl_context,
                    model=self._model_for("site-classifier"),
                    timeout=_TIMEOUTS["site-classifier"],
                ): "classification",
                pool.submit(
                    self._caller.call,
                    role="content-extractor",
                    system_prompt=CONTENT_EXTRACTOR_SYSTEM,
                    context=crawl_context,
                    model=self._model_for("content-extractor"),
                    timeout=_TIMEOUTS["content-extractor"],
                ): "content_map",
                pool.submit(
                    self._caller.call,
                    role="business-analyzer",
                    system_prompt=BUSINESS_ANALYZER_SYSTEM,
                    context=crawl_context,
                    model=self._model_for("business-analyzer"),
                    timeout=_TIMEOUTS["business-analyzer"],
                ): "business_profile",
            }

            results = {}
            for future in as_completed(futures):
                key = futures[future]
                results[key] = future.result()

        # Sequential: Spec Challenger with retry loop
        spec_approved = False
        for iteration in range(3):
            challenger_input = {
                "classification": results["classification"],
                "content_map": results["content_map"],
                "business_profile": results["business_profile"],
            }
            challenger_result = self._caller.call(
                role="spec-challenger",
                system_prompt=SPEC_CHALLENGER_SYSTEM,
                context=challenger_input,
                model=self._model_for("spec-challenger"),
                timeout=_TIMEOUTS["spec-challenger"],
            )

            spec = SpecChallengerResult(**challenger_result)
            if spec.approved:
                spec_approved = True
                break

            # Re-run failing agents based on challenger feedback
            _logger.warning(
                "Spec Challenger rejected (iteration %d): %s",
                iteration + 1,
                [i.description for i in spec.issues if i.severity == "blocking"],
            )
            for issue in spec.issues:
                if issue.severity != "blocking":
                    continue
                if "classifier" in issue.recommendation.lower():
                    results["classification"] = self._caller.call(
                        role="site-classifier",
                        system_prompt=SITE_CLASSIFIER_SYSTEM,
                        context=crawl_context + f"\n\nPrevious issue: {issue.description}",
                        model=self._model_for("site-classifier"),
                    )
                elif (
                    "content" in issue.recommendation.lower()
                    or "extractor" in issue.recommendation.lower()
                ):
                    results["content_map"] = self._caller.call(
                        role="content-extractor",
                        system_prompt=CONTENT_EXTRACTOR_SYSTEM,
                        context=crawl_context + f"\n\nPrevious issue: {issue.description}",
                        model=self._model_for("content-extractor"),
                    )

        if not spec_approved:
            _logger.warning(
                "Spec Challenger did not approve after 3 iterations — proceeding with warnings"
            )

        results["spec_approved"] = spec_approved
        self._emit("phase1_done", {"classification": results["classification"]})
        return results

    # --- Phase 2: Design Strategy ---

    def _run_phase2(self, phase1: dict) -> dict:
        """Run design agents: palette + UX + KISS (parallel, max 2 concurrent)."""
        self._emit("phase2_start")
        design_context = {
            "classification": phase1["classification"],
            "content_map": phase1["content_map"],
            "business_profile": phase1["business_profile"],
        }

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {
                pool.submit(
                    self._caller.call,
                    role="color-palette",
                    system_prompt=COLOR_PALETTE_ARCHITECT_SYSTEM,
                    context=design_context,
                    model=self._model_for("color-palette"),
                    timeout=_TIMEOUTS["color-palette"],
                ): "palette",
                pool.submit(
                    self._caller.call,
                    role="ux-expert",
                    system_prompt=UX_EXPERT_SYSTEM,
                    context=design_context,
                    model=self._model_for("ux-expert"),
                    timeout=_TIMEOUTS["ux-expert"],
                ): "wireframe",
                pool.submit(
                    self._caller.call,
                    role="kiss-metrics",
                    system_prompt=KISS_METRIC_EXPERT_SYSTEM,
                    context=design_context,
                    model=self._model_for("kiss-metrics"),
                    timeout=_TIMEOUTS["kiss-metrics"],
                ): "kiss",
            }

            results = {}
            for future in as_completed(futures):
                results[futures[future]] = future.result()

        self._emit("phase2_done", {"color_mode": results["palette"].get("color_mode")})
        return results

    # --- Phase 3: Selection (sequential) ---

    def _run_phase3(self, phase1: dict, phase2: dict) -> dict:
        """Run selection: Component Selector -> Copywriter (sequential)."""
        self._emit("phase3_start")

        selection_context = {
            "classification": phase1["classification"],
            "content_map": phase1["content_map"],
            "wireframe": phase2["wireframe"],
            "palette": phase2["palette"],
            "kiss": phase2["kiss"],
        }

        # Step 1: Component Selector
        manifest = self._caller.call(
            role="component-selector",
            system_prompt=COMPONENT_SELECTOR_SYSTEM,
            context=selection_context,
            model=self._model_for("component-selector"),
            timeout=_TIMEOUTS["component-selector"],
        )

        # Step 2: Copywriter (needs manifest)
        copy_context = {
            "content_map": phase1["content_map"],
            "business_profile": phase1["business_profile"],
            "component_manifest": manifest,
        }
        copy = self._caller.call(
            role="copywriter",
            system_prompt=COPYWRITER_SYSTEM,
            context=copy_context,
            model=self._model_for("copywriter"),
            timeout=_TIMEOUTS["copywriter"],
        )

        self._emit("phase3_done")
        return {"manifest": manifest, "copy": copy}

    # --- Phase 4: Build (section-by-section) ---

    def _run_phase4(self, phase1: dict, phase2: dict, phase3: dict) -> str:
        """Build page section-by-section, stitch, then enhance with animations."""
        self._emit("phase4_start")
        palette = ColorPalette(**phase2["palette"])

        sections = phase3["manifest"].get("sections", [])
        copy_slots = phase3["copy"].get("slots", {})

        # 4a: Build each section sequentially (parallel hits rate limits on claude-code-api)
        fragments: list[SectionFragment] = []
        sorted_sections = sorted(sections, key=lambda s: s.get("placement_order", 0))

        for section in sorted_sections:
            section_context = {
                "section": section,
                "palette": phase2["palette"],
                "copy": {
                    k: v for k, v in copy_slots.items() if k.startswith(section["section_name"])
                },
                "wireframe": phase2.get("wireframe", {}),
            }
            _logger.info("building section=%s", section["section_name"])
            html = self._caller.call_raw(
                role="builder",
                system_prompt=BUILDER_SECTION_SYSTEM,
                context=section_context,
                model=self._model_for("builder"),
                max_tokens=8000,
                timeout=_TIMEOUTS["builder"],
            )

            # Validate builder output contains actual HTML, not an error message
            if "<" not in html or len(html) < 200:
                _logger.warning(
                    "builder returned non-HTML for section=%s chars=%d — skipping",
                    section["section_name"],
                    len(html),
                )
                continue

            fragments.append(SectionFragment(section_name=section["section_name"], html=html))

        # 4b: Stitch (deterministic)
        title = phase1.get("classification", {}).get("industry", "Site")
        assembled = stitch_page(fragments, palette, title)

        # 4c: Animation enhancement — SKIPPED for now
        # Passing the full assembled page (~40K chars) to the animation specialist
        # exceeds practical limits (response too large, timeouts). The stitcher already
        # includes base styles and CSS custom properties. Animations can be added in a
        # future iteration via targeted CSS injection rather than full-page rewrite.
        _logger.info("animation_skipped — page already has base styles from stitcher")

        self._emit("phase4_done")
        return assembled

    # --- Phase 5: QA ---

    def _safe_qa_call(self, role: str, system_prompt: str, context: dict) -> dict:
        """Call a QA agent, returning a degraded result on any failure."""
        try:
            return self._caller.call(
                role=role,
                system_prompt=system_prompt,
                context=context,
                model=self._model_for(role),
                timeout=_TIMEOUTS.get(role, 60),
            )
        except Exception as e:
            _logger.warning("QA agent '%s' failed: %s — treating as degraded pass", role, e)
            return {"passed": True, "feedback": f"QA agent '{role}' failed: {e}", "degraded": True}

    def _run_phase5(self, html: str, phase1: dict) -> dict:
        """Run QA swarm: Static Analyzer + Content QA + A11y/SEO (sequential, resilient)."""
        self._emit("phase5_start")

        # Static Analyzer (deterministic, no LLM) — hard gate
        static_result = StaticAnalyzer.analyze(html)

        # AI QA agents (sequential to avoid rate limits, resilient to failures)
        content_qa = self._safe_qa_call(
            "content-qa",
            CONTENT_QA_SYSTEM,
            {"content_map": phase1["content_map"], "html": html[:30000]},
        )

        a11y_qa = self._safe_qa_call(
            "a11y-seo",
            A11Y_SEO_SYSTEM,
            {"html": html[:30000]},
        )

        # Visual QA deferred — Playwright integration pending
        visual_qa = {
            "passed": True,
            "feedback": "Visual QA deferred — Playwright integration pending",
        }

        # Static analyzer is a hard gate; AI QA agents are advisory for now
        all_passed = static_result.passed

        feedback_parts = []
        if not static_result.passed:
            feedback_parts.extend(static_result.failures)
        if not content_qa.get("passed"):
            feedback_parts.append(content_qa.get("feedback", "Content QA failed"))
        if not a11y_qa.get("passed"):
            feedback_parts.append(a11y_qa.get("feedback", "A11y/SEO QA failed"))

        self._emit("phase5_done", {"passed": all_passed})
        return {
            "passed": all_passed,
            "static": {"passed": static_result.passed, "failures": static_result.failures},
            "content_qa": content_qa,
            "a11y_qa": a11y_qa,
            "visual_qa": visual_qa,
            "feedback": "\n".join(feedback_parts),
        }

    # --- Full Pipeline ---

    def run(self, crawl: CrawlResult) -> SwarmResult:
        """Execute the full 6-phase pipeline.

        Returns:
            SwarmResult with final HTML and quality report.
        """
        _logger.info("swarm_pipeline_start url=%s", crawl.url)

        # Phase 1: Analysis
        phase1 = self._run_phase1(crawl)
        phases_completed = ["analysis"]

        # Phase 2: Design Strategy
        phase2 = self._run_phase2(phase1)
        phases_completed.append("design")

        # Phase 3: Selection (sequential)
        phase3 = self._run_phase3(phase1, phase2)
        phases_completed.append("selection")

        # Phase 4 + 5: Build -> QA loop (1 iteration for now — each takes ~7 min)
        html = ""
        qa_report: dict = {}
        iteration = 1
        for iteration in range(1, 2):  # TODO: increase to 3 once pipeline is faster
            _logger.info("swarm_build_iteration %d", iteration)

            # Phase 4: Build
            html = self._run_phase4(phase1, phase2, phase3)
            phases_completed.append(f"build_iter{iteration}")

            # Phase 5: QA
            qa_report = self._run_phase5(html, phase1)
            phases_completed.append(f"qa_iter{iteration}")

            if qa_report["passed"]:
                _logger.info("swarm_qa_passed iteration=%d", iteration)
                break

            _logger.warning(
                "swarm_qa_failed iteration=%d feedback=%s",
                iteration,
                qa_report.get("feedback", "")[:200],
            )

        _logger.info(
            "swarm_pipeline_done iterations=%d passed=%s", iteration, qa_report.get("passed")
        )

        return SwarmResult(
            html=html,
            quality_report=qa_report,
            iterations=iteration,
            phases_completed=phases_completed,
        )
