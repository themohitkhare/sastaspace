# Project Research Summary

**Project:** SastaSpace — AI Website Redesigner with Lead-Generation Frontend
**Domain:** Public-facing AI tool (Next.js frontend + Python FastAPI backend) with long-running jobs
**Researched:** 2026-03-21
**Confidence:** HIGH

## Executive Summary

SastaSpace is a lead-generation tool that crawls a user-submitted URL, redesigns the website using Claude AI, and presents the result as social proof to drive freelance/agency hire inquiries. The canonical implementation pattern for this class of product is a Next.js App Router frontend (Server Components for SEO, client components for interactive progress) paired with the existing Python/FastAPI backend, connected via Server-Sent Events for real-time streaming and a Next.js Server Action for contact form submission. The recommended architecture uses Next.js as a thin proxy in front of FastAPI — keeping the backend internal — with a single Cloudflare tunnel exposing only the Next.js origin. This eliminates CORS entirely and is the cleanest approach for a self-hosted, single-machine deployment.

The product's core UX challenge is the 30-60 second redesign wait. Research is unambiguous: indeterminate spinners cause abandonment at this duration. The solution is SSE-driven named stage progress ("Crawling your site...", "Analyzing layout...", "Generating redesign...") with a determinate progress bar. SastaSpace's competitive advantage over v0.dev and Galileo AI is deep personalization without effort — the user provides only a URL, and the redesign is of their actual site. This "it's about you" factor is the primary emotional hook and should anchor all copy and UX decisions.

The critical risks are architectural and security concerns that must be addressed in Phase 1, before any public exposure. Cloudflare tunnels buffer SSE streams from `EventSource` (GET-based), so the frontend must use `fetch()` with `ReadableStream` (POST-based SSE) or the product's primary UX feature — real-time progress — will not work in production. The iframe that displays LLM-generated HTML is an XSS vector if sandboxed incorrectly; `allow-scripts allow-same-origin` is equivalent to no sandbox. And an unrated public endpoint that spawns 30-60 second Playwright+LLM jobs will be resource-exhausted within hours of launch. These three issues are not retrofittable — they must be designed in from the start.

## Key Findings

### Recommended Stack

The frontend is a standard Next.js 16 / React 19 / Tailwind CSS 4 / TypeScript 5 stack scaffolded with `create-next-app`. App Router is non-negotiable in 2026; Pages Router is legacy with no new feature development. shadcn/ui provides accessible component primitives that copy source into the project (no npm dependency lock-in), fully compatible with Tailwind v4. Motion (formerly Framer Motion) handles landing page scroll reveals and progress animations. Resend (via Next.js Server Action + React Email) handles contact form delivery on a free tier sufficient for lead-gen volume. The only backend addition needed is bumping the FastAPI pin from `>=0.115.0` to `>=0.135.0` to unlock built-in `EventSourceResponse` SSE support.

**Core technologies:**
- Next.js 16 (App Router): Frontend framework — SSR for SEO, Server Components for landing page, client components for SSE-powered progress UI
- React 19: UI library — bundled with Next.js 16, Server Actions for contact form
- Tailwind CSS 4: Styling — zero config file, `@theme inline` directive, scaffolded by `create-next-app`
- shadcn/ui: Component primitives — copies source, Radix UI base, Tailwind v4 compatible
- FastAPI 0.135+: Backend — built-in SSE via `EventSourceResponse`, existing redesign pipeline
- sse-starlette 3.3+: SSE fallback — if staying on FastAPI <0.135 short term
- Resend SDK 4.x: Email delivery — 3,000 emails/month free, Server Action integration
- Motion 12.x: Animation — landing page animations, progress transitions

**Do not use:** Next.js API Routes to proxy the SSE stream (buffering issues), WebSockets (overkill for unidirectional progress), polling (60 requests vs. 1 SSE connection), Redux/Zustand (no complex global state needed), `tailwind.config.js` (Tailwind v4 uses CSS-based config).

### Expected Features

The product's core value — seeing your own site redesigned — is the differentiator. Everything else serves that moment or converts it into a lead.

**Must have (table stakes — launch blockers):**
- URL input with prominent CTA — the entry point; zero friction, no login gate
- SSE progress with named stages + percentage bar — mandatory for 30-60s wait; abandonment prevention
- Full-page redesign preview (iframe) — the payoff moment; clean rendering at multiple viewports
- Contact form with contextual "hire me" CTA — the conversion point; appears on result page at peak engagement
- Mobile responsive landing and result pages — 50%+ traffic is mobile
- Professional visual design quality — this site IS the portfolio; cheap-looking = zero trust
- 3-5 curated portfolio examples on landing page — social proof before the user commits to waiting

**Should have (competitive differentiators — v1.x):**
- Before/after interactive slider — single most powerful visual proof element; requires original screenshot from Playwright (already captured) + redesign screenshot
- Shareable result URLs with Open Graph meta tags — viral distribution; each share is free marketing
- Animated progress visualization (screenshot morphing) — upgrades the wait from functional to engaging
- SEO meta tags + JSON-LD structured data — organic traffic; add once page design is stable

**Defer (v2+):**
- User accounts / redesign history — adds auth complexity, kills frictionless experience; shareable URLs serve the same purpose
- Multiple redesign variations — triples cost and wait time, creates decision paralysis
- Download/export HTML — gives away the product; undermines lead-gen model
- Blog / content marketing — SEO long play, only after validating lead quality

**Anti-features to explicitly reject:** login wall, side-by-side comparison (halves visual impact), live chat (can't staff solo), public gallery of all submissions (quality is inconsistent).

### Architecture Approach

The system uses a two-service architecture: Next.js (port 3000) handles all UI, SSR, and acts as a thin proxy for API calls; FastAPI (port 8080) orchestrates the redesign pipeline and streams SSE events. A single Cloudflare tunnel with ingress rules exposes Next.js publicly; FastAPI stays internal. The Next.js Route Handler proxies the SSE stream byte-for-byte to avoid CORS, but the browser must use `fetch()` + `ReadableStream` (not `EventSource`) to avoid Cloudflare's GET-based SSE buffering. Application state is a linear three-step flow — idle, in-progress, result — manageable with `useState` alone; no global state store is needed.

**Major components:**
1. **Next.js App (port 3000)** — Landing page RSC (SEO), client progress component (SSE consumer), result page (iframe display), contact form (Server Action), Route Handler (SSE proxy to FastAPI)
2. **FastAPI (port 8080)** — `/api/redesign` POST with `EventSourceResponse` SSE streaming, `/api/contact` POST endpoint, `/{subdomain}/` static redesign serving; wrap `redesign()` in `asyncio.to_thread()` to avoid blocking the event loop
3. **Cloudflare Tunnel** — Single named tunnel, one hostname (`sastaspace.com`), routes to Next.js; FastAPI stays on localhost only
4. **claude-code-api gateway (port 8000)** — Existing, no changes needed

**Build order (hard dependencies):** FastAPI SSE endpoint (1) → Next.js scaffold (2, parallel) → Next.js SSE proxy Route Handler (3) → Progress UI component (4) → Result page (5) → Landing page design (6, parallel with 4-5) → Contact form (7) → Cloudflare tunnel config (8, final).

### Critical Pitfalls

1. **Cloudflare tunnel buffers GET-based SSE** — `EventSource` API (GET) is fully buffered by Cloudflare Quick Tunnels and has edge cases on named tunnels. Use `fetch()` with `ReadableStream` (POST-based SSE) from day one. Also use a named tunnel with `protocol: http2` in cloudflared config. Validate streaming through the tunnel on the first day, not after the frontend is complete.

2. **iframe XSS via incorrect sandbox** — `sandbox="allow-scripts allow-same-origin"` is equivalent to no sandbox; iframe can access parent DOM and cookies. Use `allow-scripts` alone (gives iframe opaque origin). Serve redesign HTML from a separate origin as defense-in-depth. Strip `<script>` tags and event handler attributes from LLM output server-side using `nh3` before storage.

3. **No rate limiting on a 30-60s compute job invites DoS** — An unprotected public endpoint that spawns Playwright + Claude jobs will be found and abused within hours. Implement `asyncio.Semaphore(1)` for concurrency control, IP-based rate limiting via `slowapi` (1 concurrent, 3/hour per IP), and Cloudflare WAF rules at the edge. This ships with the endpoint, not after.

4. **SSE connection drops with no recovery** — Mobile network switches, tab backgrounding, and Cloudflare's ~100s idle timeout will drop connections mid-job. The architecture must include a job ID returned on submission, so clients can reconnect and resume from `Last-Event-ID`. Implement a polling fallback if SSE fails twice. Hash input URLs for idempotent submissions.

5. **Next.js Route Handler as SSE proxy has payload and timeout limits** — Next.js API routes are designed for lightweight request/response, not streaming proxies. The recommended pattern is direct FastAPI calls with CORS, or the proxy pattern using `Response` with streamed body (not `json()`). Never use `next.config.js` rewrites for streaming endpoints.

## Implications for Roadmap

Based on the combined research, the build order dictated by hard architectural dependencies and the security requirements that cannot be retrofitted suggests a four-phase structure.

### Phase 1: Secure API Foundation
**Rationale:** The FastAPI SSE endpoint is the dependency root for everything else. It also carries Phase 1's most critical security requirements (rate limiting, iframe sandboxing, URL validation, LLM output sanitization) that cannot be added after public launch. Validating SSE streaming through the Cloudflare tunnel must happen here — if the streaming architecture is wrong, the entire frontend must be rewritten.
**Delivers:** A working, hardened `/api/redesign` SSE endpoint with concurrency control, IP rate limiting, URL validation (no SSRF), and LLM output sanitization. Verified streaming through named Cloudflare tunnel using POST/ReadableStream.
**Addresses:** SSE progress streaming (P1 feature), redesign pipeline (P1 feature)
**Avoids:** Cloudflare SSE buffering, DoS via unlimited compute jobs, iframe XSS, path traversal, SSRF via URL input

### Phase 2: Core Frontend — Landing Page + Progress Flow
**Rationale:** The landing page (URL input) and the SSE-powered progress UI are the product's primary interaction. Together they define the user experience from "I want to try this" to "I see my site redesigned." These two components share the SSE client architecture and should be built together.
**Delivers:** Full redesign flow in the browser — URL input form, SSE-powered progress display with named stages and percentage bar, result page with iframe preview. End-to-end flow works on desktop and mobile.
**Uses:** Next.js App Router, React `useState` + `useEffect` for SSE state, shadcn/ui components, Next.js Route Handler (SSE proxy), Tailwind CSS 4
**Implements:** Next.js App (landing page RSC + client progress component), Next.js Route Handler proxy, Result page with sandboxed iframe
**Avoids:** Indeterminate spinner (progress abandonment), iframe sandbox misconfiguration

### Phase 3: Conversion Layer — Contact Form + Visual Polish
**Rationale:** The contact form is the revenue mechanism — it must exist before the tool is shared publicly. Visual polish (professional design quality) is classified as a P1 feature because the site is the portfolio; it must look credible. Portfolio examples provide social proof. These can be built in parallel and are independent of the redesign flow internals.
**Delivers:** Contact form with Turnstile spam protection and honeypot, email delivery via Resend Server Action, curated portfolio examples on landing page, professional visual design quality with Motion animations.
**Uses:** Next.js Server Action, Resend SDK 4.x, React Email, Cloudflare Turnstile, Motion 12.x
**Implements:** Contact form component, email notification template, landing page hero and portfolio section
**Avoids:** Contact form spam (Turnstile + honeypot + time-based check), multi-step form friction

### Phase 4: Differentiation + Distribution
**Rationale:** Once the core flow is live and generating leads, add the features that create viral distribution and competitive separation. Before/after slider requires original screenshots (Playwright already captures these) and a redesign screenshot. Shareable URLs with OG meta tags enable sharing. SEO optimization is deferred until page design is stable to avoid rework.
**Delivers:** Before/after interactive slider, shareable result URLs with Open Graph meta tags, SEO optimization (meta tags, JSON-LD), optional animated progress visualization.
**Addresses:** Before/after slider (P2), shareable URLs (P2), SEO (P2)
**Avoids:** Premature SEO work before page design is final

### Phase Ordering Rationale

- **Security-first ordering:** Phase 1 establishes all security primitives (rate limiting, sandboxing, input validation, output sanitization) before the frontend is built. This avoids the "looks done but isn't" trap where a working demo is deployed with live XSS vectors.
- **Dependency-driven:** FastAPI SSE endpoint must exist before the Next.js SSE proxy can be written, which must exist before the progress UI can be tested. This hard chain determines the Phase 1 → Phase 2 ordering.
- **Revenue gate:** The contact form (Phase 3) must ship before public promotion. A tool without a lead capture mechanism wastes the product's primary purpose.
- **Viral features last:** Before/after slider and shareable URLs (Phase 4) are high-value but require a stable core. Adding them before the core UX is validated risks rework if the progress flow needs redesign.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** POST-based SSE implementation pattern in FastAPI with `fetch()` + `ReadableStream` client-side — the exact implementation details for POST SSE with reconnection and `Last-Event-ID` forwarding need validation against FastAPI 0.135+ docs
- **Phase 1:** `nh3` HTML sanitization configuration — what attributes and tags to strip from LLM output without breaking legitimate styling
- **Phase 4:** Screenshot capture of rendered redesign HTML for before/after slider — requires either Playwright screenshotting the served HTML or a headless render step; implementation details unclear

Phases with standard patterns (skip research):
- **Phase 2:** Next.js App Router + shadcn/ui patterns are extremely well-documented; standard implementation
- **Phase 3:** Resend Server Action + React Email is a documented, official Resend integration; Turnstile has straightforward server-side verification API
- **Phase 3:** Contact form best practices are well-established (Zod validation, Server Action submission, inline confirmation)

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All core technologies verified against official docs. Version compatibility matrix cross-checked. `create-next-app` scaffold handles most configuration automatically. |
| Features | MEDIUM-HIGH | Feature prioritization grounded in NNGroup UX research and competitor analysis (v0.dev, Galileo AI). MVP definition is opinionated but logical. Some feature values (before/after slider conversion lift) are qualitative, not quantitative. |
| Architecture | HIGH | SSE patterns, Cloudflare tunnel routing, and proxy vs. direct call trade-offs all verified against official FastAPI, Next.js, and Cloudflare docs. Streaming architecture confirmed against known GitHub issues for the buffering problem. |
| Pitfalls | HIGH | Cloudflare SSE buffering is a documented GitHub issue (cloudflared#199, cloudflared#1449). iframe sandbox XSS escape is a real CVE pattern (Excalidraw GHSA). DoS via unprotected compute endpoints is well-documented. Security patterns are confirmed, not theoretical. |

**Overall confidence:** HIGH

### Gaps to Address

- **POST-based SSE client implementation:** The `EventSource` API only supports GET; switching to `fetch()` + `ReadableStream` for POST-based SSE is the correct approach but the exact code pattern for passing `Last-Event-ID` on reconnect via POST needs implementation-level research during Phase 1 planning.
- **FastAPI 0.135+ SSE API surface:** The architecture uses `fastapi.sse.EventSourceResponse` and `ServerSentEvent` from FastAPI's built-in module. Verify the exact import path and event naming API against the installed version before coding.
- **Redesign screenshot capture for before/after slider:** The original screenshot is already captured by Playwright during crawl. Capturing the "after" screenshot (rendered redesign HTML) requires either a headless browser step or a client-side capture API — the mechanism is not yet specified. Defer to Phase 4 planning.
- **Contact form storage strategy:** PITFALLS.md recommends storing submissions locally first, then forwarding via email. The exact storage mechanism (SQLite vs. append-only JSON file) is not decided and should be confirmed during Phase 3 planning.

## Sources

### Primary (HIGH confidence)
- [Next.js 16 release blog](https://nextjs.org/blog/next-16) — Turbopack default, React Compiler stable
- [FastAPI SSE Documentation](https://fastapi.tiangolo.com/tutorial/server-sent-events/) — built-in SSE since v0.135.0
- [shadcn/ui Tailwind v4 docs](https://ui.shadcn.com/docs/tailwind-v4) — v4 compatibility confirmed
- [Cloudflare Tunnel Configuration](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/local-management/configuration-file/) — ingress rules for multiple services
- [Cloudflare cloudflared SSE buffering issue #199](https://github.com/cloudflare/cloudflared/issues/199) — documented buffering problem
- [Cloudflare cloudflared SSE over GET not streamed #1449](https://github.com/cloudflare/cloudflared/issues/1449) — confirmed GET SSE buffering
- [sse-starlette on PyPI](https://pypi.org/project/sse-starlette/) — version 3.3.3, production-ready SSE
- [Resend Next.js integration](https://resend.com/docs/send-with-nextjs) — Server Actions support confirmed

### Secondary (MEDIUM confidence)
- [NNGroup: Progress Indicators Make a Slow System Less Insufferable](https://www.nngroup.com/articles/progress-indicators/) — mandatory determinate progress for 10s+ waits
- [NNGroup: Status Trackers and Progress Updates](https://www.nngroup.com/articles/status-tracker-progress-update/) — 16 design guidelines
- [Next.js SSE Discussion](https://github.com/vercel/next.js/discussions/48427) — Route Handler buffering issues
- [HackTricks: Iframes in XSS, CSP and SOP](https://book.hacktricks.xyz/pentesting-web/xss-cross-site-scripting/iframes-in-xss-and-csp) — sandbox escape patterns
- [Excalidraw stored XSS via srcdoc](https://github.com/excalidraw/excalidraw/security/advisories/GHSA-m64q-4jqh-f72f) — real CVE for this exact pattern

### Tertiary (LOW confidence — qualitative)
- [SaaSFrame: 10 SaaS Landing Page Trends for 2026](https://www.saasframe.io/blog/10-saas-landing-page-trends-for-2026-with-real-examples) — design direction
- [Orizon: 10 Favourite Landing Page Designs in Fall 2025](https://www.orizon.co/blog/our-10-favourite-landing-page-designs-in-fall-2025-and-why-they-convert) — visual quality benchmarks
- [Long-Running AI Tasks UI Patterns](https://particula.tech/blog/long-running-ai-tasks-user-interface-patterns) — progress UX patterns for AI tools

---
*Research completed: 2026-03-21*
*Ready for roadmap: yes*
