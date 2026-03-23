# Component-Based React Redesign Pipeline

**Date**: 2026-03-24
**Status**: Implemented

## Problem

SastaSpace generates pure static HTML for redesigned websites. Meanwhile, the
`components/` directory contains 2,474 battle-tested React components (heroes,
features, pricing, testimonials, navbars, footers, etc.) from 21st.dev — with
Framer Motion animations, scroll reveals, and interactive hover effects. These
components produce far higher quality output than Claude generating HTML from
scratch.

## Solution

Replace the HTML Builder step with a 3-step component pipeline:

```
Planner (LLM) -> RedesignPlan
    |
Component Selector (Python) -> selects 6-12 gold-tier components
    |
Component Composer (LLM) -> React source files (App.tsx + components)
    |
React Builder (Vite) -> built HTML + JS + CSS bundle
    |
Deploy -> serves from sites/{subdomain}/
```

### Component Selector (`sastaspace/component_selector.py`)

Pure Python, no LLM needed. Algorithm:
1. Map plan sections (hero, features, pricing...) to component categories
2. Load `tiers.json` for each category — prefer gold, then silver
3. Score candidates by archetype match, site type affinity, and popularity
4. Return top match per section with full source code

### Component Composer (new LLM step)

Receives the plan + selected component source code. Outputs React files:
- `src/App.tsx` — imports and composes all components with real content
- `src/globals.css` — CSS variables mapped from plan colors
- Modified component files if branding adjustments needed

Key rules: replace Next.js imports (next/link, next/image), remove "use client",
wire content_map text into component props.

### React Builder (`sastaspace/react_builder.py`)

Runs `vite build` in a temp directory using `redesign-template/` as the base.
Template has all common deps pre-installed (React, Framer Motion, Tailwind,
Lucide, Radix UI). Build takes ~5s.

### Deployment

`deploy()` now accepts an optional `build_dir` parameter. When provided, copies
the entire Vite `dist/` output (index.html + assets/) instead of writing a
single HTML file. The existing static file server already handles subdirectory
assets via `/{subdomain}/{path}`.

## Configuration

- `use_component_pipeline: bool = True` — enables the React pipeline
- `components_dir: Path = ./components` — component library location
- `redesign_template_dir: Path = ./redesign-template` — Vite template

Falls back to legacy HTML pipeline if Node.js unavailable, components dir
missing, or template dir missing.

## Files Changed/Created

### New
- `sastaspace/component_selector.py` — matching algorithm
- `sastaspace/react_builder.py` — Vite build step
- `redesign-template/` — Vite + React + Tailwind template project
- `sastaspace/agents/prompts.py` — COMPOSER_SYSTEM + COMPOSER_USER_TEMPLATE

### Modified
- `sastaspace/agents/pipeline.py` — added component pipeline path
- `sastaspace/html_utils.py` — added RedesignResult dataclass
- `sastaspace/redesigner.py` — returns RedesignResult
- `sastaspace/deployer.py` — build_dir parameter for bundle deploy
- `sastaspace/jobs.py` — handles RedesignResult
- `sastaspace/server.py` — handles RedesignResult
- `sastaspace/config.py` — new settings
- `backend/Dockerfile` — Node.js 22 + template deps pre-installed
