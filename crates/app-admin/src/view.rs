//! Pure render functions for the admin dashboard.
//! No state mutation — all reads from `AdminState`.

use crate::state::{
    AdminState, ContainerRow, DeviceFlowPhase, FlaggedComment, Focus, LogPopoverState,
};
use ratatui::{
    layout::{Alignment, Constraint, Direction, Layout, Rect},
    style::{Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Clear, List, ListItem, Paragraph, Wrap},
    Frame,
};
use sastaspace_core::theme::Theme;

// ── Top-level render dispatch ─────────────────────────────────────────────────

pub fn render(frame: &mut Frame, area: Rect, state: &AdminState, theme: &Theme) {
    if !state.is_authenticated() {
        render_device_flow(frame, area, state, theme);
        return;
    }

    // btop-style: three vertical sections
    let rows = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(9),  // metrics
            Constraint::Length(10), // containers
            Constraint::Min(6),     // moderation queue
        ])
        .split(area);

    render_metrics(frame, rows[0], state, theme);
    render_containers(frame, rows[1], state, theme);
    render_moderation(frame, rows[2], state, theme);

    // Log popover overlays everything.
    if matches!(&state.log_popover, LogPopoverState::Open { .. }) {
        render_log_popover(frame, area, state, theme);
    }
}

// ── Device-flow panel ─────────────────────────────────────────────────────────

fn render_device_flow(frame: &mut Frame, area: Rect, state: &AdminState, theme: &Theme) {
    // Centre a fixed-size box in the terminal.
    let popup = centered_rect(60, 14, area);

    let block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.accent))
        .title(Span::styled(" admin · owner login ", theme.header()));

    let body = match &state.device_flow {
        DeviceFlowPhase::Idle => vec![
            Line::from(""),
            Line::from(Span::styled("Owner authentication required.", theme.body())),
            Line::from(""),
            Line::from(Span::styled(
                "Press [enter] to start Google device-flow login.",
                theme.muted(),
            )),
        ],
        DeviceFlowPhase::Requesting => vec![
            Line::from(""),
            Line::from(Span::styled("Requesting code from Google…", theme.muted())),
        ],
        DeviceFlowPhase::Pending {
            user_code,
            verification_url,
            ..
        } => {
            let remaining = state
                .time_remaining()
                .map(|d| format!("{}s remaining", d.as_secs()))
                .unwrap_or_default();
            vec![
                Line::from(""),
                Line::from(Span::styled("Open this URL on any device:", theme.body())),
                Line::from(Span::styled(
                    format!("  {verification_url}"),
                    theme.header(),
                )),
                Line::from(""),
                Line::from(Span::styled("Then enter this code:", theme.body())),
                Line::from(Span::styled(
                    format!("  {user_code}"),
                    Style::default()
                        .fg(theme.accent)
                        .add_modifier(Modifier::BOLD),
                )),
                Line::from(""),
                Line::from(Span::styled(remaining, theme.muted())),
                Line::from(""),
                Line::from(Span::styled("Polling… (ctrl-c to cancel)", theme.muted())),
            ]
        }
        DeviceFlowPhase::Done => vec![
            Line::from(""),
            Line::from(Span::styled(
                "Authenticated! Loading dashboard…",
                Style::default().fg(theme.success),
            )),
        ],
        DeviceFlowPhase::Failed(msg) => vec![
            Line::from(""),
            Line::from(Span::styled(
                "Authentication failed:",
                Style::default().fg(theme.error),
            )),
            Line::from(Span::styled(msg.clone(), theme.body())),
            Line::from(""),
            Line::from(Span::styled("Press [enter] to retry.", theme.muted())),
        ],
    };

    frame.render_widget(Clear, popup);
    let inner = block.inner(popup);
    frame.render_widget(block, popup);
    let para = Paragraph::new(body)
        .alignment(Alignment::Center)
        .wrap(Wrap { trim: true });
    frame.render_widget(para, inner);
}

// ── System metrics panel ──────────────────────────────────────────────────────

fn render_metrics(frame: &mut Frame, area: Rect, state: &AdminState, theme: &Theme) {
    let focused = state.focus == Focus::Metrics;
    let border_style = if focused {
        Style::default().fg(theme.accent)
    } else {
        Style::default().fg(theme.border)
    };
    let block = Block::default()
        .borders(Borders::ALL)
        .border_style(border_style)
        .title(Span::styled(" system metrics ", theme.header()));

    let m = &state.metrics;

    let uptime_str = format_uptime(m.uptime_s);
    let gpu_line = match (&m.gpu_model, m.gpu_pct) {
        (Some(model), Some(pct)) => format!("GPU {model}: {pct}%"),
        (Some(model), None) => format!("GPU {model}"),
        _ => "GPU: n/a".into(),
    };

    let lines = vec![
        Line::from(vec![
            Span::styled("CPU  ", theme.muted()),
            Span::styled(format!("{:.1}%", m.cpu_pct), bar_style(m.cpu_pct, theme)),
            Span::styled(format!("  ({} cores)", m.cores), theme.muted()),
        ]),
        Line::from(vec![
            Span::styled("MEM  ", theme.muted()),
            Span::styled(
                format!("{:.1}/{:.1} GB", m.mem_used_gb, m.mem_total_gb),
                bar_style(m.mem_pct, theme),
            ),
            Span::styled(format!("  ({:.1}%)", m.mem_pct), theme.muted()),
        ]),
        Line::from(vec![
            Span::styled("SWAP ", theme.muted()),
            Span::styled(
                format!("{}/{} MB", m.swap_used_mb, m.swap_total_mb),
                theme.body(),
            ),
        ]),
        Line::from(vec![
            Span::styled("DISK ", theme.muted()),
            Span::styled(
                format!("{}/{} GB", m.disk_used_gb, m.disk_total_gb),
                bar_style(m.disk_pct, theme),
            ),
            Span::styled(format!("  ({:.1}%)", m.disk_pct), theme.muted()),
        ]),
        Line::from(vec![
            Span::styled("NET  ", theme.muted()),
            Span::styled(
                format!(
                    "↑ {}  ↓ {}",
                    fmt_bytes(m.net_tx_bytes),
                    fmt_bytes(m.net_rx_bytes)
                ),
                theme.body(),
            ),
        ]),
        Line::from(vec![
            Span::styled("UP   ", theme.muted()),
            Span::styled(uptime_str, theme.body()),
            Span::styled("  ", theme.muted()),
            Span::styled(gpu_line, theme.muted()),
        ]),
    ];

    let inner = block.inner(area);
    frame.render_widget(block, area);
    let para = Paragraph::new(lines);
    frame.render_widget(para, inner);
}

fn bar_style(pct: f32, theme: &Theme) -> Style {
    if pct >= 90.0 {
        Style::default().fg(theme.error)
    } else if pct >= 70.0 {
        Style::default().fg(theme.warn)
    } else {
        Style::default().fg(theme.success)
    }
}

fn fmt_bytes(b: u64) -> String {
    if b >= 1_000_000_000 {
        format!("{:.1} GB", b as f64 / 1e9)
    } else if b >= 1_000_000 {
        format!("{:.1} MB", b as f64 / 1e6)
    } else if b >= 1_000 {
        format!("{:.1} KB", b as f64 / 1e3)
    } else {
        format!("{b} B")
    }
}

fn format_uptime(s: u64) -> String {
    let days = s / 86400;
    let hours = (s % 86400) / 3600;
    let mins = (s % 3600) / 60;
    if days > 0 {
        format!("{days}d {hours}h {mins}m")
    } else if hours > 0 {
        format!("{hours}h {mins}m")
    } else {
        format!("{mins}m")
    }
}

// ── Container status panel ────────────────────────────────────────────────────

fn render_containers(frame: &mut Frame, area: Rect, state: &AdminState, theme: &Theme) {
    let focused = state.focus == Focus::Containers;
    let border_style = if focused {
        Style::default().fg(theme.accent)
    } else {
        Style::default().fg(theme.border)
    };
    let block = Block::default()
        .borders(Borders::ALL)
        .border_style(border_style)
        .title(Span::styled(" containers ", theme.header()));

    let items: Vec<ListItem> = state
        .containers
        .iter()
        .map(|c| render_container_row(c, theme))
        .collect();

    let list = if items.is_empty() {
        List::new(vec![ListItem::new(Span::styled(
            "  no containers — waiting for collector…",
            theme.muted(),
        ))])
        .block(block)
    } else {
        List::new(items).block(block)
    };
    frame.render_widget(list, area);
}

fn render_container_row(c: &ContainerRow, theme: &Theme) -> ListItem<'static> {
    let status_style = if c.status.contains("running") || c.status.contains("Up") {
        Style::default().fg(theme.success)
    } else if c.status.contains("exited") || c.status.contains("Exit") {
        Style::default().fg(theme.error)
    } else {
        Style::default().fg(theme.warn)
    };

    let mem_str = if c.mem_limit_mb > 0 {
        format!("{}/{} MB", c.mem_used_mb, c.mem_limit_mb)
    } else {
        format!("{} MB", c.mem_used_mb)
    };

    let restart_str = if c.restart_count > 0 {
        format!("  restarts:{}", c.restart_count)
    } else {
        String::new()
    };

    let uptime_str = format_uptime(c.uptime_s);

    Line::from(vec![
        Span::styled(format!("  {:<28}", truncate(&c.name, 28)), theme.body()),
        Span::styled(format!("{:<12}", truncate(&c.status, 12)), status_style),
        Span::styled(format!("  mem {:<14}", mem_str), theme.muted()),
        Span::styled(format!("up {:<10}", uptime_str), theme.muted()),
        Span::styled(restart_str, Style::default().fg(theme.warn)),
    ])
    .into()
}

fn truncate(s: &str, max: usize) -> &str {
    &s[..s.char_indices().nth(max).map(|(i, _)| i).unwrap_or(s.len())]
}

// ── Moderation queue panel ────────────────────────────────────────────────────

fn render_moderation(frame: &mut Frame, area: Rect, state: &AdminState, theme: &Theme) {
    let focused = state.focus == Focus::Moderation;
    let border_style = if focused {
        Style::default().fg(theme.accent)
    } else {
        Style::default().fg(theme.border)
    };

    let hint = if focused {
        " [a]pprove [r]eject [d]elete [l]ogs "
    } else {
        " flagged comments · [tab] to focus "
    };

    let block = Block::default()
        .borders(Borders::ALL)
        .border_style(border_style)
        .title(Span::styled(" moderation queue ", theme.header()))
        .title_bottom(Span::styled(hint, theme.muted()));

    if state.flagged.is_empty() {
        let para = Paragraph::new(vec![
            Line::from(""),
            Line::from(Span::styled(
                "  no flagged comments — queue is clear.",
                theme.muted(),
            )),
        ])
        .block(block);
        frame.render_widget(para, area);
        return;
    }

    let items: Vec<ListItem> = state
        .flagged
        .iter()
        .enumerate()
        .map(|(i, c)| render_moderation_row(i, c, i == state.flagged_selected, theme))
        .collect();

    let list = List::new(items).block(block);
    frame.render_widget(list, area);
}

fn render_moderation_row(
    _idx: usize,
    c: &FlaggedComment,
    selected: bool,
    theme: &Theme,
) -> ListItem<'static> {
    let row_style = if selected {
        theme.focused()
    } else {
        theme.body()
    };
    let slug_style = if selected {
        theme.focused()
    } else {
        theme.muted()
    };

    let body_preview = truncate(&c.body, 60).to_string();
    Line::from(vec![
        Span::styled(format!("  #{:<6} ", c.id), slug_style),
        Span::styled(format!("{:<20}  ", truncate(&c.author_name, 20)), row_style),
        Span::styled(format!("[{}]  ", truncate(&c.post_slug, 12)), slug_style),
        Span::styled(body_preview, row_style),
    ])
    .into()
}

// ── Log popover ───────────────────────────────────────────────────────────────

fn render_log_popover(frame: &mut Frame, area: Rect, state: &AdminState, theme: &Theme) {
    let popup = centered_rect(90, 80, area);
    frame.render_widget(Clear, popup);

    let container_name = match &state.log_popover {
        LogPopoverState::Open { container } => container.clone(),
        _ => String::new(),
    };

    let block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.accent))
        .title(Span::styled(
            format!(" logs · {container_name} "),
            theme.header(),
        ))
        .title_bottom(Span::styled(" [esc] close ", theme.muted()));

    let inner = block.inner(popup);
    frame.render_widget(block, popup);

    // Show the most recent lines that fit in the popup height.
    let visible_rows = inner.height as usize;
    // Collect filtered lines first, then take the tail.
    let filtered: Vec<&crate::state::LogLine> = state
        .log_lines
        .iter()
        .filter(|l| l.container == container_name)
        .collect();
    let start = filtered.len().saturating_sub(visible_rows);
    let lines: Vec<Line> = filtered[start..]
        .iter()
        .map(|l| {
            let level_style = match l.level.as_str() {
                "error" => Style::default().fg(theme.error),
                "warn" => Style::default().fg(theme.warn),
                "debug" => Style::default().fg(theme.muted),
                _ => theme.body(),
            };
            Line::from(vec![
                Span::styled(format!("{:<6} ", truncate(&l.level, 6)), level_style),
                Span::styled(l.text.clone(), theme.body()),
            ])
        })
        .collect();

    if lines.is_empty() {
        let para = Paragraph::new(vec![Line::from(Span::styled(
            "  waiting for log events…",
            theme.muted(),
        ))]);
        frame.render_widget(para, inner);
    } else {
        let para = Paragraph::new(lines);
        frame.render_widget(para, inner);
    }
}

// ── Layout helpers ────────────────────────────────────────────────────────────

/// Return a `Rect` centred in `base` with the given percentage dimensions.
fn centered_rect(percent_x: u16, percent_y: u16, base: Rect) -> Rect {
    let popup_height = base.height * percent_y / 100;
    let popup_width = base.width * percent_x / 100;
    let y = base.y + (base.height.saturating_sub(popup_height)) / 2;
    let x = base.x + (base.width.saturating_sub(popup_width)) / 2;
    Rect::new(x, y, popup_width, popup_height)
}
