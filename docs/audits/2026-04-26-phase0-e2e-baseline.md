# Phase 0 E2E Baseline

**Date:** 2026-04-26
**Commit:** 594e5f6c4ed940d0c2c038f119bea32623ff7d61

Ran the full Playwright suite against live prod after the SpacetimeDB-native
rewire's Phase 0 changes (module rename, workers skeleton, LocalAI install).
Stack at this point: spacetime + ollama + localai + workers (idle) + 4 Python
services (still active) + 4 nginx static apps.

The dev compose now adds two new sidecar containers (`workers`, `localai`),
both idling — not consumed by any frontend yet. Phase 0 is purely additive at
the runtime level; no live behavior is supposed to change.

## Run command

```bash
cd tests/e2e
E2E_TEST_SECRET=<from prod auth container> pnpm exec playwright test \
  specs/admin.spec.ts specs/auth.spec.ts \
  specs/comments-anon.spec.ts specs/comments-signed-in.spec.ts \
  specs/landing.spec.ts specs/notes.spec.ts
```

## Result — tracked specs (the regression gate)

**PASS — 30 tests, 30 passed, 0 failed.** Total ~35 s.

Tracked specs covered:
- `specs/admin.spec.ts` — admin queue: anon redirect; non-owner reject; owner-connect (auth-gated)
- `specs/auth.spec.ts` — magic-link flow, expired/used token paths, prev_identity claim
- `specs/comments-anon.spec.ts` — anonymous read paths
- `specs/comments-signed-in.spec.ts` — signed-in submit/moderation flow
- `specs/landing.spec.ts` — landing nav (10 tests, all pass)
- `specs/notes.spec.ts` — notes index, articles, sign-in modal hydration (8 tests, all pass)

This is the regression gate Phase 1+ measures against.

## Result — full suite including untracked specs (informational)

The repo also contains **untracked** in-flight typewars E2E specs (added by the
user during the typewars-auth feature work, not yet committed at the time of
Phase 0):

- `tests/e2e/specs/typewars-auth.spec.ts`
- `tests/e2e/specs/typewars-battle.spec.ts`
- `tests/e2e/specs/typewars-leaderboard.spec.ts`
- `tests/e2e/specs/typewars-legion-swap.spec.ts`
- `tests/e2e/specs/typewars-profile.spec.ts`
- `tests/e2e/specs/typewars-register.spec.ts`
- `tests/e2e/specs/typewars-warmap.spec.ts`

Running the **full** 54-test suite: **53 pass, 1 fail.**

The single failing test is in untracked work (`typewars-auth.spec.ts:19` —
"magic-link round trip stores JWT under typewars:auth_token and lands on
warmap"). The failure root cause is unrelated to Phase 0:

> The `signInTypewars` helper in `tests/e2e/helpers/auth.ts:73-84` calls
> `/auth/verify` without a `prev_identity` query param. The auth service
> (`services/auth/main.py`, still in Python through Phase 3) returns a 400 with
> "Missing or invalid prev_identity in callback URL." The helper's comment
> claims the verify endpoint accepts no `prev_identity`, but in production it
> doesn't.

This is a real bug in the in-flight typewars-auth work — pre-existing and not
caused by the module rename, workers scaffold, or LocalAI install. Phase 0
deliberately does not modify the helper or spec because they are part of the
user's separately-tracked work; the user explicitly directed Phase 0 to leave
their uncommitted/untracked changes alone.

**Phase 0 acceptance criterion satisfied:** every tracked test still passes
after the rename. Untracked in-flight tests are the user's responsibility to
land green before merging the typewars-auth feature.
