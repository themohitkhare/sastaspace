# SpacetimeDB-Native Rewire — Master Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to dispatch the parallel workstream plans (Phase 1 & 2). Phase 0, 3, 4 use superpowers:executing-plans for serial execution. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace 4 Python services with STDB reducers + a single TS workers process, ending with zero Python in the project source tree.

**Architecture:** Reducers in Rust STDB modules hold all business logic; workers (Mastra agents in one Node process) shuttle external I/O (Resend, Ollama, LocalAI, Docker socket) by subscribing to "intent" tables and calling result reducers. LocalAI joins Ollama on taxila as a sibling self-hosted model server.

**Tech Stack:** Rust (SpacetimeDB modules), TypeScript (Next.js apps + Mastra workers), Docker Compose, Cloudflared, Ollama, LocalAI, Playwright (E2E).

**Spec:** `docs/superpowers/specs/2026-04-26-spacetimedb-native-design.md`

---

## How to use this plan

This plan is a master orchestrator. The actual work lives in **child plan files** in this same directory. Execute in this order:

| Phase | Mode | Child plan file | Concurrency |
|---|---|---|---|
| 0 — Foundation | Serial | `2026-04-26-stdb-native-phase0.md` ✅ written | 1 |
| 1 — Reducers + workers | Parallel | `…-phase1-w1-auth.md` ✅, `…-w2-admin.md` ⏳, `…-w3-deck.md` ⏳, `…-w4-moderator.md` ⏳ | 4 |
| 2 — Frontend rewire | Parallel | `2026-04-26-stdb-native-phase2-f1-notes.md` ⏳, `…-f2-typewars.md` ⏳, `…-f3-admin.md` ⏳, `…-f4-deck.md` ⏳ | 4 |
| 3 — Cutover | Serial | `2026-04-26-stdb-native-phase3-cutover.md` ⏳ | 1 |
| 4 — Cleanup | Serial | `2026-04-26-stdb-native-phase4-cleanup.md` ⏳ | 1 |

✅ = drafted with this commit and ready to execute. ⏳ = drafted as a Task at end of preceding phase (deferred so it can use the actual reducer signatures and table names that landed). W2–W4 plans are intentionally drafted in parallel during Phase 0 execution — see "How parallel work bootstraps" below.

**Phase gates:** Each phase ends with **full E2E suite green**. No phase starts until the preceding phase has met its acceptance criteria.

### How parallel work bootstraps

To save calendar time, **W2/W3/W4 plan drafting runs in parallel with Phase 0 execution**:

```
   ┌─ exec Phase 0 (subagent A, serial) ─────┐
   │                                         │
t──┼─ draft W2 plan (subagent B) ────────────┼──→ all Phase 1 work parallel-dispatchable
   │                                         │
   ├─ draft W3 plan (subagent C) ────────────┤
   │                                         │
   └─ draft W4 plan (subagent D) ────────────┘
```

W2/W3/W4 plans use the same shape as W1 (already drafted) — `…-phase1-w1-auth.md` is the template. Each plan-drafting subagent reads the spec and W1 to learn the pattern, then produces its workstream's plan. By the time Phase 0 finishes, all 4 Phase 1 plans exist and can be dispatched as 4 parallel implementation subagents.

Phase 2 plan-drafting follows the same pattern: drafted in parallel with Phase 1 execution, using the W1–W4 reducer signatures that land.

---

## Repo file layout deltas

This is the inventory of what gets created, modified, or deleted across the whole rewire. Sub-plans reference these paths.

**Created (top-level dirs):**
- `workers/` (Phase 0)
- `modules/` (Phase 0 — by renaming `module/` and `game/`)
- `infra/localai/` (Phase 0)
- `infra/deck-out/` (Phase 1 W3 — host-side dir for served zips)

**Created (files in existing dirs):**
- `workers/package.json`, `workers/Dockerfile`, `workers/src/index.ts`, `workers/src/shared/{stdb.ts,mastra.ts,env.ts}`, `workers/src/agents/{auth-mailer,admin-collector,deck-agent,moderator-agent}.ts` (Phase 0 skeletons; Phase 1 fleshes each)
- `apps/notes/src/app/auth/verify/page.tsx` (Phase 2 F1)
- `apps/typewars/src/app/auth/verify/page.tsx` (Phase 2 F2)
- `STRUCTURE.md` (Phase 4)

**Modified:**
- `modules/sastaspace/src/lib.rs` (Phase 1 — each W adds tables + reducers)
- `infra/docker-compose.yml` (Phase 0 base edits, Phase 1 worker block, Phase 3 service removals)
- `infra/cloudflared/*.yml` (Phase 3 — drop `api.sastaspace.com` ingress)
- `apps/admin/src/components/panels/*.tsx` (Phase 2 F3)
- `apps/landing/src/app/lab/deck/Deck.tsx` (Phase 2 F4)
- `apps/notes/src/app/page.tsx`, `apps/notes/src/lib/auth.ts` (Phase 2 F1)
- `apps/typewars/src/app/page.tsx`, `apps/typewars/src/lib/auth.ts` (Phase 2 F2)
- `packages/stdb-bindings/src/*` (regenerated automatically — Phase 1 each W ends with regenerate step)
- `packages/auth-ui/src/SignInModal.tsx` (Phase 2 F1 — switch fetch to reducer call)
- `pnpm-workspace.yaml` (Phase 0 — add `workers/`, drop nothing yet)
- `Cargo.toml` workspace, CI workflows (Phase 0 — module rename)

**Deleted (Phase 4):**
- `services/auth/`, `services/admin-api/`, `services/deck/` — entire trees
- `infra/agents/moderator/` — entire tree
- The 4 Python service blocks in `infra/docker-compose.yml`

---

## Cross-cutting rules every sub-plan follows

- **TDD.** Every reducer ships with a Rust unit test. Every worker agent ships with a Vitest spec covering happy + one failure path. Frontend changes ship with Playwright spec edits.
- **Feature flag every worker.** Each agent in `workers/src/index.ts` checks `env.WORKER_<NAME>_ENABLED` before registering. Default to `false` in `infra/docker-compose.yml` until cutover.
- **Both paths coexist.** Through Phase 1–3, the Python service AND the new worker can both run. Cutover (Phase 3) flips the flag and stops the Python container per worker, one at a time.
- **STDB bindings regen at end of every reducer-touching task.** Run `cd modules/sastaspace && spacetime generate --lang typescript --out-dir ../../packages/stdb-bindings/src` and commit the regenerated files alongside the reducer.
- **Frequent commits.** One logical step = one commit. No multi-task commits.
- **Pre-commit hook.** Repo has a pre-commit script (currently no-op per `[pre-commit] no Makefile/ci target — skipping` in the spec commit). Don't bypass with `--no-verify` if/when it's re-enabled.
- **graphify update.** After each phase boundary commit, run `graphify update .` to keep the knowledge graph current.

---

## Phase 0 — Foundation (start here)

Phase 0 is fully detailed in `2026-04-26-stdb-native-phase0.md`. It produces:

- `modules/sastaspace/` and `modules/typewars/` (renamed)
- `workers/` skeleton boots cleanly with no agents registered
- LocalAI installed on taxila and verified with a manual MusicGen call
- Baseline E2E suite documented as green (or fixed to be green before any other work)
- Updated docker-compose with the new directories wired
- Updated CI workflows referencing the new paths

**Cannot proceed to Phase 1 until Phase 0 acceptance is met.**

---

## Phase 1 — Parallel workstream dispatch (4 agents)

Once Phase 0 lands, dispatch **4 parallel subagents** using superpowers:dispatching-parallel-agents — one per workstream. Each follows its own plan file:

| Workstream | Plan | Touches |
|---|---|---|
| W1 auth-mailer | `…-phase1-w1-auth.md` | `modules/sastaspace/src/lib.rs` (auth tables/reducers), `workers/src/agents/auth-mailer.ts` |
| W2 admin-collector | `…-phase1-w2-admin.md` | `modules/sastaspace/src/lib.rs` (metrics tables/reducers), `workers/src/agents/admin-collector.ts` |
| W3 deck-agent | `…-phase1-w3-deck.md` | `modules/sastaspace/src/lib.rs` (deck tables/reducers, fallback rules port), `workers/src/agents/deck-agent.ts` |
| W4 moderator-agent | `…-phase1-w4-moderator.md` | `workers/src/agents/moderator-agent.ts` (no new tables — uses existing `comment`) |

**Coordination risk:** All four W's modify `modules/sastaspace/src/lib.rs`. Risk of merge conflicts. Mitigation: each W appends to clearly delimited sections with comment fences (e.g. `// === auth-mailer tables ===` … `// === end auth-mailer tables ===`). The first W to merge wins; subsequent W's rebase trivially because the conflicts are append-only.

**Phase 1 acceptance:**
- All 4 worker agents present in `workers/src/agents/`, each behind a feature flag, each with `WORKER_*_ENABLED=false` in compose
- All new reducers in `modules/sastaspace/src/lib.rs` have unit tests
- All 4 workers have Vitest specs (happy + 1 failure path each)
- Bindings regenerated and committed
- `docker compose up workers` starts cleanly with all flags off (no agents register, process stays alive)
- Existing Python services still pass their existing tests (untouched)
- Full E2E baseline still green

---

## Phase 2 — Frontend rewire (4 parallel agents)

After Phase 1, **draft the four Phase 2 plans** (now we know the actual reducer signatures from regenerated bindings). Then dispatch 4 parallel subagents:

| Workstream | Plan to draft | Touches |
|---|---|---|
| F1 notes auth | `…-phase2-f1-notes.md` | `apps/notes/src/app/auth/verify/page.tsx`, `apps/notes/src/lib/auth.ts`, `packages/auth-ui/src/SignInModal.tsx` |
| F2 typewars auth | `…-phase2-f2-typewars.md` | `apps/typewars/src/app/auth/verify/page.tsx`, `apps/typewars/src/lib/auth.ts` |
| F3 admin panels | `…-phase2-f3-admin.md` | `apps/admin/src/components/panels/*.tsx`, `apps/admin/src/lib/data.ts` (delete), `apps/admin/src/hooks/` |
| F4 deck frontend | `…-phase2-f4-deck.md` | `apps/landing/src/app/lab/deck/Deck.tsx` |

**Phase 2 acceptance:**
- Each app talks to the new reducer paths through a per-app env flag (e.g. `NEXT_PUBLIC_USE_STDB_AUTH=true`) so the rewired path can be enabled per app without one-shot risk
- E2E specs for each app pass against both the legacy path and the rewired path (run twice in CI matrix)
- No production traffic flipped yet

---

## Phase 3 — Cutover (sequential)

Plan to draft after Phase 2: `2026-04-26-stdb-native-phase3-cutover.md`

Outline:
1. Set `WORKER_AUTH_MAILER_ENABLED=true`, restart workers; observe `pending_email` queue draining for 1 hour. Stop `sastaspace-auth` container. Run E2E auth specs.
2. Repeat for admin-collector → stop `sastaspace-admin-api`. Run admin E2E.
3. Repeat for deck-agent → stop `sastaspace-deck`. Run deck E2E.
4. Repeat for moderator-agent → stop `sastaspace-moderator`. Run moderator E2E (synthetic comment + verify status flips within 10 s).
5. Drop `api.sastaspace.com` ingress from cloudflared config.
6. Final full E2E suite run on prod-equivalent staging compose. Must be 100% green.
7. Add `auth.sastaspace.com → 410 Gone` static page (one-release deprecation per spec open question 1).

**Phase 3 acceptance:** all 4 Python service containers stopped, `docker compose ps` shows no `sastaspace-{auth,admin-api,deck,moderator}`. Full E2E green.

---

## Phase 4 — Cleanup (sequential)

Plan to draft after Phase 3: `2026-04-26-stdb-native-phase4-cleanup.md`

Outline:
1. `git rm -r services/auth/ services/admin-api/ services/deck/ infra/agents/moderator/`
2. Remove the 4 Python service blocks from `infra/docker-compose.yml`
3. Remove `auth.sastaspace.com` cloudflared route (after 410-page period elapses)
4. Move `deck-step2-expanded.png`, `deck-step3-results.png` to `docs/deck/` (or delete)
5. Move root `idea.md` to `docs/archive/` or delete
6. Move `SECURITY_AUDIT.md` to `docs/audits/2026-04-25-security.md` (rename per audit L1)
7. Add `.playwright-mcp/` to `.gitignore`
8. Write `STRUCTURE.md` at repo root: one paragraph per top-level dir (apps, workers, modules, packages, infra, docs, tests)
9. Update `README.md` to reflect the new architecture
10. Run `graphify update .` and verify god nodes shifted away from Python types
11. Final E2E run

**Phase 4 acceptance:**
- `find . -name '*.py' -not -path '*/node_modules/*' -not -path '*/.venv/*'` → empty
- `docker compose ps` shows: spacetime, ollama, localai, workers, landing, notes, admin, typewars, cloudflared (and nothing more)
- `STRUCTURE.md` exists
- E2E green
- Updated graph snapshot committed

---

## Risk & rollback

See spec § "Rollback plan." TL;DR: through Phase 3, both paths coexist. A single env flag flip + `docker compose up <service>` restores the Python path in ~5 minutes. Phase 4 is irreversible without `git revert`; do not start Phase 4 until Phase 3 has been stable for 48 h.

---

## Self-review note

This master plan intentionally defers full Phase 2/3/4 task drafts. Reason: those plans benefit from knowing the actual reducer signatures and table column types that land in Phase 1. Drafting them now would either:
- Repeat the spec verbatim (low information add), or
- Lock in fictional signatures that turn into rework

The Phase 1 plans (W1–W4) are detailed because Phase 0 doesn't change reducer signatures; the spec already nails them down.

**Next action:** Execute `2026-04-26-stdb-native-phase0.md`.
