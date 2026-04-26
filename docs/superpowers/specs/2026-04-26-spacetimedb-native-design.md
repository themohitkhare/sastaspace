# SpacetimeDB-Native Rewire

**Date:** 2026-04-26
**Status:** Draft — awaiting owner review
**Supersedes:** `2026-04-26-admin-realdata-design.md` (the FastAPI admin-api path)
**Related audit:** `docs/audits/2026-04-26-structure-audit.md` (H1, H3, H4 are obsoleted by this spec)

---

## Problem

The repo has 5 runtimes (Rust modules, 4 Python services, TypeScript apps, nginx, bash) and three different "ways to write a backend" (Rust reducer, Python FastAPI, frontend-direct STDB call). Two more Python services (`services/admin-api/`, `services/deck/`) are mid-implementation and about to land. AI-assisted development is harder when each new feature has to choose a runtime, a service shape, and a place to live.

The owner's goal: **collapse to the smallest stack that an AI can confidently maintain** — preferably one language for application code, one place for business logic, one pattern for backend work.

Self-hosting is a hard constraint. Everything must run on the existing `taxila` GPU box (Ollama is already there) — no paid APIs.

---

## Goal

After the rewire:

- **Zero Python files in the project source tree.** Application code is TypeScript (frontends + workers) and Rust (SpacetimeDB modules).
- **All business logic lives in SpacetimeDB reducers.** External I/O (email, model calls, host metrics) lives in tiny TS workers that subscribe to STDB tables and shuttle bytes — they hold no logic.
- **One pattern for every backend feature.** Frontend calls reducer → reducer writes intent row → worker does I/O → worker calls reducer with result → frontend sees result via subscription.
- **Existing E2E surface unchanged.** Users see the same product. No URL changes (except `api.sastaspace.com` is removed). No auth flow changes for end users.

---

## Architecture (target end-state)

```
GPU box (taxila):
  ollama       :11434   text LLMs (existing — unchanged)
  localai      :8080    NEW — MusicGen + future audio backends (Go binary, OpenAI API)
  spacetime    :3100    DB + business logic (existing — expanded with new tables/reducers)
  workers      :—       NEW — single Node process running 4 Mastra agents
  cloudflared  :—       tunnels (existing — one ingress dropped)

Cloudflare:
  sastaspace.com           → apps/landing/   (nginx, static)
  notes.sastaspace.com     → apps/notes/     (nginx, static)
  admin.sastaspace.com     → apps/admin/     (nginx, static)
  typewars.sastaspace.com  → apps/typewars/  (nginx, static)
  stdb.sastaspace.com      → spacetime container
  api.sastaspace.com       → DELETED (no admin-api proxy any more)
```

---

## Repo layout (target)

```
sastaspace/
├── apps/                      # User-facing Next.js (existing, modest changes)
│   ├── admin/                 # Google Sign-In retained; STDB direct + new tables
│   ├── landing/               # Lab/deck calls reducers instead of HTTP
│   ├── notes/                 # Auth callback page now does the verify locally
│   └── typewars/              # Auth callback page now does the verify locally
│
├── workers/                   # NEW — one Node process, multiple Mastra agents
│   ├── package.json
│   ├── Dockerfile
│   └── src/
│       ├── index.ts           # boot all agents
│       ├── shared/
│       │   ├── stdb.ts        # @clockworklabs/spacetimedb-sdk wiring
│       │   ├── mastra.ts      # Mastra instance + provider config
│       │   └── env.ts         # typed env loader (zod)
│       └── agents/
│           ├── auth-mailer.ts
│           ├── admin-collector.ts
│           ├── deck-agent.ts
│           └── moderator-agent.ts
│
├── modules/                   # RENAMED from module/ + game/ (audit H2)
│   ├── sastaspace/            # was module/ — Rust STDB module (expanded)
│   └── typewars/              # was game/ — Rust STDB module (untouched)
│
├── packages/                  # Existing TS libs
│   ├── design-tokens/
│   ├── stdb-bindings/         # ★ regenerated after new tables/reducers land
│   ├── typewars-bindings/
│   └── auth-ui/               # SignInModal: small refactor, calls reducer directly
│
├── infra/
│   ├── docker-compose.yml     # ★ rewritten — drops 4 Python services, adds localai + workers
│   ├── cloudflared/           # api.sastaspace.com ingress removed
│   ├── localai/               # NEW — config + model preload script
│   ├── README.md              # Updated: ollama + localai install on taxila
│   └── (nginx configs per app — unchanged)
│
├── docs/
│   ├── superpowers/specs/     # this spec lives here
│   └── audits/                # existing audits
│
├── tests/
│   └── e2e/                   # existing Playwright suite — expanded per phase
│
├── services/                  # ❌ DELETED in cleanup phase
└── infra/agents/              # ❌ DELETED in cleanup phase (moderator was here)
```

---

## What gets added to the SpacetimeDB module

All in `modules/sastaspace/src/lib.rs`. No tables/reducers added to `modules/typewars/`.

### New tables

| Table | Purpose | Visibility | Approx churn |
|---|---|---|---|
| `pending_email` | One row per outbound email (magic-link, future broadcasts). Worker drains, calls `mark_email_sent` on success or `mark_email_failed` on failure. | private | low (one per sign-in) |
| `system_metrics` | One-row rolling table (id=0) with current CPU/mem/disk/net/GPU snapshot. Collector overwrites every 3 s. | public-read (admin only via row-level filter) | constant 1 row |
| `container_status` | One row per known container with status/uptime/mem. Collector upserts every 15 s. | public-read | ~10 rows |
| `log_interest` | One row per (container, subscriber identity). Created when admin Logs panel mounts, deleted on unmount. Worker only follows logs for containers with interest. | private | sparse |
| `log_event` | Ring-buffer of recent log lines (cap 500 per container, evicted by scheduled reducer). | public-read | bursty but bounded |
| `plan_request` | Deck plan requests. Status: pending/done/failed. | public-read by submitter | one per /lab/deck submit |
| `generate_job` | Deck audio render jobs. Status: pending/done/failed. Stores result URL when done. | public-read by submitter | one per generate |
| `app_config` | Static config the workers need to read (callback URLs, rate limits, etc.). One row, owner-writable. | public-read | static |

### New reducers

Logic that previously lived in Python services moves here. Names match what they replace.

**Email/auth (replaces `services/auth/main.py`):**
- `request_magic_link(email, app, prev_identity?, callback_url)` — validates email, generates token, inserts `auth_token` + `pending_email` rows in one transaction
- `verify_token(token, display_name)` — atomic: validates token + expiry + not-already-used, marks used, looks up email from `auth_token`, registers `User` row keyed by `ctx.sender()`. Replaces the multi-step Python flow (consume → SQL lookup → register) with one reducer call. For typewars, a parallel `verify_token_typewars(token, prev_identity_hex, display_name)` is added in `modules/typewars/` that calls into `claim_progress`.
- `mark_email_sent(email_id, provider_msg_id)` — worker call after Resend success
- `mark_email_failed(email_id, error)` — worker call on failure (allows retry policy)

**Admin (replaces `services/admin-api/main.py`):**
- `set_comment_status(id, status)` — already exists, no change
- `delete_comment(id)` — already exists, no change
- `upsert_system_metrics(snapshot)` — collector call, owner-only
- `upsert_container_status(name, status, uptime_s, mem_used_mb, mem_limit_mb, restart_count)` — collector call, owner-only
- `append_log_event(container, ts_micros, level, text)` — collector call, owner-only
- `add_log_interest(container)` — frontend call (admin only); creates row keyed on (container, sender)
- `remove_log_interest(container)` — frontend call; deletes row
- `prune_log_events()` — `#[reducer(scheduled)]` every 60 s; trims `log_event` to most recent 500 per container

**Deck (replaces `services/deck/main.py`):**
- `request_plan(description, count)` — inserts `plan_request` (pending), returns id. Defines the deterministic local-fallback rules in Rust (port of `_local_draft`).
- `set_plan(request_id, tracks)` — worker call after Ollama success
- `set_plan_fallback(request_id)` — worker call when Ollama fails; reducer computes deterministic fallback from the original description+count
- `request_generate(plan_id, edited_tracks)` — inserts `generate_job` (pending)
- `set_generate_done(job_id, zip_url)` — worker call after LocalAI render
- `set_generate_failed(job_id, error)` — worker call on render failure

**Moderator (replaces `infra/agents/moderator/main.py`):**
- The `comment` table already exists with status='pending'. No new tables needed — worker just subscribes to `WHERE status='pending'`.
- `set_comment_status` already exists; the worker calls it with the verdict.
- The injection-detection result is incorporated into the verdict by the worker; the reducer just records the final status.

**Total addition to `modules/sastaspace/src/lib.rs`:** ~10–12 new reducers, ~8 new tables, estimated ~400–500 LOC on top of the existing 417.

---

## What goes in `workers/`

Single Node process. Each agent is one file under `src/agents/`, ~30–60 LOC of Mastra glue. Each agent's pattern:

```
1. on boot: connect to STDB with the worker's owner JWT
2. subscribe to a query (the "intent" rows)
3. for each new row, call the external thing (Resend / Ollama / LocalAI / Docker / nvidia-smi)
4. call back into STDB with the result
```

### `auth-mailer.ts`
- Subscribes: `SELECT * FROM pending_email WHERE status='queued'`
- For each: builds magic-link URL from row + app_config, calls Resend SDK, calls `mark_email_sent` or `mark_email_failed`
- ~50 LOC

### `admin-collector.ts`
- Three independent loops in one file:
  - Every 3 s: read psutil-equivalents (`os.cpus()`, `os.totalmem()`, fs stats, `nvidia-smi` exec) → call `upsert_system_metrics`
  - Every 15 s: list docker containers via `dockerode` or `docker` CLI → call `upsert_container_status` per container
  - Subscribe `log_interest`; for each (container, subscriber) row, ensure a `docker logs --follow` subprocess is running; on each line call `append_log_event`. When interest row deleted, kill subprocess.
- ~250 LOC (most volume in this codebase)

### `deck-agent.ts`
- Subscribes: `SELECT * FROM plan_request WHERE status='pending'` AND `SELECT * FROM generate_job WHERE status='pending'`
- For plan_request: call Ollama via Mastra `Agent` with the planner instructions; on success → `set_plan`; on failure → `set_plan_fallback` (reducer does the fallback). Note: gemma3:1b's prompt-injection guard pattern from the moderator is NOT applied here — the user's project description is their own, not third-party content.
- For generate_job: for each track, call LocalAI's MusicGen endpoint (LocalAI exposes a backend-specific URL — exact path confirmed during W3 implementation against the LocalAI version we install in Phase 0). Collect WAV bytes, zip them, write zip to a deck-out directory mounted from the host (`infra/deck-out/<job_id>.zip`), nginx serves it. Call `set_generate_done` with the URL or `set_generate_failed` on render error.
- ~120 LOC

### `moderator-agent.ts`
- Subscribes: `SELECT * FROM comment WHERE status='pending'`
- For each: run injection guard (Mastra Agent with detector instructions, calls Ollama), then content classifier (second Mastra Agent with classifier instructions, calls Ollama). Call `set_comment_status` with `approved` or `flagged`.
- ~80 LOC

### Shared (`workers/src/shared/`)
- `stdb.ts` — connects with the owner JWT, exposes `db.subscribe(query, handler)` and `db.callReducer(name, ...args)` (~80 LOC)
- `mastra.ts` — Mastra instance config, provider definitions for ollama (text) and localai (audio), shared retry/telemetry settings (~50 LOC)
- `env.ts` — typed env via zod (~40 LOC)

**Total `workers/src/`:** ~700 LOC TypeScript, all roughly the same shape.

---

## Per-app frontend changes

### `apps/admin/`
- Delete `src/lib/data.ts` (mock data)
- New `src/lib/stdb-admin.ts`: connects with owner JWT (from Google Sign-In flow's identity mapping)
- Comments panel: subscribe to `comment`, `user`; moderation buttons call `set_comment_status` / `delete_comment` reducers directly
- Server panel: subscribe to single-row `system_metrics`
- Services panel: subscribe to `container_status`
- Logs panel: on mount call `add_log_interest(name)`, subscribe to `log_event WHERE container=name`, on unmount call `remove_log_interest(name)`
- TypeWars panel: subscribe to `typewars` module tables (already in scope per the in-flight admin-realdata spec — that subscription part is salvaged)
- Owner-JWT shape: Google Sign-In gives an ID token; admin verifies it client-side against Google's JWKS, then loads a stored owner-STDB-token from localStorage (one-time setup, owner pastes the token from `spacetime login`). No backend round-trip.

### `apps/landing/`
- `/lab/deck/Deck.tsx`: replace `fetch(/plan)` and `fetch(/generate)` with `db.callReducer('request_plan', ...)` etc.
- Subscribe to the returned `plan_request` row by id for live status; same for `generate_job`
- On `generate_job.status='done'`, the row's `zip_url` field is the download link (served by nginx from `infra/deck-out/`)

### `apps/notes/`
- Replace POST to `auth.sastaspace.com/auth/request` with `db.callReducer('request_magic_link', email, 'notes', null, callbackUrl)`
- New page `src/app/auth/verify/page.tsx`:
  1. parse `?t=<token>` from URL
  2. call `POST /v1/identity` on STDB to mint fresh identity + JWT (anonymous HTTP call, no auth needed)
  3. reconnect to STDB with new JWT
  4. call `verify_token(t, display_name)` reducer — atomic validate + register
  5. store JWT in localStorage, redirect to `/`
- The current `/auth/callback` page (which handles JWT-from-fragment after the FastAPI redirect) gets retired once `/auth/verify` is live

### `apps/typewars/`
- Same `request_magic_link` swap as notes
- Same `/auth/verify` page added (calls `claim_progress` reducer instead of `register_user`)
- Game subscriptions unchanged

---

## Infra changes

### `infra/docker-compose.yml`
- Remove: `auth`, `admin-api`, `deck`, `moderator` service blocks
- Add: `workers` service block (Node 22 alpine, runs the single workers process). Volume-mounts `/var/run/docker.sock:ro` (for admin-collector) and `./deck-out:/app/deck-out:rw` (for deck-agent zip output). `network_mode: host` so it reaches Ollama/LocalAI/STDB on host loopback.
- Add: `localai` service block (Go binary container, ports 8080→127.0.0.1:8080, GPU passthrough, model preload via init script)
- Add: `deck-out` directory mount on the existing `landing` nginx container so generated zips are servable at `sastaspace.com/deck-out/<job_id>.zip` (or a subdomain — Phase 0 decision)
- Keep: `landing`, `notes`, `admin`, `typewars` (all nginx static), `spacetime` (existing)

### `infra/cloudflared/`
- Remove `api.sastaspace.com` ingress route
- All other routes unchanged (`stdb.sastaspace.com` still routes to spacetime container; app subdomains still route to nginx)

### `infra/localai/`
- New directory: `models.yaml` (declares MusicGen backend + which model file), `preload.sh` (downloads `facebook/musicgen-small` weights on first boot)

### Auth domain
- `auth.sastaspace.com` becomes unused. Recommend: leave the Cloudflare ingress in place for one release pointing to a 410 Gone static page, then remove. Tracks any stale clients still hitting it.

---

## Migration phases

Phases are designed for parallelism — every phase except Phase 0 splits into independent workstreams that can be developed and reviewed in parallel.

### Phase 0 — Foundation (sequential, ~1 day)
**Workstream:** single
- Rename `module/` → `modules/sastaspace/`, update Cargo.toml, CI, generate scripts, docker-compose volume paths, README
- Rename `game/` → `modules/typewars/`, same updates
- Add `workers/` skeleton with package.json, Dockerfile, empty agents
- Stand up LocalAI on taxila (compose service + preload), verify `curl /v1/audio/generations` works manually
- Ship E2E baseline: full Playwright suite passes against current architecture, screenshot/snapshot captured for diff later

### Phase 1 — Reducer + worker development (parallel, ~3–4 days)

Four independent workstreams. Each adds tables + reducers to `modules/sastaspace/src/lib.rs`, builds its worker agent, and adds E2E coverage. Each ships behind a feature flag (env `WORKER_<NAME>_ENABLED=true|false`) so a worker can be active without yet wiring the frontend to it.

| Workstream | Owner can be | Touches |
|---|---|---|
| **W1: auth-mailer** | parallel agent A | `pending_email` table + 3 reducers; `auth-mailer.ts`; tests |
| **W2: admin-collector** | parallel agent B | 5 metrics tables + 6 reducers; `admin-collector.ts`; tests |
| **W3: deck-agent** | parallel agent C | 2 deck tables + 6 reducers + Rust port of `_local_draft`; `deck-agent.ts`; tests |
| **W4: moderator-agent** | parallel agent D | (no new tables — uses existing `comment`); `moderator-agent.ts`; tests |

Each workstream's deliverable: feature-flagged worker is running on the dev compose, reducers are in the module, unit + integration tests pass. **Frontend not yet rewired.**

### Phase 2 — Frontend rewire (parallel, ~2–3 days)

Four independent workstreams. Each switches one app from "calls Python service" to "calls reducer." E2E suite gates each PR.

| Workstream | Touches |
|---|---|
| **F1: notes auth** | request_magic_link + new /auth/verify page in notes |
| **F2: typewars auth** | same in typewars |
| **F3: admin panels** | comments + server + services + logs panels rewired |
| **F4: deck** | landing /lab/deck rewired |

Each workstream's deliverable: E2E spec for that app's user-visible flows passes against the rewired path AND against the legacy path (legacy still running, both behind the worker flag).

### Phase 3 — Cutover (sequential, ~1 day)
**Workstream:** single
- Flip `WORKER_*_ENABLED=true` on prod for each worker
- Watch for one canary period (1 hour each, staggered) — observe STDB row state, worker logs, Sentry/error rates
- Once each worker is healthy, kill the corresponding Python service container in compose
- Run **full E2E regression suite against prod-equivalent** (staging compose with cutover applied) — must be 100% green to proceed

### Phase 4 — Cleanup (parallel, ~0.5 day)
- Delete `services/auth/`, `services/admin-api/`, `services/deck/`, `infra/agents/moderator/` directories
- Delete the `auth`, `admin-api`, `deck`, `moderator` blocks from docker-compose.yml (already commented out in cutover; this is removal)
- Delete unused root files flagged by audit: `deck-step2-expanded.png`, `deck-step3-results.png`, root `idea.md` (move to `docs/archive/` if anything's reusable)
- Update `README.md` and add `STRUCTURE.md` describing the simplified layout
- Final E2E suite run on the cleaned tree
- Run `graphify update .` to refresh the knowledge graph

---

## Testing strategy

### Existing baseline (must not regress)
The E2E suite at `tests/e2e/` covers:
- Notes auth (sign-in + verify + comment submit)
- Typewars auth (sign-in + verify + claim progress + battle + leaderboard + profile + warmap + register + legion-swap — per untracked specs in git status)
- Admin panel (current state — assumed minimal until F3 lands)
- Deck happy path (assumed via `apps/landing/src/app/lab/deck/`)

**Phase 0 deliverable:** confirm 100% green baseline before any other work starts. Capture timing baselines.

### New tests per workstream

- **W1/F1/F2:** new specs for the rewired auth flow at the verify-page level (currently the verify is a server-side redirect; will become a client-side flow with multiple reducer calls). Must cover: happy path, expired token, used token, network blip mid-verify, prev_identity claim path.
- **W2/F3:** new specs per admin panel: live metrics update visible within 5 s of change, container status updates after `docker restart`, log lines appear in panel within 2 s of being emitted, log_interest properly cleaned up on panel close.
- **W3/F4:** new spec for /lab/deck end-to-end: submit → plan appears → user edits → generate → zip downloads. Plus failure paths (Ollama unavailable, LocalAI unavailable).
- **W4:** new spec for moderator end-to-end: submit a benign comment → status='approved' within 10 s; submit an injection-attempt comment → status='flagged' within 10 s.

### Regression gate
Every phase ends with **full E2E suite green** before next phase starts. Phase 3 cutover requires the suite to pass against the cutover-applied staging compose, not just against the current dev path.

### What "100% E2E regression" means in this spec
- Every existing E2E test continues to pass
- Every user-visible flow in the four apps has at least one E2E test (happy + at least one failure path)
- New flows added in Phase 1/2 ship with their own E2E specs
- Suite runs on every PR via existing CI; no merging on red

---

## Rollback plan

The Python services are not deleted until Phase 4. During Phase 1–3, both paths coexist:

- A worker can be killed (`docker stop sastaspace-worker-<name>`) and the corresponding Python service restarted from compose. Frontend feature flag flips back. ~5 minute revert.
- Reducers are additive — leaving them in place after a rollback causes no harm; tables stay populated but unread.
- No DB migration is destructive in this spec. Schema additions only; no drops, no renames of existing tables.

After Phase 4 cleanup, rollback requires `git revert` of the cleanup PR + redeploy. So Phase 4 only happens after Phase 3 has been stable for at least 48 h.

---

## Out of scope

Explicitly NOT covered by this spec (some are follow-ups, some are deliberate non-goals):

- New features in any app. Migration only.
- Changes to `modules/typewars/` (the game module). Untouched.
- Replacing the existing comment moderation guards (the prompt structure stays; only the runtime moves from Python to TS Mastra agent).
- Replacing Resend with a self-hosted SMTP. Email is still external; only the call-site moves.
- Removing nginx in favor of Cloudflare Pages. Static serving stays.
- Auth method changes for any app. Notes/typewars stay magic-link, admin stays Google Sign-In.
- Performance optimization. Workers run as one process; splitting is a future call.
- The `packages/spacetime-client-py/` extraction the structure audit's H1 recommended. Obsolete now.

---

## Open questions

1. **Cleanup of `auth.sastaspace.com` Cloudflare ingress** — leave with 410 Gone for one release, or remove immediately at cutover? *(Default: 410 page for one release.)*
2. **Where to host generated WAV zips** — `infra/deck-out/` directory served by nginx (proposed), or write zip bytes into `generate_job.zip_data` blob? STDB doesn't have great blob support so nginx-served directory is cleaner. *(Default: nginx directory.)*
3. **Should `auth-mailer` and `moderator-agent` ever be split into separate processes?** Same Ollama dependency, same Mastra runtime, no resource competition expected. *(Default: stay one process; revisit if Ollama becomes a bottleneck.)*
4. **`workers/Dockerfile` — Node 22 alpine vs distroless?** Alpine is smaller, distroless is more locked down. *(Default: Node 22 alpine to match existing nginx alpine images for consistency.)*
5. **`module/` rename — does anything else in CI/scripts hard-code that path?** Need to audit `.github/workflows/`, `package.json` scripts, any `Cargo.toml` workspace declaration. Phase 0 task. *(Open.)*
6. **LocalAI MusicGen endpoint shape** — LocalAI's MusicGen backend has a backend-specific URL (not OpenAI-compatible like its chat endpoints). Exact path + request body confirmed during Phase 0 by hitting `curl` against the installed LocalAI. Worker uses raw fetch for this one call; Mastra still wraps the Ollama LLM call. *(Resolve in Phase 0.)*
7. **Where to serve generated zips** — `sastaspace.com/deck-out/<job>.zip` (sub-path of landing) or `deck.sastaspace.com/<job>.zip` (new subdomain)? *(Default: subdomain `deck.sastaspace.com` since /lab/deck is being promoted out of /lab anyway per audit M1.)*

---

## Effort estimate

Optimistic (parallel agents, no surprises):
- Phase 0: 1 day
- Phase 1: 3–4 days (4 streams × ~1 day each, with reducer integration time)
- Phase 2: 2–3 days (4 streams × ~0.5 day each + integration)
- Phase 3: 1 day
- Phase 4: 0.5 day

**Total: 7.5–9.5 days of wall-clock if parallelized; ~14–18 days serial.**

Realistic with debugging: add ~30%. Call it **2 weeks parallel, 3–4 weeks serial.**

---

## Acceptance criteria

The rewire is "done" when:

- [ ] `find . -name '*.py' | grep -v node_modules | grep -v .venv` returns zero results
- [ ] `services/` and `infra/agents/` directories no longer exist
- [ ] `docker compose ps` shows: spacetime, ollama, localai, workers, landing, notes, admin, typewars, cloudflared (and nothing more)
- [ ] All E2E specs in `tests/e2e/` pass against the rewired stack
- [ ] No `api.sastaspace.com` route exists in cloudflared config
- [ ] `STRUCTURE.md` exists and accurately describes the new layout
- [ ] `graphify-out/GRAPH_REPORT.md` is regenerated; god-node count is reduced (no more `Sender`, `LlamaGuardClassifier` god-nodes — they were Python types)
