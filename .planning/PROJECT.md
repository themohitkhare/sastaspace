# SastaSpace — AI Website Redesigner

## What This Is

SastaSpace is a lead generation tool and AI-powered website redesigner. Anyone can enter their domain URL and receive a free, Claude AI-generated redesign of their website — then hire the owner as a consultant to build the real thing. The backend CLI pipeline (crawl → AI redesign → preview) is already built; the next milestone is a beautiful public-facing web frontend.

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

### Active

- [ ] Public landing page with URL input — user enters a domain and submits
- [ ] Real-time progress feedback — user sees what's happening during the 30-60s redesign
- [ ] Redesign result page — full redesign shown in an iframe/preview with link to original
- [ ] Contact form CTA — "Like what you see? Let's build the real thing" → name, email, message
- [ ] API endpoint — FastAPI route that accepts a URL and streams/returns redesign status + result
- [ ] Beautiful, professional design — the site itself must look like a $5,000 website (it's a portfolio)
- [ ] Mobile responsive

### Out of Scope

- User authentication / accounts — it's free and open, no login needed
- Billing / payments — lead gen model, not SaaS subscription
- Multiple redesign history per user — single-use flow, no persistence needed per visitor
- Backend hosting migration — runs on local machine via Cloudflare Zero Trust tunnel, not cloud

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
| Next.js for frontend | SSR for SEO, React ecosystem, strong design capabilities | — Pending |
| Full redesign view (not side-by-side) | Cleaner, more impactful first impression | — Pending |
| Contact form (not booking link) | Allows async lead capture without requiring calendar integration | — Pending |
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
*Last updated: 2026-03-21 after initialization*
