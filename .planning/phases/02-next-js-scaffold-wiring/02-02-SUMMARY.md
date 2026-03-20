---
phase: 02-next-js-scaffold-wiring
plan: 02
subsystem: infra
tags: [makefile, cloudflare-tunnel, dev-workflow, ingress-routing]

# Dependency graph
requires:
  - phase: 02-next-js-scaffold-wiring/01
    provides: Next.js scaffold in web/ directory with package.json dev script
provides:
  - "make dev single-command concurrent dev server startup (FastAPI + Next.js)"
  - "Cloudflare tunnel ingress config with path-based routing (/api/* -> FastAPI, catch-all -> Next.js)"
affects: [03-core-ui, 04-contact-form-polish]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Makefile concurrent processes via $(MAKE) & wait", "Cloudflare tunnel path-based ingress routing"]

key-files:
  created: ["cloudflared/config.yml"]
  modified: ["Makefile"]

key-decisions:
  - "$(MAKE) recursive calls for concurrent dev servers (proper signal propagation on Ctrl+C)"
  - "Placeholder-based tunnel config (user fills UUID/hostname after one-time cloudflared setup)"

patterns-established:
  - "Dev workflow: make dev starts all services concurrently"
  - "Routing: /api/* to FastAPI (8080), everything else to Next.js (3000)"

requirements-completed: [FRONT-03, FRONT-04]

# Metrics
duration: 2min
completed: 2026-03-21
---

# Phase 02 Plan 02: Makefile Dev Targets + Cloudflare Tunnel Config Summary

**Concurrent dev workflow via `make dev` (FastAPI 8080 + Next.js 3000) and Cloudflare tunnel ingress with path-based routing**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-20T23:54:53Z
- **Completed:** 2026-03-20T23:56:32Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Single-command `make dev` starts both FastAPI and Next.js dev servers concurrently
- Cloudflare tunnel config routes /api/* to FastAPI (port 8080) and all other traffic to Next.js (port 3000)
- Existing Makefile targets (install, lint, test, ci) preserved unchanged

## Task Commits

Each task was committed atomically:

1. **Task 1: Add concurrent dev server targets to Makefile** - `fe56567` (feat)
2. **Task 2: Create Cloudflare tunnel ingress config** - `b12afd6` (feat)

## Files Created/Modified
- `Makefile` - Added dev, dev-api, dev-web targets for concurrent server startup
- `cloudflared/config.yml` - Cloudflare tunnel ingress rules with path-based routing

## Decisions Made
- Used `$(MAKE) dev-api & $(MAKE) dev-web & wait` pattern for concurrent processes -- ensures Ctrl+C propagates to both child processes via make's signal handling
- Tunnel config uses placeholder values (`<TUNNEL_UUID>`, `<HOSTNAME>`) since actual values require one-time manual cloudflared setup

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required

For Cloudflare tunnel to work, user must:
1. Install cloudflared: `brew install cloudflared`
2. Login: `cloudflared tunnel login`
3. Create tunnel: `cloudflared tunnel create sastaspace`
4. Replace `<TUNNEL_UUID>` and `<HOSTNAME>` in `cloudflared/config.yml`

## Next Phase Readiness
- Dev workflow ready -- `make dev` starts both servers for frontend development
- Tunnel config ready for production routing once user completes one-time setup
- Phase 02 complete, ready for Phase 03 (Core UI)

## Self-Check: PASSED

All files and commits verified.

---
*Phase: 02-next-js-scaffold-wiring*
*Completed: 2026-03-21*
