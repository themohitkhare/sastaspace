//! In-memory state for the notes app. Mirrors `project` and `comment` STDB tables.
//! The shell hydrates this via `Notes::set_projects` / `Notes::set_comments`.

/// A project row treated as a note.
#[derive(Debug, Clone, PartialEq)]
pub struct NoteRow {
    pub slug: String,
    pub title: String,
    pub body: String, // blurb field doubles as the note body for v1
    pub status: String,
    pub tags: Vec<String>,
    pub url: String,
}

/// A comment on a note.
#[derive(Debug, Clone, PartialEq)]
pub struct CommentRow {
    pub id: u64,
    pub post_slug: String,
    pub author_name: String,
    pub body: String,
    pub status: String,
}

/// Vim-style editing modes.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum EditMode {
    #[default]
    Normal,
    Insert,
}

/// Which pane is focused / what popover is open.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum Focus {
    #[default]
    List,
    Editor,
    Comments,
}

/// What the shell should do next (reducer call intent).
#[derive(Debug, Clone, PartialEq)]
pub enum PendingAction {
    /// Shell should call `upsert_project` with this payload.
    SaveNote {
        slug: String,
        title: String,
        body: String,
        status: String,
        tags: Vec<String>,
        url: String,
    },
    /// Shell should call `submit_user_comment` with this payload.
    PostComment { post_slug: String, body: String },
    /// Shell should open the login modal.
    NeedLogin,
}

#[derive(Debug, Default)]
pub struct NotesState {
    pub notes: Vec<NoteRow>,
    pub comments: Vec<CommentRow>,
    pub selected: usize,
    pub focus: Focus,
    pub edit_mode: EditMode,
    /// Buffer for the note body while in insert mode.
    pub editor_buf: String,
    /// Whether we have a bearer token (populated by shell on startup).
    pub authenticated: bool,
    /// Pending action for the shell to pick up and clear.
    pub pending: Option<PendingAction>,
    /// Comment compose buffer (when comments popover is open).
    pub comment_buf: String,
    /// Transient status message (e.g. "saved", "error saving").
    pub status_msg: Option<String>,
    // Vim command buffer (for `:w` detection)
    pub(crate) cmd_buf: String,
}

impl NotesState {
    pub fn set_notes(&mut self, mut rows: Vec<NoteRow>) {
        rows.sort_by(|a, b| a.title.cmp(&b.title));
        self.notes = rows;
        if self.selected >= self.notes.len() {
            self.selected = self.notes.len().saturating_sub(1);
        }
    }

    pub fn set_comments(&mut self, rows: Vec<CommentRow>) {
        self.comments = rows;
    }

    pub fn move_selection(&mut self, delta: isize) {
        if self.notes.is_empty() {
            return;
        }
        let n = self.notes.len() as isize;
        let cur = self.selected as isize;
        let next = ((cur + delta).rem_euclid(n)) as usize;
        self.selected = next;

        // Reset editor buffer to show selected note's body.
        if let Some(note) = self.notes.get(self.selected) {
            self.editor_buf = note.body.clone();
        }
    }

    pub fn current_note(&self) -> Option<&NoteRow> {
        self.notes.get(self.selected)
    }

    /// Comments for the currently selected note.
    pub fn current_comments(&self) -> Vec<&CommentRow> {
        match self.current_note() {
            Some(n) => self
                .comments
                .iter()
                .filter(|c| c.post_slug == n.slug)
                .collect(),
            None => vec![],
        }
    }

    /// Enter insert mode (if editor is focused).
    pub fn enter_insert(&mut self) {
        if self.focus == Focus::Editor && !self.authenticated {
            self.pending = Some(PendingAction::NeedLogin);
            return;
        }
        if self.focus == Focus::Editor {
            self.edit_mode = EditMode::Insert;
        }
    }

    /// Exit insert mode back to normal.
    pub fn exit_insert(&mut self) {
        self.edit_mode = EditMode::Normal;
        self.cmd_buf.clear();
    }

    /// Handle a character typed in insert mode / comment compose.
    pub fn type_char(&mut self, c: char) {
        match self.focus {
            Focus::Editor if self.edit_mode == EditMode::Insert => {
                self.editor_buf.push(c);
            }
            Focus::Comments => {
                self.comment_buf.push(c);
            }
            _ => {
                // Normal mode: accumulate into cmd_buf for vim commands like `:w`
                if self.focus == Focus::Editor {
                    self.cmd_buf.push(c);
                }
            }
        }
    }

    pub fn backspace(&mut self) {
        match self.focus {
            Focus::Editor if self.edit_mode == EditMode::Insert => {
                self.editor_buf.pop();
            }
            Focus::Comments => {
                self.comment_buf.pop();
            }
            _ => {}
        }
    }

    /// Process Enter key depending on context.
    pub fn enter(&mut self) {
        match self.focus {
            Focus::Editor if self.edit_mode == EditMode::Insert => {
                self.editor_buf.push('\n');
            }
            Focus::Comments => {
                // Submit comment.
                if let Some(note) = self.current_note() {
                    let body = self.comment_buf.trim().to_string();
                    if !body.is_empty() {
                        self.pending = Some(PendingAction::PostComment {
                            post_slug: note.slug.clone(),
                            body,
                        });
                        self.comment_buf.clear();
                    }
                }
            }
            _ => {}
        }
    }

    /// Try to execute `:w` save command.
    pub fn try_save(&mut self) {
        if let Some(note) = self.current_note() {
            self.pending = Some(PendingAction::SaveNote {
                slug: note.slug.clone(),
                title: note.title.clone(),
                body: self.editor_buf.clone(),
                status: note.status.clone(),
                tags: note.tags.clone(),
                url: note.url.clone(),
            });
            self.status_msg = Some("saving…".to_string());
        }
        self.cmd_buf.clear();
        self.exit_insert();
    }

    /// Check if cmd_buf contains a vim `:w` command and execute it.
    pub fn check_cmd(&mut self) {
        if self.cmd_buf == ":w" || self.cmd_buf.starts_with(":w ") {
            self.try_save();
        }
    }
}
