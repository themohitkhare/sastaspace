# Swarm Redesign Pipeline — Design Spec

**Date:** 2026-03-26
**Status:** Draft
**Goal:** Replace the Agno multi-agent pipeline with a Claude Code CLI-based swarm orchestrator using Ruflo, Stitch, and Playwright MCP tools for dramatically better redesign quality.

---

## 1. Problem Statement

The current Agno pipeline (Planner → Builder/Composer) produces mediocre designs because:

- **Visual quality:** Layouts look generic, poor typography, weak color choices
- **No iteration:** Single-shot generation with no visual feedback loop
- **Content fidelity:** Hallucinated text, broken images, missing sections
- **Prompt-only enforcement:** Rules like "don't use placeholder images" are ignored by LLMs with no programmatic gate to catch violations

The new pipeline must produce portfolio-quality redesigns ($10k+ look) using a coordinated swarm of specialized AI agents with visual verification loops and programmatic quality gates.

---

## 2. Current State (Existing Infrastructure)

The codebase already has significant infrastructure that this design builds on:

| Module | What It Does | Status |
|--------|-------------|--------|
| `sastaspace/worker.py` | Redis Stream consumer with health checks, job processing loop | **Exists — extend** |
| `sastaspace/jobs.py` | `JobService` with enqueue, consumer groups, pub/sub status updates, checkpoint recovery | **Exists — extend** |
| `sastaspace/routes/redesign.py` | `POST /redesign` endpoint, job creation, `RedesignRequest` model | **Exists — modify** (add email field) |
| `sastaspace/routes/sse.py` | `redis_job_stream()` bridges Redis pub/sub to SSE for real-time progress | **Exists — keep** for status polling |
| `sastaspace/quality_scorer.py` | `score_redesign()` quality scoring | **Exists — integrate** into QA phase |
| `sastaspace/html_validator.py` | Accessibility validation | **Exists — integrate** into Static Analyzer |
| `sastaspace/agents/pipeline.py` | Agno pipeline with checkpointing, retry logic, parallel builder | **Exists — replace** (keep as fallback) |
| `sastaspace/config.py` | `Settings` with `redis_url`, `mongodb_url`, `claude_code_api_url` | **Exists — extend** |
| `components/index.json` | Component catalog with individual JSON files | **Exists — index** |

---

## 3. Architecture Overview

### Integration Layer

```
Frontend (k8s) → Backend (k8s) → Redis job queue (existing JobService)
                                         ↓
                                   Worker (existing sastaspace/worker.py)
                                   Python orchestrator (per-phase calls)
                                         ↓
                                   claude-code-api (per agent call)
                                         ↓
                                   Claude Code CLI sessions
                                   ├── Ruflo MCP (coordination)
                                   ├── Stitch MCP (design systems)
                                   ├── Playwright MCP (visual QA)
                                   └── Programmatic static analysis (Python)
```

**Key design decisions:**

1. **Async job model:** The backend no longer waits for completion. User submits URL + optional email. Backend enqueues via existing `JobService`. Frontend shows status page with phase-level progress polling via existing SSE infrastructure.

2. **Python orchestrator, not LLM orchestrator (C-2 fix):** The existing `worker.py` is extended with a Python state machine that drives the 6-phase pipeline. Each phase makes 1-3 calls to `claude-code-api` (one per agent). This avoids betting on a single LLM session to self-orchestrate 14 agents across 10-15 minutes. Phase transitions, retries, and checkpointing are handled in Python code, not in an LLM prompt.

3. **Email is optional (I-1 fix):** If email is provided, send notification on completion. If not, the status page polls for completion via existing Redis pub/sub → SSE bridge (`routes/sse.py`). This preserves the "no signup required" product constraint.

**Flow:**
1. User submits URL (+ optional email) on frontend
2. Backend creates job via existing `JobService.enqueue()`, returns `{ jobId }`
3. Frontend redirects to `/status/{jobId}` — polls for phase-level progress
4. Existing `worker.py` picks up job, runs Python orchestrator
5. Orchestrator calls `claude-code-api` once per agent (not one mega-prompt)
6. On completion: deploy to sites dir + update Redis status + optionally email via Resend
7. Frontend status page detects completion, redirects to result

### Connectivity

- Backend (MicroK8s) → Redis (`redis_url` in existing `config.py`) for job queue
- Worker (host or k8s) → Redis to pick up jobs via existing consumer group
- Worker → claude-code-api (`claude_code_api_url` = `http://192.168.0.37:8000/v1`) per agent call
- Worker → sites dir (existing `sites_dir` config) for deployment
- Worker → Resend API for optional email notification
- Claude Code CLI → Ruflo, Stitch, Playwright MCP (configured in Claude Code's MCP settings)

---

## 4. Pre-requisite: Component Catalog Index

Before any redesign runs, the existing component catalog (2,474+ components from `components/index.json` and individual component JSON files) must be pre-indexed into a searchable format.

**Indexing dimensions:**
- Category (hero, nav, footer, pricing, testimonial, CTA, feature-grid, etc.)
- Industry fit (e-commerce, SaaS, portfolio, blog, restaurant, agency)
- Layout type (bento, editorial, split-hero, asymmetric, minimal, full-bleed)
- Visual style (dark, light, gradient, glass, brutalist, corporate, playful)
- Complexity (simple, moderate, complex)
- Responsive level (basic, full, mobile-first)

**Indexing method:** LLM-assisted batch processing. Each component's JSON metadata + preview screenshot is analyzed by Claude (Haiku for cost efficiency) to assign the 6 indexing dimensions. Results stored in a structured JSON index.

**Index schema:**
```json
{
  "component_id": "hero-001",
  "name": "Split Hero with CTA",
  "source_path": "components/heroes/split-hero/",
  "category": "hero",
  "industry_fit": ["saas", "agency", "portfolio"],
  "layout_type": "split-hero",
  "visual_style": ["light", "corporate"],
  "complexity": "moderate",
  "responsive_level": "mobile-first",
  "embedding_vector": [0.12, ...],  // for semantic search via Ruflo embeddings
  "tags": ["cta", "image-left", "gradient-bg"]
}
```

**Query interface:** Dual-mode:
1. **Filter query:** JSON filter on category + industry + style (fast, deterministic)
2. **Semantic search:** Ruflo `mcp__ruflo__embeddings_search` for natural language queries like "hero section for a restaurant with dark theme" (flexible, AI-powered)

**Update trigger:** Re-index when components are added/removed/modified (git hook or `make index-components` command).

---

## 4. Agent Roster (14 Agents, 6 Phases)

### Phase 1 — ANALYSIS (parallel, then sequential review)

| Agent | Ruflo Role | Cognitive Pattern | Input | Output |
|-------|-----------|-------------------|-------|--------|
| **Site Classifier** | scout | systems | Crawl data, screenshot | Site type (blog/e-commerce/portfolio/SaaS/agency/restaurant/nonprofit/etc.), industry vertical, complexity score |
| **Content Extractor** | scout | systems | Crawl data, HTML | Strict content map: all text with location tags, all image URLs with context, all CTAs, nav structure, forms, pricing tables. This is the "source of truth" — no content outside this map may appear in the redesign. |
| **Business Analyzer** | scout | systems | Crawl data, meta tags, content | Business profile: industry, target audience, competitive positioning, value proposition, revenue model, key differentiators, brand voice/personality. Feeds into design and copy decisions. |
| **Spec Challenger** | specialist | lateral | All Phase 1 outputs | Adversarial review with structured output (see below). Must approve before Phase 2 begins. |

**Spec Challenger output schema:**
```json
{
  "approved": true/false,
  "issues": [
    {
      "category": "missing_content|wrong_classification|business_assumption|edge_case",
      "severity": "blocking|warning",
      "description": "...",
      "recommendation": "..."
    }
  ]
}
```
- If `approved: false` with blocking issues → re-run the specific Phase 1 agent that produced the faulty output with the issue description as feedback
- Max 2 re-runs per agent, max 3 total Spec Challenger iterations
- If still failing after 3 iterations → proceed with warnings logged, human review flagged

**Execution:** Site Classifier + Content Extractor + Business Analyzer run in parallel. Spec Challenger runs sequentially after all three complete.

**Output format decision logic (Site Classifier):**
- **HTML output** when: simple site (< 5 sections), no complex interactions, no product grids, blog or portfolio
- **React/Vite output** when: complex site (5+ sections), e-commerce, SaaS with pricing tables, interactive elements needed, component catalog has good matches
- Decision stored in Phase 1 output, used by Builder in Phase 4

### Phase 2 — DESIGN STRATEGY (parallel)

| Agent | Ruflo Role | Cognitive Pattern | Input | Output |
|-------|-----------|-------------------|-------|--------|
| **Color Palette Architect** | specialist | divergent | Brand colors from crawl, industry, business profile | Harmonious color palette using color theory (complementary/analogous/triadic). Industry-appropriate. Psychology-informed (warm for urgency, cool for trust). OKLCH format with hex fallbacks. |
| **UX Expert** | specialist | systems | Site type, business profile, content map, conversion goals | Information architecture, user flow, conversion funnel design. F/Z-pattern selection. Mobile-first wireframe logic. Industry-specific UX patterns (e.g., e-commerce needs product grid + cart flow, portfolio needs gallery + case studies). |
| **KISS Metric Expert** | specialist | critical | All Phase 1 outputs, content map | Complexity scores: cognitive load (1-10), visual noise budget, interaction cost limit, content density target. These scores constrain Phase 4 — Builder and Animation Specialist must respect them. |

### Phase 3 — SELECTION (parallel)

| Agent | Ruflo Role | Cognitive Pattern | Input | Output |
|-------|-----------|-------------------|-------|--------|
| **Component Selector** | worker | convergent | Site type, UX wireframe, design tokens, KISS scores, pre-indexed component catalog | Component manifest: exact components to use with file paths, layout placement, and customization notes. Queries the pre-built index, not LLM guessing. |
| **Copywriter** | specialist | adaptive | Content map, business profile, brand voice, UX flow | Polished copy for new layout: headlines, CTAs, microcopy, section descriptions. STRICT RULE: only improve/rephrase existing text. NEVER invent new content, features, testimonials, or statistics. |

### Phase 4 — BUILD (sequential)

| Agent | Ruflo Role | Cognitive Pattern | Input | Output |
|-------|-----------|-------------------|-------|--------|
| **Builder** | worker | convergent | Component manifest, design tokens, polished copy, UX wireframe, content map | Complete HTML or React output. Pure assembly — creative decisions already made. Uses exact components, exact colors, exact copy. Output format decided by Site Classifier in Phase 1. |
| **Animation Specialist** | specialist | divergent | Builder output, KISS scores | Enhanced output with: scroll reveals, micro-interactions, hover effects, page transitions. CSS-first, minimal JS. Amount of animation constrained by KISS score — simpler sites get fewer animations. |

### Phase 5 — QA SWARM (parallel, all must pass)

| Agent | Type | Checks | Gate |
|-------|------|--------|------|
| **Visual QA** | AI (Playwright) | Desktop + mobile screenshots. Scores: layout alignment, whitespace balance, typography hierarchy, color harmony, image rendering. Each 1-10. | Any score < 7 = BLOCK |
| **Content QA** | AI | Diff original text vs redesign output. Check every entry in content map appears in output. Flag hallucinated text, missing sections, broken links. | Any hallucinated content = BLOCK. Any missing section = BLOCK. |
| **Accessibility + SEO Auditor** | AI + Static | WCAG contrast ratios (4.5:1 minimum), heading hierarchy (h1→h2→h3, no skips), meta tags present, alt text on images, Open Graph tags, structured data. | Critical a11y fail = BLOCK |
| **Static Analyzer** | Programmatic (no AI) | See static checks list below. | Any check fail = BLOCK |

**Static Analyzer checks (programmatic gates):**
- HTML validation (or react-doctor for React output)
- Every `<img src>` URL resolves (HEAD request, or local file exists)
- Every internal `<a href="#section">` has a matching `id`
- No `placeholder.com`, `unsplash.com`, `example.com`, `via.placeholder` URLs
- No orphaned CSS classes (referenced in HTML but undefined in CSS)
- No external CDN dependencies (except Google Fonts)
- All Google Fonts `@import` URLs return 200
- `<!DOCTYPE html>` present, `</html>` closing tag present
- File/bundle size under 500KB (HTML) or 2MB (React build)
- No inline `console.log` or debug statements
- All CSS custom properties referenced are defined

**Iteration loop (hard gates, no consensus voting):**
1. All 4 QA agents run in parallel
2. Results collected, BLOCK/PASS for each
3. **Static Analyzer is deterministic — any failure is an unconditional BLOCK** (not subject to voting)
4. **AI QA agents:** all must pass. Any BLOCK → specific feedback extracted and sent to Builder (Phase 4 retry)
5. Max 3 iterations
6. After 3 fails: ship best-scoring version with a quality warning flag in metadata
7. No consensus voting for QA — quality gates are binary pass/fail, not opinion-based

**Per-agent timeouts:**
- Phase 1-3 agents: 120s per agent call
- Phase 4 Builder: 300s (large output)
- Phase 4 Animation: 120s
- Phase 5 QA agents: 60s each
- Static Analyzer: 30s (programmatic, no LLM)
- On timeout: skip agent with degraded output flag, do not block pipeline

### Phase 6 — DEPLOY

1. Deploy final output to sites directory (same as current `deployer.py`)
2. Update site registry (`_registry.json`)
3. Send email via Resend:
   - To: user's email (collected on frontend)
   - Subject: "Your AI Redesign of {domain} is Ready"
   - Body: Preview screenshot + link to `sastaspace.com/{subdomain}`
4. Update job status in Redis to "completed"
5. Store redesign metadata in MongoDB (site type, agent scores, iteration count, total time)

---

## 6. Ruflo Hive-Mind Configuration

```
Topology: hierarchical
Queen: python-orchestrator (the worker process)

Workers spawned per redesign:
- 4 scouts (Phase 1 analysis agents)
- 5 specialists (Phase 2-3 design + selection agents)
- 2 workers (Phase 4 build agents)
- 3 AI QA specialists + 1 programmatic checker (Phase 5)

Consensus strategy: NOT used for QA (hard gates instead)
Ruflo used for: agent lifecycle tracking, task assignment, coordination metrics
```

Each agent is represented as a Ruflo agent with:
- Unique ID: `redesign-{jobId}-{role}` (e.g., `redesign-abc123-visual-qa`)
- Status tracking via `mcp__ruflo__agent_status`
- Task assignment via `mcp__ruflo__task_assign`
- Completion via `mcp__ruflo__task_complete` with result data

---

## 7. Stitch MCP Integration

**Source of truth:** The Color Palette Architect (Phase 2) produces the canonical color palette and typography decisions. Stitch **consumes** these decisions — it does not generate its own independently.

**Flow:**
1. Color Palette Architect outputs: primary color (hex), secondary, accent, fonts, color mode, roundness
2. These feed into Stitch as inputs:

   a. `mcp__stitch__create_project` — Create a Stitch project for this redesign
   b. `mcp__stitch__create_design_system` — Apply the Architect's decisions:
      - `customColor` ← Architect's primary color
      - `overridePrimaryColor`, `overrideSecondaryColor` ← Architect's palette
      - `headlineFont`, `bodyFont` ← Architect's typography choices
      - `colorMode` ← Architect's light/dark decision
      - `roundness` ← Architect's corner radius decision
      - `designMd` ← markdown description of the brand aesthetic from Business Analyzer
   c. `mcp__stitch__generate_screen_from_text` — Generate 2-3 variant screens for key sections (hero, features, pricing) as visual references for the Builder
   d. `mcp__stitch__apply_design_system` — Apply the design system to generated screens

3. Stitch-generated design tokens + screen variants feed into the Builder (Phase 4) for component customization and visual reference.

---

## 8. Playwright MCP Integration

Used by **Visual QA** agent in Phase 5:

1. `mcp__plugin_playwright__browser_navigate` — Load the deployed redesign URL
2. `mcp__plugin_playwright__browser_take_screenshot` — Capture desktop viewport
3. `mcp__plugin_playwright__browser_resize` — Resize to mobile (375x812)
4. `mcp__plugin_playwright__browser_take_screenshot` — Capture mobile viewport
5. `mcp__plugin_playwright__browser_snapshot` — Get accessibility tree for a11y audit
6. `mcp__plugin_playwright__browser_network_requests` — Check for 404s on images/fonts
7. `mcp__plugin_playwright__browser_evaluate` — Run custom JS checks (contrast ratios, heading hierarchy)

Screenshots are passed to the Visual QA agent for AI-powered visual analysis.

---

## 9. Cost Analysis

### Per-agent token budget estimates

| Agent | Input Tokens | Output Tokens | Model Tier | Cost/Call |
|-------|-------------|---------------|------------|-----------|
| Site Classifier | ~5K | ~1K | Haiku (cheap) | ~$0.005 |
| Content Extractor | ~10K | ~3K | Haiku | ~$0.01 |
| Business Analyzer | ~5K | ~2K | Haiku | ~$0.007 |
| Spec Challenger | ~10K | ~1K | Sonnet | ~$0.04 |
| Color Palette Architect | ~3K | ~2K | Sonnet | ~$0.02 |
| UX Expert | ~8K | ~3K | Sonnet | ~$0.04 |
| KISS Metric Expert | ~5K | ~1K | Haiku | ~$0.005 |
| Component Selector | ~5K | ~2K | Sonnet | ~$0.025 |
| Copywriter | ~8K | ~3K | Sonnet | ~$0.04 |
| Builder | ~15K | ~15K | Opus (quality) | ~$0.75 |
| Animation Specialist | ~10K | ~5K | Sonnet | ~$0.06 |
| Visual QA | ~5K + screenshot | ~2K | Sonnet | ~$0.03 |
| Content QA | ~10K | ~2K | Haiku | ~$0.01 |
| A11y/SEO Auditor | ~5K | ~2K | Haiku | ~$0.005 |

**Per-redesign cost (no retries):** ~$1.05
**Per-redesign cost (3 QA retries):** ~$2.80 (Builder re-runs are the expensive part)
**Monthly projection (100 redesigns/month):** ~$105-280

**Model tier strategy:**
- **Haiku** (fast, cheap): Classification, content extraction, simple analysis
- **Sonnet** (balanced): Design decisions, UX, QA evaluation
- **Opus** (highest quality): Builder only — this is the critical output

**Cost comparison:** Current Agno pipeline uses 2-3 Sonnet calls ≈ $0.10-0.30 per redesign. New pipeline is 3-10x more expensive but quality improvement should justify it for a lead-gen tool where each redesign is a potential consulting sale.

**Cost controls:**
- Haiku for all analysis/classification (70% of agents)
- Only Builder uses Opus
- Static Analyzer is free (programmatic)
- Cache Phase 1 results for re-redesigns of the same site

---

## 10. Frontend Changes

### New Flow

Current: User enters URL → SSE stream → live progress → redirect to result
New: User enters URL + email → job submitted → waiting page → email notification

### URL Input Form Changes
- Add email field (**optional** — preserves "no signup required" constraint)
- Helper text: "Get notified when your redesign is ready (optional)"
- On submit: POST to backend `/redesign` which creates Redis job
- Response: `{ jobId }`
- Redirect to `/status/{jobId}` waiting page

### Waiting Page (`/status/[jobId]`)
- Poll `/api/jobs/{jobId}/status` every 15s for phase-level updates (via existing SSE infrastructure)
- Show current phase with engaging animations:
  - "Analyzing your website..." (Phase 1)
  - "Crafting your color palette..." (Phase 2)
  - "Selecting the perfect components..." (Phase 3)
  - "Building your new site..." (Phase 4)
  - "Running quality checks..." (Phase 5)
  - "Almost there — deploying..." (Phase 6)
- If email was provided: "We'll also email you when it's ready"
- On completion: auto-redirect to result page (same as current behavior)

### Email Template (via Resend)
- Subject: "Your AI Redesign of {domain} is Ready!"
- Hero: Desktop screenshot of the redesign
- CTA button: "View Your Redesign" → `sastaspace.com/{subdomain}`
- Footer: "Want this built for real? Contact us" → contact page

---

## 10. Backend Changes

### Modify existing: `POST /redesign` (`sastaspace/routes/redesign.py`)
- Add optional `email` field to `RedesignRequest` model
- Job creation already exists via `JobService.enqueue()` — add email to job payload
- Return `{ jobId, status: "queued" }` (existing pattern)

### Existing: `GET /api/jobs/{jobId}/status`
- Already exists in `routes/redesign.py` — extend with phase-level detail
- Include: current phase name, elapsed time, agent statuses

### Extend existing: Worker (`sastaspace/worker.py`)
- Add new `pipeline_type: "swarm"` job handler alongside existing Agno handler
- Python state machine drives the 6-phase pipeline:

```python
class SwarmOrchestrator:
    """Python orchestrator — one claude-code-api call per agent."""

    def run(self, job: dict) -> RedesignResult:
        # Phase 1: ANALYSIS (parallel calls)
        classifier_result = self._call_agent("site-classifier", crawl_data)
        content_result = self._call_agent("content-extractor", crawl_data)
        business_result = self._call_agent("business-analyzer", crawl_data)

        # Phase 1b: Spec Challenger (sequential)
        spec_review = self._call_agent("spec-challenger",
            [classifier_result, content_result, business_result])
        if not spec_review.approved:
            # Re-run failing agents with feedback, max 3 iterations
            ...

        # Phase 2-6: similar pattern — Python controls flow,
        # each agent is a single claude-code-api call with focused prompt
        ...

    def _call_agent(self, role: str, context: dict, timeout: int = 120) -> dict:
        """Make one call to claude-code-api with a role-specific prompt."""
        client = OpenAI(base_url=self.api_url, api_key="claude-code")
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": AGENT_PROMPTS[role]},
                {"role": "user", "content": json.dumps(context)},
            ],
            max_tokens=self.token_budgets[role],
            timeout=timeout,
        )
        return json.loads(response.choices[0].message.content)
```

Each agent call is a **focused, single-purpose prompt** to `claude-code-api`. The Python orchestrator handles:
- Phase sequencing and parallel execution (asyncio/ThreadPoolExecutor)
- Checkpoint saving between phases (existing `checkpoint_callback` pattern)
- Retry logic on failure
- Timeout enforcement per agent
- Progress reporting via Redis pub/sub (existing `JobService` pattern)
- Ruflo agent lifecycle management (spawn, track, complete)

### Agent prompts
Each agent gets its own system prompt stored in `sastaspace/agents/swarm_prompts.py`. Prompts are role-specific and focused (not a mega-prompt). Example for Site Classifier:

```python
SITE_CLASSIFIER_SYSTEM = """You are a website classification expert.
Analyze the crawled website data and classify it.

Output JSON:
{
  "site_type": "blog|ecommerce|portfolio|saas|agency|restaurant|nonprofit|other",
  "industry": "...",
  "complexity_score": 1-10,
  "output_format": "html|react",
  "output_format_reasoning": "...",
  "sections_detected": ["hero", "features", ...],
  "conversion_goals": ["..."]
}
"""
```

---

## 12. Data Flow Summary

```
User → Frontend → Backend → Redis
                                ↓
                          Host Worker
                                ↓
                     claude-code-api → Claude Code CLI
                                ↓
                     Ruflo hive-mind (hierarchical)
                                ↓
┌─────────────────────────────────────────────────┐
│ Phase 1: Site Classifier ─┐                     │
│          Content Extractor ├→ Spec Challenger    │
│          Business Analyzer ┘                     │
│                                                  │
│ Phase 2: Color Palette Architect ─┐              │
│          UX Expert                ├→ (parallel)  │
│          KISS Metric Expert ──────┘              │
│                                                  │
│ Phase 3: Component Selector ─┐                   │
│          Copywriter ─────────┘ (parallel)        │
│                                                  │
│ Phase 4: Builder → Animation Specialist          │
│                                                  │
│ Phase 5: Visual QA ──────┐                       │
│          Content QA ──────├→ Consensus Vote       │
│          A11y/SEO Auditor ├→ PASS or BLOCK       │
│          Static Analyzer ─┘  (→ retry Phase 4)   │
│                                                  │
│ Phase 6: Deploy + Email                          │
└─────────────────────────────────────────────────┘
```

---

## 13. Key Principles (from article + brainstorming)

1. **Gates over rules:** Every quality constraint has a programmatic check, not just a prompt instruction
2. **Adversarial review:** Spec Challenger reviews assumptions before design begins
3. **Multiple parallel reviewers:** 4 independent QA agents catch different categories of issues
4. **Explicit role boundaries:** Each agent has one job with clear inputs/outputs
5. **Content binding:** Content map is the strict source of truth — no hallucination possible when enforced by Content QA gate
6. **Iteration over perfection:** QA loop allows 3 refinement passes rather than demanding first-shot quality
7. **Async over blocking:** Email notification eliminates timeout issues and is better UX for long processes
8. **Industry-specific design:** Site Classifier + Business Analyzer ensure designs are tailored, not generic

---

## 14. Migration Path

1. **Phase A:** Build component catalog indexer (pre-requisite, no dependencies)
2. **Phase B:** Frontend changes — add optional email field, status page (can run parallel with A)
3. **Phase C:** Extend `worker.py` with SwarmOrchestrator + add email to `RedesignRequest`
4. **Phase D:** Write agent prompts + wire up Phase 1-4 agents via claude-code-api calls
5. **Phase E:** Add Stitch integration for design system generation (Phase 2 enhancement)
6. **Phase F:** Add Playwright visual QA loop (Phase 5)
7. **Phase G:** Add static analyzer programmatic gates (Phase 5)
8. **Phase H:** End-to-end testing on 10 test sites, quality comparison vs Agno
9. **Phase I:** Deprecate Agno pipeline, switch to swarm as default

The Agno pipeline remains as fallback during migration and for quick/cheap redesigns if needed.

---

## 15. Success Criteria

**Quality (measured on 10 test sites across 5 industries):**
- Redesign output quality rated 8+/10 by owner on a rubric: layout (1-10), typography (1-10), color (1-10), content fidelity (1-10), responsiveness (1-10)
- Baseline: current Agno pipeline rated on same rubric for comparison

**Content integrity (programmatic, measurable):**
- Zero hallucinated content in output (enforced by Content QA gate)
- Zero broken image URLs (enforced by Static Analyzer gate)
- 100% of original content map entries present in output

**Compliance (programmatic):**
- All redesigns pass WCAG 4.5:1 contrast requirements
- Valid HTML5 (no parser errors)

**Reliability:**
- Pipeline completes successfully on 90%+ of submissions
- Total pipeline time under 15 minutes for 90th percentile
- Email delivery (when email provided) within 5 minutes of pipeline completion

**Cost:**
- Average cost per redesign under $3.00 (including retries)
