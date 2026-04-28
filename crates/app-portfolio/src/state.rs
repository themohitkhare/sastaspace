//! In-memory state for the portfolio splash. Mirrors the `project` STDB
//! table; the shell hydrates this via `Portfolio::set_projects` whenever
//! a `StdbEvent::Updated("project")` action arrives.

#[derive(Debug, Clone, PartialEq)]
pub struct ProjectRow {
    pub slug: String,
    pub title: String,
    pub blurb: String,
    pub status: String,
}

#[derive(Debug, Default)]
pub struct PortfolioState {
    pub projects: Vec<ProjectRow>,
    pub selected: usize,
}

impl PortfolioState {
    pub fn set_projects(&mut self, mut rows: Vec<ProjectRow>) {
        rows.sort_by(|a, b| a.title.cmp(&b.title));
        self.projects = rows;
        if self.selected >= self.projects.len() {
            self.selected = self.projects.len().saturating_sub(1);
        }
    }

    pub fn move_selection(&mut self, delta: isize) {
        if self.projects.is_empty() {
            return;
        }
        let n = self.projects.len() as isize;
        let cur = self.selected as isize;
        let next = ((cur + delta).rem_euclid(n)) as usize;
        self.selected = next;
    }

    pub fn current(&self) -> Option<&ProjectRow> {
        self.projects.get(self.selected)
    }
}
