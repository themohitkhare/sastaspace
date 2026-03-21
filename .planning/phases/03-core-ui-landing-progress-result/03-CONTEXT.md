# Phase 3: Core UI — Landing + Progress + Result - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the complete user-facing flow: landing page with URL input → progress experience while SSE streams → result reveal page. Users go from "I have a URL" to "I can see my redesigned site." Contact form (Phase 4) and polish are out of scope.

</domain>

<decisions>
## Implementation Decisions

### Landing page — visual direction
- **D-01:** Hero has subtle background motion/animation (dynamic and alive) — not static
- **D-02:** URL input is center-stage dominant — the entire hero is built around the input field (v0.dev / Perplexity pattern), not secondary to a headline
- **D-03:** "How it works" section uses a horizontal timeline with connected steps (3 steps: Enter URL → AI Redesigns → See Result)
- **D-04:** Tone is approachable and service-oriented — targets non-technical business owners, not developers. Think boutique agency, not dev tool. No jargon.

### Progress view — layout and messaging
- **D-05:** Single focused status line (not a vertical step list) — one line of text updates with each SSE event
- **D-06:** Per-step progress indicators — each of the 3 steps (crawling, redesigning, deploying) has its own visual loader/bar that activates and completes in sequence
- **D-07:** No time estimate — PROG-05 is intentionally omitted. Avoids false expectations.
- **D-08:** Plain English step labels personalized to the submitted domain — extract domain/company name from the URL and use it in messaging:
  - crawling → "Analyzing acme.com"
  - redesigning → "Redesigning your site with AI"
  - deploying → "Preparing your new acme.com"
- **D-09:** Technical SSE event names (crawling/redesigning/deploying) are NEVER shown to the user — always map to plain English + personalized copy

### Result page — presentation
- **D-10:** Blurred/obscured teaser of the redesigned site is shown on the result page with a prominent "Take me to the future" button overlaid
- **D-11:** Clicking "Take me to the future" navigates to the deployed redesign URL in the same tab (full page navigation to `/<subdomain>/`) — not an iframe, not a new tab
- **D-12:** The sandboxed iframe (RESULT-01) serves as the blurred teaser source — the iframe renders the redesign but is visually obscured (CSS blur/overlay) until the button is clicked
- **D-13:** Result page header: "Your new [domain] is ready" + teaser + CTA button + "View original site" link
- **D-14:** No contact form placeholder in Phase 3 — Phase 4 adds it. Result page ends after the CTA.
- **D-15:** Shareable result URL (`/<subdomain>/`) shows the same result page — copy adapts slightly ("acme.com has been redesigned" vs "Your new acme.com is ready")

### Page transitions
- **D-16:** Claude's discretion on all transition animations — optimized for non-technical audience (smooth but fast, never janky)
- **D-17:** URL updates during flow: `/` (landing) → `/` during progress (no URL change, React state swap) → `/<subdomain>/` on result (URL changes when done event fires, enabling shareability)
- **D-18:** Back button from result → landing page (clean restart), not progress (which would be broken state)
- **D-19:** Progress view lives at `/` as a state overlay — no separate route, no history entry pushed

### Claude's Discretion
- Exact transition animation style and timing (landing → progress → result)
- Background effect choice from the component library (subtle motion, not overwhelming)
- Blur/overlay implementation for the result teaser
- Step loader animation style (per-step indicators)
- Exact domain name extraction logic from submitted URL

</decisions>

<specifics>
## Specific Ideas

- Hero pattern: center-stage URL input with animated/living background — reference v0.dev and Perplexity for input prominence
- Progress: single status line, not a step list — feel like "the machine is working" not a checklist
- Result reveal: blurred teaser + "Take me to the future" button is the emotional peak of the product — this is the conversion moment
- Non-tech audience: every word should feel like a friendly agency, not an AI startup. "Your site" not "the URL". "Ready" not "deployed".
- Component library at `components/` has heroes, backgrounds, spinner-loaders, and inputs to draw from — prefer these over building from scratch

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase requirements
- `.planning/REQUIREMENTS.md` §Frontend — Landing Page (LAND-01 through LAND-05)
- `.planning/REQUIREMENTS.md` §Frontend — Progress Experience (PROG-01 through PROG-06, note: PROG-05 time estimate is intentionally omitted per D-07)
- `.planning/REQUIREMENTS.md` §Frontend — Result Page (RESULT-01 through RESULT-04)
- `.planning/ROADMAP.md` §Phase 3 — success criteria and goal statement

### Design system (established in Phase 2)
- `.planning/phases/02-next-js-scaffold-wiring/02-UI-SPEC.md` — color tokens (oklch zinc), typography (Inter), spacing scale, component patterns

### API contract (established in Phase 1)
- `.planning/phases/01-secure-api-foundation/01-CONTEXT.md` §SSE Event Payload Shape — exact event names, data fields, progress values, `done.subdomain` field for result URL construction

### Existing scaffold
- `web/src/app/page.tsx` — current placeholder page to replace
- `web/src/app/layout.tsx` — root layout with Inter font and global styles
- `web/src/app/globals.css` — Tailwind v4 + oklch theme variables
- `web/src/components/ui/button.tsx` — only shadcn component installed so far

### Component library
- `components/marketing-blocks/heroes/` — hero section blocks (animated backgrounds, input-centered layouts)
- `components/marketing-blocks/backgrounds/` — background effects (subtle motion options)
- `components/marketing-blocks/features/` — feature/steps sections (for "How it works")
- `components/ui-components/inputs/` — input variants including `ruixen.ui__url-input.json`
- `components/ui-components/spinner-loaders/` — step loaders and progress components
- `components/index.json` — component registry index

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `web/src/components/ui/button.tsx`: shadcn Button — use for "Take me to the future" CTA and other actions
- `web/src/app/globals.css`: oklch zinc theme variables (`--background`, `--primary`, `--muted`, etc.) — all new components must use these tokens
- `web/src/app/layout.tsx`: Inter font already wired to `<body>` via `next/font/google`

### Established Patterns
- oklch color space throughout (not hsl) — shadcn v4 base-nova default
- Tailwind v4 `@theme inline` pattern for token mapping (see globals.css)
- `"use client"` directive required for any component using state, effects, or SSE fetch
- SSE must use `fetch()` + `ReadableStream`, NOT `EventSource` (Cloudflare buffers GET SSE — locked decision from Phase 1)
- FastAPI runs at port 8080, Next.js at 3000 — browser calls FastAPI directly at `http://localhost:8080/redesign` (no proxy)

### Integration Points
- SSE `done` event carries `subdomain` field (e.g. `"acme-corp"`) — use this to construct result URL `/<subdomain>/` and for personalized copy
- SSE `error` event carries `error` string — show as friendly message in progress view with retry option (PROG-06)
- Result page route: `web/src/app/[subdomain]/page.tsx` — dynamic route that loads the deployed redesign and shows the result experience
- The deployed HTML lives at `/<subdomain>/` served by FastAPI's static file server — the iframe `src` and the "Take me to the future" navigation target

</code_context>

<deferred>
## Deferred Ideas

- Before/after interactive slider (original screenshot vs redesign) — v2, see REQUIREMENTS.md DIFF-01
- Shareable OG preview tags on result page — v2, see REQUIREMENTS.md DIFF-02
- Contact form on result page — Phase 4 (CONTACT-01 through CONTACT-06)
- Countdown timer / time estimate — explicitly excluded per D-07

</deferred>

---

*Phase: 03-core-ui-landing-progress-result*
*Context gathered: 2026-03-21*
