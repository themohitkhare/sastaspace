# Phase 8: E2E Test Suite - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Create a Playwright E2E test suite that verifies the full user flow (landing → progress → result → contact form). Tests should be runnable both locally and in Docker.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

All implementation choices are at Claude's discretion — pure infrastructure phase.

Key constraints:
- Playwright is already a dev dependency in web/package.json
- Tests should cover: landing page render, URL validation, progress view, result page, contact form
- Tests run against the Next.js dev server (or production build)
- Docker test runner: `docker compose run tests` or add a test profile to compose
- Backend can be mocked or tests can use the real backend if running
- Focus on frontend E2E tests that verify the UI works correctly

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `@playwright/test` already in web/package.json devDependencies
- `web/test-results/` directory exists (Playwright already configured)
- Existing components have testable structure (data attributes, semantic HTML)

### Established Patterns
- Next.js App Router with client components using "use client"
- AppFlow state machine manages view transitions
- SSE client connects to backend at NEXT_PUBLIC_BACKEND_URL

### Integration Points
- Landing page at /
- Progress view (transitions in-place via AppFlow)
- Result page at /[subdomain]/
- Contact form on result page
- API route at /api/contact

</code_context>

<specifics>
## Specific Ideas

No specific requirements — standard E2E testing.

</specifics>

<deferred>
## Deferred Ideas

None.

</deferred>
