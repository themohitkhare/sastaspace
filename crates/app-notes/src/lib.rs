//! Notes app — two-pane (list + editor) with vim-style modal editing and comments popover.
//! Reads `project` rows from STDB (all rows treated as notes for v1).
//! Comments read from `comment` table.

mod state;
mod view;

pub use state::{CommentRow, NoteRow, NotesState, PendingAction};

use crossterm::event::{KeyCode, KeyEvent};
use ratatui::{layout::Rect, Frame};
use sastaspace_core::{
    event::{Action, InputAction},
    theme::Theme,
    App, AppResult,
};
use state::{EditMode, Focus};

pub struct Notes {
    state: NotesState,
    theme: Theme,
}

impl Notes {
    pub fn new() -> Self {
        Self {
            state: NotesState::default(),
            theme: Theme::default_dark(),
        }
    }

    /// Hydrate notes from STDB project rows. Called by shell on `Updated("project")`.
    pub fn set_notes(&mut self, rows: Vec<NoteRow>) {
        let prev_slug = self.state.current_note().map(|n| n.slug.clone());
        self.state.set_notes(rows);
        // Restore editor buffer for newly selected note.
        if let Some(note) = self.state.current_note() {
            if self.state.edit_mode == EditMode::Normal {
                self.state.editor_buf = note.body.clone();
            }
        }
        // If we had a selected slug, try to keep it.
        if let Some(slug) = prev_slug {
            if let Some(idx) = self.state.notes.iter().position(|n| n.slug == slug) {
                self.state.selected = idx;
                if let Some(note) = self.state.notes.get(idx) {
                    if self.state.edit_mode == EditMode::Normal {
                        self.state.editor_buf = note.body.clone();
                    }
                }
            }
        }
    }

    /// Hydrate comments from STDB comment rows. Called by shell on `Updated("comment")`.
    pub fn set_comments(&mut self, rows: Vec<CommentRow>) {
        self.state.set_comments(rows);
    }

    /// Set whether we have a valid auth token. Called by shell after keychain check.
    pub fn set_authenticated(&mut self, auth: bool) {
        self.state.authenticated = auth;
    }

    /// Take any pending action (reducer call or login prompt). Clears it.
    pub fn take_pending(&mut self) -> Option<PendingAction> {
        self.state.pending.take()
    }

    /// Shell calls this to acknowledge a save completed successfully.
    pub fn on_save_ok(&mut self) {
        self.state.status_msg = Some("saved".to_string());
    }

    /// Shell calls this to report a save error.
    pub fn on_save_err(&mut self, msg: String) {
        self.state.status_msg = Some(format!("error: {msg}"));
    }
}

impl Default for Notes {
    fn default() -> Self {
        Self::new()
    }
}

impl App for Notes {
    fn id(&self) -> &'static str {
        "notes"
    }

    fn title(&self) -> &str {
        "sastaspace · notes"
    }

    fn render(&mut self, frame: &mut Frame, area: Rect) {
        view::render(frame, area, &self.state, &self.theme);
    }

    fn handle(&mut self, action: Action) -> AppResult {
        if let Action::Input(InputAction::Key(KeyEvent { code, .. })) = action {
            self.handle_key(code);
        }
        AppResult::Continue
    }

    fn as_any_mut(&mut self) -> &mut dyn std::any::Any {
        self
    }
}

impl Notes {
    fn handle_key(&mut self, code: KeyCode) {
        match self.state.focus {
            Focus::List => self.handle_list_key(code),
            Focus::Editor => self.handle_editor_key(code),
            Focus::Comments => self.handle_comments_key(code),
        }
    }

    fn handle_list_key(&mut self, code: KeyCode) {
        match code {
            KeyCode::Char('j') | KeyCode::Down => self.state.move_selection(1),
            KeyCode::Char('k') | KeyCode::Up => self.state.move_selection(-1),
            KeyCode::Tab | KeyCode::Enter | KeyCode::Char('l') => {
                self.state.focus = Focus::Editor;
                // Load current note's body into editor buffer.
                if let Some(note) = self.state.current_note() {
                    self.state.editor_buf = note.body.clone();
                }
            }
            KeyCode::Char('c') if self.state.current_note().is_some() => {
                self.state.focus = Focus::Comments;
            }
            _ => {}
        }
    }

    fn handle_editor_key(&mut self, code: KeyCode) {
        match self.state.edit_mode {
            EditMode::Normal => match code {
                KeyCode::Tab | KeyCode::Char('h') => {
                    self.state.focus = Focus::List;
                    self.state.cmd_buf.clear();
                }
                KeyCode::Char('c') if self.state.current_note().is_some() => {
                    self.state.focus = Focus::Comments;
                    self.state.cmd_buf.clear();
                }
                KeyCode::Char('i') => {
                    self.state.enter_insert();
                }
                KeyCode::Char(':') => {
                    self.state.cmd_buf = ":".to_string();
                }
                KeyCode::Char('w') if self.state.cmd_buf == ":" => {
                    self.state.cmd_buf.push('w');
                    self.state.check_cmd();
                }
                KeyCode::Char(c) if self.state.cmd_buf.starts_with(':') => {
                    self.state.cmd_buf.push(c);
                    self.state.check_cmd();
                }
                KeyCode::Esc => {
                    self.state.cmd_buf.clear();
                }
                _ => {}
            },
            EditMode::Insert => match code {
                KeyCode::Esc => self.state.exit_insert(),
                KeyCode::Char(c) => self.state.type_char(c),
                KeyCode::Backspace => self.state.backspace(),
                KeyCode::Enter => self.state.enter(),
                _ => {}
            },
        }
    }

    fn handle_comments_key(&mut self, code: KeyCode) {
        match code {
            KeyCode::Esc => {
                self.state.focus = Focus::Editor;
                self.state.comment_buf.clear();
            }
            KeyCode::Char(c) => self.state.type_char(c),
            KeyCode::Backspace => self.state.backspace(),
            KeyCode::Enter => self.state.enter(),
            _ => {}
        }
    }
}
