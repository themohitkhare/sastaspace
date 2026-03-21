# Roadmap: SastaSpace

## Milestones

- ✅ **v1.0 Web Frontend** — Phases 1-4 (shipped 2026-03-21) [→ archive](milestones/v1.0-ROADMAP.md)
- 🚧 **v2.0 Production Ship** — Phases 5-8 (in progress)

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

**Parallelization:**
- Wave 1 (parallel): Phases 5, 6, 7 — no dependencies between them
- Wave 2 (sequential): Phase 8 — depends on all Wave 1 phases

- [x] **Phase 5: Docker Infrastructure** - Containerize backend, frontend, and claude-code-api with Compose orchestration
- [ ] **Phase 6: SEO + Feature Flags** - Meta tags, sitemap, social previews, and Turnstile feature flag
- [ ] **Phase 7: Design Assets** - Favicon, OG images, and app icons via Stitch MCP
- [ ] **Phase 8: E2E Test Suite** - Playwright tests covering full user flow, runnable in Docker

## Phase Details

### Phase 5: Docker Infrastructure
**Goal**: The entire application runs from a single `docker compose up` command with proper networking, persistence, and health monitoring
**Depends on**: Nothing (Wave 1 — parallel with Phases 6, 7)
**Requirements**: DOCK-01, DOCK-02, DOCK-03, DOCK-04, DOCK-05, DOCK-06, DOCK-07
**Success Criteria** (what must be TRUE):
  1. Running `docker compose up` starts backend, frontend, and claude-code-api — all three containers reach healthy status
  2. A user can submit a URL through the frontend container and receive a redesign served by the backend container (full flow works across containers)
  3. Restarting containers preserves previously generated redesigns (volume persistence)
  4. Environment configuration lives in a single `.env` file — no secrets hardcoded in Dockerfiles or compose
**Plans**: 1 plan
Plans:
- [x] 05-01-PLAN.md — Dockerfiles, docker-compose.yml, networking, volumes, health checks, .env config

### Phase 6: SEO + Feature Flags
**Goal**: The site is discoverable by search engines and shareable on social media, with Turnstile controllable via environment variable
**Depends on**: Nothing (Wave 1 — parallel with Phases 5, 7)
**Requirements**: SEO-01, SEO-02, SEO-04, FLAG-01, FLAG-02
**Success Criteria** (what must be TRUE):
  1. Sharing the landing page URL on Twitter/Slack/iMessage shows a rich preview with title, description, and image
  2. Sharing a result page URL (e.g., /example-com/) shows a dynamic preview with the subdomain name
  3. robots.txt and sitemap.xml are accessible at their standard paths
  4. Setting `NEXT_PUBLIC_ENABLE_TURNSTILE=false` hides the Turnstile widget and the contact form submits successfully without a token
**Plans**: 1 plan
Plans:
- [x] 06-01-PLAN.md — SEO metadata, robots/sitemap, and Turnstile feature flag

### Phase 7: Design Assets
**Goal**: The site has professional branding with custom favicon and social sharing images
**Depends on**: Nothing (Wave 1 — parallel with Phases 5, 6)
**Requirements**: ASSET-01, ASSET-02, SEO-03
**Success Criteria** (what must be TRUE):
  1. Browser tab shows a custom SastaSpace favicon (not the default Next.js icon)
  2. App icons render correctly when added to mobile home screen (iOS Safari, Android Chrome)
  3. OG image template exists and renders correctly in social sharing previews
**Plans**: 1 plan
Plans:
- [ ] 07-01-PLAN.md — Favicon, app icons, OG image, and manifest via Stitch MCP

### Phase 8: E2E Test Suite
**Goal**: Automated Playwright tests verify the full user flow and can run inside Docker
**Depends on**: Phases 5, 6, 7 (Wave 2 — runs after all Wave 1 phases complete)
**Requirements**: TEST-01, TEST-02, TEST-03, TEST-04, TEST-05, TEST-06
**Success Criteria** (what must be TRUE):
  1. `docker compose run tests` (or equivalent) executes the full E2E suite and reports pass/fail
  2. Tests verify the complete user journey: landing page loads, invalid URL shows error, valid URL triggers progress, result page shows iframe and contact form
  3. Contact form validation is tested (empty submit shows inline errors)
  4. Tests pass in CI-like conditions (headless browser, no manual intervention)
**Plans**: TBD

## Progress

**Execution Order:**
Wave 1 (parallel): 5, 6, 7 → Wave 2: 8

| Phase | Milestone | Plans | Status | Completed |
|-------|-----------|-------|--------|-----------|
| 1. Secure API Foundation | v1.0 | 2/2 | Complete | 2026-03-21 |
| 2. Next.js Scaffold + Wiring | v1.0 | 2/2 | Complete | 2026-03-21 |
| 3. Core UI — Landing + Progress + Result | v1.0 | 3/3 | Complete | 2026-03-21 |
| 4. Contact Form + Polish | v1.0 | 2/2 | Complete | 2026-03-21 |
| 5. Docker Infrastructure | v2.0 | 1/1 | Complete   | 2026-03-21 |
| 6. SEO + Feature Flags | v2.0 | 1/1 | Planned | - |
| 7. Design Assets | v2.0 | 1/1 | Planned | - |
| 8. E2E Test Suite | v2.0 | 0/? | Not started | - |

### Phase 9: Premium UI Redesign

**Goal:** Complete visual overhaul — replace generic AI-template aesthetic with premium editorial design using Instrument Serif + Space Grotesk typography, warm gold/amber palette, asymmetric layouts, and purposeful animation
**Requirements**: Ad-hoc (no formal requirement IDs)
**Depends on:** Phase 8
**Plans:** 2 plans

Plans:
- [x] 09-01-PLAN.md — Design system: fonts (Instrument Serif + Space Grotesk), warm color palette, FlickeringGrid background
- [x] 09-02-PLAN.md — Component redesign: asymmetric hero, editorial how-it-works, polished result/progress views
