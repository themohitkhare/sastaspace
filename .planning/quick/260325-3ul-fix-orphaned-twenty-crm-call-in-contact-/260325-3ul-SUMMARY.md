---
phase: quick
plan: 260325-3ul
subsystem: api
tags: [contact-form, dead-code, twenty-crm]

requires: []
provides:
  - Clean contact form route with no dead CRM references
affects: []

tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - web/src/app/api/contact/route.ts
    - web/src/__tests__/api-contact.test.ts

key-decisions:
  - "Fixed pre-existing test assertion that expected 1 email send but route sends 2 (owner + transactional)"

patterns-established: []

requirements-completed: []

duration: 2min
completed: 2026-03-25
---

# Quick Task 260325-3ul: Fix Orphaned Twenty CRM Call in Contact Route

**Removed dead /twenty/person fetch from contact form API route, eliminating silent 2s timeout on every submission**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-24T21:17:57Z
- **Completed:** 2026-03-24T21:20:02Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- Removed orphaned Twenty CRM sync block (22 lines) from contact form API route
- Eliminated silent 2-second timeout penalty on every contact form submission
- Fixed pre-existing test bug where assertion expected 1 email call but route sends 2

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove orphaned Twenty CRM sync block from contact route** - `1e5aa714` (fix)

## Files Created/Modified
- `web/src/app/api/contact/route.ts` - Removed dead Twenty CRM sync try/catch block (lines 121-142)
- `web/src/__tests__/api-contact.test.ts` - Fixed assertion: `toHaveBeenCalledOnce()` to `toHaveBeenCalledTimes(2)` to match actual route behavior (owner email + transactional email)

## Decisions Made
- Fixed test assertion as part of task rather than leaving it broken -- the test was already failing before the route change due to the transactional email feature sending a second `emails.send` call

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed pre-existing test assertion mismatch**
- **Found during:** Task 1 (Remove Twenty CRM block)
- **Issue:** Test `sends email and returns ok:true on valid submission` expected `mockSend` to be called once, but route sends 2 emails (owner notification + transactional to submitter). Test was failing before this plan's changes.
- **Fix:** Changed `toHaveBeenCalledOnce()` to `toHaveBeenCalledTimes(2)` with explanatory comment
- **Files modified:** `web/src/__tests__/api-contact.test.ts`
- **Verification:** All 7 tests pass
- **Committed in:** `1e5aa714` (part of task commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Pre-existing test bug fixed to meet plan's success criteria. No scope creep.

## Issues Encountered
None beyond the pre-existing test bug documented above.

## Known Stubs
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Contact form route is clean with no dead code references
- All tests passing

---
*Quick task: 260325-3ul*
*Completed: 2026-03-25*
