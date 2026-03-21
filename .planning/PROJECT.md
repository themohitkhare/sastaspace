# SastaSpace — AI Website Redesigner

## What This Is

SastaSpace is a lead generation tool and AI-powered website redesigner. Anyone can enter their domain URL and receive a free, Claude AI-generated redesign of their website — then hire the owner as a consultant to build the real thing. The full-stack application (FastAPI backend + Next.js frontend) is built and functional in development. Next step is production readiness via containerization and E2E testing.

## Core Value

Users see a stunning AI redesign of their own website and immediately want to hire you to make it real.

## Requirements

### Validated

- ✓ Playwright crawler extracts content, screenshots, and metadata from any URL — existing
- ✓ Claude AI (via claude-code-api gateway) redesigns sites into single-file HTML — existing
- ✓ FastAPI preview server serves redesigned HTML locally at `localhost:8080/{subdomain}/` — existing
- ✓ CLI commands: `redesign`, `list`, `open`, `remove`, `serve` — existing
- ✓ Deployer manages subdomain registry and writes HTML to `sites/` directory — existing
- ✓ No Anthropic API key required — uses Claude Code subscription via local gateway — existing

### Validated

- ✓ Public landing page with URL input — hero section, Spotlight animation, URL validation — Validated in Phase 3: Core UI
- ✓ Real-time progress feedback — SSE client (fetch + ReadableStream), per-step animated indicators, AppFlow state machine — Validated in Phase 3: Core UI
- ✓ Redesign result page — sandboxed iframe teaser, shareable `/[subdomain]/` dynamic route — Validated in Phase 3: Core UI

### Validated

- ✓ Contact form CTA — Name, Email, Message fields with AnimatePresence success swap — Validated in Phase 4: Contact Form + Polish
- ✓ Mobile responsive — 375px viewport, no overflow, 44px touch targets — Validated in Phase 4: Contact Form + Polish
- ✓ Beautiful, professional design — shadcn v4, Spotlight animation, smooth SSE progress — Validated in Phases 3–4

### Active

- [ ] Docker Compose orchestration — single `docker compose up` runs backend, frontend, and claude-code-api
- [ ] E2E Playwright test suite — full user flow from landing → progress → result → contact form
- [ ] Feature flags — Turnstile behind `NEXT_PUBLIC_ENABLE_TURNSTILE` flag
- [ ] SEO & OG meta tags — social sharing previews, sitemap, structured data
- [ ] Production environment config — .env management, health checks, graceful shutdown
- [ ] Design assets — favicon, OG images, app icons via Stitch MCP

### Out of Scope

- User authentication / accounts — it's free and open, no login needed
- Billing / payments — lead gen model, not SaaS subscription
- Multiple redesign history per user — single-use flow, no persistence needed per visitor
- Cloud hosting migration — Docker runs locally, exposed via Cloudflare tunnel, not cloud-hosted
- Kubernetes / container orchestration — Docker Compose is sufficient for single-machine deployment

## Context

- **Backend**: Python 3.14, FastAPI, Playwright, OpenAI-compatible client → claude-code-api gateway
- **Frontend decision**: Next.js (React, SSR, good for SEO and public-facing landing pages)
- **Deployment**: Local machine (Mac) exposed via Cloudflare Zero Trust tunnel to the public internet
- **Business model**: Free tool for lead generation — users get a taste, then hire the owner as a web design consultant
- **Redesign time**: ~30-60 seconds per site (Playwright crawl + Claude generation)
- **Existing API**: FastAPI runs at `localhost:8080`, currently only serves static redesign files — needs a `/redesign` endpoint added
- **Contact form**: Submissions need to go somewhere — email (via SMTP/SendGrid) or a simple local store

## Constraints

- **Tech stack**: Next.js frontend, Python/FastAPI backend — keep these separate
- **Deployment**: Cloudflare tunnel exposes local ports — both Next.js and FastAPI need to be accessible
- **No auth**: Completely open, no signup required
- **Design quality**: The website is itself a portfolio piece — it must look exceptional

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Next.js for frontend | SSR for SEO, React ecosystem, strong design capabilities | ✓ Phase 2 |
| Full redesign view (not side-by-side) | Cleaner, more impactful first impression | ✓ Phase 3 — blurred iframe teaser on result page |
| SSE via fetch + ReadableStream (not EventSource) | POST-based SSE required for auth-ready future; EventSource is GET-only | ✓ Phase 3 |
| No time estimate on progress view | Avoids false expectations; decided in design contract D-07 | ✓ Phase 3 |
| Contact form (not booking link) | Allows async lead capture without requiring calendar integration | ✓ Phase 4 — Resend email delivery, honeypot + Turnstile spam protection |
| Local hosting via Cloudflare tunnel | User already has this setup, avoids hosting costs | — Pending |
| Keep backend as FastAPI (extend, don't replace) | Existing CLI already uses FastAPI preview server | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
## Current Milestone: v2.0 Production Ship

**Goal:** Make SastaSpace production-ready with Docker containerization, E2E tests, and polish.

**Target features:**
- Docker Compose with backend + frontend + claude-code-api gateway
- Playwright E2E test suite covering full user flow
- Feature flags for Turnstile (production vs dev)
- SEO/OG meta tags for social sharing
- Design assets (favicon, OG images) via Stitch MCP
- Production environment configuration

---
*Last updated: 2026-03-21 after v1.0 milestone archived — starting v2.0 Production Ship*
