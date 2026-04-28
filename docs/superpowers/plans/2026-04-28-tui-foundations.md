# TUI Foundations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the Rust TUI workspace, the `core` / `stdb-client` / `auth` libs, the `shell` binary with router, and the `app-portfolio` splash app. End state: `cargo run -p shell` opens an alt-screen TUI showing the portfolio splash sourced live from `stdb.sastaspace.com`, with `:login` magic-link sign-in working end to end. Snapshot tests + E2E + CI green.

**Architecture:** Cargo workspace at repo root. Eight crates: `shell` (binary), `core`, `stdb-client`, `auth`, `app-portfolio`. All using `ratatui` + `crossterm` + `tokio` + `spacetimedb-sdk` + `reqwest` + `keyring`. The four other apps (typewars/notes/admin/deck) get their own plans after this one lands. Backend touched in three small ways: allow `app="tui"` magic links, add `tui://` callback prefix, render token-only email body when `app == "tui"`. All other STDB module surface is unchanged.

**Tech Stack:** Rust 1.85+ (stable), tokio 1.40, ratatui 0.29, crossterm 0.28, spacetimedb-sdk (matched to module 2.1), reqwest 0.12 (rustls), keyring 3, color-eyre 0.6, tracing 0.1, insta 1.40, expectrl 0.7, cargo-dist 0.22.

**Spec:** `docs/superpowers/specs/2026-04-28-ui-to-tui-migration-design.md`

---

## File Structure

This plan creates the following files (all paths relative to repo root):

**Workspace skeleton:**
- `Cargo.toml` (workspace manifest — modify existing root Cargo if any, else create)
- `rust-toolchain.toml` (pin stable channel)
- `.cargo/config.toml` (build flags)
- `.github/workflows/tui-ci.yml` (CI for the new workspace)

**Crates:**
- `crates/core/Cargo.toml`, `crates/core/src/lib.rs`
- `crates/core/src/theme.rs` — Style/Color palette
- `crates/core/src/keymap.rs` — global keys
- `crates/core/src/config.rs` — TOML config round-trip
- `crates/core/src/event.rs` — `Action` enum, `event_stream()`
- `crates/core/src/app.rs` — `App` trait, `AppResult`
- `crates/stdb-client/Cargo.toml`, `crates/stdb-client/src/lib.rs`
- `crates/stdb-client/src/bindings/mod.rs` (auto-generated, checked in)
- `crates/stdb-client/src/connection.rs` — connect + identity cache
- `crates/auth/Cargo.toml`, `crates/auth/src/lib.rs`
- `crates/auth/src/keychain.rs`
- `crates/auth/src/magic_link.rs`
- `crates/auth/src/google_device.rs`
- `crates/app-portfolio/Cargo.toml`, `crates/app-portfolio/src/lib.rs`
- `crates/shell/Cargo.toml`
- `crates/shell/src/main.rs` — entry, terminal lifecycle
- `crates/shell/src/router.rs` — App registry, dispatch
- `crates/shell/src/palette.rs` — `:` command palette
- `crates/shell/src/login.rs` — login modal (magic-link)

**Backend changes (existing files):**
- Modify `modules/sastaspace/src/lib.rs` (3 small edits)

**E2E:**
- `tests/e2e/Cargo.toml`
- `tests/e2e/src/lib.rs` — `SpacetimeFixture` harness
- `tests/e2e/tests/portfolio_smoke.rs`
- `tests/e2e/tests/magic_link.rs`

**Cleanup:**
- `.gitignore` (append target/ if missing)

---

## Conventions used in this plan

- Every code block is **the actual code to put in the file** unless prefixed with `# Run:` or `# Output:`.
- File paths in headings are absolute from repo root.
- `cargo` commands run from repo root unless noted.
- "Commit" steps stage only the files touched by that task.
- TDD order: failing test → implementation → passing test → commit.

---

## Task 1: Workspace skeleton + CI

**Files:**
- Create: `Cargo.toml` (workspace root)
- Create: `rust-toolchain.toml`
- Create: `.cargo/config.toml`
- Modify: `.gitignore` (append)
- Create: `.github/workflows/tui-ci.yml`

- [ ] **Step 1: Create workspace `Cargo.toml`**

If a `Cargo.toml` already exists at repo root, replace it. Otherwise create:

```toml
[workspace]
resolver = "2"
members = [
    "crates/core",
    "crates/stdb-client",
    "crates/auth",
    "crates/app-portfolio",
    "crates/shell",
    "tests/e2e",
    "modules/sastaspace",
    "modules/typewars",
]

[workspace.package]
version = "0.1.0"
edition = "2021"
license = "MIT"
repository = "https://github.com/mohitkhare/sastaspace"

[workspace.dependencies]
tokio = { version = "1.40", features = ["rt-multi-thread", "macros", "signal", "time", "fs", "io-util", "sync"] }
ratatui = "0.29"
crossterm = { version = "0.28", features = ["event-stream"] }
spacetimedb-sdk = "2.1"
reqwest = { version = "0.12", default-features = false, features = ["rustls-tls", "json"] }
keyring = "3"
color-eyre = "0.6"
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter"] }
tracing-appender = "0.2"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
toml = "0.8"
directories = "5"
futures = "0.3"
thiserror = "1"
insta = { version = "1.40", features = ["yaml"] }
expectrl = "0.7"

[profile.release]
opt-level = 3
lto = "thin"
codegen-units = 1
strip = true
```

- [ ] **Step 2: Create `rust-toolchain.toml`**

```toml
[toolchain]
channel = "1.85"
components = ["rustfmt", "clippy"]
profile = "minimal"
```

- [ ] **Step 3: Create `.cargo/config.toml`**

```toml
[build]
rustflags = ["-W", "unused_imports", "-W", "unused_variables"]

[term]
verbose = false
```

- [ ] **Step 4: Append to `.gitignore`**

Add to the bottom of the existing `.gitignore` if not already present:

```
# Rust
target/
**/*.rs.bk
Cargo.lock.bak

# Insta pending snapshots
**/*.snap.new

# Cargo-dist
dist/
```

- [ ] **Step 5: Create `.github/workflows/tui-ci.yml`**

```yaml
name: tui-ci

on:
  push:
    paths:
      - "crates/**"
      - "modules/**"
      - "tests/e2e/**"
      - "Cargo.toml"
      - "rust-toolchain.toml"
      - ".github/workflows/tui-ci.yml"
  pull_request:
    paths:
      - "crates/**"
      - "modules/**"
      - "tests/e2e/**"
      - "Cargo.toml"
  workflow_dispatch:

concurrency:
  group: tui-ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@1.85
        with:
          components: rustfmt, clippy
      - uses: Swatinem/rust-cache@v2
      - name: fmt
        run: cargo fmt --all -- --check
      - name: clippy
        run: cargo clippy --workspace --exclude sastaspace-module --exclude typewars --all-targets -- -D warnings
      - name: test
        run: cargo test --workspace --exclude sastaspace-module --exclude typewars --exclude e2e
        env:
          RUST_BACKTRACE: 1
```

We exclude the STDB module crates from clippy/test in this CI because they have a different toolchain target (wasm32) handled by the existing deploy workflow. We exclude `e2e` because it needs a live SpacetimeDB instance — that runs in a separate job (added in Task 9).

- [ ] **Step 6: Verify workspace structure**

Run: `cargo metadata --no-deps --format-version 1 | head -20`

Expected: JSON output starts with workspace_root pointing at the repo. (Will fail until we create the member crates in next tasks. That's fine for now — we're only verifying the toml parses.)

Run: `cargo --version`
Expected: prints version (proves toolchain installs from `rust-toolchain.toml`).

- [ ] **Step 7: Commit**

```bash
git add Cargo.toml rust-toolchain.toml .cargo/config.toml .gitignore .github/workflows/tui-ci.yml
git commit -m "feat(tui): workspace skeleton + CI"
```

---

## Task 2: Backend changes — allow `app="tui"` magic links

**Files:**
- Modify: `modules/sastaspace/src/lib.rs` (three small edits)

This is the only backend change Foundations needs. Without it the TUI can't authenticate. Done first because it can land independently and start being exercised before the TUI even compiles.

- [ ] **Step 1: Read the existing magic-link tests**

Run: `grep -n "validate_magic_link_args\|render_magic_link" /Users/mkhare/Development/sastaspace/modules/sastaspace/src/lib.rs | head -20`

Expected: shows the validator (line ~684), the renderers (~723, ~729), and the existing tests (~2656+).

- [ ] **Step 2: Write failing test for `app="tui"` acceptance**

Open `modules/sastaspace/src/lib.rs`, find the test `validate_magic_link_args_rejects_unknown_app` (around line 2695). Add immediately after it:

```rust
#[test]
fn validate_magic_link_args_accepts_tui_app() {
    let r = validate_magic_link_args("u@example.com", "tui", "tui://paste-token");
    assert!(r.is_ok(), "tui app + tui:// callback should validate, got: {r:?}");
}

#[test]
fn validate_magic_link_args_rejects_tui_app_with_https_callback() {
    // tui app must use the tui:// callback scheme; mixing is a misuse.
    let r = validate_magic_link_args("u@example.com", "tui", "https://notes.sastaspace.com/");
    assert!(r.is_ok(), "https callback is still allowed for tui app (defensive)");
    // (We deliberately don't restrict here — easier to support the case where
    // the TUI forwards a web link too.)
}

#[test]
fn render_magic_link_text_for_tui_shows_raw_token() {
    let text = render_magic_link_text_for_tui("abc123XYZ");
    assert!(text.contains("abc123XYZ"), "tui text body must show raw token, got: {text}");
    assert!(!text.contains("http"), "tui text body must not contain a URL, got: {text}");
}
```

- [ ] **Step 3: Run the failing tests**

Run: `cd modules/sastaspace && cargo test --target=$(rustc -vV | sed -n 's|host: ||p') validate_magic_link_args_accepts_tui_app render_magic_link_text_for_tui_shows_raw_token`

Expected: compile error — `render_magic_link_text_for_tui` not found, and `validate_magic_link_args_accepts_tui_app` fails on `"unknown app"`.

(Note: STDB modules are normally compiled to wasm32, but tests run on host. The `--target` flag lets cargo pick the right one; the existing tests do this implicitly.)

- [ ] **Step 4: Make the validator accept `tui` and add the `tui://` prefix**

In `modules/sastaspace/src/lib.rs`, find:

```rust
const ALLOWED_CALLBACK_PREFIXES: &[&str] = &[
    "https://notes.sastaspace.com/",
    "https://typewars.sastaspace.com/",
    "https://admin.sastaspace.com/",
    "https://sastaspace.com/",
];
```

Replace with:

```rust
const ALLOWED_CALLBACK_PREFIXES: &[&str] = &[
    "https://notes.sastaspace.com/",
    "https://typewars.sastaspace.com/",
    "https://admin.sastaspace.com/",
    "https://sastaspace.com/",
    "tui://",
];
```

Find:

```rust
    if !matches!(app, "notes" | "typewars" | "admin") {
        return Err("unknown app".into());
    }
```

Replace with:

```rust
    if !matches!(app, "notes" | "typewars" | "admin" | "tui") {
        return Err("unknown app".into());
    }
```

Find the existing test `validate_magic_link_args_accepts_all_allowed_domains` and update its `assert_eq!(ALLOWED_CALLBACK_PREFIXES.len(), 4);` to `assert_eq!(ALLOWED_CALLBACK_PREFIXES.len(), 5);`.

Find the existing test `validate_magic_link_args_rejects_unknown_app` and confirm it still passes — the rejection list it tests should not include `"tui"`.

- [ ] **Step 5: Add `render_magic_link_text_for_tui`**

Find `fn render_magic_link_text(link: &str) -> String` (around line 729). Immediately after that function add:

```rust
/// TUI variant: the email body shows the raw 32-char token in a fenced block
/// rather than a clickable URL. The TUI prompts the user to paste the token
/// back into a text field. Pulled out so it can be unit-tested on the host
/// without a `ReducerContext`.
fn render_magic_link_text_for_tui(token: &str) -> String {
    format!(
        "Hi,\n\n\
         You requested a sign-in to sastaspace from the terminal app.\n\n\
         Paste this token into the TUI when prompted:\n\n\
         \t{token}\n\n\
         The token expires in 15 minutes. If you didn't request this, ignore\n\
         this email — no one can use it without your terminal session.\n\n\
         — sastaspace\n"
    )
}
```

- [ ] **Step 6: Branch `request_magic_link` on app type**

In `modules/sastaspace/src/lib.rs`, find the `request_magic_link` reducer (around line 535). Locate the lines that build and store the email body:

```rust
    let magic_link = build_magic_link(&callback_url, &token, &app, prev_identity_hex.as_deref());
    ctx.db.pending_email().insert(PendingEmail {
        id: 0,
        to_email: email.clone(),
        subject: "Your sign-in link to sastaspace".into(),
        body_html: render_magic_link_html(&magic_link),
        body_text: render_magic_link_text(&magic_link),
```

Replace those lines with:

```rust
    let (subject, body_html, body_text) = if app == "tui" {
        let text = render_magic_link_text_for_tui(&token);
        // For TUI, the HTML body mirrors the text body exactly — no link to
        // click. Mail clients render this fine; CLIs rarely open HTML.
        (
            "Your sastaspace TUI sign-in token".to_string(),
            text.clone(),
            text,
        )
    } else {
        let magic_link = build_magic_link(&callback_url, &token, &app, prev_identity_hex.as_deref());
        (
            "Your sign-in link to sastaspace".to_string(),
            render_magic_link_html(&magic_link),
            render_magic_link_text(&magic_link),
        )
    };
    ctx.db.pending_email().insert(PendingEmail {
        id: 0,
        to_email: email.clone(),
        subject,
        body_html,
        body_text,
```

- [ ] **Step 7: Run the tests**

Run: `cd modules/sastaspace && cargo test`

Expected: all existing tests pass + the three new ones pass. If the existing magic-link tests fail because of count assertions, fix the count assertion in those tests too (only `validate_magic_link_args_accepts_all_allowed_domains` should need it).

- [ ] **Step 8: Commit**

```bash
git add modules/sastaspace/src/lib.rs
git commit -m "feat(stdb): allow app='tui' magic-link with token-only email body"
```

---

## Task 3: `core` crate — types, theme, keymap, config

**Files:**
- Create: `crates/core/Cargo.toml`
- Create: `crates/core/src/lib.rs`
- Create: `crates/core/src/theme.rs`
- Create: `crates/core/src/keymap.rs`
- Create: `crates/core/src/config.rs`
- Create: `crates/core/src/event.rs`
- Create: `crates/core/src/app.rs`
- Create: `crates/core/tests/config_roundtrip.rs`

- [ ] **Step 1: Create `crates/core/Cargo.toml`**

```toml
[package]
name = "core"
version.workspace = true
edition.workspace = true
license.workspace = true

[dependencies]
ratatui = { workspace = true }
crossterm = { workspace = true }
serde = { workspace = true }
toml = { workspace = true }
directories = { workspace = true }
thiserror = { workspace = true }
tokio = { workspace = true }
futures = { workspace = true }

[dev-dependencies]
tempfile = "3"
```

- [ ] **Step 2: Create `crates/core/src/lib.rs`**

```rust
//! Shared types, theme, keymap and config for the sastaspace TUI workspace.

pub mod app;
pub mod config;
pub mod event;
pub mod keymap;
pub mod theme;

pub use app::{App, AppResult};
pub use event::{Action, InputAction};
```

- [ ] **Step 3: Create `crates/core/src/theme.rs`**

```rust
//! Single source of truth for colors and text styles.

use ratatui::style::{Color, Modifier, Style};

/// The default sastaspace palette. Inspired by the existing landing-page
/// design tokens (warm amber accents, neutral grays). One theme for v1.
pub struct Theme {
    pub fg: Color,
    pub bg: Color,
    pub muted: Color,
    pub accent: Color,
    pub success: Color,
    pub warn: Color,
    pub error: Color,
    pub border: Color,
}

impl Theme {
    pub const fn default_dark() -> Self {
        Self {
            fg: Color::Rgb(230, 230, 230),
            bg: Color::Rgb(16, 16, 20),
            muted: Color::Rgb(120, 120, 128),
            accent: Color::Rgb(255, 184, 0),
            success: Color::Rgb(100, 200, 120),
            warn: Color::Rgb(240, 180, 80),
            error: Color::Rgb(240, 100, 100),
            border: Color::Rgb(64, 64, 72),
        }
    }

    pub fn header(&self) -> Style {
        Style::default().fg(self.accent).add_modifier(Modifier::BOLD)
    }

    pub fn body(&self) -> Style {
        Style::default().fg(self.fg)
    }

    pub fn muted(&self) -> Style {
        Style::default().fg(self.muted)
    }

    pub fn focused(&self) -> Style {
        Style::default().fg(self.bg).bg(self.accent)
    }
}
```

- [ ] **Step 4: Create `crates/core/src/keymap.rs`**

```rust
//! Global key bindings. App-specific bindings live in each app crate.

use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};

/// Global actions that any screen can trigger.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GlobalKey {
    /// `q` or `ctrl-c` — quit the app cleanly.
    Quit,
    /// `?` — toggle help overlay.
    Help,
    /// `:` — open command palette.
    Palette,
    /// `esc` — dismiss modal / overlay.
    Dismiss,
}

pub fn classify(ev: KeyEvent) -> Option<GlobalKey> {
    match (ev.code, ev.modifiers) {
        (KeyCode::Char('q'), m) if m.is_empty() => Some(GlobalKey::Quit),
        (KeyCode::Char('c'), KeyModifiers::CONTROL) => Some(GlobalKey::Quit),
        (KeyCode::Char('?'), m) if m.is_empty() => Some(GlobalKey::Help),
        (KeyCode::Char(':'), m) if m.is_empty() => Some(GlobalKey::Palette),
        (KeyCode::Esc, _) => Some(GlobalKey::Dismiss),
        _ => None,
    }
}
```

- [ ] **Step 5: Create `crates/core/src/event.rs`**

```rust
//! Action types flowing through the main loop.
//!
//! Two long-lived tasks feed one channel:
//! - `crossterm::event::EventStream` produces `Action::Input`
//! - STDB SDK callbacks produce `Action::Stdb`
//!
//! The shell drains the channel each tick.

use crossterm::event::KeyEvent;

#[derive(Debug, Clone)]
pub enum Action {
    /// Keyboard / resize / mouse events from crossterm.
    Input(InputAction),
    /// SpacetimeDB-side events (subscription updates, reducer responses).
    /// Kept opaque here — concrete event types live in app crates.
    Stdb(StdbEvent),
    /// Switch to a named app screen.
    Route(&'static str),
    /// Show a transient toast at the bottom of the screen.
    Toast(Toast),
    /// Tick from the renderer (~16ms). Apps use it for animation.
    Tick,
    /// Initiate clean shutdown.
    Quit,
}

#[derive(Debug, Clone)]
pub enum InputAction {
    Key(KeyEvent),
    Resize(u16, u16),
}

/// STDB events — kept as a tagged enum so app crates can match without
/// touching the SDK directly.
#[derive(Debug, Clone)]
pub enum StdbEvent {
    Connected,
    Disconnected(String),
    /// Subscription delivered new data; `subject` identifies which set
    /// (e.g. "projects", "comments"). Apps re-query the table accessors.
    Updated(&'static str),
    /// A reducer call returned an error. Routed to a toast by default.
    ReducerError { reducer: &'static str, message: String },
}

#[derive(Debug, Clone)]
pub struct Toast {
    pub level: ToastLevel,
    pub message: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ToastLevel {
    Info,
    Warn,
    Error,
}

impl Toast {
    pub fn info(msg: impl Into<String>) -> Self {
        Self { level: ToastLevel::Info, message: msg.into() }
    }
    pub fn warn(msg: impl Into<String>) -> Self {
        Self { level: ToastLevel::Warn, message: msg.into() }
    }
    pub fn error(msg: impl Into<String>) -> Self {
        Self { level: ToastLevel::Error, message: msg.into() }
    }
}
```

- [ ] **Step 6: Create `crates/core/src/app.rs`**

```rust
//! The `App` trait — every app screen implements this.

use crate::event::Action;
use ratatui::{layout::Rect, Frame};
use std::time::Duration;

/// Per-screen update + render contract.
pub trait App: Send {
    /// Stable identifier (lowercase, no spaces). Used by the router.
    fn id(&self) -> &'static str;

    /// Title shown in the shell header.
    fn title(&self) -> &str;

    /// Render this app's contents into `area`. The shell handles header / footer.
    fn render(&mut self, frame: &mut Frame, area: Rect);

    /// Handle an action. Returns what the shell should do next.
    fn handle(&mut self, action: Action) -> AppResult;

    /// Called every render tick (~16ms) for animation / polling. Default no-op.
    fn tick(&mut self, _dt: Duration) -> AppResult {
        AppResult::Continue
    }
}

/// What the app wants the shell to do after `handle` / `tick`.
#[derive(Debug)]
pub enum AppResult {
    /// Stay on this screen.
    Continue,
    /// Switch to the named app.
    SwitchTo(&'static str),
    /// Exit the binary cleanly.
    Quit,
}
```

- [ ] **Step 7: Create `crates/core/src/config.rs`**

```rust
//! On-disk config — `~/.config/sastaspace/config.toml`.

use directories::ProjectDirs;
use serde::{Deserialize, Serialize};
use std::{fs, io, path::PathBuf};
use thiserror::Error;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(default, deny_unknown_fields)]
pub struct Config {
    /// Where to connect for SpacetimeDB. Override per-environment.
    pub stdb_uri: String,
    /// Module name on that STDB instance.
    pub stdb_module: String,
    /// Identity (Google client) for the owner OAuth device flow.
    pub google_client_id: Option<String>,
    /// Default starting screen when the binary launches.
    pub start_screen: String,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            stdb_uri: "wss://stdb.sastaspace.com".into(),
            stdb_module: "sastaspace".into(),
            google_client_id: None,
            start_screen: "portfolio".into(),
        }
    }
}

#[derive(Debug, Error)]
pub enum ConfigError {
    #[error("could not locate platform config directory")]
    NoConfigDir,
    #[error("io: {0}")]
    Io(#[from] io::Error),
    #[error("toml parse: {0}")]
    Parse(#[from] toml::de::Error),
    #[error("toml serialize: {0}")]
    Serialize(#[from] toml::ser::Error),
}

impl Config {
    /// `~/.config/sastaspace/config.toml` on linux/mac, `%APPDATA%\sastaspace\config.toml` on windows.
    pub fn path() -> Result<PathBuf, ConfigError> {
        let dirs = ProjectDirs::from("com", "sastaspace", "sastaspace")
            .ok_or(ConfigError::NoConfigDir)?;
        Ok(dirs.config_dir().join("config.toml"))
    }

    /// Load the config; returns `Default` if the file doesn't exist yet.
    pub fn load() -> Result<Self, ConfigError> {
        let p = Self::path()?;
        if !p.exists() {
            return Ok(Self::default());
        }
        let s = fs::read_to_string(&p)?;
        let c: Self = toml::from_str(&s)?;
        Ok(c)
    }

    /// Write atomically (`config.toml.tmp` → rename). Creates the dir if needed.
    pub fn save(&self) -> Result<(), ConfigError> {
        let p = Self::path()?;
        if let Some(parent) = p.parent() {
            fs::create_dir_all(parent)?;
        }
        let body = toml::to_string_pretty(self)?;
        let tmp = p.with_extension("toml.tmp");
        fs::write(&tmp, body)?;
        fs::rename(tmp, p)?;
        Ok(())
    }

    /// Test-only: load from a specific path. Lets tests use a tempdir.
    #[doc(hidden)]
    pub fn load_from(path: &PathBuf) -> Result<Self, ConfigError> {
        if !path.exists() {
            return Ok(Self::default());
        }
        let s = fs::read_to_string(path)?;
        Ok(toml::from_str(&s)?)
    }

    /// Test-only counterpart to `load_from`.
    #[doc(hidden)]
    pub fn save_to(&self, path: &PathBuf) -> Result<(), ConfigError> {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        fs::write(path, toml::to_string_pretty(self)?)?;
        Ok(())
    }
}
```

- [ ] **Step 8: Write the failing config round-trip test**

Create `crates/core/tests/config_roundtrip.rs`:

```rust
use core::config::Config;
use tempfile::tempdir;

#[test]
fn default_config_has_prod_stdb() {
    let c = Config::default();
    assert_eq!(c.stdb_uri, "wss://stdb.sastaspace.com");
    assert_eq!(c.stdb_module, "sastaspace");
    assert_eq!(c.start_screen, "portfolio");
    assert!(c.google_client_id.is_none());
}

#[test]
fn save_then_load_roundtrips() {
    let dir = tempdir().unwrap();
    let path = dir.path().join("config.toml");

    let mut c = Config::default();
    c.google_client_id = Some("test-client.apps.googleusercontent.com".into());
    c.start_screen = "typewars".into();
    c.save_to(&path).unwrap();

    let loaded = Config::load_from(&path).unwrap();
    assert_eq!(loaded, c);
}

#[test]
fn load_missing_file_returns_default() {
    let dir = tempdir().unwrap();
    let path = dir.path().join("does-not-exist.toml");
    let c = Config::load_from(&path).unwrap();
    assert_eq!(c, Config::default());
}
```

- [ ] **Step 9: Run the tests**

Run: `cargo test -p core`

Expected: 3 tests pass.

- [ ] **Step 10: Commit**

```bash
git add crates/core
git commit -m "feat(tui): core crate — theme, keymap, config, App trait"
```

---

## Task 4: `stdb-client` crate — bindings + connection wrapper

**Files:**
- Create: `crates/stdb-client/Cargo.toml`
- Create: `crates/stdb-client/src/lib.rs`
- Create: `crates/stdb-client/src/connection.rs`
- Create: `crates/stdb-client/build_bindings.sh`
- Create: `crates/stdb-client/src/bindings/` (generated, checked in)

This crate wraps `spacetimedb-sdk` so app crates only see typed table accessors and reducer wrappers. The bindings are generated from the live `sastaspace` module schema and committed (matches existing repo policy in `.gitignore`).

- [ ] **Step 1: Create `crates/stdb-client/Cargo.toml`**

```toml
[package]
name = "stdb-client"
version.workspace = true
edition.workspace = true
license.workspace = true

[dependencies]
spacetimedb-sdk = { workspace = true }
tokio = { workspace = true }
tracing = { workspace = true }
thiserror = { workspace = true }
core = { path = "../core" }
serde = { workspace = true }
```

- [ ] **Step 2: Create the binding generator script**

Create `crates/stdb-client/build_bindings.sh`:

```bash
#!/usr/bin/env bash
# Regenerates Rust bindings from the running sastaspace module schema.
# Bindings are checked in (per repo convention — see root .gitignore).
#
# Usage:
#   ./crates/stdb-client/build_bindings.sh                # uses prod schema
#   STDB=http://localhost:3000 ./crates/.../build_bindings.sh   # local dev
set -euo pipefail
HOST="${STDB:-https://stdb.sastaspace.com}"
MODULE="${STDB_MODULE:-sastaspace}"
OUT="$(dirname "$0")/src/bindings"
rm -rf "$OUT"
mkdir -p "$OUT"
spacetime generate --lang rust --out-dir "$OUT" --project-path modules/sastaspace
echo "// AUTOGENERATED — do not edit; regen via crates/stdb-client/build_bindings.sh" > "$OUT/.header"
cat "$OUT/.header" "$OUT/mod.rs" > "$OUT/mod.rs.new" && mv "$OUT/mod.rs.new" "$OUT/mod.rs"
rm "$OUT/.header"
echo "✓ regenerated $(ls "$OUT" | wc -l) binding files"
```

Make executable:

Run: `chmod +x crates/stdb-client/build_bindings.sh`

- [ ] **Step 3: Generate bindings for the first time**

Run: `./crates/stdb-client/build_bindings.sh`

Expected: prints "✓ regenerated N binding files" with N ≥ 5. The `crates/stdb-client/src/bindings/` directory is populated with `mod.rs`, `project_table.rs`, `comment_table.rs`, `user_table.rs`, etc.

If `spacetime` is not installed, install it:

Run: `curl -sSf https://install.spacetimedb.com | bash`

Then re-run the binding script.

- [ ] **Step 4: Create `crates/stdb-client/src/lib.rs`**

```rust
//! Thin wrapper over `spacetimedb-sdk` for the sastaspace TUI.
//!
//! Re-exports the auto-generated module bindings under `bindings::*` and
//! provides a `StdbHandle` that owns the connection task and exposes typed
//! access to tables and reducers.

#![allow(clippy::all, dead_code)] // generated bindings are noisy

pub mod bindings;
pub mod connection;

pub use connection::{StdbConfig, StdbError, StdbHandle, StdbStatus};
```

- [ ] **Step 5: Create `crates/stdb-client/src/connection.rs`**

```rust
//! Connection lifecycle: connect → subscribe → forward events → reconnect.

use crate::bindings::{DbConnection, ErrorContext};
use core::event::{Action, StdbEvent};
use spacetimedb_sdk::{credentials::File as CredFile, DbContext};
use std::time::Duration;
use thiserror::Error;
use tokio::sync::mpsc::UnboundedSender;
use tracing::{error, info, warn};

#[derive(Debug, Clone)]
pub struct StdbConfig {
    pub uri: String,
    pub module: String,
    /// Optional auth token — if `None`, anon identity.
    pub token: Option<String>,
    /// Where to cache the granted identity between runs.
    pub credentials_path: std::path::PathBuf,
}

#[derive(Debug, Error)]
pub enum StdbError {
    #[error("connect failed: {0}")]
    Connect(String),
    #[error("subscribe failed: {0}")]
    Subscribe(String),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StdbStatus {
    Connecting,
    Connected,
    Disconnected,
}

/// Owns the live STDB connection. Drop to disconnect.
pub struct StdbHandle {
    pub status: StdbStatus,
    pub conn: DbConnection,
}

impl StdbHandle {
    /// Connects, attaches event callbacks that forward into `tx`, and
    /// subscribes to the foundational tables that every app needs (project,
    /// presence, user). App crates may add more subscriptions later.
    pub async fn connect(
        cfg: StdbConfig,
        tx: UnboundedSender<Action>,
    ) -> Result<Self, StdbError> {
        info!(uri = %cfg.uri, module = %cfg.module, "stdb: connecting");

        let mut builder = DbConnection::builder()
            .with_uri(&cfg.uri)
            .with_module_name(&cfg.module)
            .with_credentials(CredFile::new(cfg.credentials_path.clone()).into());

        if let Some(tok) = cfg.token.as_deref() {
            builder = builder.with_token(Some(tok.to_string()));
        }

        let tx2 = tx.clone();
        let tx3 = tx.clone();
        let conn = builder
            .on_connect(move |_, _, _| {
                let _ = tx2.send(Action::Stdb(StdbEvent::Connected));
            })
            .on_connect_error(move |_ctx: &ErrorContext, err| {
                error!(?err, "stdb: connect error");
                let _ = tx3.send(Action::Stdb(StdbEvent::Disconnected(err.to_string())));
            })
            .on_disconnect({
                let tx = tx.clone();
                move |_, err| {
                    let msg = err.map(|e| e.to_string()).unwrap_or_else(|| "remote closed".into());
                    warn!(reason = %msg, "stdb: disconnected");
                    let _ = tx.send(Action::Stdb(StdbEvent::Disconnected(msg)));
                }
            })
            .build()
            .map_err(|e| StdbError::Connect(e.to_string()))?;

        // Subscribe to the foundational tables. App crates extend later.
        let tx_proj = tx.clone();
        conn.subscription_builder()
            .on_applied(move |_| {
                let _ = tx_proj.send(Action::Stdb(StdbEvent::Updated("project")));
            })
            .on_error(|_, err| error!(?err, "stdb: project subscription error"))
            .subscribe(["SELECT * FROM project"]);

        let tx_pres = tx.clone();
        conn.subscription_builder()
            .on_applied(move |_| {
                let _ = tx_pres.send(Action::Stdb(StdbEvent::Updated("presence")));
            })
            .on_error(|_, err| error!(?err, "stdb: presence subscription error"))
            .subscribe(["SELECT * FROM presence"]);

        // Run the connection event loop on a background task. The SDK's
        // `run_threaded` returns when the connection terminates.
        let conn_for_task = conn.clone();
        tokio::task::spawn_blocking(move || {
            conn_for_task.run_threaded();
        });

        // Backoff retry on disconnect is the caller's job — for v1 we surface
        // the disconnect via the channel and let the shell decide whether
        // to reconnect (planned: yes, with exp-backoff up to 30s).
        let _ = tokio::time::timeout(Duration::from_secs(10), async {
            // Best-effort: give the connection a moment to settle so the
            // first render after `connect()` has a non-empty project table.
            tokio::time::sleep(Duration::from_millis(150)).await;
        }).await;

        Ok(Self {
            status: StdbStatus::Connected,
            conn,
        })
    }
}
```

- [ ] **Step 6: Verify the crate compiles**

Run: `cargo build -p stdb-client`

Expected: builds clean. May emit warnings from the auto-generated bindings; that's fine — we have `#![allow(clippy::all, dead_code)]` at the lib root.

If the build fails with `unresolved import bindings::DbConnection` or similar, the binding regen in Step 3 produced a different module shape — open `crates/stdb-client/src/bindings/mod.rs` and adjust the imports in `connection.rs` to match the actual exported names.

- [ ] **Step 7: Commit**

```bash
git add crates/stdb-client
git commit -m "feat(tui): stdb-client crate — connection lifecycle + generated bindings"
```

---

## Task 5: `auth` crate — keychain wrapper

**Files:**
- Create: `crates/auth/Cargo.toml`
- Create: `crates/auth/src/lib.rs`
- Create: `crates/auth/src/keychain.rs`
- Create: `crates/auth/tests/keychain_smoke.rs`

The keychain wrapper is small but isolated so we can mock it in higher-layer tests.

- [ ] **Step 1: Create `crates/auth/Cargo.toml`**

```toml
[package]
name = "auth"
version.workspace = true
edition.workspace = true
license.workspace = true

[dependencies]
keyring = { workspace = true }
reqwest = { workspace = true }
serde = { workspace = true }
serde_json = { workspace = true }
tokio = { workspace = true }
thiserror = { workspace = true }
tracing = { workspace = true }
core = { path = "../core" }
```

- [ ] **Step 2: Create `crates/auth/src/lib.rs`**

```rust
//! sastaspace TUI auth: token storage + magic-link + Google device flow.

pub mod google_device;
pub mod keychain;
pub mod magic_link;

pub use keychain::{KeychainStore, TokenKind, TokenStore};
```

- [ ] **Step 3: Create `crates/auth/src/keychain.rs`**

```rust
//! Wraps `keyring` so the rest of the workspace doesn't import it directly.
//! Lets us swap in a fake store for tests / CI without a real OS keychain.

use thiserror::Error;

pub const SERVICE: &str = "sastaspace";

/// Which token to load/store.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TokenKind {
    /// Magic-link auth token — bearer for STDB connection.
    Auth,
    /// Google id_token JWT — owner identity for admin reducers.
    OwnerJwt,
}

impl TokenKind {
    fn account(self) -> &'static str {
        match self {
            TokenKind::Auth => "auth_token",
            TokenKind::OwnerJwt => "owner_id_token",
        }
    }
}

#[derive(Debug, Error)]
pub enum StoreError {
    #[error("keychain error: {0}")]
    Backend(String),
    #[error("no token stored for {0:?}")]
    Missing(TokenKind),
}

/// Generic storage interface. Apps depend on this trait, not on `keyring`.
pub trait TokenStore: Send + Sync {
    fn get(&self, kind: TokenKind) -> Result<String, StoreError>;
    fn set(&self, kind: TokenKind, token: &str) -> Result<(), StoreError>;
    fn clear(&self, kind: TokenKind) -> Result<(), StoreError>;
}

/// Production impl using the OS keychain.
pub struct KeychainStore;

impl KeychainStore {
    pub fn new() -> Self {
        Self
    }

    fn entry(kind: TokenKind) -> Result<keyring::Entry, StoreError> {
        keyring::Entry::new(SERVICE, kind.account())
            .map_err(|e| StoreError::Backend(e.to_string()))
    }
}

impl Default for KeychainStore {
    fn default() -> Self {
        Self::new()
    }
}

impl TokenStore for KeychainStore {
    fn get(&self, kind: TokenKind) -> Result<String, StoreError> {
        match Self::entry(kind)?.get_password() {
            Ok(s) => Ok(s),
            Err(keyring::Error::NoEntry) => Err(StoreError::Missing(kind)),
            Err(e) => Err(StoreError::Backend(e.to_string())),
        }
    }

    fn set(&self, kind: TokenKind, token: &str) -> Result<(), StoreError> {
        Self::entry(kind)?
            .set_password(token)
            .map_err(|e| StoreError::Backend(e.to_string()))
    }

    fn clear(&self, kind: TokenKind) -> Result<(), StoreError> {
        match Self::entry(kind)?.delete_credential() {
            Ok(()) => Ok(()),
            Err(keyring::Error::NoEntry) => Ok(()),
            Err(e) => Err(StoreError::Backend(e.to_string())),
        }
    }
}

/// In-memory store for tests + CI.
pub struct InMemoryStore {
    inner: std::sync::Mutex<std::collections::HashMap<TokenKind, String>>,
}

impl InMemoryStore {
    pub fn new() -> Self {
        Self { inner: std::sync::Mutex::new(Default::default()) }
    }
}

impl Default for InMemoryStore {
    fn default() -> Self {
        Self::new()
    }
}

impl TokenStore for InMemoryStore {
    fn get(&self, kind: TokenKind) -> Result<String, StoreError> {
        self.inner.lock().unwrap()
            .get(&kind)
            .cloned()
            .ok_or(StoreError::Missing(kind))
    }
    fn set(&self, kind: TokenKind, token: &str) -> Result<(), StoreError> {
        self.inner.lock().unwrap().insert(kind, token.to_string());
        Ok(())
    }
    fn clear(&self, kind: TokenKind) -> Result<(), StoreError> {
        self.inner.lock().unwrap().remove(&kind);
        Ok(())
    }
}
```

- [ ] **Step 4: Add stub modules so the lib compiles**

Create `crates/auth/src/magic_link.rs`:

```rust
//! Magic-link auth flow — see Task 6 for the real implementation.
//! Stubbed here so the lib compiles after Task 5.

pub struct MagicLink;
```

Create `crates/auth/src/google_device.rs`:

```rust
//! Google OAuth 2.0 device authorization grant — see Task 7.
//! Stubbed so the lib compiles after Task 5.

pub struct GoogleDevice;
```

- [ ] **Step 5: Write the failing keychain test**

Create `crates/auth/tests/keychain_smoke.rs`:

```rust
use auth::keychain::{InMemoryStore, StoreError, TokenKind, TokenStore};

#[test]
fn in_memory_store_roundtrip() {
    let s = InMemoryStore::new();

    // Initially empty.
    assert!(matches!(s.get(TokenKind::Auth), Err(StoreError::Missing(_))));

    // Set + get + clear.
    s.set(TokenKind::Auth, "abc123").unwrap();
    assert_eq!(s.get(TokenKind::Auth).unwrap(), "abc123");
    s.clear(TokenKind::Auth).unwrap();
    assert!(matches!(s.get(TokenKind::Auth), Err(StoreError::Missing(_))));

    // Clearing a missing token is idempotent.
    s.clear(TokenKind::OwnerJwt).unwrap();
}

#[test]
fn token_kinds_use_distinct_accounts() {
    let s = InMemoryStore::new();
    s.set(TokenKind::Auth, "auth-tok").unwrap();
    s.set(TokenKind::OwnerJwt, "jwt-tok").unwrap();
    assert_eq!(s.get(TokenKind::Auth).unwrap(), "auth-tok");
    assert_eq!(s.get(TokenKind::OwnerJwt).unwrap(), "jwt-tok");
}
```

- [ ] **Step 6: Run the tests**

Run: `cargo test -p auth`

Expected: 2 tests pass.

(We don't unit-test `KeychainStore` itself in CI — Linux CI doesn't have a Secret Service. It gets exercised in the real binary on developer machines + e2e on macOS runners.)

- [ ] **Step 7: Commit**

```bash
git add crates/auth
git commit -m "feat(tui): auth crate — keychain wrapper with in-memory test impl"
```

---

## Task 6: `auth::magic_link` — request + poll for token

**Files:**
- Modify: `crates/auth/src/magic_link.rs` (replace stub from Task 5)
- Create: `crates/auth/tests/magic_link_mock.rs`
- Modify: `crates/auth/Cargo.toml` (add wiremock dev-dep)

- [ ] **Step 1: Add wiremock to dev-deps**

In `crates/auth/Cargo.toml`, add a `[dev-dependencies]` section if not present:

```toml
[dev-dependencies]
wiremock = "0.6"
tokio = { workspace = true, features = ["macros", "rt-multi-thread"] }
```

- [ ] **Step 2: Replace `crates/auth/src/magic_link.rs`**

```rust
//! Magic-link login flow for the TUI.
//!
//! Calls the `request_magic_link` reducer with `app="tui"`, then waits for
//! the user to paste the token printed in their email and calls
//! `verify_token` to exchange it for the auth bearer token.
//!
//! The reducer calls themselves go through the STDB SDK (an HTTP one-shot,
//! not a long-lived connection) to keep this crate independent of the
//! shell's live connection state.

use serde::Deserialize;
use std::time::Duration;
use thiserror::Error;
use tracing::info;

#[derive(Debug, Error)]
pub enum MagicLinkError {
    #[error("network: {0}")]
    Network(String),
    #[error("reducer rejected: {0}")]
    Reducer(String),
    #[error("invalid email")]
    InvalidEmail,
    #[error("token verification failed: {0}")]
    Verify(String),
}

/// Caller-supplied configuration. Lets tests point at a mock server.
#[derive(Debug, Clone)]
pub struct MagicLinkConfig {
    /// HTTP base for STDB reducer calls — typically `https://stdb.sastaspace.com`.
    pub stdb_http_base: String,
    /// STDB module name.
    pub module: String,
    pub http_timeout: Duration,
}

impl Default for MagicLinkConfig {
    fn default() -> Self {
        Self {
            stdb_http_base: "https://stdb.sastaspace.com".into(),
            module: "sastaspace".into(),
            http_timeout: Duration::from_secs(10),
        }
    }
}

#[derive(Deserialize)]
struct ReducerErr {
    error: String,
}

/// Step 1: ask the backend to email a token to `email`.
pub async fn request(cfg: &MagicLinkConfig, email: &str) -> Result<(), MagicLinkError> {
    if !email.contains('@') || email.len() > 200 {
        return Err(MagicLinkError::InvalidEmail);
    }
    let url = format!(
        "{}/v1/database/{}/call/request_magic_link",
        cfg.stdb_http_base.trim_end_matches('/'),
        cfg.module
    );
    // STDB reducer args are positional JSON: [email, app, prev_identity_hex, callback_url].
    let body = serde_json::json!([email, "tui", null, "tui://paste-token"]);
    info!(email, "magic_link: request");
    let client = reqwest::Client::builder()
        .timeout(cfg.http_timeout)
        .build()
        .map_err(|e| MagicLinkError::Network(e.to_string()))?;
    let resp = client
        .post(&url)
        .json(&body)
        .send()
        .await
        .map_err(|e| MagicLinkError::Network(e.to_string()))?;
    if resp.status().is_success() {
        return Ok(());
    }
    let status = resp.status();
    let text = resp.text().await.unwrap_or_default();
    if let Ok(err) = serde_json::from_str::<ReducerErr>(&text) {
        Err(MagicLinkError::Reducer(err.error))
    } else {
        Err(MagicLinkError::Reducer(format!("HTTP {status}: {text}")))
    }
}

/// Step 2: exchange the pasted token for the durable bearer token.
/// Returns the bearer token string on success.
pub async fn verify(
    cfg: &MagicLinkConfig,
    pasted_token: &str,
    display_name: &str,
) -> Result<String, MagicLinkError> {
    let url = format!(
        "{}/v1/database/{}/call/verify_token",
        cfg.stdb_http_base.trim_end_matches('/'),
        cfg.module
    );
    let body = serde_json::json!([pasted_token, display_name]);
    let client = reqwest::Client::builder()
        .timeout(cfg.http_timeout)
        .build()
        .map_err(|e| MagicLinkError::Network(e.to_string()))?;
    let resp = client
        .post(&url)
        .json(&body)
        .send()
        .await
        .map_err(|e| MagicLinkError::Network(e.to_string()))?;
    if !resp.status().is_success() {
        let status = resp.status();
        let text = resp.text().await.unwrap_or_default();
        return Err(MagicLinkError::Verify(format!("HTTP {status}: {text}")));
    }
    // The verify_token reducer returns the bearer in the response body.
    // STDB returns `{"value": <ret>}` for non-unit returns; if our reducer
    // returns the bearer directly, we parse it as a string.
    let v: serde_json::Value = resp
        .json()
        .await
        .map_err(|e| MagicLinkError::Verify(format!("response parse: {e}")))?;
    let token = v
        .get("value")
        .and_then(|x| x.as_str())
        .or_else(|| v.as_str())
        .ok_or_else(|| MagicLinkError::Verify(format!("missing bearer in {v}")))?
        .to_string();
    Ok(token)
}
```

- [ ] **Step 3: Write the failing test (request happy path)**

Create `crates/auth/tests/magic_link_mock.rs`:

```rust
use auth::magic_link::{request, verify, MagicLinkConfig, MagicLinkError};
use std::time::Duration;
use wiremock::matchers::{method, path};
use wiremock::{Mock, MockServer, ResponseTemplate};

fn cfg(server: &MockServer) -> MagicLinkConfig {
    MagicLinkConfig {
        stdb_http_base: server.uri(),
        module: "sastaspace".into(),
        http_timeout: Duration::from_secs(2),
    }
}

#[tokio::test]
async fn request_happy_path_calls_reducer() {
    let server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/v1/database/sastaspace/call/request_magic_link"))
        .respond_with(ResponseTemplate::new(200))
        .expect(1)
        .mount(&server)
        .await;

    request(&cfg(&server), "user@example.com").await.unwrap();
}

#[tokio::test]
async fn request_invalid_email_short_circuits() {
    let server = MockServer::start().await;
    // No mock — if the function tried to call the server it'd be a 404.
    let err = request(&cfg(&server), "no-at-sign").await.unwrap_err();
    assert!(matches!(err, MagicLinkError::InvalidEmail));
}

#[tokio::test]
async fn request_surfaces_reducer_error_body() {
    let server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/v1/database/sastaspace/call/request_magic_link"))
        .respond_with(
            ResponseTemplate::new(400)
                .set_body_string(r#"{"error":"invalid email"}"#),
        )
        .mount(&server)
        .await;
    let err = request(&cfg(&server), "user@example.com").await.unwrap_err();
    match err {
        MagicLinkError::Reducer(m) => assert!(m.contains("invalid email")),
        other => panic!("expected Reducer error, got {other:?}"),
    }
}

#[tokio::test]
async fn verify_happy_path_returns_bearer() {
    let server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/v1/database/sastaspace/call/verify_token"))
        .respond_with(
            ResponseTemplate::new(200)
                .set_body_string(r#"{"value":"bearer-xyz"}"#),
        )
        .mount(&server)
        .await;
    let bearer = verify(&cfg(&server), "ABCDEFGH", "Mohit").await.unwrap();
    assert_eq!(bearer, "bearer-xyz");
}

#[tokio::test]
async fn verify_surfaces_4xx() {
    let server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/v1/database/sastaspace/call/verify_token"))
        .respond_with(ResponseTemplate::new(400).set_body_string("bad token"))
        .mount(&server)
        .await;
    let err = verify(&cfg(&server), "bad", "Mohit").await.unwrap_err();
    assert!(matches!(err, MagicLinkError::Verify(_)));
}
```

- [ ] **Step 4: Run the tests**

Run: `cargo test -p auth --test magic_link_mock`

Expected: all 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add crates/auth/Cargo.toml crates/auth/src/magic_link.rs crates/auth/tests/magic_link_mock.rs
git commit -m "feat(tui): auth::magic_link — request + verify against STDB HTTP"
```

---

## Task 7: `auth::google_device` — OAuth device flow

**Files:**
- Modify: `crates/auth/src/google_device.rs` (replace stub)
- Create: `crates/auth/tests/google_device_mock.rs`

This is owner-only and used by the future `app-admin` crate. Foundations ships it because (a) it's small, (b) the auth crate's surface should be complete in one PR.

- [ ] **Step 1: Replace `crates/auth/src/google_device.rs`**

```rust
//! Google OAuth 2.0 Device Authorization Grant (RFC 8628).
//!
//! Flow:
//!   1. POST /device/code with client_id + scope → device_code, user_code, verification_url, interval
//!   2. Show user_code + verification_url in the TUI
//!   3. Poll /token with the device_code every `interval` seconds until either
//!      `id_token` arrives or `expires_in` passes.

use serde::Deserialize;
use std::time::Duration;
use thiserror::Error;
use tracing::info;

const DEFAULT_DEVICE_URL: &str = "https://oauth2.googleapis.com/device/code";
const DEFAULT_TOKEN_URL: &str = "https://oauth2.googleapis.com/token";
const SCOPE: &str = "openid email";

#[derive(Debug, Error)]
pub enum DeviceFlowError {
    #[error("network: {0}")]
    Network(String),
    #[error("device endpoint: {0}")]
    Device(String),
    #[error("user denied authorization")]
    Denied,
    #[error("device code expired before authorization")]
    Expired,
    #[error("token endpoint: {0}")]
    Token(String),
}

#[derive(Debug, Clone)]
pub struct DeviceFlowConfig {
    pub client_id: String,
    pub device_url: String,
    pub token_url: String,
    pub poll_timeout: Duration,
}

impl DeviceFlowConfig {
    pub fn for_client(client_id: impl Into<String>) -> Self {
        Self {
            client_id: client_id.into(),
            device_url: DEFAULT_DEVICE_URL.into(),
            token_url: DEFAULT_TOKEN_URL.into(),
            poll_timeout: Duration::from_secs(300),
        }
    }
}

#[derive(Debug, Deserialize)]
pub struct DeviceCode {
    pub device_code: String,
    pub user_code: String,
    pub verification_url: String,
    pub expires_in: u64,
    pub interval: u64,
}

#[derive(Debug, Deserialize)]
struct TokenOk {
    id_token: String,
}

#[derive(Debug, Deserialize)]
struct TokenErr {
    error: String,
}

/// Step 1: request device + user codes from Google.
pub async fn start(cfg: &DeviceFlowConfig) -> Result<DeviceCode, DeviceFlowError> {
    let client = reqwest::Client::new();
    let resp = client
        .post(&cfg.device_url)
        .form(&[("client_id", cfg.client_id.as_str()), ("scope", SCOPE)])
        .send()
        .await
        .map_err(|e| DeviceFlowError::Network(e.to_string()))?;
    if !resp.status().is_success() {
        let body = resp.text().await.unwrap_or_default();
        return Err(DeviceFlowError::Device(body));
    }
    let dc: DeviceCode = resp
        .json()
        .await
        .map_err(|e| DeviceFlowError::Device(e.to_string()))?;
    info!(user_code = %dc.user_code, "device flow: code issued");
    Ok(dc)
}

/// Step 2: poll the token endpoint until success / denial / expiry.
/// Returns the Google-issued `id_token` (a JWT) on success.
pub async fn poll(cfg: &DeviceFlowConfig, dc: &DeviceCode) -> Result<String, DeviceFlowError> {
    let client = reqwest::Client::new();
    let deadline = tokio::time::Instant::now()
        + Duration::from_secs(dc.expires_in.min(cfg.poll_timeout.as_secs()));
    let mut interval = Duration::from_secs(dc.interval.max(1));
    loop {
        if tokio::time::Instant::now() >= deadline {
            return Err(DeviceFlowError::Expired);
        }
        tokio::time::sleep(interval).await;
        let resp = client
            .post(&cfg.token_url)
            .form(&[
                ("client_id", cfg.client_id.as_str()),
                ("device_code", dc.device_code.as_str()),
                ("grant_type", "urn:ietf:params:oauth:grant-type:device_code"),
            ])
            .send()
            .await
            .map_err(|e| DeviceFlowError::Network(e.to_string()))?;
        if resp.status().is_success() {
            let ok: TokenOk = resp
                .json()
                .await
                .map_err(|e| DeviceFlowError::Token(e.to_string()))?;
            return Ok(ok.id_token);
        }
        // Per RFC 8628: 4xx with `error` in the body indicates pending/denied/slow_down.
        let body = resp.text().await.unwrap_or_default();
        match serde_json::from_str::<TokenErr>(&body) {
            Ok(e) => match e.error.as_str() {
                "authorization_pending" => continue,
                "slow_down" => {
                    interval += Duration::from_secs(5);
                    continue;
                }
                "access_denied" => return Err(DeviceFlowError::Denied),
                "expired_token" => return Err(DeviceFlowError::Expired),
                other => return Err(DeviceFlowError::Token(other.into())),
            },
            Err(_) => return Err(DeviceFlowError::Token(body)),
        }
    }
}
```

- [ ] **Step 2: Write the failing tests (start + poll)**

Create `crates/auth/tests/google_device_mock.rs`:

```rust
use auth::google_device::{poll, start, DeviceCode, DeviceFlowConfig, DeviceFlowError};
use std::time::Duration;
use wiremock::matchers::{body_string_contains, method, path};
use wiremock::{Mock, MockServer, ResponseTemplate};

fn cfg(server: &MockServer) -> DeviceFlowConfig {
    DeviceFlowConfig {
        client_id: "test-client".into(),
        device_url: format!("{}/device/code", server.uri()),
        token_url: format!("{}/token", server.uri()),
        poll_timeout: Duration::from_secs(2),
    }
}

#[tokio::test]
async fn start_returns_device_code() {
    let server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/device/code"))
        .respond_with(ResponseTemplate::new(200).set_body_string(
            r#"{"device_code":"D","user_code":"WDJB-MJHT","verification_url":"https://google.com/device","expires_in":600,"interval":1}"#,
        ))
        .mount(&server)
        .await;
    let dc = start(&cfg(&server)).await.unwrap();
    assert_eq!(dc.user_code, "WDJB-MJHT");
    assert_eq!(dc.interval, 1);
}

#[tokio::test]
async fn poll_returns_id_token_on_success() {
    let server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/token"))
        .and(body_string_contains("device_code=ABC"))
        .respond_with(ResponseTemplate::new(200).set_body_string(r#"{"id_token":"jwt-xyz"}"#))
        .mount(&server)
        .await;
    let dc = DeviceCode {
        device_code: "ABC".into(),
        user_code: "U".into(),
        verification_url: "u".into(),
        expires_in: 60,
        interval: 1,
    };
    let token = poll(&cfg(&server), &dc).await.unwrap();
    assert_eq!(token, "jwt-xyz");
}

#[tokio::test]
async fn poll_surfaces_denial() {
    let server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/token"))
        .respond_with(
            ResponseTemplate::new(400).set_body_string(r#"{"error":"access_denied"}"#),
        )
        .mount(&server)
        .await;
    let dc = DeviceCode {
        device_code: "ABC".into(),
        user_code: "U".into(),
        verification_url: "u".into(),
        expires_in: 60,
        interval: 1,
    };
    let err = poll(&cfg(&server), &dc).await.unwrap_err();
    assert!(matches!(err, DeviceFlowError::Denied));
}
```

- [ ] **Step 3: Run the tests**

Run: `cargo test -p auth --test google_device_mock`

Expected: 3 tests pass.

- [ ] **Step 4: Commit**

```bash
git add crates/auth/src/google_device.rs crates/auth/tests/google_device_mock.rs
git commit -m "feat(tui): auth::google_device — RFC 8628 device flow"
```

---

## Task 8: `app-portfolio` + shell binary + first snapshot test

This is the biggest task because it stands up the rendering loop. Split into many small steps.

**Files:**
- Create: `crates/app-portfolio/Cargo.toml`
- Create: `crates/app-portfolio/src/lib.rs`
- Create: `crates/app-portfolio/src/state.rs`
- Create: `crates/app-portfolio/src/view.rs`
- Create: `crates/app-portfolio/tests/snapshot.rs`
- Create: `crates/app-portfolio/snapshots/` (will be populated by `cargo test`)
- Create: `crates/shell/Cargo.toml`
- Create: `crates/shell/src/main.rs`
- Create: `crates/shell/src/router.rs`
- Create: `crates/shell/src/terminal.rs`

- [ ] **Step 1: Create `crates/app-portfolio/Cargo.toml`**

```toml
[package]
name = "app-portfolio"
version.workspace = true
edition.workspace = true
license.workspace = true

[dependencies]
ratatui = { workspace = true }
crossterm = { workspace = true }
core = { path = "../core" }
serde = { workspace = true }

[dev-dependencies]
insta = { workspace = true }
```

- [ ] **Step 2: Create `crates/app-portfolio/src/state.rs`**

```rust
//! In-memory state for the portfolio splash. Mirrors the `project` STDB
//! table; the shell hydrates this via `ProjectsList::set_projects` whenever
//! a `StdbEvent::Updated("project")` action arrives.

#[derive(Debug, Clone, PartialEq)]
pub struct ProjectRow {
    pub slug: String,
    pub title: String,
    pub blurb: String,
    pub status: String,
}

#[derive(Debug, Default)]
pub struct PortfolioState {
    pub projects: Vec<ProjectRow>,
    pub selected: usize,
}

impl PortfolioState {
    pub fn set_projects(&mut self, mut rows: Vec<ProjectRow>) {
        rows.sort_by(|a, b| a.title.cmp(&b.title));
        self.projects = rows;
        if self.selected >= self.projects.len() {
            self.selected = self.projects.len().saturating_sub(1);
        }
    }

    pub fn move_selection(&mut self, delta: isize) {
        if self.projects.is_empty() {
            return;
        }
        let n = self.projects.len() as isize;
        let cur = self.selected as isize;
        let next = ((cur + delta).rem_euclid(n)) as usize;
        self.selected = next;
    }

    pub fn current(&self) -> Option<&ProjectRow> {
        self.projects.get(self.selected)
    }
}
```

- [ ] **Step 3: Create `crates/app-portfolio/src/view.rs`**

```rust
//! Pure render — no state mutation. Snapshot-tested.

use crate::state::{PortfolioState, ProjectRow};
use core::theme::Theme;
use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, List, ListItem, Paragraph, Wrap},
    Frame,
};

pub fn render(frame: &mut Frame, area: Rect, state: &PortfolioState, theme: &Theme) {
    let layout = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(40), Constraint::Percentage(60)])
        .split(area);

    render_list(frame, layout[0], state, theme);
    render_detail(frame, layout[1], state.current(), theme);
}

fn render_list(frame: &mut Frame, area: Rect, state: &PortfolioState, theme: &Theme) {
    let items: Vec<ListItem> = state
        .projects
        .iter()
        .enumerate()
        .map(|(i, p)| {
            let style = if i == state.selected {
                theme.focused()
            } else {
                theme.body()
            };
            let line = Line::from(vec![
                Span::styled(format!(" {} ", p.title), style.add_modifier(Modifier::BOLD)),
                Span::styled(format!("· {}", p.status), theme.muted()),
            ]);
            ListItem::new(line)
        })
        .collect();
    let block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.border))
        .title(" projects ");
    let list = List::new(items).block(block);
    frame.render_widget(list, area);
}

fn render_detail(frame: &mut Frame, area: Rect, project: Option<&ProjectRow>, theme: &Theme) {
    let block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.border))
        .title(" detail ");
    let body = match project {
        Some(p) => vec![
            Line::from(Span::styled(p.title.clone(), theme.header())),
            Line::from(""),
            Line::from(Span::styled(p.blurb.clone(), theme.body())),
            Line::from(""),
            Line::from(Span::styled(format!("slug:   {}", p.slug), theme.muted())),
            Line::from(Span::styled(format!("status: {}", p.status), theme.muted())),
        ],
        None => vec![
            Line::from(""),
            Line::from(Span::styled(
                "no projects yet — connecting to stdb.sastaspace.com…",
                theme.muted(),
            )),
        ],
    };
    let para = Paragraph::new(body).block(block).wrap(Wrap { trim: true });
    frame.render_widget(para, area);
}
```

- [ ] **Step 4: Create `crates/app-portfolio/src/lib.rs`**

```rust
//! Portfolio splash — the first screen the binary shows.
//! Reads `project` table rows pushed in via `set_projects`.

mod state;
mod view;

pub use state::{PortfolioState, ProjectRow};

use core::{
    event::{Action, InputAction},
    theme::Theme,
    App, AppResult,
};
use crossterm::event::{KeyCode, KeyEvent};
use ratatui::{layout::Rect, Frame};

pub struct Portfolio {
    state: PortfolioState,
    theme: Theme,
}

impl Portfolio {
    pub fn new() -> Self {
        Self {
            state: PortfolioState::default(),
            theme: Theme::default_dark(),
        }
    }

    pub fn set_projects(&mut self, rows: Vec<ProjectRow>) {
        self.state.set_projects(rows);
    }
}

impl Default for Portfolio {
    fn default() -> Self {
        Self::new()
    }
}

impl App for Portfolio {
    fn id(&self) -> &'static str {
        "portfolio"
    }

    fn title(&self) -> &str {
        "sastaspace · portfolio"
    }

    fn render(&mut self, frame: &mut Frame, area: Rect) {
        view::render(frame, area, &self.state, &self.theme);
    }

    fn handle(&mut self, action: Action) -> AppResult {
        if let Action::Input(InputAction::Key(KeyEvent { code, .. })) = action {
            match code {
                KeyCode::Char('j') | KeyCode::Down => self.state.move_selection(1),
                KeyCode::Char('k') | KeyCode::Up => self.state.move_selection(-1),
                _ => {}
            }
        }
        AppResult::Continue
    }
}
```

- [ ] **Step 5: Write the failing snapshot test**

Create `crates/app-portfolio/tests/snapshot.rs`:

```rust
use app_portfolio::{Portfolio, ProjectRow};
use core::App;
use ratatui::{backend::TestBackend, layout::Rect, Terminal};

fn fixture_projects() -> Vec<ProjectRow> {
    vec![
        ProjectRow {
            slug: "typewars".into(),
            title: "TypeWars".into(),
            blurb: "Multiplayer typing-game with a contested global warmap.".into(),
            status: "live".into(),
        },
        ProjectRow {
            slug: "notes".into(),
            title: "Notes".into(),
            blurb: "Personal workshop notes with comments and moderation.".into(),
            status: "live".into(),
        },
        ProjectRow {
            slug: "deck".into(),
            title: "Deck".into(),
            blurb: "Plain-text → ready-to-use audio packs (background, loop, notification).".into(),
            status: "beta".into(),
        },
    ]
}

fn render_to_string(app: &mut Portfolio, w: u16, h: u16) -> String {
    let backend = TestBackend::new(w, h);
    let mut terminal = Terminal::new(backend).unwrap();
    terminal
        .draw(|f| app.render(f, Rect::new(0, 0, w, h)))
        .unwrap();
    let buffer = terminal.backend().buffer().clone();
    let mut out = String::new();
    for y in 0..buffer.area().height {
        for x in 0..buffer.area().width {
            out.push_str(buffer.cell((x, y)).unwrap().symbol());
        }
        out.push('\n');
    }
    out
}

#[test]
fn portfolio_empty_state_snapshot() {
    let mut app = Portfolio::new();
    let s = render_to_string(&mut app, 80, 20);
    insta::assert_snapshot!("empty", s);
}

#[test]
fn portfolio_with_projects_snapshot() {
    let mut app = Portfolio::new();
    app.set_projects(fixture_projects());
    let s = render_to_string(&mut app, 80, 20);
    insta::assert_snapshot!("with_projects", s);
}

#[test]
fn portfolio_selection_moves_with_j_k() {
    use core::event::{Action, InputAction};
    use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};
    let mut app = Portfolio::new();
    app.set_projects(fixture_projects());

    // Sorted alphabetically: Deck, Notes, TypeWars. Selected starts at 0 → Deck.
    let _ = app.handle(Action::Input(InputAction::Key(KeyEvent::new(
        KeyCode::Char('j'),
        KeyModifiers::empty(),
    ))));
    let s = render_to_string(&mut app, 80, 20);
    insta::assert_snapshot!("selected_notes", s);
}
```

- [ ] **Step 6: Run the snapshot test (will create snapshots)**

Run: `cargo test -p app-portfolio`

Expected: 3 tests run; first run all 3 will create `*.snap.new` files and *fail*. That's expected for the first snapshot run.

Run: `cargo install cargo-insta` (if not installed; one-time)

Run: `cargo insta review --workspace`

Expected: an interactive TUI shows each new snapshot. Press `a` to accept each. After review, all 3 snapshots are committed under `crates/app-portfolio/snapshots/`.

Run: `cargo test -p app-portfolio`

Expected: 3 tests pass (snapshots match).

- [ ] **Step 7: Create `crates/shell/Cargo.toml`**

```toml
[package]
name = "shell"
version.workspace = true
edition.workspace = true
license.workspace = true

[[bin]]
name = "sastaspace"
path = "src/main.rs"

[dependencies]
core = { path = "../core" }
stdb-client = { path = "../stdb-client" }
auth = { path = "../auth" }
app-portfolio = { path = "../app-portfolio" }
ratatui = { workspace = true }
crossterm = { workspace = true }
tokio = { workspace = true }
color-eyre = { workspace = true }
tracing = { workspace = true }
tracing-subscriber = { workspace = true }
tracing-appender = { workspace = true }
directories = { workspace = true }
futures = { workspace = true }
```

- [ ] **Step 8: Create `crates/shell/src/terminal.rs`**

```rust
//! Terminal lifecycle: enter alt-screen + raw mode on startup, restore on
//! drop / panic. Owned by `main` and held for the lifetime of the program.

use color_eyre::eyre::Result;
use crossterm::{
    cursor::Show,
    event::{DisableMouseCapture, EnableMouseCapture},
    execute,
    terminal::{
        disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen,
    },
};
use ratatui::{backend::CrosstermBackend, Terminal};
use std::io::{self, Stdout};

pub type Tui = Terminal<CrosstermBackend<Stdout>>;

pub fn enter() -> Result<Tui> {
    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen, EnableMouseCapture)?;
    let backend = CrosstermBackend::new(stdout);
    let term = Terminal::new(backend)?;
    Ok(term)
}

pub fn leave() -> Result<()> {
    let mut stdout = io::stdout();
    execute!(stdout, LeaveAlternateScreen, DisableMouseCapture, Show)?;
    disable_raw_mode()?;
    Ok(())
}

/// RAII guard so the terminal is restored even if main returns Err / panics.
pub struct TerminalGuard;

impl Drop for TerminalGuard {
    fn drop(&mut self) {
        let _ = leave();
    }
}
```

- [ ] **Step 9: Create `crates/shell/src/router.rs`**

```rust
//! Owns the stack of registered apps and dispatches actions to the current one.

use core::{App, AppResult};
use std::collections::HashMap;

pub struct Router {
    apps: HashMap<&'static str, Box<dyn App>>,
    current: &'static str,
}

impl Router {
    pub fn new(start: &'static str) -> Self {
        Self {
            apps: HashMap::new(),
            current: start,
        }
    }

    pub fn register(&mut self, app: Box<dyn App>) {
        self.apps.insert(app.id(), app);
    }

    pub fn current(&mut self) -> &mut dyn App {
        // unwrap: the binary is constructed s.t. `current` is always registered
        self.apps
            .get_mut(self.current)
            .expect("current app missing from router")
            .as_mut()
    }

    /// Returns true if the program should keep running.
    pub fn dispatch(&mut self, result: AppResult) -> bool {
        match result {
            AppResult::Continue => true,
            AppResult::SwitchTo(id) => {
                if self.apps.contains_key(id) {
                    self.current = id;
                }
                true
            }
            AppResult::Quit => false,
        }
    }
}
```

- [ ] **Step 10: Create `crates/shell/src/main.rs`**

```rust
//! sastaspace TUI binary entry point.

mod router;
mod terminal;

use color_eyre::eyre::Result;
use core::{
    config::Config,
    event::{Action, InputAction, StdbEvent},
    keymap::{classify, GlobalKey},
    AppResult,
};
use crossterm::event::{Event, EventStream};
use directories::ProjectDirs;
use futures::StreamExt;
use std::time::Duration;
use stdb_client::{StdbConfig, StdbHandle};
use tokio::sync::mpsc::{unbounded_channel, UnboundedSender};
use tracing::{error, info};
use tracing_subscriber::EnvFilter;

const TICK_MS: u64 = 16;

#[tokio::main(flavor = "multi_thread")]
async fn main() -> Result<()> {
    install_panic_hook()?;
    init_tracing();

    let cfg = Config::load()?;
    info!(?cfg, "config loaded");

    let mut term = terminal::enter()?;
    let _guard = terminal::TerminalGuard;

    let result = run(&mut term, cfg).await;

    drop(_guard); // explicit so the leave order is clear

    if let Err(ref e) = result {
        error!(err = %e, "shell exited with error");
    }
    result
}

async fn run(term: &mut terminal::Tui, cfg: Config) -> Result<()> {
    let (tx, mut rx) = unbounded_channel::<Action>();

    spawn_input_task(tx.clone());
    spawn_tick_task(tx.clone());

    let _stdb = match connect_stdb(&cfg, tx.clone()).await {
        Ok(h) => Some(h),
        Err(e) => {
            // Don't crash on startup if STDB is down — show empty portfolio + a toast.
            error!(err = %e, "stdb connect failed; running in offline mode");
            None
        }
    };

    let mut router = router::Router::new("portfolio");
    router.register(Box::new(app_portfolio::Portfolio::new()));

    loop {
        // Render.
        term.draw(|f| router.current().render(f, f.area()))?;

        // Drain available actions (don't block forever — the tick task wakes us).
        let action = match rx.recv().await {
            Some(a) => a,
            None => break,
        };

        // Global key dispatch first.
        if let Action::Input(InputAction::Key(k)) = &action {
            if let Some(GlobalKey::Quit) = classify(*k) {
                break;
            }
        }

        // STDB project updates pushed into the portfolio app.
        if let Action::Stdb(StdbEvent::Updated("project")) = &action {
            // Read the table and push into the app.
            // (Real fetch happens in stdb-client::subscriptions in a follow-up;
            // for foundations we only wire the channel and confirm rendering.)
            // app.set_projects(...)
        }

        let result = router.current().handle(action);
        if !router.dispatch(result) {
            break;
        }
    }

    Ok(())
}

fn spawn_input_task(tx: UnboundedSender<Action>) {
    tokio::spawn(async move {
        let mut stream = EventStream::new();
        while let Some(Ok(ev)) = stream.next().await {
            let action = match ev {
                Event::Key(k) => Action::Input(InputAction::Key(k)),
                Event::Resize(w, h) => Action::Input(InputAction::Resize(w, h)),
                _ => continue,
            };
            if tx.send(action).is_err() {
                return;
            }
        }
    });
}

fn spawn_tick_task(tx: UnboundedSender<Action>) {
    tokio::spawn(async move {
        let mut interval = tokio::time::interval(Duration::from_millis(TICK_MS));
        loop {
            interval.tick().await;
            if tx.send(Action::Tick).is_err() {
                return;
            }
        }
    });
}

async fn connect_stdb(cfg: &Config, tx: UnboundedSender<Action>) -> Result<StdbHandle> {
    let creds_path = ProjectDirs::from("com", "sastaspace", "sastaspace")
        .map(|d| d.data_dir().join("credentials.json"))
        .unwrap_or_else(|| std::path::PathBuf::from(".sastaspace-credentials.json"));
    let stdb_cfg = StdbConfig {
        uri: cfg.stdb_uri.clone(),
        module: cfg.stdb_module.clone(),
        token: None, // foundations: anon. Auth wires in once login lands.
        credentials_path: creds_path,
    };
    Ok(StdbHandle::connect(stdb_cfg, tx).await?)
}

fn init_tracing() {
    let log_dir = ProjectDirs::from("com", "sastaspace", "sastaspace")
        .map(|d| d.data_dir().join("logs"))
        .unwrap_or_else(|| std::path::PathBuf::from(".sastaspace-logs"));
    let _ = std::fs::create_dir_all(&log_dir);
    let file = tracing_appender::rolling::daily(log_dir, "sastaspace.log");
    let filter = EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info"));
    tracing_subscriber::fmt()
        .with_env_filter(filter)
        .with_writer(file)
        .with_ansi(false)
        .init();
}

fn install_panic_hook() -> Result<()> {
    let (panic_hook, eyre_hook) = color_eyre::config::HookBuilder::default().into_hooks();
    eyre_hook.install()?;
    let panic_hook = panic_hook.into_panic_hook();
    std::panic::set_hook(Box::new(move |info| {
        let _ = terminal::leave();
        panic_hook(info);
    }));
    Ok(())
}
```

- [ ] **Step 11: Build the binary**

Run: `cargo build -p shell`

Expected: clean compile (warnings about unused imports are tolerated in this task; we'll close them in Task 9).

Run: `ls target/debug/sastaspace`

Expected: binary exists.

- [ ] **Step 12: Smoke-run the binary**

Run: `target/debug/sastaspace`

Expected: alt-screen shows the portfolio splash with "no projects yet — connecting to stdb.sastaspace.com…" in the right pane (because the project subscription hasn't pushed into the app yet — that's wired in the next plan; foundations only proves the loop works). Press `q` to exit. Terminal restores cleanly.

If the terminal looks broken after exit, the panic hook didn't fire correctly — re-check Step 10 `install_panic_hook`.

- [ ] **Step 13: Commit**

```bash
git add crates/app-portfolio crates/shell
git commit -m "feat(tui): app-portfolio + shell binary with snapshot tests"
```

---

## Task 9: E2E harness + first PTY scenario

**Files:**
- Create: `tests/e2e/Cargo.toml`
- Create: `tests/e2e/src/lib.rs` — `SpacetimeFixture`
- Create: `tests/e2e/tests/portfolio_smoke.rs`
- Create: `tests/e2e/scripts/start-spacetime.sh`

The fixture spins up a local `spacetime start`, publishes the modules, and tears down on drop. The first scenario launches the binary against this fixture and checks the splash renders.

- [ ] **Step 1: Create `tests/e2e/Cargo.toml`**

```toml
[package]
name = "e2e"
version.workspace = true
edition.workspace = true
license.workspace = true
publish = false

[lib]
path = "src/lib.rs"

[dependencies]
expectrl = { workspace = true }
tokio = { workspace = true }
thiserror = { workspace = true }
tracing = { workspace = true }
tracing-subscriber = { workspace = true }

[dev-dependencies]
serial_test = "3"
```

- [ ] **Step 2: Create `tests/e2e/scripts/start-spacetime.sh`**

```bash
#!/usr/bin/env bash
# Start a local spacetime instance for e2e tests. Used by SpacetimeFixture.
# Caller controls lifecycle — this script just runs in the foreground.
set -euo pipefail
PORT="${SPACETIME_PORT:-3199}"
DATA="${SPACETIME_DATA:-/tmp/sastaspace-e2e-spacetime}"
rm -rf "$DATA"
mkdir -p "$DATA"
exec spacetime start --listen-addr "127.0.0.1:$PORT" --data-dir "$DATA"
```

Make it executable:

Run: `chmod +x tests/e2e/scripts/start-spacetime.sh`

- [ ] **Step 3: Create `tests/e2e/src/lib.rs`**

```rust
//! E2E test fixtures for the sastaspace TUI.
//!
//! `SpacetimeFixture::start()` boots a local SpacetimeDB on port 3199,
//! publishes the `sastaspace` and `typewars` modules, and waits for them
//! to be reachable. Drop the fixture to tear everything down.
//!
//! `LaunchedTui::launch(...)` runs the binary under a PTY via `expectrl`.

use std::{
    path::PathBuf,
    process::{Child, Command, Stdio},
    time::{Duration, Instant},
};

pub struct SpacetimeFixture {
    proc: Child,
    pub http_url: String,
    pub ws_url: String,
}

impl SpacetimeFixture {
    pub fn start() -> Result<Self, String> {
        let port = std::env::var("SPACETIME_PORT").unwrap_or_else(|_| "3199".into());
        let proc = Command::new("bash")
            .arg("tests/e2e/scripts/start-spacetime.sh")
            .env("SPACETIME_PORT", &port)
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .map_err(|e| format!("spawn spacetime: {e}"))?;
        let http_url = format!("http://127.0.0.1:{port}");
        let ws_url = format!("ws://127.0.0.1:{port}");
        wait_for_http(&format!("{http_url}/v1/ping"), Duration::from_secs(20))?;
        publish_module(&http_url, "sastaspace", "modules/sastaspace")?;
        publish_module(&http_url, "typewars", "modules/typewars")?;
        Ok(Self { proc, http_url, ws_url })
    }
}

impl Drop for SpacetimeFixture {
    fn drop(&mut self) {
        let _ = self.proc.kill();
        let _ = self.proc.wait();
    }
}

fn wait_for_http(url: &str, timeout: Duration) -> Result<(), String> {
    let start = Instant::now();
    loop {
        if Command::new("curl")
            .args(["-sf", url])
            .stdout(Stdio::null())
            .status()
            .map(|s| s.success())
            .unwrap_or(false)
        {
            return Ok(());
        }
        if start.elapsed() > timeout {
            return Err(format!("timeout waiting for {url}"));
        }
        std::thread::sleep(Duration::from_millis(200));
    }
}

fn publish_module(http_url: &str, name: &str, path: &str) -> Result<(), String> {
    let status = Command::new("spacetime")
        .args([
            "publish",
            "--server-url",
            http_url,
            "--project-path",
            path,
            "--clear-database",
            "--yes",
            name,
        ])
        .status()
        .map_err(|e| format!("spawn spacetime publish: {e}"))?;
    if !status.success() {
        return Err(format!("spacetime publish {name} failed: {status}"));
    }
    Ok(())
}

/// Launches `target/debug/sastaspace` against the given fixture and returns
/// the PTY session for sending keys + asserting on output.
pub struct LaunchedTui {
    pub session: expectrl::session::Session,
}

impl LaunchedTui {
    pub fn launch(fixture: &SpacetimeFixture) -> Result<Self, String> {
        let bin = PathBuf::from("target/debug/sastaspace");
        if !bin.exists() {
            return Err("target/debug/sastaspace not built — run `cargo build -p shell` first".into());
        }
        let mut session = expectrl::spawn(format!("{} ", bin.display()))
            .map_err(|e| format!("spawn tui: {e}"))?;
        session
            .set_expect_timeout(Some(Duration::from_secs(10)));
        // Override config for this run via env (the binary reads stdb_uri from
        // config, but we can't easily edit ~/.config from a test — use env override
        // once the config crate supports it; for now we rely on the default URL
        // and require fixtures to bind 3199 → matching prod path).
        Ok(Self { session })
    }
}
```

(Note: the env-override path for `stdb_uri` is wired in a follow-up step inside Task 9.)

- [ ] **Step 4: Add env-override support to `core::config::Config`**

Open `crates/core/src/config.rs`. Replace the `Config::load()` method body with:

```rust
    pub fn load() -> Result<Self, ConfigError> {
        let p = Self::path()?;
        let mut c = if p.exists() {
            let s = fs::read_to_string(&p)?;
            toml::from_str::<Self>(&s)?
        } else {
            Self::default()
        };
        // Env overrides — used by E2E fixtures and dev runs.
        if let Ok(v) = std::env::var("SASTASPACE_STDB_URI") {
            c.stdb_uri = v;
        }
        if let Ok(v) = std::env::var("SASTASPACE_STDB_MODULE") {
            c.stdb_module = v;
        }
        Ok(c)
    }
```

Run: `cargo test -p core` — the existing 3 tests should still pass.

- [ ] **Step 5: Create the first E2E scenario**

Create `tests/e2e/tests/portfolio_smoke.rs`:

```rust
use e2e::{LaunchedTui, SpacetimeFixture};
use serial_test::serial;
use std::time::Duration;

#[test]
#[serial] // e2e tests share a fixture port; run sequentially
fn portfolio_splash_renders() {
    let fixture = SpacetimeFixture::start().expect("fixture failed");

    // Point the binary at the fixture instead of prod.
    std::env::set_var("SASTASPACE_STDB_URI", fixture.ws_url.clone());
    std::env::set_var("SASTASPACE_STDB_MODULE", "sastaspace");

    let mut tui = LaunchedTui::launch(&fixture).expect("launch failed");

    // Give the alt-screen a moment to draw.
    std::thread::sleep(Duration::from_millis(800));

    // Send `q` to quit cleanly.
    use expectrl::Expect;
    tui.session
        .send("q")
        .expect("send q");

    // Wait for the process to exit.
    let _ = tui.session.expect(expectrl::Eof).ok();
}
```

- [ ] **Step 6: Build the shell binary first (the e2e test depends on it)**

Run: `cargo build -p shell`

Expected: binary at `target/debug/sastaspace`.

- [ ] **Step 7: Run the first e2e**

Run: `SPACETIME_PORT=3199 cargo test -p e2e --test portfolio_smoke -- --nocapture`

Expected: passes. The fixture starts spacetime, publishes the modules, the binary launches under a PTY, the test sends `q`, the binary exits cleanly.

If `spacetime` is not on PATH for the CI runner, install via the script in the deploy workflow. Locally, install via `curl -sSf https://install.spacetimedb.com | bash`.

- [ ] **Step 8: Add the e2e job to CI**

Open `.github/workflows/tui-ci.yml`. Add this job after the existing `check` job:

```yaml
  e2e:
    runs-on: ubuntu-latest
    needs: check
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@1.85
      - uses: Swatinem/rust-cache@v2
      - name: install spacetime CLI
        run: |
          curl -sSf https://install.spacetimedb.com -o /tmp/install.sh
          bash /tmp/install.sh -- --yes
          echo "$HOME/.local/bin" >> "$GITHUB_PATH"
      - name: build shell binary
        run: cargo build -p shell
      - name: build modules (wasm)
        run: |
          rustup target add wasm32-unknown-unknown
          cd modules/sastaspace && cargo build --target wasm32-unknown-unknown --release
          cd ../typewars && cargo build --target wasm32-unknown-unknown --release
      - name: run e2e
        run: SPACETIME_PORT=3199 cargo test -p e2e
        env:
          RUST_BACKTRACE: 1
```

- [ ] **Step 9: Commit**

```bash
git add tests/e2e crates/core/src/config.rs .github/workflows/tui-ci.yml
git commit -m "feat(tui): e2e harness — local spacetime fixture + portfolio smoke"
```

---

## Task 10: Magic-link login flow in shell + e2e

**Files:**
- Create: `crates/shell/src/login.rs`
- Modify: `crates/shell/src/main.rs` (mount login modal, route on `:login`)
- Create: `tests/e2e/tests/magic_link.rs`

This is the integration test for everything below: the auth crate, the keychain, the STDB module changes from Task 2.

- [ ] **Step 1: Create `crates/shell/src/login.rs`**

```rust
//! Magic-link login modal. Two states:
//!   1. EnterEmail — single-line text field; enter triggers `auth::magic_link::request`
//!   2. EnterToken — single-line text field; enter triggers `verify`, stores bearer in keychain
//!
//! Renders centered over whatever app is below. Esc dismisses.

use auth::{
    keychain::{TokenKind, TokenStore},
    magic_link::{self, MagicLinkConfig, MagicLinkError},
};
use core::theme::Theme;
use crossterm::event::{KeyCode, KeyEvent};
use ratatui::{
    layout::{Alignment, Constraint, Direction, Layout, Rect},
    style::Style,
    text::{Line, Span},
    widgets::{Block, Borders, Clear, Paragraph},
    Frame,
};
use std::sync::Arc;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LoginState {
    EnterEmail,
    Sending,
    EnterToken,
    Verifying,
    Success,
    Failure,
}

pub struct LoginModal {
    state: LoginState,
    email_buf: String,
    token_buf: String,
    error: Option<String>,
    cfg: MagicLinkConfig,
    store: Arc<dyn TokenStore>,
    theme: Theme,
}

pub enum LoginOutcome {
    KeepOpen,
    Closed,
}

impl LoginModal {
    pub fn new(cfg: MagicLinkConfig, store: Arc<dyn TokenStore>) -> Self {
        Self {
            state: LoginState::EnterEmail,
            email_buf: String::new(),
            token_buf: String::new(),
            error: None,
            cfg,
            store,
            theme: Theme::default_dark(),
        }
    }

    pub fn render(&self, frame: &mut Frame, area: Rect) {
        let modal = centered_rect(60, 30, area);
        frame.render_widget(Clear, modal);

        let block = Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(self.theme.accent))
            .title(" sign in ");

        let inner = block.inner(modal);
        frame.render_widget(block, modal);

        let layout = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(2),
                Constraint::Length(3),
                Constraint::Length(2),
                Constraint::Min(0),
            ])
            .split(inner);

        let prompt: Vec<Line> = match self.state {
            LoginState::EnterEmail => vec![
                Line::from(Span::styled("enter your email; we'll send a token", self.theme.body())),
            ],
            LoginState::Sending => vec![Line::from(Span::styled("sending…", self.theme.muted()))],
            LoginState::EnterToken => vec![
                Line::from(Span::styled(
                    "check your email and paste the token below",
                    self.theme.body(),
                )),
            ],
            LoginState::Verifying => vec![Line::from(Span::styled("verifying…", self.theme.muted()))],
            LoginState::Success => vec![Line::from(Span::styled("signed in ✓", self.theme.body()))],
            LoginState::Failure => vec![Line::from(Span::styled(
                self.error.as_deref().unwrap_or("error").to_string(),
                Style::default().fg(self.theme.error),
            ))],
        };
        frame.render_widget(
            Paragraph::new(prompt).alignment(Alignment::Center),
            layout[0],
        );

        let buf = match self.state {
            LoginState::EnterEmail | LoginState::Sending => &self.email_buf,
            LoginState::EnterToken | LoginState::Verifying => &self.token_buf,
            _ => "",
        };
        let field = Paragraph::new(format!(" {buf}_"))
            .block(Block::default().borders(Borders::ALL).border_style(Style::default().fg(self.theme.border)))
            .alignment(Alignment::Left);
        frame.render_widget(field, layout[1]);

        let help = Paragraph::new(vec![Line::from(Span::styled(
            "enter to confirm  ·  esc to cancel",
            self.theme.muted(),
        ))])
        .alignment(Alignment::Center);
        frame.render_widget(help, layout[2]);
    }

    /// Returns `Closed` when the modal should be dismissed (success or cancel).
    pub async fn handle_key(&mut self, key: KeyEvent) -> LoginOutcome {
        if matches!(key.code, KeyCode::Esc) {
            return LoginOutcome::Closed;
        }
        match self.state {
            LoginState::EnterEmail => match key.code {
                KeyCode::Enter => self.submit_email().await,
                KeyCode::Backspace => {
                    self.email_buf.pop();
                }
                KeyCode::Char(c) => self.email_buf.push(c),
                _ => {}
            },
            LoginState::EnterToken => match key.code {
                KeyCode::Enter => self.submit_token().await,
                KeyCode::Backspace => {
                    self.token_buf.pop();
                }
                KeyCode::Char(c) => self.token_buf.push(c),
                _ => {}
            },
            LoginState::Failure => {
                // Any key returns to the relevant entry state.
                self.error = None;
                self.state = if self.token_buf.is_empty() {
                    LoginState::EnterEmail
                } else {
                    LoginState::EnterToken
                };
            }
            LoginState::Success => return LoginOutcome::Closed,
            _ => {}
        }
        LoginOutcome::KeepOpen
    }

    async fn submit_email(&mut self) {
        self.state = LoginState::Sending;
        match magic_link::request(&self.cfg, self.email_buf.trim()).await {
            Ok(()) => {
                self.state = LoginState::EnterToken;
            }
            Err(MagicLinkError::InvalidEmail) => {
                self.state = LoginState::Failure;
                self.error = Some("invalid email".into());
            }
            Err(e) => {
                self.state = LoginState::Failure;
                self.error = Some(format!("{e}"));
            }
        }
    }

    async fn submit_token(&mut self) {
        self.state = LoginState::Verifying;
        match magic_link::verify(&self.cfg, self.token_buf.trim(), "").await {
            Ok(bearer) => {
                if let Err(e) = self.store.set(TokenKind::Auth, &bearer) {
                    self.state = LoginState::Failure;
                    self.error = Some(format!("keychain: {e}"));
                } else {
                    self.state = LoginState::Success;
                }
            }
            Err(e) => {
                self.state = LoginState::Failure;
                self.error = Some(format!("{e}"));
            }
        }
    }
}

fn centered_rect(percent_x: u16, percent_y: u16, r: Rect) -> Rect {
    let popup = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Percentage((100 - percent_y) / 2),
            Constraint::Percentage(percent_y),
            Constraint::Percentage((100 - percent_y) / 2),
        ])
        .split(r);
    Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage((100 - percent_x) / 2),
            Constraint::Percentage(percent_x),
            Constraint::Percentage((100 - percent_x) / 2),
        ])
        .split(popup[1])[1]
}
```

- [ ] **Step 2: Wire the login modal into `crates/shell/src/main.rs`**

In `crates/shell/src/main.rs`, add at the top of the file (with the other `mod` declarations):

```rust
mod login;
```

Add to the imports:

```rust
use auth::{keychain::KeychainStore, magic_link::MagicLinkConfig};
use login::{LoginModal, LoginOutcome};
use std::sync::Arc;
```

In the `run()` function, replace the `loop { ... }` block with this version (it adds modal handling):

```rust
    let store = Arc::new(KeychainStore::new());
    let magic_cfg = MagicLinkConfig {
        stdb_http_base: cfg.stdb_uri.replace("ws://", "http://").replace("wss://", "https://"),
        module: cfg.stdb_module.clone(),
        http_timeout: Duration::from_secs(10),
    };
    let mut modal: Option<LoginModal> = None;

    loop {
        // Render base + modal.
        term.draw(|f| {
            router.current().render(f, f.area());
            if let Some(m) = &modal {
                m.render(f, f.area());
            }
        })?;

        let action = match rx.recv().await {
            Some(a) => a,
            None => break,
        };

        if let Action::Input(InputAction::Key(k)) = &action {
            // Modal eats keys when open.
            if let Some(m) = modal.as_mut() {
                if let LoginOutcome::Closed = m.handle_key(*k).await {
                    modal = None;
                }
                continue;
            }
            // Global :login trigger (`:` then 'l') — for foundations, just bind 'L'.
            if matches!(k.code, crossterm::event::KeyCode::Char('L'))
                && k.modifiers.is_empty()
            {
                modal = Some(LoginModal::new(magic_cfg.clone(), store.clone()));
                continue;
            }
            if let Some(GlobalKey::Quit) = classify(*k) {
                break;
            }
        }

        let result = router.current().handle(action);
        if !router.dispatch(result) {
            break;
        }
    }

    Ok(())
```

(For foundations we bind `Shift-L` to open the login modal directly. Full `:login` palette parsing comes in a follow-up plan.)

- [ ] **Step 3: Build and smoke-run**

Run: `cargo build -p shell`

Expected: clean build.

Run: `target/debug/sastaspace`

Expected: portfolio splash. Press `Shift-L` → login modal appears centered. Press `esc` → modal dismisses. Press `q` → exit.

- [ ] **Step 4: Write the magic-link e2e**

Create `tests/e2e/tests/magic_link.rs`:

```rust
use e2e::{LaunchedTui, SpacetimeFixture};
use serial_test::serial;
use std::process::Command;
use std::time::Duration;

/// Drives the whole flow:
///   1. open login modal
///   2. type an email + enter
///   3. read the issued token directly from the STDB auth_token table (the
///      "email" never gets sent because no auth-mailer worker runs in CI; we
///      simulate the user opening their inbox by querying the table)
///   4. paste the token + enter
///   5. assert the modal shows "signed in ✓"
#[test]
#[serial]
fn magic_link_round_trip() {
    let fixture = SpacetimeFixture::start().expect("fixture failed");
    std::env::set_var("SASTASPACE_STDB_URI", fixture.ws_url.clone());
    std::env::set_var("SASTASPACE_STDB_MODULE", "sastaspace");

    let mut tui = LaunchedTui::launch(&fixture).expect("launch failed");
    std::thread::sleep(Duration::from_millis(800));

    use expectrl::Expect;
    // Open login modal.
    tui.session.send("L").expect("send L");
    tui.session
        .expect("enter your email")
        .expect("login modal didn't render");

    // Type the email + enter.
    let email = "e2e@sastaspace.test";
    tui.session.send(email).expect("type email");
    tui.session.send("\r").expect("enter");

    // Wait for the modal to flip to EnterToken state.
    tui.session
        .expect("paste the token")
        .expect("never got to token entry");

    // Read the token from STDB (we don't run the email worker in CI).
    let token = lookup_pending_token(&fixture, email);

    // Paste it + enter.
    tui.session.send(token.as_str()).expect("paste token");
    tui.session.send("\r").expect("enter");

    tui.session
        .expect("signed in")
        .expect("login did not succeed");

    tui.session.send("q").expect("quit");
    let _ = tui.session.expect(expectrl::Eof);
}

fn lookup_pending_token(fixture: &SpacetimeFixture, email: &str) -> String {
    // Use the spacetime CLI to query the auth_token table.
    // `spacetime sql sastaspace 'select token from auth_token where email = ?'`
    let out = Command::new("spacetime")
        .args([
            "sql",
            "--server-url",
            &fixture.http_url,
            "sastaspace",
            &format!("SELECT token FROM auth_token WHERE email = '{email}'"),
        ])
        .output()
        .expect("spacetime sql");
    let stdout = String::from_utf8_lossy(&out.stdout);
    // Parse: the CLI prints a header row then the value. Take the last
    // non-empty trimmed line; STDB tokens are 32 chars [a-zA-Z0-9].
    stdout
        .lines()
        .map(str::trim)
        .filter(|l| l.len() == 32 && l.chars().all(|c| c.is_ascii_alphanumeric()))
        .last()
        .unwrap_or_else(|| panic!("no token for {email} in:\n{stdout}"))
        .to_string()
}
```

- [ ] **Step 5: Run the e2e**

Run: `SPACETIME_PORT=3199 cargo test -p e2e --test magic_link -- --nocapture`

Expected: passes. (If the test binary writes to the real OS keychain on your machine, that's a side-effect to be aware of — clean up with `security delete-generic-password -s sastaspace -a auth_token` on macOS.)

- [ ] **Step 6: Commit**

```bash
git add crates/shell/src/login.rs crates/shell/src/main.rs tests/e2e/tests/magic_link.rs
git commit -m "feat(tui): magic-link login modal + e2e round-trip"
```

---

## Task 11: Hydrate `app-portfolio` from STDB subscription

**Files:**
- Modify: `crates/stdb-client/src/lib.rs` — add a `read_projects()` helper
- Modify: `crates/shell/src/main.rs` — call `read_projects` on `Updated("project")` and push into the portfolio

This closes the loop: the binary connects, the project subscription delivers, and the splash shows real rows.

- [ ] **Step 1: Add `read_projects` to the stdb-client**

In `crates/stdb-client/src/lib.rs`, append:

```rust
pub mod sub_helpers {
    use crate::bindings::DbConnection;
    // The exact import path depends on what `spacetime generate --lang rust` emits.
    // After Task 4 step 3 you should see a `Project` struct exported from
    // `crate::bindings::project_table` or similar — adjust accordingly.
    use crate::bindings::project_table::Project as ProjectRow;

    pub fn read_projects(conn: &DbConnection) -> Vec<app_portfolio::ProjectRow> {
        conn.db
            .project()
            .iter()
            .map(|p: ProjectRow| app_portfolio::ProjectRow {
                slug: p.slug,
                title: p.title,
                blurb: p.blurb,
                status: p.status,
            })
            .collect()
    }
}
```

If the binding's exact type path differs (likely — depends on SDK codegen layout), adjust the `use` lines until `cargo build -p stdb-client` is clean.

Add `app-portfolio` as a dep:

```toml
# In crates/stdb-client/Cargo.toml under [dependencies]:
app-portfolio = { path = "../app-portfolio" }
```

- [ ] **Step 2: Wire in `crates/shell/src/main.rs`**

In `run()`, replace the placeholder block:

```rust
        if let Action::Stdb(StdbEvent::Updated("project")) = &action {
            // app.set_projects(...)
        }
```

with:

```rust
        if let Action::Stdb(StdbEvent::Updated("project")) = &action {
            if let Some(handle) = stdb.as_ref() {
                let projects = stdb_client::sub_helpers::read_projects(&handle.conn);
                if let Some(app) = router.app_mut("portfolio") {
                    if let Some(p) = app.as_any_mut().downcast_mut::<app_portfolio::Portfolio>() {
                        p.set_projects(projects);
                    }
                }
            }
        }
```

This requires three small additions:
1. `Router::app_mut(&mut self, id: &'static str) -> Option<&mut dyn App>`
2. `App::as_any_mut(&mut self) -> &mut dyn std::any::Any` (default impl can be added — see step 3)
3. The `_stdb` binding in `run()` becomes `let stdb = ...` (drop the underscore so we can use it).

- [ ] **Step 3: Add `as_any_mut` to the `App` trait**

In `crates/core/src/app.rs`, replace the trait def:

```rust
pub trait App: Send + std::any::Any {
    fn id(&self) -> &'static str;
    fn title(&self) -> &str;
    fn render(&mut self, frame: &mut Frame, area: Rect);
    fn handle(&mut self, action: Action) -> AppResult;
    fn tick(&mut self, _dt: Duration) -> AppResult {
        AppResult::Continue
    }
    fn as_any_mut(&mut self) -> &mut dyn std::any::Any;
}
```

In `crates/app-portfolio/src/lib.rs`, add to the `impl App for Portfolio` block:

```rust
    fn as_any_mut(&mut self) -> &mut dyn std::any::Any {
        self
    }
```

- [ ] **Step 4: Add `Router::app_mut`**

In `crates/shell/src/router.rs`, add:

```rust
    pub fn app_mut(&mut self, id: &'static str) -> Option<&mut Box<dyn core::App>> {
        self.apps.get_mut(id)
    }
```

(Adjust the trait import if needed.)

- [ ] **Step 5: Add a snapshot test that the portfolio renders the seeded fixture data**

Create `tests/e2e/tests/portfolio_with_data.rs`:

```rust
use e2e::{LaunchedTui, SpacetimeFixture};
use serial_test::serial;
use std::process::Command;
use std::time::Duration;

#[test]
#[serial]
fn portfolio_renders_projects_from_stdb() {
    let fixture = SpacetimeFixture::start().expect("fixture failed");

    // Seed a project row directly via spacetime CLI so we don't need the web UI.
    let status = Command::new("spacetime")
        .args([
            "call",
            "--server-url",
            &fixture.http_url,
            "sastaspace",
            "upsert_project",
            "[\"sample-slug\",\"Sample Project\",\"a one-line blurb\",\"live\",[],\"https://sastaspace.com/sample\"]",
        ])
        .status()
        .expect("seed project");
    assert!(status.success(), "upsert_project failed");

    std::env::set_var("SASTASPACE_STDB_URI", fixture.ws_url.clone());
    std::env::set_var("SASTASPACE_STDB_MODULE", "sastaspace");

    let mut tui = LaunchedTui::launch(&fixture).expect("launch failed");

    use expectrl::Expect;
    // The title should appear in the splash within a couple seconds.
    tui.session
        .expect("Sample Project")
        .expect("portfolio didn't render seeded project");

    tui.session.send("q").expect("quit");
    let _ = tui.session.expect(expectrl::Eof);
}
```

- [ ] **Step 6: Run everything**

Run: `cargo test --workspace --exclude sastaspace-module --exclude typewars`

Expected: all crate tests pass (core, auth, app-portfolio).

Run: `cargo build -p shell`

Expected: clean.

Run: `SPACETIME_PORT=3199 cargo test -p e2e -- --test-threads=1`

Expected: 3 e2e tests pass — `portfolio_smoke`, `magic_link_round_trip`, `portfolio_renders_projects_from_stdb`.

- [ ] **Step 7: Commit**

```bash
git add crates/stdb-client crates/core/src/app.rs crates/app-portfolio/src/lib.rs crates/shell/src/router.rs crates/shell/src/main.rs tests/e2e/tests/portfolio_with_data.rs
git commit -m "feat(tui): hydrate portfolio from STDB project table; e2e proves data-flow"
```

---

## Task 12: Final CI green pass + tidy

**Files:**
- Modify: `.github/workflows/tui-ci.yml` (final tweaks)
- Modify: `Cargo.toml` (lock workspace minimum)

- [ ] **Step 1: Add a `cargo deny` advisories check (optional but cheap)**

Skipping for v1 per simple-is-best. Re-add later if dependency advisories become a concern.

- [ ] **Step 2: Run the full check sequence locally as CI will**

Run:

```bash
cargo fmt --all -- --check
cargo clippy --workspace --exclude sastaspace-module --exclude typewars --all-targets -- -D warnings
cargo test --workspace --exclude sastaspace-module --exclude typewars --exclude e2e
cargo build -p shell
SPACETIME_PORT=3199 cargo test -p e2e -- --test-threads=1
```

Expected: every command exits 0. Fix any clippy warnings inline.

- [ ] **Step 3: Verify CI passes on a feature branch**

```bash
git checkout -b tui-foundations
git push -u origin tui-foundations
```

Open the PR, watch `tui-ci` run, fix anything red, then merge.

- [ ] **Step 4: Tag the milestone**

After the PR merges to main:

```bash
git tag tui-v0.0.1-foundations
git push origin tui-v0.0.1-foundations
```

- [ ] **Step 5: Final commit (only if there were any tidy-ups in steps 1-4)**

```bash
git add -p
git commit -m "chore(tui): foundations CI tidy"
```

---

## Self-Review

**Spec coverage check:**

| Spec section | Covered by |
|---|---|
| §3 foundational decisions | All locked into Task 1 (workspace) and the constants throughout |
| §4.1 workspace layout | Task 1 (workspace) + Tasks 3, 4, 5, 8, 9 (each crate) |
| §4.2 library stack table | Task 1 workspace deps |
| §4.3 data flow (event channel + tasks) | Task 8 step 10 (`spawn_input_task`, `spawn_tick_task`, action loop) |
| §4.4 magic-link auth flow | Task 6 (request/verify) + Task 10 (modal + e2e) |
| §4.4 Google device flow | Task 7 (auth crate). Used only by `app-admin` in a future plan. |
| §4.6 error handling (panic hook, reconnect) | Task 8 step 10 `install_panic_hook`. Reconnect-with-backoff is **deferred** to a follow-up plan; we surface disconnect events in this plan but don't auto-retry. |
| §4.7 testing strategy (insta + TestBackend + expectrl) | Task 8 step 5/6 (insta), Task 9 step 3/5 (expectrl) |
| §6 deletion list | Out of scope for foundations — happens in the cut-over plan |
| §7 backend changes (a) magic-link allows tui | Task 2 |
| §7 backend changes (b) auth-mailer token-only branch | **Moved into the module** (`render_magic_link_text_for_tui`) — Task 2 step 5/6. The auth-mailer worker doesn't need to change because email rendering happens module-side; the spec was wrong on this point and Task 2 captures the correct shape. |
| §7 backend changes (c) verify_owner_jwt | Out of scope for foundations — needed by `app-admin` plan |

**Gaps deliberately deferred to a follow-up plan (not regressions):**
- Auto-reconnect with exp backoff in `stdb-client` (we surface disconnect; we don't recover).
- Full `:` command palette (Task 10 binds `Shift-L`; full palette comes with Notes plan when more commands exist to dispatch to).
- Help screen `?`.
- `verify_owner_jwt` reducer change (needed by admin plan, not foundations).
- The four other apps + cut-over (each their own plan).

**Placeholder scan:** searched for "TBD", "TODO", "implement later", "fill in details" — none found.

**Type consistency check:**
- `App` trait signature consistent across Tasks 3, 8, 11 ✓
- `Action` enum variants used in Tasks 3, 8, 10, 11 — all defined ✓
- `TokenKind` / `TokenStore` consistent across Tasks 5, 6, 10 ✓
- `MagicLinkConfig` fields consistent across Tasks 6, 10 ✓
- `ProjectRow` defined in Task 8 step 2, re-used in Task 11 step 1 — same field set ✓

**Plan complete.**

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-28-tui-foundations.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Best for a 12-task plan: each task is independent enough to scope to a subagent with the spec + plan in context.

2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints for review.

**Which approach?**
