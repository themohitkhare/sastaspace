# SpacetimeDB-Native Rewire — Cross-Cutting Risk Audit

**Date:** 2026-04-26
**Scope:** Audit of the SpacetimeDB-native rewire (spec `docs/superpowers/specs/2026-04-26-spacetimedb-native-design.md`, master plan `docs/superpowers/plans/2026-04-26-stdb-native-master.md`) — Phase 0 ✅, Phase 1 ✅ merged, Phase 2 plans drafted (not yet implemented), Phase 3 cutover plan not yet drafted.
**Type:** Read-only cross-cutting risk review. No code modified.
**Methodology:** Read graphify GRAPH_REPORT, reviewed compose, CI workflow, cloudflared scripts, all package.json files, all Phase 2 plan files, the sastaspace and typewars Rust modules, every workers/src file, the E2E helpers and specs, and the existing audits. Cross-checked plan assumptions against generated bindings (`packages/stdb-bindings/src/generated/`) and against actual landed source (`workers/src/shared/stdb.ts`, `apps/admin/src/hooks/useStdb.ts`).

---

## Summary

The rewire is in good shape at the reducer + worker layer (Phase 1 landed cleanly with a single bindings regen on main and one inline gap-fill — `claim_progress_self`). The high-risk surface for Phase 3 cutover is **not** the code that is written, but four classes of gap that the implementer reports under-emphasise:

1. **Phase 2 plans still encode SDK-shape assumptions that Phase 1 disproved** — the same drift the user enumerated, baked into example code that an implementer subagent will copy verbatim.
2. **Two pieces of Phase 1 infrastructure ship a load-bearing URL nothing actually serves yet** — most notably `deck.sastaspace.com` (the worker writes zips to a directory with no nginx + no tunnel ingress).
3. **The E2E suite is structurally tied to `auth.sastaspace.com`** — when Phase 3 stops the FastAPI auth container, every signed-in spec breaks until helpers are rewritten.
4. **CI assumes the Python services exist** — the `auth`/`moderator` jobs will fail outright when their directories are deleted in Phase 4, and the `e2e` job's `needs:` graph references jobs that won't exist.

**Counts:** 5 CRITICAL · 8 HIGH · 9 MEDIUM · 5 LOW = **27 findings.** The single most important new risk is **N1 (deck.sastaspace.com has no nginx server + no cloudflared ingress)** — Phase 1 W3 shipped a worker that writes to `infra/deck-out/` and reports a public URL that returns 404 because the static-server side was never built.

---

## Confirmed known issues (from the implementer reports)

Each row records the issue, where it is captured today, and what's still missing.

### K1 — `reducers.requestPlan(conn, …)` vs `conn.reducers.requestPlan({…})` shape drift
- **Captured in:** `workers/src/shared/stdb.ts:81-96` (worker uses the `conn.reducers` form correctly via `Record<string, fn>` cast). Worker comments explicitly note the shape.
- **NOT captured in:** Phase 2 plans `…-f1-notes.md:148, 179` and `…-f2-typewars.md:212` use the OLD `reducers.requestMagicLink(conn, …)` shape in copy-paste-ready code blocks. F1 plan line 188 hand-waves "if the actual surface differs, adapt to what packages/stdb-bindings/src/generated/index.ts actually exports" but doesn't fix the example. **Implementer subagent will copy the broken form first, then debug. Wastes a round trip.**
- **Action:** Patch the F1/F2 plans before dispatching Phase 2 (see Phase-3-prep checklist).

### K2 — `tables.planRequest(conn)` vs `conn.db.plan_request` snake_case
- **Captured in:** `workers/src/agents/admin-collector.ts:174-176` (uses `conn.db.logInterest` — camelCase form because the SDK's accessor map camelCases) and `workers/src/agents/auth-mailer.ts:59` (`conn.db as { pendingEmail }`). Phase 1 implementers all converged on camelCase via `conn.db.<x>` after live testing.
- **Spec/plan exposure:** Phase 2 plans use a mix of `conn.db.planRequest` and `tables.planRequest` — no single statement of truth. The deck-agent file landed with both forms documented as a structural type (`workers/src/agents/deck-agent.ts:407-417`).
- **Action:** Add an SDK-errata block to the spec (see Phase-3-prep). Camel/snake matters because the bindings generator emits **camelCase accessors** on the runtime `conn.db.<name>` even though Rust source is snake_case.

### K3 — `row.createdAt.toMicrosSinceUnixEpoch()` vs `.microsSinceUnixEpoch` getter
- **Captured in:** Nowhere — the workers don't read timestamps from rows in this manner. The Rust side (`modules/sastaspace/src/lib.rs:548`) uses the method form correctly because it's Rust SDK, not TS SDK.
- **NOT captured in:** Phase 2 F4 plan `…-f4-deck.md:226, 324` uses `row.createdAt.toMicrosSinceUnixEpoch()` in inline structural types and runtime checks. Implementer will hit a TypeError at runtime.
- **Action:** Fix in the F4 plan and add to SDK-errata.

### K4 — `onInsert` returns void, not unsubscribe; use `removeOnInsert(cb)`
- **Captured in:** Nowhere in code; workers never unsubscribe (they hold the subscription for process lifetime).
- **NOT captured in:** Phase 2 F4 plan `…-f4-deck.md:261, 351` does `const offInsert = planTable.onInsert((_ctx, row) => …)` and treats `offInsert` as a callable cleanup. SDK does NOT return a function — `onInsert` returns `void`. The frontend (where mount/unmount cleanup matters) is the place this will explode at runtime.
- **Action:** Fix in F4 plan; add to SDK-errata.

### K5 — `withDatabaseName` not `withModuleName`
- **Captured in:** `workers/src/shared/stdb.ts:20-22` (explicit comment), `apps/notes/src/lib/spacetime.ts:29`, `apps/typewars/src/lib/spacetime.ts:23`, `apps/landing/src/lib/spacetime.ts:52`, `apps/admin/src/hooks/useStdb.ts:16,24`. **All landed code is correct.**
- **NOT captured in:** Phase 2 F1 plan `…-f1-notes.md:120` still emits `.withModuleName(STDB_MODULE)` in the example.
- **Action:** Fix in F1 plan; add to SDK-errata.

### K6 — Reducer return values not surfaced to TS clients
- **Captured in:** Nowhere explicitly. Workers don't try to read return values; they observe via subscription. Frontend (Phase 2) is where this will bite — the F1 plan's `reducers.requestMagicLink.onSuccess(...)` shape (`…-f1-notes.md:138-148`) implies the SDK exposes a per-call success/failure callback, which it does NOT. The actual SDK 2.1 pattern is: call returns `Promise<void>` (resolves when sent, not when reducer succeeds), then watch the *table change* the reducer caused, OR wait for an `onReducer<Name>` event on the connection.
- **Action:** Phase 2 F1 implementer needs an explicit pattern: "fire-and-forget the reducer call; wait for the row insert/update via subscription handler." Add to SDK-errata.

### K7 — F2 needed `claim_progress_self` reducer (gap-fill from F2 plan-drafter)
- **Captured in:** Commit `947c8f8a` adds the reducer to `modules/typewars/src/player.rs`. Bindings regenerated. F2 plan references it (line 35: "F1 modifies … F2 just consumes that swap … prev_identity_hex=<current guest identity hex>"). **Closed.**
- **Residual risk:** The reducer was added in a one-off commit on main, not as part of any phase plan. Phase 3 cutover plan must include "verify all custom reducers added during Phase 1/2 still exist post-deploy" as a check.

### K8 — F2's flag-driven flow needs F1's SignInModal `onRequest` prop
- **Captured in:** F2 plan lines 20, 27 explicitly note "F1 (notes) modifies `packages/auth-ui/src/SignInModal.tsx` to swap fetch for the reducer call. F2 does NOT touch that file — it consumes the swap via the per-app `NEXT_PUBLIC_USE_STDB_AUTH` flag." F2 also has a guard: "If F2 races ahead of F1, defer the modal-swap step until F1 lands and rebase."
- **Residual risk:** This dependency is in prose, not in CI. If both F1 and F2 dispatch as parallel subagents (which the master plan says they should), F2 could merge first and ship a typewars build that uses an unmodified modal. Recommend serial F1→F2 ordering or a CI gate.

### K9 — `oneShotAgent` / `ollamaProvider` factory collision in `workers/src/shared/mastra.ts`
- **Captured in:** `workers/src/shared/mastra.ts:21-65` shows both `oneShotAgent()` (W4) and `ollamaProvider()` (W3) coexisting. **Auto-resolved on merge — no follow-up needed.**

### K10 — W2's `connection: unknown` made redundant by W1's typed `StdbConn`
- **Captured in:** `workers/src/shared/stdb.ts:25-32` — `StdbConnection = any` + `connection: StdbConnection`. W2's `unknown` was upgraded to W1's `any` on merge. **Closed.**

### K11 — `modules/sastaspace/src/lib.rs` Cargo.toml deps merged manually per W
- **Captured in:** Implicit in the merge commits (`83ea06b9`, `cb588ccf`, `3fb4e68d`). Lock file regenerated each merge.
- **Residual risk:** Phase 2 frontend work doesn't add module deps, so this is closed for now. Phase 3 may add new reducers (e.g. status-flip helpers) — same conflict shape will recur. Recommend: any cutover-time reducer additions land via a single dedicated PR.

### K12 — `NEXT_PUBLIC_USE_STDB_*` build-time vs runtime
- **Captured in:** F2 plan lines 635 and 774 explicitly call this out and propose two CI builds. F4 plan lines 643-655 documents an `ARG NEXT_PUBLIC_USE_STDB_DECK` Dockerfile arg.
- **NOT captured in:** Reality — apps/landing, apps/notes, apps/typewars, apps/admin are served by **static nginx in compose**; there is no Node build stage in compose, so `ARG` in a Dockerfile means nothing for the static-export path. The build happens on the GH Actions runner (see `.github/workflows/deploy.yml`). **Two builds = two CI matrix entries running `pnpm build` with different env, then producing two `out/` artifacts.** F1 plan glosses this; F2 plan acknowledges; F3 admin plan doesn't address; F4 plan addresses but with a Dockerfile shape that doesn't apply.
- **Action:** Phase 3 cutover plan must define the matrix CI strategy explicitly. See N3.

### K13 — `apps/landing` is static nginx; no Node build stage to receive build args
- **Captured in:** Phase 0 audit (`docs/audits/2026-04-26-phase0-e2e-baseline.md`) implicit only.
- **Action:** Spec explicitly. See N3.

### K14 — F1/F2/F4 may add conflicting matrix entries to `tests/e2e/playwright.config.ts`
- **Captured in:** F1 plan lines 855-862 propose a second project entry. F4 plan line 831 proposes a similar second project. F2 doesn't propose config edits (uses `addInitScript` runtime override).
- **Action:** Phase 2 implementers MUST coordinate the playwright.config.ts edit. The current file (read at audit time) has only one project (`desktop-chromium`). If both F1 and F4 each add a `*-stdb` project they conflict. Recommend: a single helper plan-step (or pre-Phase-3 task) consolidates the matrix.

### K15 — Live-stack smoke tests not run during workstream development
- **Captured in:** Phase 1 W1-W4 commit messages note unit-test-only coverage. Phase 0 baseline doc mentions the typewars-auth.spec.ts failure caused by an unrelated bug.
- **Residual risk:** Phase 3 is the FIRST end-to-end test. The cutover plan needs an explicit pre-cutover full smoke session in staging.

### K16 — SpacetimeDB v2.1 has no host-runnable TestContext
- **Captured in:** Each W's plan describes "extracted helper unit tests" (e.g. `validate_magic_link_args`, `_local_draft` port, `wrap_for_classifier`).
- **Residual risk:** Reducer body coverage exists only via live smoke. Phase 3 cutover relies on E2E to catch reducer regressions.

### K17 — `Deck.tsx` grew from 1421 → 1516 lines; M1 from structure audit unchanged
- **Captured in:** Structure audit `docs/audits/2026-04-26-structure-audit.md` § M1.
- **Residual risk:** F4 will add ~100 more lines (flag branching). Phase 4 should split Deck.tsx as part of the M1 promotion-out-of-`/lab` cleanup.

### K18 — Bindings regen race avoided by single post-merge run
- **Captured in:** Commit `4b55496a` "regenerate stdb-bindings after Phase 1 W1-W4 merge."
- **Residual risk:** Phase 3 may add reducers (e.g. retry helpers). Same single-regen discipline must apply.

### K19 — Owner-STDB-token UX (manual paste per browser)
- **Captured in:** F3 plan lines 26 + 89-96 (`OwnerTokenSettings.tsx` + `localStorage.admin_stdb_owner_token`).
- **Residual risk:** Single-owner footgun. If the owner clears localStorage, every admin write breaks until they re-paste. Worth tracking but acceptable for a personal-blog admin panel.

### K20 — User WIP zones (admin/*, tests/e2e/*, services/admin-api, services/deck) coexist with merged work
- **Captured in:** Phase 0 baseline doc lines 39-70 explicitly mention. Implementer subagents have been careful so far.
- **Residual risk:** Phase 4 deletes `services/admin-api/` and `services/deck/`. If the user has uncommitted local changes in those trees at cutover time, `git rm -r` will succeed (because untracked files in a `rm -r`'d dir survive rm — but if user ran `git add` they'd be lost). Phase 4 plan must include "check git status clean in these dirs before deletion."

---

## NEW findings (discovered in this audit)

### CRITICAL

#### N1 — `deck.sastaspace.com` has no nginx server and no cloudflared ingress
**Category:** Infra wiring gap.
**Severity:** CRITICAL — Phase 1 W3 ships a worker that writes WAV zips to `infra/deck-out/<job_id>.zip` and reports a public download URL `https://deck.sastaspace.com/<job_id>.zip` (default in `workers/src/shared/env.ts:16`). But:
- `infra/docker-compose.yml` does NOT mount `./deck-out` into any nginx container. The landing nginx (`infra/landing/nginx.conf`) has no `/deck-out/` location and no second `server { server_name deck.sastaspace.com; }` block.
- `infra/cloudflared/` contains `add-stdb-ingress.sh` and `add-typewars-ingress.sh` but **no `add-deck-ingress.sh`**. There is no DNS record or tunnel ingress for `deck.sastaspace.com`.
- Spec § Open Question 7 was decided as "subdomain `deck.sastaspace.com`" but no plan picks up the implementation.

**Result:** The moment Phase 2 F4 lands and Phase 3 enables `WORKER_DECK_AGENT_ENABLED=true` in prod, `set_generate_done(job_id, "https://deck.sastaspace.com/<id>.zip")` fires successfully but the URL returns NXDOMAIN / 404. `/lab/deck` shows "ready" with a broken download link.

**Mitigation:**
1. Add a new nginx server block to `infra/docker-compose.yml` (or extend the existing `landing` container with a second `server` directive) that serves `infra/deck-out/` at port `127.0.0.1:3160` (the now-vacated deck-API port).
2. Add `infra/cloudflared/add-deck-ingress.sh` mirroring `add-typewars-ingress.sh`, hostname `deck.sastaspace.com`, service `http://localhost:3160`.
3. Run both before flipping `WORKER_DECK_AGENT_ENABLED=true`.
4. Add an E2E smoke: `curl -I https://deck.sastaspace.com/` returns a non-NXDOMAIN status.

**Owner/when:** Phase 3 prep. **Effort:** M (~3h: nginx config + ingress script + tunnel apply + verify).

---

#### N2 — CI workflow `e2e` job depends on `auth`/`moderator` jobs; Phase 4 deletes those
**Category:** CI breakage.
**Severity:** CRITICAL — `.github/workflows/deploy.yml:501` declares:
```
e2e:
  needs: [landing-deploy, notes, admin, moderator, auth]
  if: … && needs.moderator.result != 'failure' && needs.auth.result != 'failure'
```
Both `moderator` (line 394) and `auth` (line 443) jobs run from `infra/agents/moderator/` and `services/auth/`. **Phase 4 deletes both directories**, and the implicit `if: needs.changes.outputs.agents == 'true'` won't even fire — but the `e2e` job still has a hard `needs:` reference, which fails the workflow validation.

**Result:** Phase 4 cleanup commit fails CI before a single test runs.

**Mitigation:**
- Phase 4 plan task: edit `.github/workflows/deploy.yml`:
  - Remove `auth` and `moderator` jobs entirely.
  - Update `e2e: needs: [landing-deploy, notes, admin]`.
  - Update the smoke-test in `e2e` (lines 528-536) to drop `https://auth.sastaspace.com/healthz`.
  - Add a `workers` job (lint + vitest from `workers/`) so the new code is gated.
- Phase 3 cutover plan task (BEFORE Phase 4): edit the `agents:` change-detector glob (line 66) to also fire on `^workers/` changes.

**Owner/when:** Phase 3 (workers CI gate) + Phase 4 (job removals). **Effort:** M (~2h, careful YAML).

---

#### N3 — `NEXT_PUBLIC_USE_STDB_*` flags can't be passed at runtime; CI must build-then-deploy
**Category:** Build/deploy wiring.
**Severity:** CRITICAL — Apps are static-exported (`output: 'export'` in every `next.config.mjs`). Build runs on the GH Actions runner; output rsyncs into nginx volume. There is **no way** to flip `NEXT_PUBLIC_USE_STDB_AUTH` at deploy time — it's baked into the JS bundle at `pnpm build`.

The current CI workflow has env at the workflow level (`.github/workflows/deploy.yml:22-26`) but no `NEXT_PUBLIC_USE_STDB_*` flags. Phase 2 plans (F1 line 855-862, F4 line 831) propose adding playwright matrix entries that *assume* a build with the flag set, but **no plan modifies the build step to set the flag in the right env at the right time**.

**Result:** When Phase 2 ships, the apps build with `NEXT_PUBLIC_USE_STDB_*` undefined → "false" → legacy path. The "STDB-flagged" matrix entries in Playwright will silently exercise the legacy path against themselves, and the rewire is still de-facto unshipped at the end of Phase 2.

**Mitigation:**
- Phase 2-prep step (before any F* implementer is dispatched): patch `.github/workflows/deploy.yml` to add `NEXT_PUBLIC_USE_STDB_AUTH=false` (and the deck/admin equivalents) as defaults at the workflow `env:`, and add a second `*-stdb` job per app (`landing-stdb`, `notes-stdb`, `typewars-stdb`, `admin-stdb`) that builds with `=true` and uploads a separate artifact. Or: parameterise via a single `build_variant: legacy|stdb` matrix.
- Phase 3 cutover plan: replace the legacy artifact with the `=true` artifact in the rsync step, then remove the legacy job.

**Owner/when:** Phase 2-prep (CI matrix) + Phase 3 cutover. **Effort:** L (~1d: matrix per app with stable artifact names).

---

#### N4 — E2E `signIn` helpers hard-bind to `auth.sastaspace.com`
**Category:** Test infrastructure.
**Severity:** CRITICAL — `tests/e2e/helpers/auth.ts:37, 65, 80` POSTs to `${AUTH}/auth/request` and navigates to `${AUTH}/auth/verify`. Six specs depend on this path:
- `auth.spec.ts:7, 14, 22` (the FastAPI side door is the test subject)
- `admin.spec.ts:23, 36, 48` (uses `signIn`)
- `comments-signed-in.spec.ts:16, 36` (uses `signIn`)

Phase 3 stops `sastaspace-auth` container, but the helper still calls it. Tests will fail with HTTP errors.

**Mitigation:**
- Add a parallel helper `signInViaStdb(page, email)` that:
  1. POSTs `request_magic_link` reducer via STDB HTTP (with a test-mode flag the `request_magic_link` reducer reads from STDB env to skip Resend and write the token into a known `test_token` table — needs reducer addition) OR
  2. Uses the existing test-mode side door but against a NEW `request_magic_link_test` reducer that bypasses queueing and returns the token via a one-shot table.
- Easier: keep the FastAPI side door alive through Phase 3 just for tests (add a `test-only` env flag to `services/auth/` that strips production behaviour) — but that contradicts the spec's "zero Python files" goal.
- Cleanest: add a `pending_email` rolling test mode — a reducer `mint_test_token(email)` that returns the token directly when STDB is in dev/staging (gated by a build-time module config). Wire `tests/e2e/helpers/auth.ts` to call it.

**Owner/when:** Phase 2 prep (so F1 can integrate it) OR Phase 3 (cutover-time test rewrite). **Effort:** M (~4h reducer + helper + unit test).

---

#### N5 — Spec acceptance criterion "all E2E specs pass against rewired stack" requires an STDB-only `signIn` path that doesn't exist
**Category:** Acceptance gate testability.
**Severity:** CRITICAL — Spec line 404: "All E2E specs in `tests/e2e/` pass against the rewired stack." Without N4's resolution, this criterion is structurally impossible to verify because the helpers themselves require the FastAPI auth service to be reachable. The Phase 0 baseline already shows the suite is built around `signIn(page, email)` calling `auth.sastaspace.com`.

**Mitigation:** Same as N4 — add an STDB-native test-mode helper. Mark this in the Phase-3-prep checklist as a hard prerequisite.

**Owner/when:** Phase 2 prep. **Effort:** see N4.

---

### HIGH

#### N6 — `apps/admin/next.config.mjs` hard-codes `https://api.sastaspace.com` as default
**Category:** Default config drift after Phase 3.
**Severity:** HIGH — Line 8: `NEXT_PUBLIC_ADMIN_API_URL: process.env.NEXT_PUBLIC_ADMIN_API_URL ?? 'https://api.sastaspace.com'`. After Phase 3 drops the `api.sastaspace.com` cloudflared ingress, this default still ships in the bundle. Any panel that branches `if (!USE_STDB_ADMIN) fetch(ADMIN_API_URL+...)` will produce browser DNS errors visible in console.

**Mitigation:** Phase 3 plan: change the default to an empty string and have any code using it gate on truthiness. Or remove the env entry entirely once F3 has flipped to STDB.

**Owner/when:** Phase 3 cutover. **Effort:** S (~30min).

---

#### N7 — Apps that use `@sastaspace/stdb-bindings` don't list it as a dep
**Category:** Workspace dep hygiene.
**Severity:** HIGH — `apps/notes/package.json` does NOT list `@sastaspace/stdb-bindings` but `apps/notes/src/lib/{spacetime,comments,admin}.ts` `import("@sastaspace/stdb-bindings")` (dynamic). Same for `apps/landing/package.json` (uses tsconfig `paths` aliasing instead). Same risk for `apps/typewars/package.json` if F2 adds STDB-direct calls (it will — verify_token et al). `packages/auth-ui/package.json` will face the same when F1 makes the modal call reducers.

This works today only because pnpm hoists the dep through `apps/admin` (which DOES list it) and the workspace resolution finds the symlink. If admin's dep is ever pruned, every dynamic-import call site breaks at runtime.

**Mitigation:** Add `"@sastaspace/stdb-bindings": "workspace:*"` (and `@sastaspace/typewars-bindings` where used) to:
- `apps/notes/package.json`
- `apps/landing/package.json`
- `packages/auth-ui/package.json` (peerDep, for F1)
- `apps/typewars/package.json` (already has typewars-bindings — add stdb-bindings for verify_token)

**Owner/when:** Phase 2 prep (F1/F2/F4 should add their own; F3 already lists it). **Effort:** S (~15min).

---

#### N8 — `workers/Dockerfile` uses `--no-frozen-lockfile` and copies no monorepo lockfile
**Category:** Reproducibility / supply-chain.
**Severity:** HIGH — `workers/Dockerfile:9` says `pnpm install --no-frozen-lockfile` because the lockfile lives at the repo root, not under `workers/`. Phase 0 explicitly punted: "Phase 1 may revisit this if reproducible CI builds become a constraint." Phase 3 cutover ships this image to prod.

**Result:** Workers container can pull a different transitive dep version than what was tested. Reproducibility broken.

**Mitigation:**
- Change CI build context from `../workers` to repo root in compose (so the root lockfile is available).
- OR: change the build to use `pnpm deploy --filter @sastaspace/workers /tmp/workers-pruned` from the root, then build from the pruned dir.
- OR: pre-copy the root lockfile + workspace YAML before `COPY package.json` and use `pnpm install --frozen-lockfile` with `--filter`.

**Owner/when:** Phase 3 (before flipping any worker flag in prod). **Effort:** M (~3h, requires testing pnpm `deploy` flow).

---

#### N9 — `dockerode` and `systeminformation` in worker image not verified to install on Alpine
**Category:** Container image risk.
**Severity:** HIGH — `workers/package.json` lists `dockerode`, `systeminformation`, `jszip`. The Dockerfile uses `node:22-alpine`. Risk:
- `dockerode` — pure JS, just needs the docker socket. The Dockerfile already adds `docker-cli` in the runtime stage (line 16) so the `docker logs --follow` subprocess in `admin-collector.ts:301` will work. **Probably OK.**
- `systeminformation` — pure JS but uses many child_process calls (`free`, `lsb_release`, etc.). Alpine doesn't have GNU coreutils — busybox `free` may not give the JSON the lib expects, and it shells out to `/proc` directly for most metrics. **Likely degraded but functional.**
- `nvidia-smi` / `rocm-smi` — invoked from `admin-collector.ts:62-86`. The container is `alpine` base + `docker-cli` only. Neither GPU CLI is in the image. Without them in the image, `readGpu()` always returns `null`, and the `system_metrics.gpu_*` columns are always null in prod.

**Mitigation:**
- Add a Phase 0/1 verification step: `docker compose run --rm workers node -e "console.log(require('systeminformation').currentLoad())"` in CI as part of the workers image build.
- Decide GPU strategy: either (a) install nvidia-smi shim in the image (`apk add nvidia-smi`? not available — usually the container needs the host's drivers passed through), or (b) accept null GPU stats from inside the worker and add a separate host-side collector. Per the spec's network_mode: host (compose line 285) the worker DOES see the host's `/proc`, so GPU CLIs would work IF installed. Add `nvidia-smi` package or copy the binary.

**Owner/when:** Phase 3 prep (must work when admin-collector flips on in prod). **Effort:** M (~3h: image rebuild + smoke test).

---

#### N10 — Bindings package uses `main: src/index.ts` not built JS; production bundlers may transpile differently
**Category:** Build correctness.
**Severity:** HIGH — `packages/stdb-bindings/package.json:8-11`: `"main": "./src/index.ts"`. Re-exports from `./generated/index.ts`. This works because every consuming app's bundler (Next/Webpack) transpiles workspace packages.

But `apps/landing/next.config.mjs` only `transpilePackages: ['@sastaspace/design-tokens']` — NOT `@sastaspace/stdb-bindings`. Same for notes and typewars. This currently works because landing uses tsconfig `paths` aliasing (the bundler treats it as a source file). Notes uses dynamic import which Next.js bundles at build time. **It's fragile and depends on bundler behavior; future Next.js or Turbopack version may stop handling it.**

**Mitigation:**
- Either: build `stdb-bindings` to JS (add `tsc` script + `dist/`), update `package.json` `main`/`types`/`exports` to point at dist.
- Or: add `@sastaspace/stdb-bindings` to `transpilePackages` in every app's next.config.mjs.

**Owner/when:** Phase 4 (cleanup). **Effort:** M (~2h).

---

#### N11 — `auth.sastaspace.com` Cloudflare 410-Gone deprecation has no plan
**Category:** Spec gap.
**Severity:** HIGH — Spec § Open Question 1 default: "leave Cloudflare ingress in place for one release pointing to a 410 Gone static page." Phase 4 cleanup line 3 says "remove the ingress after 410-page period elapses." But:
- No nginx config exists for the 410 page.
- No script removes the ingress (mirror of `add-typewars-ingress.sh`).
- No definition of "one release" period.

**Mitigation:**
- Phase 3 task: write `infra/landing/auth-410.conf` — nginx server block returning `410 Gone` with `Retry-After: 0`.
- Phase 4 task: write `infra/cloudflared/remove-auth-ingress.sh`.
- Decide and document the "one release" interval (e.g. 7 days post-cutover).

**Owner/when:** Phase 3 + Phase 4. **Effort:** S (~1h).

---

#### N12 — F2 plan-drafter's coordination with F1 is documented but not enforced
**Category:** Process.
**Severity:** HIGH (re-stated from K8 because it's structural). The master plan dispatches F1-F4 in parallel. Without a code-level dependency (e.g. F1 lands a typed `RequestStdbAuth` shape exported from `auth-ui`, and F2's type-check fails until that shape is present), F2 can ship a build that targets a SignInModal version that doesn't yet have the new prop.

**Mitigation:** Master plan amendment for Phase 2: dispatch F1 first (serial), wait for merge, then dispatch F2/F3/F4 in parallel (none depend on F1's specific changes after the modal lands).

**Owner/when:** Phase 2-prep amendment. **Effort:** S (one-line plan edit).

---

#### N13 — `STDB_TOKEN=phase0-placeholder-no-agents-enabled` is the default in compose
**Category:** Footgun.
**Severity:** HIGH — `infra/docker-compose.yml:296` explicitly sets the workers' STDB_TOKEN to a placeholder that's not an owner JWT. When Phase 3 flips any `WORKER_*_ENABLED=true`, the worker will try to call `assert_owner`-gated reducers and **every reducer call will fail with "not authorized"** until the owner provides their real JWT in `../workers/.env`.

The risk is silent: the worker boots, subscribes, and sends reducer calls that all error. The pending_email rows pile up; system_metrics rows never insert.

**Mitigation:**
- Phase 3 cutover plan task 0: provision `workers/.env` on the prod host with the real `SPACETIME_TOKEN` (use the same one CI uses, see `.github/workflows/deploy.yml:133`).
- Add a startup health check to the workers process: on boot, call a no-op owner-only reducer (e.g. a new `noop_owner_check()`) and exit non-zero if it fails, so docker restart-loops the container with a clear error.

**Owner/when:** Phase 3 prep. **Effort:** S for env wiring; M for the health-check reducer (~2h).

---

### MEDIUM

#### N14 — `apps/admin` `data.ts` mock vs `usePoll` legacy live in untracked changes
**Category:** Tech debt.
**Severity:** MEDIUM — Phase 2 F3 plan says delete `apps/admin/src/lib/data.ts` (mock) once panels are rewired. The user's in-flight admin work has untracked `apps/admin/src/hooks/` changes. The merge order matters — F3 needs the user's WIP to land first OR F3 must explicitly handle both states.

**Mitigation:** Add a "merge user's admin WIP first" gate before F3 dispatch.

**Owner/when:** Phase 2 prep. **Effort:** S.

---

#### N15 — Spec calls for `STRUCTURE.md` but it doesn't exist
**Category:** Acceptance criterion.
**Severity:** MEDIUM — Spec line 406, Phase 4 plan line 8.
**Mitigation:** Phase 4 task exists. Just verify it lands.

**Owner/when:** Phase 4. **Effort:** S.

---

#### N16 — `set_comment_status` (legacy) and `set_comment_status_with_reason` (W4) both owner-only — moderator worker uses the new one, admin UI uses the old one
**Category:** Reducer surface ambiguity.
**Severity:** MEDIUM — `modules/sastaspace/src/lib.rs:194` (legacy) and `:383` (with reason). Both `assert_owner`. Admin UI's manual moderation uses `set_comment_status` (no reason recorded → no `moderation_event` row). Moderator-agent uses the with-reason variant. Result: `moderation_event` table has gaps for human-moderated comments.

**Mitigation:** F3 plan should use the with-reason variant, passing `reason="manual-override"` (after adding `manual-override` to the `MODERATION_REASONS` allow-list at `lib.rs:371`). One reducer survives long-term; legacy is a manual-override convenience.

**Owner/when:** Phase 2 F3 implementation OR Phase 3 follow-up. **Effort:** S.

---

#### N17 — `ALLOWED_CONTAINERS` in `lib.rs:635-650` includes the soon-deleted Python container names
**Category:** Cleanup-time gotcha.
**Severity:** MEDIUM — Lines 647-650 list `sastaspace-auth`, `sastaspace-admin-api`, `sastaspace-deck`, `sastaspace-moderator`. The comment says "Removed in Phase 4 cleanup."

**Mitigation:** Phase 4 task list includes "remove legacy entries from `ALLOWED_CONTAINERS`." Plus the matching `admin-collector.ts:33-37` ALLOWED_CONTAINERS list — must be edited in lockstep.

**Owner/when:** Phase 4. **Effort:** S.

---

#### N18 — `admin-collector.ts` still does `docker logs --follow` shell-out instead of dockerode streams
**Category:** Resilience.
**Severity:** MEDIUM — `admin-collector.ts:301-307` uses `spawn("docker", ["logs", ...])`. This depends on the docker CLI being in the image (it is — Dockerfile line 16) and on the docker socket being mounted (it is — compose line 287). But it's two failure modes (CLI missing, socket missing) instead of one (dockerode-only). Dockerode supports `container.logs({follow: true, stdout: true, stderr: true})` returning a stream.

**Mitigation:** Convert to dockerode. Lower risk surface, faster startup, simpler tests.

**Owner/when:** Post-rewire follow-up. **Effort:** M (~3h).

---

#### N19 — No reducer test for `verify_token` token-already-used path
**Category:** Test gap.
**Severity:** MEDIUM — `lib.rs:545-547` short-circuits on `tok.used_at.is_some()`. Coverage for this path likely exists in unit tests but should be confirmed via `cargo llvm-cov` summary.

**Mitigation:** Add a test if absent. Phase 2 F1 implementation will exercise it via the "used token" E2E spec path (F1 plan line 327 mentions it).

**Owner/when:** Phase 2 F1. **Effort:** S.

---

#### N20 — `oneShotAgent` and `ollamaProvider` both export an `OllamaProvider` instance — singleton vs per-instance
**Category:** Code cleanliness.
**Severity:** MEDIUM — `workers/src/shared/mastra.ts:21-36` exports both `ollama` (eagerly created at import) AND a memoized `ollamaProvider()` factory. Both create the same singleton; no caller uses both. Pick one.

**Mitigation:** Inline cleanup post-merge.

**Owner/when:** Phase 4. **Effort:** S.

---

#### N21 — `STDB_TOKEN`-required workers can't boot for tests without a real token; vitest spec coverage limited
**Category:** Test gap.
**Severity:** MEDIUM — `workers/src/shared/env.ts:6` requires non-empty STDB_TOKEN. Vitest specs (`*.test.ts`) need to mock `process.env.STDB_TOKEN` before importing. `index.ts` short-circuits on no agents enabled but `env.ts` parses immediately. Risk: tests that import a worker module always need an env stub.

**Mitigation:** Make STDB_TOKEN optional in `env.ts` and assert presence in `index.ts:32` before `await connect(...)`.

**Owner/when:** Phase 2/3. **Effort:** S.

---

#### N22 — Spec acceptance criterion "no `api.sastaspace.com` route" — no automated check
**Category:** Acceptance verification.
**Severity:** MEDIUM — Spec line 405. There's no script that queries the Cloudflare tunnel config to verify the route is gone. Easy to forget at cutover.

**Mitigation:** Phase 3 cutover plan includes a verification command (`curl -sS "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT/cfd_tunnel/$TUNNEL/configurations" | jq '.result.config.ingress[].hostname' | grep api.sastaspace.com` should be empty).

**Owner/when:** Phase 3. **Effort:** S.

---

### LOW

#### N23 — Root-level `deck-step2-expanded.png`, `deck-step3-results.png`, `idea.md` still in tree
**Category:** Repo hygiene.
**Severity:** LOW — Tracked in structure audit L1. Phase 4 cleanup task.
**Effort:** S.

#### N24 — `.playwright-mcp/` not in gitignore
**Category:** Repo hygiene.
**Severity:** LOW — Tracked in structure audit L1. Phase 4 cleanup task.
**Effort:** S.

#### N25 — `tests/e2e/playwright.config.ts` has `fullyParallel: false, workers: 1` — slow at scale
**Category:** Performance.
**Severity:** LOW — When the matrix doubles (legacy + STDB), serial execution will hurt. Comment says "serialise to keep stdb state predictable."
**Mitigation:** Long-term, partition specs by app and let each app run parallel with isolated user emails.
**Effort:** M.

#### N26 — `pnpm audit --prod --audit-level moderate` is run only for landing/notes apps, not workers
**Category:** Security hygiene.
**Severity:** LOW — `.github/workflows/deploy.yml:179, 257`. Workers job (when added per N2) should include the same audit.
**Effort:** S.

#### N27 — `services/auth/Dockerfile` still has E2E_TEST_SECRET wiring; once auth is killed, that test side door dies
**Category:** Test path.
**Severity:** LOW — Already covered by N4. Listed separately for completeness.
**Effort:** Subsumed into N4.

---

## Phase-3-prep checklist (HARD prerequisites before drafting the cutover plan)

These must complete BEFORE the Phase 3 cutover plan-drafter is dispatched. Items in **bold** unblock other items.

### A. SDK errata applied to spec & Phase 2 plans (resolves K1-K6)
- [ ] **Add an "SDK 2.1 errata" appendix to the spec** (`docs/superpowers/specs/2026-04-26-spacetimedb-native-design.md`) listing:
  - Reducer call shape: `await conn.reducers.<name>({...})` returns `Promise<void>` resolved on send
  - Reducer outcome: observe via subscription event (`conn.db.<table>.onUpdate`) or `conn.onReducer<Name>`
  - `conn.db.<name>` is camelCased even though Rust source is snake_case
  - Timestamps: `row.<x>.microsSinceUnixEpoch` getter, no method
  - Subscription unsub: `removeOnInsert(cb)` symmetric remover; `onInsert` returns void
  - Builder: `.withDatabaseName(...)` (not `withModuleName`)
- [ ] Patch F1 plan code blocks (lines 120, 138-148, 169-179) to use the corrected shapes
- [ ] Patch F2 plan code block (line 212) to use the corrected shape
- [ ] Patch F4 plan code (lines 226, 261, 324, 351) for `microsSinceUnixEpoch` getter + `removeOnInsert`

### B. Reducer-side gaps closed
- [ ] **N4 / N5: Add an STDB-native test-mode helper** — either a `mint_test_token(email)` reducer gated by a module env config, or a `request_magic_link_test` variant the E2E helper can call. Without this, the rewire's E2E acceptance criterion is structurally unverifiable.
- [ ] N16: Add `manual-override` to `MODERATION_REASONS` in `modules/sastaspace/src/lib.rs:371` and have F3 use `set_comment_status_with_reason("manual-override")` for human moderation.
- [ ] (Optional) N13: Add a `noop_owner_check` reducer for the workers boot-time health check.

### C. Infrastructure landed (resolves N1, N6, N11)
- [ ] **N1: nginx server for `infra/deck-out/`** — extend compose with a `deck` static container (or add a second server block to landing nginx) listening on `127.0.0.1:3160`.
- [ ] **N1: `infra/cloudflared/add-deck-ingress.sh`** — mirror `add-typewars-ingress.sh`.
- [ ] **N1: Run both** on prod and verify `curl -I https://deck.sastaspace.com/` returns 200 (with empty index) or a directory listing.
- [ ] N11: `infra/landing/auth-410.conf` for the `auth.sastaspace.com` deprecation page.
- [ ] N11: `infra/cloudflared/remove-auth-ingress.sh` for the eventual ingress removal.
- [ ] N6: Phase 3 plan removes `NEXT_PUBLIC_ADMIN_API_URL` default from `apps/admin/next.config.mjs`.

### D. CI wiring (resolves N2, N3, N8, N26)
- [ ] **N3: `.github/workflows/deploy.yml` matrix per app** — add `landing-stdb`, `notes-stdb`, `typewars-stdb`, `admin-stdb` jobs that build with `NEXT_PUBLIC_USE_STDB_*=true`. Either keep both artifacts and wire which one rsyncs based on a flag, OR replace the legacy artifact at cutover time.
- [ ] **N2: Add a `workers` job** — lint + vitest from `workers/`. Update the `agents:` change-detector regex to also fire on `^workers/`.
- [ ] **N8: Workers Dockerfile rebuild** — use `pnpm deploy --filter` from repo root OR copy lockfile + workspace YAML before install, and switch to `--frozen-lockfile`.
- [ ] N26: Add `pnpm audit --prod --audit-level moderate` to the workers job.
- [ ] (Phase 4): Remove `auth` and `moderator` jobs and update the `e2e: needs:` graph.

### E. Workspace dependency hygiene (resolves N7)
- [ ] Add `"@sastaspace/stdb-bindings": "workspace:*"` to `apps/notes/package.json`, `apps/landing/package.json`, `apps/typewars/package.json` (also `typewars-bindings`), and as a peerDep of `packages/auth-ui/package.json`.
- [ ] Verify `pnpm install --frozen-lockfile` still passes after lockfile regeneration.

### F. Test infrastructure (resolves N4, N5, K14)
- [ ] **Implement `signInViaStdb(page, email)` helper in `tests/e2e/helpers/auth.ts`** keyed off `E2E_AUTH_BACKEND=stdb|fastapi`.
- [ ] Consolidate the playwright matrix decision: a single `playwright.config.ts` with `projects: [legacy, stdb]` reading `E2E_AUTH_BACKEND`, OR two CI runs each with a single project. Pick before F1 lands.
- [ ] Run a full E2E pass against the **dev compose with all `WORKER_*_ENABLED=true`** before drafting Phase 3.

### G. Documentation
- [ ] N15: Stub `STRUCTURE.md` at repo root (Phase 4 fills it in).
- [ ] Add the SDK errata block to spec (see A above).
- [ ] Update `master.md` Phase 2 dispatch order: F1 serial → F2/F3/F4 parallel (N12).

### H. Coordination gates
- [ ] N20 / user WIP: `git status` clean inside `apps/admin/`, `tests/e2e/`, `services/admin-api/`, `services/deck/` before Phase 3 starts.
- [ ] Verify `claim_progress_self` (commit `947c8f8a`) is in the bindings + still typechecks against typewars module after any Phase 2 typewars-side changes.

---

## Open questions for the owner

1. **N4/N5 strategy:** are you OK adding a `test_token` table + `mint_test_token` reducer (lives in module forever, gated by env) OR do you prefer to keep the FastAPI auth service alive in test-mode-only through Phase 3 and delete it in Phase 4? The former is cleaner; the latter is faster.
2. **N3 CI strategy:** do you want a single CI build with `NEXT_PUBLIC_USE_STDB_*=true` baked-in (one-shot cutover, no fallback), or a side-by-side matrix that produces both artifacts per push? Side-by-side is safer but doubles build minutes.
3. **N1 deck-out hosting:** spec § Open Q7 picked subdomain. Confirm `deck.sastaspace.com` (new tunnel ingress) over `sastaspace.com/deck-out/` (path on existing landing). Subdomain is cleaner; path is one fewer cloudflared write.
4. **N12 Phase 2 dispatch:** OK to amend master plan to F1 serial → rest parallel? Adds ~half a day calendar but eliminates the modal-shape race.
5. **N9 GPU CLI in workers image:** OK to add `nvidia-smi` (or rocm-smi) to the workers Dockerfile, or accept null GPU stats from inside the worker process?
6. **N11 deprecation interval:** how long should `auth.sastaspace.com` 410 Gone serve before the ingress is removed? (Default 7 days from cutover.)

---

## Appendix A — files referenced

- `docs/superpowers/specs/2026-04-26-spacetimedb-native-design.md` — primary spec
- `docs/superpowers/plans/2026-04-26-stdb-native-master.md` — master plan
- `docs/superpowers/plans/2026-04-26-stdb-native-phase2-{f1,f2,f3,f4}-*.md` — Phase 2 plans (drafted, not implemented)
- `docs/audits/2026-04-26-phase0-e2e-baseline.md` — Phase 0 baseline
- `docs/audits/2026-04-26-structure-audit.md` — prior structure audit
- `infra/docker-compose.yml` — full stack composition
- `infra/cloudflared/add-{stdb,typewars}-ingress.sh` — existing ingress scripts (no `add-deck-ingress.sh`)
- `.github/workflows/deploy.yml` — CI workflow
- `modules/sastaspace/src/lib.rs` — Rust module (2178 lines after Phase 1)
- `modules/typewars/src/player.rs` — `claim_progress_self` (commit `947c8f8a`)
- `packages/stdb-bindings/src/generated/index.ts` — regenerated bindings (commit `4b55496a`)
- `workers/src/shared/{stdb,mastra,env}.ts` — worker shared code
- `workers/src/agents/{auth-mailer,admin-collector,deck-agent,moderator-agent}.ts`
- `tests/e2e/helpers/{auth,urls,stdb}.ts` — E2E helpers
- `tests/e2e/specs/*.spec.ts` — E2E specs (13 total, 6 use `signIn`)
- `apps/admin/{next.config.mjs,src/hooks/useStdb.ts}` — admin app
- All `apps/*/package.json` and `packages/*/package.json` — workspace dep audit
