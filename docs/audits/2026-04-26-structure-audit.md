# Repo Structure & Component Audit

**Date:** 2026-04-26
**Scope:** Full monorepo at `/Users/mkhare/Development/sastaspace`
**Type:** Structural / architectural review (not security, not line-level code quality)
**Trigger:** New untracked work (`services/admin-api/`, `services/deck/`, `apps/landing/src/app/lab/deck/`) about to land; chance to catch drift before it calcifies.

---

## 1. Methodology

1. Read `graphify-out/GRAPH_REPORT.md` for god nodes, communities, and inferred coupling.
2. Walked top-level layout: `apps/`, `packages/`, `services/`, `infra/`, `module/`, `game/`, `docs/`, `tests/`.
3. Compared the new `services/admin-api/` skeleton to `services/auth/` (the spec says to "mirror it exactly").
4. Cross-checked design-tokens consumption across apps.
5. Mapped untracked work (`deck`) across its three locations.

No code was modified. This is a read-only audit.

---

## 2. Repo inventory

| Top-level dir | Purpose (as observed) | Notes |
|---|---|---|
| `apps/` | Deployable Next.js frontends (`admin`, `landing`, `notes`, `typewars`) | Mostly siloed; share via `packages/` inconsistently |
| `packages/` | Shared TS libs (`design-tokens`, `stdb-bindings`) | No Python equivalent — see H1 |
| `services/` | Python FastAPI backends (`auth`, plus new `admin-api`, `deck`) | Each ships its own Dockerfile, pyproject, ruff cfg |
| `infra/` | docker-compose, Cloudflare tunnel, agents (`infra/agents/moderator/`) | Mixes ops config with long-running Python agents — see H4 |
| `module/` | Rust SpacetimeDB module: **sastaspace** core schema | Name is misleading; it's a backend, not a "module" namespace |
| `game/` | Rust SpacetimeDB module: **typewars** | Same shape as `module/` but different top-level name |
| `docs/` | Design specs (currently only `superpowers/specs/`) | This audit lives here |
| `tests/` | Root-level tests dir | Purpose unclear; per-app and per-service tests live in their packages |
| `graphify-out/` | Knowledge graph artifacts | Used for this audit |
| `node_modules/` | pnpm install output | Standard |

Root-level loose artifacts: `deck-step2-expanded.png`, `deck-step3-results.png`, `idea.md`, `SECURITY_AUDIT.md`, `.playwright-mcp/` (45 dirs of MCP run artifacts).

---

## 3. Graph signal

From `graphify-out/GRAPH_REPORT.md` (594 nodes, 1046 edges, 34 communities):

**God nodes (concentrated coupling):**
| Node | Edges | Bridges |
|---|---|---|
| `SpacetimeClient` | 36 | Auth Service ↔ AI Comment Moderation ↔ Email |
| `Sender` (email) | 20 | Email Pipeline ↔ Auth ↔ Moderation |
| `LlamaGuardClassifier` | 17 | Moderation engine internals |
| `Verdict` / `GuardResult` | 16 each | Moderation type surface |
| `verify_magic_link()` | 11 | Auth flow core |

**`SpacetimeClient` and `Sender` crossing community boundaries is the headline finding.** It tells us the same Python types are being used across `services/auth/`, `infra/agents/moderator/`, and (about to be) `services/admin-api/` — but they're **not** in a shared package. Each consumer holds its own copy. That's H1.

**Thin communities (3–5 nodes each):** Footer, CommentForm, BrandMark, Chip, ProjectsList, PresencePill, TopNav. These are UI primitives that *should* be shared package-level components but appear once per app — graph isolation reflects code isolation. That's M3.

---

## 4. Findings

### HIGH

#### H1 — `SpacetimeClient` duplicated per Python service
- **Where:** `services/auth/src/sastaspace_auth/stdb.py`. The `services/admin-api/` design spec (`docs/superpowers/specs/2026-04-26-admin-realdata-design.md`) explicitly says "copy from services/auth/". `services/deck/` will follow the same pattern.
- **Evidence:** Graphify flags `SpacetimeClient` with 36 edges spanning 3 communities. There is no `packages/spacetime-client-py/`.
- **Risk:** Every retry, error-handling, or transport bugfix has to be applied N times. Behavior will diverge. The TS side already solved this with `@sastaspace/stdb-bindings`; Python has nothing equivalent.
- **Fix:** Extract HTTP transport + retry into `packages/spacetime-client-py/`. Each service installs it via local path in `pyproject.toml` and only owns its reducer wrappers.
- **Effort:** ~1 day. Must do before `admin-api` and `deck` ship.

#### H2 — `module/` vs `game/` vs `packages/` — three top-level dirs, no convention
- **Where:** `module/Cargo.toml` (sastaspace SpacetimeDB module), `game/Cargo.toml` (typewars SpacetimeDB module), `packages/` (TS libs).
- **Risk:** A new contributor reads `module/` as a shared namespace. It's actually one specific Rust backend. `game/` is the same kind of thing under a different name.
- **Fix:** Either `modules/sastaspace/` + `modules/typewars/` (sibling layout), or move both under `services/` (they are backends). Add `STRUCTURE.md` at root with one line per top-level dir.
- **Effort:** ~0.5 day (rename + update CI/Cargo paths + STRUCTURE.md).

#### H3 — `services/admin-api` bundles three unrelated concerns
- **Where:** Spec at `docs/superpowers/specs/2026-04-26-admin-realdata-design.md`. One service handles (a) system/Docker metrics via Docker socket, (b) SSE log streaming via subprocess, (c) STDB write proxy gated by Google JWT.
- **Risk:** Different threat models in one process. Docker-socket bind-mount colocated with a public JWT-gated proxy is uncomfortable. Will balloon to a 2k-line `main.py` once admin grows (alerts, restarts, snapshots).
- **Fix:** Split routers internally now: `routers/system.py`, `routers/logs.py`, `routers/stdb_proxy.py`. Document a charter in `services/admin-api/README.md` for what does/doesn't belong. Future split into separate services becomes mechanical.
- **Effort:** ~0.5 day, fits inside the implementation PR.

#### H4 — No documented rule for `infra/agents/` vs `services/`
- **Where:** `infra/agents/moderator/` is a long-running Python loop with its own STDB client and email sender. `services/auth/` is also Python with its own copies.
- **Risk:** Next backend feature has no obvious home. Result: more `SpacetimeClient` and `Sender` clones.
- **Fix:** Add `ARCHITECTURE.md` at root with one section: services = HTTP listeners; agents = workers/loops; both consume `packages/*` for STDB, email, JWT.
- **Effort:** ~0.5 day, mostly writing.

### MEDIUM

#### M1 — `deck` work is split across three places with no source of truth
- **Where:** `apps/landing/src/app/lab/deck/` (51KB `Deck.tsx`), `services/deck/` (FastAPI), root `deck-step*.png`. `idea.md` calls it "audio-designer"; the `/lab` placement says experiment; the dedicated service says feature.
- **Fix:** Decide. If shipping → `apps/landing/src/app/deck/` and a top-level entry. If experimental → keep under `/lab` and add `apps/landing/src/app/lab/README.md` listing experiments. Either way, move the PNGs to `docs/deck/` and either supersede or delete `idea.md`.
- **Effort:** ~0.5 day.

#### M2 — Service boilerplate is hand-copied
- **Where:** `services/auth/`, `services/admin-api/`, `services/deck/` share near-identical Dockerfile, pyproject test config, ruff config, tests layout.
- **Fix:** `services/_template/` skeleton + a `make new-service NAME=foo` target. Or extract shared ruff/pytest config into a root `pyproject.toml` that services inherit.
- **Effort:** ~0.5 day.

#### M3 — `packages/design-tokens` not consumed by `apps/admin`; primitives reinvented per app
- **Where:** `apps/admin/package.json` doesn't depend on `@sastaspace/design-tokens`. Graph shows Footer, Chip, BrandMark, PresencePill, TopNav each living as a thin community per app.
- **Risk:** Visual drift across apps. A re-skin requires N edits.
- **Fix:** (1) Add design-tokens to admin's deps. (2) Promote recurring primitives to `packages/ui/`. Apps import; apps don't reimplement.
- **Effort:** ~1 day for first pass; ongoing as more primitives surface.

#### M4 — No typed contract between frontend and HTTP services
- **Where:** `Deck.tsx` calls `services/deck` over plain fetch with hand-typed request/response shapes. The new admin frontend will do the same against `admin-api`.
- **Risk:** STDB bindings give typed IPC; HTTP services don't. Schema drift breaks the UI silently at runtime.
- **Fix:** FastAPI emits OpenAPI for free. Add `openapi-typescript` (or `orval`) and generate a TS client into `packages/api-clients/`. Apps import the client.
- **Effort:** ~0.5 day to bootstrap, then near-zero per service.

#### M5 — Service naming inconsistent
- `auth`, `admin-api`, `deck` — only one has the `-api` suffix. Python packages are `sastaspace-auth`, `sastaspace-admin-api`, `sastaspace-deck`.
- **Fix:** Pick a rule (drop `-api`; they're all APIs) and put it in `services/README.md`. Rename `admin-api` → `admin` before the URL and Cloudflare ingress bake in.
- **Effort:** ~1 hour, but only if done before deploy.

### LOW

#### L1 — Root directory clutter
- `deck-step2-expanded.png`, `deck-step3-results.png`, `idea.md`, `SECURITY_AUDIT.md`, `.playwright-mcp/` (test artifacts).
- **Fix:** PNGs → `docs/deck/`. `idea.md` → delete or `docs/` and mark archived. `SECURITY_AUDIT.md` → `docs/audits/2026-04-25-security.md` (matches this file's location). Add `.playwright-mcp/` to `.gitignore`.
- **Effort:** ~15 minutes.

#### L2 — Root `tests/` purpose unclear
- Per-app and per-service tests live alongside their code. What does the root `tests/` cover?
- **Fix:** Add a one-line `tests/README.md` explaining the scope (cross-cutting E2E?) or delete if obsolete.
- **Effort:** ~15 minutes.

---

## 5. Recommended sequence

The new `services/admin-api/` and `services/deck/` are not yet committed. That's the leverage moment.

**Before either service is committed:**
1. **H1** — create `packages/spacetime-client-py/`. Refactor `services/auth/` to use it. New services start clean.
2. **H3** — split `admin-api` into routers from day one.
3. **M5** — rename `admin-api` → `admin` (URL hasn't been published).

**This week (alongside implementation):**
4. **H4** — write `ARCHITECTURE.md`. One page.
5. **H2** — pick `module/`/`game/` rename and ship it.
6. **M1** — decide if `deck` is permanent or experimental; move accordingly.

**This month:**
7. **M2** — `services/_template/`.
8. **M3** — `packages/ui/` for shared primitives.
9. **M4** — generated OpenAPI client.

**Whenever:**
10. **L1** + **L2** — root cleanup. Trivial.

---

## 6. Open questions for the owner

1. Is `module/` intended to stay as the *only* Rust SpacetimeDB module, or will more land? (Affects H2 fix shape.)
2. Is `deck` a permanent feature or a `/lab` experiment? (M1.)
3. Should `infra/agents/moderator/` move under `services/` since it's also a Python long-running process? Or stay in `infra/` as ops? (H4 ties to this.)
4. What's the root `tests/` directory for? (L2.)

---

## 7. What was NOT in scope

- Security review (separate `/security-review` already covered the design spec; turned up zero findings since the diff was docs-only).
- Code-level quality (line-by-line correctness, test coverage gaps, individual function complexity).
- Performance.
- Dependency hygiene / outdated packages.

---

## Appendix A — files referenced

- `graphify-out/GRAPH_REPORT.md` — graph snapshot used for god-node and thin-community signal.
- `docs/superpowers/specs/2026-04-26-admin-realdata-design.md` — admin-api design spec being audited against.
- `services/auth/src/sastaspace_auth/stdb.py` — `SpacetimeClient` original (to be extracted in H1).
- `apps/landing/src/app/lab/deck/Deck.tsx` — deck UI (M1).
- `apps/admin/package.json` — missing `design-tokens` dep (M3).
- `pnpm-workspace.yaml`, `package.json` — workspace definition (no changes proposed).
