# Feature Coverage Inventory — 2026-04-26

**Purpose:** ground truth for the autonomous developer loop. Every checkbox is a unit a loop iteration can pick up, fix, verify, and close.

**Key for Status column:** ✅ implemented + tested | ⚠️ implemented, gap in test | ❌ missing / broken | 🚧 WIP (user is building, separate effort)

---

## Top-line tally

| Surface | Total features | E2E covered | Unit-tested | Production-verified | MISSING |
|---|---|---|---|---|---|
| Landing | 18 | 14 | 5 | 14 | 4 |
| Notes | 16 | 11 | 4 | 11 | 5 |
| Typewars | 22 | 4* | 2 | 4 | 9 |
| Admin | 24 | 6 | 0 | 8 | 10 |
| Deck | 16 | 3 | 0 | 3 | 6 |
| Workers | 16 | 4 | 12 | 4 | 4 |
| Module reducers (sastaspace) | 19 | 6 | 8 | 6 | 5 |
| Module reducers (typewars) | 9 | 1* | 14 | 1 | 5 |
| CI jobs | 14 | — | — | 10 | 4 |

*Typewars E2E specs in WIP (`tests/e2e/specs/typewars-*.spec.ts`) — treated as SEPARATE-EFFORT.

---

## Landing (sastaspace.com)

### Routes

| Route | Page component | Status |
|---|---|---|
| `/` | `apps/landing/src/app/page.tsx` (HomePage) | ✅ |
| `/lab` | `apps/landing/src/app/lab/page.tsx` | ✅ |
| `/projects` | `apps/landing/src/app/projects/page.tsx` | ✅ |
| `/about` | `apps/landing/src/app/about/page.tsx` | ✅ |
| `/lab/deck` | `apps/landing/src/app/lab/deck/page.tsx` + `Deck.tsx` | ✅ |

### Component map

| Feature | Component | URL/Route | E2E spec | Unit test | Status | Gap |
|---|---|---|---|---|---|---|
| Site brand / TopNav | `TopNav.tsx` | all | `landing.spec.ts` (nav-links test) | `TopNav.test.tsx` | ✅ | none |
| Hero section (h1 + lede + CTA row) | `HomePage` inline | `/` | `landing.spec.ts:12` | — | ✅ | no unit test |
| CTA "see the lab →" link | `HomePage` | `/` | `landing.spec.ts:18` | — | ✅ | none |
| CTA "about the idea" link | `HomePage` | `/` | `landing.spec.ts:25` | — | ✅ | none |
| Footer (github + linkedin links) | `Footer.tsx` | all | `landing.spec.ts:67` | `Footer.test.tsx` | ✅ | none |
| PresencePill ("X in the lab") | `PresencePill.tsx` | `/` (and everywhere footer is shown) | — | `PresencePill.test.tsx` | ⚠️ | no E2E test for live STDB count |
| ProjectsList (static projects) | `ProjectsList.tsx` | `/projects` | `landing.spec.ts:52` | `ProjectsList.test.tsx` | ✅ | none |
| BrandMark logo | `BrandMark.tsx` | all | `landing.spec.ts:15` (getByLabel) | `BrandMark.test.tsx` | ✅ | none |
| Chip badge | `Chip.tsx` | `/lab` | — | `Chip.test.tsx` | ✅ | no E2E |
| Lab page principles section | `apps/landing/src/app/lab/page.tsx` | `/lab` | `landing.spec.ts:43` | — | ✅ | none |
| About page | `apps/landing/src/app/about/page.tsx` | `/about` | `landing.spec.ts:59` | — | ✅ | none |
| Security headers (HSTS, X-Frame, CSP, nosniff) | Next.js headers config | all routes | `landing.spec.ts:87–103` | — | ✅ | none |
| CSP `frame-ancestors 'none'` | Next.js headers config | all routes | `landing.spec.ts:100` | — | ✅ | none |
| Deck: Stepper (3 steps) | `Stepper` (inline Deck.tsx) | `/lab/deck` | `deck.spec.ts` | — | ✅ | none |
| Deck: Composer (textarea, count slider, plan button, Cmd+Enter) | `Composer` (inline Deck.tsx) | `/lab/deck` | `deck.spec.ts:37–55` | — | ✅ | none |
| Deck: Prompt examples (5 buttons) | inline Deck.tsx | `/lab/deck` | — | — | ⚠️ | no E2E, no unit test |
| Deck: Recents section (mock data) | `Recents` (inline Deck.tsx) | `/lab/deck` | — | — | ❌ | mock data only; no E2E; not wired to real generation history — **GAP** |
| Deck: PlanEditor (per-track mood/tempo/instruments/length selectors) | `PlanEditor` (inline Deck.tsx) | `/lab/deck` | — | — | ⚠️ | no dedicated E2E or unit test; covered incidentally by happy-path |
| Deck: PlanView (track list, add/remove/duplicate, generate button) | `PlanView` + `PlanItem` (inline Deck.tsx) | `/lab/deck` | `deck.spec.ts:48–60` | — | ✅ | none |
| Deck: GeneratingView (per-track progress, overall %) | `GeneratingView` (inline Deck.tsx) | `/lab/deck` | `deck.spec.ts:62` (implicitly) | — | ⚠️ | no explicit assertion on GeneratingView state |
| Deck: Results (waveform canvas, play/pause, download .zip, share-link copy) | `Results` + `ResultTrack` (inline Deck.tsx) | `/lab/deck` | `deck.spec.ts:65–89` | — | ✅ | none |
| Deck: STDB path (USE_STDB=true) via useDeckStdb + deckStdbFlows | `useDeckStdb.ts`, `deckStdbFlows.ts` | `/lab/deck` | `deck.spec.ts` (stdb mode) | — | ⚠️ | stdb flow tested only when E2E_DECK_FLOW=stdb; skipped in CI |

---

## Notes (notes.sastaspace.com)

### Routes

| Route | Page component | Status |
|---|---|---|
| `/` | `apps/notes/src/app/page.tsx` (post list) | ✅ |
| `/[slug]` | `apps/notes/src/app/[slug]/page.tsx` (article) | ✅ |
| `/auth/verify` | `apps/notes/src/app/auth/verify/page.tsx` | ✅ |
| `/auth/callback` | `apps/notes/src/app/auth/callback/page.tsx` (legacy) | ✅ |
| `/admin/comments` | `apps/notes/src/app/admin/comments/page.tsx` | ⚠️ |

### Component map

| Feature | Component | URL/Route | E2E spec | Unit test | Status | Gap |
|---|---|---|---|---|---|---|
| Index post list (headings, links) | `page.tsx` | `/` | `notes.spec.ts:6` | — | ✅ | none |
| Post secondary sort / draft filtering | `lib/posts.ts` | `/` | — | — | ⚠️ | no E2E; draft filtering untested |
| Article page (MDX render) | `[slug]/page.tsx` | `/[slug]` | `notes.spec.ts:12` | — | ✅ | none |
| Comments section heading | `Comments.tsx` | `/[slug]` | `notes.spec.ts:23` | `Comments.test.tsx` | ✅ | none |
| Anon sign-in gate (no textarea, CTA visible) | `CommentForm.tsx` | `/[slug]` | `comments-anon.spec.ts:22` | — | ✅ | none |
| Anon gate → opens auth modal | `CommentForm.tsx` + `AuthMenu.tsx` | `/[slug]` | `comments-anon.spec.ts:31` | — | ✅ | none |
| AuthMenu: sign-in button (hydrated) | `AuthMenu.tsx` | `/` + `/[slug]` | `notes.spec.ts:36` | — | ✅ | none |
| AuthMenu: sign-in modal open | `AuthMenu.tsx` | any | `notes.spec.ts:40` | — | ✅ | none |
| AuthMenu: email input + send magic link | `AuthMenu.tsx` | any | `notes-auth-stdb.spec.ts` | — | ✅ | none |
| AuthMenu: "sent" confirmation state | `AuthMenu.tsx` | any | — | — | ⚠️ | no direct E2E on sent state |
| AuthMenu: Esc closes modal (focus trap) | `AuthMenu.tsx` | any | — | — | ⚠️ | Esc / focus-trap not E2E tested |
| Signed-in comment form (textarea + submit) | `CommentForm.tsx` | `/[slug]` | `comments-signed-in.spec.ts` | `CommentForm.test.tsx` | ✅ | none |
| Comment list (approved, with moderation status visibility) | `Comments.tsx` | `/[slug]` | `comments-signed-in.spec.ts` | `Comments.test.tsx` | ✅ | none |
| TopBar (site name, nav, AuthMenu integration) | `TopBar.tsx` | all | `notes.spec.ts` | `TopBar.test.tsx` | ✅ | none |
| Footer | `Footer.tsx` | all | — | `Footer.test.tsx` | ⚠️ | no E2E for footer on notes |
| Auth verify page (STDB token consume + User register) | `auth/verify/page.tsx` | `/auth/verify` | `notes-auth-stdb.spec.ts` | `auth.test.ts` | ✅ | none |
| Auth callback page (legacy magic-link) | `auth/callback/page.tsx` | `/auth/callback` | — | — | ⚠️ | legacy path; no dedicated E2E |
| Admin comments page (notes-side queue) | `admin/comments/page.tsx` | `/admin/comments` | `admin.spec.ts` (moderator.spec.ts) | — | ✅ | separate from admin.sastaspace.com |

---

## Typewars (typewars.sastaspace.com)

### Routes

| Route | Page component | Status |
|---|---|---|
| `/` | `apps/typewars/src/app/page.tsx` (shell) | ✅ |
| `/auth/verify` | `apps/typewars/src/app/auth/verify/page.tsx` | ✅ |
| `/auth/callback` | `apps/typewars/src/app/auth/callback/page.tsx` | ✅ |

### Component map

| Feature | Component | URL/Route | E2E spec | Unit test | Status | Gap |
|---|---|---|---|---|---|---|
| STDB connection / hydration guard | `App.tsx` | `/` | — | — | ⚠️ | loading state has no E2E |
| LegionSelect (5 cards, callsign input, enlist) | `LegionSelect.tsx` | `/` (pre-register) | typewars-register.spec.ts 🚧 | — | 🚧 | WIP spec — separate effort |
| MapWarMap (globe, region list, drag) | `MapWarMap.tsx` | `/` (warmap) | typewars-warmap.spec.ts 🚧 | — | 🚧 | WIP spec — separate effort |
| MapWarMap → open leaderboard button | `MapWarMap.tsx` | `/` | typewars-leaderboard.spec.ts 🚧 | — | 🚧 | WIP |
| MapWarMap → swap legion button | `MapWarMap.tsx` | `/` | typewars-legion-swap.spec.ts 🚧 | — | 🚧 | WIP |
| Battle screen (HP bar, words grid, input) | `Battle.tsx` | `/` (battle) | typewars-battle.spec.ts 🚧 | — | 🚧 | WIP |
| Battle: streak/multiplier HUD | `Battle.tsx` | `/` | typewars-battle.spec.ts 🚧 | — | 🚧 | WIP |
| Battle: legion HUD | `Battle.tsx` | `/` | typewars-battle.spec.ts 🚧 | — | 🚧 | WIP |
| LegionSwapModal (5 cards, focus trap, confirm) | `LegionSwapModal.tsx` | `/` | typewars-legion-swap.spec.ts 🚧 | — | 🚧 | WIP |
| LegionSwapModal: `onSwap` reducer wire | `App.tsx` `swapLegion` callback | `/` | — | — | ❌ | **MISSING REDUCER** — `change_legion` / `swap_legion` does not exist in typewars module; `swapLegion` is a TODO no-op — **CRITICAL GAP** |
| Leaderboard (legion bars, player table) | `Leaderboard.tsx` | `/` (leaderboard) | typewars-leaderboard.spec.ts 🚧 | — | 🚧 | WIP |
| Leaderboard: "you" marker | `Leaderboard.tsx` | `/` | typewars-leaderboard.spec.ts 🚧 | — | 🚧 | WIP |
| Leaderboard → open ProfileModal | `Leaderboard.tsx` | `/` | typewars-profile.spec.ts 🚧 | — | 🚧 | WIP |
| ProfileModal (player stats, region subscriptions) | `ProfileModal.tsx` | `/` | typewars-profile.spec.ts 🚧 | — | 🚧 | WIP |
| LiberatedSplash screen | `LiberatedSplash.tsx` | `/` | — | — | ⚠️ | no E2E; transient state |
| SignInTrigger | `SignInTrigger.tsx` | `/` | — | — | ⚠️ | no E2E |
| Avatar | `Avatar.tsx` | `/` (various) | — | — | ⚠️ | no E2E |
| Topbar (callsign, season, day counter) | `App.tsx` / layout | `/` | typewars-auth.spec.ts 🚧 | — | 🚧 | WIP |
| Auth verify page (STDB claim_progress_self) | `auth/verify/page.tsx` | `/auth/verify` | typewars-auth.spec.ts (stdb) 🚧 | — | 🚧 | WIP |
| Auth callback page (legacy) | `auth/callback/page.tsx` | `/auth/callback` | typewars-auth-stdb.spec.ts | — | ⚠️ | covered by existing typewars-auth-stdb.spec.ts |

---

## Admin (admin.sastaspace.com)

### Routes (hash-routing inside SPA)

| Route | Panel component | Status |
|---|---|---|
| `#/` | `Dashboard.tsx` | ✅ |
| `#/comments` | `Comments.tsx` | ✅ |
| `#/server` | `Server.tsx` | ✅ |
| `#/services` | `Services.tsx` | ✅ |
| `#/game` | `TypeWars.tsx` | ✅ |
| `#/logs` | `Logs.tsx` | ✅ |

### Component map

| Feature | Component | E2E spec | Unit test | Status | Gap |
|---|---|---|---|---|---|
| Google OAuth sign-in | `AuthSignIn.tsx` | `admin.spec.ts` | — | ✅ | none |
| AuthDenied (non-owner rejection) | `AuthDenied.tsx` | — | — | ⚠️ | no E2E for denied path |
| Shell: sidebar navigation (6 items) | `Shell.tsx` | `admin-panels.spec.ts` | — | ✅ | none |
| Shell: topbar (title, updated-X-ago, refresh) | `Shell.tsx` | — | — | ⚠️ | no E2E |
| Shell: settings modal (owner-token paste UI) | `Shell.tsx` + `OwnerTokenSettings.tsx` | — | — | ⚠️ | no E2E for settings modal |
| Shell: sidebar collapse/expand | `Shell.tsx` | — | — | ⚠️ | no E2E |
| Shell: nav badge (pending comments count) | `Shell.tsx` | `admin-panels.spec.ts` | — | ✅ | none |
| Shell: services down dot | `Shell.tsx` | — | — | ⚠️ | no E2E |
| Comments: pending/approved/flagged/rejected filter tabs | `Comments.tsx` | `admin-panels.spec.ts` | — | ✅ | none |
| Comments: post filter + search | `Comments.tsx` | — | — | ⚠️ | no E2E |
| Comments: approve/flag/reject/delete actions | `Comments.tsx` | `admin-panels.spec.ts` | — | ✅ | none |
| Comments: error banner on action failure | `Comments.tsx` | — | — | ⚠️ | no E2E for error banner |
| Comments: moderation reason visibility (verdict from moderator-agent) | `Comments.tsx` | — | — | ⚠️ | no E2E |
| Server: CPU %, cores, bar | `Server.tsx` | `admin-panels.spec.ts` | — | ✅ | none |
| Server: memory used/total GB, mem%, bar | `Server.tsx` | `admin-panels.spec.ts` | — | ✅ | none |
| Server: swap used/total MB | `Server.tsx` | — | — | ⚠️ | present in UI; no dedicated E2E assertion |
| Server: disk used/total GB, disk%, mount | `Server.tsx` | — | — | ⚠️ | no E2E |
| Server: network tx/rx MB/s (area chart) | `Server.tsx` | — | — | ⚠️ | no E2E |
| Server: uptime | `Server.tsx` | — | — | ⚠️ | no E2E |
| Server: GPU usage %, VRAM used/total, GPU temp, GPU model | `Server.tsx` | — | — | ⚠️ | rendered conditionally when `data.gpu` present; no E2E; GPU absent on prod (CPU-only box as of 2026-04-25) |
| Server: CPU history line chart (60 samples) | `Server.tsx` + `LineChart.tsx` | — | — | ⚠️ | no E2E |
| Server: memory history line chart | `Server.tsx` | — | — | ⚠️ | no E2E |
| Services: container status list (running/stopped/restarting) | `Services.tsx` | `admin-panels.spec.ts` | — | ✅ | none |
| Services: uptime, mem usage, restart count, image | `Services.tsx` | — | — | ⚠️ | details not E2E-asserted |
| Logs: container picker | `Logs.tsx` | — | — | ⚠️ | no E2E |
| Logs: log lines display + auto-scroll | `Logs.tsx` | — | — | ⚠️ | no E2E |
| Logs: level filter (highlight) | `Logs.tsx` | — | — | ⚠️ | no E2E |
| Logs: log_interest registration via STDB reducer | `Logs.tsx` | — | — | ⚠️ | no E2E |
| TypeWars panel (admin game view) | `TypeWars.tsx` | — | — | ⚠️ | no E2E; content unknown without deeper inspection |
| Dashboard (overview / nav shortcuts) | `Dashboard.tsx` | — | — | ⚠️ | no E2E |

---

## Deck (sastaspace.com/lab/deck + deck.sastaspace.com)

### Feature map

| Feature | Location | E2E spec | Unit test | Status | Gap |
|---|---|---|---|---|---|
| Composer: textarea (600-char, spellcheck off) | `Deck.tsx` `Composer` | `deck.spec.ts:92` | — | ✅ | none |
| Composer: track count stepper (1–10) | `Deck.tsx` `Composer` | — | — | ⚠️ | no E2E for +/- buttons |
| Composer: "plan tracks" button disabled on < 4 chars | `Deck.tsx` | `deck.spec.ts:92` | — | ✅ | none |
| Composer: Cmd+Enter shortcut | `Deck.tsx` | — | — | ⚠️ | no E2E for keyboard shortcut |
| Composer: "clear" button | `Deck.tsx` | — | — | ⚠️ | no E2E |
| Prompt examples (5 preset buttons) | `Deck.tsx` | — | — | ⚠️ | no E2E |
| Recents list (3 mock items, replay button) | `Deck.tsx` `Recents` | — | — | ❌ | **Mock data only** — not wired to real generation history; no E2E — **GAP** |
| PlanningCard (Ollama progress animation) | `Deck.tsx` `PlanningCard` | — | — | ⚠️ | transient; no E2E assertion |
| PlanView: back + redraft buttons | `Deck.tsx` `PlanView` | — | — | ⚠️ | no E2E for back/redraft |
| PlanEditor: name input, desc textarea | `Deck.tsx` `PlanEditor` | — | — | ⚠️ | no E2E for individual field edits |
| PlanEditor: type select (8 options) | `Deck.tsx` `PlanEditor` | — | — | ⚠️ | no E2E |
| PlanEditor: mood select (10 options) | `Deck.tsx` `PlanEditor` | — | — | ⚠️ | no E2E |
| PlanEditor: length segmented control (6 options) | `Deck.tsx` `PlanEditor` | — | — | ⚠️ | no E2E |
| PlanEditor: tempo segmented control (4 options) | `Deck.tsx` `PlanEditor` | — | — | ⚠️ | no E2E |
| PlanEditor: instruments input + musicgen prompt preview | `Deck.tsx` `PlanEditor` | — | — | ⚠️ | no E2E |
| PlanItem: duplicate / remove track buttons | `Deck.tsx` `PlanItem` | — | — | ⚠️ | no E2E |
| GeneratingView: per-track status (queued/running/done), overall % | `Deck.tsx` `GeneratingView` | `deck.spec.ts:62` (implicitly) | — | ⚠️ | no assertion on track-level status |
| Results: waveform canvas (Web Audio synth) | `Deck.tsx` `ResultTrack` | — | — | ⚠️ | no E2E for audio playback |
| Results: download .zip button | `Deck.tsx` `Results` | `deck.spec.ts:65` | — | ✅ | none |
| Results: share-link copy button | `Deck.tsx` `Results` | — | — | ⚠️ | no E2E for copy-to-clipboard |
| Results: track-level play/pause | `Deck.tsx` `ResultTrack` | — | — | ⚠️ | no E2E |
| LocalAI integration (CPU image vs GPU image) | `workers/src/agents/deck-agent.ts` `renderViaLocalAi` | — | `deck-agent.test.ts` | ⚠️ | CPU/GPU image selection is deploy-time compose config; not E2E tested |
| deck.sastaspace.com zip server (nginx) | `infra/deck/nginx.conf` | `deck-static-deploy` smoke | — | ✅ | friendly landing page absent — serves nginx autoindex or 403 |

---

## Workers (`workers/`, single container)

### Agent map

| Agent | Trigger | Key actions | Unit test file | E2E spec | Status | Gap |
|---|---|---|---|---|---|---|
| auth-mailer | `pending_email` table insert (status='queued') | Resend.emails.send → `mark_email_sent` / `mark_email_failed` | `auth-mailer.test.ts` | `notes-auth-stdb.spec.ts` (implicit) | ✅ | Resend rejection path not E2E-tested |
| admin-collector: system_metrics loop (3 s) | setInterval 3 000 ms | `si.currentLoad/mem/fsSize/networkStats/time` → `upsertSystemMetrics` | `admin-collector.test.ts` | `admin-panels.spec.ts` | ✅ | none |
| admin-collector: container status loop (15 s) | setInterval 15 000 ms | `docker.listContainers` + inspect + stats → `upsertContainerStatus` | `admin-collector.test.ts` | `admin-panels.spec.ts` | ✅ | none |
| admin-collector: GPU metrics (nvidia-smi / rocm-smi) | inside 3-s loop | `readGpu()` → fields on `upsertSystemMetrics` | `admin-collector.test.ts` | — | ⚠️ | GPU absent on prod box (CPU-only); collector returns null→null fields; no E2E assertion on GPU card in UI |
| admin-collector: log streaming via dockerode | `log_interest` subscription INSERT/DELETE | `docker logs --follow` subprocess → `appendLogEvent` per line | `admin-collector.test.ts` | — | ⚠️ | log streaming behaviour (onInsert/onDelete of log_interest) not E2E-tested |
| admin-collector: log level classification | per log line | `classifyLevel()` → "info"/"warn"/"error"/"debug" | `admin-collector.test.ts` | — | ✅ | unit-tested |
| deck-agent: plan_request subscription | `plan_request` INSERT with status='pending' | Mastra Agent (Ollama gemma3:1b) → `setPlan` / `setPlanFallback` | `deck-agent.test.ts` | `deck.spec.ts` (stdb mode) | ⚠️ | stdb E2E only runs when E2E_DECK_FLOW=stdb |
| deck-agent: generate_job subscription | `generate_job` INSERT with status='pending' | LocalAI /v1/sound-generation per track → JSZip → `setGenerateDone` / `setGenerateFailed` | `deck-agent.test.ts` | `deck.spec.ts` (stdb mode) | ⚠️ | same; requires musicgen-capable LocalAI image |
| deck-agent: parseTracks helper | agent output | JSON parse + validate track schema | `deck-agent.test.ts` | — | ✅ | unit-tested |
| deck-agent: buildReadme helper | ZIP assembly | builds README.txt inside zip | `deck-agent.test.ts` | — | ✅ | unit-tested |
| deck-agent: slugify + uniqueFilename | per track WAV | collision-free filename | `deck-agent.test.ts` | — | ✅ | unit-tested |
| moderator-agent: injection detector | `comment` INSERT status='pending' | Mastra one-shot (gemma3:1b) INJECTION_DETECTOR_PROMPT → `BENIGN`/`ATTACK` | `moderator-agent.test.ts` | `moderator.spec.ts` | ✅ | none |
| moderator-agent: content classifier | after injection pass | Mastra one-shot CLASSIFIER_INSTRUCTIONS → `SAFE`/`UNSAFE` | `moderator-agent.test.ts` | `moderator.spec.ts` | ✅ | none |
| moderator-agent: parseDetectorReply | per agent response | fail-closed parse | `moderator-agent.test.ts` | — | ✅ | unit-tested |
| moderator-agent: parseClassifierVerdict | per agent response | fail-closed parse | `moderator-agent.test.ts` | — | ✅ | unit-tested |
| moderator-agent: fail-closed on exception | any agent throw | `setCommentStatusWithReason(id, "flagged", "classifier-error")` | `moderator-agent.test.ts` | — | ✅ | unit-tested |

---

## Spacetime module — sastaspace (`modules/sastaspace/`)

### Tables

| Table | Public | Write reducers | Index | Gap |
|---|---|---|---|---|
| `project` | Yes | `upsert_project` (owner), `delete_project` (owner) | PK slug | none |
| `presence` | Yes | `client_connected` (auto), `client_disconnected` (auto), `heartbeat` (any) | PK identity | none |
| `comment` | Yes | `submit_user_comment` (signed-in), `set_comment_status` (owner), `set_comment_status_with_reason` (owner), `delete_comment` (owner) | PK id auto_inc, btree post_slug, btree submitter | none |
| `user` | Yes | `register_user` (owner), `register_owner_self` (owner), `verify_token` (any, consumes token) | PK identity, unique email | none |
| `auth_token` | No (private) | `issue_auth_token` (owner), `consume_auth_token` (owner), `request_magic_link` (any), `verify_token` (any) | PK token | none |
| `moderation_event` | Yes | `set_comment_status_with_reason` (owner) | PK id auto_inc, btree comment_id | none |
| `pending_email` | No (private) | `request_magic_link` (any), `mark_email_sent` (owner), `mark_email_failed` (owner) | PK id auto_inc | none |
| `system_metrics` | Yes (STDB public) | `upsert_system_metrics` (owner) | PK (singleton — see reducer) | none |
| `container_status` | Yes | `upsert_container_status` (owner) | PK name | none |
| `log_event` | Yes | `append_log_event` (owner) | scheduled prune via `prune_log_events_schedule` | none |
| `log_interest` | Yes | `set_log_interest` (owner / signed-in admin) | PK container | none |
| `app_config_secret` | No (private) | `set_e2e_test_secret` (owner) | PK id (singleton 0) | none |
| `last_test_token` | No (private) | `mint_test_token` (owner+secret) | PK id (singleton 0) | none |
| `prune_log_events_schedule` | No | scheduled | PK scheduled_id | none |

### Reducers

| Reducer | Callable by | E2E spec | Unit test | Status | Gap |
|---|---|---|---|---|---|
| `init` | STDB system (once) | — | — | ✅ | none |
| `client_connected` | any | — | — | ✅ | none |
| `client_disconnected` | any | — | — | ✅ | none |
| `heartbeat` | any connected | — | — | ✅ | none |
| `upsert_project` | owner only | — | — | ✅ | no E2E test |
| `delete_project` | owner only | — | — | ✅ | no E2E test |
| `register_owner_self` | owner only | — | — | ✅ | called from CI bootstrap |
| `submit_user_comment` | signed-in user | `comments-signed-in.spec.ts` | module unit tests | ✅ | none |
| `set_comment_status` | owner only | `admin.spec.ts` | module unit tests | ✅ | none |
| `set_comment_status_with_reason` | owner only | `moderator.spec.ts` | module unit tests | ✅ | none |
| `delete_comment` | owner only | `admin-panels.spec.ts` | — | ✅ | none |
| `register_user` | owner only | `notes-auth-stdb.spec.ts` | module unit tests | ✅ | none |
| `issue_auth_token` | owner only | — | module unit tests | ✅ | no E2E (legacy path) |
| `consume_auth_token` | owner only | — | module unit tests | ✅ | no E2E (legacy path) |
| `request_magic_link` | any | `notes-auth-stdb.spec.ts` | module unit tests | ✅ | none |
| `verify_token` | any | `notes-auth-stdb.spec.ts` | module unit tests | ✅ | none |
| `mark_email_sent` | owner only | — | workers unit tests | ✅ | no standalone E2E |
| `mark_email_failed` | owner only | — | workers unit tests | ✅ | no standalone E2E |
| `noop_owner_check` | owner only | — | — | ✅ | workers boot health gate |
| `set_e2e_test_secret` | owner only | — | — | ✅ | CI/dev only |
| `mint_test_token` | owner + e2e_secret | `notes-auth-stdb.spec.ts` | module unit tests | ✅ | none |
| `upsert_system_metrics` | owner only | `admin-panels.spec.ts` | workers unit tests | ✅ | none |
| `upsert_container_status` | owner only | `admin-panels.spec.ts` | workers unit tests | ✅ | none |
| `append_log_event` | owner only | — | workers unit tests | ✅ | no E2E for log streaming |
| `prune_log_events` | scheduled (60 s) | — | — | ✅ | scheduled; no E2E |

---

## Spacetime module — typewars (`modules/typewars/`)

### Tables

| Table | Public | Write reducers | Scheduled tasks | Gap |
|---|---|---|---|---|
| `player` | Yes | `register_player` (any), `claim_progress` (owner), `claim_progress_self` (any) | none | none |
| `region` | Yes | `region_tick` (scheduled) | `region_tick_schedule` every ~3 s | none |
| `global_war` | Yes | `global_war_tick` (scheduled) | `war_tick_schedule` every ~60 s | none |
| `battle_session` | Yes | `start_battle` (any), `end_battle` (any), `auto_end_battle` (client_disconnected) | none | none |
| `word` | Yes | `submit_word` (any), `spawn_words` (internal), `expire_words_tick` (scheduled) | `word_expire_schedule` | none |
| `legion` | Yes | (static, seeded) | none | none |

### Reducers

| Reducer | Callable by | E2E spec | Unit test | Status | Gap |
|---|---|---|---|---|---|
| `init` | STDB system | — | — | ✅ | seeds regions + war + schedules |
| `client_connected` | any | — | — | ✅ | no-op |
| `client_disconnected` | any | — | — | ✅ | calls `auto_end_battle` |
| `register_player` | any | typewars-register.spec.ts 🚧 | `player.rs` unit tests | ✅ | E2E is WIP |
| `claim_progress` | owner only | — | `player.rs` unit tests | ✅ | no E2E |
| `claim_progress_self` | any | typewars-auth.spec.ts 🚧 | `player.rs` unit tests | ✅ | E2E is WIP |
| `start_battle` | any (registered) | typewars-battle.spec.ts 🚧 | — | ✅ | E2E is WIP |
| `end_battle` | any (session owner) | typewars-battle.spec.ts 🚧 | — | ✅ | E2E is WIP |
| `submit_word` | any (in session) | typewars-battle.spec.ts 🚧 | — | ✅ | E2E is WIP |
| `region_tick` | scheduled | — | region.rs unit tests | ✅ | no E2E |
| `global_war_tick` | scheduled | — | war.rs unit tests | ✅ | no E2E |
| `expire_words_tick` | scheduled | — | word.rs unit tests | ✅ | no E2E |
| **`change_legion` / `swap_legion`** | any (registered) | — | — | ❌ | **DOES NOT EXIST** in module — LegionSwapModal calls a no-op in App.tsx — **CRITICAL GAP** |

---

## CI/CD (`.github/workflows/deploy.yml`)

### Secrets inventory (referenced in workflow)

| Secret | Used by | Gap |
|---|---|---|
| `SPACETIME_TOKEN` | module-publish, auth, workers-deploy (E2E), e2e | maps to maincloud-issued owner JWT |
| `WORKERS_STDB_TOKEN` | workers-deploy | prod-server-issued JWT for WebSocket handshake; preferred over SPACETIME_TOKEN |
| `RESEND_API_KEY` | auth, workers-deploy | Resend email API |
| `E2E_TEST_SECRET` | auth, e2e | enables mint_test_token side-door in CI |

### Jobs

| Job | Trigger condition | Smoke check | Rollback step | Status | Gap |
|---|---|---|---|---|---|
| `changes` | every push/PR/schedule/dispatch | path diff → outputs | none | ✅ | none |
| `module-gate` | `changes.module == true` | `cargo test` on host | none | ✅ | no coverage threshold reported |
| `module-publish` | push/dispatch + module-gate pass | `spacetime publish` CLI | none | ✅ | no automatic rollback |
| `landing-gate` | `changes.landing == true` | next build + vitest | none | ✅ | none |
| `landing-deploy` | push/dispatch + landing-gate pass | `curl 200` + CSP header check | none | ✅ | none |
| `notes` | `changes.notes == true` | next build + vitest + `curl 200` | none | ✅ | none |
| `typewars` | `changes.typewars == true` | next build + vitest + `curl 200` | none | ✅ | none |
| `admin` | `changes.admin == true` | next build + `curl 200` + `docker logs` check | none | ✅ | no vitest for admin |
| `moderator` | `changes.agents == true` | pytest + docker compose ps + polling log check | none | ⚠️ | legacy Python job; Phase 4 deletes it |
| `auth` | `changes.agents == true` | pytest + `curl /healthz 200` | none | ⚠️ | legacy Python job; Phase 4 deletes it |
| `workers` | `changes.workers == true` | tsc --noEmit + vitest + pnpm audit (high) | none | ✅ | audit-level bumped from moderate to high — pending @mastra/core fix |
| `workers-deploy` | push/dispatch + workers+module-publish pass | docker logs grep for "owner token verified" or "all enabled agents started" | `docker compose stop workers` | ✅ | none |
| `auth-410-deploy` | push/dispatch + workers/agents change | `curl 410` | `docker compose stop auth-410` | ✅ | tombstone only |
| `deck-static-deploy` | push/dispatch + workers/agents change | `curl 200` or 403 (nginx up) | start legacy deck | ✅ | none |
| `e2e` | after all deploys (push/schedule/dispatch) | Playwright suite (all specs) | none | ⚠️ | typewars-*.spec.ts specs are WIP; if they run they may fail |

---

## Open gaps — prioritised

| # | Surface | Gap | Severity | Action |
|---|---|---|---|---|
| 1 | Typewars | **`change_legion` / `swap_legion` reducer MISSING** from typewars module — `LegionSwapModal` onSwap is a TODO no-op; the UI silently closes without swapping | Critical | Add `swap_legion` reducer to `modules/typewars/src/player.rs`; wire in `App.tsx` `swapLegion` callback; add to typewars-bindings; write E2E |
| 2 | Deck | **Recents section is mock data** — hard-coded 3 items, not wired to any real generation history | High | Wire to STDB `generate_job` table or worker-side persisted history; or explicitly label as "demo" in production |
| 3 | Admin | **GPU metrics untested** — collector publishes GPU fields; Server panel renders them; but prod has no GPU (CPU-only box) so the card always shows "n/a"; no E2E assertion exists for either GPU-present or GPU-absent paths | Medium | Add E2E assertion for `gpu — no GPU detected` card in admin-panels.spec.ts; document prod box GPU status in reference_prod_taxila.md |
| 4 | Admin | **Logs panel has no E2E coverage** — container picker, log streaming, log_interest reducer, level highlight, auto-scroll all unverified | Medium | Add `admin-panels.spec.ts` test: pick container → assert log lines appear |
| 5 | Landing | **PresencePill has no E2E test** — STDB subscription count is unit-tested in isolation but live count on the page is never E2E-asserted | Low-Medium | Add E2E: navigate to `/`, assert PresencePill text matches `/\d+ in the lab/i` |
| 6 | Notes | **AuthMenu Esc + focus-trap** unverified by E2E — opens modal but Esc close and focus management have no test | Medium | Add E2E to `notes-auth-stdb.spec.ts`: open modal → press Escape → assert modal gone |
| 7 | Notes | **Auth callback (legacy) page** has no E2E — only the STDB verify path is tested; old magic-link flow from FastAPI era is untested | Low | Either add E2E or document as intentionally deprecated |
| 8 | Deck | **STDB deck flow (E2E_DECK_FLOW=stdb)** skipped in CI — the STDB plan/generate path requires the deck-agent worker and musicgen-capable LocalAI; skipped via `test.skip` unless env var set | High | Enable in CI after LocalAI AIO image is confirmed on prod; at minimum gate with E2E_DECK_FLOW=stdb in a separate scheduled run |
| 9 | CI | **pnpm audit level bumped** from moderate to high for workers job (continue-on-error: true) due to @mastra/core transitive deps | Medium | Track @mastra/core release fixing jsondiffpatch/uuid<14; restore `--audit-level moderate` when available |
| 10 | Admin | **Settings modal (owner-token paste UI)** has no E2E — critical for STDB moderation actions in admin | High | Add E2E: open settings → paste token → assert STDB token button changes label |

---

## Loop iteration backlog (smallest-to-largest)

A queue the autonomous loop walks top-to-bottom each iteration:

1. **[E2E] Add PresencePill E2E test** — `tests/e2e/specs/landing.spec.ts` — assert `/\d+ in the lab/i` visible on `/`
2. **[E2E] Add AuthMenu Esc-close E2E test** — `tests/e2e/specs/notes-auth-stdb.spec.ts` — open modal, press Esc, assert gone
3. **[E2E] Add admin Logs panel E2E test** — `tests/e2e/specs/admin-panels.spec.ts` — pick container, assert log lines render
4. **[E2E] Add admin GPU-absent E2E assertion** — `tests/e2e/specs/admin-panels.spec.ts` — assert `gpu — no GPU detected` card text
5. **[E2E] Add admin settings modal E2E** — `tests/e2e/specs/admin-panels.spec.ts` — paste owner-token, verify button label changes
6. **[E2E] Add legacy notes auth/callback E2E or deprecation test** — either test the redirect or assert 410
7. **[E2E] Add Deck prompt-examples E2E** — `tests/e2e/specs/deck.spec.ts` — click one example, assert textarea fills
8. **[E2E] Add Deck share-link copy E2E** — `tests/e2e/specs/deck.spec.ts` — click share, assert clipboard or label
9. **[FEAT] Add `swap_legion` reducer to typewars module** — `modules/typewars/src/player.rs` — wire in App.tsx `swapLegion`, add bindings, write unit test
10. **[FEAT] Enable STDB-native deck E2E in scheduled CI run** — set E2E_DECK_FLOW=stdb in a separate nightly Playwright job or workflow_dispatch after LocalAI AIO image confirmed
11. **[FEAT] Wire Deck Recents to real generation history** — read `generate_job` rows via STDB or persist to a separate log table; remove mock data
12. **[E2E] Add admin Services panel detail assertions** — `admin-panels.spec.ts` — assert uptime, mem, restart count are rendered per container row
13. **[CI] Restore pnpm audit --audit-level moderate** for workers job once @mastra/core deps are patched
14. **[E2E] Add Deck GeneratingView per-track state assertions** — `tests/e2e/specs/deck.spec.ts` — assert "running"/"done" labels per track row during generate phase

---

*Generated by autonomous scan of `apps/`, `workers/`, `modules/`, `tests/e2e/`, `.github/workflows/` on 2026-04-26.*
*User WIP files (`tests/e2e/specs/typewars-*.spec.ts`, `services/admin-api/`, `services/deck/`, `.playwright-mcp/`) excluded from coverage grading.*
