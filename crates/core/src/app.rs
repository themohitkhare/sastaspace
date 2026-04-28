//! The `App` trait — every app screen implements this.

use crate::event::Action;
use ratatui::{layout::Rect, Frame};
use std::time::Duration;

/// Per-screen update + render contract.
pub trait App: Send + std::any::Any {
    /// Stable identifier (lowercase, no spaces). Used by the router.
    fn id(&self) -> &'static str;

    /// Title shown in the shell header.
    fn title(&self) -> &str;

    /// Render this app's contents into `area`. The shell handles header / footer.
    fn render(&mut self, frame: &mut Frame, area: Rect);

    /// Handle an action. Returns what the shell should do next.
    fn handle(&mut self, action: Action) -> AppResult;

    /// Called every render tick (~16ms) for animation / polling. Default no-op.
    fn tick(&mut self, _dt: Duration) -> AppResult {
        AppResult::Continue
    }

    /// Downcasting support — allows the shell to recover a concrete type from
    /// a `Box<dyn App>` without an unsafe transmute.
    fn as_any_mut(&mut self) -> &mut dyn std::any::Any;
}

/// What the app wants the shell to do after `handle` / `tick`.
#[derive(Debug)]
pub enum AppResult {
    /// Stay on this screen.
    Continue,
    /// Switch to the named app.
    SwitchTo(&'static str),
    /// Exit the binary cleanly.
    Quit,
}
