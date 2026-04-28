//! E2E test fixtures for the sastaspace TUI.
//!
//! `SpacetimeFixture::start()` boots a local SpacetimeDB on port 3199,
//! publishes the `sastaspace` and `typewars` modules, and waits for them
//! to be reachable. Drop the fixture to tear everything down.
//!
//! `LaunchedTui::launch(...)` runs the binary under a PTY via `expectrl`.
//!
//! Wasm publish strategy: tries pre-built sibling-checkout wasm first
//! (kludge; the dev machine has a broken local wasm toolchain), falls
//! back to `spacetime publish --module-path` so CI can build fresh.

use std::{
    path::PathBuf,
    process::{Child, Command, Stdio},
    time::{Duration, Instant},
};

fn pick_free_port() -> u16 {
    let listener = std::net::TcpListener::bind("127.0.0.1:0").expect("bind ephemeral");
    let port = listener.local_addr().unwrap().port();
    drop(listener);
    port
}

/// Pre-built wasm in the sibling sastaspace checkout.
///
/// KLUDGE: The dev machine has a broken wasm toolchain (`cargo build
/// --target wasm32-unknown-unknown` fails due to an env-level rustup
/// issue unrelated to this repo). These absolute paths let
/// `cargo test -p e2e` succeed locally without rebuilding wasm.
///
/// On CI the sibling checkout does not exist, so `publish_module` falls
/// back to `spacetime publish --module-path` which rebuilds wasm from
/// source on a healthy rustup installation.
///
/// Once the local toolchain is repaired, remove this constant and the
/// `wasm.exists()` branch in `publish_module`.
const SIBLING_WASM_SASTASPACE: &str =
    "/Users/mkhare/Development/sastaspace/modules/sastaspace/target/wasm32-unknown-unknown/release/sastaspace_module.wasm";
const SIBLING_WASM_TYPEWARS: &str =
    "/Users/mkhare/Development/sastaspace/modules/typewars/target/wasm32-unknown-unknown/release/typewars_module.wasm";

pub struct SpacetimeFixture {
    proc: Child,
    pub http_url: String,
    pub ws_url: String,
    /// Holds the tempdir alive until the fixture is dropped, then auto-deletes it.
    _data_dir: tempfile::TempDir,
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
        publish_module(
            &spacetime_bin,
            &http_url,
            "sastaspace",
            "modules/sastaspace",
            SIBLING_WASM_SASTASPACE,
        )?;
        publish_module(
            &spacetime_bin,
            &http_url,
            "typewars",
            "modules/typewars",
            SIBLING_WASM_TYPEWARS,
        )?;
        Ok(Self {
            proc,
            http_url,
            ws_url,
            _data_dir: data_dir,
        })
    }
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
    name: &str,
    module_path: &str,
    sibling_wasm: &str,
) -> Result<(), String> {
    // Strategy: use pre-built wasm from sibling checkout if available (local dev
    // kludge — see SIBLING_WASM_* constants above). Otherwise fall back to
    // --module-path which triggers a fresh wasm build (the CI path).
    let wasm = std::path::Path::new(sibling_wasm);
    // No --delete-data needed: the fixture always starts a fresh in-memory instance.
    let status = if wasm.exists() {
        Command::new(spacetime_bin)
            .args([
                "publish",
                "--server",
                http_url,
                "--bin-path",
                sibling_wasm,
                "--anonymous",
                "--yes",
                name,
            ])
            .status()
            .map_err(|e| format!("spawn spacetime publish (sibling-wasm): {e}"))?
    } else {
        Command::new(spacetime_bin)
            .args([
                "publish",
                "--server",
                http_url,
                "--module-path",
                module_path,
                "--anonymous",
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
