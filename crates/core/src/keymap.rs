//! Global key bindings. App-specific bindings live in each app crate.

use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};

/// Global actions that any screen can trigger.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GlobalKey {
    /// `q` or `ctrl-c` — quit the app cleanly.
    Quit,
    /// `?` — toggle help overlay.
    Help,
    /// `:` — open command palette.
    Palette,
    /// `esc` — dismiss modal / overlay.
    Dismiss,
}

pub fn classify(ev: KeyEvent) -> Option<GlobalKey> {
    match (ev.code, ev.modifiers) {
        (KeyCode::Char('q'), m) if m.is_empty() => Some(GlobalKey::Quit),
        (KeyCode::Char('c'), KeyModifiers::CONTROL) => Some(GlobalKey::Quit),
        (KeyCode::Char('?'), m) if m.is_empty() => Some(GlobalKey::Help),
        (KeyCode::Char(':'), m) if m.is_empty() => Some(GlobalKey::Palette),
        (KeyCode::Esc, _) => Some(GlobalKey::Dismiss),
        _ => None,
    }
}
