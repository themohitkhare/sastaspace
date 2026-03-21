---
phase: 4
slug: contact-form-polish
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-21
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (not yet installed — Wave 0 installs) |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `cd web && npx vitest run --reporter=verbose` |
| **Full suite command** | `cd web && npx vitest run` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Visual check in browser (form render, submit, success state)
- **After every plan wave:** Full browser walkthrough of result page + contact flow
- **Before `/gsd:verify-work`:** Full suite must be green + manual QA at 375px on all 3 pages

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 4-01-01 | 01 | 0 | CONTACT-03, CONTACT-04 | unit | `cd web && npx vitest run src/app/api/contact/route.test.ts` | ❌ W0 | ⬜ pending |
| 4-01-02 | 01 | 1 | CONTACT-03, CONTACT-04 | unit | `cd web && npx vitest run src/app/api/contact/route.test.ts` | ❌ W0 | ⬜ pending |
| 4-02-01 | 02 | 2 | CONTACT-01, CONTACT-02 | manual | Visual check at /[subdomain] result page | N/A | ⬜ pending |
| 4-02-02 | 02 | 2 | CONTACT-05, CONTACT-06 | manual | Submit form, verify inline swap; confirm no phone field | N/A | ⬜ pending |
| 4-03-01 | 03 | 3 | CONTACT-01 through CONTACT-06 | manual | Mobile QA at 375px on all 3 pages | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `web/src/app/api/contact/route.test.ts` — stubs for CONTACT-03 (honeypot + Turnstile) and CONTACT-04 (Resend mocked)
- [ ] vitest install: `cd web && npm install -D vitest` (if not already present)

*Most requirements (CONTACT-01, 02, 05, 06) are UI/visual and best verified manually at this project scale.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Form renders with headline below redesign preview | CONTACT-01 | DOM structure + visual layout requires browser | Navigate to /[subdomain] result page, scroll below iframe, verify h2 "Like what you see? Let's build the real thing." is visible |
| Exactly 3 fields: Name, Email, Message (no phone) | CONTACT-02, CONTACT-06 | Visual field count + absence check | Count visible form fields; confirm no phone input exists |
| Inline success swap without navigation | CONTACT-05 | Animation + state transition requires browser | Submit form with valid data, confirm page does not navigate and success message "Thanks, I'll be in touch." appears |
| Mobile rendering at 375px | All | Responsive layout requires visual check | Open DevTools, set viewport to 375px, verify all 3 pages (landing, progress, result) look professional |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
