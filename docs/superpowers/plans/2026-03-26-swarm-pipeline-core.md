# Swarm Redesign Pipeline — Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Python SwarmOrchestrator state machine, 14 agent prompts, static analyzer, and backend wiring so that redesign jobs can run through the new 6-phase swarm pipeline via the existing worker/Redis/MongoDB infrastructure.

**Architecture:** A Python state machine (`SwarmOrchestrator`) extends the existing `worker.py` job handler. Each of the 14 agents is a single focused call to `claude-code-api` via the OpenAI Python client. The orchestrator controls phase sequencing, parallel execution, retries, checkpointing, and progress reporting. The existing `JobService` pub/sub pushes phase-level updates to the frontend. A programmatic `StaticAnalyzer` enforces hard quality gates without LLM calls.

**Tech Stack:** Python 3.11+, FastAPI, OpenAI Python SDK (pointed at claude-code-api), Redis Streams, MongoDB (via existing `sastaspace/database.py`), Pydantic v2, pytest + pytest-asyncio.

**Spec:** `docs/superpowers/specs/2026-03-26-swarm-redesign-pipeline-design.md`

**Scope:** This plan covers Migration Phases C, D, and G from the spec. Phases A (component indexer), B (frontend), E (Stitch), F (Playwright QA), and H-I (E2E/switchover) are separate plans.

---

## File Map

### New Files

| File | Responsibility |
|------|---------------|
| `sastaspace/swarm/orchestrator.py` | `SwarmOrchestrator` class — state machine driving the 6-phase pipeline |
| `sastaspace/swarm/agent_caller.py` | `AgentCaller` — thin wrapper around OpenAI client for focused per-agent calls |
| `sastaspace/swarm/prompts.py` | System prompts for all 14 agents (one constant per agent) |
| `sastaspace/swarm/schemas.py` | Pydantic models for agent inputs/outputs (SiteClassification, ContentMap, BusinessProfile, etc.) |
| `sastaspace/swarm/static_analyzer.py` | Programmatic quality gates (HTML validation, broken images, placeholder URLs, font fallbacks) |
| `sastaspace/swarm/stitcher.py` | Python page assembler — merges per-section HTML fragments into final page |
| `sastaspace/swarm/__init__.py` | Public API: `SwarmOrchestrator`, `StaticAnalyzerResult` |
| `tests/test_swarm_schemas.py` | Unit tests for all Pydantic schema models |
| `tests/test_agent_caller.py` | Unit tests for AgentCaller (mocked OpenAI client) |
| `tests/test_static_analyzer.py` | Unit tests for all static analysis checks |
| `tests/test_stitcher.py` | Unit tests for HTML stitching |
| `tests/test_orchestrator.py` | Integration tests for SwarmOrchestrator (mocked agent calls) |

### Modified Files

| File | What Changes |
|------|-------------|
| `sastaspace/config.py` | Add `use_swarm_pipeline: bool`, `swarm_builder_model: str`, per-agent model settings |
| `sastaspace/jobs.py` | Add `email` to enqueue/handler, extend `redesign_handler` to dispatch to swarm |
| `sastaspace/routes/redesign.py` | Add optional `email` field to `RedesignRequest`, pass to enqueue |
| `sastaspace/database.py` | Add `email` field to `create_job()` and job document schema |

**Note:** `worker.py` is NOT modified — the swarm dispatch is wired into `redesign_handler` in `jobs.py`, which is already the handler called by `worker.py` via `process_messages()`.

---

## Task 1: Agent Output Schemas (Pydantic Models)

**Files:**
- Create: `sastaspace/swarm/__init__.py`
- Create: `sastaspace/swarm/schemas.py`
- Test: `tests/test_swarm_schemas.py`

These schemas define the contract between agents. Every agent outputs JSON matching one of these models.

- [ ] **Step 1: Create package and write schema tests**

```bash
mkdir -p sastaspace/swarm
touch sastaspace/swarm/__init__.py
```

```python
# tests/test_swarm_schemas.py
import pytest
from sastaspace.swarm.schemas import (
    SiteClassification,
    ContentMap,
    ContentSlot,
    BusinessProfile,
    SpecChallengerResult,
    SpecIssue,
    ColorPalette,
    UXWireframe,
    KISSMetrics,
    ComponentSlot,
    ComponentManifest,
    SlotMappedCopy,
    SectionFragment,
    AnimationEnhancement,
    VisualQAResult,
    ContentQAResult,
    A11ySEOResult,
)


class TestSiteClassification:
    def test_valid_classification(self):
        sc = SiteClassification(
            site_type="saas",
            industry="developer tools",
            complexity_score=7,
            output_format="react",
            output_format_reasoning="5+ sections with pricing table",
            sections_detected=["hero", "features", "pricing", "testimonials", "footer"],
            conversion_goals=["sign up for free trial"],
        )
        assert sc.site_type == "saas"
        assert sc.output_format in ("html", "react")

    def test_complexity_score_bounds(self):
        with pytest.raises(Exception):
            SiteClassification(
                site_type="blog",
                industry="tech",
                complexity_score=11,  # out of bounds
                output_format="html",
                output_format_reasoning="simple",
                sections_detected=["hero"],
                conversion_goals=[],
            )


class TestContentMap:
    def test_content_map_with_slots(self):
        cm = ContentMap(
            texts=[ContentSlot(location="hero.heading", content="Welcome to Acme")],
            image_urls=[{"url": "https://acme.com/logo.png", "context": "logo"}],
            ctas=["Sign Up Free"],
            nav_items=["Home", "About", "Pricing"],
            forms=[],
            pricing_tables=[],
        )
        assert len(cm.texts) == 1
        assert cm.texts[0].location == "hero.heading"


class TestSpecChallenger:
    def test_approved(self):
        r = SpecChallengerResult(approved=True, issues=[])
        assert r.approved

    def test_blocking_issue(self):
        r = SpecChallengerResult(
            approved=False,
            issues=[
                SpecIssue(
                    category="missing_content",
                    severity="blocking",
                    description="No pricing data extracted",
                    recommendation="Re-run content extractor with pricing focus",
                )
            ],
        )
        assert not r.approved
        assert r.issues[0].severity == "blocking"


class TestColorPalette:
    def test_requires_fallback_fonts(self):
        cp = ColorPalette(
            primary="#1a1a2e",
            secondary="#16213e",
            accent="#e94560",
            background="#0f3460",
            text="#eee",
            headline_font="'Inter', 'Helvetica Neue', Arial, sans-serif",
            body_font="'Source Sans 3', 'Segoe UI', sans-serif",
            color_mode="dark",
            roundness="8px",
            rationale="Dark theme for developer tools",
        )
        assert "sans-serif" in cp.headline_font
        assert "sans-serif" in cp.body_font


class TestKISSMetrics:
    def test_scores_in_range(self):
        k = KISSMetrics(
            cognitive_load=6,
            visual_noise_budget=4,
            interaction_cost_limit=3,
            content_density_target=5,
            animation_budget="moderate",
        )
        assert 1 <= k.cognitive_load <= 10


class TestComponentManifest:
    def test_slot_definitions(self):
        m = ComponentManifest(
            sections=[
                ComponentSlot(
                    section_name="hero",
                    component_id="hero-001",
                    component_path="marketing-blocks/heroes/aceternity__lamp.json",
                    slot_definitions={"heading": "string", "subheading": "string", "cta": "string"},
                    placement_order=0,
                )
            ]
        )
        assert m.sections[0].slot_definitions["heading"] == "string"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_swarm_schemas.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'sastaspace.swarm.schemas'`

- [ ] **Step 3: Implement schemas**

```python
# sastaspace/swarm/schemas.py
"""Pydantic models for swarm agent inputs and outputs."""
from __future__ import annotations

from pydantic import BaseModel, Field


# --- Phase 1: Analysis ---


class SiteClassification(BaseModel):
    site_type: str = Field(description="blog|ecommerce|portfolio|saas|agency|restaurant|nonprofit|other")
    industry: str
    complexity_score: int = Field(ge=1, le=10)
    output_format: str = Field(description="html|react", pattern=r"^(html|react)$")
    output_format_reasoning: str
    sections_detected: list[str]
    conversion_goals: list[str]


class ContentSlot(BaseModel):
    location: str = Field(description="Dot-notation location, e.g. 'hero.heading'")
    content: str


class ContentMap(BaseModel):
    texts: list[ContentSlot]
    image_urls: list[dict]
    ctas: list[str]
    nav_items: list[str]
    forms: list[dict] = Field(default_factory=list)
    pricing_tables: list[dict] = Field(default_factory=list)


class BusinessProfile(BaseModel):
    industry: str
    target_audience: str
    value_proposition: str
    revenue_model: str
    key_differentiators: list[str]
    brand_voice: str
    competitive_positioning: str = ""


class SpecIssue(BaseModel):
    category: str = Field(description="missing_content|wrong_classification|business_assumption|edge_case")
    severity: str = Field(description="blocking|warning", pattern=r"^(blocking|warning)$")
    description: str
    recommendation: str


class SpecChallengerResult(BaseModel):
    approved: bool
    issues: list[SpecIssue] = Field(default_factory=list)


# --- Phase 2: Design Strategy ---


class ColorPalette(BaseModel):
    primary: str
    secondary: str
    accent: str
    background: str
    text: str
    headline_font: str = Field(description="Must include web-safe fallback stack")
    body_font: str = Field(description="Must include web-safe fallback stack")
    color_mode: str = Field(description="light|dark", pattern=r"^(light|dark)$")
    roundness: str
    rationale: str = ""


class UXWireframe(BaseModel):
    layout_pattern: str = Field(description="F-pattern|Z-pattern|single-column|dashboard")
    section_order: list[str] = Field(description="Ordered list of section names")
    conversion_funnel: list[str] = Field(description="AIDA stages mapped to sections")
    mobile_strategy: str = Field(default="stack-and-simplify")
    sticky_header: bool = True
    industry_patterns: list[str] = Field(default_factory=list)


class KISSMetrics(BaseModel):
    cognitive_load: int = Field(ge=1, le=10)
    visual_noise_budget: int = Field(ge=1, le=10)
    interaction_cost_limit: int = Field(ge=1, le=10)
    content_density_target: int = Field(ge=1, le=10)
    animation_budget: str = Field(description="none|minimal|moderate|rich")


# --- Phase 3: Selection ---


class ComponentSlot(BaseModel):
    section_name: str
    component_id: str
    component_path: str
    slot_definitions: dict[str, str] = Field(description="slot_name -> type (string, list, etc.)")
    placement_order: int


class ComponentManifest(BaseModel):
    sections: list[ComponentSlot]


class SlotMappedCopy(BaseModel):
    slots: dict[str, str] = Field(description="Dot-notation slot -> polished copy text")
    unmapped_content: list[str] = Field(
        default_factory=list,
        description="Original content that couldn't be mapped to any slot",
    )


# --- Phase 4: Build ---


class SectionFragment(BaseModel):
    section_name: str
    html: str
    css: str = ""
    js: str = ""


class AnimationEnhancement(BaseModel):
    enhanced_html: str
    animations_added: list[str] = Field(default_factory=list)
    kiss_score_respected: bool = True


# --- Phase 5: QA ---


class VisualQAResult(BaseModel):
    layout_alignment: int = Field(ge=1, le=10)
    whitespace_balance: int = Field(ge=1, le=10)
    typography_hierarchy: int = Field(ge=1, le=10)
    color_harmony: int = Field(ge=1, le=10)
    image_rendering: int = Field(ge=1, le=10)
    passed: bool
    feedback: str = ""


class ContentQAResult(BaseModel):
    hallucinated_content: list[str] = Field(default_factory=list)
    missing_sections: list[str] = Field(default_factory=list)
    broken_links: list[str] = Field(default_factory=list)
    passed: bool
    feedback: str = ""


class A11ySEOResult(BaseModel):
    contrast_issues: list[str] = Field(default_factory=list)
    heading_issues: list[str] = Field(default_factory=list)
    missing_meta: list[str] = Field(default_factory=list)
    missing_alt_text: int = 0
    passed: bool
    feedback: str = ""
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_swarm_schemas.py -v
```

Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add sastaspace/swarm/__init__.py sastaspace/swarm/schemas.py tests/test_swarm_schemas.py
git commit -m "feat(swarm): add Pydantic schemas for 14-agent pipeline I/O contracts"
```

---

## Task 2: AgentCaller — Thin OpenAI Client Wrapper

**Files:**
- Create: `sastaspace/swarm/agent_caller.py`
- Test: `tests/test_agent_caller.py`

Wraps the OpenAI Python client for single-purpose agent calls with timeout, JSON parsing, and retry.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_agent_caller.py
import json
from unittest.mock import MagicMock, patch

import pytest

from sastaspace.swarm.agent_caller import AgentCaller, AgentCallError


class TestAgentCaller:
    def _make_caller(self):
        return AgentCaller(
            api_url="http://localhost:8000/v1",
            api_key="test-key",
            default_model="claude-sonnet-4-6-20250514",
        )

    def _mock_response(self, content: str):
        choice = MagicMock()
        choice.message.content = content
        resp = MagicMock()
        resp.choices = [choice]
        return resp

    @patch("sastaspace.swarm.agent_caller.OpenAI")
    def test_call_returns_parsed_json(self, mock_openai_cls):
        client = MagicMock()
        mock_openai_cls.return_value = client
        client.chat.completions.create.return_value = self._mock_response(
            '{"site_type": "saas", "industry": "dev tools"}'
        )

        caller = self._make_caller()
        result = caller.call(
            role="site-classifier",
            system_prompt="Classify this site.",
            context={"url": "https://example.com"},
            timeout=60,
        )
        assert result["site_type"] == "saas"

    @patch("sastaspace.swarm.agent_caller.OpenAI")
    def test_call_extracts_json_from_markdown_fence(self, mock_openai_cls):
        client = MagicMock()
        mock_openai_cls.return_value = client
        client.chat.completions.create.return_value = self._mock_response(
            'Here is the result:\n```json\n{"site_type": "blog"}\n```'
        )

        caller = self._make_caller()
        result = caller.call(
            role="site-classifier",
            system_prompt="Classify.",
            context={},
        )
        assert result["site_type"] == "blog"

    @patch("sastaspace.swarm.agent_caller.OpenAI")
    def test_call_returns_raw_string_when_not_json(self, mock_openai_cls):
        client = MagicMock()
        mock_openai_cls.return_value = client
        client.chat.completions.create.return_value = self._mock_response(
            "<!DOCTYPE html><html><body>Hello</body></html>"
        )

        caller = self._make_caller()
        result = caller.call_raw(
            role="builder",
            system_prompt="Build HTML.",
            context={},
        )
        assert result.startswith("<!DOCTYPE html>")

    @patch("sastaspace.swarm.agent_caller.OpenAI")
    def test_call_with_model_override(self, mock_openai_cls):
        client = MagicMock()
        mock_openai_cls.return_value = client
        client.chat.completions.create.return_value = self._mock_response('{"ok": true}')

        caller = self._make_caller()
        caller.call(
            role="builder",
            system_prompt="Build.",
            context={},
            model="claude-opus-4-6-20250514",
        )
        call_kwargs = client.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == "claude-opus-4-6-20250514"

    @patch("sastaspace.swarm.agent_caller.OpenAI")
    def test_call_raises_on_empty_response(self, mock_openai_cls):
        client = MagicMock()
        mock_openai_cls.return_value = client
        client.chat.completions.create.return_value = self._mock_response("")

        caller = self._make_caller()
        with pytest.raises(AgentCallError, match="Empty response"):
            caller.call(role="test", system_prompt="Test.", context={})

    @patch("sastaspace.swarm.agent_caller.OpenAI")
    def test_call_with_max_tokens(self, mock_openai_cls):
        client = MagicMock()
        mock_openai_cls.return_value = client
        client.chat.completions.create.return_value = self._mock_response('{"ok": true}')

        caller = self._make_caller()
        caller.call(role="test", system_prompt="Test.", context={}, max_tokens=5000)
        call_kwargs = client.chat.completions.create.call_args
        assert call_kwargs.kwargs["max_tokens"] == 5000
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_agent_caller.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement AgentCaller**

```python
# sastaspace/swarm/agent_caller.py
"""Thin wrapper around OpenAI client for focused per-agent calls."""
from __future__ import annotations

import json
import logging
import re

from openai import OpenAI

_logger = logging.getLogger(__name__)

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL)


class AgentCallError(Exception):
    """Raised when an agent call fails."""


class AgentCaller:
    """Makes single-purpose calls to claude-code-api for individual agents."""

    def __init__(
        self,
        api_url: str = "http://localhost:8000/v1",
        api_key: str = "claude-code",
        default_model: str = "claude-sonnet-4-6-20250514",
    ):
        self._client = OpenAI(base_url=api_url, api_key=api_key)
        self._default_model = default_model

    def call(
        self,
        role: str,
        system_prompt: str,
        context: dict | list | str,
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        timeout: int = 120,
    ) -> dict:
        """Call an agent and return parsed JSON response.

        Handles JSON wrapped in markdown fences.
        """
        raw = self.call_raw(
            role=role,
            system_prompt=system_prompt,
            context=context,
            model=model,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        return self._parse_json(raw, role)

    def call_raw(
        self,
        role: str,
        system_prompt: str,
        context: dict | list | str,
        *,
        model: str | None = None,
        max_tokens: int = 16000,
        timeout: int = 120,
    ) -> str:
        """Call an agent and return raw string response (for HTML/code output)."""
        user_content = context if isinstance(context, str) else json.dumps(context)
        _logger.info("agent_call_start role=%s model=%s", role, model or self._default_model)

        response = self._client.chat.completions.create(
            model=model or self._default_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            max_tokens=max_tokens,
            timeout=timeout,
        )

        content = response.choices[0].message.content or ""
        if not content.strip():
            raise AgentCallError(f"Empty response from agent '{role}'")

        _logger.info("agent_call_done role=%s chars=%d", role, len(content))
        return content

    def _parse_json(self, raw: str, role: str) -> dict:
        """Extract JSON from raw response, handling markdown fences."""
        text = raw.strip()

        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown fence
        match = _JSON_FENCE_RE.search(text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Try finding first { to last }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass

        raise AgentCallError(
            f"Agent '{role}' returned non-JSON response: {text[:200]}..."
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_agent_caller.py -v
```

Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add sastaspace/swarm/agent_caller.py tests/test_agent_caller.py
git commit -m "feat(swarm): add AgentCaller with JSON extraction and model override"
```

---

## Task 3: Static Analyzer — Programmatic Quality Gates

**Files:**
- Create: `sastaspace/swarm/static_analyzer.py`
- Test: `tests/test_static_analyzer.py`

Deterministic checks that unconditionally block deployment. No LLM involved.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_static_analyzer.py
import pytest

from sastaspace.swarm.static_analyzer import StaticAnalyzer, StaticAnalyzerResult


VALID_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Test</title>
  <style>
    :root { --color-primary: #1a1a2e; }
    body { font-family: 'Inter', sans-serif; color: var(--color-primary); }
    .hero { background: #fff; }
    @media (max-width: 768px) { .hero { padding: 1rem; } }
  </style>
</head>
<body>
  <header><nav><a href="#features">Features</a></nav></header>
  <section id="features">
    <h1>Features</h1>
    <img src="https://example-real-site.com/logo.png" alt="Logo">
  </section>
  <footer>Footer</footer>
</body>
</html>"""


class TestStaticAnalyzer:
    def test_valid_html_passes(self):
        result = StaticAnalyzer.analyze(VALID_HTML)
        assert result.passed
        assert len(result.failures) == 0

    def test_missing_doctype_fails(self):
        html = "<html><body>No doctype</body></html>"
        result = StaticAnalyzer.analyze(html)
        assert not result.passed
        assert any("DOCTYPE" in f for f in result.failures)

    def test_missing_closing_html_fails(self):
        html = "<!DOCTYPE html><html><body>No closing tag"
        result = StaticAnalyzer.analyze(html)
        assert not result.passed
        assert any("</html>" in f for f in result.failures)

    def test_placeholder_url_detected(self):
        html = VALID_HTML.replace(
            "https://example-real-site.com/logo.png",
            "https://via.placeholder.com/300x200",
        )
        result = StaticAnalyzer.analyze(html)
        assert not result.passed
        assert any("placeholder" in f.lower() for f in result.failures)

    def test_unsplash_url_detected(self):
        html = VALID_HTML.replace(
            "https://example-real-site.com/logo.png",
            "https://images.unsplash.com/photo-123",
        )
        result = StaticAnalyzer.analyze(html)
        assert not result.passed
        assert any("unsplash" in f.lower() for f in result.failures)

    def test_missing_font_fallback_detected(self):
        html = VALID_HTML.replace(
            "font-family: 'Inter', sans-serif;",
            "font-family: 'Inter';",
        )
        result = StaticAnalyzer.analyze(html)
        assert not result.passed
        assert any("fallback" in f.lower() for f in result.failures)

    def test_broken_internal_anchor_detected(self):
        html = VALID_HTML.replace('id="features"', 'id="pricing"')
        result = StaticAnalyzer.analyze(html)
        assert not result.passed
        assert any("features" in f for f in result.failures)

    def test_console_log_detected(self):
        html = VALID_HTML.replace("</body>", "<script>console.log('debug')</script></body>")
        result = StaticAnalyzer.analyze(html)
        assert not result.passed
        assert any("console.log" in f for f in result.failures)

    def test_undefined_css_variable_detected(self):
        html = VALID_HTML.replace("color: var(--color-primary)", "color: var(--color-missing)")
        result = StaticAnalyzer.analyze(html)
        assert not result.passed
        assert any("--color-missing" in f for f in result.failures)

    def test_file_size_limit(self):
        huge = "<!DOCTYPE html><html><body>" + "x" * 600_000 + "</body></html>"
        result = StaticAnalyzer.analyze(huge)
        assert not result.passed
        assert any("size" in f.lower() for f in result.failures)

    def test_external_cdn_detected(self):
        html = VALID_HTML.replace(
            "</head>",
            '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5/dist/css/bootstrap.min.css"></head>',
        )
        result = StaticAnalyzer.analyze(html)
        assert not result.passed
        assert any("external" in f.lower() or "cdn" in f.lower() for f in result.failures)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_static_analyzer.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement StaticAnalyzer**

```python
# sastaspace/swarm/static_analyzer.py
"""Programmatic quality gates — no LLM, deterministic checks."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

# Banned placeholder URL patterns
_PLACEHOLDER_PATTERNS = re.compile(
    r"(placeholder\.com|via\.placeholder|unsplash\.com|images\.unsplash|"
    r"picsum\.photos|lorempixel|dummyimage\.com|placehold\.co|"
    r"example\.com/.*\.(jpg|png|gif|svg|webp))",
    re.IGNORECASE,
)

# External CDN patterns (Google Fonts allowed)
_EXTERNAL_CDN_RE = re.compile(
    r'(?:href|src)=["\']https?://(?!fonts\.googleapis\.com|fonts\.gstatic\.com)([^"\']+)',
    re.IGNORECASE,
)

_CDN_HOSTS = (
    "cdn.jsdelivr.net",
    "cdnjs.cloudflare.com",
    "unpkg.com",
    "cdn.tailwindcss.com",
    "stackpath.bootstrapcdn.com",
    "maxcdn.bootstrapcdn.com",
)

# Font family without fallback: matches 'FontName' or "FontName" not followed by a comma
_FONT_NO_FALLBACK_RE = re.compile(
    r"font-family\s*:\s*['\"][^'\"]+['\"](?:\s*;|\s*})",
    re.IGNORECASE,
)

# CSS custom property usage
_CSS_VAR_USE_RE = re.compile(r"var\(\s*(--[a-zA-Z0-9_-]+)\s*\)")
_CSS_VAR_DEF_RE = re.compile(r"(--[a-zA-Z0-9_-]+)\s*:")

_MAX_HTML_SIZE = 500_000  # 500KB


@dataclass
class StaticAnalyzerResult:
    passed: bool
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class _AnchorIDParser(HTMLParser):
    """Extract internal anchor hrefs and element IDs from HTML."""

    def __init__(self):
        super().__init__()
        self.internal_anchors: list[str] = []
        self.element_ids: set[str] = set()
        self.img_srcs: list[str] = []
        self.font_families: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if "id" in attrs_dict:
            self.element_ids.add(attrs_dict["id"])
        if tag == "a":
            href = attrs_dict.get("href", "")
            if href.startswith("#") and len(href) > 1:
                self.internal_anchors.append(href[1:])
        if tag == "img":
            src = attrs_dict.get("src", "")
            if src:
                self.img_srcs.append(src)


class StaticAnalyzer:
    """Deterministic HTML quality gate — any failure is an unconditional BLOCK."""

    @staticmethod
    def analyze(html: str) -> StaticAnalyzerResult:
        failures: list[str] = []
        warnings: list[str] = []

        # 1. DOCTYPE check
        if not html.strip().startswith("<!DOCTYPE html>") and not html.strip().startswith("<!doctype html>"):
            failures.append("Missing <!DOCTYPE html> declaration")

        # 2. Closing </html> tag
        if "</html>" not in html.lower():
            failures.append("Missing </html> closing tag")

        # 3. File size
        if len(html.encode("utf-8")) > _MAX_HTML_SIZE:
            failures.append(f"File size {len(html.encode('utf-8')):,} bytes exceeds {_MAX_HTML_SIZE:,} byte limit")

        # 4. Placeholder URLs
        placeholder_matches = _PLACEHOLDER_PATTERNS.findall(html)
        if placeholder_matches:
            unique = set(m if isinstance(m, str) else m[0] for m in placeholder_matches)
            for url in list(unique)[:5]:
                failures.append(f"Placeholder/stock URL detected: {url}")

        # 5. Parse HTML for anchors, IDs, images
        parser = _AnchorIDParser()
        try:
            parser.feed(html)
        except Exception:
            warnings.append("HTML parsing encountered errors")

        # 6. Internal anchor targets
        for anchor in parser.internal_anchors:
            if anchor not in parser.element_ids:
                failures.append(f"Internal anchor #{anchor} has no matching id attribute")

        # 7. console.log / debug statements
        if re.search(r"\bconsole\.(log|debug|warn|info|error)\s*\(", html):
            failures.append("console.log or debug statements found in output")

        # 8. External CDN dependencies
        for match in _EXTERNAL_CDN_RE.finditer(html):
            url = match.group(1)
            if any(host in url for host in _CDN_HOSTS):
                failures.append(f"External CDN dependency detected: {url[:80]}")

        # 9. Font fallback check
        font_no_fallback = _FONT_NO_FALLBACK_RE.findall(html)
        for decl in font_no_fallback:
            if "," not in decl:
                failures.append(f"Font declaration without web-safe fallback: {decl.strip()[:60]}")

        # 10. CSS custom property references vs definitions
        used_vars = set(_CSS_VAR_USE_RE.findall(html))
        defined_vars = set(_CSS_VAR_DEF_RE.findall(html))
        undefined = used_vars - defined_vars
        for var in sorted(undefined):
            failures.append(f"CSS custom property {var} is used but never defined")

        return StaticAnalyzerResult(
            passed=len(failures) == 0,
            failures=failures,
            warnings=warnings,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_static_analyzer.py -v
```

Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add sastaspace/swarm/static_analyzer.py tests/test_static_analyzer.py
git commit -m "feat(swarm): add StaticAnalyzer with 10 programmatic quality gates"
```

---

## Task 4: HTML Stitcher — Deterministic Page Assembly

**Files:**
- Create: `sastaspace/swarm/stitcher.py`
- Test: `tests/test_stitcher.py`

Merges per-section HTML fragments into a complete page. No LLM — pure Python.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_stitcher.py
from sastaspace.swarm.schemas import SectionFragment, ColorPalette
from sastaspace.swarm.stitcher import stitch_page


class TestStitcher:
    def _palette(self):
        return ColorPalette(
            primary="#1a1a2e",
            secondary="#16213e",
            accent="#e94560",
            background="#ffffff",
            text="#333333",
            headline_font="'Inter', sans-serif",
            body_font="'Source Sans 3', sans-serif",
            color_mode="light",
            roundness="8px",
        )

    def test_basic_stitching(self):
        fragments = [
            SectionFragment(section_name="hero", html="<section><h1>Hello</h1></section>"),
            SectionFragment(section_name="features", html="<section><h2>Features</h2></section>"),
        ]
        result = stitch_page(fragments, self._palette(), "Test Site")
        assert "<!DOCTYPE html>" in result
        assert "</html>" in result
        assert "<h1>Hello</h1>" in result
        assert "<h2>Features</h2>" in result
        assert result.index("Hello") < result.index("Features")

    def test_includes_css_variables(self):
        fragments = [SectionFragment(section_name="hero", html="<section>Hi</section>")]
        result = stitch_page(fragments, self._palette(), "Test")
        assert "--color-primary: #1a1a2e" in result
        assert "--color-accent: #e94560" in result

    def test_includes_google_fonts(self):
        fragments = [SectionFragment(section_name="hero", html="<section>Hi</section>")]
        result = stitch_page(fragments, self._palette(), "Test")
        assert "fonts.googleapis.com" in result

    def test_merges_section_css(self):
        fragments = [
            SectionFragment(
                section_name="hero",
                html="<section class='hero'>Hi</section>",
                css=".hero { padding: 4rem; }",
            ),
        ]
        result = stitch_page(fragments, self._palette(), "Test")
        assert ".hero { padding: 4rem; }" in result

    def test_preserves_section_order(self):
        fragments = [
            SectionFragment(section_name="footer", html="<footer>End</footer>"),
            SectionFragment(section_name="hero", html="<section>Start</section>"),
        ]
        # Stitcher preserves input order — orchestrator controls order
        result = stitch_page(fragments, self._palette(), "Test")
        assert result.index("End") < result.index("Start")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_stitcher.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement stitcher**

```python
# sastaspace/swarm/stitcher.py
"""Deterministic page assembly from section fragments."""
from __future__ import annotations

import re

from sastaspace.swarm.schemas import ColorPalette, SectionFragment


def _extract_font_name(font_stack: str) -> str:
    """Extract the first font name from a CSS font stack for Google Fonts import."""
    match = re.match(r"['\"]?([^'\",:]+)", font_stack.strip())
    return match.group(1).strip() if match else ""


def _google_fonts_import(palette: ColorPalette) -> str:
    """Generate Google Fonts @import for the palette's fonts."""
    fonts = set()
    for font_stack in (palette.headline_font, palette.body_font):
        name = _extract_font_name(font_stack)
        if name and name.lower() not in ("sans-serif", "serif", "monospace", "arial", "helvetica"):
            fonts.add(name.replace(" ", "+"))
    if not fonts:
        return ""
    families = "&".join(f"family={f}:wght@300;400;500;600;700" for f in sorted(fonts))
    return f'@import url("https://fonts.googleapis.com/css2?{families}&display=swap");'


def stitch_page(
    fragments: list[SectionFragment],
    palette: ColorPalette,
    title: str,
) -> str:
    """Assemble section fragments into a complete HTML page.

    Args:
        fragments: Ordered list of section HTML fragments.
        palette: Color palette for CSS custom properties.
        title: Page <title>.

    Returns:
        Complete HTML string starting with <!DOCTYPE html>.
    """
    fonts_import = _google_fonts_import(palette)

    # Collect per-section CSS
    section_css_parts = []
    for frag in fragments:
        if frag.css.strip():
            section_css_parts.append(f"/* {frag.section_name} */\n{frag.css}")

    section_css = "\n\n".join(section_css_parts)

    # Collect per-section JS
    section_js_parts = []
    for frag in fragments:
        if frag.js.strip():
            section_js_parts.append(f"// {frag.section_name}\n{frag.js}")

    section_js = "\n\n".join(section_js_parts)

    # Assemble body
    body_html = "\n\n".join(frag.html for frag in fragments)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    {fonts_import}

    :root {{
      --color-primary: {palette.primary};
      --color-secondary: {palette.secondary};
      --color-accent: {palette.accent};
      --color-background: {palette.background};
      --color-text: {palette.text};
      --font-headline: {palette.headline_font};
      --font-body: {palette.body_font};
      --radius: {palette.roundness};
    }}

    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      font-family: var(--font-body);
      color: var(--color-text);
      background: var(--color-background);
      line-height: 1.6;
      -webkit-font-smoothing: antialiased;
    }}
    h1, h2, h3, h4, h5, h6 {{ font-family: var(--font-headline); line-height: 1.2; }}
    img {{ max-width: 100%; height: auto; display: block; }}
    a {{ color: var(--color-accent); text-decoration: none; }}

    {section_css}
  </style>
</head>
<body>
  {body_html}
  {f'<script>{section_js}</script>' if section_js else ''}
</body>
</html>"""
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_stitcher.py -v
```

Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add sastaspace/swarm/stitcher.py tests/test_stitcher.py
git commit -m "feat(swarm): add deterministic HTML stitcher for section assembly"
```

---

## Task 5: Agent Prompts

**Files:**
- Create: `sastaspace/swarm/prompts.py`

All 14 agent system prompts as constants. No tests needed — prompts are validated through integration tests.

- [ ] **Step 1: Create prompts file**

```python
# sastaspace/swarm/prompts.py
"""System prompts for all 14 swarm agents.

Each prompt is a focused, single-purpose instruction. The Python orchestrator
controls sequencing — agents never see the full pipeline.
"""

# --- Phase 1: Analysis ---

SITE_CLASSIFIER_SYSTEM = """You are a website classification expert. Analyze the crawled website data and screenshot to classify this site.

You MUST output valid JSON with this exact schema:
{
  "site_type": "blog|ecommerce|portfolio|saas|agency|restaurant|nonprofit|other",
  "industry": "specific industry vertical",
  "complexity_score": 1-10,
  "output_format": "html|react",
  "output_format_reasoning": "why this format was chosen",
  "sections_detected": ["hero", "features", ...],
  "conversion_goals": ["primary CTA action"]
}

Output format decision logic:
- "html" when: simple site (< 5 sections), no complex interactions, blog or portfolio
- "react" when: complex site (5+ sections), e-commerce, SaaS with pricing, interactive elements

Output ONLY the JSON object. No explanation."""

CONTENT_EXTRACTOR_SYSTEM = """You are a meticulous content extraction specialist. Extract ALL text content, images, CTAs, and navigation from the crawled website data.

This content map is the STRICT source of truth. No content outside this map may appear in the redesign.

You MUST output valid JSON:
{
  "texts": [
    {"location": "hero.heading", "content": "exact text from site"},
    {"location": "hero.subheading", "content": "exact text"},
    ...
  ],
  "image_urls": [
    {"url": "https://...", "context": "logo|hero-bg|product|team|..."}
  ],
  "ctas": ["exact CTA button text"],
  "nav_items": ["Home", "About", ...],
  "forms": [{"type": "contact|newsletter|search", "fields": ["name", "email"]}],
  "pricing_tables": [{"tier": "...", "price": "...", "features": [...]}]
}

Rules:
- Extract EVERY piece of visible text with its semantic location
- Use dot-notation for locations: section.element (e.g., "features[0].title")
- Include ALL image URLs exactly as they appear in the HTML
- Do NOT add, rephrase, or summarize any content
- Output ONLY the JSON object."""

BUSINESS_ANALYZER_SYSTEM = """You are a business analyst. Analyze the crawled website to build a business profile that will inform design and copy decisions.

You MUST output valid JSON:
{
  "industry": "specific industry",
  "target_audience": "who visits this site and why",
  "value_proposition": "core offer in one sentence",
  "revenue_model": "how this business makes money",
  "key_differentiators": ["what sets them apart"],
  "brand_voice": "professional|casual|playful|authoritative|friendly|...",
  "competitive_positioning": "premium|budget|mid-market|niche"
}

Base your analysis ONLY on what's visible on the site. Do NOT invent information.
Output ONLY the JSON object."""

SPEC_CHALLENGER_SYSTEM = """You are an adversarial reviewer. You receive the outputs of three analysis agents (Site Classifier, Content Extractor, Business Analyzer) and challenge their assumptions.

Your job is to find problems BEFORE the expensive design/build phases begin.

You MUST output valid JSON:
{
  "approved": true/false,
  "issues": [
    {
      "category": "missing_content|wrong_classification|business_assumption|edge_case",
      "severity": "blocking|warning",
      "description": "specific problem found",
      "recommendation": "what to fix and which agent should re-run"
    }
  ]
}

Check for:
1. Missing content: Are there visible sections the Content Extractor missed?
2. Wrong classification: Does the site type match the actual content?
3. Business assumptions: Is the value proposition accurate based on the content?
4. Edge cases: Multilingual site? Single-page app? Under construction?

If everything looks correct, set approved=true with an empty issues array.
Output ONLY the JSON object."""

# --- Phase 2: Design Strategy ---

COLOR_PALETTE_ARCHITECT_SYSTEM = """You are a color and typography expert specializing in web design.

Given the brand's existing colors and industry context, design a harmonious color palette and typography system.

You MUST output valid JSON:
{
  "primary": "#hex",
  "secondary": "#hex",
  "accent": "#hex",
  "background": "#hex",
  "text": "#hex",
  "headline_font": "'Font Name', 'Fallback', sans-serif",
  "body_font": "'Font Name', 'Fallback', sans-serif",
  "color_mode": "light|dark",
  "roundness": "4px|8px|12px|9999px",
  "rationale": "brief explanation of choices"
}

Rules:
- Use the brand's existing colors as a starting point, improve subtly
- Apply color theory: complementary, analogous, or triadic harmonies
- Industry norms: tech=blues/purples, food=warm, finance=navy/green
- MUST include web-safe fallback fonts (sans-serif, serif, etc.)
- Use Google Fonts that are available (check fonts.google.com)
- Ensure 4.5:1 contrast ratio between text and background
- Output ONLY the JSON object."""

UX_EXPERT_SYSTEM = """You are a UX architect specializing in conversion-optimized web layouts.

Given the site classification, business profile, and content map, design the information architecture and user flow.

You MUST output valid JSON:
{
  "layout_pattern": "F-pattern|Z-pattern|single-column|dashboard",
  "section_order": ["nav", "hero", "features", "testimonials", "pricing", "cta", "footer"],
  "conversion_funnel": ["Attention: hero", "Interest: features", "Desire: testimonials", "Action: pricing/cta"],
  "mobile_strategy": "stack-and-simplify|tab-navigation|accordion-sections",
  "sticky_header": true,
  "industry_patterns": ["e-commerce: product grid above fold", "saas: social proof near CTA"]
}

Rules:
- Section order must use ONLY sections that exist in the content map
- Do NOT add sections that have no content to fill them
- Conversion funnel maps AIDA stages to actual sections
- Industry patterns are specific to the detected site type
- Output ONLY the JSON object."""

KISS_METRIC_EXPERT_SYSTEM = """You are a simplicity and cognitive load expert. Analyze the site and assign complexity constraints that the builder must respect.

You MUST output valid JSON:
{
  "cognitive_load": 1-10,
  "visual_noise_budget": 1-10,
  "interaction_cost_limit": 1-10,
  "content_density_target": 1-10,
  "animation_budget": "none|minimal|moderate|rich"
}

Guidelines:
- Simple blog/portfolio: cognitive_load 3-4, animation "minimal"
- SaaS landing page: cognitive_load 5-6, animation "moderate"
- E-commerce: cognitive_load 6-7, animation "moderate"
- Agency/creative: cognitive_load 7-8, animation "rich"

Lower scores = simpler design. The builder will be constrained by these scores.
Output ONLY the JSON object."""

# --- Phase 3: Selection ---

COMPONENT_SELECTOR_SYSTEM = """You are a UI component selection expert. Given the site type, UX wireframe, design tokens, and KISS scores, select the best components from the available catalog.

You receive a catalog index of available components with their categories and descriptions.

You MUST output valid JSON:
{
  "sections": [
    {
      "section_name": "hero",
      "component_id": "component-name",
      "component_path": "category-group/category/file.json",
      "slot_definitions": {
        "heading": "string",
        "subheading": "string",
        "cta": "string",
        "background_image": "url"
      },
      "placement_order": 0
    }
  ]
}

Rules:
- Select ONE component per section from the catalog
- Define slot_definitions: what content slots this component needs filled
- Only select sections that have content in the content map
- Prefer components matching the site type and visual style
- Respect KISS scores: low cognitive_load = simpler components
- Output ONLY the JSON object."""

COPYWRITER_SYSTEM = """You are a conversion copywriter. You receive the original content map AND a component manifest with slot definitions.

Your job: map the original content into the exact component slots. Polish the copy for the new layout, but NEVER invent new content.

You MUST output valid JSON:
{
  "slots": {
    "hero.heading": "polished heading text",
    "hero.subheading": "polished subheading",
    "hero.cta": "original CTA text",
    "features[0].title": "feature 1 title",
    "features[0].description": "feature 1 description"
  },
  "unmapped_content": ["any original content that didn't fit into any slot"]
}

STRICT RULES:
- Only fill slots that have matching original content
- Leave slots EMPTY (omit from JSON) rather than invent content
- NEVER create new features, testimonials, statistics, or quotes
- You may rephrase for clarity and impact, but the meaning must be identical
- CTA text should be kept as-is or made more action-oriented
- Output ONLY the JSON object."""

# --- Phase 4: Build ---

BUILDER_SECTION_SYSTEM = """You are an expert HTML/CSS developer. Build ONE section of a website page.

You receive:
- The component source code (TSX/HTML)
- Design tokens (colors, fonts, spacing)
- Copy for this section's slots
- UX placement instructions

Output a SINGLE HTML fragment for this section. Include inline CSS scoped to this section.

Rules:
- Use the design tokens as CSS custom properties (--color-primary, etc.)
- Fill content slots with the provided copy EXACTLY
- Keep all original image URLs — do NOT replace with placeholders
- Use semantic HTML5 elements (section, article, header, footer, nav)
- Make it fully responsive with @media queries
- Do NOT output <!DOCTYPE html>, <html>, <head>, or <body> tags — just the section fragment
- Do NOT use any external CSS frameworks (Bootstrap, Tailwind CDN)
- Output ONLY the HTML fragment."""

ANIMATION_SPECIALIST_SYSTEM = """You are a CSS animation expert. Enhance the provided HTML page with scroll reveals, micro-interactions, and hover effects.

You receive:
- The assembled HTML page
- KISS scores (animation_budget constrains how much you add)

Animation budget mapping:
- "none": Do not add any animations. Return the HTML unchanged.
- "minimal": Only add subtle hover effects on buttons/links. No scroll animations.
- "moderate": Add scroll-reveal fade-ins on sections + button hover effects.
- "rich": Add scroll reveals, parallax hints, counter animations, hover transforms.

Rules:
- CSS-first: Use @keyframes, transitions, and IntersectionObserver
- No external animation libraries (GSAP, Animate.css, etc.)
- Animations must not cause layout shift or hurt performance
- All animations should respect prefers-reduced-motion
- Output the COMPLETE enhanced HTML page (not a diff)."""

# --- Phase 5: QA ---

VISUAL_QA_SYSTEM = """You are a visual design quality reviewer. You receive desktop and mobile screenshots of a redesigned website.

Score each dimension 1-10:

You MUST output valid JSON:
{
  "layout_alignment": 1-10,
  "whitespace_balance": 1-10,
  "typography_hierarchy": 1-10,
  "color_harmony": 1-10,
  "image_rendering": 1-10,
  "passed": true/false,
  "feedback": "specific issues to fix, or empty if passed"
}

A score below 7 in ANY dimension means passed=false.
Be specific in feedback — "hero heading is too small" not "typography needs work".
Output ONLY the JSON object."""

CONTENT_QA_SYSTEM = """You are a content fidelity auditor. Compare the original content map against the redesigned HTML output.

Check:
1. Every text entry in the content map appears in the output (exact or close match)
2. No text appears in the output that wasn't in the content map (hallucination)
3. All image URLs from the content map are present
4. All internal links work

You MUST output valid JSON:
{
  "hallucinated_content": ["any text in output not from content map"],
  "missing_sections": ["sections from content map not in output"],
  "broken_links": ["any broken internal anchors"],
  "passed": true/false,
  "feedback": "specific issues to fix"
}

passed=false if ANY hallucinated content or missing sections.
Output ONLY the JSON object."""

A11Y_SEO_SYSTEM = """You are an accessibility and SEO auditor. Analyze the HTML for compliance issues.

Check:
1. Color contrast (text vs background) — minimum 4.5:1 ratio
2. Heading hierarchy: h1 → h2 → h3 (no skips)
3. All images have alt text
4. Meta tags: title, description, viewport present
5. Open Graph tags for social sharing
6. Semantic HTML structure

You MUST output valid JSON:
{
  "contrast_issues": ["specific elements with low contrast"],
  "heading_issues": ["h3 appears before h2", ...],
  "missing_meta": ["og:title", "og:description", ...],
  "missing_alt_text": 0,
  "passed": true/false,
  "feedback": "specific issues to fix"
}

passed=false if ANY critical contrast issue or heading hierarchy violation.
Output ONLY the JSON object."""
```

- [ ] **Step 2: Commit**

```bash
git add sastaspace/swarm/prompts.py
git commit -m "feat(swarm): add focused system prompts for all 14 pipeline agents"
```

---

## Task 6: SwarmOrchestrator — The State Machine

**Files:**
- Create: `sastaspace/swarm/orchestrator.py`
- Test: `tests/test_orchestrator.py`

The core state machine that drives the 6-phase pipeline.

- [ ] **Step 1: Write failing integration tests**

```python
# tests/test_orchestrator.py
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sastaspace.crawler import CrawlResult
from sastaspace.swarm.orchestrator import SwarmOrchestrator
from sastaspace.swarm.schemas import SiteClassification


def _crawl_result():
    return CrawlResult(
        url="https://example-site.com",
        title="Example Site",
        meta_description="A test site",
        html_source="<html><body><h1>Hello</h1></body></html>",
        headings=["Hello"],
        text_content="Hello world, this is a test site with features.",
        images=[{"url": "https://example-site.com/logo.png", "alt": "logo"}],
        colors=["#1a1a2e", "#e94560"],
        fonts=["Inter"],
        sections=[],
        navigation_links=[],
    )


class TestSwarmOrchestratorPhase1:
    """Test Phase 1: Analysis agents."""

    @patch("sastaspace.swarm.orchestrator.AgentCaller")
    def test_phase1_runs_three_agents_and_challenger(self, mock_caller_cls):
        caller = MagicMock()
        mock_caller_cls.return_value = caller

        # Mock the three parallel agents
        caller.call.side_effect = [
            # Site Classifier
            {
                "site_type": "saas",
                "industry": "dev tools",
                "complexity_score": 6,
                "output_format": "html",
                "output_format_reasoning": "simple site",
                "sections_detected": ["hero", "features"],
                "conversion_goals": ["sign up"],
            },
            # Content Extractor
            {
                "texts": [{"location": "hero.heading", "content": "Hello"}],
                "image_urls": [{"url": "https://example-site.com/logo.png", "context": "logo"}],
                "ctas": ["Sign Up"],
                "nav_items": ["Home"],
                "forms": [],
                "pricing_tables": [],
            },
            # Business Analyzer
            {
                "industry": "dev tools",
                "target_audience": "developers",
                "value_proposition": "Simple tools",
                "revenue_model": "SaaS subscription",
                "key_differentiators": ["easy to use"],
                "brand_voice": "professional",
                "competitive_positioning": "mid-market",
            },
            # Spec Challenger
            {"approved": True, "issues": []},
        ]

        orchestrator = SwarmOrchestrator(
            api_url="http://localhost:8000/v1",
            api_key="test",
        )
        result = orchestrator._run_phase1(_crawl_result())
        assert result["classification"]["site_type"] == "saas"
        assert result["content_map"]["ctas"] == ["Sign Up"]
        assert result["business_profile"]["industry"] == "dev tools"
        assert result["spec_approved"]

    @patch("sastaspace.swarm.orchestrator.AgentCaller")
    def test_phase1_retries_on_spec_rejection(self, mock_caller_cls):
        caller = MagicMock()
        mock_caller_cls.return_value = caller

        classifier_result = {
            "site_type": "blog",
            "industry": "tech",
            "complexity_score": 3,
            "output_format": "html",
            "output_format_reasoning": "simple",
            "sections_detected": ["hero"],
            "conversion_goals": [],
        }
        content_result = {
            "texts": [],
            "image_urls": [],
            "ctas": [],
            "nav_items": [],
            "forms": [],
            "pricing_tables": [],
        }
        business_result = {
            "industry": "tech",
            "target_audience": "readers",
            "value_proposition": "news",
            "revenue_model": "ads",
            "key_differentiators": [],
            "brand_voice": "casual",
            "competitive_positioning": "niche",
        }

        caller.call.side_effect = [
            classifier_result,
            content_result,
            business_result,
            # Challenger rejects
            {
                "approved": False,
                "issues": [
                    {
                        "category": "wrong_classification",
                        "severity": "blocking",
                        "description": "This is actually a SaaS site",
                        "recommendation": "Re-run classifier",
                    }
                ],
            },
            # Re-run classifier
            {**classifier_result, "site_type": "saas"},
            # Challenger approves
            {"approved": True, "issues": []},
        ]

        orchestrator = SwarmOrchestrator(api_url="http://localhost:8000/v1", api_key="test")
        result = orchestrator._run_phase1(_crawl_result())
        assert result["spec_approved"]
        assert result["classification"]["site_type"] == "saas"


class TestSwarmOrchestratorStaticAnalysis:
    """Test that static analysis blocks bad output."""

    def test_orchestrator_blocks_placeholder_urls(self):
        from sastaspace.swarm.static_analyzer import StaticAnalyzer

        bad_html = '<!DOCTYPE html><html><body><img src="https://via.placeholder.com/300"></body></html>'
        result = StaticAnalyzer.analyze(bad_html)
        assert not result.passed
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_orchestrator.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement SwarmOrchestrator**

```python
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
    ANIMATION_SPECIALIST_SYSTEM,
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
    VISUAL_QA_SYSTEM,
)
from sastaspace.swarm.schemas import (
    BusinessProfile,
    ColorPalette,
    ComponentManifest,
    ContentMap,
    KISSMetrics,
    SectionFragment,
    SiteClassification,
    SlotMappedCopy,
    SpecChallengerResult,
    UXWireframe,
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
    "builder": "opus",
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
    "animation": 120,
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

        # Parallel: 3 analysis agents
        with ThreadPoolExecutor(max_workers=3) as pool:
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
                elif "content" in issue.recommendation.lower() or "extractor" in issue.recommendation.lower():
                    results["content_map"] = self._caller.call(
                        role="content-extractor",
                        system_prompt=CONTENT_EXTRACTOR_SYSTEM,
                        context=crawl_context + f"\n\nPrevious issue: {issue.description}",
                        model=self._model_for("content-extractor"),
                    )

        if not spec_approved:
            _logger.warning("Spec Challenger did not approve after 3 iterations — proceeding with warnings")

        results["spec_approved"] = spec_approved
        self._emit("phase1_done", {"classification": results["classification"]})
        return results

    # --- Phase 2: Design Strategy ---

    def _run_phase2(self, phase1: dict) -> dict:
        """Run design agents: palette + UX + KISS (parallel)."""
        self._emit("phase2_start")
        design_context = {
            "classification": phase1["classification"],
            "content_map": phase1["content_map"],
            "business_profile": phase1["business_profile"],
        }

        with ThreadPoolExecutor(max_workers=3) as pool:
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
        """Run selection: Component Selector → Copywriter (sequential)."""
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
        kiss = KISSMetrics(**phase2["kiss"])

        sections = phase3["manifest"].get("sections", [])
        copy_slots = phase3["copy"].get("slots", {})

        # 4a: Build each section in parallel
        fragments: list[SectionFragment] = []

        def _build_section(section: dict) -> SectionFragment:
            section_context = {
                "section": section,
                "palette": phase2["palette"],
                "copy": {k: v for k, v in copy_slots.items() if k.startswith(section["section_name"])},
                "wireframe": phase2.get("wireframe", {}),
            }
            html = self._caller.call_raw(
                role="builder",
                system_prompt=BUILDER_SECTION_SYSTEM,
                context=section_context,
                model=self._model_for("builder"),
                max_tokens=4096,
                timeout=_TIMEOUTS["builder"],
            )
            return SectionFragment(section_name=section["section_name"], html=html)

        with ThreadPoolExecutor(max_workers=6) as pool:
            future_to_order = {
                pool.submit(_build_section, s): s.get("placement_order", i)
                for i, s in enumerate(sections)
            }
            indexed: list[tuple[int, SectionFragment]] = []
            for future in as_completed(future_to_order):
                order = future_to_order[future]
                indexed.append((order, future.result()))

        # Sort by placement order
        indexed.sort(key=lambda x: x[0])
        fragments = [frag for _, frag in indexed]

        # 4b: Stitch (deterministic)
        title = phase1.get("classification", {}).get("industry", "Site")
        assembled = stitch_page(fragments, palette, title)

        # 4c: Animation enhancement
        anim_context = {
            "html": assembled,
            "animation_budget": kiss.animation_budget,
            "kiss_scores": {
                "cognitive_load": kiss.cognitive_load,
                "visual_noise_budget": kiss.visual_noise_budget,
            },
        }
        enhanced = self._caller.call_raw(
            role="animation",
            system_prompt=ANIMATION_SPECIALIST_SYSTEM,
            context=anim_context,
            model=self._model_for("animation"),
            max_tokens=20000,
            timeout=_TIMEOUTS["animation"],
        )

        self._emit("phase4_done")
        return enhanced

    # --- Phase 5: QA ---

    def _run_phase5(self, html: str, phase1: dict) -> dict:
        """Run QA swarm: Visual QA + Content QA + A11y/SEO + Static Analyzer (parallel)."""
        self._emit("phase5_start")

        # Static Analyzer (deterministic, no LLM)
        static_result = StaticAnalyzer.analyze(html)

        # AI QA agents (parallel)
        content_qa_context = {
            "content_map": phase1["content_map"],
            "html": html[:30000],  # Truncate for token budget
        }
        a11y_context = {"html": html[:30000]}

        with ThreadPoolExecutor(max_workers=2) as pool:
            content_future = pool.submit(
                self._caller.call,
                role="content-qa",
                system_prompt=CONTENT_QA_SYSTEM,
                context=content_qa_context,
                model=self._model_for("content-qa"),
                timeout=_TIMEOUTS["content-qa"],
            )
            a11y_future = pool.submit(
                self._caller.call,
                role="a11y-seo",
                system_prompt=A11Y_SEO_SYSTEM,
                context=a11y_context,
                model=self._model_for("a11y-seo"),
                timeout=_TIMEOUTS["a11y-seo"],
            )

            content_qa = content_future.result()
            a11y_qa = a11y_future.result()

        # Note: Visual QA requires Playwright — deferred to separate plan (Phase F)
        # For now, visual_qa is a placeholder pass
        visual_qa = {"passed": True, "feedback": "Visual QA deferred — Playwright integration pending"}

        all_passed = (
            static_result.passed
            and content_qa.get("passed", False)
            and a11y_qa.get("passed", False)
        )

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

        # Phase 4 + 5: Build → QA loop (max 3 iterations)
        html = ""
        qa_report: dict = {}
        for iteration in range(1, 4):
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

        _logger.info("swarm_pipeline_done iterations=%d passed=%s", iteration, qa_report.get("passed"))

        return SwarmResult(
            html=html,
            quality_report=qa_report,
            iterations=iteration,
            phases_completed=phases_completed,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_orchestrator.py -v
```

Expected: ALL PASS

- [ ] **Step 5: Update `__init__.py` exports**

```python
# sastaspace/swarm/__init__.py
"""Swarm redesign pipeline — deterministic Python orchestrator with 14 specialized agents."""
from sastaspace.swarm.orchestrator import SwarmOrchestrator, SwarmResult
from sastaspace.swarm.static_analyzer import StaticAnalyzer, StaticAnalyzerResult

__all__ = ["SwarmOrchestrator", "SwarmResult", "StaticAnalyzer", "StaticAnalyzerResult"]
```

- [ ] **Step 6: Commit**

```bash
git add sastaspace/swarm/orchestrator.py sastaspace/swarm/__init__.py tests/test_orchestrator.py
git commit -m "feat(swarm): add SwarmOrchestrator state machine with 6-phase pipeline and QA loop"
```

---

## Task 7: Wire into Existing Worker + Config

**Files:**
- Modify: `sastaspace/config.py`
- Modify: `sastaspace/routes/redesign.py`
- Modify: `sastaspace/jobs.py`

- [ ] **Step 1: Add swarm config settings**

Add to `sastaspace/config.py` Settings class:

```python
    # Swarm pipeline
    use_swarm_pipeline: bool = False  # Feature flag — default off during migration
    swarm_builder_model: str = "claude-opus-4-6-20250514"
```

- [ ] **Step 2: Add optional email to RedesignRequest**

In `sastaspace/routes/redesign.py`, add to `RedesignRequest`:

```python
class RedesignRequest(BaseModel):
    url: str
    tier: str = "free"
    model_provider: str = "claude"
    prompt: str = ""
    force: bool = False
    email: str = ""  # Optional — for email notification on completion
```

- [ ] **Step 3: Pass email through the full job pipeline**

This requires coordinated changes across 4 files:

**a) `sastaspace/jobs.py` `enqueue()` (line ~117):**
- Add `email: str = ""` parameter
- Add `"email": email` to `stream_fields` dict (line ~140)

**b) `sastaspace/database.py` `create_job()`:**
- Add `email: str = ""` parameter
- Include `"email": email` in the MongoDB job document

**c) `sastaspace/jobs.py` `process_messages()` (line ~344):**
- Extract `email = msg_data.get("email", "")` alongside other fields
- Pass `email` to `handler()` call

**d) `sastaspace/jobs.py` `_recover_pending()` (line ~247):**
- Extract `email` from recovered message fields
- Pass to handler call

**e) `sastaspace/jobs.py` `redesign_handler()` signature (line ~409):**
- Add `email: str = ""` parameter (for future Phase 6 email notification)

**f) `sastaspace/routes/redesign.py` POST handler:**
- Pass `request.email` to `svc.enqueue(..., email=request.email)`

- [ ] **Step 4: Add swarm dispatch to redesign_handler**

In `sastaspace/jobs.py` `redesign_handler()`, add a swarm branch that **replaces the redesign step** (lines ~574-647) but **reuses** the existing deploy, sanitize, badge injection, quality scoring, and site registration logic that follows it.

```python
# Insert AFTER the crawl stage (after crawl_result is obtained, ~line 560)
# and INSTEAD OF the existing Agno redesign call (~lines 574-647).
# The code after redesign (validation, deploy, badge, quality score, registry)
# is REUSED as-is.

if settings.use_swarm_pipeline:
    import asyncio
    from sastaspace.swarm import SwarmOrchestrator

    # Capture the event loop BEFORE entering the thread
    _loop = asyncio.get_running_loop()

    def _on_swarm_progress(phase, data):
        # Map swarm phases to SSE events
        phase_map = {
            "phase1_start": ("analyzing", 15),
            "phase2_start": ("designing", 35),
            "phase3_start": ("selecting", 50),
            "phase4_start": ("building", 65),
            "phase5_start": ("reviewing", 80),
        }
        if phase in phase_map:
            event, progress = phase_map[phase]
            # Use run_coroutine_threadsafe — NOT get_event_loop()
            future = asyncio.run_coroutine_threadsafe(
                job_service.publish_status(job_id, event, {"progress": progress}),
                _loop,
            )
            future.result(timeout=5)  # Wait up to 5s for publish

    orchestrator = SwarmOrchestrator(
        api_url=settings.claude_code_api_url,
        api_key=settings.claude_code_api_key,
        progress_callback=_on_swarm_progress,
    )
    swarm_result = await asyncio.to_thread(orchestrator.run, crawl_result)
    html = swarm_result.html
    # Fall through to existing validation/deploy/quality scoring logic
else:
    # Existing Agno pipeline call (unchanged)
    ...
```

**Important integration notes:**
- The swarm branch replaces ONLY the redesign step (lines ~574-647 in current `redesign_handler`)
- All post-redesign logic (HTML validation, quality scoring, badge injection, sanitization, deploy, registry, Vikunja sync) is reused unchanged
- The `html` variable assignment is the contract between the redesign step and the post-processing steps
- The worker processes one job at a time (`BATCH_SIZE = 1`), so `ThreadPoolExecutor` nesting is safe

- [ ] **Step 5: Run existing tests to verify no regressions**

```bash
uv run pytest tests/ -v --timeout=30
```

Expected: ALL existing tests PASS (swarm is off by default)

- [ ] **Step 6: Commit**

```bash
git add sastaspace/config.py sastaspace/routes/redesign.py sastaspace/jobs.py
git commit -m "feat(swarm): wire SwarmOrchestrator into worker with use_swarm_pipeline feature flag"
```

---

## Task 8: Run Full Test Suite + Lint

- [ ] **Step 1: Run linter**

```bash
uv run ruff check sastaspace/ tests/
uv run ruff format --check sastaspace/ tests/
```

Expected: PASS

- [ ] **Step 2: Run all tests**

```bash
uv run pytest tests/ -v
```

Expected: ALL PASS (484 existing + ~20 new)

- [ ] **Step 3: Fix any issues**

- [ ] **Step 4: Final commit if any fixes**

```bash
git add -u
git commit -m "fix: lint and test fixes for swarm pipeline"
```

---

## Summary

| Task | What It Builds | Tests | Estimated Size |
|------|---------------|-------|----------------|
| 1 | Pydantic schemas (14 agent I/O contracts) | 8 test cases | ~200 lines |
| 2 | AgentCaller (OpenAI wrapper with JSON extraction) | 6 test cases | ~100 lines |
| 3 | StaticAnalyzer (10 programmatic gates) | 11 test cases | ~150 lines |
| 4 | HTML Stitcher (deterministic assembly) | 5 test cases | ~80 lines |
| 5 | Agent prompts (14 system prompts) | via integration tests | ~300 lines |
| 6 | SwarmOrchestrator (6-phase state machine) | 3 test cases | ~350 lines |
| 7 | Config + worker wiring | existing tests | ~30 lines changed |
| 8 | Full test suite verification | all tests | 0 new lines |

**What this plan does NOT cover (separate plans):**
- Phase A: Component catalog indexer
- Phase B: Frontend changes (email field, status page)
- Phase E: Stitch MCP integration
- Phase F: Playwright visual QA
- Phase H-I: E2E testing and migration switchover
