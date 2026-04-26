# Phase 3 — Staging Acceptance

**Status at end of Section A:** PARTIAL — prep complete, full E2E gate pending operator run.

This doc lives alongside the cutover plan as the gate Section B (cutover) measures
against. It is filled in two passes:

1. End of Section A (this commit) — the executor records what was prepared and
   identifies what remains as an operator gate.
2. Operator pass — when the staging compose is brought up with the prod-equivalent
   shape, run the full E2E matrix and append the result.

---

## A6 — pre-flight (executor)

**Date:** 2026-04-26
**Commit:** bbf3b004 (worktree-agent-a9f7252d48942da74)

### What landed in Section A on this worktree

- A1: audit fixes N6 + N16 + N22 (manual-* moderation reasons + admin
  ADMIN_API_URL default cleared + cloudflared verify script).
- A2: workers Dockerfile reproducibility (N8) + GPU CLI rocm-smi-lib (N9).
- A3: `noop_owner_check` reducer + worker boot health check (N13).
- A5 (on `phase3/cutover-artifact-swap` branch, not merged): deploy.yml
  artifact swap from legacy → stdb for landing/notes/typewars/admin.
- Bindings regen: `noop_owner_check` reducer wired into
  `packages/stdb-bindings/src/generated/`.

### Tests at the worktree tip

```
modules/sastaspace cargo test --lib   → 65 passing (was 63 on main; +2 in A1+A3)
workers pnpm test                     → 25 passing (4 specs)
workers pnpm lint                     → clean
apps/admin pnpm typecheck             → clean
```

WASM build: clean (`cargo build --target wasm32-unknown-unknown --release`).
Worker container build: clean (`docker build -f workers/Dockerfile .` from repo root).
Worker container boots and idles cleanly with no agents enabled.

### Local STDB smoke (sanity check — not the E2E gate)

The module was published to the local STDB (`spacetime publish -s local sastaspace`)
and the bindings regenerated. Calling `noop_owner_check` from the local CLI's
non-owner identity returns "not authorized" (530 HTTP). This confirms the
reducer correctly rejects non-owner calls — the failure mode the worker boot
check catches. The positive case (owner identity → ok) requires the prod owner
JWT and is verified by the operator on taxila during A4 Step 6.

### What remains as the A6 operator gate

The full A6 acceptance — running the Playwright suite against a staging
compose with `profile=stdb-native`, all four `WORKER_*_ENABLED=true`, all
four legacy Python services still up, in BOTH `E2E_AUTH_BACKEND=fastapi`
and `=stdb` matrix entries — is an operator action. Steps:

1. Bring up the staging stack (Plan A6 Steps 1–5).
2. `set_e2e_test_secret` once on the staging STDB (Plan A6 Step 4).
3. Run the FULL Playwright matrix, both backends (Plan A6 Step 6).
4. Append the result to this doc as a "Result" subsection.
5. Tear down the staging extras (Plan A6 Step 9).

After A6 is green, run new §A7 (moderator E2E spec — see
`tests/e2e/specs/moderator.spec.ts`) and pause for owner approval before B1.

### Known carve-outs

- The Section A executor cannot mint or load the prod owner JWT into a
  staging compose; the operator does that as part of A4 (workers/.env on
  taxila) and A6 Step 4 (E2E secret on staging STDB).
- The Section A executor cannot SSH to taxila to provision workers/.env;
  A4's runbook is documented in the plan and is an operator action before
  any B-task fires.

---

## Result

(Filled in by the operator after running the A6 matrix.)

```
- E2E_AUTH_BACKEND=fastapi: <PASS/FAIL> — N specs, M assertions, T sec
- E2E_AUTH_BACKEND=stdb:    <PASS/FAIL> — N specs, M assertions, T sec
```

## Stack

(Filled in by the operator — `docker compose ps` output of the staging stack
during the run.)
