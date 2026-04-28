//! Admin dashboard — btop-style TUI app.
//!
//! # Layout
//!
//! ```text
//! ┌─ system metrics ──────────────────────────────────────────────────────────┐
//! │ CPU 24.5%  (8 cores)                                                      │
//! │ MEM 7.2/15.6 GB  (46.2%)                                                  │
//! │ …                                                                         │
//! ├─ containers ──────────────────────────────────────────────────────────────┤
//! │  stdb             Up 2d 3h   mem 124/512 MB  …                            │
//! │  moderator-agent  Up 1d 0h   mem  48/256 MB  …                            │
//! ├─ moderation queue ────────────────────────── [a]pprove [r]eject [d]elete ─┤
//! │  #12  Alice       [my-post]  This comment is spam…                        │
//! └───────────────────────────────────────────────────────────────────────────┘
//! ```
//!
//! Press `l` to open the log-stream popover for the focused container.
//!
//! # Owner gate
//!
//! On entry the app checks the OS keychain for a `TokenKind::OwnerJwt`. If
//! absent or a prior check failed, a centred device-flow panel is shown.
//! On success the JWT is stored and all reducer calls include it.
//!
//! # STDB integration
//!
//! The shell hydrates the app via `set_*` methods when STDB subscription
//! callbacks fire. The app never talks to STDB directly — it receives data
//! through the `Action` channel.

mod state;
#[cfg(test)]
mod tests;
mod view;

pub use state::{
    AdminState, ContainerRow, DeviceFlowPhase, FlaggedComment, Focus, LogLine, LogPopoverState,
    SystemMetrics,
};

use auth::{
    google_device::{self, DeviceFlowConfig},
    keychain::{TokenKind, TokenStore},
    InMemoryStore,
};
use crossterm::event::{KeyCode, KeyEvent};
use ratatui::{layout::Rect, Frame};
use sastaspace_core::{
    event::{Action, InputAction},
    theme::Theme,
    App, AppResult,
};
use std::sync::Arc;
use tracing::{error, info};

/// The admin TUI app.
pub struct Admin {
    /// Public for tests — allows direct state mutation without going through
    /// the full async shell. Not intended for production use.
    pub state: AdminState,
    theme: Theme,
    device_cfg: DeviceFlowConfig,
    store: Arc<dyn TokenStore>,
}

impl Admin {
    /// Construct with an OS keychain store.
    pub fn new(device_cfg: DeviceFlowConfig) -> Self {
        use auth::keychain::KeychainStore;
        Self::with_store(device_cfg, Arc::new(KeychainStore::new()))
    }

    /// Construct with a custom token store (used in tests).
    pub fn with_store(device_cfg: DeviceFlowConfig, store: Arc<dyn TokenStore>) -> Self {
        let mut s = Self {
            state: AdminState::default(),
            theme: Theme::default_dark(),
            device_cfg,
            store,
        };
        // Try to load a previously stored JWT.
        s.try_load_jwt_from_keychain();
        s
    }

    fn try_load_jwt_from_keychain(&mut self) {
        match self.store.get(TokenKind::OwnerJwt) {
            Ok(jwt) => {
                info!("admin: loaded owner JWT from keychain");
                self.state.owner_jwt = Some(jwt);
            }
            Err(_) => {
                // Not yet authenticated — device-flow panel will be shown.
            }
        }
    }

    // ── Data hydration (called by the shell on STDB callbacks) ────────────────

    pub fn set_metrics(&mut self, m: SystemMetrics) {
        self.state.metrics = m;
    }

    pub fn set_containers(&mut self, containers: Vec<ContainerRow>) {
        self.state.containers = containers;
        self.state.containers.sort_by(|a, b| a.name.cmp(&b.name));
    }

    pub fn set_flagged_comments(&mut self, comments: Vec<FlaggedComment>) {
        self.state.flagged = comments;
        if self.state.flagged_selected >= self.state.flagged.len() {
            self.state.flagged_selected = self.state.flagged.len().saturating_sub(1);
        }
    }

    pub fn push_log_line(&mut self, line: LogLine) {
        self.state.push_log_line(line);
    }

    // ── Device-flow helpers (called from async context in the shell) ──────────

    /// Begin the device-flow. Spawns a background task that posts to Google
    /// and drives polling; sends `Action::AdminDeviceFlowUpdate` events back.
    /// The shell should call this when the user presses Enter on the Idle panel.
    ///
    /// Returns the `DeviceCode` so the TUI can display the user_code immediately.
    pub async fn start_device_flow(
        &mut self,
    ) -> Result<auth::google_device::DeviceCode, auth::google_device::DeviceFlowError> {
        self.state.device_flow = DeviceFlowPhase::Requesting;
        let dc = google_device::start(&self.device_cfg).await?;
        self.state.device_flow = DeviceFlowPhase::Pending {
            user_code: dc.user_code.clone(),
            verification_url: dc.verification_url.clone(),
            expires_in: dc.expires_in,
            issued_at: std::time::Instant::now(),
        };
        Ok(dc)
    }

    /// Store the JWT after a successful device-flow poll.
    pub fn complete_device_flow(&mut self, jwt: String) {
        if let Err(e) = self.store.set(TokenKind::OwnerJwt, &jwt) {
            error!("admin: failed to store owner JWT in keychain: {e}");
        }
        self.state.owner_jwt = Some(jwt);
        self.state.device_flow = DeviceFlowPhase::Done;
    }

    /// Record a device-flow failure.
    pub fn fail_device_flow(&mut self, msg: String) {
        self.state.device_flow = DeviceFlowPhase::Failed(msg);
    }

    /// Reset the device-flow panel so the user can retry.
    pub fn reset_device_flow(&mut self) {
        self.state.device_flow = DeviceFlowPhase::Idle;
    }

    /// Current JWT (if authenticated). Passed as the extra arg to owner reducers.
    pub fn owner_jwt(&self) -> Option<&str> {
        self.state.owner_jwt.as_deref()
    }

    // ── Log popover helpers ───────────────────────────────────────────────────

    pub fn open_log_popover(&mut self, container: String) {
        self.state.log_lines.clear();
        self.state.log_popover = LogPopoverState::Open { container };
    }

    pub fn close_log_popover(&mut self) {
        self.state.log_popover = LogPopoverState::Closed;
    }

    pub fn log_popover_container(&self) -> Option<&str> {
        match &self.state.log_popover {
            LogPopoverState::Open { container } => Some(container.as_str()),
            _ => None,
        }
    }
}

impl Default for Admin {
    fn default() -> Self {
        Self::with_store(
            DeviceFlowConfig::for_client(""),
            Arc::new(InMemoryStore::new()),
        )
    }
}

impl App for Admin {
    fn id(&self) -> &'static str {
        "admin"
    }

    fn title(&self) -> &str {
        "sastaspace · admin"
    }

    fn render(&mut self, frame: &mut Frame, area: Rect) {
        view::render(frame, area, &self.state, &self.theme);
    }

    fn handle(&mut self, action: Action) -> AppResult {
        if let Action::Input(InputAction::Key(k)) = action {
            return self.handle_key(k);
        }
        AppResult::Continue
    }

    fn as_any_mut(&mut self) -> &mut dyn std::any::Any {
        self
    }
}

impl Admin {
    fn handle_key(&mut self, k: KeyEvent) -> AppResult {
        // If the log popover is open, only Esc can close it.
        if matches!(&self.state.log_popover, LogPopoverState::Open { .. }) {
            if k.code == KeyCode::Esc {
                self.close_log_popover();
            }
            return AppResult::Continue;
        }

        // If not authenticated, handle the device-flow panel.
        if !self.state.is_authenticated() {
            if k.code == KeyCode::Enter {
                // The shell will call `start_device_flow` asynchronously.
                // We just signal that we want to start.
                self.state.device_flow = DeviceFlowPhase::Requesting;
            }
            return AppResult::Continue;
        }

        // Authenticated — handle the main dashboard.
        match k.code {
            // Navigation between panes
            KeyCode::Tab => {
                self.state.focus = match self.state.focus {
                    state::Focus::Metrics => state::Focus::Containers,
                    state::Focus::Containers => state::Focus::Moderation,
                    state::Focus::Moderation => state::Focus::Metrics,
                };
            }
            // Moderation actions (only when moderation pane is focused)
            KeyCode::Char('j') | KeyCode::Down if self.state.focus == state::Focus::Moderation => {
                self.state.move_flagged_selection(1);
            }
            KeyCode::Char('k') | KeyCode::Up if self.state.focus == state::Focus::Moderation => {
                self.state.move_flagged_selection(-1);
            }
            // Log popover: open for selected container
            KeyCode::Char('l') => {
                let container = if self.state.focus == state::Focus::Containers
                    && !self.state.containers.is_empty()
                {
                    self.state
                        .containers
                        .first()
                        .map(|c| c.name.clone())
                        .unwrap_or_default()
                } else {
                    // Default: open logs for first container.
                    self.state
                        .containers
                        .first()
                        .map(|c| c.name.clone())
                        .unwrap_or_default()
                };
                if !container.is_empty() {
                    self.open_log_popover(container);
                }
            }
            // `q` to go back to portfolio (owner is already authenticated, no need to quit)
            KeyCode::Char('q') => return AppResult::SwitchTo("portfolio"),
            _ => {}
        }
        AppResult::Continue
    }
}
