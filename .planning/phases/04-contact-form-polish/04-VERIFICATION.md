---
phase: 04-contact-form-polish
verified: 2026-03-21T10:30:00Z
status: human_needed
score: 9/9 automated must-haves verified
human_verification:
  - test: "Contact form end-to-end flow with live Resend and Turnstile keys"
    expected: "Filling Name, Email, Message and submitting sends a real email to OWNER_EMAIL with reply-to set to the submitter's address; form swaps to thank-you state inline"
    why_human: "Requires live external services (Resend API key, Cloudflare Turnstile site key); cannot verify email delivery or Turnstile challenge resolution programmatically"
  - test: "AnimatePresence success state swap visual transition"
    expected: "After successful submission the form fades out and 'Thanks, I'll be in touch.' fades in with no navigation or page reload"
    why_human: "Animation and state transition behavior requires browser rendering to observe"
  - test: "Mobile rendering at 375px — no horizontal overflow on any page"
    expected: "Landing, progress, and result pages all render without a horizontal scrollbar; no content touches the viewport edge"
    why_human: "Visual overflow requires browser DevTools or device to confirm; grep can find classes but cannot validate rendered layout"
  - test: "Touch targets meet 44px minimum on mobile"
    expected: "Submit button (h-11=44px), URL input button (h-11), and all interactive elements are reachable with a finger tap without accidental adjacent-target triggering"
    why_human: "Touch target adequacy requires physical or simulated mobile interaction"
  - test: "Turnstile spam protection — honeypot silent 200 and Turnstile 400 failure paths"
    expected: "Bot that fills the website honeypot field gets 200 OK with no email sent; request with invalid Turnstile token gets 400 'Verification failed'"
    why_human: "Requires sending crafted requests to a running server with real Turnstile secret key for the failure path; test keys always pass"
---

# Phase 04: Contact Form + Polish Verification Report

**Phase Goal:** Visitors who see their redesign can immediately express interest in hiring, and the entire experience feels premium on all devices
**Verified:** 2026-03-21T10:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Result page shows a contact form with name, email, and message fields below the redesign preview | VERIFIED | `contact-form.tsx` renders all three fields; `result-view.tsx` renders `<ContactForm subdomain={subdomain} />` after the "View original site" link |
| 2 | Submitting the form sends an email to the owner via Resend with reply-to set to submitter's email | VERIFIED (code) | `route.ts` line 53: `replyTo: email`; `getResend().emails.send(...)` called with owner's address; **email delivery requires human verification with live keys** |
| 3 | Bots that fill the honeypot field get a silent 200 OK without email being sent | VERIFIED (code) | `route.ts` lines 22-24: `if (website) { return Response.json({ ok: true }); }` — email path is bypassed |
| 4 | Turnstile verification failure returns a 400 error | VERIFIED (code) | `route.ts` lines 44-46: checks `turnstileData.success`, returns `status: 400` on failure |
| 5 | After successful submission, the form swaps to a thank-you message inline without navigation | VERIFIED (code) | `contact-form.tsx` uses `AnimatePresence mode="wait"` with `key="form"` and `key="thanks"`; status `!== "success"` gates the swap |
| 6 | No phone number field exists on the form | VERIFIED | `grep phone contact-form.tsx` returns no matches |
| 7 | All three pages render at 375px with minimum 16px horizontal padding | VERIFIED (code) | `hero-section.tsx` has `px-4 pt-16`; `progress-view.tsx` has `px-4`; `result-view.tsx` has `px-4 pt-16`; **visual rendering requires human verification** |
| 8 | Step indicator labels are readable on mobile without clipping | VERIFIED (code) | `step-indicator.tsx` uses `w-36 sm:w-48` — 144px fixed on mobile, 192px on sm+; `shrink-0` prevents compression |
| 9 | Contact form submit button meets 44px touch target requirement | VERIFIED | `contact-form.tsx` line 208: `className="w-full h-11 mt-6"` — `h-11` = 44px |

**Score:** 9/9 truths verified (5 items flagged for human confirmation)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `web/src/app/api/contact/route.ts` | POST handler: honeypot → turnstile → resend → response | VERIFIED | 75 lines; exports `POST`; contains `escapeHtml`, honeypot check, Turnstile fetch, `getResend().emails.send`, `replyTo` |
| `web/src/components/result/contact-form.tsx` | Contact form with fields, Turnstile, honeypot, AnimatePresence swap | VERIFIED | 241 lines; `"use client"`, exports `ContactForm`, contains all required elements |
| `web/src/components/result/result-view.tsx` | Result page with ContactForm integrated below iframe | VERIFIED | 67 lines; imports and renders `<ContactForm subdomain={subdomain} />` with `<hr>` divider |
| `web/.env.example` | Documents required environment variables | VERIFIED | Contains `RESEND_API_KEY`, `OWNER_EMAIL`, `NEXT_PUBLIC_TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET_KEY` with dev test keys |
| `web/src/components/progress/step-indicator.tsx` | Mobile-polished step indicator labels | VERIFIED | Responsive `w-36 sm:w-48` label width applied (commit a7a456f) |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `contact-form.tsx` | `/api/contact` | `fetch POST in handleSubmit` | WIRED | Line 51: `const res = await fetch("/api/contact", { method: "POST", ... })` — response parsed and drives state |
| `route.ts` | `resend.emails.send` | `getResend()` factory call | WIRED | Line 50: `const { error } = await getResend().emails.send({...})` — result checked, error propagated |
| `result-view.tsx` | `contact-form.tsx` | `import and render ContactForm` | WIRED | Line 5: `import { ContactForm }` — line 62: `<ContactForm subdomain={subdomain} />` |
| `url-input-form.tsx` | mobile layout | `flex-col sm:flex-row` stacking | WIRED | Line 75: `flex flex-col sm:flex-row` — stacks vertically on mobile, horizontal on sm+ |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CONTACT-01 | 04-01 | Contact form on result page with correct headline | SATISFIED | `contact-form.tsx` line 93: "Like what you see? Let's build the real thing." |
| CONTACT-02 | 04-01 | 3 fields only: Name, Email, Message | SATISFIED | Three `<Input>` / `<textarea>` elements; no phone or other fields |
| CONTACT-03 | 04-01 | Turnstile widget + honeypot field | SATISFIED | `<Turnstile options={{ size: "invisible" }} />` + `name="website"` honeypot input |
| CONTACT-04 | 04-01 | Email sent via Resend to owner's inbox with reply-to | SATISFIED (code) | `replyTo: email`, `to: [process.env.OWNER_EMAIL!]` in route handler |
| CONTACT-05 | 04-01, 04-02 | Success state inline, no navigation | SATISFIED (code) | `AnimatePresence mode="wait"` swap; no `router.push` or redirect on success |
| CONTACT-06 | 04-01 | No phone number field | SATISFIED | No `phone` string found in `contact-form.tsx` |

No orphaned requirements found for Phase 4.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | — |

Scanned for: TODO/FIXME, placeholder comments, `return null`, `return []`, empty handlers. None found in phase-modified files.

Notable: `route.ts` uses a `getResend()` factory pattern (deviation from plan) rather than module-level instantiation — this is a **correct** architectural decision to avoid build-time failures when `RESEND_API_KEY` is not set. Not a stub.

---

### Human Verification Required

#### 1. Contact Form End-to-End with Live Keys

**Test:** Set `RESEND_API_KEY`, `OWNER_EMAIL`, and production Turnstile keys in `web/.env.local`. Run `make dev`. Navigate to a result page. Fill all three fields and submit.
**Expected:** Email arrives in owner's inbox; reply-to is the submitter's address; form swaps to "Thanks, I'll be in touch." without navigating away.
**Why human:** Requires live Resend and Cloudflare Turnstile services; email delivery cannot be verified by static analysis.

#### 2. AnimatePresence Success State Swap

**Test:** Submit the form successfully (or force `status = "success"` in dev tools).
**Expected:** The form fades out (opacity 0, 200ms) and the thank-you message fades in without any flash or layout shift.
**Why human:** Animation timing and visual quality require browser rendering.

#### 3. No Horizontal Overflow at 375px

**Test:** Open each page (landing, /example-com progress mid-flow, /example-com result) in browser DevTools with viewport set to 375px width.
**Expected:** No horizontal scrollbar appears; all text and UI elements are within the viewport; nothing touches the edge.
**Why human:** CSS class presence does not guarantee rendered layout correctness.

#### 4. Touch Target Adequacy on Mobile

**Test:** On a real mobile device or 375px emulation, tap the "Redesign My Site" button on landing, and the "Send Message" button on the result page.
**Expected:** Both buttons are easily tappable without accidentally hitting adjacent elements; no misfire on small targets.
**Why human:** Touch accuracy requires physical or simulated touch interaction.

#### 5. Honeypot + Turnstile Failure Paths (Integration)

**Test:** With dev test keys (always-pass Turnstile), manually POST to `/api/contact` with `{ website: "filled" }` and separately with `{ turnstileToken: null }`.
**Expected:** Honeypot request returns `200 { ok: true }` with no email sent. Note: Turnstile null/invalid with dev test keys will still pass — production secret key required to test the 400 failure path.
**Why human:** Requires running server and crafted API requests; production Turnstile failure path requires production credentials.

---

### Summary

Phase 04 delivered all required artifacts with substantive, wired implementations:

- The contact form (`contact-form.tsx`, 241 lines) is fully implemented with state management, client-side validation, animated success state swap, invisible Turnstile, and honeypot — not a stub.
- The API route (`route.ts`, 75 lines) implements the full pipeline: honeypot check → Turnstile verification → HTML-escaped email via Resend — not a stub.
- ResultView integration is wired: `ContactForm` is imported and rendered with the `subdomain` prop.
- Mobile polish was applied: step indicator labels use responsive widths (`w-36 sm:w-48`); all pages have `px-4` horizontal padding; landing URL form stacks with `flex-col sm:flex-row`; result page iframe uses `aspect-[4/3] sm:aspect-video`.
- Submit button is `h-11` (44px) — meets touch target requirement.
- No phone field found (CONTACT-06 confirmed).
- Commits verified: `2564c8e`, `a8dd6d5`, `a7a456f`, `4b301aa` all exist in git log.

The phase goal is **achievable in production** pending external service configuration (Resend domain verification, Turnstile widget creation). All code paths are correctly wired. Human verification of the live email flow and visual mobile rendering is required before declaring complete.

---

_Verified: 2026-03-21T10:30:00Z_
_Verifier: Claude (gsd-verifier)_
