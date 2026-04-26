# Consolidated 7-Lens Audit — 2026-04-26

**Auditors (parallel, Sonnet 4.6):** feature-readiness · ui · ux · security · completeness · performance · cicd
**Average grade:** **6.4 / 10** — solid but with real gaps. The TypeScript/Rust core is well-built; the gaps are mostly in test coverage, mobile UX, and one structural privacy bug.

| Lens | Grade | Headline |
|---|---|---|
| Security | **8/10** | No criticals; `request_magic_link` callback_url phishing path + public `user` table are real |
| UI | **7/10** | Strong tokens, but admin duplicates them; brand violations (ALL CAPS, font-weight 600, box-shadow) in typewars |
| Completeness | **7/10** | Only 4 TODO markers, 0 unimplemented! macros — but two specs are permanently `test.skip`'d |
| Performance | **7/10** | Static exports, good Cargo profile; `submit_word` full-table scan + `SELECT * FROM user` are real costs |
| UX | **6/10** | Battle screen unusable on mobile; LegionSwapModal silent no-op; deck "share link" is dead UI |
| Feature readiness | **5/10** | Deck audio broken in prod (LocalAI image); A6 staging gate never run; 3 specs skipped |
| CI/CD | **5/10** | Pipeline not structurally broken; today's red streak was 3 root causes (bootstrap iter, coverage thresholds, e2e gating) |

---

## Cross-audit signal (issues flagged by ≥2 auditors)

| # | Finding | Lenses | Severity |
|---|---------|--------|----------|
| 1 | `register_owner_e2e` reducer missing — `SKIP_PENDING_BOOTSTRAP_FIX=true` permanently skips admin-panels.spec.ts + moderator.spec.ts | feature, completeness, cicd, ux | **HIGH** |
| 2 | Modal accessibility — no focus trap, ARIA roles, or Esc bindings on 3 of 4 modal implementations | ux, ui | **HIGH** |
| 3 | `SELECT * FROM user` (typewars verify page) + `user` table is `public` — emails leak to anon STDB subscribers | performance C1, security D4 | **HIGH** |
| 4 | Typewars battle screen unusable on mobile — recent CSS fix missed `.battle-*` classes | ux C1 | **HIGH** |
| 5 | CI matrix `legacy` build doubles wall-time on every push for rollback artifacts | performance M8, cicd | MEDIUM |
| 6 | No `:focus-visible` rings — WCAG 2.4.7 fail across all apps | ui H6, ux a11y | MEDIUM |
| 7 | Brand violations: ALL CAPS labels (`ENLIST →`, `CONFIRM SWITCH →`, `YOU`), font-weight 600 in 3 topbars, `box-shadow` in 2 game states | ui H1-H5 | LOW |

---

## Top-10 prioritized action plan

### P0 — concrete, high-impact, ≤1 hour each

1. **Add `continue-on-error: true` to `bootstrap — install E2E test secret` step** (`deploy.yml:932`). Stops the next STDB encoding-iteration storm from cascading into 10 red runs. **5 min.**
2. **Domain-pin `callback_url` in `validate_magic_link_args`** (`modules/sastaspace/src/lib.rs`). Closes a real phishing path: anyone can call `request_magic_link` with `callback_url=https://evil.example/`. **5-line Rust change.**
3. **Filter `SELECT * FROM user` subscription** (`apps/typewars/src/app/auth/verify/page.tsx:164`). Currently leaks all User rows including emails to any client opening the verify page. **Add `WHERE identity = X'<hex>'`.**
4. **Gate `add_log_interest` with `assert_owner`** (`modules/sastaspace/src/lib.rs:1109`). Currently any anon STDB identity can register log interest and trigger collector subprocesses on prod. **1-line.**
5. **Fix `LegionSwapModal` silent no-op** (`apps/typewars/src/components/App.tsx:68`). The `onSwap` handler discards the chosen legion and just closes. **Wire the missing reducer call.**

### P1 — meaningful, 1-3 hours each

6. **Add `register_owner_e2e()` reducer + flip both `SKIP_PENDING_BOOTSTRAP_FIX = false`** (`modules/sastaspace/src/lib.rs` + `tests/e2e/specs/{admin-panels,moderator}.spec.ts`). Unblocks 2 entire test suites permanently in CI. **~30 min including bindings regen + push.**
7. **Mobile-fix typewars battle screen** (`apps/typewars/src/styles/typewars.css`). My earlier fix covered legion-select / map / words-grid / leaderboard but missed `.battle-input-row`, `.region-hp-wrap`, soft-keyboard handling. **~1-2 hours including verification on mobile viewport.**
8. **Index `submit_word` lookup** (`modules/typewars/src/word.rs:119`). Currently full-scan `iter()` on every keypress; `session_id` btree index already exists, just not used. **5-line Rust change.**
9. **Wire admin to `@sastaspace/design-tokens` instead of duplicating tokens** (`apps/admin/src/app/globals.css:7-69`). Replace hand-rolled `:root` block with `@import`. **20 min.**
10. **Modal focus traps + ARIA + Esc bindings** in `SignInModal`, `LegionSwapModal`, `ProfileModal` to match `AuthMenu` (notes). **WCAG 2.1 SC 2.1.2 fail today.**

### P2 — important but defer if time-boxed

- Fix landing coverage scope (exclude `src/app/**`, raise thresholds to 50/55) — turns coverage gate from a noise floor into a meaningful signal
- Gate CI matrix `legacy` variant behind `workflow_dispatch` only — halves frontend CI wall-time
- Strip `api.sastaspace.com` from admin CSP `connect-src`
- Fix dead "Copy share link" button on deck (`navigator.clipboard.writeText`)
- Add `:focus-visible` outline globally
- Lowercase `ENLIST →` / `CONFIRM SWITCH →` / `YOU` (brand: sentence case)
- Replace `box-shadow: inset` with `outline` on typewars selected states
- Add Rust unit tests for `claim_progress_self`, `mark_email_sent`, `mark_email_failed`
- Add workers `healthcheck` block in compose

### P3 — operator action (cannot fix from CI)

- **Run A6 staging acceptance gate** on taxila per `2026-04-26-phase3-staging-acceptance.md`. The Result section is blank.
- **Swap LocalAI image** to `localai/localai:latest-aio-gpu-hipblas` + AMD GPU device mounts. Until done, every deck `generate_job` fails.

---

## CI/CD-specific findings

The CI pipeline **is not structurally broken** — prod is healthy and the runner has 2 instances on `taxila` picking up jobs in 5-15s with no queue. Today's red streak (40+ failures across the day) decomposes into:

- **11 runs** failed on the `register_user(owner)` bootstrap step iterating SATS Identity encodings
- **3 runs** failed on landing coverage thresholds being out of sync with the static-projects refactor
- **10 runs** were `cancelled` due to `concurrency: cancel-in-progress: true` (rapid debug iterations)
- **1 run** failed on artifact-not-found cascade
- **1 run** failed on `cpu-features` native add-on
- **5 runs** (early morning) failed pre-cutover on missing E2E_TEST_SECRET

**Adding more self-hosted runners would not help** — runners aren't the bottleneck. The fixes are workflow-shape:
- `continue-on-error: true` on bootstrap
- Realistic coverage thresholds + `src/app/**` exclude
- Gate `legacy` matrix behind dispatch-only
- Move workers container build off the prod runner (build-on-prod has a partial-rsync race)

---

## Phase 4 cleanup backlog (consolidated)

14 items consolidated from the 7 reports — see `2026-04-26-audit-completeness.md` § "Phase 4 backlog" for the full table. Highlights:

- `git rm -r services/{auth,deck,admin-api}/ infra/agents/moderator/`
- Remove 4 Python service blocks from `docker-compose.yml`
- Remove `api.sastaspace.com` cloudflared route (≥7 days post-cutover)
- Drop `legacy` build_variant matrix from all 4 CI app jobs
- Drop `project` table + `upsert_project` / `delete_project` reducers (now unused after static-projects refactor)
- Migrate `admin-collector` log streaming from shell-out to dockerode streams (audit N18)
- Delete `apps/{notes,typewars}/src/app/auth/callback/page.tsx`
- Write `STRUCTURE.md`
- Refresh graphify after deletions

---

## What's actually shippable right now (per feature)

The feature-readiness audit's per-surface scorecard distilled:

- **Ship-ready (≥90%):** Landing home, Notes posts, Typewars game (legion-select / war-map / battle / leaderboard), Admin Google sign-in
- **Functional but unverified (60-80%):** Notes magic-link STDB sign-in, Typewars STDB sign-in, Admin Comments queue, Admin Server/Services/Logs panels — all wired but blocked from CI verification by `register_owner_e2e` gap
- **Broken in production (<35%):** Deck STDB audio generation (LocalAI image swap pending)
- **CI-untested post-cutover (0%):** Deck (legacy flow skipped, STDB flow not gated), admin-panels (skipped), moderator (skipped)

---

## Index to individual reports

- [`2026-04-26-audit-feature-readiness.md`](./2026-04-26-audit-feature-readiness.md)
- [`2026-04-26-audit-ui.md`](./2026-04-26-audit-ui.md)
- [`2026-04-26-audit-ux.md`](./2026-04-26-audit-ux.md)
- [`2026-04-26-audit-security.md`](./2026-04-26-audit-security.md)
- [`2026-04-26-audit-completeness.md`](./2026-04-26-audit-completeness.md)
- [`2026-04-26-audit-performance.md`](./2026-04-26-audit-performance.md)
- [`2026-04-26-audit-cicd.md`](./2026-04-26-audit-cicd.md)

---

## Recommended next batch

If you want me to proceed autonomously, I'd execute P0 (5 fixes) + P1 #6-#10 in that order — that's ~3-4 hours of work, addresses every `HIGH` cross-audit finding, and makes a meaningful dent in the average grade. Stop me before any individual fix if you'd rather change priority.

Operator-only items (P3) are gated on you doing them by hand on taxila — flag them when complete and I'll wire follow-ups.
