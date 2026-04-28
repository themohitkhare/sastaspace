//! Pure render — no state mutation. Snapshot-tested.

use crate::state::{DeckState, GenerateStatus, PlanStatus, Screen};
use ratatui::{
    layout::{Constraint, Direction, Layout, Rect},
    style::{Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Gauge, List, ListItem, Paragraph, Wrap},
    Frame,
};
use sastaspace_core::theme::Theme;

pub fn render(frame: &mut Frame, area: Rect, state: &DeckState, theme: &Theme) {
    match state.screen {
        Screen::Plan => render_plan(frame, area, state, theme),
        Screen::Generate => render_generate(frame, area, state, theme),
    }
}

// ─── Plan screen ─────────────────────────────────────────────────────────────

fn render_plan(frame: &mut Frame, area: Rect, state: &DeckState, theme: &Theme) {
    let layout = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3), // header / status
            Constraint::Min(8),    // description input
            Constraint::Length(3), // track count row
            Constraint::Min(6),    // plan output (tracks)
            Constraint::Length(3), // footer hints
        ])
        .split(area);

    // ── Header ───────────────────────────────────────────────────────────────
    let status_text = match &state.plan_status {
        PlanStatus::Idle => Span::styled("idle", theme.muted()),
        PlanStatus::Pending => Span::styled("planning… (AI is thinking)", theme.body()),
        PlanStatus::Done => Span::styled("plan ready ✓", Style::default().fg(theme.success)),
        PlanStatus::Failed(e) => {
            Span::styled(format!("failed: {e}"), Style::default().fg(theme.error))
        }
    };
    let header = Paragraph::new(Line::from(vec![
        Span::styled(" deck ", theme.header()),
        Span::styled("· plan screen  status: ", theme.muted()),
        status_text,
    ]))
    .block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(theme.border)),
    );
    frame.render_widget(header, layout[0]);

    // ── Description input ────────────────────────────────────────────────────
    let desc_title = if state.editing {
        " description (insert — Esc to finish) "
    } else {
        " description (i = insert mode) "
    };
    let desc_block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(if state.editing {
            theme.accent
        } else {
            theme.border
        }))
        .title(desc_title);
    let desc_text = if state.description.is_empty() {
        Paragraph::new(Span::styled(
            "Describe the project audio you need…",
            theme.muted(),
        ))
        .block(desc_block)
    } else {
        Paragraph::new(state.description.as_str())
            .block(desc_block)
            .wrap(Wrap { trim: false })
    };
    frame.render_widget(desc_text, layout[1]);

    // ── Track count ───────────────────────────────────────────────────────────
    let gauge_label = format!(" tracks: {}  (← → to adjust) ", state.track_count);
    let gauge = Gauge::default()
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(theme.border))
                .title(gauge_label),
        )
        .gauge_style(Style::default().fg(theme.accent).bg(theme.border))
        .ratio(state.track_count as f64 / 10.0)
        .label(format!("{}/10", state.track_count));
    frame.render_widget(gauge, layout[2]);

    // ── Planned tracks list ───────────────────────────────────────────────────
    let tracks_block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.border))
        .title(" planned tracks ");

    if state.planned_tracks.is_empty() {
        let hint = match &state.plan_status {
            PlanStatus::Idle => "Enter description + press Enter to generate plan",
            PlanStatus::Pending => "Waiting for AI planner…",
            PlanStatus::Done => "Tracks loaded above (scroll if needed)",
            PlanStatus::Failed(_) => "Plan failed — check status",
        };
        let p = Paragraph::new(Span::styled(hint, theme.muted())).block(tracks_block);
        frame.render_widget(p, layout[3]);
    } else {
        let items: Vec<ListItem> = state
            .planned_tracks
            .iter()
            .enumerate()
            .map(|(i, t)| {
                let line = Line::from(vec![
                    Span::styled(format!(" {:2}. ", i + 1), theme.muted()),
                    Span::styled(t.name.clone(), theme.body().add_modifier(Modifier::BOLD)),
                    Span::styled(format!("  [{}]", t.kind), theme.muted()),
                    Span::styled(format!("  {}s", t.length), theme.muted()),
                    Span::styled(format!("  {}", t.mood), theme.muted()),
                ]);
                ListItem::new(line)
            })
            .collect();
        let list = List::new(items).block(tracks_block);
        frame.render_widget(list, layout[3]);
    }

    // ── Footer hints ──────────────────────────────────────────────────────────
    let hints = match &state.plan_status {
        PlanStatus::Done => {
            " Enter/g = generate   :approve = advance to generate screen   q = quit "
        }
        _ => " i = insert desc   ← → = track count   Enter = plan   q = quit ",
    };
    let footer = Paragraph::new(Span::styled(hints, theme.muted())).block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(theme.border)),
    );
    frame.render_widget(footer, layout[4]);
}

// ─── Generate screen ──────────────────────────────────────────────────────────

fn render_generate(frame: &mut Frame, area: Rect, state: &DeckState, theme: &Theme) {
    let layout = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3), // header
            Constraint::Min(10),   // tracks + status
            Constraint::Length(3), // footer hints
        ])
        .split(area);

    // ── Header ────────────────────────────────────────────────────────────────
    let gen_status_span = match &state.generate_status {
        GenerateStatus::Idle => Span::styled("idle — press Enter to start", theme.muted()),
        GenerateStatus::Pending => {
            Span::styled("generating audio… (this takes a few minutes)", theme.body())
        }
        GenerateStatus::Done { .. } => {
            Span::styled("done — downloading zip", Style::default().fg(theme.accent))
        }
        GenerateStatus::Failed(e) => {
            Span::styled(format!("failed: {e}"), Style::default().fg(theme.error))
        }
        GenerateStatus::Downloading => {
            Span::styled("downloading zip…", Style::default().fg(theme.accent))
        }
        GenerateStatus::Downloaded { path } => Span::styled(
            format!("saved to {path}"),
            Style::default().fg(theme.success),
        ),
    };
    let header = Paragraph::new(Line::from(vec![
        Span::styled(" deck ", theme.header()),
        Span::styled("· generate screen  status: ", theme.muted()),
        gen_status_span,
    ]))
    .block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(theme.border)),
    );
    frame.render_widget(header, layout[0]);

    // ── Body: track list + status message ────────────────────────────────────
    let body_layout = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(60), Constraint::Percentage(40)])
        .split(layout[1]);

    // Left: track list
    let tracks_block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.border))
        .title(" tracks to generate ");
    let items: Vec<ListItem> = state
        .planned_tracks
        .iter()
        .enumerate()
        .map(|(i, t)| {
            let line = Line::from(vec![
                Span::styled(format!(" {:2}. ", i + 1), theme.muted()),
                Span::styled(t.name.clone(), theme.body().add_modifier(Modifier::BOLD)),
                Span::styled(format!("  {}s  {} ", t.length, t.mood), theme.muted()),
            ]);
            ListItem::new(line)
        })
        .collect();
    if items.is_empty() {
        let p = Paragraph::new(Span::styled(
            "No tracks — go back to Plan screen",
            theme.muted(),
        ))
        .block(tracks_block);
        frame.render_widget(p, body_layout[0]);
    } else {
        let list = List::new(items).block(tracks_block);
        frame.render_widget(list, body_layout[0]);
    }

    // Right: status / download info
    let info_lines = build_info_lines(state, theme);
    let info = Paragraph::new(info_lines)
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(theme.border))
                .title(" info "),
        )
        .wrap(Wrap { trim: true });
    frame.render_widget(info, body_layout[1]);

    // ── Footer hints ──────────────────────────────────────────────────────────
    let hints = match &state.generate_status {
        GenerateStatus::Downloaded { .. } => {
            #[cfg(feature = "audio")]
            {
                " p = play first track   b = back to plan   q = quit "
            }
            #[cfg(not(feature = "audio"))]
            {
                " b = back to plan   q = quit  (audio playback not compiled in) "
            }
        }
        _ => " Enter = start generate   b = back to plan   q = quit ",
    };
    let footer = Paragraph::new(Span::styled(hints, theme.muted())).block(
        Block::default()
            .borders(Borders::ALL)
            .border_style(Style::default().fg(theme.border)),
    );
    frame.render_widget(footer, layout[2]);
}

fn build_info_lines<'a>(state: &'a DeckState, theme: &'a Theme) -> Vec<Line<'a>> {
    let mut lines = Vec::new();

    if let Some(id) = state.plan_request_id {
        lines.push(Line::from(vec![
            Span::styled("plan id: ", theme.muted()),
            Span::styled(id.to_string(), theme.body()),
        ]));
    }
    if let Some(id) = state.generate_job_id {
        lines.push(Line::from(vec![
            Span::styled("job id:  ", theme.muted()),
            Span::styled(id.to_string(), theme.body()),
        ]));
    }
    lines.push(Line::from(""));

    match &state.generate_status {
        GenerateStatus::Downloaded { path } => {
            lines.push(Line::from(Span::styled("Files saved to:", theme.muted())));
            lines.push(Line::from(Span::styled(
                path.clone(),
                theme.body().add_modifier(Modifier::BOLD),
            )));
        }
        GenerateStatus::Done { zip_url } => {
            lines.push(Line::from(Span::styled("Zip URL:", theme.muted())));
            lines.push(Line::from(Span::styled(zip_url.clone(), theme.body())));
        }
        GenerateStatus::Failed(e) => {
            lines.push(Line::from(Span::styled(
                format!("Error: {e}"),
                Style::default().fg(theme.error),
            )));
        }
        _ => {}
    }

    if let Some(msg) = &state.status_msg {
        lines.push(Line::from(""));
        lines.push(Line::from(Span::styled(msg.clone(), theme.muted())));
    }

    lines
}
