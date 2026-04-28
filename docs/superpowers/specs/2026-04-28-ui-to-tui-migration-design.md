# UI→TUI Migration: sastaspace as a Rust Terminal Binary

**Status:** design — pending implementation plan
**Date:** 2026-04-28
**Owner:** Mohit
**Replaces:** all four Next.js apps (`apps/landing`, `apps/notes`, `apps/admin`, `apps/typewars`) and three Python services (`services/admin-api`, `services/auth`, `services/deck`) — the TypeScript worker for `deck` (ACE-Step bridge) is the only non-Rust process that survives.

---

## 1. Goal

Replace the entire web client + Python service surface with a single Rust TUI binary, distributed btop-style (Homebrew, `cargo install`, GitHub releases). The SpacetimeDB Rust modules (`modules/sastaspace`, `modules/typewars`) are kept as-is — they are the canonical backend.

Motivation: AI-driven development is faster and more reliable against a TUI than against a browser stack. A `ratatui::backend::TestBackend` snapshot is a deterministic 2D grid of characters; a Playwright run is a flaky network of headless Chrome, page lifecycle, hydration races, and visual diffs. Snapshot tests over rendered terminal buffers are the leverage we are buying.

## 2. Non-goals

- **No web client of any kind.** No "static landing page that links to the binary." If you can `curl` the binary, that's the landing page. The README on GitHub is the marketing site.
- **No new SpacetimeDB module surface.** Existing `sastaspace` (35 reducers, 18 tables) and `typewars` (22 reducers, 9 tables) modules cover everything.
- **No local STDB.** Every TUI connects to `wss://stdb.sastaspace.com`. Offline = no app.
- **No new auth model.** Magic-link emails (existing `request_magic_link` reducer + `auth-mailer` worker) plus Google device-flow OAuth for the owner role. No SSH keys, no WebAuthn, no anonymous-only.
- **No multi-binary split.** One `sastaspace` binary, app routing inside.
- **No backwards-compat with the web stack during the cut-over window.** Hard switch on a chosen day; the web apps and Python services are deleted in the same PR that flips DNS.

## 3. Foundational decisions (locked from brainstorm)

| Decision | Choice |
|---|---|
| Audience | Personal + small known group + public download (btop-style binary) |
| STDB location | Single remote at `stdb.sastaspace.com` |
| v1 scope | All five surfaces (portfolio splash, notes, admin, typewars, deck) ported |
| Auth | Magic-link email (existing) + Google OAuth device flow for owner |
| Workspace shape | Cargo workspace, app-per-crate (Approach A from brainstorm) |
| Guiding principle | Simple is best — YAGNI ruthlessly, no speculative abstractions |

## 4. Architecture

### 4.1 Workspace layout

```
sastaspace-tui/                       # rename of repo root (or new top-level dir; see §11)
├── Cargo.toml                        # workspace manifest
├── rust-toolchain.toml               # pin stable Rust
├── crates/
│   ├── shell/                        # the binary
│   │   ├── src/main.rs               # entry: parse args → init → router loop
│   │   └── src/router.rs             # current-screen state machine
│   ├── core/                         # shared types, theme, keymap, config
│   │   ├── src/theme.rs              # Style/Color palette (one source of truth)
│   │   ├── src/keymap.rs             # global keys (q quit, ? help, : command)
│   │   ├── src/config.rs             # ~/.config/sastaspace/config.toml load+save
│   │   └── src/event.rs              # crossterm Event → app-level Action enum
│   ├── stdb-client/                  # thin wrapper over spacetimedb-sdk
│   │   ├── src/connection.rs         # connect, reconnect-with-backoff, identity cache
│   │   ├── src/subscriptions.rs      # typed sub helpers (one per app's working set)
│   │   └── src/reducers.rs           # typed reducer call wrappers
│   ├── auth/                         # auth flows + token storage
│   │   ├── src/magic_link.rs         # request_magic_link → poll auth_token table
│   │   ├── src/google_device.rs      # OAuth 2.0 device authorization grant
│   │   └── src/keychain.rs           # `keyring` crate wrapper
│   ├── app-portfolio/                # the splash / "landing" replacement
│   ├── app-typewars/
│   ├── app-notes/
│   ├── app-admin/
│   └── app-deck/
└── modules/                          # existing STDB modules, moved into workspace
    ├── sastaspace/                   # unchanged
    └── typewars/                     # unchanged
```

Each `app-*` crate exposes one struct that implements:

```rust
pub trait App {
    fn id(&self) -> &'static str;                 // "typewars", "notes", ...
    fn title(&self) -> &str;                       // shown in header
    fn render(&mut self, frame: &mut Frame, area: Rect);
    fn handle(&mut self, action: Action) -> AppResult;
    fn tick(&mut self, dt: Duration) -> AppResult; // animation, polling
}
```

`AppResult` is a small enum: `Continue`, `SwitchTo(&str)`, `Quit`, `Error(eyre::Report)`. The shell's router holds a `Box<dyn App>` for the current screen and a registry of factories for the others.

### 4.2 Library stack

| Concern | Crate | Why |
|---|---|---|
| Rendering | `ratatui` 0.29 + `crossterm` 0.28 | de facto standard, alternate-screen + raw mode out of the box |
| Async runtime | `tokio` (rt-multi-thread, signal, time, fs, io-util) | required by spacetimedb-sdk; one runtime for the whole binary |
| STDB client | `spacetimedb-sdk` (matched to module Rust SDK version) + auto-gen bindings via `spacetime generate --lang rust` checked into `crates/stdb-client/src/bindings/` | typed reducers + typed table subscriptions, no hand-rolled JSON |
| HTTP (auth) | `reqwest` 0.12 (rustls, no native-tls) | magic-link request, Google OAuth polling |
| Token storage | `keyring` 3 | OS keychain (macOS Keychain / Linux Secret Service / Windows Credential Mgr) — never write tokens to plaintext |
| Audio (deck only) | `rodio` 0.20 + save-to-disk to `~/Music/sastaspace/<job>/*.wav` | local playback works; if no audio sink (SSH session), still saves files |
| Logging | `tracing` + `tracing-subscriber` + `tracing-appender` rolling to `~/.local/share/sastaspace/logs/` | doesn't pollute the TUI alt-screen |
| Errors | `color-eyre` (`install_panic_hook` BEFORE entering alt-screen) | rich panics, terminal restored cleanly |
| Config | `toml` + `serde` + `directories` for XDG paths | dead simple, no figment indirection |
| Snapshot tests | `insta` 1.40 + `ratatui::backend::TestBackend` | the AI-dev leverage |
| Distribution | `cargo-dist` 0.22 → GitHub Releases (mac-arm64, mac-x86, linux-x86, linux-arm64, windows-x86) + Homebrew tap + `cargo install` | single config drives all artifacts |

### 4.3 Data flow

```
┌──────────────────────────┐     wss://stdb.sastaspace.com    ┌────────────────────────┐
│  sastaspace TUI (local)  │ ◄──────────────────────────────► │  SpacetimeDB modules   │
│                          │     subscriptions + reducers      │  sastaspace, typewars  │
│  ┌────────────────────┐  │                                   └────────────────────────┘
│  │ tokio runtime      │  │                                              │
│  │  ├ stdb conn task  │──┼─── Action ───┐                               │
│  │  └ event read task │──┼─── Action ───┤                               │
│  └────────────────────┘  │              ▼                       ┌───────┴────────┐
│                          │     ┌─────────────────┐              │ auth-mailer    │
│  ┌────────────────────┐  │     │  Router         │              │ worker (TS)    │
│  │ ratatui main loop  │◄─┼─────│  + current App  │              │ deck-agent (TS)│
│  │  ├ render(frame)   │  │     └─────────────────┘              │ moderator (TS) │
│  │  └ poll Action chan│  │                                       └────────────────┘
│  └────────────────────┘  │
└──────────────────────────┘
```

- Two long-lived tokio tasks feed into a single `mpsc::UnboundedSender<Action>`:
  1. `crossterm::event::EventStream` → keyboard/mouse/resize → `Action::Input(...)`
  2. STDB callbacks (subscription updates, reducer responses) → `Action::Stdb(...)`
- The main loop drains the channel each tick, dispatches to the current `App`, and renders one frame. ~60 fps cap via `tokio::time::interval(16ms)`.
- Workers (`auth-mailer.ts`, `deck-agent.ts`, `moderator-agent.ts`) keep running on the prod box exactly as today. They subscribe to STDB and write back. The TUI never talks to them directly.

### 4.4 Auth flow

**Magic-link (notes / typewars / comments):**
1. User opens `:login` palette in TUI.
2. TUI prompts for email, calls `request_magic_link({ email, app: "tui", prev_identity_hex: None, callback_url: "tui://paste-token" })` reducer.
3. `auth-mailer` worker (existing) sends the email. In `app == "tui"` mode the email body shows the raw 32-char token in a monospace code block with copy-friendly framing instead of a clickable link.
4. User pastes the token into the TUI input field.
5. TUI calls `verify_token({ token, display_name })` reducer.
6. Reducer returns the auth token; TUI stores it in OS keychain under `sastaspace::auth_token`.
7. Future STDB connections set the token as the bearer credential.

This requires three small backend changes (all listed in §7): allow `app == "tui"` in `validate_magic_link_args`, allow the `tui://` scheme in `ALLOWED_CALLBACK_PREFIXES`, and a branch in `auth-mailer.ts` that renders a token-only email when `app == "tui"`.

**Google OAuth device flow (admin only):**
1. User opens admin app → `:owner-login`.
2. TUI hits `https://oauth2.googleapis.com/device/code` with the existing `GOOGLE_CLIENT_ID`.
3. TUI displays the verification URL + 6-digit user code in a centered panel: "open https://google.com/device on any device, enter `WDJB-MJHT`".
4. TUI polls `https://oauth2.googleapis.com/token` every 5 seconds.
5. On approval, Google returns an `id_token` (JWT).
6. TUI stores the JWT in keychain under `sastaspace::owner_id_token`.
7. Owner-only reducer calls (e.g., `set_comment_status`, `delete_comment`) include the JWT in the connection's reducer-call HTTP header → existing admin-api logic moves *into the STDB module's reducers* via a `verify_owner_jwt` helper, so we can delete the FastAPI service entirely (see §6).

### 4.5 Per-app design briefs

Each app gets one paragraph of intent here; full screen wireframes go in the implementation plan.

**Portfolio (`app-portfolio`)** — the splash. Replaces `apps/landing`. Renders the `project` table from STDB as a list of cards with title, description, status, presence count. `↵` opens the project (currently means switch to the named app). `:` opens command palette (`:notes`, `:typewars`, `:admin`, `:deck`, `:login`, `:quit`, `:help`). Default screen on launch.

**Typewars (`app-typewars`)** — the most native TUI fit. Components:
- *LegionSelect:* 5-column grid, arrow keys + enter. (~60 LOC)
- *MapWarMap:* 25-region list with HP bars, status chips, legion contribution legend rendered via Unicode block characters. (~150 LOC)
- *Battle:* the typing screen. Word stream scrolls left-to-right, current word highlighted, HUD shows WPM / ACC / DMG. Real keyboard input (no DOM dance). This is *better* in TUI than in the web app.
- *Leaderboard / Profile / LegionSwap:* simple table or modal popovers.
Subscribes to: `player`, `region`, `word`, `battle_session`, `global_war`. Calls reducers: `register_player`, `enter_battle`, `submit_word`, `swap_legion`, `claim_progress_self`.

**Notes (`app-notes`)** — minimal. Two-pane: left list of notes (subscribed from `project` table where `kind = "note"`), right pane is the editor. Insert mode = vim-style `i`. Save = `:w`. Comments per-note are a popover. Subscribes to `project`, `comment`, `user`. Calls `upsert_project`, `submit_user_comment`, `request_magic_link` for sign-in.

**Admin (`app-admin`)** — replaces both `apps/admin` AND `services/admin-api`. Layout mirrors btop:
- *Top:* system metrics (`system_metrics` table, populated by existing `admin-collector` worker → no FastAPI needed).
- *Middle:* container status (`container_status` table, also populated by `admin-collector`).
- *Bottom:* moderation queue (`comment` table where `status = "flagged"`), with `a` approve / `r` reject / `d` delete keys.
- *Logs popover:* `l` opens a log stream view subscribed to `log_event` table (TUI inserts a `log_interest` row to subscribe; collector tails docker and writes events; TUI removes the interest on close).
Owner-only. The Google OAuth device flow above gates entry. The `set_comment_status` and `delete_comment` reducers verify the JWT inside the module.

**Deck (`app-deck`)** — text input → audio. Two screens:
- *Plan:* text area for the project description, slider for track count (1–10), `↵` calls `request_plan` reducer. UI subscribes to the user's `plan_request` row, renders the plan as it streams in.
- *Generate:* once plan is approved (`:approve`), calls `request_generate`. Subscribes to `generate_job`. When `status = done`, downloads the zip via STDB's `generate_job.url` field, unpacks to `~/Music/sastaspace/<job_id>/`, and offers `p` to play via `rodio`.

### 4.6 Error handling

- **Network drop:** `stdb-client` reconnects with exponential backoff (1s → 30s cap). The TUI shows a discreet "↻ reconnecting…" badge in the header; current screen state is preserved.
- **Reducer errors:** typed `Err(String)` from STDB → routed as `Action::ReducerError { reducer, message }` → app renders an inline toast (3-line popover, auto-dismiss 4s, `esc` to dismiss).
- **Panics:** `color-eyre::install` runs *before* enter-alt-screen. The hook restores the terminal (leave-alt-screen + show-cursor + disable-raw-mode) before printing the report. No more "terminal stuck after a crash."
- **Auth expiry:** if the bearer token is rejected, drop into the `:login` flow automatically and re-attempt the failed action once.
- **Unrecoverable:** `Quit { reason }` is shown for ~2s in the alt screen, then the binary exits non-zero with the reason printed to stderr.

### 4.7 Testing strategy

This is the entire reason for the migration, so it gets specified in detail.

**Unit tests (per-crate):**
- `core`: pure-data tests for keymap parsing, theme palette, config round-tripping.
- `stdb-client`: integration tests against a `spacetime start --listen-addr 127.0.0.1:3199` instance spun up in CI via a `tests/spacetime_fixture.rs` harness. Reducers called → table reads asserted.
- `auth`: HTTP mocked via `wiremock`. Magic-link round trip, OAuth device polling, keychain set/get.
- Each `app-*`: snapshot tests using `ratatui::backend::TestBackend` + `insta`. Pattern:
  ```rust
  let mut app = TypewarsApp::with_fixture(fixtures::battle_mid_round());
  let mut term = Terminal::new(TestBackend::new(120, 40)).unwrap();
  term.draw(|f| app.render(f, f.size())).unwrap();
  insta::assert_snapshot!(term.backend());
  ```
  Snapshots are committed to `crates/app-*/snapshots/` as plain text. A failure is a `git diff` of two ASCII rectangles. AI agents can read, reason about, and update them as easily as source code.

**End-to-end tests (top-level):**
- `tests/e2e/` in the workspace root. Drive the real binary via `expectrl` (PTY-based expect for Rust) connected to a CI-spun `spacetime start` instance.
- Replaces every Playwright spec. Each existing spec maps to an expectrl scenario:
  - `tests/e2e/typewars_battle.rs` ← `tests/e2e/specs/typewars-battle.spec.ts`
  - `tests/e2e/notes_signed_in.rs` ← `tests/e2e/specs/comments-signed-in.spec.ts`
  - …etc.
- A scenario is ~30-50 lines of "send keys, expect string in pane." Fast (no browser warmup), deterministic (no hydration races), greppable (it's text).

**CI pipeline (single `ci.yml`):**
```
1. cargo fmt --check
2. cargo clippy -- -D warnings
3. cargo test --workspace            # unit + snapshot
4. spawn spacetime start in background
5. publish modules to local STDB
6. cargo test --test e2e -- --test-threads=1
7. cargo dist build (release artifacts)
```
Total target: under 5 min on GitHub Actions free tier.

## 5. Distribution

`cargo-dist` config in workspace `Cargo.toml`:
- Binaries: macOS (arm64 + x86_64 universal), Linux (x86_64 + arm64 musl), Windows (x86_64).
- Homebrew tap auto-published to `mohitkhare/homebrew-sastaspace`.
- `cargo install sastaspace` from crates.io.
- `curl https://sastaspace.com/install.sh | sh` — one shell script that detects platform and downloads the right release artifact. The "landing page" is just this install script + the README rendered by GitHub.

DNS:
- `stdb.sastaspace.com` → existing prod box (unchanged)
- `sastaspace.com` → GitHub Pages serving the README + install.sh (one tiny static thing — not a Next.js app)
- All `*.sastaspace.com` web subdomains (notes, typewars, admin, deck, lab) — DNS removed in cut-over PR.

## 6. What gets deleted

Cut-over PR removes (in this order):
1. `apps/landing/`, `apps/notes/`, `apps/admin/`, `apps/typewars/`
2. `services/admin-api/` — admin TUI now talks to STDB directly; `admin-collector` worker (already exists) populates `system_metrics` + `container_status` + `log_event` tables.
3. `services/auth/` — magic-link goes through `auth-mailer` worker (existing).
4. `services/deck/` — already on the deletion list per `render.py` comments; deck-agent TS worker is the production path.
5. `tests/e2e/` (Playwright) — replaced by Rust expectrl tests in workspace root.
6. `packages/` — Next.js shared packages (no consumer left).
7. `infra/` Cloudflare tunnel routes for the deleted hostnames.

Also deleted (root clutter from `docs/audits/2026-04-26-structure-audit.md` finding L1, mooted-or-now-removable by this migration):
- `apps/landing/src/app/lab/deck/Deck.tsx` and the rest of `lab/` — folded into the deletion of `apps/landing/`.
- `deck-step2-expanded.png`, `deck-step3-results.png` at repo root — orphaned mockups.
- `idea.md` at repo root — superseded; the `README.md` becomes the project description.
- `SECURITY_AUDIT.md` at repo root — moved to `docs/audits/2026-04-25-security.md` to match the audit dir convention.
- `.playwright-mcp/` — Playwright MCP run artifacts; `.playwright-mcp/` is added to `.gitignore` and any committed snapshots removed.
- `tests/` (root) — was Playwright-only; the new `tests/e2e/` lives at the workspace root and contains Rust expectrl scenarios instead.
- `graphify-out/` — keep. Cheap, useful for navigation, the graphify post-edit hook still maintains it.

What survives:
- `modules/sastaspace/`, `modules/typewars/` — backend, only the three small changes from §7.
- `workers/` — TypeScript STDB workers (auth-mailer, deck-agent, moderator-agent, admin-collector). They are *not* user-facing UI; they are STDB-side automation that runs on the prod box. Keeping them in TS for v1 per the *simple-is-best* and *staged-migrations* rules: they work, they're small, they're not the bottleneck this migration is solving. A future v2 project can port them to Rust if there's a reason.
- `infra/` minus deleted hostnames.
- `graphify-out/`, `docs/`.

## 7. Backend changes the migration requires

Three small things, none of them shape changes:

**(a) Magic-link allows TUI clients.** In `modules/sastaspace/src/lib.rs`:
- `validate_magic_link_args`: change `matches!(app, "notes" | "typewars" | "admin")` to `matches!(app, "notes" | "typewars" | "admin" | "tui")`.
- `ALLOWED_CALLBACK_PREFIXES`: add `"tui://"` so the existing prefix check passes.

**(b) Auth-mailer renders token-only email for TUI.** In `workers/src/agents/auth-mailer.ts`, branch on the `pending_email.app` field: when `app === "tui"`, render an email whose body is *just* the raw token in a fenced block ("Paste this into your terminal: `XXXXXXXX…`"), not a clickable HTML link. The build-link helpers in the module already produce a `tui://paste-token?token=…` URL we can ignore in this branch.

**(c) Owner JWT verification moves into the module.** New helper in `modules/sastaspace/src/lib.rs`:

```rust
fn verify_owner_jwt(token: &str) -> Result<(), String> {
    // verify Google id_token signature against jwks_uri, check aud == GOOGLE_CLIENT_ID,
    // check email == OWNER_EMAIL. JWKS (cached + rotated) lives in app_config_secret.
}
```

Existing `set_comment_status` and `delete_comment` reducers gain a `jwt: String` argument and call `verify_owner_jwt(&jwt)?` before doing the mutation; `assert_owner` becomes a wrapper around it. This is what lets us delete `services/admin-api/` entirely.

## 8. Phasing (high-level — detailed plan comes from writing-plans)

Bundle the work in three commits-per-app to keep PRs reviewable, but ship the cut-over as one PR:

1. **Foundations PR** — workspace skeleton, `core`, `stdb-client`, `auth`, shell with empty router, portfolio splash. Snapshot tests + CI green.
2. **Typewars PR** — `app-typewars` end-to-end, including all 7 typewars e2e scenarios as expectrl tests.
3. **Notes PR** — `app-notes` end-to-end, including notes / comments e2e.
4. **Deck PR** — `app-deck` end-to-end. New reducer `verify_owner_jwt` lands here too (deck doesn't use it but admin does and we don't want it blocking).
5. **Admin PR** — `app-admin` end-to-end. Owner JWT flow.
6. **Cut-over PR** — delete the web stack, delete services, flip DNS, publish first cargo-dist release. Web is gone the moment this merges.

## 9. Open questions deferred to writing-plans

- Exact column widths / pane proportions per app (visible in snapshot tests).
- Specific keymap (vim-ish vs emacs-ish vs crossterm-ish). Default proposed: vim-ish global (`hjkl` nav, `:` palette, `?` help, `q` quit) with crossterm fallback for arrow keys / page up / etc.
- Which `tokio::sync` primitive backs the action channel (`mpsc::unbounded` is the obvious starting point).
- Snapshot-test seed strategy for time-dependent screens (typewars HUD, deck progress bars).

## 10. Out of scope for v1

- Mouse support (ratatui supports it; not needed for v1).
- Plugin system / scriptability.
- TUI themes beyond the one default theme.
- Multi-account support (one identity per binary instance).
- A "headless" mode (running deck without ratatui). The Rust core is library-shaped enough that a CLI binary could be added later if there's demand.

## 11. Audit findings folded in

`docs/audits/2026-04-26-structure-audit.md` enumerated 11 structural issues. The TUI migration moots 9 of them automatically:

| Finding | Disposition |
|---|---|
| H1 `SpacetimeClient` duplicated per Python service | Moot — all Python services deleted |
| H2 `module/` vs `game/` vs `packages/` naming | Already resolved — `modules/sastaspace/` + `modules/typewars/` exist as siblings |
| H3 `services/admin-api` bundles three concerns | Moot — `admin-api` deleted entirely |
| H4 No rule for `infra/agents/` vs `services/` | Mostly moot — `services/` gone; `workers/` is the only place backend automation lives |
| M1 `deck` split across three places | Moot — `apps/landing/lab/deck`, `services/deck`, root PNGs all deleted |
| M2 Service boilerplate hand-copied | Moot — services deleted |
| M3 `design-tokens` not consumed by admin | Moot — all Next.js apps deleted; theme lives in `crates/core/src/theme.rs` |
| M4 No typed contract frontend↔HTTP | Moot — no HTTP services, no frontend; all I/O is typed STDB reducers |
| M5 Service naming inconsistent | Moot — services deleted |
| L1 Root clutter (PNGs, idea.md, SECURITY_AUDIT.md, .playwright-mcp) | **Folded into §6 deletion list** |
| L2 Root `tests/` purpose unclear | Folded — replaced by Rust `tests/e2e/` at workspace root |

This is unusual leverage for a single migration: a structural audit's worth of cleanup happens for free.

## 12. Repo layout decision

**Choice:** keep `sastaspace/` as the repo root; add `crates/` alongside existing `modules/`, `workers/`, `infra/`. The cut-over PR removes `apps/`, `services/`, `packages/`, `tests/e2e/`. The repo's identity (mohit's monorepo named "sastaspace") is unchanged; only the surface shape inside it shrinks.

Resulting tree post-cutover:

```
sastaspace/
├── Cargo.toml                # workspace
├── crates/                   # new — TUI + libs
├── modules/                  # unchanged — STDB
├── workers/                  # unchanged — STDB-side TS automation
├── infra/                    # trimmed
├── docs/
└── README.md                 # the landing page
```
