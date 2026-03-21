---
phase: 04-contact-form-polish
plan: 01
subsystem: ui, api
tags: [resend, turnstile, contact-form, email, spam-protection, react, next-api-route]

# Dependency graph
requires:
  - phase: 03-core-ui-landing-progress-result
    provides: ResultView component, shadcn UI components, AnimatePresence patterns
provides:
  - POST /api/contact route handler with honeypot + Turnstile + Resend email
  - ContactForm component with AnimatePresence success state swap
  - ResultView integration with contact form below iframe
  - .env.example documenting required environment variables
affects: [04-02-polish, deployment]

# Tech tracking
tech-stack:
  added: [resend, "@marsidev/react-turnstile"]
  patterns: [lazy-sdk-init, honeypot-silent-200, turnstile-invisible-mode]

key-files:
  created:
    - web/src/app/api/contact/route.ts
    - web/src/components/result/contact-form.tsx
    - web/.env.example
  modified:
    - web/src/components/result/result-view.tsx
    - web/package.json
    - web/.gitignore

key-decisions:
  - "Lazy Resend SDK initialization (getResend() factory) to avoid build-time API key requirement"
  - "Honeypot returns 200 OK to avoid revealing bot detection"

patterns-established:
  - "Lazy SDK init: wrap new Resend() in factory function for build-time safety"
  - "Contact form state machine: idle -> submitting -> success/error"
  - "Invisible Turnstile via @marsidev/react-turnstile with onExpire reset"

requirements-completed: [CONTACT-01, CONTACT-02, CONTACT-03, CONTACT-04, CONTACT-05, CONTACT-06]

# Metrics
duration: 4min
completed: 2026-03-21
---

# Phase 04 Plan 01: Contact Form Summary

**Contact form with Resend email delivery, invisible Turnstile + honeypot spam protection, and AnimatePresence success state swap on the result page**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-21T09:23:36Z
- **Completed:** 2026-03-21T09:27:12Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- POST /api/contact route with honeypot check, Turnstile verification, Resend email delivery, and HTML escaping
- ContactForm component with 3 fields (name, email, message), invisible Turnstile, hidden honeypot, loading state, and AnimatePresence swap to thank-you message
- ResultView integration with hr divider and 48px spacing below iframe content

## Task Commits

Each task was committed atomically:

1. **Task 1: Install dependencies, create API route handler, and add env var documentation** - `2564c8e` (feat)
2. **Task 2: Build ContactForm component and integrate into ResultView** - `a8dd6d5` (feat)

## Files Created/Modified
- `web/src/app/api/contact/route.ts` - POST handler: honeypot -> turnstile -> resend -> response
- `web/src/components/result/contact-form.tsx` - Contact form with fields, turnstile, honeypot, AnimatePresence swap
- `web/src/components/result/result-view.tsx` - Added ContactForm integration below iframe content
- `web/.env.example` - Documents RESEND_API_KEY, OWNER_EMAIL, Turnstile keys
- `web/package.json` - Added resend, @marsidev/react-turnstile dependencies
- `web/.gitignore` - Added !.env.example exception

## Decisions Made
- Lazy Resend SDK initialization via `getResend()` factory function to avoid build-time API key requirement (Resend constructor throws without key, breaking `npm run build`)
- Honeypot returns 200 OK with `{ ok: true }` to avoid revealing bot detection mechanism

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Lazy Resend SDK initialization for build-time safety**
- **Found during:** Task 2 (build verification)
- **Issue:** `new Resend(process.env.RESEND_API_KEY)` at module scope throws during `npm run build` when env var not set
- **Fix:** Wrapped in `getResend()` factory function, called at request time instead of module load
- **Files modified:** web/src/app/api/contact/route.ts
- **Verification:** `npm run build` passes without RESEND_API_KEY set
- **Committed in:** a8dd6d5 (Task 2 commit)

**2. [Rule 3 - Blocking] Added .env.example exception to .gitignore**
- **Found during:** Task 1 (commit)
- **Issue:** `.env*` pattern in .gitignore blocks .env.example from being tracked
- **Fix:** Added `!.env.example` negation rule
- **Files modified:** web/.gitignore
- **Verification:** `git add web/.env.example` succeeds
- **Committed in:** 2564c8e (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both fixes necessary for correct build and version control. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations above.

## User Setup Required

**External services require manual configuration.** The following environment variables must be set in `web/.env.local`:

- `RESEND_API_KEY` - From Resend Dashboard -> API Keys
- `OWNER_EMAIL` - Email address where leads should arrive
- `NEXT_PUBLIC_TURNSTILE_SITE_KEY` - From Cloudflare Dashboard -> Turnstile -> Add Widget (Invisible type)
- `TURNSTILE_SECRET_KEY` - From Cloudflare Dashboard -> Turnstile -> Widget settings

Development test keys are documented in `web/.env.example`.

## Known Stubs
None - all data flows are wired end-to-end.

## Next Phase Readiness
- Contact form feature is complete and build-verified
- Ready for 04-02 mobile polish pass
- Resend domain verification and Turnstile widget creation needed before production use

## Self-Check: PASSED

All created files verified on disk. All commit hashes found in git log.

---
*Phase: 04-contact-form-polish*
*Completed: 2026-03-21*
