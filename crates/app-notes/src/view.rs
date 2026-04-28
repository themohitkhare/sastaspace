//! Pure render — no state mutation. Snapshot-tested.

use crate::state::{CommentRow, EditMode, Focus, NotesState};
use ratatui::{
    layout::{Alignment, Constraint, Direction, Layout, Rect},
    style::{Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Clear, List, ListItem, Paragraph, Wrap},
    Frame,
};
use sastaspace_core::theme::Theme;

pub fn render(frame: &mut Frame, area: Rect, state: &NotesState, theme: &Theme) {
    let layout = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(30), Constraint::Percentage(70)])
        .split(area);

    render_list(frame, layout[0], state, theme);
    render_editor(frame, layout[1], state, theme);

    if state.focus == Focus::Comments {
        render_comments_popover(frame, area, state, theme);
    }

    // Status bar at bottom of editor pane (drawn last so it overlays).
    if let Some(msg) = &state.status_msg {
        let status_area = Rect::new(
            layout[1].x,
            layout[1].y + layout[1].height - 1,
            layout[1].width,
            1,
        );
        let status = Paragraph::new(Span::styled(
            format!(" {msg} "),
            Style::default().fg(theme.accent),
        ));
        frame.render_widget(status, status_area);
    }
}

fn render_list(frame: &mut Frame, area: Rect, state: &NotesState, theme: &Theme) {
    let list_focused = state.focus == Focus::List;
    let border_style = if list_focused {
        Style::default().fg(theme.accent)
    } else {
        Style::default().fg(theme.border)
    };

    let items: Vec<ListItem> = state
        .notes
        .iter()
        .enumerate()
        .map(|(i, n)| {
            let style = if i == state.selected {
                theme.focused()
            } else {
                theme.body()
            };
            let line = Line::from(vec![
                Span::styled(format!(" {} ", n.title), style.add_modifier(Modifier::BOLD)),
                Span::styled(format!("· {}", n.status), theme.muted()),
            ]);
            ListItem::new(line)
        })
        .collect();

    let block = Block::default()
        .borders(Borders::ALL)
        .border_style(border_style)
        .title(" notes ");
    let list = List::new(items).block(block);
    frame.render_widget(list, area);
}

fn render_editor(frame: &mut Frame, area: Rect, state: &NotesState, theme: &Theme) {
    let editor_focused = matches!(state.focus, Focus::Editor);
    let border_style = if editor_focused {
        Style::default().fg(theme.accent)
    } else {
        Style::default().fg(theme.border)
    };

    let mode_indicator = match (editor_focused, state.edit_mode) {
        (true, EditMode::Insert) => " editor  [INSERT] ",
        (true, EditMode::Normal) => " editor  [NORMAL] ",
        _ => " editor ",
    };

    let block = Block::default()
        .borders(Borders::ALL)
        .border_style(border_style)
        .title(mode_indicator);

    match state.current_note() {
        None => {
            let para = Paragraph::new(vec![
                Line::from(""),
                Line::from(Span::styled(
                    "no notes yet — connecting to stdb…",
                    theme.muted(),
                )),
                Line::from(""),
                Line::from(Span::styled(
                    "j/k  navigate list  ·  Tab  focus editor  ·  i  insert  ·  :w  save  ·  c  comments",
                    theme.muted(),
                )),
            ])
            .block(block)
            .wrap(Wrap { trim: true });
            frame.render_widget(para, area);
        }
        Some(note) => {
            let title_line = Line::from(Span::styled(note.title.clone(), theme.header()));

            let body_text = if editor_focused && state.edit_mode == EditMode::Insert {
                // Show live buffer with cursor
                format!("{}_", state.editor_buf)
            } else {
                state.editor_buf.clone()
            };

            let mut lines = vec![title_line, Line::from("")];
            for line in body_text.lines() {
                lines.push(Line::from(Span::styled(line.to_string(), theme.body())));
            }
            if body_text.ends_with('\n') || body_text.is_empty() {
                lines.push(Line::from(Span::styled(
                    if editor_focused && state.edit_mode == EditMode::Insert {
                        "_"
                    } else {
                        ""
                    },
                    theme.body(),
                )));
            }
            lines.push(Line::from(""));
            lines.push(Line::from(Span::styled(
                format!("slug: {}  ·  tags: {}", note.slug, note.tags.join(", ")),
                theme.muted(),
            )));

            // Help hint at the bottom
            let help = if editor_focused {
                match state.edit_mode {
                    EditMode::Insert => "  esc → normal  ·  :w → save",
                    EditMode::Normal => {
                        "  i → insert  ·  :w → save  ·  c → comments  ·  Tab → list"
                    }
                }
            } else {
                "  Tab → editor  ·  c → comments  ·  j/k → navigate"
            };
            lines.push(Line::from(Span::styled(help, theme.muted())));

            if !state.cmd_buf.is_empty() && state.edit_mode == EditMode::Normal {
                lines.push(Line::from(Span::styled(
                    format!(":{}", state.cmd_buf.trim_start_matches(':')),
                    theme.body(),
                )));
            }

            let para = Paragraph::new(lines).block(block).wrap(Wrap { trim: true });
            frame.render_widget(para, area);
        }
    }
}

fn render_comments_popover(frame: &mut Frame, area: Rect, state: &NotesState, theme: &Theme) {
    let popup = centered_rect(70, 70, area);
    frame.render_widget(Clear, popup);

    let title = if let Some(note) = state.current_note() {
        format!(" comments: {} ", note.title)
    } else {
        " comments ".to_string()
    };

    let block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.accent))
        .title(title.as_str());

    let inner = block.inner(popup);
    frame.render_widget(block, popup);

    let layout = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Min(3), Constraint::Length(3)])
        .split(inner);

    // Comment list
    let comments = state.current_comments();
    let items: Vec<ListItem> = if comments.is_empty() {
        vec![ListItem::new(Line::from(Span::styled(
            "  no comments yet",
            theme.muted(),
        )))]
    } else {
        comments
            .iter()
            .map(|c| render_comment_item(c, theme))
            .collect()
    };
    let comment_list = List::new(items);
    frame.render_widget(comment_list, layout[0]);

    // Compose area
    let compose_block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.border))
        .title(" add comment (enter to submit  ·  esc to close) ");
    let compose = Paragraph::new(format!(" {}_", state.comment_buf))
        .block(compose_block)
        .alignment(Alignment::Left);
    frame.render_widget(compose, layout[1]);
}

fn render_comment_item<'a>(c: &'a CommentRow, theme: &Theme) -> ListItem<'a> {
    ListItem::new(vec![
        Line::from(vec![
            Span::styled(format!("  {} ", c.author_name), theme.header()),
            Span::styled(format!("· {}", c.status), theme.muted()),
        ]),
        Line::from(Span::styled(format!("  {}", c.body), theme.body())),
        Line::from(""),
    ])
}

fn centered_rect(percent_x: u16, percent_y: u16, r: Rect) -> Rect {
    let popup = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Percentage((100 - percent_y) / 2),
            Constraint::Percentage(percent_y),
            Constraint::Percentage((100 - percent_y) / 2),
        ])
        .split(r);
    Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage((100 - percent_x) / 2),
            Constraint::Percentage(percent_x),
            Constraint::Percentage((100 - percent_x) / 2),
        ])
        .split(popup[1])[1]
}
