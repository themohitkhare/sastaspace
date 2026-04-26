# Feature Readiness Audit — 2026-04-26

**Auditor:** feature-readiness
**Methodology:** Read all spec, plan, handoff, and CI documents; traced every feature surface from the frontend component through the worker/reducer chain to infra config; cross-checked what CI actually deploys vs what the spec claims is done; identified stubs, skipped tests, unexecuted steps, and features that exist in code but have a blocking dependency unresolved in production.
**Overall grade:** 5/10 — The TypeScript surface (landing, notes posts, typewars game core) is genuinely ship-ready; the new STDB-native paths for auth (notes + typewars), admin Comments, and moderator are wired and deployed but their E2E gate is hard-blocked by an unsolved owner-identity bootstrap issue; Deck audio generation has a hard dependency on a LocalAI image swap that has never been executed on taxila; Admin Server/Services/Logs panels are live-data-ready on paper but the staging acceptance gate (A6) was never completed by the operator; and four legacy Python service CI jobs are still running alongside their TS replacements with no Phase 4 cleanup done.

---

## Per-feature readiness scorecard

| Feature | Surface | Ship-ready % | Critical gaps |
|---|---|---|---|
| Landing home | sastaspace.com | 95% | PresencePill loading state shows "…" briefly before STDB connects; cosmetic only |
| Notes posts (listing + reading) | notes.sastaspace.com | 98% | Static export; works fully. No blocking gap. |
| Notes comments (anon — read only) | notes.sastaspace.com | 95% | Comments display via STDB subscription; no write path for anon users (by design). |
| Notes comments (signed-in) | notes.sastaspace.com | 60% | submit_user_comment reducer exists; E2E spec for signed-in comments (`comments-signed-in.spec.ts`) is hard-skipped because `admin-panels.spec.ts` `SKIP_PENDING_BOOTSTRAP_FIX=true` blocks the seeding path — no `register_owner_e2e` reducer exists to seed a user row via the owner token in CI |
| Notes magic-link sign-in (STDB) | notes.sastaspace.com | 75% | STDB path wired and deployed (NEXT_PUBLIC_USE_STDB_AUTH=true); auth-mailer worker enabled in prod compose; but staging A6 gate (full E2E matrix stdb+fastapi) was never run — result field in `2026-04-26-phase3-staging-acceptance.md` is blank. The feature works logically but production smoke has not been formally signed off. |
| Typewars legion select | typewars.sastaspace.com | 95% | Component exists (`LegionSelect.tsx`); backed by typewars module; unblocked. |
| Typewars war map | typewars.sastaspace.com | 95% | `MapWarMap.tsx` + region subscription; unblocked. |
| Typewars battle screen | typewars.sastaspace.com | 95% | `Battle.tsx`; backed by typewars module; unblocked. |
| Typewars leaderboard | typewars.sastaspace.com | 95% | `Leaderboard.tsx`; backed by typewars module; unblocked. |
| Typewars region claim | typewars.sastaspace.com | 90% | Reducer path exists; E2E spec `typewars-warmap.spec.ts` is in WIP/untracked state and not yet gated in CI. |
| Typewars magic-link sign-in (STDB) | typewars.sastaspace.com | 65% | `SignInTrigger.tsx` flips callback to `/auth/verify` when USE_STDB_AUTH=true; verify page calls `verify_token` + `claim_progress_self`; staging gate never run; claim_progress_self path in the verify page may be missing — `claim_progress_self` reducer is in the typewars module but the verify page references it only in a comment ("fall back to subscribing to the User row"); same SKIP_PENDING_BOOTSTRAP_FIX blocks E2E coverage. |
| Deck (legacy /lab/deck) | sastaspace.com/lab/deck | 0% (SKIPPED) | CI deploys `landing-out-stdb` artifact; E2E runs with `E2E_AUTH_BACKEND=stdb`; deck.spec.ts `test.skip(AUTH_BACKEND === "stdb" && FLOW === "legacy", ...)` fires → deck is entirely untested in CI post-cutover. The legacy path calls the Python deck service which CI stops. |
| Deck STDB mode | sastaspace.com/lab/deck | 30% | Frontend wired (`USE_STDB_DECK=true` baked into prod bundle). Planner path (Ollama→set_plan) is implemented. Audio generation is **blocked**: the workers compose uses `localai/localai:latest` (CPU image, no MusicGen backend bundled); infra/localai/README.md §"Phase 1 W3 status" explicitly says the AIO-GPU image swap has never been executed on taxila; `/v1/sound-generation` returns 400. All generate_job rows will call `set_generate_failed`. |
| Admin panel sign-in | admin.sastaspace.com | 90% | Google OAuth works; STDB owner token paste-in UI exists. Missing: no automated test that the owner token accepted post-cutover is the `SPACETIME_TOKEN` (maincloud) vs `WORKERS_STDB_TOKEN` (prod-server) form — comment at deploy.yml:895 documents the split but no guard enforces which one works in admin. |
| Admin Comments queue | admin.sastaspace.com | 70% | STDB subscription + `set_comment_status_with_reason` + `delete_comment` wired. Optimistic UI. Blocks: `admin-panels.spec.ts` is entirely skipped (`SKIP_PENDING_BOOTSTRAP_FIX=true`); no automated CI gate for this panel. |
| Admin Server panel (system_metrics) | admin.sastaspace.com | 65% | `ServerStdb` subscribes to `system_metrics` table. Worker `admin-collector` enabled in prod compose. Blocks: staging A6 gate never run; `upsert_system_metrics` call depends on `nvidia-smi`/`rocm-smi` being present in the container — the Dockerfile installs `rocm-smi-lib` from alpine edge testing with `|| true` (soft-fail); on prod taxila with AMD 7900 XTX, if the package isn't available, GPU metrics are silently null. |
| Admin Services panel (container_status) | admin.sastaspace.com | 65% | `ServicesStdb` subscribes to `container_status`. Worker enabled. Same staging gap. `ALLOWED_CONTAINERS` list in admin-collector still includes `sastaspace-auth`, `sastaspace-admin-api`, `sastaspace-deck`, `sastaspace-moderator` — these containers are stopped in prod but still reported as "stopped" in the UI rather than absent, which may confuse operators. |
| Admin Logs panel | admin.sastaspace.com | 60% | `LogsStdb` + `log_interest` add/remove pattern wired. Requires owner token to register interest; without it, read-only (existing log_event rows only). Not tested in CI. |
| Worker auth-mailer | n/a | 80% | Agent wired, enabled in prod compose. `RESEND_API_KEY` provisioned via CI secret. Drain loop + error reporting complete. Soft gap: reducer calls use positional args (`reducers.markEmailSent(row.id, ...)`) but SDK 2.1 errata (Appendix A of spec) says args must be a single object literal — if bindings regen changed the call shape, this may silently fail. Workers Vitest spec covers happy+failure paths but against a mock, not a live STDB. |
| Worker admin-collector | n/a | 65% | Agent wired, enabled in prod compose. Metrics + container loops implemented. Hard gap: `ALLOWED_CONTAINERS` list is duplicated (hardcoded in both `admin-collector.ts:23-37` and `modules/sastaspace/src/lib.rs` ALLOWED_CONTAINERS constant) — keep-in-sync comment says "Future: thread through app_config" but it's not done. Log-interest subprocess management has no unit test for the actual `docker logs --follow` path (only the STDB subscription logic is tested). |
| Worker deck-agent | n/a | 35% | Planner (Ollama) path implemented and tested. Audio renderer (`renderViaLocalAi`) calls `/v1/sound-generation` which returns 400 on the current `localai/localai:latest` image — every generate_job will call `set_generate_failed` until the AIO image is deployed on taxila. |
| Worker moderator-agent | n/a | 70% | Agent wired, enabled in prod compose. Injection detector + classifier implemented. Prompt verbatim-ported from Python. `moderator.spec.ts` created but entirely skipped (`SKIP_PENDING_BOOTSTRAP_FIX=true` + `MODERATOR_ENABLED` gate). Manual verification of the moderation flow has not been documented. |

---

## Critical findings (must-fix before claiming "feature complete")

1. **Deck audio generation is broken in production** (`infra/localai/README.md:72-116`, `workers/src/agents/deck-agent.ts:311-315`). The compose file uses `localai/localai:latest` (CPU image); the MusicGen backend is not bundled in this image. Every generate_job triggers `set_generate_failed`. The fix (swap to `localai/localai:latest-aio-gpu-hipblas` + add AMD GPU device mounts on taxila) has been documented but never executed. This makes the STDB Deck feature entirely non-functional end-to-end despite the planner working.

2. **Deck E2E is completely skipped in CI post-cutover** (`tests/e2e/specs/deck.spec.ts:22-25`, `.github/workflows/deploy.yml:985`). CI sets `E2E_AUTH_BACKEND=stdb` and `E2E_DECK_FLOW` is not set (defaults to `"legacy"`). The skip condition `AUTH_BACKEND === "stdb" && FLOW === "legacy"` fires, so zero deck tests run. The deck feature has no automated CI gate at all.

3. **`admin-panels.spec.ts` and `moderator.spec.ts` are permanently skipped** (`SKIP_PENDING_BOOTSTRAP_FIX=true` is a hardcoded `true` constant in both files). The blocker is that there is no `register_owner_e2e` reducer and the STDB HTTP API's Identity encoding for `register_user` is not working from test code. Every admin Comments panel action and every moderator verdict is unverified in CI. Fixing requires adding a `register_owner_e2e()` reducer (no args, uses `ctx.sender()`) to `modules/sastaspace/src/lib.rs`.

4. **Phase 3 Section A6 staging gate was never completed by the operator** (`docs/audits/2026-04-26-phase3-staging-acceptance.md:80-92`). The "Result" section is blank. The cutover-committed compose has all 4 workers enabled (`WORKER_*_ENABLED=true`), but the formal staging acceptance — running the full Playwright matrix against a prod-equivalent compose with both `E2E_AUTH_BACKEND=fastapi` and `=stdb` — was documented as an operator action and never done. This means the production cutover was performed without the spec-required gate.

5. **Notes magic-link auth STDB path has no confirmed end-to-end production verification.** The `verifyTokenViaStdb` function mints a fresh anonymous identity, connects, calls `verify_token`, then disconnects — meaning the JWT it returns (`minted.token`) was used to call the reducer, but the session token persisted is the *anonymous* JWT, not a user-bound JWT tied to any email. If STDB resolves identity by connection token, sessions work; if it expects the identity minted at `verify_token` call time to match a User row lookup later, comments will silently fail with "not signed in" (`lib.rs:242`). This is a correctness risk that needs a live smoke test.

---

## High-priority findings

6. **Auth-mailer reducer calls use positional args, violating SDK 2.1 errata** (`workers/src/agents/auth-mailer.ts:98-101`). `reducers.markEmailSent(row.id, ...)` and `reducers.markEmailFailed(row.id, ...)` use positional args. Appendix A of the spec says SDK 2.1 reducer calls must use a single object literal (`await conn.reducers.markEmailSent({id, providerMsgId})`). The vitest spec mocks the reducer so this would not be caught by tests. If bindings regen aligned to the spec shape, these calls silently no-op (no-arg object) or throw.

7. **`ALLOWED_CONTAINERS` list is duplicated and already stale** (`workers/src/agents/admin-collector.ts:23-37`). The hardcoded list still includes `sastaspace-auth`, `sastaspace-admin-api`, `sastaspace-deck`, `sastaspace-moderator` — containers stopped by the Phase 3 cutover. The services panel will show these as "stopped" rather than absent, which is misleading. The spec's intended fix ("thread through `app_config`") is not implemented.

8. **Typewars `claim_progress_self` invocation in the verify page is incomplete** (`apps/typewars/src/app/auth/verify/page.tsx:20`). The spec says step 3 of the typewars verify flow is: if `?prev=<hex>` is in the URL, connect to the typewars module and call `claim_progress_self(prevIdentity, email)`. The page comment documents this but the inline `TODO` and "fall back to subscribing to the User row" language suggests the actual call may be conditional or missing. Unverified because E2E is blocked by bootstrap fix.

9. **`rocm-smi-lib` install in workers Dockerfile is a soft-fail** (`workers/Dockerfile:44-50`). The `|| true` means if the alpine edge testing package is unavailable, GPU metrics are silently `null`. On prod (taxila, AMD 7900 XTX), this means `system_metrics.gpu` is always null in the Server panel even when Ollama/LocalAI is using the GPU. The spec-documented fallback is to host-bind `/opt/rocm/bin/rocm-smi` via compose volumes, but this is not in the compose file.

10. **Admin owner token identity confusion** (`.github/workflows/deploy.yml:895-900`). The E2E workflow comment explains that `SPACETIME_TOKEN` (maincloud-issued JWT) is used for `set_e2e_test_secret` HTTP calls, while `WORKERS_STDB_TOKEN` (prod-server-issued JWT) is used for the worker WebSocket handshake. But `admin_stdb_owner_token` in localStorage (set by the admin UI) is used for both reducer HTTP calls AND the STDB WebSocket connection. There is no documented procedure for which JWT format the admin UI should use, and no guard in the UI or bindings to detect the wrong form.

11. **Legacy Python service CI jobs (`auth`, `moderator`) still build, test, and deploy** (`.github/workflows/deploy.yml:500-548`, `549-604`). They are gated on the `agents` change-detector, which fires when `services/auth/` or `infra/agents/` change. The Phase 3 `workers-deploy` CI step stops these containers after a successful workers deployment, but the next commit that touches `services/auth/` or `infra/agents/` will restart them — creating a race condition between the legacy and new paths in production.

---

## Medium / nice-to-have

12. **`RECENTS` array in Deck.tsx is hardcoded mock data** (`apps/landing/src/app/lab/deck/Deck.tsx:74-90`). "Recently on the deck" shows three hardcoded fake entries ("2 min ago", "yesterday", "last week") regardless of whether the user or anyone else has ever submitted a plan. Once real `plan_request` data exists in STDB, this should subscribe to recent rows.

13. **`GeneratingView` in Deck is a pure client-side animation, not connected to actual job status** (`Deck.tsx:769-858`). When `USE_STDB_DECK=true`, clicking "generate audio" transitions to `GeneratingView` which auto-completes after a timed animation (`durs[i] = length * 120ms`), then shows the Results screen regardless of whether the STDB `generate_job` row ever reaches `status='done'`. Only when the user clicks "download .zip" is the actual `submitGenerate` call made. If the job is still `pending` or `failed`, the download UI shows "download failed — retry". This is a UX gap: the "generating" animation is fake.

14. **Admin dashboard fallback polling still calls `usePoll` with `'__skip__'`** (`apps/admin/src/components/panels/Dashboard.tsx:23-28`). When `USE_STDB_ADMIN=true`, polled data is skipped by passing `'__skip__'` as the URL. This relies on `usePoll` treating non-URL strings as a skip signal — confirm this is explicitly handled in `usePoll.ts` or it will fetch `/api/__skip__` on the prod domain.

15. **`verify-no-api-ingress.sh` is not wired into CI** (`infra/cloudflared/verify-no-api-ingress.sh`). The script exists (part of audit N22) but is not called from `.github/workflows/deploy.yml`. There is no automated gate preventing `api.sastaspace.com` from being re-added to the cloudflared config accidentally.

16. **Notes `/auth/callback` page still deployed** (`apps/notes/src/app/auth/callback/page.tsx`). Marked `PHASE 4 DELETE`. With the stdb-native artifact deployed and auth.sastaspace.com returning 410, any stale magic-link email (sent pre-cutover, within the 15-min TTL window) that lands on `/auth/callback` will receive a broken session (token from a dead service). This is a 15-minute window at cutover — acceptable, but the page should be removed in Phase 4 promptly.

17. **Admin `useStdb.ts` provider has a reload-on-token-save pattern** (`apps/admin/src/hooks/useStdb.ts:62-66`). The `SastaspaceProvider` reads the owner token once at mount and does not re-read on `storage` change. The comment says: "The OwnerTokenSettings modal triggers a `window.location.reload()` after save". This is a fragile pattern — the reload won't fire in iframes or non-browser environments, and any future test that sets the token programmatically will need to explicitly reload.

---

## Phase 4 cleanup items

The following are not new findings — they are known deferred work that belongs in the Phase 4 cleanup sprint. Listing them here so the controller can cross-reference with the structure auditor.

- **Delete `services/auth/`, `services/admin-api/`, `services/deck/`, `infra/agents/moderator/`**. All four are superseded but not yet removed. CI still builds and deploys them when the `agents` change-detector fires.
- **Remove legacy Python service blocks from `infra/docker-compose.yml`** (`auth`, `admin-api`, `deck`, `moderator` services, lines 228–347). The `workers-deploy` step stops them but keeps the blocks for rollback. Phase 4 is the agreed removal point.
- **Remove `api.sastaspace.com` from cloudflared** via `infra/cloudflared/remove-auth-ingress.sh` (≥7 days post Phase 3).
- **Remove `apps/notes/src/app/auth/callback/page.tsx`** and equivalent in typewars (`apps/typewars/src/app/auth/callback/`).
- **Add `register_owner_e2e` reducer** to `modules/sastaspace/src/lib.rs`. Unblocks `admin-panels.spec.ts` and `moderator.spec.ts` (finding #3 above — listed as Phase 4 follow-up in both spec files).
- **Write `STRUCTURE.md`** at repo root (spec acceptance criterion).
- **Add `.playwright-mcp/` to `.gitignore`**.
- **Move root `idea.md` and `SECURITY_AUDIT.md`** per spec Phase 4 outline.
- **Run `graphify update .`** to refresh the knowledge graph after deletions.

---

## Recommended next 5 actions

1. **Execute the LocalAI image swap on taxila** (Critical, unblocks Deck STDB). On taxila: `sed -i 's|localai/localai:latest|localai/localai:latest-aio-gpu-hipblas|' infra/docker-compose.yml`; add AMD GPU `devices: [/dev/kfd, /dev/dri]` mounts; `docker compose pull localai && docker compose up -d localai`; smoke-test `/v1/sound-generation`. This is the single highest-impact unblocked action — nothing else in Deck works without it.

2. **Add `register_owner_e2e` reducer to `modules/sastaspace/src/lib.rs`** (Critical, unblocks 3 blocked E2E specs). A ~10-line reducer that takes no args and calls `register_user` with `ctx.sender()` and `ctx.db`. Merge, regenerate bindings, flip `SKIP_PENDING_BOOTSTRAP_FIX = false` in `admin-panels.spec.ts` and `moderator.spec.ts`. This unblocks automated CI coverage for admin Comments, moderator verdicts, and signed-in comment submission.

3. **Run Phase 3 Section A6 staging gate on taxila** (High, closes the formal cutover debt). Follow `2026-04-26-stdb-native-phase3-cutover.md` §A6 steps 1–9: bring up staging compose with `profile=stdb-native` + all workers enabled, run `set_e2e_test_secret`, run the full Playwright matrix for both `E2E_AUTH_BACKEND=fastapi` and `=stdb`, append the result to `docs/audits/2026-04-26-phase3-staging-acceptance.md`. Until this is done, the cutover is not formally accepted per the spec's own acceptance criteria.

4. **Fix `E2E_DECK_FLOW` env var in CI or add a STDB-path deck smoke test** (High, prevents deck from being invisible in CI). Two options: (a) set `E2E_DECK_FLOW: stdb` in the `e2e` job's env block in `.github/workflows/deploy.yml:884-900` — but this requires the prod LocalAI to be working (action 1); or (b) add a minimal `FLOW=stdb` smoke test that only checks the plan step (Ollama is working) and skips the generate step when LocalAI is not yet ready. Without any deck test in CI, regressions are invisible.

5. **Fix auth-mailer reducer call shapes** (`workers/src/agents/auth-mailer.ts:98-101`). Replace positional `reducers.markEmailSent(row.id, ...)` and `reducers.markEmailFailed(row.id, ...)` with the SDK 2.1 object-literal shape from Appendix A: `await conn.reducers.markEmailSent({ id: row.id, providerMsgId: ... })`. Verify the actual generated binding accessor names against `packages/stdb-bindings/src/generated/`. Update the Vitest mock to match. Low effort, high confidence impact on email delivery reliability.
