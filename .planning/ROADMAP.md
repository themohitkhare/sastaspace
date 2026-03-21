# Roadmap: SastaSpace Web Frontend

## Overview

SastaSpace has a working CLI pipeline (crawl, redesign, deploy). This milestone delivers the public-facing web frontend: a FastAPI SSE endpoint hardened with rate limiting and sanitization, a Next.js App Router frontend with landing page, real-time progress experience, result display, and a contact form that converts visitors into consulting leads. The build order is dependency-driven: the API foundation must exist before the frontend can consume it, and the conversion layer ships before public promotion.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Secure API Foundation** - Extend FastAPI with SSE /redesign endpoint, rate limiting, HTML sanitization, and CORS
- [ ] **Phase 2: Next.js Scaffold + Wiring** - Scaffold Next.js 16 App Router in web/, install UI toolchain, configure dev workflow and tunnel
- [ ] **Phase 3: Core UI -- Landing + Progress + Result** - Build the complete user-facing flow from URL input through progress to redesign display
- [ ] **Phase 4: Contact Form + Polish** - Add lead capture contact form and final visual/responsive polish

## Phase Details

### Phase 1: Secure API Foundation
**Goal**: A hardened, streaming /redesign endpoint that the frontend can consume safely
**Depends on**: Nothing (first phase)
**Requirements**: API-01, API-02, API-03, API-04, API-05, API-06, API-07, API-08
**Success Criteria** (what must be TRUE):
  1. A POST request to /redesign with a valid URL returns an SSE stream with named step events (crawling, redesigning, deploying, done) and terminates with a result URL
  2. Submitting more than 3 requests per hour from the same IP returns a rate limit error
  3. A second concurrent redesign request is rejected while one is already running
  4. LLM-generated HTML served from the result URL has dangerous tags and attributes stripped (script tags, event handlers removed by nh3)
  5. A fetch request from the Next.js origin (localhost:3000) is allowed by CORS; requests from other origins are rejected
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md — Config, dependencies, CORS middleware, and test scaffolds
- [x] 01-02-PLAN.md — /redesign SSE endpoint with rate limiting, concurrency cap, sanitization, and full tests

### Phase 2: Next.js Scaffold + Wiring
**Goal**: A running Next.js dev environment wired to the FastAPI backend with the full UI toolchain ready
**Depends on**: Phase 1
**Requirements**: FRONT-01, FRONT-02, FRONT-03, FRONT-04
**Success Criteria** (what must be TRUE):
  1. Running `make dev` starts both the FastAPI server and Next.js dev server, and both are accessible
  2. The Next.js app renders a placeholder page at localhost:3000 using shadcn/ui components styled with Tailwind v4
  3. Cloudflare tunnel ingress routes /api/* traffic to FastAPI and all other traffic to Next.js
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md — Scaffold Next.js 16 in web/, install shadcn/ui + Tailwind v4 + Motion, create placeholder page
- [x] 02-02-PLAN.md — Wire Makefile dev target for concurrent servers, create Cloudflare tunnel ingress config

### Phase 3: Core UI -- Landing + Progress + Result
**Goal**: Users can enter a URL, watch their site get redesigned in real time, and see the finished result
**Depends on**: Phase 2
**Requirements**: LAND-01, LAND-02, LAND-03, LAND-04, LAND-05, PROG-01, PROG-02, PROG-03, PROG-04, PROG-05, PROG-06, RESULT-01, RESULT-02, RESULT-03, RESULT-04
**Success Criteria** (what must be TRUE):
  1. User sees a polished landing page with hero section, URL input field, and "how it works" explanation
  2. Submitting an invalid URL shows a validation error without leaving the page
  3. After submitting a valid URL, the page transitions to a progress view showing named steps (crawling, redesigning, deploying) with an animated progress bar and time estimate
  4. When the redesign completes, the user sees their redesigned site rendered in a sandboxed iframe with a link to the original site
  5. The result page URL is shareable -- visiting it directly loads the redesign without re-running the process
**Plans**: 3 plans

Plans:
- [x] 03-01-PLAN.md — Foundation components (shadcn input/label, spotlight, progress, url-utils) + landing page with hero and how-it-works
- [x] 03-02-PLAN.md — SSE client, useRedesign hook, progress view with per-step indicators, app-flow state machine
- [x] 03-03-PLAN.md — Result page with blurred iframe teaser, CTA button, shareable dynamic route at /[subdomain]/

### Phase 4: Contact Form + Polish
**Goal**: Visitors who see their redesign can immediately express interest in hiring, and the entire experience feels premium on all devices
**Depends on**: Phase 3
**Requirements**: CONTACT-01, CONTACT-02, CONTACT-03, CONTACT-04, CONTACT-05, CONTACT-06
**Success Criteria** (what must be TRUE):
  1. The result page shows a contact form with name, email, and message fields beneath the redesign preview
  2. Submitting the contact form sends an email to the owner's inbox via Resend and shows an inline success confirmation
  3. The contact form rejects spam submissions (Cloudflare Turnstile verification fails for bots, honeypot field catches simple scrapers)
  4. All pages (landing, progress, result) render correctly and look professional on mobile devices (375px width and up)
**Plans**: 2 plans

Plans:
- [x] 04-01-PLAN.md — Contact form API route (Resend + Turnstile + honeypot), ContactForm component, ResultView integration
- [x] 04-02-PLAN.md — Mobile polish pass at 375px + human verification of contact form flow

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Secure API Foundation | 2/2 | Complete | - |
| 2. Next.js Scaffold + Wiring | 2/2 | Complete | - |
| 3. Core UI -- Landing + Progress + Result | 3/3 | Complete | - |
| 4. Contact Form + Polish | 2/2 | Complete | - |
