//! Portfolio splash — the first screen the binary shows.
//! Reads `project` table rows pushed in via `set_projects`.

mod state;
mod view;

pub use state::{PortfolioState, ProjectRow};

use sastaspace_core::{
    event::{Action, InputAction},
    theme::Theme,
    App, AppResult,
};
use crossterm::event::{KeyCode, KeyEvent};
use ratatui::{layout::Rect, Frame};

pub struct Portfolio {
    state: PortfolioState,
    theme: Theme,
}

impl Portfolio {
    pub fn new() -> Self {
        Self {
            state: PortfolioState::default(),
            theme: Theme::default_dark(),
        }
    }

    pub fn set_projects(&mut self, rows: Vec<ProjectRow>) {
        self.state.set_projects(rows);
    }
}

impl Default for Portfolio {
    fn default() -> Self {
        Self::new()
    }
}

impl App for Portfolio {
    fn id(&self) -> &'static str {
        "portfolio"
    }

    fn title(&self) -> &str {
        "sastaspace · portfolio"
    }

    fn render(&mut self, frame: &mut Frame, area: Rect) {
        view::render(frame, area, &self.state, &self.theme);
    }

    fn handle(&mut self, action: Action) -> AppResult {
        if let Action::Input(InputAction::Key(KeyEvent { code, .. })) = action {
            match code {
                KeyCode::Char('j') | KeyCode::Down => self.state.move_selection(1),
                KeyCode::Char('k') | KeyCode::Up => self.state.move_selection(-1),
                _ => {}
            }
        }
        AppResult::Continue
    }
}
