//! Pure in-memory state for all typewars screens.
//! Shell feeds data in via `TypewarsApp::set_*` methods whenever STDB events arrive.

use std::cmp::Reverse;
use std::time::Instant;

// ---------------------------------------------------------------------------
// Legion metadata (mirrors LEGION_INFO from the web app)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LegionId {
    Ashborn = 0,
    TheCodex = 1,
    Wardens = 2,
    Surge = 3,
    Solari = 4,
}

impl LegionId {
    pub fn from_u8(v: u8) -> Self {
        match v {
            0 => Self::Ashborn,
            1 => Self::TheCodex,
            2 => Self::Wardens,
            3 => Self::Surge,
            4 => Self::Solari,
            _ => Self::Ashborn,
        }
    }

    pub fn as_u8(self) -> u8 {
        self as u8
    }

    pub fn name(self) -> &'static str {
        match self {
            Self::Ashborn => "Ashborn",
            Self::TheCodex => "The Codex",
            Self::Wardens => "Wardens",
            Self::Surge => "Surge",
            Self::Solari => "Solari",
        }
    }

    pub fn short(self) -> &'static str {
        match self {
            Self::Ashborn => "ASH",
            Self::TheCodex => "COD",
            Self::Wardens => "WAR",
            Self::Surge => "SRG",
            Self::Solari => "SOL",
        }
    }

    pub fn mechanic(self) -> &'static str {
        match self {
            Self::Ashborn => "streak bonus",
            Self::TheCodex => "accuracy multiplier",
            Self::Wardens => "regen suppression",
            Self::Surge => "overdrive",
            Self::Solari => "difficulty insight",
        }
    }

    pub fn description(self) -> &'static str {
        match self {
            Self::Ashborn => {
                "10-hit streaks trigger an ash nova. Break your streak and lose it all."
            }
            Self::TheCodex => "Perfect accuracy pushes your multiplier beyond the normal cap.",
            Self::Wardens => "Your damage suppresses region regen at a higher rate.",
            Self::Surge => "Hitting 3× mult enters Overdrive — cap raises to 5×.",
            Self::Solari => "Word difficulty is always visible to you.",
        }
    }

    pub fn all() -> [LegionId; 5] {
        [
            LegionId::Ashborn,
            LegionId::TheCodex,
            LegionId::Wardens,
            LegionId::Surge,
            LegionId::Solari,
        ]
    }
}

// ---------------------------------------------------------------------------
// Shared row types (shell maps stdb bindings to these)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq)]
pub struct PlayerRow {
    pub username: String,
    pub legion: u8,
    pub total_damage: u64,
    pub season_damage: u64,
    pub best_wpm: u32,
}

#[derive(Debug, Clone, PartialEq)]
pub struct RegionRow {
    pub id: u32,
    pub name: String,
    pub tier: u8,
    pub controlling_legion: i8,
    pub enemy_hp: u64,
    pub enemy_max_hp: u64,
    pub regen_rate: u64,
    pub damage: [u64; 5],
    pub active_wardens: u32,
}

impl RegionRow {
    pub fn hp_pct(&self) -> f64 {
        if self.enemy_max_hp == 0 {
            0.0
        } else {
            self.enemy_hp as f64 / self.enemy_max_hp as f64
        }
    }

    pub fn is_liberated(&self) -> bool {
        self.controlling_legion >= 0
    }

    pub fn status(&self) -> RegionStatus {
        if self.controlling_legion >= 0 {
            RegionStatus::Liberated(LegionId::from_u8(self.controlling_legion as u8))
        } else if self.enemy_hp < self.enemy_max_hp {
            RegionStatus::Contested
        } else {
            RegionStatus::Pristine
        }
    }

    pub fn total_damage(&self) -> u64 {
        self.damage.iter().sum()
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RegionStatus {
    Liberated(LegionId),
    Contested,
    Pristine,
}

#[derive(Debug, Clone, PartialEq)]
pub struct WordRow {
    pub id: u64,
    pub session_id: u64,
    pub text: String,
    pub difficulty: u8,
    pub base_damage: u64,
    pub expires_at_ms: u64,
}

#[derive(Debug, Clone, PartialEq)]
pub struct BattleSessionRow {
    pub id: u64,
    pub region_id: u32,
    pub started_at_ms: u64,
    pub streak: u32,
    pub multiplier: f32,
    pub accuracy_hits: u32,
    pub accuracy_misses: u32,
    pub damage_dealt: u64,
    pub active: bool,
}

// ---------------------------------------------------------------------------
// Screen enum
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Screen {
    /// First screen: no player row exists yet.
    LegionSelect,
    /// Main map + region list.
    WarMap,
    /// Battle typing screen.
    Battle,
    /// Leaderboard table.
    Leaderboard,
    /// Profile popover.
    Profile,
    /// Legion swap popover.
    LegionSwap,
    /// Liberated celebration.
    LiberatedSplash,
}

// ---------------------------------------------------------------------------
// LegionSelectState
// ---------------------------------------------------------------------------

#[derive(Debug, Default)]
pub struct LegionSelectState {
    /// Which of the 5 columns is highlighted.
    pub cursor: usize,
    /// Callsign being typed (max 24 chars).
    pub callsign: String,
    /// Whether the cursor is in the callsign input (vs the grid).
    pub focus_input: bool,
    /// Submission error message.
    pub error: Option<String>,
    /// Submission is in flight.
    pub submitting: bool,
}

impl LegionSelectState {
    pub fn selected_legion(&self) -> LegionId {
        LegionId::from_u8(self.cursor as u8)
    }

    pub fn can_submit(&self) -> bool {
        !self.callsign.trim().is_empty() && !self.submitting
    }

    pub fn move_cursor(&mut self, delta: isize) {
        let n = 5isize;
        self.cursor = ((self.cursor as isize + delta).rem_euclid(n)) as usize;
    }
}

// ---------------------------------------------------------------------------
// WarMapState
// ---------------------------------------------------------------------------

#[derive(Debug, Default)]
pub struct WarMapState {
    pub regions: Vec<RegionRow>,
    /// Index into `regions` (the list).
    pub selected: usize,
    /// Whether the RegionDetail panel is open.
    pub detail_open: bool,
}

impl WarMapState {
    pub fn set_regions(&mut self, mut regions: Vec<RegionRow>) {
        regions.sort_by_key(|r| r.id);
        self.regions = regions;
        if self.selected >= self.regions.len() {
            self.selected = self.regions.len().saturating_sub(1);
        }
    }

    pub fn selected_region(&self) -> Option<&RegionRow> {
        self.regions.get(self.selected)
    }

    pub fn move_selection(&mut self, delta: isize) {
        if self.regions.is_empty() {
            return;
        }
        let n = self.regions.len() as isize;
        self.selected = ((self.selected as isize + delta).rem_euclid(n)) as usize;
    }

    pub fn liberated_count(&self) -> usize {
        self.regions.iter().filter(|r| r.is_liberated()).count()
    }

    pub fn contested_count(&self) -> usize {
        self.regions
            .iter()
            .filter(|r| !r.is_liberated() && r.enemy_hp < r.enemy_max_hp)
            .count()
    }

    pub fn pristine_count(&self) -> usize {
        self.regions
            .iter()
            .filter(|r| !r.is_liberated() && r.enemy_hp == r.enemy_max_hp)
            .count()
    }

    /// Per-legion region count.
    pub fn legion_region_count(&self, id: LegionId) -> usize {
        self.regions
            .iter()
            .filter(|r| r.controlling_legion == id.as_u8() as i8)
            .count()
    }
}

// ---------------------------------------------------------------------------
// BattleState
// ---------------------------------------------------------------------------

#[derive(Debug)]
pub struct BattleState {
    pub region: RegionRow,
    pub player_legion: LegionId,
    pub session: Option<BattleSessionRow>,
    pub words: Vec<WordRow>,
    /// Current typed input buffer.
    pub input: String,
    /// Timestamp of the render tick (for WPM/expiry calcs).
    pub now_ms: u64,
    /// Visual flash: shake on streak break.
    pub shake_until: Option<Instant>,
    /// Awaiting session start.
    pub loading: bool,
}

impl BattleState {
    pub fn new(region: RegionRow, player_legion: LegionId) -> Self {
        Self {
            region,
            player_legion,
            session: None,
            words: Vec::new(),
            input: String::new(),
            now_ms: 0,
            shake_until: None,
            loading: true,
        }
    }

    pub fn wpm(&self) -> u32 {
        let session = match &self.session {
            Some(s) => s,
            None => return 0,
        };
        let start_ms = session.started_at_ms;
        if start_ms == 0 || self.now_ms <= start_ms {
            return 0;
        }
        let elapsed_min = (self.now_ms - start_ms) as f64 / 60_000.0;
        if elapsed_min <= 0.0 {
            return 0;
        }
        (session.accuracy_hits as f64 / elapsed_min).round() as u32
    }

    pub fn accuracy(&self) -> u32 {
        let session = match &self.session {
            Some(s) => s,
            None => return 100,
        };
        let total = session.accuracy_hits + session.accuracy_misses;
        if total == 0 {
            100
        } else {
            ((session.accuracy_hits as f64 / total as f64) * 100.0).round() as u32
        }
    }

    pub fn sorted_words(&self) -> Vec<&WordRow> {
        let mut ws: Vec<&WordRow> = self.words.iter().collect();
        ws.sort_by_key(|w| w.id);
        ws.truncate(8);
        ws
    }

    /// Returns the word in the display set whose text starts with the current input.
    pub fn matching_word(&self) -> Option<&WordRow> {
        if self.input.is_empty() {
            return None;
        }
        let lower = self.input.to_lowercase();
        self.sorted_words()
            .into_iter()
            .find(|w| w.text.starts_with(&lower[..]))
    }

    pub fn is_shaking(&self) -> bool {
        self.shake_until
            .map(|t| t > Instant::now())
            .unwrap_or(false)
    }

    pub fn is_overdrive(&self) -> bool {
        self.player_legion == LegionId::Surge
            && self
                .session
                .as_ref()
                .map(|s| s.multiplier >= 3.0)
                .unwrap_or(false)
    }
}

// ---------------------------------------------------------------------------
// LeaderboardState
// ---------------------------------------------------------------------------

#[derive(Debug, Default)]
pub struct LeaderboardState {
    pub players: Vec<PlayerRow>,
    pub regions: Vec<RegionRow>,
    pub my_username: String,
    pub selected: usize,
}

impl LeaderboardState {
    pub fn sorted_players(&self) -> Vec<&PlayerRow> {
        let mut ps: Vec<&PlayerRow> = self.players.iter().collect();
        ps.sort_by_key(|b| std::cmp::Reverse(b.season_damage));
        ps
    }

    pub fn my_rank(&self) -> Option<usize> {
        self.sorted_players()
            .iter()
            .position(|p| p.username == self.my_username)
            .map(|i| i + 1)
    }

    pub fn legion_damage(&self, id: LegionId) -> u64 {
        self.regions
            .iter()
            .map(|r| r.damage[id.as_u8() as usize])
            .sum()
    }

    pub fn move_selection(&mut self, delta: isize) {
        let n = self.players.len();
        if n == 0 {
            return;
        }
        self.selected = ((self.selected as isize + delta).rem_euclid(n as isize)) as usize;
    }
}

// ---------------------------------------------------------------------------
// ProfileState
// ---------------------------------------------------------------------------

#[derive(Debug, Default)]
pub struct ProfileState {
    pub username: String,
    pub player: Option<PlayerRow>,
    pub regions: Vec<RegionRow>,
}

impl ProfileState {
    pub fn regions_held(&self) -> usize {
        match &self.player {
            None => 0,
            Some(p) => self
                .regions
                .iter()
                .filter(|r| r.controlling_legion == p.legion as i8)
                .count(),
        }
    }
}

// ---------------------------------------------------------------------------
// LegionSwapState
// ---------------------------------------------------------------------------

#[derive(Debug)]
pub struct LegionSwapState {
    pub current_legion: LegionId,
    pub picked: LegionId,
    pub loading: bool,
    pub error: Option<String>,
}

impl LegionSwapState {
    pub fn new(current: LegionId) -> Self {
        Self {
            current_legion: current,
            picked: current,
            loading: false,
            error: None,
        }
    }

    pub fn move_cursor(&mut self, delta: isize) {
        let n = 5isize;
        let cur = self.picked.as_u8() as isize;
        let next = ((cur + delta).rem_euclid(n)) as u8;
        self.picked = LegionId::from_u8(next);
    }
}

// ---------------------------------------------------------------------------
// LiberatedSplashState
// ---------------------------------------------------------------------------

#[derive(Debug)]
pub struct LiberatedSplashState {
    pub region: RegionRow,
    pub winner: LegionId,
    /// Ticks since the splash appeared (for animation).
    pub ticks: u64,
}

impl LiberatedSplashState {
    pub fn new(region: RegionRow, winner: LegionId) -> Self {
        Self {
            region,
            winner,
            ticks: 0,
        }
    }

    pub fn sorted_contributions(&self) -> Vec<(LegionId, u64)> {
        let mut cs: Vec<(LegionId, u64)> = LegionId::all()
            .iter()
            .map(|&id| (id, self.region.damage[id.as_u8() as usize]))
            .collect();
        cs.sort_by_key(|b| Reverse(b.1));
        cs
    }
}

// ---------------------------------------------------------------------------
// Top-level TypewarsState
// ---------------------------------------------------------------------------

#[derive(Debug)]
pub struct TypewarsState {
    pub screen: Screen,
    pub player: Option<PlayerRow>,
    pub regions: Vec<RegionRow>,
    // Screen-specific sub-states
    pub legion_select: LegionSelectState,
    pub war_map: WarMapState,
    pub battle: Option<BattleState>,
    pub leaderboard: LeaderboardState,
    pub profile: Option<ProfileState>,
    pub legion_swap: Option<LegionSwapState>,
    pub liberated_splash: Option<LiberatedSplashState>,
}

impl Default for TypewarsState {
    fn default() -> Self {
        Self {
            screen: Screen::LegionSelect,
            player: None,
            regions: Vec::new(),
            legion_select: LegionSelectState::default(),
            war_map: WarMapState::default(),
            battle: None,
            leaderboard: LeaderboardState::default(),
            profile: None,
            legion_swap: None,
            liberated_splash: None,
        }
    }
}

impl TypewarsState {
    /// Called when the player row is updated (or initially received from STDB).
    /// Switches away from LegionSelect if a player now exists.
    pub fn set_player(&mut self, player: PlayerRow) {
        self.player = Some(player.clone());
        if self.screen == Screen::LegionSelect {
            self.screen = Screen::WarMap;
        }
        // Keep leaderboard my_username in sync
        self.leaderboard.my_username = player.username.clone();
    }

    pub fn set_regions(&mut self, regions: Vec<RegionRow>) {
        self.regions = regions.clone();
        self.war_map.set_regions(regions.clone());
        self.leaderboard.regions = regions.clone();
        if let Some(battle) = &mut self.battle {
            // Update the live region data in the battle
            if let Some(r) = regions.iter().find(|r| r.id == battle.region.id) {
                battle.region = r.clone();
            }
        }
        // Check for newly-liberated region while in battle
        if self.screen == Screen::Battle {
            if let Some(battle) = &self.battle {
                if let Some(r) = self.regions.iter().find(|r| r.id == battle.region.id) {
                    if r.is_liberated() {
                        let winner = LegionId::from_u8(r.controlling_legion as u8);
                        let splash = LiberatedSplashState::new(r.clone(), winner);
                        self.liberated_splash = Some(splash);
                        self.screen = Screen::LiberatedSplash;
                    }
                }
            }
        }
    }

    pub fn set_players(&mut self, players: Vec<PlayerRow>) {
        self.leaderboard.players = players;
    }

    pub fn set_battle_session(&mut self, session: BattleSessionRow) {
        if let Some(battle) = &mut self.battle {
            if session.active {
                battle.session = Some(session);
                battle.loading = false;
            } else {
                // Session ended
                battle.session = None;
            }
        }
    }

    pub fn set_words(&mut self, words: Vec<WordRow>) {
        if let Some(battle) = &mut self.battle {
            battle.words = words;
        }
    }

    pub fn enter_war_map(&mut self) {
        self.screen = Screen::WarMap;
        self.battle = None;
    }

    pub fn enter_battle(&mut self, region: RegionRow) {
        let legion = self
            .player
            .as_ref()
            .map(|p| LegionId::from_u8(p.legion))
            .unwrap_or(LegionId::Ashborn);
        self.battle = Some(BattleState::new(region, legion));
        self.screen = Screen::Battle;
    }

    pub fn exit_battle(&mut self) {
        self.battle = None;
        self.screen = Screen::WarMap;
    }

    pub fn open_leaderboard(&mut self) {
        self.screen = Screen::Leaderboard;
    }

    pub fn open_profile(&mut self, username: String) {
        let player = self
            .leaderboard
            .players
            .iter()
            .find(|p| p.username == username)
            .cloned();
        self.profile = Some(ProfileState {
            username: username.clone(),
            player,
            regions: self.regions.clone(),
        });
        self.screen = Screen::Profile;
    }

    pub fn close_profile(&mut self) {
        self.profile = None;
        self.screen = Screen::Leaderboard;
    }

    pub fn open_legion_swap(&mut self) {
        let legion = self
            .player
            .as_ref()
            .map(|p| LegionId::from_u8(p.legion))
            .unwrap_or(LegionId::Ashborn);
        self.legion_swap = Some(LegionSwapState::new(legion));
        self.screen = Screen::LegionSwap;
    }

    pub fn close_legion_swap(&mut self) {
        self.legion_swap = None;
        self.screen = Screen::WarMap;
    }
}

// ---------------------------------------------------------------------------
// Unit tests for pure state logic
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn make_region(id: u32, hp: u64, max_hp: u64, legion: i8) -> RegionRow {
        RegionRow {
            id,
            name: format!("Region {id}"),
            tier: 1,
            controlling_legion: legion,
            enemy_hp: hp,
            enemy_max_hp: max_hp,
            regen_rate: 10,
            damage: [100, 200, 50, 0, 0],
            active_wardens: 3,
        }
    }

    #[test]
    fn region_status_pristine() {
        let r = make_region(0, 1000, 1000, -1);
        assert_eq!(r.status(), RegionStatus::Pristine);
    }

    #[test]
    fn region_status_contested() {
        let r = make_region(0, 900, 1000, -1);
        assert_eq!(r.status(), RegionStatus::Contested);
    }

    #[test]
    fn region_status_liberated() {
        let r = make_region(0, 0, 1000, 2);
        assert_eq!(r.status(), RegionStatus::Liberated(LegionId::Wardens));
    }

    #[test]
    fn war_map_counts() {
        let mut state = WarMapState::default();
        state.set_regions(vec![
            make_region(0, 1000, 1000, -1), // pristine
            make_region(1, 900, 1000, -1),  // contested
            make_region(2, 0, 1000, 1),     // liberated by Codex
        ]);
        assert_eq!(state.liberated_count(), 1);
        assert_eq!(state.contested_count(), 1);
        assert_eq!(state.pristine_count(), 1);
    }

    #[test]
    fn war_map_selection_wraps() {
        let mut state = WarMapState::default();
        state.set_regions(vec![
            make_region(0, 1000, 1000, -1),
            make_region(1, 1000, 1000, -1),
        ]);
        state.selected = 0;
        state.move_selection(-1);
        assert_eq!(state.selected, 1); // wraps to end
    }

    #[test]
    fn legion_select_cursor_wraps() {
        let mut s = LegionSelectState::default(); // cursor starts at 0
        s.move_cursor(-1);
        assert_eq!(s.cursor, 4);
        s.move_cursor(1);
        assert_eq!(s.cursor, 0);
    }

    #[test]
    fn battle_wpm_zero_before_session() {
        let region = make_region(0, 1000, 1000, -1);
        let state = BattleState::new(region, LegionId::Surge);
        assert_eq!(state.wpm(), 0);
    }

    #[test]
    fn battle_accuracy_100_when_no_words() {
        let region = make_region(0, 1000, 1000, -1);
        let state = BattleState::new(region, LegionId::Ashborn);
        assert_eq!(state.accuracy(), 100);
    }

    #[test]
    fn set_player_transitions_to_warmap() {
        let mut state = TypewarsState::default();
        assert_eq!(state.screen, Screen::LegionSelect);
        state.set_player(PlayerRow {
            username: "testuser".into(),
            legion: 0,
            total_damage: 0,
            season_damage: 0,
            best_wpm: 0,
        });
        assert_eq!(state.screen, Screen::WarMap);
    }

    #[test]
    fn leaderboard_sorted_by_season_damage() {
        let state = LeaderboardState {
            players: vec![
                PlayerRow {
                    username: "b".into(),
                    legion: 0,
                    total_damage: 0,
                    season_damage: 100,
                    best_wpm: 0,
                },
                PlayerRow {
                    username: "a".into(),
                    legion: 1,
                    total_damage: 0,
                    season_damage: 200,
                    best_wpm: 0,
                },
            ],
            ..Default::default()
        };
        let sorted = state.sorted_players();
        assert_eq!(sorted[0].username, "a");
        assert_eq!(sorted[1].username, "b");
    }

    #[test]
    fn hp_pct_calculation() {
        let r = make_region(0, 750, 1000, -1);
        assert!((r.hp_pct() - 0.75).abs() < 1e-9);
    }

    #[test]
    fn legion_swap_state_wraps() {
        // Wardens = 2, +2 = 4 = Solari
        let mut s = LegionSwapState::new(LegionId::Wardens);
        s.move_cursor(2);
        assert_eq!(s.picked, LegionId::Solari);
        // Solari = 4, +1 = 5 % 5 = 0 = Ashborn
        s.move_cursor(1);
        assert_eq!(s.picked, LegionId::Ashborn);
    }
}
