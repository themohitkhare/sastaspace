//! Typewars TUI app — multiplayer typing-game with a contested global warmap.
//!
//! Implements the `App` trait from `sastaspace-core`. The shell hydrates
//! player/region/word data by calling the `set_*` methods after STDB events.

pub mod state;
mod view;

/// Re-export commonly-used state types at crate root for ergonomics.
pub use state::{BattleSessionRow, LegionId, PlayerRow, RegionRow, TypewarsState, WordRow};
/// Re-export for tests that need `LiberatedSplashState`, `Screen`, etc.
pub mod state_pub {
    pub use crate::state::{LiberatedSplashState, Screen};
}

use crossterm::event::{KeyCode, KeyEvent};
use ratatui::{layout::Rect, Frame};
use sastaspace_core::{
    event::{Action, InputAction},
    theme::Theme,
    App, AppResult,
};
use state::Screen;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

/// The top-level typewars app struct. Hand to the shell router.
pub struct TypewarsApp {
    pub state: TypewarsState,
    theme: Theme,
    /// Pending reducer calls — communicated back to the shell via `AppResult`.
    /// We don't call STDB directly; instead we return a `SwitchTo` or
    /// embed commands in the event stream. For now reducer calls are handled
    /// by the shell reading `TypewarsApp` via `as_any_mut` downcasting.
    pub pending_reducer: Option<ReducerCall>,
}

/// A queued reducer call that the shell should dispatch to STDB.
#[derive(Debug, Clone)]
pub enum ReducerCall {
    RegisterPlayer { username: String, legion: u8 },
    StartBattle { region_id: u32 },
    EndBattle { session_id: u64 },
    SubmitWord { session_id: u64, word: String },
    SwapLegion { new_legion: u8 },
}

impl TypewarsApp {
    pub fn new() -> Self {
        Self {
            state: TypewarsState::default(),
            theme: Theme::default_dark(),
            pending_reducer: None,
        }
    }

    // -----------------------------------------------------------------------
    // Data hydration — called by the shell from `Action::Stdb(Updated("..."))`.
    // -----------------------------------------------------------------------

    pub fn set_player(&mut self, player: PlayerRow) {
        self.state.set_player(player);
    }

    pub fn set_regions(&mut self, regions: Vec<RegionRow>) {
        self.state.set_regions(regions);
    }

    pub fn set_players(&mut self, players: Vec<PlayerRow>) {
        self.state.set_players(players);
    }

    pub fn set_battle_session(&mut self, session: BattleSessionRow) {
        self.state.set_battle_session(session);
    }

    pub fn set_words(&mut self, words: Vec<WordRow>) {
        self.state.set_words(words);
    }

    pub fn take_pending_reducer(&mut self) -> Option<ReducerCall> {
        self.pending_reducer.take()
    }

    // -----------------------------------------------------------------------
    // Key handling helpers
    // -----------------------------------------------------------------------

    fn handle_key(&mut self, key: KeyEvent) -> AppResult {
        // Global: Escape goes "back" in most contexts.
        if key.code == KeyCode::Esc {
            // If the callsign input is focused on the LegionSelect screen,
            // Esc should defocus it (not navigate away from the screen).
            if self.state.screen == Screen::LegionSelect && self.state.legion_select.focus_input {
                self.state.legion_select.focus_input = false;
                return AppResult::Continue;
            }
            return self.handle_escape();
        }

        match &self.state.screen {
            Screen::LegionSelect => self.handle_legion_select_key(key),
            Screen::WarMap => self.handle_war_map_key(key),
            Screen::Battle => self.handle_battle_key(key),
            Screen::Leaderboard => self.handle_leaderboard_key(key),
            Screen::Profile => self.handle_profile_key(key),
            Screen::LegionSwap => self.handle_legion_swap_key(key),
            Screen::LiberatedSplash => self.handle_liberated_splash_key(key),
        }
    }

    fn handle_escape(&mut self) -> AppResult {
        match self.state.screen {
            Screen::LegionSelect => AppResult::Continue,
            Screen::WarMap => AppResult::Continue, // top-level; quit handled globally
            Screen::Battle => {
                // End battle on server, go back to map.
                if let Some(battle) = &self.state.battle {
                    if let Some(session) = &battle.session {
                        self.pending_reducer = Some(ReducerCall::EndBattle {
                            session_id: session.id,
                        });
                    }
                }
                self.state.exit_battle();
                AppResult::Continue
            }
            Screen::Leaderboard => {
                self.state.screen = Screen::WarMap;
                AppResult::Continue
            }
            Screen::Profile => {
                self.state.close_profile();
                AppResult::Continue
            }
            Screen::LegionSwap => {
                self.state.close_legion_swap();
                AppResult::Continue
            }
            Screen::LiberatedSplash => {
                self.state.liberated_splash = None;
                self.state.screen = Screen::WarMap;
                AppResult::Continue
            }
        }
    }

    fn handle_legion_select_key(&mut self, key: KeyEvent) -> AppResult {
        let sel = &mut self.state.legion_select;

        if sel.focus_input {
            match key.code {
                KeyCode::Char(c) if sel.callsign.len() < 24 => {
                    sel.callsign.push(c);
                }
                KeyCode::Char(_) => {} // callsign at max length, ignore
                KeyCode::Backspace => {
                    sel.callsign.pop();
                }
                KeyCode::Enter if sel.can_submit() => {
                    sel.submitting = true;
                    self.pending_reducer = Some(ReducerCall::RegisterPlayer {
                        username: sel.callsign.trim().to_string(),
                        legion: sel.cursor as u8,
                    });
                }
                KeyCode::Enter => {} // can't submit yet, ignore
                KeyCode::Esc | KeyCode::Tab => {
                    sel.focus_input = false;
                }
                _ => {}
            }
        } else {
            match key.code {
                KeyCode::Left | KeyCode::Char('h') => sel.move_cursor(-1),
                KeyCode::Right | KeyCode::Char('l') => sel.move_cursor(1),
                KeyCode::Tab | KeyCode::Char('i') => {
                    sel.focus_input = true;
                }
                KeyCode::Enter => {
                    if sel.can_submit() {
                        sel.submitting = true;
                        self.pending_reducer = Some(ReducerCall::RegisterPlayer {
                            username: sel.callsign.trim().to_string(),
                            legion: sel.cursor as u8,
                        });
                    } else if !sel.focus_input {
                        sel.focus_input = true;
                    }
                }
                _ => {}
            }
        }
        AppResult::Continue
    }

    fn handle_war_map_key(&mut self, key: KeyEvent) -> AppResult {
        match key.code {
            KeyCode::Char('j') | KeyCode::Down => self.state.war_map.move_selection(1),
            KeyCode::Char('k') | KeyCode::Up => self.state.war_map.move_selection(-1),
            KeyCode::Enter => {
                if let Some(r) = self.state.war_map.selected_region().cloned() {
                    // Start battle: queue reducer call, enter battle screen.
                    self.pending_reducer = Some(ReducerCall::StartBattle { region_id: r.id });
                    self.state.enter_battle(r);
                }
            }
            KeyCode::Char('L') | KeyCode::Char('b') => {
                self.state.open_leaderboard();
            }
            KeyCode::Char('s') => {
                self.state.open_legion_swap();
            }
            _ => {}
        }
        AppResult::Continue
    }

    fn handle_battle_key(&mut self, key: KeyEvent) -> AppResult {
        if let Some(battle) = &mut self.state.battle {
            match key.code {
                KeyCode::Enter => {
                    // Submit word on Enter
                    let typed = battle.input.trim().to_lowercase().to_string();
                    if !typed.is_empty() {
                        if let Some(session) = &battle.session {
                            self.pending_reducer = Some(ReducerCall::SubmitWord {
                                session_id: session.id,
                                word: typed,
                            });
                        }
                        battle.input.clear();
                    }
                }
                KeyCode::Char(' ') => {
                    // Submit word on Space
                    let typed = battle.input.trim().to_lowercase().to_string();
                    if !typed.is_empty() {
                        if let Some(session) = &battle.session {
                            self.pending_reducer = Some(ReducerCall::SubmitWord {
                                session_id: session.id,
                                word: typed,
                            });
                        }
                        battle.input.clear();
                    } else {
                        battle.input.push(' ');
                    }
                }
                KeyCode::Char(c) => {
                    battle.input.push(c);
                }
                KeyCode::Backspace => {
                    battle.input.pop();
                }
                _ => {}
            }
        }
        AppResult::Continue
    }

    fn handle_leaderboard_key(&mut self, key: KeyEvent) -> AppResult {
        match key.code {
            KeyCode::Char('j') | KeyCode::Down => self.state.leaderboard.move_selection(1),
            KeyCode::Char('k') | KeyCode::Up => self.state.leaderboard.move_selection(-1),
            KeyCode::Enter => {
                let sorted = self.state.leaderboard.sorted_players();
                if let Some(p) = sorted.get(self.state.leaderboard.selected).cloned() {
                    let username = p.username.clone();
                    self.state.open_profile(username);
                }
            }
            KeyCode::Char('q') | KeyCode::Backspace => {
                self.state.screen = Screen::WarMap;
            }
            _ => {}
        }
        AppResult::Continue
    }

    fn handle_profile_key(&mut self, key: KeyEvent) -> AppResult {
        if let KeyCode::Char('q') = key.code {
            self.state.close_profile();
        }
        AppResult::Continue
    }

    fn handle_legion_swap_key(&mut self, key: KeyEvent) -> AppResult {
        if let Some(swap) = &mut self.state.legion_swap {
            match key.code {
                KeyCode::Left | KeyCode::Char('h') => swap.move_cursor(-1),
                KeyCode::Right | KeyCode::Char('l') => swap.move_cursor(1),
                KeyCode::Enter => {
                    let new_legion = swap.picked;
                    if new_legion != swap.current_legion {
                        swap.loading = true;
                        self.pending_reducer = Some(ReducerCall::SwapLegion {
                            new_legion: new_legion.as_u8(),
                        });
                    }
                }
                _ => {}
            }
        }
        AppResult::Continue
    }

    fn handle_liberated_splash_key(&mut self, key: KeyEvent) -> AppResult {
        match key.code {
            KeyCode::Enter | KeyCode::Char('q') | KeyCode::Char(' ') => {
                self.state.liberated_splash = None;
                self.state.screen = Screen::WarMap;
            }
            _ => {}
        }
        AppResult::Continue
    }
}

impl Default for TypewarsApp {
    fn default() -> Self {
        Self::new()
    }
}

impl App for TypewarsApp {
    fn id(&self) -> &'static str {
        "typewars"
    }

    fn title(&self) -> &str {
        "typewars · contested worlds"
    }

    fn render(&mut self, frame: &mut Frame, area: Rect) {
        view::render(frame, area, &self.state, &self.theme);
    }

    fn handle(&mut self, action: Action) -> AppResult {
        if let Action::Input(InputAction::Key(key)) = action {
            return self.handle_key(key);
        }
        AppResult::Continue
    }

    fn tick(&mut self, _dt: Duration) -> AppResult {
        // Update now_ms in battle state for WPM / word expiry display.
        if let Some(battle) = &mut self.state.battle {
            battle.now_ms = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map(|d| d.as_millis() as u64)
                .unwrap_or(0);
        }
        // Advance liberated splash tick counter.
        if let Some(splash) = &mut self.state.liberated_splash {
            splash.ticks = splash.ticks.saturating_add(1);
        }
        AppResult::Continue
    }

    fn as_any_mut(&mut self) -> &mut dyn std::any::Any {
        self
    }
}
