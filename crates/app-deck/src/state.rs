//! Deck app state — shared between the two screens.

use serde::{Deserialize, Serialize};

/// Which screen we are on.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Screen {
    Plan,
    Generate,
}

/// A single planned track as returned by the deck-agent AI planner.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PlannedTrack {
    pub name: String,
    #[serde(rename = "type")]
    pub kind: String,
    pub length: u32,
    pub desc: String,
    pub tempo: String,
    pub instruments: String,
    pub mood: String,
}

/// Status of the plan request (mirrors STDB `plan_request.status`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PlanStatus {
    Idle,
    Pending,
    Done,
    Failed(String),
}

/// Status of the generate job (mirrors STDB `generate_job.status`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GenerateStatus {
    Idle,
    Pending,
    Done { zip_url: String },
    Failed(String),
    Downloading,
    Downloaded { path: String },
}

#[derive(Debug)]
pub struct DeckState {
    pub screen: Screen,

    // ── Plan screen ──────────────────────────────────────────────────────────
    /// Raw text the user is typing.
    pub description: String,
    /// Cursor position within `description` (byte offset).
    pub description_cursor: usize,
    /// Track count slider value (1–10).
    pub track_count: u32,
    /// Whether we are in text-input mode (insert mode).
    pub editing: bool,

    pub plan_status: PlanStatus,
    /// STDB row id for the submitted plan_request.
    pub plan_request_id: Option<u64>,
    /// Parsed tracks from a done plan_request.
    pub planned_tracks: Vec<PlannedTrack>,

    // ── Generate screen ───────────────────────────────────────────────────────
    pub generate_status: GenerateStatus,
    pub generate_job_id: Option<u64>,

    // ── Toast / messages ──────────────────────────────────────────────────────
    pub status_msg: Option<String>,
}

impl Default for DeckState {
    fn default() -> Self {
        Self {
            screen: Screen::Plan,
            description: String::new(),
            description_cursor: 0,
            track_count: 3,
            editing: false,
            plan_status: PlanStatus::Idle,
            plan_request_id: None,
            planned_tracks: Vec::new(),
            generate_status: GenerateStatus::Idle,
            generate_job_id: None,
            status_msg: None,
        }
    }
}

impl DeckState {
    /// Insert a character at the current cursor position.
    pub fn insert_char(&mut self, c: char) {
        self.description.insert(self.description_cursor, c);
        self.description_cursor += c.len_utf8();
    }

    /// Delete the character before the cursor (backspace).
    pub fn backspace(&mut self) {
        if self.description_cursor == 0 {
            return;
        }
        let mut cur = self.description_cursor;
        // Step back one UTF-8 character.
        loop {
            cur -= 1;
            if self.description.is_char_boundary(cur) {
                break;
            }
        }
        self.description.remove(cur);
        self.description_cursor = cur;
    }

    /// Clamp + set track count.
    pub fn set_track_count(&mut self, n: u32) {
        self.track_count = n.clamp(1, 10);
    }

    pub fn increment_track_count(&mut self) {
        self.set_track_count(self.track_count + 1);
    }

    pub fn decrement_track_count(&mut self) {
        self.set_track_count(self.track_count.saturating_sub(1));
    }

    /// Called when STDB delivers a `plan_request` update with status=done.
    pub fn apply_plan_done(&mut self, tracks_json: &str) {
        match serde_json::from_str::<Vec<PlannedTrack>>(tracks_json) {
            Ok(tracks) => {
                self.planned_tracks = tracks;
                self.plan_status = PlanStatus::Done;
                self.status_msg = Some("Plan ready — press :approve or 'g' to generate".into());
            }
            Err(e) => {
                self.plan_status = PlanStatus::Failed(format!("bad tracks_json: {e}"));
            }
        }
    }

    /// Called when STDB delivers a `plan_request` update with status=failed.
    pub fn apply_plan_failed(&mut self, error: &str) {
        self.plan_status = PlanStatus::Failed(error.to_owned());
        self.status_msg = Some(format!("Plan failed: {error}"));
    }

    /// Called when STDB delivers a `generate_job` update with status=done.
    pub fn apply_generate_done(&mut self, zip_url: String) {
        self.generate_status = GenerateStatus::Done { zip_url };
        self.status_msg = Some("Job done — downloading zip…".into());
    }

    /// Called when STDB delivers a `generate_job` update with status=failed.
    pub fn apply_generate_failed(&mut self, error: &str) {
        self.generate_status = GenerateStatus::Failed(error.to_owned());
        self.status_msg = Some(format!("Generate failed: {error}"));
    }

    /// Transition to Generate screen after plan approval.
    pub fn approve(&mut self) {
        if self.plan_status == PlanStatus::Done {
            self.screen = Screen::Generate;
            self.generate_status = GenerateStatus::Idle;
            self.status_msg = Some("Approved — press Enter to generate".into());
        }
    }
}
