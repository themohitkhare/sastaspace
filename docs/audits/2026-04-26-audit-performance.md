# Performance Audit — 2026-04-26

**Auditor:** performance
**Methodology:** Static analysis of the full monorepo. Read Next.js configs, package manifests, CSS files, React components, Rust reducer bodies, TypeScript worker agents, CI workflow YAML, and Docker configs. Checked subscription query shapes in all apps and workers, full-table `iter()` patterns in Rust, scheduler cadences, worker poll intervals, Docker layer ordering, CI matrix structure, and font/image loading strategies. No builds were run.
**Overall grade:** 7/10

The stack is architecturally sound for a low-traffic personal project. All four Next.js apps are static exports (zero SSR cost at runtime), the STDB release profile is well-tuned, the Dockerfile uses proper multi-stage layering, and the CI path cache is in place. The most material gap is a handful of full-table `iter()` scans in hot Rust reducers and one unfiltered full-table WebSocket subscription that leaks all User rows to a transient client — both are easy to fix.

---

## Frontend

| App | Estimated bundle | Heaviest deps | Likely Lighthouse perf | Top issue |
|---|---|---|---|---|
| landing | Small (~150 KB gzip est.) | `spacetimedb` SDK, design-tokens | 90–95 | `images: { unoptimized: true }` + full-table presence subscription |
| notes | Small (~180 KB gzip est.) | `spacetimedb` SDK, `next-mdx-remote`, `gray-matter` | 88–93 | Same `unoptimized` images; `next-mdx-remote` is client-side parsed |
| typewars | Medium (~320 KB gzip est.) | `spacetimedb` SDK + react hooks, `@sastaspace/typewars-bindings` | 80–88 | 250 ms WPM tick `setInterval` + full-table `user` subscription at login |
| admin | Small (~140 KB gzip est.) | `spacetimedb` SDK | 92–96 | `SELECT * FROM comment` (all statuses, all time) — fine for admin-only use |

### Bundle size

All four apps are `output: 'export'` (confirmed). Next.js static export produces no server-side runtime cost — pages are pre-rendered HTML + a client JS bundle. Bundle estimates are based on import graphs; no `.next/` directory exists in the worktree (no prior build).

**Landing** depends only on `spacetimedb` (~80 KB gzip for SDK v2.1) and the design-tokens CSS package. No Mastra, no heavy parsers.

**Notes** adds `next-mdx-remote` and `gray-matter`. These are used server-side during `next build` to parse MDX content, but `next-mdx-remote`'s client-side serialization module can add ~30–50 KB to the browser bundle depending on how imports are structured. Worth confirming via `next build --debug` or bundle analyzer.

**TypeWars** is the heaviest: it imports `spacetimedb/react` hooks + the generated `@sastaspace/typewars-bindings` barrel. The `spacetimedb` package ships CommonJS + ESM; Next.js tree-shaking should prune most of it, but the generated bindings barrel likely includes all table/reducer types even when only a subset are used.

**Admin** is minimal — no Tailwind (no `postcss.config.mjs` in package.json), only the STDB SDK.

### Image optimization

**Issue (medium):** All four `next.config.mjs` files set `images: { unoptimized: true }`. This was necessary for static export compatibility (Next.js Image Optimization API requires a Node server), but it means no WebP conversion, no responsive `srcset`, and no lazy-load blur placeholders from the framework. In practice the apps appear to have **no raster images at all** (no `.png`/`.jpg` found in `apps/`), so the cost is currently zero. However, the flag is a footgun — any future image upload will bypass optimization silently.

### Font loading

**Good.** All four apps use `next/font/google` with:
- `display: 'swap'` (prevents invisible text during font load)
- `variable` mode (CSS custom property, no class pollution)
- Minimal weight subsets (`400`, `500` only)

`landing/src/app/globals.css` also sets `body { font-display: swap; }` as a belt-and-suspenders fallback, though this is redundant with next/font's built-in `display: swap`. No preconnect/preload hints are manually added — next/font handles those automatically during static export.

**Minor issue:** The `typewars` `layout.tsx` omits the `weight` array for `Inter` (landing and notes specify `['400', '500']`). Without explicit weights, Google Fonts may serve all available weights, adding ~100–200 KB to the font transfer.

### Render performance

**Good practice in typewars:** `App.tsx`, `Battle.tsx`, `Leaderboard.tsx`, `MapWarMap.tsx` all use `useMemo` and `useCallback` appropriately. Query objects are memoized so the STDB subscription does not re-subscribe on every render.

**Battle WPM tick (minor issue):** `Battle.tsx` runs:
```js
const id = setInterval(() => setNow(Date.now()), 250);
```
This fires 4× per second and triggers a re-render of the entire `Battle` component tree every 250 ms during gameplay. The WPM display is the only consumer of `now`. If the word grid or contribution bar is expensive to diff (8 word cards with transition styles), this could cause perceptible jank. Mitigation: extract the WPM display into its own `React.memo`-wrapped component that receives `now` as a prop, so only that subtree re-renders.

**No virtualization needed** — the word grid is fixed at 8 cards, the leaderboard renders all players in a flat list (fine for a personal-scale game with hundreds of players, not thousands).

### STDB subscription patterns (frontend)

| Location | Query | Assessment |
|---|---|---|
| `landing/src/lib/spacetime.ts:59` | `SELECT * FROM presence` | OK — presence is a small table (~active sessions). Correct filtered approach for a presence counter. |
| `landing/src/app/lab/deck/deckStdbFlows.ts:137` | `SELECT * FROM plan_request WHERE submitter = X'...'` | Good — filtered by identity hex. |
| `landing/src/app/lab/deck/deckStdbFlows.ts:247` | `SELECT * FROM generate_job WHERE submitter = X'...'` | Good — filtered by identity hex. |
| `notes/src/lib/comments.ts:51` | `SELECT * FROM comment WHERE post_slug = '...' AND status = 'approved'` | Good — double-filtered. |
| `notes/src/lib/admin.ts:68` | `SELECT * FROM comment` | Expected for admin — intentionally fetches all statuses. |
| **`typewars/src/app/auth/verify/page.tsx:164`** | **`SELECT * FROM user`** | **CRITICAL — see below.** |

**Critical finding — full `user` table subscription at auth:**

```ts
.subscribe(["SELECT * FROM user"]);
```

This is called in the auth verify page as a fallback when `sessionStorage` doesn't have the pending email. It subscribes to **every User row in the sastaspace module** to find the one row belonging to the newly-minted identity. Because `User` is a `#[table(..., public)]` table that includes email addresses, this exposes **all registered users' emails** to the client for the duration of the verify page load (until `conn.disconnect()` is called after `onInsert` fires).

The comment in the code acknowledges this is a fallback path pending F1 landing. The correct fix is `SELECT * FROM user WHERE identity = X'<hex>'` — filtered by the target identity.

### CSS bundle

**Good** — all apps use Tailwind v4 which is entirely tree-shaken at build time (no runtime JS, no unused utilities in the output). The `@theme` block in `landing/globals.css` is minimal. No CSS-in-JS layer exists.

`typewars.css` grew with mobile breakpoints but is a single, well-structured flat file (539 lines). No duplication detected. The `backdrop-filter: blur(8px)` on `.topbar` can be GPU-expensive on older mobile hardware — the mobile `@media (max-width: 720px)` block doesn't disable it.

---

## Backend (Rust + workers)

### Rust module — release profile

**Excellent.** `modules/sastaspace/Cargo.toml`:
```toml
[profile.release]
opt-level = "z"   # size-optimize for WASM
lto = true        # cross-crate dead-code elimination
strip = true      # remove debug symbols
codegen-units = 1 # best optimization, single pass
```

This is an ideal WASM release profile. `opt-level = "z"` + `lto = true` + `codegen-units = 1` will produce the smallest, fastest module at the cost of longer compile times — which is acceptable for a CI build.

### Reducer hot paths (sastaspace module)

**Issue — `add_log_interest` full scan (`iter()`):**
```rust
let already = ctx
    .db
    .log_interest()
    .iter()
    .any(|r| r.container == container && r.subscriber == ctx.sender());
```
`log_interest` has `#[index(btree)]` on both `container` and `subscriber` separately. A compound equality check (both fields) can't use a single composite index, but it could use either index to narrow the scan. With 13 containers × N concurrent admin users, the table stays tiny in practice — but this is still an O(N) scan when O(1) is available. Fix: add a composite index on `(container, subscriber)` or use a `#[primary_key]` on the composite pair.

**Issue — `remove_log_interest` full scan:**
```rust
let to_delete: Vec<LogInterest> = ctx
    .db
    .log_interest()
    .iter()
    .filter(|r| r.container == container && r.subscriber == ctx.sender())
    .collect();
```
Same pattern. Same fix.

**Issue — `prune_log_events` is O(total_log_events × num_containers) every 60s:**
```rust
for container in ALLOWED_CONTAINERS.iter() {
    let mut rows: Vec<LogEvent> = ctx
        .db
        .log_event()
        .iter()
        .filter(|r| r.container == *container)
        .collect();
    ...
}
```
`log_event` has `#[index(btree)]` on `container`. This loop should use a **btree range filter** (`ctx.db.log_event().container().filter(container)`) instead of full-table `iter()` + client-side filter. With 13 containers × 500 rows cap each, the worst-case table is 6,500 rows scanned 13 times per tick = 84,500 row accesses every 60s. Small today, scales poorly.

**Issue — `session.rs:start_battle` full scan:**
```rust
let already_active = ctx
    .db
    .battle_session()
    .iter()
    .any(|s| s.player_identity == ctx.sender() && s.active);
```
`battle_session` has `#[index(btree)]` on `player_identity`. This should use `.player_identity().filter(ctx.sender())` and then check `.any(|s| s.active)` — O(sessions_per_player) instead of O(total_active_sessions_globally).

**Issue — `session.rs:auto_end_battle` full scan:**
```rust
let sessions: Vec<BattleSession> = ctx
    .db
    .battle_session()
    .iter()
    .filter(|s| s.player_identity == ctx.sender() && s.active)
    .collect();
```
Same as above — called on every disconnect event. Should use the `player_identity` btree index.

**Issue — `player.rs:register_player` full player table scan:**
```rust
let existing: Vec<String> = ctx
    .db
    .player()
    .iter()
    .map(|p| p.username.to_lowercase())
    .collect();
```
Called once per registration (low frequency) but does O(total_players) work. If `username` had a `#[unique]` index, this would be O(1). Adding `#[unique]` + `#[index(btree)]` on `username` would make this a simple `ctx.db.player().username().find(lower)`.

**Issue — `word.rs:submit_word` uses `iter()` not the session_id index:**
```rust
let hit: Option<Word> = ctx.db.word().iter().find(|w| {
    is_word_match(w.session_id, &w.text, ...)
});
```
`word` has `#[index(btree)]` on `session_id`. This is the **hottest reducer** (called on every keypress for every active player). It should use `ctx.db.word().session_id().filter(&session_id)` and then check text/expiry — O(words_in_session=8) instead of O(total_live_words_globally). With 100 concurrent players at 8 words each, that's 800 rows scanned per keypress.

**Issue — `word.rs:expire_words_tick` full scan at 2s cadence:**
```rust
let expired: Vec<Word> = ctx
    .db
    .word()
    .iter()
    .filter(|w| w.expires_at.to_micros_since_unix_epoch() <= ts_now)
    .collect();

let active: Vec<crate::session::BattleSession> = ctx
    .db
    .battle_session()
    .iter()
    .filter(|s| s.active)
    .collect();
```
This reducer fires **every 2 seconds** and does two full-table scans: all words + all battle sessions. With N active players, this is O(8N) + O(active_sessions) every 2s. A btree index on `expires_at` (or a scheduled-at-correct-time approach) would eliminate the first scan; the battle_session scan could be avoided with an indexed `active` column. At small scale (50 concurrent) this is ~400 row reads every 2s — manageable, but worth noting.

**Issue — `war.rs:global_war_tick` full region scan every 300s:**
```rust
let target = ctx
    .db
    .region()
    .iter()
    .filter(|r| r.controlling_legion >= 0)
    .min_by_key(|r| r.active_wardens);
```
25 regions total — trivially small. Fine as-is.

**Issue — `region.rs:region_tick` full region scan every 60s:**
```rust
let regions: Vec<Region> = ctx.db.region().iter().collect();
```
25 rows — negligible.

### Workers — poll intervals

**Admin-collector:**
- System metrics: `setInterval(..., 3_000)` — every 3s. This fires `upsertSystemMetrics` which calls `si.currentLoad()` (CPU sampling), `si.mem()`, `si.fsSize()`, `si.networkStats()`, `si.time()`, and optionally `nvidia-smi` / `rocm-smi`. On an idle server this is unnecessary CPU churn; consider backing off to 10–15s when the admin panel has no active connections.
- Container status: `setInterval(..., 15_000)` — every 15s. Calls `docker.listContainers` + `container.inspect()` + `container.stats()` for each container. 13 containers × 2 Docker API calls = 26 HTTP round-trips to the Docker socket every 15s. Fine for an admin panel, but the `stats({ stream: false })` call is a snapshot endpoint that blocks briefly.

**Worker subscriptions:**
- `auth-mailer`: `SELECT * FROM pending_email WHERE status = 'queued'` — filtered, correct.
- `moderator-agent`: `SELECT * FROM comment WHERE status = 'pending'` — filtered, correct.
- `deck-agent`: `SELECT * FROM plan_request WHERE status = 'pending'` + `SELECT * FROM generate_job WHERE status = 'pending'` — filtered, correct.
- `admin-collector`: `SELECT * FROM log_interest` — full-table, but `log_interest` is a small private table (13 containers × N admin users). Acceptable.

**tsx runtime compile at startup:** The workers Dockerfile runs TypeScript source via `tsx` at runtime (`--import tsx`). This adds ~200–400 ms of JIT compilation on every container restart. For production workers, compiling to `.js` during the Docker build would eliminate this latency. Tracked as known pattern in the Dockerfile comments.

### Heartbeat cadence

`landing/src/lib/spacetime.ts`:
```js
window.setInterval(tick, 20_000);
```
20s heartbeat for presence — reasonable. The reducer `heartbeat` only touches the caller's own row via primary key — O(1).

---

## CI / build

### Structure

The pipeline has 9+ jobs with smart `changes:` detection (skip unchanged areas). The matrix strategy (`build_variant: [legacy, stdb]`) doubles the build/test work for landing, notes, typewars, and admin apps on every push that touches those paths — two Next.js builds per app. This was intentional for Phase 3 preparation but adds ~4–8 min to CI wall time per push.

**Good:** `pnpm install --frozen-lockfile` is used everywhere — no lockfile drift.

**Good:** `Swatinem/rust-cache@v2` is present for both `module-gate` and `module-publish` — Cargo registry + build cache is preserved between runs.

**Good:** `pnpm install --frozen-lockfile --filter @sastaspace/workers...` in the `workers` CI job correctly uses workspace filtering.

### Docker layer caching

**Workers Dockerfile — good structure.** Layer order:
1. Copy workspace metadata + lockfile (rarely changes)
2. Copy `workers/package.json`, `workers/tsconfig.json` (changes only on dep update)
3. Copy `packages/stdb-bindings/package.json`, `packages/typewars-bindings/package.json`
4. `pnpm install --frozen-lockfile` (cached unless steps 1–3 change)
5. Copy source files (`workers/src`, `packages/*/src`)

This is correct: source changes do NOT invalidate the install layer. If `package.json` or `tsconfig.json` changes, the install re-runs from that point forward — expected.

**Minor:** The `build` stage compiles TypeScript (`pnpm build`) but the final image **does not use the compiled output** — it runs `tsx src/index.ts` directly. The `build` stage is unused in the final image, meaning ~60–120s of TypeScript compilation on every CI run produces an artifact that is discarded. Either use the compiled output in the final stage or remove the `build` stage.

### E2E tests

**`fullyParallel: false, workers: 1`** — all Playwright tests run serially against live prod. This is intentional (STDB state must be predictable) but means the e2e job is a long sequential chain. Estimated wall time: 10–15 min for the full spec suite. No obvious quick win here given the state dependency.

**Playwright runs headless Chromium** (no `--headed` in CI, `test:headed` is a local alias). Correct.

**`pnpm audit --prod --audit-level high` is `continue-on-error: true`** in both `landing-gate` and `workers` jobs. This means known moderate-severity advisories from `@mastra/core` transitive deps are silently ignored. The comment tracks this as a follow-up.

---

## Critical findings (anything that visibly hurts user experience)

### C1 — Full `user` table subscription leaks all emails to client

**File:** `apps/typewars/src/app/auth/verify/page.tsx:164`

```ts
.subscribe(["SELECT * FROM user"])
```

The `user` table is `public` and contains email addresses. Any browser opening the auth/verify page (including an attacker) will receive all registered users' emails via this subscription before `conn.disconnect()` is called. This is a data-leak vector masquerading as a fallback implementation detail.

**Fix:** Replace with `SELECT * FROM user WHERE identity = X'${targetHex}'` — one row, zero leakage.

### C2 — `submit_word` full-table scan on the hottest reducer path

**File:** `modules/typewars/src/word.rs:119`

```rust
let hit: Option<Word> = ctx.db.word().iter().find(|w| { ... });
```

Called on **every keypress** from every active player. With N=100 concurrent players each holding 8 live words, this scans 800 rows on every word submission. An indexed lookup by `session_id` would reduce this to ≤8 comparisons. At scale this saturates the STDB reducer queue.

**Fix:** `ctx.db.word().session_id().filter(&session_id).find(|w| w.text == word && w.expires_at.to_micros_since_unix_epoch() > ts_now)`

---

## High-priority findings

### H1 — `expire_words_tick` full scans every 2 seconds

**File:** `modules/typewars/src/word.rs:467–498`

Two full-table scans at a 2s tick cadence. As active player count grows, this becomes the dominant CPU consumer in the STDB scheduler. The `word` table already has a `session_id` btree index; an `expires_at` index would allow filtering expired words without scanning the whole table. The `battle_session` scan is unavoidable unless `active` is indexed.

### H2 — `start_battle` and `auto_end_battle` use full session table scans

**Files:** `modules/typewars/src/session.rs:40–41` and `89–94`

`battle_session` has a `player_identity` btree index. Both reducers should use `.player_identity().filter(ctx.sender())` instead of `iter()`.

### H3 — `register_player` scans all players to check username uniqueness

**File:** `modules/typewars/src/player.rs:63–68`

Add `#[unique]` + `#[index(btree)]` on `player.username` and replace the `iter()` collect with a direct indexed lookup.

---

## Medium / nice-to-have

### M1 — `typewars` layout omits `Inter` weight subset

`apps/typewars/src/app/layout.tsx`: `Inter({ subsets: ['latin'], variable: '--font-inter', display: 'swap' })` — no `weight` array. Specify `weight: ['400', '500']` to prevent Google Fonts from shipping the full variable font (~200 KB vs ~40 KB).

### M2 — `prune_log_events` O(N) scan inside 60s scheduled tick

**File:** `modules/sastaspace/src/lib.rs:1153–1158`

Use `ctx.db.log_event().container().filter(container)` (btree index on `container` exists) instead of full-table `iter()` + client-side filter.

### M3 — `add_log_interest` / `remove_log_interest` dual-field scan

**File:** `modules/sastaspace/src/lib.rs:1114–1136`

Low traffic (admin-only), but correctness: composite index on `(container, subscriber)` or a primary key on the pair would enable O(1) lookup.

### M4 — Admin-collector 3s metrics interval

**File:** `workers/src/agents/admin-collector.ts:17`

`METRICS_INTERVAL_MS = 3_000`. Consider backing off to 10s when `conn.db.logInterest.iter()` returns zero rows (no admin panel is watching). The admin panel is owner-only; metrics polling at 3s when nobody is looking is wasted CPU and STDB reducer calls (~1,200 `upsertSystemMetrics` calls per hour idle).

### M5 — Workers `build` Docker stage is unused

**File:** `workers/Dockerfile:29–31`

The `FROM workspace AS build` stage compiles TypeScript but the final image copies source and runs `tsx` — the compiled output is discarded. Either: (a) eliminate the build stage, or (b) use the compiled output in the final image (removing the `tsx` runtime dependency).

### M6 — `backdrop-filter: blur(8px)` on `.topbar` not disabled on mobile

**File:** `apps/typewars/src/styles/typewars.css:11`

The mobile `@media (max-width: 720px)` block doesn't disable `backdrop-filter`. This property triggers compositor layers and can cause dropped frames on mid-range Android devices. Consider `backdrop-filter: none` in the mobile breakpoint, or `@supports not (backdrop-filter: blur(1px)) { .topbar { background: rgba(245,241,232,0.95); } }`.

### M7 — `next-mdx-remote` client-side bundle in notes

**File:** `apps/notes/package.json`

`next-mdx-remote` ships a client-side bundle for hydration. If notes posts do not need client-side interactivity, switching to `compileMDX` (server-only) or raw `unified` pipeline during `next build` would remove the MDX runtime from the browser bundle entirely. Estimated saving: ~30–50 KB gzip.

### M8 — CI matrix doubles Next.js build time

The `landing`, `notes`, `typewars`, and `admin` jobs each run `matrix: build_variant: [legacy, stdb]`. Post-Phase 3 cutover, the `legacy` variant is only needed as a rollback artifact — it does not deploy. Consider adding `if: github.event_name == 'workflow_dispatch'` to the legacy build steps so normal pushes only build the stdb variant, halving the CI frontend build time.

### M9 — `images: { unoptimized: true }` is a footgun

All four apps. No images exist today, so no active cost. Document in a `CONTRIBUTING.md` note or `// @perf` comment that any future `<img>` or `<Image>` will bypass optimization and must use Cloudflare Images or an external CDN.

---

## Quick wins (1-line fixes worth >5% gain)

**QW1 — Fix `submit_word` btree lookup (biggest real gain):**
```rust
// Before
let hit: Option<Word> = ctx.db.word().iter().find(|w| is_word_match(...));

// After
let hit = ctx
    .db
    .word()
    .session_id()
    .filter(&session_id)
    .find(|w| w.text == word && w.expires_at.to_micros_since_unix_epoch() > ts_now);
```

**QW2 — Fix `start_battle` + `auto_end_battle` session lookup:**
```rust
// Before
ctx.db.battle_session().iter().filter(|s| s.player_identity == ctx.sender())

// After
ctx.db.battle_session().player_identity().filter(ctx.sender())
```

**QW3 — Fix user table subscription in auth/verify:**
```ts
// Before
.subscribe(["SELECT * FROM user"])

// After (pending email from sessionStorage is the preferred path; this is fallback-only)
.subscribe([`SELECT * FROM user WHERE identity = X'${target.toHexString()}'`])
```

**QW4 — Add Inter weight subset in typewars layout:**
```ts
Inter({ subsets: ['latin'], weight: ['400', '500'], variable: '--font-inter', display: 'swap' })
```

**QW5 — Fix `prune_log_events` to use btree index:**
```rust
// Before
ctx.db.log_event().iter().filter(|r| r.container == *container).collect()

// After (container btree index exists)
ctx.db.log_event().container().filter(container).collect()
```

---

## Recommended next 5 actions

1. **Fix `submit_word` indexed lookup (QW1)** — this is the single highest-impact backend change. Every keypress from every active player currently does a full-table scan of live words. The `session_id` btree index already exists; this is a 2-line change.

2. **Fix the `SELECT * FROM user` subscription (QW3)** — data-privacy critical. Replace with an identity-filtered query. The `sessionStorage` path (`PENDING_EMAIL_KEY`) is already the primary path; this subscription fires only in the edge-case fallback.

3. **Add `#[unique]` + `#[index(btree)]` on `player.username` and fix `register_player` (H3)** — eliminates a full player scan at registration. At 1,000 players this scans 1,000 rows on every registration call. A single Cargo.toml schema change + 2-line reducer change.

4. **Fix `expire_words_tick` `battle_session` scan and `word` expiry scan (H1)** — at 50 concurrent players this runs 400 word row reads + 50 session row reads every 2 seconds. Add `#[index(btree)]` on `word.expires_at` and filter there, or restructure to use `session_id()` index + per-session expiry checks.

5. **Remove the unused `build` Docker stage in `workers/Dockerfile` (M5) and fix CI legacy-variant builds (M8)** — immediately shaves CI wall time without any code logic changes. The build stage compiles TypeScript that is never used; removing it saves ~60–90s per workers build. The matrix fix saves a full second Next.js build per affected push.
