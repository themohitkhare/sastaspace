//! Connection lifecycle: connect → subscribe → forward events.
//!
//! SDK shape (verified against spacetimedb-sdk 2.1 + generated bindings):
//!   - `DbConnection::builder()` → `DbConnectionBuilder`
//!   - builder methods: `.with_uri()`, `.with_database_name()`, `.with_token(Option<String>)`
//!   - callbacks: `.on_connect(|ctx, identity, token| ...)`,
//!                `.on_connect_error(|ctx, err| ...)`,
//!                `.on_disconnect(|ctx, Option<Error>| ...)`
//!   - `.build().expect(...)` → `DbConnection`
//!   - `conn.run_threaded()` spawns a background OS thread (sync, no async needed).
//!   - Subscriptions: `ctx.subscription_builder().on_applied(|sub_ctx| ...).subscribe(vec![...])`

use crate::bindings::DbConnection;
use sastaspace_core::event::{Action, StdbEvent};
use spacetimedb_sdk::DbContext;
use std::path::PathBuf;
use thiserror::Error;
use tokio::sync::mpsc::UnboundedSender;
use tracing::{error, info, warn};

#[derive(Debug, Clone)]
pub struct StdbConfig {
    pub uri: String,
    pub module: String,
    /// Optional bearer token from a previous magic-link login.
    pub token: Option<String>,
    /// Where to cache the granted identity between runs.
    /// Stored for caller reference; the Rust SDK uses the token directly,
    /// not a credentials file path.
    pub credentials_path: PathBuf,
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
    /// The underlying SDK connection — callers may add more subscriptions via
    /// `conn.subscription_builder()` or call reducers via `conn.reducers`.
    pub conn: DbConnection,
}

impl StdbHandle {
    /// Connects, attaches event callbacks that forward into `tx`, subscribes to
    /// the `project` and `presence` tables, and spawns the SDK run loop on a
    /// background OS thread (via `conn.run_threaded()`).
    ///
    /// This function is synchronous internally — the SDK `build()` call blocks
    /// until the WebSocket handshake completes. We wrap it in
    /// `spawn_blocking` so that callers in async contexts don't block the
    /// tokio executor.
    pub async fn connect(
        cfg: StdbConfig,
        tx: UnboundedSender<Action>,
    ) -> Result<Self, StdbError> {
        let tx_connect = tx.clone();
        let tx_error = tx.clone();
        let tx_disconnect = tx.clone();
        let tx_sub_project = tx.clone();
        let tx_sub_presence = tx.clone();

        let uri = cfg.uri.clone();
        let module = cfg.module.clone();
        let token = cfg.token.clone();

        let conn = tokio::task::spawn_blocking(move || {
            DbConnection::builder()
                .with_uri(uri.as_str())
                .with_database_name(module.as_str())
                .with_token(token)
                .on_connect(move |ctx, _identity, _token| {
                    info!("stdb: connected");
                    let _ = tx_connect.send(Action::Stdb(StdbEvent::Connected));

                    let tx_proj = tx_sub_project.clone();
                    ctx.subscription_builder()
                        .on_applied(move |_sub_ctx| {
                            let _ = tx_proj.send(Action::Stdb(StdbEvent::Updated("project")));
                        })
                        .subscribe(vec!["SELECT * FROM project".to_string()]);

                    let tx_pres = tx_sub_presence.clone();
                    ctx.subscription_builder()
                        .on_applied(move |_sub_ctx| {
                            let _ = tx_pres.send(Action::Stdb(StdbEvent::Updated("presence")));
                        })
                        .subscribe(vec!["SELECT * FROM presence".to_string()]);
                })
                .on_connect_error(move |_ctx, err| {
                    error!("stdb: connect error: {err}");
                    let _ = tx_error.send(Action::Stdb(StdbEvent::Disconnected(err.to_string())));
                })
                .on_disconnect(move |_ctx, err| {
                    if let Some(e) = err {
                        warn!("stdb: disconnected with error: {e}");
                        let _ = tx_disconnect
                            .send(Action::Stdb(StdbEvent::Disconnected(e.to_string())));
                    } else {
                        info!("stdb: disconnected cleanly");
                        let _ = tx_disconnect
                            .send(Action::Stdb(StdbEvent::Disconnected("clean".to_string())));
                    }
                })
                .build()
                .map_err(|e| StdbError::Connect(e.to_string()))
        })
        .await
        .map_err(|e| StdbError::Connect(format!("spawn_blocking join error: {e}")))?
        ?;

        // Spawn the SDK's internal message-processing loop on a background thread.
        conn.run_threaded();

        Ok(StdbHandle {
            status: StdbStatus::Connected,
            conn,
        })
    }
}
