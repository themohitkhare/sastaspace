//! In-memory state for the admin dashboard.
//! Hydrated by the shell from STDB subscription callbacks.

use std::time::{Duration, Instant};

// ── System metrics ────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Default)]
pub struct SystemMetrics {
    pub cpu_pct: f32,
    pub cores: u32,
    pub mem_used_gb: f32,
    pub mem_total_gb: f32,
    pub mem_pct: f32,
    pub swap_used_mb: u32,
    pub swap_total_mb: u32,
    pub disk_used_gb: u32,
    pub disk_total_gb: u32,
    pub disk_pct: f32,
    pub net_tx_bytes: u64,
    pub net_rx_bytes: u64,
    pub uptime_s: u64,
    pub gpu_pct: Option<u32>,
    pub gpu_model: Option<String>,
    pub updated_at_ms: u64,
}

// ── Container status ──────────────────────────────────────────────────────────

#[derive(Debug, Clone)]
pub struct ContainerRow {
    pub name: String,
    pub status: String,
    pub image: String,
    pub uptime_s: u64,
    pub mem_used_mb: u32,
    pub mem_limit_mb: u32,
    pub restart_count: u32,
}

// ── Moderation queue ──────────────────────────────────────────────────────────

#[derive(Debug, Clone)]
pub struct FlaggedComment {
    pub id: u64,
    pub post_slug: String,
    pub author_name: String,
    pub body: String,
}

// ── Log event ─────────────────────────────────────────────────────────────────

#[derive(Debug, Clone)]
pub struct LogLine {
    pub container: String,
    pub level: String,
    pub text: String,
    pub ts_micros: i64,
}

// ── Device-flow auth panel ────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq, Default)]
pub enum DeviceFlowPhase {
    /// Not yet started.
    #[default]
    Idle,
    /// Requesting a code from Google.
    Requesting,
    /// Waiting for the user to authorise on their device.
    Pending {
        user_code: String,
        verification_url: String,
        expires_in: u64,
        /// Monotonic instant when the code was issued (for countdown timer).
        issued_at: Instant,
    },
    /// Device flow succeeded — JWT stored in keychain.
    Done,
    /// Device flow failed.
    Failed(String),
}

// ── Log popover ───────────────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub enum LogPopoverState {
    #[default]
    Closed,
    /// Open, subscribed to `container`.
    Open { container: String },
}

// ── Top-level admin state ─────────────────────────────────────────────────────

/// Which pane currently has keyboard focus.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum Focus {
    #[default]
    Metrics,
    Containers,
    Moderation,
}

#[derive(Debug, Default)]
pub struct AdminState {
    /// Gate: `None` = not authenticated, `Some(jwt)` = authenticated.
    pub owner_jwt: Option<String>,
    /// Device-flow panel when not yet authenticated.
    pub device_flow: DeviceFlowPhase,

    // ── Data panels ───────────────────────────────────────────────────────────
    pub metrics: SystemMetrics,
    pub containers: Vec<ContainerRow>,
    pub flagged: Vec<FlaggedComment>,
    pub flagged_selected: usize,

    // ── Log popover ───────────────────────────────────────────────────────────
    pub log_popover: LogPopoverState,
    pub log_lines: Vec<LogLine>,

    // ── Focus ─────────────────────────────────────────────────────────────────
    pub focus: Focus,
}

impl AdminState {
    // ── Device-flow helpers ───────────────────────────────────────────────────

    pub fn is_authenticated(&self) -> bool {
        self.owner_jwt.is_some()
    }

    pub fn time_remaining(&self) -> Option<Duration> {
        if let DeviceFlowPhase::Pending {
            expires_in,
            issued_at,
            ..
        } = &self.device_flow
        {
            let elapsed = issued_at.elapsed().as_secs();
            Some(Duration::from_secs(expires_in.saturating_sub(elapsed)))
        } else {
            None
        }
    }

    // ── Moderation navigation ─────────────────────────────────────────────────

    pub fn move_flagged_selection(&mut self, delta: isize) {
        if self.flagged.is_empty() {
            return;
        }
        let n = self.flagged.len() as isize;
        let cur = self.flagged_selected as isize;
        self.flagged_selected = ((cur + delta).rem_euclid(n)) as usize;
    }

    pub fn selected_flagged(&self) -> Option<&FlaggedComment> {
        self.flagged.get(self.flagged_selected)
    }

    // ── Log lines management ──────────────────────────────────────────────────

    /// Keep only the most recent N lines so the popover doesn't grow unbounded.
    const MAX_LOG_LINES: usize = 500;

    pub fn push_log_line(&mut self, line: LogLine) {
        self.log_lines.push(line);
        if self.log_lines.len() > Self::MAX_LOG_LINES {
            self.log_lines.remove(0);
        }
    }
}
