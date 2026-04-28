//! Shared types, theme, keymap and config for the sastaspace TUI workspace.

pub mod app;
pub mod config;
pub mod event;
pub mod keymap;
pub mod theme;

pub use app::{App, AppResult};
pub use event::{Action, InputAction};
