//! Pure render — no state mutation. Snapshot-tested.

use crate::state::{PortfolioState, ProjectRow};
use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, List, ListItem, Paragraph, Wrap},
    Frame,
};
use sastaspace_core::theme::Theme;

pub fn render(frame: &mut Frame, area: Rect, state: &PortfolioState, theme: &Theme) {
    let layout = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(40), Constraint::Percentage(60)])
        .split(area);

    render_list(frame, layout[0], state, theme);
    render_detail(frame, layout[1], state.current(), theme);
}

fn render_list(frame: &mut Frame, area: Rect, state: &PortfolioState, theme: &Theme) {
    let items: Vec<ListItem> = state
        .projects
        .iter()
        .enumerate()
        .map(|(i, p)| {
            let style = if i == state.selected {
                theme.focused()
            } else {
                theme.body()
            };
            let line = Line::from(vec![
                Span::styled(format!(" {} ", p.title), style.add_modifier(Modifier::BOLD)),
                Span::styled(format!("· {}", p.status), theme.muted()),
            ]);
            ListItem::new(line)
        })
        .collect();
    let block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.border))
        .title(" projects ");
    let list = List::new(items).block(block);
    frame.render_widget(list, area);
}

fn render_detail(frame: &mut Frame, area: Rect, project: Option<&ProjectRow>, theme: &Theme) {
    let block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.border))
        .title(" detail ");
    let body = match project {
        Some(p) => vec![
            Line::from(Span::styled(p.title.clone(), theme.header())),
            Line::from(""),
            Line::from(Span::styled(p.blurb.clone(), theme.body())),
            Line::from(""),
            Line::from(Span::styled(format!("slug:   {}", p.slug), theme.muted())),
            Line::from(Span::styled(format!("status: {}", p.status), theme.muted())),
        ],
        None => vec![
            Line::from(""),
            Line::from(Span::styled(
                "no projects yet — connecting to stdb.sastaspace.com…",
                theme.muted(),
            )),
        ],
    };
    let para = Paragraph::new(body).block(block).wrap(Wrap { trim: true });
    frame.render_widget(para, area);
}
