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
