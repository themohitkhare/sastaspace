# Completeness Audit — 2026-04-26

**Auditor:** completeness
**Methodology:** Read the Phase 3 handoff doc and cutover plan for context, then ran `rg` across all non-generated, non-lock-file source to enumerate TODO/FIXME/HACK markers, `test.skip` occurrences, `#[allow(dead_code)]` and `#[ignore]` in Rust, phase-marker strings in source files, empty/silent `catch {}` blocks, half-deployed feature flags, PHASE 4 DELETE markers, and dual-mode code paths. Inspected `infra/docker-compose.yml` for flag state, `.github/workflows/deploy.yml` for legacy build variants, and all README.md files for documentation gaps.

**Commands run:**

```
rg -n 'TODO|FIXME|XXX|HACK|todo!|unimplemented!|test\.skip|it\.skip|xit\(|#\[ignore\]' --type rust --type ts --type tsx --type js --type yaml -g '!node_modules' -g '!target' -g '!.next' -g '!dist' -g '!.venv' -g '!*.lock' -g '!*.md'

rg -n '#\[allow\(dead_code\)\]' --type rust -g '!target'
rg -n 'WORKER_\w+_ENABLED\s*=\s*false|NEXT_PUBLIC_USE_STDB' across infra/ and .github/
grep -n 'SKIP_PENDING_BOOTSTRAP_FIX|Phase 3 prep|Phase 4|post-cutover|PHASE 4 CLEANUP' in all non-markdown source files
find apps/ modules/ workers/ packages/ -maxdepth 2 -name README.md
```

**Overall grade:** 7/10
**Headline number:** 4 TODO/FIXME markers in source (all Phase 4 modularization); 7 active `test.skip` call-sites across 3 specs (2 env-gated runtime skips + 2 structural `SKIP_PENDING_BOOTSTRAP_FIX = true` blocks); 1 `#[allow(dead_code)]` in Rust; 0 `#[ignore]`d tests; 0 `unimplemented!()` or `todo!()` macros; 0 empty silent catch blocks.

---

> **User WIP — not in scope:** `tests/e2e/specs/typewars-*.spec.ts`, `tests/e2e/helpers/typewars.ts`, `services/admin-api/`, `services/deck/`, `.playwright-mcp/`, `deck-step*.png`, `tests/e2e/package.json` modifications, `docs/audits/2026-04-26-structure-audit.md`. These are the user's own in-flight work and are excluded from grading.

---

## Critical: half-finished features that block "feature complete" status

### C1 — `SKIP_PENDING_BOOTSTRAP_FIX = true` hard-codes two entire test suites to permanent skip

**Files:**
- `tests/e2e/specs/admin-panels.spec.ts:36` — `const SKIP_PENDING_BOOTSTRAP_FIX = true;` skips the entire `admin panels — STDB live updates` describe block at `line 68-70`.
- `tests/e2e/specs/moderator.spec.ts:47` — same constant, skips both moderator E2E test cases at `lines 58-61`.

**Symptom:** Both files are committed, non-WIP E2E specs that are permanently skipped regardless of whether `E2E_OWNER_STDB_TOKEN` or `E2E_MODERATOR_ENABLED` is set. The constant is a compile-time true, not an env var. The skip message reads: _"owner-as-user bootstrap pending — Phase 4 follow-up to register owner via dedicated reducer"_.

**Root cause:** `submit_user_comment` requires `ctx.sender()` to be a registered `User` row. The owner identity's HTTP API encoding for `Identity` (u256) is undocumented; attempts with hex/0x-prefix-hex/decimal string all fail. A dedicated `register_owner_e2e` reducer (no args, uses `ctx.sender()` directly) or CLI-based bootstrapping would unblock both specs.

**Impact:** The admin-panels real-time STDB path and the moderator-agent E2E both have zero automated test coverage running in CI, even post-cutover. These cover the two most operationally silent failure modes (comments stuck pending, admin UI showing stale data).

**Fix:** Add a `register_owner_e2e` reducer to `modules/sastaspace/src/lib.rs` (owner-only, no args, calls `ctx.db.user().insert(...)` with `ctx.sender()`), wire the E2E bootstrap, set `SKIP_PENDING_BOOTSTRAP_FIX = false`.

---

### C2 — `claim_progress_self` (new Phase 2 F2 reducer) has no unit tests

**File:** `modules/typewars/src/player.rs:177`

`claim_progress_self` is the STDB-native replacement path for `claim_progress`: the caller's own identity (`ctx.sender()`) is the `new_identity`, which means the malicious-client threat model differs from the owner-gated original. The test suite at `player.rs:206` tests `plan_claim` (the shared pure logic) exhaustively, but has **no test that exercises `claim_progress_self` directly**, meaning the new "self-service" path (including the `is_guest_already_verified` guard and the reducer's integration with `ctx.sender()`) is untested at the Rust unit-test layer.

The typewars-auth-stdb E2E spec (`tests/e2e/specs/typewars-auth-stdb.spec.ts`) provides indirect coverage via the browser, but it only runs when `E2E_TYPEWARS_USE_STDB_AUTH=true` (not default CI).

---

## High: meaningful TODOs / FIXMEs that should be tracked

### H1 — Admin CSP still allows `api.sastaspace.com` post-cutover

**File:** `infra/admin/security_headers.conf:16`

The `connect-src` directive includes `https://api.sastaspace.com`. Phase 3 cutover is supposed to retire this endpoint (Phase 3 plan N6 drops it from `next.config.mjs`). The nginx CSP is a separate surface that was not updated. Post-cutover, `api.sastaspace.com` no longer exists; browsers will correctly refuse those calls, but the CSP is misleading and opens a future attack surface if the hostname is ever reclaimed.

```
connect-src 'self' ... https://api.sastaspace.com https://stdb.sastaspace.com wss://stdb.sastaspace.com;
```

**Fix:** Remove `https://api.sastaspace.com` from `connect-src` in `infra/admin/security_headers.conf`. Phase 4 cleanup is the appropriate time.

---

### H2 — `modules/sastaspace` `project` and `Presence` tables are dead on the frontend

**File:** `apps/landing/src/lib/projects.ts:8`

```ts
// The `project` table + reducers in modules/sastaspace stay
// for now — Phase 4 cleanup will drop them.
```

The `project` table (`upsert_project`, `delete_project` reducers) and `Presence` table (`heartbeat` reducer subscription) are defined in `modules/sastaspace/src/lib.rs` but are **no longer written to or subscribed from any frontend code**. `apps/landing/src/lib/spacetime.ts` still calls `subscribePresence` and `heartbeat`, so the Presence table has active reads. The `project` table has zero frontend subscribers or writers; `upsert_project` and `delete_project` reducers are keeper code scheduled for Phase 4 deletion. These inflate WASM bundle size and test surface for no current value.

**Impact:** Low security risk, moderate WASM bloat, potential confusion for new contributors reading the schema.

---

### H3 — Dual-mode legacy-vs-stdb CI still builds both variants for typewars and admin (deploy is stdb only)

**File:** `.github/workflows/deploy.yml:366,445`

Both the `typewars` and `admin` CI jobs have `build_variant: [legacy, stdb]` matrices. The comments confirm PHASE 3 CUTOVER has been applied — only `matrix.build_variant == 'stdb'` deploys. But the `legacy` variant **still builds, typechecks, and uploads a rollback artifact every CI run**.

This is intentional (rollback target per Phase 3 plan), but it doubles CI time for these jobs and the legacy artifact has a 7-day TTL per `retention-days: 7`. No automation removes it after the 48h stabilisation window.

**Notes-specific:** `notes` job at line 290 also has the same `[legacy, stdb]` matrix with the same "stdb deploys, legacy is rollback" comment.

**Fix (Phase 4):** Drop the `legacy` matrix entry from all four app CI jobs. Currently marked in comments as `# Phase 4 deletes those Python jobs`.

---

### H4 — Docker `workers` service has no compose `healthcheck`

**File:** `infra/docker-compose.yml` — `workers:` service at line 356

The `workers` service is the only runtime service without a `healthcheck`. All other services (spacetime, landing, notes, typewars, admin, localai, deck-static, auth-410, auth, deck, admin-api, moderator) have health checks. Audit finding N13 was partially addressed (the `noop_owner_check` call at boot in `workers/src/index.ts:54` exits non-zero on token failure), but there is no `healthcheck:` block in compose, so `docker compose ps` always shows `workers` as "running" even if it crashed after boot.

**Fix:** Add a `healthcheck` that checks `docker inspect sastaspace-workers --format '{{.State.Running}}'` or uses a sentinel file the worker writes on successful startup.

---

### H5 — `admin-collector` still shell-spawns `docker logs` instead of using `dockerode` streams

**Files:**
- `workers/src/agents/admin-collector.ts:300-335` — `spawn("docker", ["logs", "--follow", ...])` shell-out
- `workers/Dockerfile:41` — comment: `# (audit N18 tracks moving to dockerode streams)`
- `.github/workflows/deploy.yml:198,635` — `# ... shipped a patched release. Tracked in audit N18 follow-up`

`dockerode` is already a dep (in `pnpm-lock.yaml:299`) and `Docker from "dockerode"` is already imported in `admin-collector.ts:2`. The container listing/inspection uses the Dockerode SDK correctly. Only the log-streaming path still uses a `docker` CLI subprocess. N18 is tracked but unresolved.

**Risk:** The shell-out path has a race on `docker` binary availability inside the Alpine container at runtime and adds process-leak risk if the subprocess is not reaped on `stop()`. The `kill()` path at line 351 handles cleanup but subprocess zombie risk remains.

---

## Medium: stylistic loose ends

### M1 — Phase 4 modularization TODOs in deck source (3 files)

**Files:**
- `apps/landing/src/app/lab/deck/useDeckStdb.ts:12` — `// TODO(Phase 4 modularization): once the legacy HTTP path is removed, this`
- `apps/landing/src/app/lab/deck/deckStdbFlows.ts:15` — `// TODO(Phase 4 modularization): once the legacy HTTP path is removed, fold`
- `apps/landing/src/app/lab/deck/Deck.tsx:7` — `// TODO(Phase 4 modularization): once cutover is stable,`

All three are well-documented inline; they explain that once `services/deck/` is deleted in Phase 4, the dual-path `USE_STDB` flag and conditional logic can be collapsed to STDB-only. These are correctly classified as Phase 4 work and are non-blocking.

---

### M2 — `auth.spec.ts` legacy auth flow is permanently dormant post-cutover

**File:** `tests/e2e/specs/auth.spec.ts:10-12`

```ts
test.skip(
  !LEGACY_ONLY,
  "/auth/request and /auth/verify on auth.sastaspace.com are 410 post-cutover; legacy-only tests are obsolete in stdb backend mode",
);
```

Post-cutover with `E2E_AUTH_BACKEND=stdb` (the new default), `auth.spec.ts` skips itself entirely. The spec is now a dead file in the committed tree since the STDB path has its own spec (`notes-auth-stdb.spec.ts`). It should be removed in Phase 4 cleanup.

---

### M3 — `deck.spec.ts` skip when `AUTH_BACKEND=stdb` and `FLOW=legacy`

**File:** `tests/e2e/specs/deck.spec.ts:22-25`

```ts
test.skip(
  AUTH_BACKEND === "stdb" && FLOW === "legacy",
  "/lab/deck legacy flow depends on services/deck FastAPI which Phase 4 deletes; ...",
);
```

This is a correct guard, but the `legacy` FLOW value will become permanently unavailable once Phase 4 removes `services/deck/`. The spec should transition to only the `stdb` flow path after Phase 4.

---

### M4 — Silent `catch {}` blocks (well-documented intent, but worth noting)

**Not empty — these are intentional fall-throughs with comments, but recorded for completeness:**

- `workers/src/agents/admin-collector.ts:79` — `} catch { /* fall through to rocm */}` — tries nvidia-smi then rocm-smi; first failure expected.
- `workers/src/agents/admin-collector.ts:114` — `} catch { return null; }` — rocm-smi absent → null GPU stats; documented behaviour.
- `workers/src/agents/admin-collector.ts:265` — `} catch { /* leave at 0 */ }` — stats parse failure → zeroed metrics.
- `apps/notes/src/lib/admin.ts:46` — `} catch { return; }` — bindings import failure exits silently; subscription just doesn't fire.
- `apps/notes/src/lib/stdbAuth.ts:138,163` — both are `conn.disconnect()` cleanup in `finally` blocks where disconnect failure is expected and irrelevant.
- `apps/notes/src/lib/comments.ts:120` — stdb bindings import failure re-throws as a proper Error (not actually silent).

None are truly silent; all have documented intent. The `admin.ts:46` case (silently returning from a subscription when bindings fail) is the weakest: it leaves the admin panel showing stale data with no log output. Low risk post-Phase 3 (bindings always load), but worth adding a `console.warn` for dev diagnostics.

---

### M5 — `#[allow(dead_code)]` on `LEGION_NAMES` and `LEGION_COUNT` in typewars

**File:** `modules/typewars/src/legion.rs:1`

```rust
#[allow(dead_code)]
pub const LEGION_NAMES: [&str; 5] = ["Ashborn", "The Codex", "Wardens", "Surge", "Solari"];
pub const LEGION_COUNT: u8 = 5;
```

`LEGION_NAMES` is suppressed because it's consumed by the frontend bindings package, not by Rust code. `LEGION_COUNT` is not suppressed but also not used in Rust (also frontend-bound). This is acceptable for a shared-constant pattern but the `#[allow]` should be narrowed to the specific item or removed if STDB's codegen allows export without Rust-side consumption.

---

### M6 — `mark_email_sent` and `mark_email_failed` have no Rust unit tests

**File:** `modules/sastaspace/src/lib.rs:551,571`

These two reducers (called by the `auth-mailer` worker to update `pending_email` row status) have no `#[test]` coverage in `lib.rs`. The `auth-mailer.test.ts` vitest spec covers the worker side (5 test cases), but the Rust reducer path (validation logic, error message on missing row, etc.) is untested at the module level. The `pending_email_struct_round_trips` test at line 2715 only tests serialisation, not the state-machine transitions.

---

## Low: noise (probably remove or accept)

### L1 — `modules/typewars/src/lib.rs` has no tests

**File:** `modules/typewars/src/lib.rs` — 41 lines, contains only `init`, `client_connected`, `client_disconnected` lifecycle reducers.

These are thin orchestration shims that call into other modules. Not worth unit testing at this layer; the sub-module functions they call are all tested. Accept.

---

### L2 — Legacy artifact retention creates CI storage accumulation

The `retention-days: 7` on `*-out-legacy` artifacts (landing/notes/typewars/admin) means each push creates a dead build artifact that sits for a week. After Phase 4 drops the matrix, this resolves itself. Accept until Phase 4.

---

### L3 — README gap: no README for `apps/typewars`, `apps/admin`, `apps/notes`, `workers`, `packages/auth-ui`, `packages/design-tokens`, `packages/typewars-bindings`, `modules/typewars`, `modules/sastaspace`

Nine directories that are top-level or first-level packages have no `README.md`. The repo has a root `README.md` and `CLAUDE.md` provides structural context. The Phase 4 plan explicitly calls for writing `STRUCTURE.md` after cleanup. Accept the gap until Phase 4; no Phase 4 executor should forget this.

---

### L4 — `typewars-auth-stdb.spec.ts` note about broader coverage

**File:** `tests/e2e/specs/typewars-auth-stdb.spec.ts:5-6` — comment says "the broader legacy + matrix coverage lives in the user's untracked typewars-auth.spec.ts". This is user WIP (not graded here), but once that spec is committed, the note should be updated or removed.

---

## Phase 4 backlog (already-known items, cross-referenced)

These are tracked and intentionally deferred. Listed here so the Phase 4 executor has a single reference:

| # | Item | Location |
|---|------|----------|
| P4-1 | `git rm -r services/auth/ services/admin-api/ services/deck/ infra/agents/moderator/` | handoff doc §"What comes after Phase 3" |
| P4-2 | Remove 4 Python service blocks from `infra/docker-compose.yml` | compose lines 230, 265, 290, 320 + `# Phase 4 deletes` comments |
| P4-3 | Run `cloudflared/remove-auth-ingress.sh` (≥7 days post-cutover) | `infra/docker-compose.yml:165`, `infra/landing/auth-410.conf` |
| P4-4 | Delete `apps/typewars/src/app/auth/callback/page.tsx` (PHASE 4 DELETE) | `apps/typewars/src/app/auth/callback/page.tsx:2` |
| P4-5 | Delete `apps/notes/src/app/auth/callback/page.tsx` (PHASE 4 DELETE) | `apps/notes/src/app/auth/callback/page.tsx:1` |
| P4-6 | Drop `legacy` build_variant matrix from all 4 CI app jobs | `.github/workflows/deploy.yml:167,290,366,445` |
| P4-7 | Drop `project` table + `upsert_project` / `delete_project` reducers | `modules/sastaspace/src/lib.rs:155-191`, `apps/landing/src/lib/projects.ts:8` |
| P4-8 | Remove `api.sastaspace.com` from admin CSP `connect-src` | `infra/admin/security_headers.conf:16` |
| P4-9 | Collapse deck dual-mode (`USE_STDB` flag) in 3 landing files | `apps/landing/src/app/lab/deck/{useDeckStdb,deckStdbFlows,Deck}.tsx` |
| P4-10 | Delete `tests/e2e/specs/auth.spec.ts` (legacy auth flow, now always skip) | `tests/e2e/specs/auth.spec.ts:10` |
| P4-11 | Write `STRUCTURE.md` (root-level codebase map) | handoff doc §"Phase 4 executor" |
| P4-12 | Refresh graphify after deletions | `CLAUDE.md` graphify rules |
| P4-13 | Migrate `admin-collector` log streaming from `docker logs` shell-out to dockerode streams (N18) | `workers/src/agents/admin-collector.ts:300`, `workers/Dockerfile:41` |
| P4-14 | Remove legacy Python CI build jobs (`moderator`, `auth` from `.github/workflows/deploy.yml:500,549`) | `.github/workflows/deploy.yml:499-549+` |

---

## Recommended next 5 actions

1. **Fix `SKIP_PENDING_BOOTSTRAP_FIX` (C1).** Add a `register_owner_e2e` reducer (owner-only, no args, self-registers `ctx.sender()` as a User row). Wire it into both `admin-panels.spec.ts` and `moderator.spec.ts` bootstrap blocks, then set `SKIP_PENDING_BOOTSTRAP_FIX = false`. This is the highest-value completeness fix: it turns on 2 committed E2E suites that currently have zero CI coverage.

2. **Add Rust unit tests for `claim_progress_self` (C2).** Two targeted tests: (a) self-service claim when guest row exists; (b) guard rejects when target is already verified. These are pure unit tests (no STDB context needed — same pattern as the existing `plan_claim_*` tests).

3. **Add `mark_email_sent` / `mark_email_failed` reducer tests (M6).** Two tests: happy path upserts `status='sent'`; error path on missing row returns an Err. Keeps the 63-test suite growing in proportion to new reducers.

4. **Add a `healthcheck` to the `workers` service in `infra/docker-compose.yml` (H4).** Even a simple sentinel file check (worker writes `/tmp/healthy` on successful startup; healthcheck does `test -f /tmp/healthy`) would surface boot failures in `docker compose ps` and compose-level dependency checks.

5. **Strip `api.sastaspace.com` from admin CSP `connect-src` (H1).** One-line change in `infra/admin/security_headers.conf`. Can be bundled into any admin nginx config change, or done standalone in Phase 4 cleanup. Low effort, removes a ghost entry from a security config.
