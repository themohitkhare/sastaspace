//! Download a zip from `zip_url`, unpack WAV files to
//! `~/Music/sastaspace/<job_id>/`, and return the directory path.
//!
//! This is the **real** download implementation — no stubs. If the HTTP
//! request or file I/O fails we return `Err` and the caller surfaces it as a
//! toast / status update. Per `feedback_no_fake_fallbacks`: fail loud.

use directories::UserDirs;
use std::path::PathBuf;
use thiserror::Error;
use tracing::{info, warn};

#[derive(Debug, Error)]
pub enum DownloadError {
    #[error("HTTP request failed: {0}")]
    Http(#[from] reqwest::Error),
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("Zip extraction error: {0}")]
    Zip(String),
    #[error("Could not determine home directory")]
    NoHomeDir,
}

/// Download `zip_url`, unpack to `~/Music/sastaspace/<job_id>/`, return the
/// destination directory path as a string.
pub async fn download_and_unpack(zip_url: &str, job_id: u64) -> Result<String, DownloadError> {
    // ── 1. Resolve destination directory ────────────────────────────────────
    let dest_dir = resolve_dest_dir(job_id)?;
    tokio::fs::create_dir_all(&dest_dir).await?;

    // ── 2. Download zip bytes ────────────────────────────────────────────────
    info!(url = %zip_url, dest = %dest_dir.display(), "downloading zip");
    let response = reqwest::get(zip_url).await?.error_for_status()?;
    let bytes = response.bytes().await?;
    info!(bytes = bytes.len(), "zip downloaded");

    // ── 3. Unpack in a blocking task (zip crate is sync) ─────────────────────
    let dest_dir_clone = dest_dir.clone();
    let bytes_vec = bytes.to_vec();
    tokio::task::spawn_blocking(move || unpack_zip(&bytes_vec, &dest_dir_clone))
        .await
        .map_err(|e| DownloadError::Zip(format!("spawn_blocking join: {e}")))?
        .map_err(DownloadError::Zip)?;

    let path_str = dest_dir.to_string_lossy().into_owned();
    info!(path = %path_str, "unpack complete");
    Ok(path_str)
}

fn resolve_dest_dir(job_id: u64) -> Result<PathBuf, DownloadError> {
    let music = UserDirs::new()
        .and_then(|u| u.audio_dir().map(|p| p.to_path_buf()))
        .unwrap_or_else(|| {
            // Fallback: ~/Music — common even if `directories` can't find audio dir.
            warn!("audio_dir not found; falling back to ~/Music");
            dirs_fallback()
        });
    Ok(music.join("sastaspace").join(job_id.to_string()))
}

fn dirs_fallback() -> PathBuf {
    // Last resort: use the executable's home dir detection.
    if let Some(home) = std::env::var_os("HOME") {
        PathBuf::from(home).join("Music")
    } else {
        PathBuf::from(".")
    }
}

fn unpack_zip(bytes: &[u8], dest: &std::path::Path) -> Result<(), String> {
    use std::io::Read;

    let cursor = std::io::Cursor::new(bytes);
    let mut archive = zip::ZipArchive::new(cursor).map_err(|e| format!("open archive: {e}"))?;

    for i in 0..archive.len() {
        let mut file = archive.by_index(i).map_err(|e| format!("entry {i}: {e}"))?;
        let name = file
            .enclosed_name()
            .ok_or_else(|| format!("unsafe path in zip entry {i}"))?;
        let out_path = dest.join(&name);

        if file.is_dir() {
            std::fs::create_dir_all(&out_path)
                .map_err(|e| format!("mkdir {}: {e}", out_path.display()))?;
        } else {
            if let Some(parent) = out_path.parent() {
                std::fs::create_dir_all(parent)
                    .map_err(|e| format!("mkdir parent {}: {e}", parent.display()))?;
            }
            let mut out = std::fs::File::create(&out_path)
                .map_err(|e| format!("create {}: {e}", out_path.display()))?;
            let mut buf = Vec::new();
            file.read_to_end(&mut buf)
                .map_err(|e| format!("read entry {i}: {e}"))?;
            std::io::Write::write_all(&mut out, &buf)
                .map_err(|e| format!("write {}: {e}", out_path.display()))?;
            info!(path = %out_path.display(), bytes = buf.len(), "extracted");
        }
    }
    Ok(())
}
