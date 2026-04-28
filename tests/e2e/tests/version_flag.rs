//! Non-TTY + flag tests — verify the binary works without a terminal.

use std::path::PathBuf;
use std::process::Command;

fn sastaspace_bin() -> PathBuf {
    // Mirror the preference order from resolve_tui_bin: release > debug.
    let candidates = [
        PathBuf::from("target/release/sastaspace"),
        PathBuf::from("target/debug/sastaspace"),
    ];
    for p in &candidates {
        if p.exists() {
            return p.clone();
        }
    }
    // Fallback: walk up from CARGO_MANIFEST_DIR.
    if let Ok(manifest) = std::env::var("CARGO_MANIFEST_DIR") {
        let root = PathBuf::from(&manifest)
            .parent()
            .and_then(|p| p.parent())
            .map(|p| p.to_path_buf());
        if let Some(r) = root {
            for suffix in ["target/release/sastaspace", "target/debug/sastaspace"] {
                let p = r.join(suffix);
                if p.exists() {
                    return p;
                }
            }
        }
    }
    panic!("sastaspace binary not found — run `cargo build -p shell [--release]` first");
}

#[test]
fn version_flag_prints_version() {
    let out = Command::new(sastaspace_bin())
        .arg("--version")
        .output()
        .expect("spawn sastaspace --version");

    assert!(
        out.status.success(),
        "--version should exit 0; got {:?}",
        out.status
    );
    let stdout = String::from_utf8_lossy(&out.stdout);
    assert!(
        stdout.contains("0.1.1"),
        "--version stdout should contain '0.1.1'; got: {stdout:?}"
    );
}

#[test]
fn short_version_flag_prints_version() {
    let out = Command::new(sastaspace_bin())
        .arg("-V")
        .output()
        .expect("spawn sastaspace -V");

    assert!(
        out.status.success(),
        "-V should exit 0; got {:?}",
        out.status
    );
    let stdout = String::from_utf8_lossy(&out.stdout);
    assert!(
        stdout.contains("0.1.1"),
        "-V stdout should contain '0.1.1'; got: {stdout:?}"
    );
}

#[test]
fn non_tty_exits_with_message() {
    // Pipe stdin so stdout is not a TTY.
    let out = Command::new(sastaspace_bin())
        .stdin(std::process::Stdio::piped())
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .spawn()
        .expect("spawn sastaspace non-interactively")
        .wait_with_output()
        .expect("wait");

    // Should exit non-zero (we use exit(1) in terminal::enter).
    assert!(
        !out.status.success(),
        "non-TTY invocation should fail; got {:?}",
        out.status
    );
    let stderr = String::from_utf8_lossy(&out.stderr);
    assert!(
        stderr.contains("requires a terminal"),
        "stderr should mention 'requires a terminal'; got: {stderr:?}"
    );
}
