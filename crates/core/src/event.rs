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
    ReducerError {
        reducer: &'static str,
        message: String,
    },
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
        Self {
            level: ToastLevel::Info,
            message: msg.into(),
        }
    }
    pub fn warn(msg: impl Into<String>) -> Self {
        Self {
            level: ToastLevel::Warn,
            message: msg.into(),
        }
    }
    pub fn error(msg: impl Into<String>) -> Self {
        Self {
            level: ToastLevel::Error,
            message: msg.into(),
        }
    }
}
