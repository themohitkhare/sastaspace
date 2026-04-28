//! Magic-link login flow for the TUI.
//!
//! Calls the `request_magic_link` reducer with `app="tui"`, then waits for
//! the user to paste the token printed in their email and calls
//! `verify_token` to exchange it for the auth bearer token.
//!
//! The reducer calls themselves go through the STDB HTTP API (one-shot HTTP
//! POSTs, not the long-lived ws connection) to keep this crate independent
//! of the shell's live STDB connection state.

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
    // STDB reducer responses for non-unit returns wrap the value: {"value": <ret>}.
    // Unit returns yield empty body. We treat the bearer as either format.
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
