//! Snapshot tests for all typewars TUI screens.
//! Run with `cargo test -p app-typewars` to generate .snap files on first run,
//! then `cargo insta review` (or INSTA_UPDATE=always) to accept.

use app_typewars::{
    state::{LiberatedSplashState, Screen},
    BattleSessionRow, LegionId, PlayerRow, RegionRow, TypewarsApp, WordRow,
};
use ratatui::{backend::TestBackend, layout::Rect, Terminal};
use sastaspace_core::App;

// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------

fn render_to_string(app: &mut TypewarsApp, w: u16, h: u16) -> String {
    let backend = TestBackend::new(w, h);
    let mut terminal = Terminal::new(backend).unwrap();
    terminal
        .draw(|f| app.render(f, Rect::new(0, 0, w, h)))
        .unwrap();
    let buffer = terminal.backend().buffer().clone();
    let mut out = String::new();
    for y in 0..buffer.area().height {
        for x in 0..buffer.area().width {
            out.push_str(buffer.cell((x, y)).unwrap().symbol());
        }
        out.push('\n');
    }
    out
}

fn make_player(username: &str, legion: u8) -> PlayerRow {
    PlayerRow {
        username: username.to_string(),
        legion,
        total_damage: 12_345,
        season_damage: 5_678,
        best_wpm: 87,
    }
}

fn make_region(id: u32, name: &str, hp: u64, max_hp: u64, legion: i8) -> RegionRow {
    RegionRow {
        id,
        name: name.to_string(),
        tier: if id < 10 {
            1
        } else if id < 20 {
            2
        } else {
            3
        },
        controlling_legion: legion,
        enemy_hp: hp,
        enemy_max_hp: max_hp,
        regen_rate: 10,
        damage: [1000, 2000, 500, 300, 200],
        active_wardens: 4,
    }
}

fn fixture_regions() -> Vec<RegionRow> {
    vec![
        make_region(0, "Arkanis Prime", 3000, 5000, -1),
        make_region(1, "Zethara Station", 5000, 5000, 1),
        make_region(2, "Ironveil Gate", 1500, 5000, -1),
        make_region(3, "The Hollow Ring", 5000, 5000, -1),
        make_region(4, "Solaris Reach", 0, 5000, 4),
    ]
}

fn fixture_players() -> Vec<PlayerRow> {
    vec![
        make_player("alpha", 0),
        make_player("beta", 1),
        make_player("gamma", 2),
    ]
}

// ---------------------------------------------------------------------------
// 1. LegionSelect — fresh app (no player yet)
// ---------------------------------------------------------------------------

#[test]
fn snapshot_legion_select_empty() {
    let mut app = TypewarsApp::new();
    let s = render_to_string(&mut app, 120, 30);
    insta::assert_snapshot!("legion_select_empty", s);
}

#[test]
fn snapshot_legion_select_cursor_moved() {
    use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};
    use sastaspace_core::event::{Action, InputAction};
    let mut app = TypewarsApp::new();
    // Move cursor right twice → The Codex (index 1) then Wardens (index 2)
    for _ in 0..2 {
        app.handle(Action::Input(InputAction::Key(KeyEvent::new(
            KeyCode::Right,
            KeyModifiers::empty(),
        ))));
    }
    let s = render_to_string(&mut app, 120, 30);
    insta::assert_snapshot!("legion_select_cursor_wardens", s);
}

// ---------------------------------------------------------------------------
// 2. WarMap
// ---------------------------------------------------------------------------

#[test]
fn snapshot_war_map() {
    let mut app = TypewarsApp::new();
    app.set_player(make_player("commander", 2));
    app.set_regions(fixture_regions());
    let s = render_to_string(&mut app, 120, 30);
    insta::assert_snapshot!("war_map", s);
}

#[test]
fn snapshot_war_map_region_selected() {
    use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};
    use sastaspace_core::event::{Action, InputAction};
    let mut app = TypewarsApp::new();
    app.set_player(make_player("commander", 0));
    app.set_regions(fixture_regions());
    // Move down once to select region index 1 (Zethara Station — liberated by Codex)
    app.handle(Action::Input(InputAction::Key(KeyEvent::new(
        KeyCode::Down,
        KeyModifiers::empty(),
    ))));
    let s = render_to_string(&mut app, 120, 30);
    insta::assert_snapshot!("war_map_second_region", s);
}

// ---------------------------------------------------------------------------
// 3. Battle (loading state)
// ---------------------------------------------------------------------------

#[test]
fn snapshot_battle_loading() {
    let mut app = TypewarsApp::new();
    let player = make_player("commander", 3);
    app.set_player(player);
    app.set_regions(fixture_regions());
    // Enter battle — region 0 (Arkanis Prime)
    let region = fixture_regions().into_iter().next().unwrap();
    app.state.enter_battle(region);
    let s = render_to_string(&mut app, 120, 30);
    insta::assert_snapshot!("battle_loading", s);
}

#[test]
fn snapshot_battle_with_session_and_words() {
    let mut app = TypewarsApp::new();
    app.set_player(make_player("commander", 0));
    app.set_regions(fixture_regions());

    let region = fixture_regions().into_iter().next().unwrap();
    app.state.enter_battle(region);

    // Inject a session
    app.set_battle_session(BattleSessionRow {
        id: 1,
        region_id: 0,
        started_at_ms: 0,
        streak: 5,
        multiplier: 1.5,
        accuracy_hits: 20,
        accuracy_misses: 2,
        damage_dealt: 480,
        active: true,
    });

    // Inject some words
    app.set_words(vec![
        WordRow {
            id: 1,
            session_id: 1,
            text: "assault".to_string(),
            difficulty: 2,
            base_damage: 40,
            expires_at_ms: u64::MAX,
        },
        WordRow {
            id: 2,
            session_id: 1,
            text: "nexus".to_string(),
            difficulty: 1,
            base_damage: 20,
            expires_at_ms: u64::MAX,
        },
        WordRow {
            id: 3,
            session_id: 1,
            text: "breach".to_string(),
            difficulty: 1,
            base_damage: 20,
            expires_at_ms: u64::MAX,
        },
    ]);

    let s = render_to_string(&mut app, 120, 30);
    insta::assert_snapshot!("battle_with_words", s);
}

// ---------------------------------------------------------------------------
// 4. Leaderboard
// ---------------------------------------------------------------------------

#[test]
fn snapshot_leaderboard() {
    use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};
    use sastaspace_core::event::{Action, InputAction};
    let mut app = TypewarsApp::new();
    app.set_player(make_player("beta", 1));
    app.set_regions(fixture_regions());
    app.set_players(fixture_players());
    // Navigate to leaderboard
    app.handle(Action::Input(InputAction::Key(KeyEvent::new(
        KeyCode::Char('b'),
        KeyModifiers::empty(),
    ))));
    let s = render_to_string(&mut app, 120, 30);
    insta::assert_snapshot!("leaderboard", s);
}

// ---------------------------------------------------------------------------
// 5. Profile modal
// ---------------------------------------------------------------------------

#[test]
fn snapshot_profile_modal() {
    let mut app = TypewarsApp::new();
    app.set_player(make_player("beta", 1));
    app.set_regions(fixture_regions());
    app.set_players(fixture_players());
    app.state.open_leaderboard();
    app.state.open_profile("alpha".to_string());
    let s = render_to_string(&mut app, 120, 30);
    insta::assert_snapshot!("profile_modal", s);
}

// ---------------------------------------------------------------------------
// 6. Legion swap modal
// ---------------------------------------------------------------------------

#[test]
fn snapshot_legion_swap_modal() {
    let mut app = TypewarsApp::new();
    app.set_player(make_player("commander", 2));
    app.set_regions(fixture_regions());
    app.state.open_legion_swap();
    let s = render_to_string(&mut app, 120, 30);
    insta::assert_snapshot!("legion_swap_modal", s);
}

// ---------------------------------------------------------------------------
// 7. Liberated splash
// ---------------------------------------------------------------------------

#[test]
fn snapshot_liberated_splash() {
    let mut app = TypewarsApp::new();
    let region = make_region(0, "Arkanis Prime", 0, 5000, 1);
    app.state.liberated_splash = Some(LiberatedSplashState::new(region, LegionId::TheCodex));
    app.state.screen = Screen::LiberatedSplash;
    let s = render_to_string(&mut app, 120, 30);
    insta::assert_snapshot!("liberated_splash", s);
}
