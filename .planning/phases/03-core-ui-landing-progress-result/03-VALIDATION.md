---
phase: 3
slug: core-ui-landing-progress-result
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-21
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | ESLint + Next.js build (primary); Vitest optional for pure function unit tests |
| **Config file** | `web/eslint.config.mjs` (exists), `web/vitest.config.ts` (Wave 0 creates if used) |
| **Quick run command** | `cd web && npm run lint` |
| **Full suite command** | `cd web && npm run build && npm run lint` |
| **Estimated runtime** | ~30 seconds (lint), ~60 seconds (build) |

---

## Sampling Rate

- **After every task commit:** Run `cd web && npm run lint`
- **After every plan wave:** Run `cd web && npm run build && npm run lint`
- **Before `/gsd:verify-work`:** Full build must be green + manual visual walkthrough
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| url-utils | 01 | 1 | LAND-02 | unit | `cd web && npm run lint` | ❌ W0 | ⬜ pending |
| sse-client | 01 | 1 | PROG-02 | unit | `cd web && npm run lint` | ❌ W0 | ⬜ pending |
| hero-section | 01 | 1 | LAND-01, LAND-04 | smoke | `cd web && npm run build` | ❌ created in task | ⬜ pending |
| how-it-works | 01 | 1 | LAND-03 | smoke | `cd web && npm run build` | ❌ created in task | ⬜ pending |
| progress-view | 02 | 2 | PROG-01, PROG-03, PROG-04, PROG-06 | smoke | `cd web && npm run build` | ❌ created in task | ⬜ pending |
| result-view | 03 | 3 | RESULT-01, RESULT-02, RESULT-03, RESULT-04 | smoke | `cd web && npm run build` | ❌ created in task | ⬜ pending |
| mobile-responsive | 01 | 1 | LAND-05 | manual-only | — | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `web/src/lib/url-utils.ts` — URL validation + domain extraction functions (LAND-02); pure functions with no browser dependencies, lint-verifiable
- [ ] `web/src/lib/sse-client.ts` — SSE AsyncGenerator using fetch() + ReadableStream (PROG-02); pure module, lint-verifiable
- [ ] `web/src/hooks/use-redesign.ts` — SSE state hook stub (PROG-01, PROG-03)

*Note: This phase is primarily UI/visual. Wave 0 focuses on pure logic files that can be validated via build + lint. Visual requirements (LAND-04, LAND-05, PROG-01, PROG-03, PROG-04, PROG-06, RESULT-01, RESULT-02) are manually verified.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Professional, high-design visual appearance | LAND-04 | Subjective visual quality | Open `localhost:3000`, inspect hero at 1280px and 375px widths |
| Mobile responsive layout | LAND-05 | Browser rendering required | DevTools responsive mode at 375px; check touch targets ≥ 44px |
| Smooth landing → progress transition | PROG-01 | Animation requires browser | Submit a URL, observe AnimatePresence fade transition |
| Step label updates per SSE event | PROG-03 | SSE requires live backend | Submit a real URL with `make dev` running, observe step labels |
| Progress bar advances through steps | PROG-04 | Animation requires browser | Same as PROG-03; each step bar fills as event fires |
| Error state shows retry option | PROG-06 | Requires error trigger | Kill FastAPI mid-stream OR submit URL with backend down; retry button must appear |
| Sandboxed iframe shows redesign | RESULT-01 | Requires completed redesign | Complete full flow; inspect iframe sandbox attribute in DevTools |
| "View original site" opens new tab | RESULT-02 | Browser behavior | Click link on result page; verify new tab opens |
| Blurred teaser with "Take me to the future" button | RESULT-10 | Visual + interaction | Observe blur overlay on result page; click button navigates to `/<subdomain>/` in same tab |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
