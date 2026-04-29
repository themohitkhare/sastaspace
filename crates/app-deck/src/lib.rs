//! Deck app — text input → audio.
//!
//! Two screens:
//! - **Plan**: describe project, set track count, submit `request_plan`,
//!   watch `plan_request` row stream in, approve to advance.
//! - **Generate**: calls `request_generate`, watches `generate_job`,
//!   downloads zip when done, unpacks to `~/Music/sastaspace/<job_id>/`,
//!   offers `p` to play via rodio (if compiled with the `audio` feature).

pub mod audio;
pub mod download;
pub mod state;
pub mod view;

pub use state::{DeckState, GenerateStatus, PlanStatus, PlannedTrack, Screen};

use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};
use ratatui::{layout::Rect, Frame};
use sastaspace_core::{
    event::{Action, InputAction},
    theme::Theme,
    App, AppResult, ReducerCall,
};
use std::path::PathBuf;
use tokio::sync::mpsc::UnboundedSender;
use tracing::warn;

/// Newtype handle so the shell can call deck-specific methods when the
/// `Updated("plan_request")` / `Updated("generate_job")` events arrive.
pub struct DeckApp {
    state: DeckState,
    theme: Theme,
    /// Channel back to the main loop so async download tasks can post events.
    /// Provided by the shell via `DeckApp::set_action_sender`.
    tx: Option<UnboundedSender<Action>>,
}

impl DeckApp {
    pub fn new() -> Self {
        Self {
            state: DeckState::default(),
            theme: Theme::default_dark(),
            tx: None,
        }
    }

    /// Wire in the action sender so download tasks can report back.
    pub fn set_action_sender(&mut self, tx: UnboundedSender<Action>) {
        self.tx = Some(tx);
    }

    /// Called by the shell when a `plan_request` row update arrives.
    pub fn on_plan_request_update(
        &mut self,
        id: u64,
        status: &str,
        tracks_json: Option<&str>,
        error: Option<&str>,
    ) {
        self.state.plan_request_id = Some(id);
        match status {
            "done" => {
                if let Some(tj) = tracks_json {
                    self.state.apply_plan_done(tj);
                }
            }
            "failed" => {
                self.state
                    .apply_plan_failed(error.unwrap_or("unknown error"));
            }
            "pending" => {
                self.state.plan_status = PlanStatus::Pending;
            }
            _ => {}
        }
    }

    /// Called by the shell when a `generate_job` row update arrives.
    pub fn on_generate_job_update(
        &mut self,
        id: u64,
        status: &str,
        zip_url: Option<&str>,
        error: Option<&str>,
    ) {
        self.state.generate_job_id = Some(id);
        match status {
            "done" => {
                if let Some(url) = zip_url {
                    self.state.apply_generate_done(url.to_owned());
                    // Kick off the async download task.
                    self.spawn_download(url.to_owned(), id);
                }
            }
            "failed" => {
                self.state
                    .apply_generate_failed(error.unwrap_or("unknown error"));
            }
            "pending" => {
                self.state.generate_status = GenerateStatus::Pending;
            }
            _ => {}
        }
    }

    fn spawn_download(&mut self, url: String, job_id: u64) {
        let tx = match self.tx.clone() {
            Some(t) => t,
            None => {
                warn!("no action sender — skipping download");
                return;
            }
        };
        self.state.generate_status = GenerateStatus::Downloading;
        tokio::spawn(async move {
            match download::download_and_unpack(&url, job_id).await {
                Ok(path) => {
                    let _ = tx.send(Action::Stdb(sastaspace_core::event::StdbEvent::Updated(
                        "deck_download_done",
                    )));
                    // We can't carry the path through the static-str StdbEvent easily,
                    // so we store it as a side effect below.  Instead, use a Toast.
                    let _ = tx.send(Action::Toast(sastaspace_core::event::Toast::info(format!(
                        "deck:downloaded:{path}"
                    ))));
                }
                Err(e) => {
                    let _ = tx.send(Action::Toast(sastaspace_core::event::Toast::error(
                        format!("deck:download_failed:{e}"),
                    )));
                }
            }
        });
    }

    /// Expose state for tests.
    pub fn state(&self) -> &DeckState {
        &self.state
    }

    /// Force-set state (for tests / shell hydration).
    pub fn state_mut(&mut self) -> &mut DeckState {
        &mut self.state
    }

    /// Accessor for the planned tracks — used by the shell to build
    /// the `tracks_json` arg for `request_generate`.
    pub fn planned_tracks(&self) -> &[PlannedTrack] {
        &self.state.planned_tracks
    }
}

impl Default for DeckApp {
    fn default() -> Self {
        Self::new()
    }
}

impl App for DeckApp {
    fn id(&self) -> &'static str {
        "deck"
    }

    fn title(&self) -> &str {
        match self.state.screen {
            Screen::Plan => "deck · plan",
            Screen::Generate => "deck · generate",
        }
    }

    fn render(&mut self, frame: &mut Frame, area: Rect) {
        view::render(frame, area, &self.state, &self.theme);
    }

    fn handle(&mut self, action: Action) -> AppResult {
        match action {
            Action::Input(InputAction::Key(k)) => self.handle_key(k),
            Action::Toast(t) => {
                // Intercept deck-internal toast payloads that carry download results.
                if t.message.starts_with("deck:downloaded:") {
                    let path = t.message.trim_start_matches("deck:downloaded:");
                    self.state.generate_status = GenerateStatus::Downloaded {
                        path: path.to_owned(),
                    };
                    self.state.status_msg = Some(format!("Saved to {path}"));
                } else if t.message.starts_with("deck:download_failed:") {
                    let err = t.message.trim_start_matches("deck:download_failed:");
                    self.state.generate_status = GenerateStatus::Failed(err.to_owned());
                    self.state.status_msg = Some(format!("Download failed: {err}"));
                }
                AppResult::Continue
            }
            _ => AppResult::Continue,
        }
    }

    fn as_any_mut(&mut self) -> &mut dyn std::any::Any {
        self
    }
}

impl DeckApp {
    fn handle_key(&mut self, k: KeyEvent) -> AppResult {
        // Editing mode eats most keys.
        if self.state.editing {
            match k.code {
                KeyCode::Esc => {
                    self.state.editing = false;
                }
                KeyCode::Backspace => {
                    self.state.backspace();
                }
                KeyCode::Char(c) => {
                    self.state.insert_char(c);
                }
                _ => {}
            }
            return AppResult::Continue;
        }

        match self.state.screen {
            Screen::Plan => self.handle_plan_key(k),
            Screen::Generate => self.handle_generate_key(k),
        }
    }

    fn handle_plan_key(&mut self, k: KeyEvent) -> AppResult {
        match k.code {
            KeyCode::Char('q') if k.modifiers == KeyModifiers::NONE => return AppResult::Quit,
            KeyCode::Char('i') if k.modifiers == KeyModifiers::NONE => {
                self.state.editing = true;
            }
            KeyCode::Left => self.state.decrement_track_count(),
            KeyCode::Right => self.state.increment_track_count(),
            KeyCode::Char('h') => self.state.decrement_track_count(),
            KeyCode::Char('l') => self.state.increment_track_count(),
            // Enter submits plan (caller responsible for actually calling reducer).
            // We signal via AppResult::CallReducer — the shell dispatches.
            KeyCode::Enter => {
                if self.state.plan_status == PlanStatus::Done {
                    // Plan already done — treat Enter as approve.
                    self.state.approve();
                } else if !self.state.description.is_empty() {
                    self.state.plan_status = PlanStatus::Pending;
                    self.state.status_msg = Some("Submitting plan request…".into());
                    return AppResult::CallReducer(ReducerCall::DeckRequestPlan);
                }
            }
            KeyCode::Char('g')
                if k.modifiers == KeyModifiers::NONE
                    && self.state.plan_status == PlanStatus::Done =>
            {
                self.state.approve();
            }
            _ => {}
        }
        AppResult::Continue
    }

    fn handle_generate_key(&mut self, k: KeyEvent) -> AppResult {
        match k.code {
            KeyCode::Char('q') if k.modifiers == KeyModifiers::NONE => return AppResult::Quit,
            KeyCode::Char('b') if k.modifiers == KeyModifiers::NONE => {
                self.state.screen = Screen::Plan;
            }
            KeyCode::Enter if self.state.generate_status == GenerateStatus::Idle => {
                self.state.generate_status = GenerateStatus::Pending;
                self.state.status_msg = Some("Submitting generate job…".into());
                return AppResult::CallReducer(ReducerCall::DeckRequestGenerate);
            }
            KeyCode::Char('p') if k.modifiers == KeyModifiers::NONE => {
                self.maybe_play();
            }
            _ => {}
        }
        AppResult::Continue
    }

    fn maybe_play(&mut self) {
        let path = match &self.state.generate_status {
            GenerateStatus::Downloaded { path } => PathBuf::from(path),
            _ => {
                self.state.status_msg =
                    Some("No audio downloaded yet — wait for status 'saved'".into());
                return;
            }
        };
        // Find first WAV in the directory.
        let wav = std::fs::read_dir(&path).ok().and_then(|mut d| {
            d.find_map(|e| {
                let e = e.ok()?;
                let p = e.path();
                if p.extension().and_then(|s| s.to_str()) == Some("wav") {
                    Some(p)
                } else {
                    None
                }
            })
        });
        match wav {
            Some(wav_path) => {
                self.state.status_msg = Some(format!("Playing {}…", wav_path.display()));
                if let Err(e) = audio::play_file(&wav_path) {
                    self.state.status_msg = Some(format!("Playback failed: {e}"));
                }
            }
            None => {
                self.state.status_msg = Some("No .wav files found in download directory".into());
            }
        }
    }
}
