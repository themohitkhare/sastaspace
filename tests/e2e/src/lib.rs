//! E2E test fixtures for the sastaspace TUI.
//!
//! `SpacetimeFixture::start()` boots a local SpacetimeDB on port 3199,
//! publishes the `sastaspace` and `typewars` modules, and waits for them
//! to be reachable. Drop the fixture to tear everything down.
//!
//! `LaunchedTui::launch(...)` runs the binary under a PTY via `expectrl`.
//!
//! Wasm publish strategy: tries in-tree wasm build first (using the
//! `RUSTC_FOR_WASM` env var to bypass Homebrew rustc on the dev machine),
//! then falls back to a pre-built sibling-checkout wasm if available.

use std::{
    io::Write,
    path::PathBuf,
    process::{Child, Command, Stdio},
    time::{Duration, Instant},
};

// ---------------------------------------------------------------------------
// ANSI-stripping expect helper
// ---------------------------------------------------------------------------

/// Wait up to `timeout` for `text` to appear in the PTY output after
/// stripping ANSI/VT100 escape sequences.
///
/// Ratatui renders to an alt-screen buffer with cursor-positioning escapes
/// that fragment text across non-contiguous bytes, so a plain string match
/// on the raw stream never succeeds. This helper accumulates raw bytes via
/// `session.try_read()` and checks the stripped output on each iteration.
///
/// Returns `Ok(())` when `text` is found, `Err(msg)` on timeout.
pub fn expect_ansi(
    session: &mut expectrl::session::Session,
    text: &str,
    timeout: Duration,
) -> Result<(), String> {
    // Drain the PTY stream in chunks until `text` appears in the ANSI-stripped
    // output.  We read up to 4 KiB every 100 ms; checking after each chunk
    // keeps latency low without busy-spinning.
    //
    // Reading continuously also unblocks the TUI's render loop when the PTY
    // output buffer is full (a common state after the initial 800 ms sleep).
    let deadline = std::time::Instant::now() + timeout;
    let mut buf: Vec<u8> = Vec::with_capacity(32 * 1024);

    // Use try_read (non-blocking) in a sleep-capped loop.  This is correct
    // here because try_read reads from the BufReader which already holds any
    // data the OS has delivered to the PTY master fd.
    let mut iters = 0u32;
    loop {
        iters += 1;
        // Drain all bytes currently available.
        let mut got_any = false;
        let mut chunk = [0u8; 4096];
        loop {
            match session.try_read(&mut chunk) {
                Ok(n) if n > 0 => {
                    buf.extend_from_slice(&chunk[..n]);
                    got_any = true;
                }
                _ => break,
            }
        }

        if iters % 20 == 1 {
            let stripped2 = strip_ansi_escapes::strip(&buf);
            let preview2 = String::from_utf8_lossy(&stripped2);
            let cap2 = preview2.len().min(80);
            eprintln!(
                "[expect_ansi] iter={iters} buf_raw={} got_any={got_any} preview={:?}",
                buf.len(),
                // Use char boundary safe slice
                {
                    let cap = preview2
                        .char_indices()
                        .map(|(i, _)| i)
                        .take_while(|&i| i <= cap2)
                        .last()
                        .unwrap_or(0);
                    &preview2[..cap]
                }
            );
        }

        // Check the full accumulated cleaned buffer.
        let clean = strip_ansi_escapes::strip(&buf);
        if let Ok(s) = std::str::from_utf8(&clean) {
            if s.contains(text) {
                return Ok(());
            }
        }

        if std::time::Instant::now() > deadline {
            let stripped = strip_ansi_escapes::strip(&buf);
            let preview = String::from_utf8_lossy(&stripped);
            let cap = preview
                .char_indices()
                .map(|(i, _)| i)
                .take_while(|&i| i <= 200)
                .last()
                .unwrap_or(0);
            return Err(format!(
                "timeout waiting for {text:?}; cleaned buf preview: {:?}",
                &preview[..cap]
            ));
        }

        // Only sleep when nothing arrived this iteration, to avoid busy-spinning
        // while still draining rapidly when data is flowing.
        if !got_any {
            std::thread::sleep(Duration::from_millis(50));
        }
    }
}

fn pick_free_port() -> u16 {
    let listener = std::net::TcpListener::bind("127.0.0.1:0").expect("bind ephemeral");
    let port = listener.local_addr().unwrap().port();
    drop(listener);
    port
}

/// Pre-built wasm in the sibling sastaspace checkout.
///
/// Fallback path for when in-tree wasm build fails. The dev machine has
/// `/opt/homebrew/bin/rustc` on PATH which lacks the wasm32 target; the
/// in-tree build path uses `RUSTC_FOR_WASM` to override that. If neither
/// approach works, this sibling path is tried last.
const SIBLING_WASM_SASTASPACE: &str =
    "/Users/mkhare/Development/sastaspace/modules/sastaspace/target/wasm32-unknown-unknown/release/sastaspace_module.wasm";
const SIBLING_WASM_TYPEWARS: &str =
    "/Users/mkhare/Development/sastaspace/modules/typewars/target/wasm32-unknown-unknown/release/typewars_module.wasm";

pub struct SpacetimeFixture {
    proc: Child,
    pub http_url: String,
    pub ws_url: String,
    /// JWT issued by the local STDB instance to the publisher identity.
    /// The publisher is the database owner, so this token can call all
    /// `assert_owner`-gated reducers (e.g. `upsert_project`).
    pub owner_token: String,
    /// Holds the tempdir alive until the fixture is dropped, then auto-deletes it.
    _data_dir: tempfile::TempDir,
    /// Temp file holding the owner's cli.toml config for `spacetime` commands.
    _owner_cfg: tempfile::NamedTempFile,
}

impl SpacetimeFixture {
    pub fn start() -> Result<Self, String> {
        let port = pick_free_port();
        // Resolve the spacetime binary: prefer PATH, fall back to known install location.
        let spacetime_bin = resolve_spacetime_bin()?;
        let listen_addr = format!("127.0.0.1:{port}");
        // Each fixture gets its own tempdir for the control-plane database so
        // consecutive runs do not share identity state (which causes 403 on re-publish).
        let data_dir = tempfile::TempDir::new().map_err(|e| format!("create tempdir: {e}"))?;
        let proc = Command::new(&spacetime_bin)
            .args([
                "start",
                "--listen-addr",
                &listen_addr,
                "--data-dir",
                data_dir.path().to_str().unwrap(),
                "--in-memory",
            ])
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .map_err(|e| format!("spawn spacetime start: {e}"))?;
        let http_url = format!("http://127.0.0.1:{port}");
        let ws_url = format!("ws://127.0.0.1:{port}");
        wait_for_http(&format!("{http_url}/v1/ping"), Duration::from_secs(20))?;

        // Obtain an owner identity from the local STDB.
        // POST /v1/identity returns {"identity": "...", "token": "..."}.
        // We publish WITH this token so the published database's owner matches.
        let owner_token = get_owner_token(&http_url)?;

        // Write a temporary cli.toml so `spacetime call` picks up the owner token.
        let mut owner_cfg = tempfile::Builder::new()
            .suffix(".toml")
            .tempfile()
            .map_err(|e| format!("create owner cfg tempfile: {e}"))?;
        let host = format!("127.0.0.1:{port}");
        write!(
            owner_cfg,
            "default_server = \"local\"\nspacetimedb_token = \"{token}\"\n\n[[server_configs]]\nnickname = \"local\"\nhost = \"{host}\"\nprotocol = \"http\"\n",
            token = owner_token,
            host = host,
        )
        .map_err(|e| format!("write owner cfg: {e}"))?;
        owner_cfg
            .flush()
            .map_err(|e| format!("flush owner cfg: {e}"))?;

        publish_module(
            &spacetime_bin,
            &http_url,
            &owner_token,
            owner_cfg.path(),
            "sastaspace",
            "modules/sastaspace",
            SIBLING_WASM_SASTASPACE,
        )?;
        publish_module(
            &spacetime_bin,
            &http_url,
            &owner_token,
            owner_cfg.path(),
            "typewars",
            "modules/typewars",
            SIBLING_WASM_TYPEWARS,
        )?;
        Ok(Self {
            proc,
            http_url,
            ws_url,
            owner_token,
            _data_dir: data_dir,
            _owner_cfg: owner_cfg,
        })
    }

    /// Return the path to the owner cli.toml config file.
    ///
    /// Useful for passing `--config-path` to `spacetime` sub-commands (e.g.
    /// `spacetime sql`) that require authentication.
    pub fn owner_cfg_path(&self) -> &std::path::Path {
        self._owner_cfg.path()
    }

    /// Call a reducer as the database owner (bypasses `assert_owner` checks).
    ///
    /// `args` is a JSON array string, e.g.
    /// `r#"["slug","Title","blurb","live",[],"https://example.com"]"#`
    pub fn call_as_owner(&self, database: &str, reducer: &str, args: &str) -> Result<(), String> {
        let bin = resolve_spacetime_bin()?;
        let status = Command::new(&bin)
            .args([
                "--config-path",
                self._owner_cfg.path().to_str().unwrap(),
                "call",
                "--server",
                &self.http_url,
                "--yes",
                database,
                reducer,
            ])
            // spacetime call accepts reducer args as individual positional args after the
            // reducer name. For structured payloads we pass them as a JSON array to the
            // HTTP API directly to avoid shell quoting issues. We use the raw CLI form
            // here — each JSON value is a separate arg.
            .args(parse_json_array_to_args(args)?)
            .status()
            .map_err(|e| format!("spawn spacetime call: {e}"))?;
        if !status.success() {
            return Err(format!(
                "spacetime call {database}::{reducer} failed: {status}"
            ));
        }
        Ok(())
    }
}

/// Parse a JSON array string into a Vec of string arguments for `spacetime call`.
/// e.g. `["slug","Title","blurb","live",[],"https://example.com"]` →
///      `["slug", "Title", "blurb", "live", "[]", "https://example.com"]`
fn parse_json_array_to_args(json: &str) -> Result<Vec<String>, String> {
    let v: serde_json::Value =
        serde_json::from_str(json).map_err(|e| format!("parse_json_array_to_args: {e}"))?;
    let arr = v
        .as_array()
        .ok_or_else(|| format!("expected JSON array, got: {json}"))?;
    Ok(arr
        .iter()
        .map(|v| match v {
            serde_json::Value::String(s) => s.clone(),
            other => other.to_string(),
        })
        .collect())
}

/// POST /v1/identity to the local STDB and return the issued JWT.
fn get_owner_token(http_url: &str) -> Result<String, String> {
    let output = Command::new("curl")
        .args(["-sf", "-X", "POST", &format!("{http_url}/v1/identity")])
        .output()
        .map_err(|e| format!("curl POST /v1/identity: {e}"))?;
    if !output.status.success() {
        return Err(format!(
            "POST /v1/identity failed: {}",
            String::from_utf8_lossy(&output.stderr)
        ));
    }
    let body = String::from_utf8_lossy(&output.stdout);
    // Body is {"identity":"...","token":"..."}
    let v: serde_json::Value =
        serde_json::from_str(&body).map_err(|e| format!("parse identity response: {e}: {body}"))?;
    v["token"]
        .as_str()
        .map(|s| s.to_string())
        .ok_or_else(|| format!("no 'token' field in identity response: {body}"))
}

/// Resolve the `spacetime` binary path.
/// Tries the system PATH first; if not found, falls back to the known local install path.
fn resolve_spacetime_bin() -> Result<std::path::PathBuf, String> {
    // `which` equivalent: check if `spacetime` resolves via PATH
    if Command::new("spacetime")
        .arg("--version")
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map(|s| s.success())
        .unwrap_or(false)
    {
        return Ok(std::path::PathBuf::from("spacetime"));
    }
    // Fallback: known dev machine install path
    let fallback = std::path::PathBuf::from("/Users/mkhare/.local/bin/spacetime");
    if fallback.exists() {
        return Ok(fallback);
    }
    Err("spacetime binary not found in PATH or /Users/mkhare/.local/bin/spacetime".into())
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
            .stderr(Stdio::null())
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

fn publish_module(
    spacetime_bin: &std::path::Path,
    http_url: &str,
    _owner_token: &str,
    owner_cfg: &std::path::Path,
    name: &str,
    module_path: &str,
    sibling_wasm: &str,
) -> Result<(), String> {
    // Strategy:
    //   1. Try in-tree wasm build (RUSTC_FOR_WASM env var works around the
    //      Homebrew rustc-on-PATH issue on the dev machine).
    //   2. Fall back to pre-built sibling-checkout wasm if available.
    //   3. Fall back to --module-path (CI path; needs a working wasm toolchain).
    //
    // All three paths publish WITH the owner token (via --config-path) so that
    // the published database's owner identity matches the token we captured in
    // SpacetimeFixture::start(). This lets call_as_owner() call assert_owner-
    // gated reducers without a hardcoded OWNER_HEX in the module.
    let workspace_root = std::path::PathBuf::from(
        std::env::var("CARGO_MANIFEST_DIR").unwrap_or_else(|_| ".".into()),
    )
    .parent() // tests/
    .and_then(|p| p.parent()) // workspace root
    .map(|p| p.to_path_buf())
    .unwrap_or_else(|| std::path::PathBuf::from("."));

    // Cargo uses the workspace-level target dir even when building from a
    // member crate's subdirectory. Both candidate paths are checked.
    let wasm_file_name = format!("{}_module.wasm", name.replace('-', "_"));
    let in_tree_wasm_workspace = workspace_root
        .join("target/wasm32-unknown-unknown/release")
        .join(&wasm_file_name);
    let in_tree_wasm_local = workspace_root
        .join("modules")
        .join(name)
        .join("target/wasm32-unknown-unknown/release")
        .join(&wasm_file_name);

    let find_in_tree = || -> Option<String> {
        for p in [&in_tree_wasm_workspace, &in_tree_wasm_local] {
            if p.exists() {
                return Some(p.to_string_lossy().into_owned());
            }
        }
        None
    };

    let bin_path: Option<String> = if let Some(p) = find_in_tree() {
        // Already built (e.g. by a previous run).
        Some(p)
    } else {
        // Try to build in-tree.  We use RUSTC_FOR_WASM if set; otherwise try
        // the rustup-managed rustc directly to bypass any Homebrew override.
        let rustc_for_wasm = std::env::var("RUSTC_FOR_WASM").ok().or_else(|| {
            let home = std::env::var("HOME").ok()?;
            let p = std::path::PathBuf::from(home)
                .join(".rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc");
            if p.exists() {
                Some(p.to_string_lossy().into_owned())
            } else {
                None
            }
        });
        let module_src = workspace_root.join(module_path);
        let mut cmd = Command::new("cargo");
        cmd.args(["build", "--target", "wasm32-unknown-unknown", "--release"])
            .current_dir(&module_src);
        if let Some(rc) = rustc_for_wasm {
            cmd.env("RUSTC", rc);
        }
        let ok = cmd
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status()
            .map(|s| s.success())
            .unwrap_or(false);
        if ok {
            find_in_tree()
        } else {
            None
        }
    };

    // Prefer the in-tree wasm; fall back to sibling checkout.
    let wasm_path = bin_path
        .filter(|p| std::path::Path::new(p).exists())
        .or_else(|| {
            if std::path::Path::new(sibling_wasm).exists() {
                Some(sibling_wasm.to_string())
            } else {
                None
            }
        });

    // No --delete-data needed: the fixture always starts a fresh in-memory instance.
    let status = if let Some(wasm) = wasm_path {
        Command::new(spacetime_bin)
            .args([
                "--config-path",
                owner_cfg.to_str().unwrap(),
                "publish",
                "--server",
                http_url,
                "--bin-path",
                &wasm,
                "--yes",
                name,
            ])
            .status()
            .map_err(|e| format!("spawn spacetime publish (wasm): {e}"))?
    } else {
        Command::new(spacetime_bin)
            .args([
                "--config-path",
                owner_cfg.to_str().unwrap(),
                "publish",
                "--server",
                http_url,
                "--module-path",
                module_path,
                "--yes",
                name,
            ])
            .status()
            .map_err(|e| format!("spawn spacetime publish (module-path): {e}"))?
    };
    if !status.success() {
        return Err(format!("spacetime publish {name} failed: {status}"));
    }
    Ok(())
}

/// Launches `target/debug/sastaspace` against the given fixture and returns
/// the PTY session for sending keys and asserting on output.
pub struct LaunchedTui {
    pub session: expectrl::session::Session,
}

impl LaunchedTui {
    pub fn launch(_fixture: &SpacetimeFixture) -> Result<Self, String> {
        // Resolve the binary path. `cargo test` CWD is the workspace root, so
        // `target/debug/sastaspace` is correct as a relative path. We also
        // check the CARGO_MANIFEST_DIR-relative absolute path as a fallback.
        let bin = resolve_tui_bin()?;
        let mut session =
            expectrl::spawn(bin.to_str().unwrap()).map_err(|e| format!("spawn tui: {e}"))?;
        session.set_expect_timeout(Some(Duration::from_secs(10)));
        Ok(Self { session })
    }
}

fn resolve_tui_bin() -> Result<PathBuf, String> {
    // When invoked via `cargo test -p e2e`, the working directory is the
    // workspace root and `CARGO_MANIFEST_DIR` points to the e2e crate.
    // Walk up from CARGO_MANIFEST_DIR to find the workspace root.
    let candidates: Vec<PathBuf> = {
        let mut v = vec![PathBuf::from("target/debug/sastaspace")];
        if let Ok(manifest) = std::env::var("CARGO_MANIFEST_DIR") {
            // e2e crate is at <workspace>/tests/e2e-rust; workspace root is two levels up.
            let workspace_root = PathBuf::from(&manifest)
                .parent() // tests/
                .and_then(|p| p.parent()) // workspace root
                .map(|p| p.to_path_buf());
            if let Some(root) = workspace_root {
                v.push(root.join("target/debug/sastaspace"));
            }
        }
        v
    };
    for path in candidates {
        if path.exists() {
            return Ok(path);
        }
    }
    Err("target/debug/sastaspace not found — run `cargo build -p shell` first".into())
}
