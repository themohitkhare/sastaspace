---
phase: quick
plan: 260325-3uk
subsystem: infra
tags: [next.js, docker, k8s, runtime-env, entrypoint]

provides:
  - "Runtime NEXT_PUBLIC_* env injection via window.__ENV__ pattern"
  - "Container entrypoint.sh that generates __env.js at startup"
  - "env.ts helper module for all client-side env access"
affects: [frontend, deployment, ci]

tech-stack:
  added: []
  patterns: ["window.__ENV__ runtime env injection for Next.js standalone containers"]

key-files:
  created:
    - web/src/lib/env.ts
    - web/entrypoint.sh
  modified:
    - web/src/lib/sse-client.ts
    - web/src/components/result/result-view.tsx
    - web/src/components/result/contact-form.tsx
    - web/src/app/layout.tsx
    - web/Dockerfile
    - k8s/frontend.yaml
    - .github/workflows/deploy.yml

key-decisions:
  - "window.__ENV__ pattern with process.env fallback for seamless local dev"
  - "entrypoint.sh writes __env.js to /app/public/ at container start"
  - "NEXT_PUBLIC_TURNSTILE_SITE_KEY sourced from k8s secret via secretKeyRef"

requirements-completed: []

duration: 4min
completed: 2026-03-25
---

# Quick Task 260325-3uk: Fix NEXT_PUBLIC_BACKEND_URL Runtime Injection Summary

**Runtime env injection for NEXT_PUBLIC_* vars via entrypoint.sh + window.__ENV__ pattern, replacing build-time inlining**

## What Changed

### Task 1: Runtime env helper and entrypoint script (162bbe4c)
- Created `web/src/lib/env.ts` with `getBackendUrl()`, `getTurnstileSiteKey()`, `isTurnstileEnabled()` helpers
- Each helper checks `window.__ENV__` first (production), falls back to `process.env` (local dev/SSR)
- Created `web/entrypoint.sh` that generates `/app/public/__env.js` from container env vars before starting Node

### Task 2: Update all client-side env references (8682ebd5)
- Replaced all `process.env.NEXT_PUBLIC_BACKEND_URL` in client code with `getBackendUrl()`
- Replaced `process.env.NEXT_PUBLIC_ENABLE_TURNSTILE` and `NEXT_PUBLIC_TURNSTILE_SITE_KEY` with env.ts helpers
- Added `<script src="/__env.js" />` to layout.tsx head (404s silently in dev, loads in production)

### Task 3: Dockerfile, k8s, and CI updates (b9f70ffe)
- Removed `ARG`/`ENV` for `NEXT_PUBLIC_*` from Dockerfile; switched CMD to ENTRYPOINT using entrypoint.sh
- Added runtime `env:` block to k8s frontend.yaml with `NEXT_PUBLIC_BACKEND_URL`, `NEXT_PUBLIC_TURNSTILE_SITE_KEY`, `NEXT_PUBLIC_ENABLE_TURNSTILE`
- Removed `--build-arg NEXT_PUBLIC_*` from CI deploy workflow

## Verification

- TypeScript compiles cleanly (`npx tsc --noEmit` passes)
- Vitest: 3 pre-existing failures unrelated to changes (same on base branch), 45 tests pass
- No `process.env.NEXT_PUBLIC_BACKEND_URL` remains in client-side code (only in server-side `api/contact/route.ts`)
- Dockerfile references entrypoint.sh; k8s manifest has runtime env vars; CI has no build-arg for NEXT_PUBLIC_*

## Deviations from Plan

None -- plan executed exactly as written.

## Known Stubs

None.
