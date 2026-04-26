# CI/CD + Full-Flow Audit — 2026-04-26

**Auditor:** cicd  
**Methodology:** Pulled last 50 runs of deploy.yml via `gh run list`; fetched failed logs via `gh run view --log-failed`; read deploy.yml end-to-end (1,000 lines); cross-referenced with git log to correlate commit messages to run outcomes; inspected all vitest.config.ts files and playwright.config.ts; scanned docker-compose.yml; checked all concurrency blocks and path-filter regexes; reviewed the secret inventory from `gh secret list`.  
**Overall grade:** 5/10  
**Bottom line:** The pipeline is not fundamentally broken — prod is healthy and deploys succeed — but it has been radiating red for the entire day of 2026-04-26 due to three intertwined problems: (1) a coverage-threshold mis-alignment with reality in `landing` that was only fixed late in the day, (2) a ten-commit debugging storm on the e2e bootstrap step that was trying invalid SATS encodings of `Identity` (u256), and (3) a one-time artifact-not-found cascade where `landing-deploy` required `landing-out-stdb` before the matrix job had produced it. None of these represent infrastructure instability; they are all code/config breaks that the CI pipeline correctly caught.

---

## Last 50 runs classification

| Bucket | Count | What it means |
|---|---|---|
| green push | 2 | `fix(e2e): skip admin-panels + moderator` (#3cc8b06); `chore(typewars): cargo fmt` (#8ef1a4b) — both clean end-to-end |
| green workflow_dispatch | 2 | Manual re-runs after fixes landed — pipeline stable at those SHAs |
| flaky-cancelled (concurrency) | 10 | Rapid iteration: new push cancelled the in-flight run before it completed. Expected during debugging storms. |
| real failure — coverage threshold | 3 | `landing-gate (legacy)` exceeded functions/branches thresholds; root cause: the static-PROJECTS refactor (`refactor(landing)`, `test(landing)`) dropped entire runtime code paths from coverage before thresholds were re-tuned. Resolved by `chore(coverage): nudge landing thresholds 9→8 funcs / 6→5 branches` — **but that run is still in_progress at audit time.** |
| real failure — e2e bootstrap | 11 | Bootstrap step tried to call `register_user(owner)` with an Identity (u256) encoded as a decimal string inside a JSON tuple. STDB returned HTTP 400 "invalid digit found in string". Ten successive commits tried hex, 0x-hex, and decimal; all rejected. Fix was to `test.skip()` the admin-panels + moderator specs and drop the problematic bootstrap step entirely. |
| real failure — artifact not found | 1 | `landing-deploy` tried to download `landing-out-stdb` but the `landing-gate` matrix job was cancelled before producing it (concurrency kill mid-matrix). |
| real failure — workers build | 1 | `cpu-features` native add-on threw "Unable to detect compiler type" inside Docker build. Fixed by subsequent worker changes. |
| real failure — missing secret / pre-cutover | 5 | Early morning runs (06:00-07:51 UTC) failed in the `e2e` job on `E2E_TEST_SECRET must be set`. The secret existed (created 2026-04-25) but the workflow at those SHAs was referencing `E2E_STDB_OWNER_TOKEN` which was not yet populated — the old version of the gate checked for `E2E_STDB_OWNER_TOKEN` which maps to `secrets.WORKERS_STDB_TOKEN`, not `SPACETIME_TOKEN`. |
| scheduled run (cancelled) | 1 | 06:03 UTC schedule run was correctly cancelled by the push at 06:05 UTC via `cancel-in-progress: true`. Expected. |
| module/clippy/fmt failures | 3 | `fix(module): satisfy rust 1.95 clippy lints` and `chore(module): cargo fmt` runs — Rust module had lint and format errors that blocked `module-gate`. Real code breaks, correctly caught. |

---

## Top-3 systemic issues

### 1. Coverage thresholds lagging behind code reality (landing app)

**File:** `apps/landing/vitest.config.ts` lines 19–24  
**Current thresholds:** lines 4%, functions 8%, statements 4%, branches 5%  
**Observed reality:** The full landing app including `Deck.tsx`, `deckStdbFlows.ts`, `useDeckStdb.ts`, `page.tsx` files is included in coverage scope. The tested surface is only 6 components (26 tests); the untested `app/**` routes drag the aggregates down to ~4% lines / 8% functions / 5% branches. After the `refactor(landing): static project list` commit removed the STDB subscription hook, the functions metric fell to 8.13% — exactly at the 9% threshold that was in force at that moment. Two runs failed before the threshold was nudged.

**Concrete fix:**  
Either (a) exclude the `app/**` page files from coverage (they are Next.js server components, not unit-testable) — which would push covered-function% into the 60%+ range and make the gate meaningful, or (b) keep the current broad scope but acknowledge the numbers are low and set thresholds to reflect that. The current approach of repeatedly nudging thresholds downward (9→8 functions, 6→5 branches) is a smell: the gate is measuring the wrong surface.

```ts
// apps/landing/vitest.config.ts — recommended exclude list
exclude: [
  "src/app/**",          // Next.js server/page components — not unit-testable
  "src/lib/spacetime.ts",
  "src/lib/projects.ts",
],
// then thresholds can go back up to 50/55/50/50 matching notes
```

---

### 2. E2E bootstrap had no fallback for the SATS Identity encoding problem

**File:** `.github/workflows/deploy.yml` lines 924–953 (current), formerly a "bootstrap — register owner as a user on prod" step  
**Problem:** Across 10 commits (15:01–16:07 UTC), the e2e job contained a step that tried to call `register_user(owner)` over the STDB HTTP API. The SATS encoding of an `Identity` (u256) was attempted as: hex string, `0x`-prefixed hex string, decimal string inside a 1-element tuple — all rejected with HTTP 400. Each failed attempt generated a full CI run (because `cancel-in-progress: true` only fires when a new push comes in, not when a step just fails).

**Deeper issue:** The step was not guarded with `continue-on-error: true` even though the comment at line 924 says admin-panels and moderator specs are already `test.skip()`'d. The bootstrap failure caused the entire e2e job to exit 1 even though the skipped specs would not have needed it.

**Concrete fix:**  
Add `continue-on-error: true` to the bootstrap step *right now* until a `register_owner_e2e()` reducer is added to the module. This prevents the ten-commit red streak pattern from recurring on the next STDB API change.

```yaml
- name: bootstrap — install E2E test secret on prod STDB
  continue-on-error: true   # ← add this
  run: |
    ...
```

The longer-term fix (add a zero-arg `register_owner_e2e()` reducer that uses `ctx.sender()`) removes the Identity encoding problem entirely.

---

### 3. `landing-deploy` can fail when `landing-gate` matrix is partially cancelled

**File:** `.github/workflows/deploy.yml` lines 221–274  
**Problem:** `landing-deploy` depends on `needs: landing-gate` and has `if: needs.landing-gate.result != 'skipped' && needs.landing-gate.result != 'cancelled'`. It downloads only `landing-out-stdb`. However, if a push comes in while `landing-gate` is mid-run, `cancel-in-progress: true` at the top level cancels the entire workflow including the matrix. The next run then starts a fresh `landing-gate`, which uploads fresh artifacts. This is normally fine.

The failure in run 24957572170 occurred because `landing-deploy` ran when `landing-gate` had `result == 'failure'` (not `'cancelled'` — the matrix fail-fast was `false` so one variant failed while the stdb variant succeeded). `landing-deploy` downloaded `landing-out-stdb` which was fine — but the stdb variant's artifact was from a previous run (the concurrency kill mid-matrix left an artifact from the prior attempt) and the download-artifact action matched it.

**More immediate concern:** The `landing-deploy` guard `needs.landing-gate.result != 'failure'` is missing. The current condition only excludes `skipped` and `cancelled`. If the `legacy` matrix leg fails (e.g., test failure), `landing-deploy` will still proceed because `fail-fast: false` means the stdb leg may still produce its artifact. The deploy then succeeds on stale/broken code. This is by design per the comments ("the legacy variant's audit step is non-blocking but still flips the overall result") but is confusing and caused at least one false-red where the deployment was fine but CI still showed red.

**Concrete fix:** Explicitly document that `landing-deploy`'s `result != 'failure'` guard is intentionally absent (the matrix is designed to deploy the stdb variant regardless of the legacy variant's test results), or add `needs.landing-gate.result != 'failure'` to the guard if you want CI red to block deploy.

---

## Workflow audit findings

### `changes` job (line 36–70)

- **`HEAD~1..HEAD` diff-base on batched pushes** is a known bug. On a push that includes N commits, only the last commit's diff is inspected. If a merge commit brings in 10 files, only the files touched between `HEAD~1` and `HEAD` (the merge commit) are detected. The PR path (`github.event.pull_request.base.sha`) is correct. Self-correction: all jobs are force-triggered on `schedule` and `workflow_dispatch`, which covers the "full rebuild" scenario. For push, a batched merge will silently skip jobs. **Medium risk.**
- **Path filter for `notes`** at line 66: `'^(apps/notes|packages|infra/notes/|infra/landing/security_headers)'` — the `security_headers` pattern is not anchored with a trailing slash or `$`, so any file under `infra/landing/security_headers*` (e.g., a future `security_headers_v2.conf`) would trigger it. Minor.
- **`deck` service has no path filter.** The `services/deck/` directory exists in the repo (shown in git status as new files) but has no corresponding detector in `changes.outputs`. If files change there, no job is triggered. **Missing detector.**

### `module-gate` / `module-publish` (lines 72–151)

- `module-gate` correctly gates `module-publish`. The cargo audit step (`--deny warnings`) is strict; this is fine.
- The `module-publish` job has `if: github.event_name == 'push' || github.event_name == 'workflow_dispatch'` — correct, won't publish on PRs.
- **No rollback path for a corrupt module publish.** The comment says nothing about rollback. If `spacetime publish` overwrites a good schema with a broken one, the only recovery is a manual re-run pointing to an older commit. Consider adding a "last known good SHA" comment to the job or a step that verifies the schema post-publish via `/v1/database/sastaspace/schema` before marking success.
- **Re-checkout in `module-publish`** is correct (the job re-checks out the repo independently from `module-gate`).

### `landing-gate` (lines 158–219)

- The matrix builds both `legacy` and `stdb` variants. Lint/typecheck/coverage only run on `legacy`. This is intentional and documented.
- **`pnpm audit --prod --audit-level high` with `continue-on-error: true`** at line 200: the audit is non-blocking. The audit advisory comment says this is temporary pending `@mastra/core` fix. The `continue-on-error: true` means even a critical advisory won't block deploy. This is a risk: if a new critical CVE lands in a transitive dependency today, CI will green while the advisory exists.
- **`needs.module-publish.result == 'success'` download is skipped** when module-publish was skipped (no module change). The `landing-gate` then proceeds with whatever bindings are checked into the repo. This is correct.

### `landing-deploy` (lines 221–274)

- `rsync -a --delete out/ "$LANDING_OUT_DIR/"` — correct, idempotent.
- The nginx restart logic hashes the config files on each run, which is good — avoids unnecessary restarts.
- **No rollback step on landing-deploy failure.** If `rsync` partially completes and then fails (unlikely but possible on disk full), there's no cleanup. Compare to `workers-deploy` which has a `rollback on failure` step.

### `notes` (lines 281–351)

- The `stdb` variant deploys inline (lines 337–351) rather than via a separate `notes-deploy` job. This works but means the stdb deploy is inside a matrix job that also builds the legacy variant. If the legacy build fails, the stdb variant won't deploy even though `fail-fast: false`. **Subtle dependency ordering issue.**
- The `notes` job runs `docker exec sastaspace-notes nginx -s reload` after rsync. This is correct for nginx static reload.

### `typewars` (lines 357–429)

- The `force-recreate` logic at line 409 is correct — bind-mounted files require inode-preserving writes.
- **Security headers cascade logic** at lines 400–419: hashes `security_headers.conf` before and after, then conditionally force-recreates `landing` and `notes`. This is correct but adds deployment coupling — a typewars change can trigger landing and notes container restarts.

### `admin` (lines 436–497)

- The directory-to-file fix for Docker-created bind-mount targets (lines 479–481) is a good defensive step but suggests the compose setup had a first-boot issue that left a dangling directory. This should be cleaned up in the compose file itself.
- **Smoke test retries 8 times** (line 490) with 4s sleep (32s total), longer than other services (5 × 4s = 20s). Reasonable given admin container might take longer to come up.

### `moderator` / `auth` (lines 500–603)

- Both are Python FastAPI services. Both have a `sleep 6` after deploy and a `sleep 4` before the smoke check — that's 10 seconds of unconditional waiting.
- Both `.venv` setups use `pyproject.toml -nt .venv/pyvenv.cfg` for caching, which is correct.
- **Phase 4 cleanup note** at line 872: `moderator` and `auth` remain in `e2e.needs:` with their result guards. They need to be removed from the `needs:` list and `if:` condition when their jobs are deleted. If they're deleted without updating `e2e`, the job will fail to parse.

### `workers` (lines 609–637)

- Installs only `--filter @sastaspace/workers...` which is correct.
- The `pnpm audit --audit-level high` with `continue-on-error: true` has the same advisory bypass concern noted above.

### `workers-deploy` (lines 647–753)

- **Good:** Has `concurrency.cancel-in-progress: false` — deploy jobs won't be cancelled mid-flight even if a new push arrives.
- **Good:** Has a `rollback on failure` step.
- **Concern:** The smoke check at lines 710–726 polls `docker logs` (not an HTTP health endpoint) for specific log line patterns. If the container emits those lines before a subsequent crash, the gate passes and the crash is silent. A better gate is `/healthz` or a structured exit code.
- **Concern:** `rsync workers/ "$PROD/workers/"` followed by `docker compose build` runs the build on the prod server from the rsynced source. If the rsync is interrupted, the prod server has a partial source tree and the build uses it. Consider building the image in CI and pushing to a registry (even a local one).

### `auth-410-deploy` (lines 759–811)

- **Trigger condition** (line 764): fires when `workers == 'true' || agents == 'true' || workflow_dispatch`. This means any `services/auth` or `infra/agents` change triggers an auth-410 redeploy, even if the auth-410 config itself hasn't changed. This is benign (just redundant) but adds ~2min to those runs.
- The rollback step (lines 808–811) just stops the container without restarting the legacy auth service. This is a non-reversible rollback unless someone manually runs `docker compose start auth`.

### `deck-static-deploy` (lines 818–866)

- **Missing path trigger:** changes to `infra/deck/nginx.conf` or `services/deck/` don't trigger this job unless `workers` or `agents` also changed. If only `infra/deck/nginx.conf` is edited, the deploy is missed.
- **Good rollback:** Stops `deck-static` and restarts legacy `deck` — genuinely reversible.
- **Smoke check** accepts HTTP 200 or 403 — correct given nginx autoindex may be on or off.

### `e2e` (lines 869–1000)

- **`needs:` list** includes `moderator` and `auth` alongside `workers-deploy`, `auth-410-deploy`, `deck-static-deploy`. The `auth` and `moderator` jobs are `if: needs.changes.outputs.agents == 'true'` — they will be `skipped` on non-agent pushes. The `e2e` guard checks `needs.moderator.result != 'failure'` and `needs.auth.result != 'failure'` — `skipped` is not `failure`, so this is safe. But the `needs:` list creates a graph edge that means `e2e` waits for `moderator` and `auth` even when they're skipped. **No practical harm but cleaner to remove post-Phase 4.**
- **`E2E_OWNER_STDB_TOKEN` and `E2E_STDB_OWNER_TOKEN`** are both set to `secrets.SPACETIME_TOKEN` (lines 899–900). Two aliases for the same value. The comment says admin-panels.spec.ts and helpers/auth.ts converged on different names. This works but is confusing. Clean up to one canonical name post-Phase 4.
- **`ADMIN_OUT_DIR` is set at workflow level** (line 31) but was not in the env block when earlier runs were executed (visible in log timestamp 07:51). This was added during the day — some early failures may reflect a missing env var.
- **playwright.config.ts defines 3 projects** (`desktop-chromium`, `notes-legacy`, `notes-stdb`) but `E2E_STDB_AUTH` is never set in the CI step. This means all three projects run against live prod but without the STDB auth toggle — `notes-stdb` will behave identically to `notes-legacy`. The matrix axis mentioned in the playwright.config.ts comment ("Phase 3 wires this fully") was never wired.

---

## Recommended workflow improvements

| Priority | Change | Impact |
|---|---|---|
| P0 | Add `continue-on-error: true` to the `bootstrap — install E2E test secret` step | Stops bootstrap API changes from causing full-run failures when admin-panels/moderator specs are already `test.skip()`'d |
| P0 | Fix `apps/landing/vitest.config.ts` coverage include: exclude `src/app/**` (server components), raise thresholds to 50/55 matching notes | Eliminates the threshold-nudge treadmill; makes the gate meaningful |
| P1 | Add `rollback on failure` step to `landing-deploy` | Parity with workers-deploy; necessary if rsync partially fails |
| P1 | Phase 4 cleanup: remove `moderator` and `auth` from `e2e.needs:` and `if:` guards | Prevents parse failure when jobs are deleted |
| P1 | Add path filter for `infra/deck/` to trigger `deck-static-deploy` independently | Ensures nginx config changes to deck-static are deployed |
| P2 | Unify `E2E_OWNER_STDB_TOKEN` / `E2E_STDB_OWNER_TOKEN` to one name | Removes confusing dual-alias; pick `E2E_STDB_OWNER_TOKEN` and update all spec helpers |
| P2 | Wire `E2E_STDB_AUTH=true` in the `run playwright` step env | Actually enables the `notes-stdb` playwright project; currently dead |
| P2 | Document or fix: `landing-deploy` proceeds even when `landing-gate` legacy leg fails | Clarify in comment or add explicit `result != 'failure'` guard |
| P2 | Move workers container build to CI (registry push) instead of build-on-prod-server | Eliminates partial-rsync-then-bad-build risk; faster cold starts |
| P3 | Change `changes` diff base for push from `HEAD~1` to `${{ github.event.before }}` | Correctly detects all changed files in batched pushes |
| P3 | Add path detector for `services/deck/` in `changes.outputs` | Currently no CI fires on changes to the new deck service |

---

## Missing CI checks (defensive moats)

1. **Gitleaks / secret scanning** — no secret scanner in CI. The identity hex `c20086b8ce1d18ec9c564044615071677620eafad99c922edbb3e3463b6f79ba` was emitted as a plain env var in a step's env dump in run 24960975115. While this particular value (the STDB Identity public key) is not secret, the pattern of writing non-redacted values to env blocks that appear in logs is a hygiene issue. Gitleaks would catch actual secrets in code; no runner-log scanning tool exists but the OWNER_HEX case shows the risk. **Recommendation:** `gitleaks protect --staged` as a pre-commit hook server-side (`runs-on: [self-hosted]` means pre-push hooks can run).

2. **Lighthouse / mobile performance budget** — no Lighthouse CI step. The landing and typewars apps ship a Next.js static export. A CI Lighthouse run (even just `lhci autorun` against a local server) would catch performance regressions early. The schedule run at 04:00 UTC would be a natural home.

3. **Trivy / container vulnerability scan** — `docker compose build workers` runs on prod. No image vulnerability scan before deployment. Even a `trivy image --exit-code 1 --severity HIGH,CRITICAL sastaspace-workers:latest` after the build step would catch compromised base images.

4. **Accessibility check (axe-core in Playwright)** — the e2e suite runs against live prod but has no axe-core assertions. A one-time `axe` pass in `landing.spec.ts` and `notes.spec.ts` would surface WCAG violations before users find them.

5. **Schema migration safety check** — when `module-publish` runs, it publishes the Rust module to SpacetimeDB. There is no pre-publish schema compatibility check. A breaking migration (e.g., removing a column that existing subscriptions expect) would silently break live clients. A step that calls `/v1/database/sastaspace/schema` before and after publish and diffs the result would provide a safety net.

6. **License compliance** — the pnpm workspace has dozens of transitive deps. No license check (e.g., `pnpm licenses list --prod | grep -E 'GPL|AGPL'`) ensures no copyleft dependencies sneak in via `@mastra/core` upgrades.

7. **PR-level deploy preview** — the workflow skips deploys on `pull_request` events (only push/dispatch/schedule deploy). No preview environment exists. PRs only get lint/typecheck/test — no live smoke test.

---

## Self-hosted runner health observations

- Two runners observed in logs: `taxila-prod` (runner 1, path `actions-runner`) and `taxila-prod-2` (runner 2, path `actions-runner-2`). Both pick up jobs within 5–15 seconds of creation — no queuing issues observed across the 50 runs.
- Runner version: `2.334.0` on both.
- Machine name on both: `taxila` (192.168.0.37 per memory reference). Both runners share the same physical host — concurrent jobs with `docker compose build` can compete for CPU/disk.
- `docker clean -ffdx` on checkout removes `node_modules/`, `packages/stdb-bindings/node_modules/`, `packages/typewars-bindings/node_modules/`, `workers/node_modules/` on every run. With no caching strategy for pnpm, every run re-installs the full workspace. A `pnpm store` cache (even a local bind mount) would save 20–40s per run.
- No evidence of runner stalling or jobs sitting queued > 2 min across the 50 runs.

---

## Secret-hygiene observations

1. **`OWNER_HEX` logged as plain env var (now-deleted step):** In run 24960975115 (SHA `e740305d`, ~16:05 UTC), the step `bootstrap — register owner as a user on prod` set `OWNER_HEX` as an env var and printed the full step env block including `OWNER_HEX: c20086b8ce1d18ec9c564044615071677620eafad99c922edbb3e3463b6f79ba`. This is a STDB Identity public key, not a private secret, but the pattern of printing unmasked hex values in logs is a hygiene issue. That step has since been removed from the current deploy.yml.

2. **`E2E_OWNER_STDB_TOKEN` / `E2E_STDB_OWNER_TOKEN` both alias `secrets.SPACETIME_TOKEN`** (lines 899–900). The `ADMIN_OUT_DIR` env var includes a hardcoded path to the prod server (`/home/mkhare/sastaspace/infra/admin/out`) — this is not secret but is an infrastructure detail that belongs in a secret or a variable rather than a workflow env.

3. **`NEXT_PUBLIC_OWNER_EMAIL: mohitkhare582@gmail.com`** is hardcoded at line 447. Public env vars for Next.js builds are not secret (they're baked into the JS bundle), but having a personal email in a public workflow file is a mild hygiene issue.

4. **No secret scanning at push time.** No `gitleaks` or similar tool is in the pipeline. The repo is public (`themohitkhare/sastaspace`).

5. **`moderator/.env` and `workers/.env` on prod** are created via `install -m 600 /dev/null` (lines 532, 688) — correct, mode-600 before write. No concern here.

6. **All five secrets** (`E2E_OWNER_STDB_TOKEN`, `E2E_TEST_SECRET`, `RESEND_API_KEY`, `SPACETIME_TOKEN`, `WORKERS_STDB_TOKEN`) are Actions secrets — never repo secrets. This is correct; repo secrets are visible to all collaborators.

---

## Recommended next 5 actions

1. **[Today, 5 min]** Confirm the in-progress run `24962178311` (`chore(coverage): nudge landing thresholds 9→8 funcs / 6→5 branches`) passes. If it does, the immediate red streak is over. Then fix the coverage scope properly (exclude `src/app/**` from landing coverage) so future refactors don't re-trigger the treadmill.

2. **[Today, 10 min]** Add `continue-on-error: true` to the `bootstrap — install E2E test secret` step in `deploy.yml` (line 932). This removes the single point of failure that caused 10 consecutive red runs on the SATS-encoding debugging storm. The admin-panels and moderator specs are already `test.skip()`'d so a bootstrap failure should never be a blocker.

3. **[This week]** Add a `register_owner_e2e()` no-arg reducer to the Rust module (uses `ctx.sender()`, no Identity encoding). This unblocks admin-panels.spec.ts and moderator.spec.ts completely and removes the STDB HTTP API encoding guesswork.

4. **[This week]** Phase 4 cleanup: remove `moderator` and `auth` jobs from `e2e.needs:` and the `if:` condition; unify `E2E_OWNER_STDB_TOKEN` / `E2E_STDB_OWNER_TOKEN` to one name; wire `E2E_STDB_AUTH=true` in the `run playwright` step so `notes-stdb` playwright project actually tests something different.

5. **[Next sprint]** Add Trivy container scan after `docker compose build workers` in `workers-deploy`, add `gitleaks` to `module-gate` (or as a push hook), and add an axe-core accessibility assertion to `landing.spec.ts` and `notes.spec.ts`. These three checks fill the largest defensive gaps at minimal CI cost.
