//! Pure render functions — no I/O, no state mutation.
//! Each public `render_*` function corresponds to one screen.

use ratatui::{
    layout::{Alignment, Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Clear, Gauge, List, ListItem, Paragraph, Wrap},
    Frame,
};
use sastaspace_core::theme::Theme;

use crate::state::{
    BattleState, LeaderboardState, LegionId, LegionSelectState, LegionSwapState,
    LiberatedSplashState, ProfileState, RegionStatus, TypewarsState, WarMapState,
};

// ---------------------------------------------------------------------------
// Top-level dispatcher
// ---------------------------------------------------------------------------

pub fn render(frame: &mut Frame, area: Rect, state: &TypewarsState, theme: &Theme) {
    use crate::state::Screen;
    match state.screen {
        Screen::LegionSelect => render_legion_select(frame, area, &state.legion_select, theme),
        Screen::WarMap => render_war_map(frame, area, &state.war_map, theme),
        Screen::Battle => {
            if let Some(battle) = &state.battle {
                render_battle(frame, area, battle, theme);
            }
        }
        Screen::Leaderboard => render_leaderboard(frame, area, &state.leaderboard, theme),
        Screen::Profile => {
            // Render leaderboard underneath, then profile on top.
            render_leaderboard(frame, area, &state.leaderboard, theme);
            if let Some(profile) = &state.profile {
                render_profile_modal(frame, area, profile, theme);
            }
        }
        Screen::LegionSwap => {
            render_war_map(frame, area, &state.war_map, theme);
            if let Some(swap) = &state.legion_swap {
                render_legion_swap_modal(frame, area, swap, theme);
            }
        }
        Screen::LiberatedSplash => {
            if let Some(splash) = &state.liberated_splash {
                render_liberated_splash(frame, area, splash, theme);
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Legion select
// ---------------------------------------------------------------------------

pub fn render_legion_select(
    frame: &mut Frame,
    area: Rect,
    state: &LegionSelectState,
    theme: &Theme,
) {
    let layout = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3), // header
            Constraint::Length(2), // eyebrow + title
            Constraint::Min(10),   // grid
            Constraint::Length(5), // callsign + enlist
            Constraint::Length(1), // warning
        ])
        .split(area);

    // Header
    let header = Paragraph::new(Line::from(vec![
        Span::styled("typewars", theme.header()),
        Span::styled(" · enlistment", theme.muted()),
    ]))
    .block(
        Block::default()
            .borders(Borders::BOTTOM)
            .border_style(Style::default().fg(theme.border)),
    );
    frame.render_widget(header, layout[0]);

    // Title area
    let title_area = layout[1];
    let title = Paragraph::new(vec![Line::from(Span::styled(
        "CHOOSE YOUR LEGION",
        theme.header().add_modifier(Modifier::BOLD),
    ))]);
    frame.render_widget(title, title_area);

    // Grid — 5 equal columns
    let grid_cols = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage(20),
            Constraint::Percentage(20),
            Constraint::Percentage(20),
            Constraint::Percentage(20),
            Constraint::Percentage(20),
        ])
        .split(layout[2]);

    for (i, id) in LegionId::all().iter().enumerate() {
        let is_selected = state.cursor == i;
        let card_style = if is_selected {
            Style::default().fg(theme.bg).bg(theme.accent)
        } else {
            Style::default().fg(theme.fg)
        };
        let border_style = if is_selected {
            Style::default().fg(theme.accent)
        } else {
            Style::default().fg(theme.border)
        };
        let tag = format!("0{} · {}", i + 1, id.short());
        let block = Block::default()
            .borders(Borders::ALL)
            .border_style(border_style)
            .title(Span::styled(
                format!(" {tag} "),
                if is_selected {
                    theme.header()
                } else {
                    theme.muted()
                },
            ));
        let body = vec![
            Line::from(Span::styled(
                id.name(),
                card_style.add_modifier(Modifier::BOLD),
            )),
            Line::from(""),
            Line::from(Span::styled(id.mechanic(), theme.muted())),
            Line::from(""),
            Line::from(Span::styled(
                id.description(),
                Style::default().fg(theme.muted),
            )),
            Line::from(""),
            if is_selected {
                Line::from(Span::styled("[ selected ]", theme.header()))
            } else {
                Line::from(Span::styled("← / → to select", theme.muted()))
            },
        ];
        let para = Paragraph::new(body).block(block).wrap(Wrap { trim: true });
        frame.render_widget(para, grid_cols[i]);
    }

    // Callsign + Enlist
    let finalize_layout = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Length(3), Constraint::Length(2)])
        .split(layout[3]);

    let callsign_block = Block::default()
        .borders(Borders::ALL)
        .border_style(if state.focus_input {
            Style::default().fg(theme.accent)
        } else {
            Style::default().fg(theme.border)
        })
        .title(Span::styled(
            format!(" callsign ({}/24) ", state.callsign.len()),
            theme.muted(),
        ));
    let callsign_val = if state.callsign.is_empty() {
        Span::styled("enter your callsign", theme.muted())
    } else {
        Span::styled(state.callsign.clone(), theme.body())
    };
    let callsign_para = Paragraph::new(Line::from(callsign_val)).block(callsign_block);
    frame.render_widget(callsign_para, finalize_layout[0]);

    let enlist_label = if state.submitting {
        "enlisting…"
    } else if !state.can_submit() {
        "Enlist → (choose a legion and enter callsign)"
    } else {
        "[ Enter ] Enlist →"
    };
    let enlist_style = if state.can_submit() {
        theme.header().add_modifier(Modifier::BOLD)
    } else {
        theme.muted()
    };
    let enlist_para = Paragraph::new(Line::from(Span::styled(enlist_label, enlist_style)));
    frame.render_widget(enlist_para, finalize_layout[1]);

    // Error / warning
    let warn_text = state
        .error
        .as_deref()
        .unwrap_or("Legion allegiance is permanent for the season. Choose carefully.");
    let warn_para = Paragraph::new(Line::from(Span::styled(
        warn_text,
        if state.error.is_some() {
            Style::default().fg(theme.error)
        } else {
            theme.muted()
        },
    )));
    frame.render_widget(warn_para, layout[4]);
}

// ---------------------------------------------------------------------------
// War map
// ---------------------------------------------------------------------------

pub fn render_war_map(frame: &mut Frame, area: Rect, state: &WarMapState, theme: &Theme) {
    let layout = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3), // header bar
            Constraint::Min(0),    // body
        ])
        .split(area);

    // Header
    let stats_line = Line::from(vec![
        Span::styled("typewars · war map", theme.header()),
        Span::styled("  |  ", theme.muted()),
        Span::styled("liberated: ", theme.muted()),
        Span::styled(format!("{}/25", state.liberated_count()), theme.body()),
        Span::styled("  contested: ", theme.muted()),
        Span::styled(state.contested_count().to_string(), theme.body()),
        Span::styled("  pristine: ", theme.muted()),
        Span::styled(state.pristine_count().to_string(), theme.body()),
    ]);
    let header_block = Block::default()
        .borders(Borders::BOTTOM)
        .border_style(Style::default().fg(theme.border));
    let header = Paragraph::new(stats_line).block(header_block);
    frame.render_widget(header, layout[0]);

    // Body: split left (region list) + right (detail panel)
    let body_layout = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(55), Constraint::Percentage(45)])
        .split(layout[1]);

    render_region_list(frame, body_layout[0], state, theme);
    render_region_detail_panel(frame, body_layout[1], state, theme);
}

fn render_region_list(frame: &mut Frame, area: Rect, state: &WarMapState, theme: &Theme) {
    let items: Vec<ListItem> = state
        .regions
        .iter()
        .enumerate()
        .map(|(i, r)| {
            let is_sel = i == state.selected;
            let (status_str, status_style) = match r.status() {
                RegionStatus::Liberated(id) => (
                    format!("[{}]", id.short()),
                    Style::default().fg(legion_color(id, theme)),
                ),
                RegionStatus::Contested => ("[~~~]".to_string(), Style::default().fg(theme.warn)),
                RegionStatus::Pristine => ("[   ]".to_string(), theme.muted()),
            };
            let hp_pct = r.hp_pct();
            let bar_len = 12usize;
            let filled = ((hp_pct * bar_len as f64).round() as usize).min(bar_len);
            let bar: String = "█".repeat(filled) + &"░".repeat(bar_len - filled);

            let row_style = if is_sel {
                theme.focused()
            } else {
                theme.body()
            };
            let line = Line::from(vec![
                Span::styled(
                    format!("{:2}  {:>16}  T{}  ", r.id + 1, r.name, r.tier),
                    row_style,
                ),
                Span::styled(
                    status_str,
                    if is_sel {
                        theme.focused()
                    } else {
                        status_style
                    },
                ),
                Span::styled("  ", row_style),
                Span::styled(
                    bar,
                    if is_sel {
                        theme.focused()
                    } else {
                        Style::default().fg(theme.success)
                    },
                ),
            ]);
            ListItem::new(line)
        })
        .collect();

    let block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.border))
        .title(Span::styled(
            format!(
                " all regions (j/k or ↑/↓ · Enter to battle) · T1:{} T2:{} T3:{} ",
                state.regions.iter().filter(|r| r.tier == 1).count(),
                state.regions.iter().filter(|r| r.tier == 2).count(),
                state.regions.iter().filter(|r| r.tier == 3).count(),
            ),
            theme.muted(),
        ));
    let list = List::new(items).block(block);
    frame.render_widget(list, area);
}

fn render_region_detail_panel(frame: &mut Frame, area: Rect, state: &WarMapState, theme: &Theme) {
    // Legend section at bottom
    let main_layout = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Min(0), Constraint::Length(8)])
        .split(area);

    // Detail / prompt
    let detail_block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.border))
        .title(Span::styled(" region detail ", theme.muted()));

    match state.selected_region() {
        None => {
            let para = Paragraph::new(Line::from(Span::styled(
                "select a region from the list",
                theme.muted(),
            )))
            .block(detail_block);
            frame.render_widget(para, main_layout[0]);
        }
        Some(r) => {
            let mut lines: Vec<Line> = Vec::new();
            lines.push(Line::from(vec![
                Span::styled(format!("  {:02} · ", r.id + 1), theme.muted()),
                Span::styled(r.name.clone(), theme.header().add_modifier(Modifier::BOLD)),
                Span::styled(format!("  T{}", r.tier), theme.muted()),
            ]));
            lines.push(Line::from(""));

            match r.status() {
                RegionStatus::Liberated(id) => {
                    lines.push(Line::from(Span::styled(
                        format!("  HELD by {} ({})", id.name(), id.short()),
                        Style::default()
                            .fg(legion_color(id, theme))
                            .add_modifier(Modifier::BOLD),
                    )));
                }
                _ => {
                    let hp_pct = r.hp_pct();
                    let bar_width = (area.width as usize).saturating_sub(6).min(40);
                    let filled = ((hp_pct * bar_width as f64).round() as usize).min(bar_width);
                    let bar = "█".repeat(filled) + &"░".repeat(bar_width - filled);
                    lines.push(Line::from(vec![
                        Span::styled("  enemy HP  ", theme.muted()),
                        Span::styled(format!("{} / {}", r.enemy_hp, r.enemy_max_hp), theme.body()),
                    ]));
                    lines.push(Line::from(Span::styled(
                        format!("  {bar}"),
                        Style::default().fg(theme.error),
                    )));
                    lines.push(Line::from(""));
                    // Contributions
                    let total_dmg = r.total_damage();
                    if total_dmg > 0 {
                        lines.push(Line::from(Span::styled("  damage dealt:", theme.muted())));
                        for id in LegionId::all() {
                            let dmg = r.damage[id.as_u8() as usize];
                            if dmg == 0 {
                                continue;
                            }
                            let pct = (dmg as f64 / total_dmg as f64 * 20.0).round() as usize;
                            let contrib_bar = "▓".repeat(pct) + &"░".repeat(20 - pct);
                            lines.push(Line::from(vec![
                                Span::styled(
                                    format!("  {:<6}", id.short()),
                                    Style::default().fg(legion_color(id, theme)),
                                ),
                                Span::styled(
                                    contrib_bar,
                                    Style::default().fg(legion_color(id, theme)),
                                ),
                                Span::styled(format!(" {}", dmg), theme.muted()),
                            ]));
                        }
                        lines.push(Line::from(""));
                    }
                }
            }
            lines.push(Line::from(Span::styled(
                format!(
                    "  {} active · {} wardens · regen {}/s",
                    r.active_wardens, r.active_wardens, r.regen_rate
                ),
                theme.muted(),
            )));
            lines.push(Line::from(""));
            lines.push(Line::from(Span::styled(
                "  [ Enter ] ENTER BATTLE",
                theme.header().add_modifier(Modifier::BOLD),
            )));

            let para = Paragraph::new(lines)
                .block(detail_block)
                .wrap(Wrap { trim: false });
            frame.render_widget(para, main_layout[0]);
        }
    }

    // Legion legend
    let legend_block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.border))
        .title(Span::styled(" legion standings ", theme.muted()));
    let legend_lines: Vec<Line> = LegionId::all()
        .iter()
        .map(|&id| {
            let count = state.legion_region_count(id);
            Line::from(vec![
                Span::styled(
                    format!("  {:<4}", id.short()),
                    Style::default().fg(legion_color(id, theme)),
                ),
                Span::styled(format!("  {:<12}", id.name()), theme.body()),
                Span::styled(format!("{} regions", count), theme.muted()),
            ])
        })
        .collect();
    let legend = Paragraph::new(legend_lines).block(legend_block);
    frame.render_widget(legend, main_layout[1]);
}

// ---------------------------------------------------------------------------
// Battle
// ---------------------------------------------------------------------------

pub fn render_battle(frame: &mut Frame, area: Rect, state: &BattleState, theme: &Theme) {
    let layout = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3), // header / HUD
            Constraint::Length(6), // region HP + contrib
            Constraint::Min(8),    // word grid
            Constraint::Length(3), // input row
            Constraint::Length(2), // legion hud
        ])
        .split(area);

    // Header HUD
    let session = state.session.as_ref();
    let wpm = state.wpm();
    let acc = state.accuracy();
    let dmg = session.map(|s| s.damage_dealt).unwrap_or(0);
    let streak = session.map(|s| s.streak).unwrap_or(0);
    let mult = session.map(|s| s.multiplier).unwrap_or(1.0);

    let hud_line = Line::from(vec![
        Span::styled("← [Esc] exit  ", theme.muted()),
        Span::styled(state.region.name.clone(), theme.header()),
        Span::styled(format!(" · T{}", state.region.tier), theme.muted()),
        Span::styled("    WPM: ", theme.muted()),
        Span::styled(format!("{wpm}"), theme.body().add_modifier(Modifier::BOLD)),
        Span::styled("   ACC: ", theme.muted()),
        Span::styled(format!("{acc}%"), theme.body().add_modifier(Modifier::BOLD)),
        Span::styled("   DMG: ", theme.muted()),
        Span::styled(format!("{dmg}"), theme.body().add_modifier(Modifier::BOLD)),
    ]);
    let hud_block = Block::default()
        .borders(Borders::BOTTOM)
        .border_style(Style::default().fg(theme.border));
    frame.render_widget(Paragraph::new(hud_line).block(hud_block), layout[0]);

    // Region HP bar
    let r = &state.region;
    let hp_pct = r.hp_pct();
    let hp_gauge = Gauge::default()
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(theme.border))
                .title(Span::styled(
                    format!(" {} · enemy HP {}/{} ", r.name, r.enemy_hp, r.enemy_max_hp),
                    theme.muted(),
                )),
        )
        .gauge_style(Style::default().fg(theme.error).bg(theme.border))
        .ratio(hp_pct.clamp(0.0, 1.0));
    frame.render_widget(hp_gauge, layout[1]);

    // Word grid
    if state.loading {
        let loading = Paragraph::new(Line::from(Span::styled(
            format!("engaging {}…", state.region.name),
            theme.muted(),
        )))
        .block(
            Block::default()
                .borders(Borders::ALL)
                .border_style(Style::default().fg(theme.border)),
        );
        frame.render_widget(loading, layout[2]);
    } else {
        let words = state.sorted_words();
        let matching = state.matching_word();
        let word_grid_cols = Layout::default()
            .direction(Direction::Horizontal)
            .constraints(
                words
                    .iter()
                    .map(|_| Constraint::Ratio(1, words.len().max(1) as u32))
                    .collect::<Vec<_>>(),
            )
            .split(layout[2]);

        for (i, word) in words.iter().enumerate() {
            if i >= word_grid_cols.len() {
                break;
            }
            let is_matching = matching.map(|m| m.id == word.id).unwrap_or(false);
            let now_ms = state.now_ms;
            let expires_ms = word.expires_at_ms;
            let life_left = expires_ms.saturating_sub(now_ms);
            let life_pct = (life_left as f64 / 5000.0).clamp(0.0, 1.0);
            let is_urgent = life_left < 1500;

            let border_style = if is_matching {
                Style::default().fg(theme.accent)
            } else if is_urgent {
                Style::default().fg(theme.error)
            } else {
                Style::default().fg(theme.border)
            };

            let block = Block::default()
                .borders(Borders::ALL)
                .border_style(border_style)
                .title(Span::styled(
                    format!(" d{} · {}dmg ", word.difficulty, word.base_damage),
                    theme.muted(),
                ));

            let word_text_line = if is_matching {
                let typed = state.input.to_lowercase();
                let typed_part = &word.text[..typed.len().min(word.text.len())];
                let rest = &word.text[typed.len().min(word.text.len())..];
                Line::from(vec![
                    Span::styled(
                        typed_part.to_string(),
                        theme.header().add_modifier(Modifier::BOLD),
                    ),
                    Span::styled(rest.to_string(), theme.body()),
                ])
            } else {
                Line::from(Span::styled(word.text.clone(), theme.body()))
            };

            let life_bar_width = word_grid_cols[i].width.saturating_sub(2) as usize;
            let filled = ((life_pct * life_bar_width as f64).round() as usize).min(life_bar_width);
            let life_bar = "─".repeat(filled) + &" ".repeat(life_bar_width - filled);
            let life_style = if is_urgent {
                Style::default().fg(theme.error)
            } else {
                Style::default().fg(theme.success)
            };

            let lines = vec![
                word_text_line,
                Line::from(Span::styled(life_bar, life_style)),
            ];
            let para = Paragraph::new(lines).block(block);
            frame.render_widget(para, word_grid_cols[i]);
        }
    }

    // Input row
    let input_layout = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Length(12), // streak
            Constraint::Min(0),     // input
            Constraint::Length(16), // mult
        ])
        .split(layout[3]);

    let streak_block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.border));
    let streak_para = Paragraph::new(vec![
        Line::from(Span::styled("streak", theme.muted())),
        Line::from(Span::styled(
            streak.to_string(),
            theme.body().add_modifier(Modifier::BOLD),
        )),
    ])
    .block(streak_block);
    frame.render_widget(streak_para, input_layout[0]);

    let shake_indicator = if state.is_shaking() { "!!! " } else { "› " };
    let input_block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.accent))
        .title(Span::styled(
            " type a word · Enter or Space to submit ",
            theme.muted(),
        ));
    let input_display = if state.input.is_empty() {
        Span::styled(format!("{shake_indicator}type…"), theme.muted())
    } else {
        Span::styled(
            format!("{shake_indicator}{}", state.input),
            theme.body().add_modifier(Modifier::BOLD),
        )
    };
    let input_para = Paragraph::new(Line::from(input_display)).block(input_block);
    frame.render_widget(input_para, input_layout[1]);

    let overdrive_style = if state.is_overdrive() {
        Style::default()
            .fg(theme.accent)
            .add_modifier(Modifier::RAPID_BLINK)
    } else {
        theme.muted()
    };
    let mult_block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.border));
    let mult_para = Paragraph::new(vec![
        Line::from(Span::styled("mult", theme.muted())),
        Line::from(Span::styled(
            format!("{:.2}×", mult),
            overdrive_style.add_modifier(Modifier::BOLD),
        )),
    ])
    .block(mult_block);
    frame.render_widget(mult_para, input_layout[2]);

    // Legion HUD footer
    let legion = state.player_legion;
    let legion_line = Line::from(vec![
        Span::styled(
            format!("  {} · {} · ", legion.short(), legion.mechanic()),
            Style::default().fg(legion_color(legion, theme)),
        ),
        Span::styled(legion.description(), theme.muted()),
    ]);
    frame.render_widget(Paragraph::new(legion_line), layout[4]);
}

// ---------------------------------------------------------------------------
// Leaderboard
// ---------------------------------------------------------------------------

pub fn render_leaderboard(frame: &mut Frame, area: Rect, state: &LeaderboardState, theme: &Theme) {
    let layout = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3),  // header
            Constraint::Length(10), // legion standings
            Constraint::Min(0),     // player roster
        ])
        .split(area);

    // Header
    let my_rank = state.my_rank();
    let rank_str = my_rank.map_or("unranked".to_string(), |r| format!("rank #{r}"));
    let header = Paragraph::new(Line::from(vec![
        Span::styled("typewars · leaderboard", theme.header()),
        Span::styled("    ", theme.muted()),
        Span::styled(format!("you: {rank_str}"), theme.muted()),
        Span::styled("    [q] back to map", theme.muted()),
    ]))
    .block(
        Block::default()
            .borders(Borders::BOTTOM)
            .border_style(Style::default().fg(theme.border)),
    );
    frame.render_widget(header, layout[0]);

    // Legion standings
    let mut standings: Vec<(LegionId, u64, usize)> = LegionId::all()
        .iter()
        .map(|&id| {
            let dmg = state.legion_damage(id);
            let regions = state
                .regions
                .iter()
                .filter(|r| r.controlling_legion == id.as_u8() as i8)
                .count();
            (id, dmg, regions)
        })
        .collect();
    standings.sort_by_key(|b| std::cmp::Reverse(b.1));
    let max_dmg = standings.first().map(|s| s.1).unwrap_or(1).max(1);

    let standings_lines: Vec<Line> = standings
        .iter()
        .enumerate()
        .map(|(rank, (id, dmg, regions))| {
            let bar_width = 20usize;
            let filled = ((*dmg as f64 / max_dmg as f64) * bar_width as f64).round() as usize;
            let bar = "█".repeat(filled) + &"░".repeat(bar_width - filled);
            Line::from(vec![
                Span::styled(format!("{} ", rank + 1), theme.muted()),
                Span::styled(
                    format!("{:<4}", id.short()),
                    Style::default().fg(legion_color(*id, theme)),
                ),
                Span::styled(format!("{:<12}  ", id.name()), theme.body()),
                Span::styled(bar, Style::default().fg(legion_color(*id, theme))),
                Span::styled(format!("  {}  {} regions", dmg, regions), theme.muted()),
            ])
        })
        .collect();
    let standings_block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.border))
        .title(Span::styled(
            " legion standings · by total damage ",
            theme.muted(),
        ));
    let standings_para = Paragraph::new(standings_lines).block(standings_block);
    frame.render_widget(standings_para, layout[1]);

    // Player roster
    let sorted = state.sorted_players();
    let items: Vec<ListItem> = sorted
        .iter()
        .enumerate()
        .take(15)
        .map(|(i, p)| {
            let is_sel = i == state.selected;
            let is_me = p.username == state.my_username;
            let legion_id = LegionId::from_u8(p.legion);
            let row_style = if is_sel {
                theme.focused()
            } else {
                theme.body()
            };
            let me_tag = if is_me { " [you]" } else { "" };
            let line = Line::from(vec![
                Span::styled(
                    format!("{:>2}  ", i + 1),
                    if is_sel {
                        theme.focused()
                    } else {
                        theme.muted()
                    },
                ),
                Span::styled(
                    format!("{:<20}", p.username),
                    row_style.add_modifier(Modifier::BOLD),
                ),
                Span::styled(
                    format!("{:<6}", legion_id.short()),
                    Style::default().fg(legion_color(legion_id, theme)),
                ),
                Span::styled(format!("  WPM {:>4}  ", p.best_wpm), theme.muted()),
                Span::styled(format!("DMG {:>10}{me_tag}", p.season_damage), row_style),
            ]);
            ListItem::new(line)
        })
        .collect();
    let roster_block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.border))
        .title(Span::styled(
            format!(
                " player roster · top {} · j/k navigate · Enter view profile ",
                sorted.len().min(15)
            ),
            theme.muted(),
        ));
    let roster = List::new(items).block(roster_block);
    frame.render_widget(roster, layout[2]);
}

// ---------------------------------------------------------------------------
// Profile modal
// ---------------------------------------------------------------------------

pub fn render_profile_modal(frame: &mut Frame, area: Rect, state: &ProfileState, theme: &Theme) {
    let modal_rect = centered_rect(60, 70, area);
    frame.render_widget(Clear, modal_rect);

    let block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.accent))
        .title(Span::styled(
            format!(" {} · profile  [Esc] close ", state.username),
            theme.header(),
        ));

    let body = match &state.player {
        None => vec![Line::from(Span::styled("player not found.", theme.muted()))],
        Some(p) => {
            let legion = LegionId::from_u8(p.legion);
            let regions_held = state.regions_held();
            vec![
                Line::from(vec![
                    Span::styled(
                        p.username.clone(),
                        theme.header().add_modifier(Modifier::BOLD),
                    ),
                    Span::styled(
                        format!("  ·  {} · {}", legion.name(), legion.mechanic()),
                        theme.muted(),
                    ),
                ]),
                Line::from(""),
                Line::from(vec![
                    Span::styled("total damage:   ", theme.muted()),
                    Span::styled(
                        p.total_damage.to_string(),
                        theme.body().add_modifier(Modifier::BOLD),
                    ),
                ]),
                Line::from(vec![
                    Span::styled("season damage:  ", theme.muted()),
                    Span::styled(
                        p.season_damage.to_string(),
                        theme.body().add_modifier(Modifier::BOLD),
                    ),
                ]),
                Line::from(vec![
                    Span::styled("best WPM:       ", theme.muted()),
                    Span::styled(
                        p.best_wpm.to_string(),
                        theme.body().add_modifier(Modifier::BOLD),
                    ),
                ]),
                Line::from(vec![
                    Span::styled("regions held:   ", theme.muted()),
                    Span::styled(
                        regions_held.to_string(),
                        theme.body().add_modifier(Modifier::BOLD),
                    ),
                ]),
                Line::from(""),
                Line::from(Span::styled(
                    format!("legion:  {} ({})", legion.name(), legion.mechanic()),
                    Style::default().fg(legion_color(legion, theme)),
                )),
            ]
        }
    };

    let para = Paragraph::new(body).block(block).wrap(Wrap { trim: true });
    frame.render_widget(para, modal_rect);
}

// ---------------------------------------------------------------------------
// Legion swap modal
// ---------------------------------------------------------------------------

pub fn render_legion_swap_modal(
    frame: &mut Frame,
    area: Rect,
    state: &LegionSwapState,
    theme: &Theme,
) {
    let modal_rect = centered_rect(80, 80, area);
    frame.render_widget(Clear, modal_rect);

    let outer_block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.accent))
        .title(Span::styled(
            " switch legion  [Esc] cancel ",
            theme.header(),
        ));
    frame.render_widget(outer_block.clone(), modal_rect);

    let inner = outer_block.inner(modal_rect);
    let layout = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(2), // header text
            Constraint::Min(0),    // grid
            Constraint::Length(3), // footer
        ])
        .split(inner);

    let header_text = if let Some(err) = &state.error {
        Line::from(Span::styled(err.clone(), Style::default().fg(theme.error)))
    } else {
        Line::from(Span::styled(
            "You can switch legions at any time. Damage history stays with you.",
            theme.muted(),
        ))
    };
    frame.render_widget(Paragraph::new(header_text), layout[0]);

    // Legion grid
    let grid = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage(20),
            Constraint::Percentage(20),
            Constraint::Percentage(20),
            Constraint::Percentage(20),
            Constraint::Percentage(20),
        ])
        .split(layout[1]);

    for (i, id) in LegionId::all().iter().enumerate() {
        let is_picked = state.picked == *id;
        let is_current = state.current_legion == *id;
        let border_style = if is_picked {
            Style::default().fg(theme.accent)
        } else {
            Style::default().fg(theme.border)
        };
        let card_style = if is_picked {
            Style::default().fg(theme.bg).bg(theme.accent)
        } else {
            Style::default().fg(theme.fg)
        };
        let tag = format!("{}{}", if is_current { "✓ " } else { "" }, id.short());
        let block = Block::default()
            .borders(Borders::ALL)
            .border_style(border_style)
            .title(Span::styled(format!(" {tag} "), theme.muted()));
        let body = vec![
            Line::from(Span::styled(
                id.name(),
                card_style.add_modifier(Modifier::BOLD),
            )),
            Line::from(""),
            Line::from(Span::styled(id.mechanic(), theme.muted())),
            if is_current {
                Line::from(Span::styled("[ current ]", theme.muted()))
            } else if is_picked {
                Line::from(Span::styled("[ selected ]", theme.header()))
            } else {
                Line::from("")
            },
        ];
        let para = Paragraph::new(body).block(block).wrap(Wrap { trim: true });
        frame.render_widget(para, grid[i]);
    }

    // Footer
    let can_confirm = state.picked != state.current_legion && !state.loading;
    let footer_line = if state.loading {
        Line::from(Span::styled("switching…", theme.muted()))
    } else {
        Line::from(vec![
            Span::styled("[←/→] select legion   ", theme.muted()),
            if can_confirm {
                Span::styled(
                    "[ Enter ] Confirm switch →",
                    theme.header().add_modifier(Modifier::BOLD),
                )
            } else {
                Span::styled("(same legion selected)", theme.muted())
            },
        ])
    };
    frame.render_widget(Paragraph::new(footer_line), layout[2]);
}

// ---------------------------------------------------------------------------
// Liberated splash
// ---------------------------------------------------------------------------

pub fn render_liberated_splash(
    frame: &mut Frame,
    area: Rect,
    state: &LiberatedSplashState,
    theme: &Theme,
) {
    let layout = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3),
            Constraint::Min(0),
            Constraint::Length(3),
        ])
        .split(area);

    let winner = state.winner;
    let accent = legion_color(winner, theme);
    let tier_label = match state.region.tier {
        1 => "tier 1",
        2 => "tier 2",
        _ => "tier 3",
    };

    // Header
    let header = Paragraph::new(Line::from(vec![Span::styled(
        "✦ REGION LIBERATED ✦",
        Style::default().fg(accent).add_modifier(Modifier::BOLD),
    )]))
    .alignment(Alignment::Center)
    .block(
        Block::default()
            .borders(Borders::BOTTOM)
            .border_style(Style::default().fg(accent)),
    );
    frame.render_widget(header, layout[0]);

    // Body
    let body_layout = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(50), Constraint::Percentage(50)])
        .split(layout[1]);

    // Left: battle stats
    let total_dmg: u64 = state.region.damage.iter().sum();
    let stats_lines = vec![
        Line::from(Span::styled(
            state.region.name.clone(),
            Style::default().fg(accent).add_modifier(Modifier::BOLD),
        )),
        Line::from(""),
        Line::from(vec![
            Span::styled("controlled by  ", theme.muted()),
            Span::styled(
                winner.name(),
                Style::default().fg(accent).add_modifier(Modifier::BOLD),
            ),
        ]),
        Line::from(vec![
            Span::styled("region tier    ", theme.muted()),
            Span::styled(tier_label, Style::default().fg(accent)),
        ]),
        Line::from(vec![
            Span::styled("total damage   ", theme.muted()),
            Span::styled(
                total_dmg.to_string(),
                theme.body().add_modifier(Modifier::BOLD),
            ),
        ]),
    ];
    let stats_block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(accent))
        .title(Span::styled(" battle stats ", theme.muted()));
    frame.render_widget(
        Paragraph::new(stats_lines).block(stats_block),
        body_layout[0],
    );

    // Right: contributions
    let contribs = state.sorted_contributions();
    let contrib_lines: Vec<Line> = contribs
        .iter()
        .enumerate()
        .map(|(rank, (id, dmg))| {
            Line::from(vec![
                Span::styled(format!("{}  ", rank + 1), theme.muted()),
                Span::styled(
                    format!("{:<4}", id.short()),
                    Style::default().fg(legion_color(*id, theme)),
                ),
                Span::styled(format!("{:<12}  ", id.name()), theme.body()),
                Span::styled(dmg.to_string(), theme.muted()),
            ])
        })
        .collect();
    let contrib_block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(theme.border))
        .title(Span::styled(" legion contribution ", theme.muted()));
    frame.render_widget(
        Paragraph::new(contrib_lines).block(contrib_block),
        body_layout[1],
    );

    // Footer
    let footer = Paragraph::new(Line::from(vec![Span::styled(
        format!(
            "  [ Enter ] RETURN TO MAP  ·  The {} has been liberated by {}. {} regen suppressed.",
            state.region.name,
            winner.name(),
            tier_label
        ),
        theme.muted(),
    )]))
    .block(
        Block::default()
            .borders(Borders::TOP)
            .border_style(Style::default().fg(accent)),
    );
    frame.render_widget(footer, layout[2]);
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Pick a distinct terminal color for each legion.
pub fn legion_color(id: LegionId, _theme: &Theme) -> Color {
    match id {
        LegionId::Ashborn => Color::Rgb(255, 120, 60), // orange-red
        LegionId::TheCodex => Color::Rgb(100, 180, 255), // blue
        LegionId::Wardens => Color::Rgb(100, 220, 130), // green
        LegionId::Surge => Color::Rgb(255, 210, 50),   // yellow (same as accent-ish)
        LegionId::Solari => Color::Rgb(200, 140, 255), // purple
    }
}

/// Returns a Rect centered at the given % of the parent.
fn centered_rect(percent_x: u16, percent_y: u16, r: Rect) -> Rect {
    let popup_layout = Layout::default()
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
        .split(popup_layout[1])[1]
}
