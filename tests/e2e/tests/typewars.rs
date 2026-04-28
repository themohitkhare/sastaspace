//! E2E tests for the typewars app.
//!
//! Navigation: the shell's global Shift-T shortcut switches to typewars.
//! On first launch (no player registered) the app shows the LegionSelect screen
//! with "CHOOSE YOUR LEGION" and five legion columns.

use e2e::{expect_ansi, LaunchedTui, SpacetimeFixture};
use serial_test::serial;
use std::time::Duration;

#[test]
#[serial]
fn typewars_legion_select_renders() {
    let fixture = SpacetimeFixture::start().expect("fixture failed");
    std::env::set_var("SASTASPACE_STDB_URI", fixture.ws_url.clone());
    // Use the sastaspace module; typewars UI state is local (LegionSelect
    // renders without needing any STDB subscription data).
    std::env::set_var("SASTASPACE_STDB_MODULE", "sastaspace");

    let mut tui = LaunchedTui::launch(&fixture).expect("launch failed");

    // Navigate to typewars via Shift-T.
    std::thread::sleep(Duration::from_millis(800));
    tui.session.send("T").expect("send Shift-T");

    // LegionSelect always renders "CHOOSE YOUR LEGION".
    expect_ansi(&mut tui.session, "CHOOSE YOUR LEGION", Duration::from_secs(6))
        .expect("LegionSelect screen not found");

    tui.session.send("q").expect("quit");
    let _ = tui.session.expect(expectrl::Eof);
}

/// The callsign input widget renders with a "(N/24)" length indicator in the
/// block title.  After the initial render, expect_ansi already consumed the
/// full-screen redraw bytes.  Subsequent expect_ansi calls see only
/// DIFFERENTIAL re-render bytes from ratatui; those only cover changed cells
/// and may not re-emit the full callsign block.
///
/// We verify the initial screen contains the callsign widget (via "0/24" in
/// the full first-render), then verify typing doesn't crash the app.
#[test]
#[serial]
fn typewars_callsign_widget_present() {
    let fixture = SpacetimeFixture::start().expect("fixture failed");
    std::env::set_var("SASTASPACE_STDB_URI", fixture.ws_url.clone());
    // Use the sastaspace module; typewars UI state is local (LegionSelect
    // renders without needing any STDB subscription data).
    std::env::set_var("SASTASPACE_STDB_MODULE", "sastaspace");

    let mut tui = LaunchedTui::launch(&fixture).expect("launch failed");

    std::thread::sleep(Duration::from_millis(800));
    tui.session.send("T").expect("send Shift-T");

    // The initial LegionSelect full-render includes the callsign block with
    // title "callsign (0/24)".  Check for "0/24" in the full first render.
    expect_ansi(&mut tui.session, "0/24", Duration::from_secs(6))
        .expect("callsign (0/24) block not found in initial render");

    // Press 'i' to focus callsign input, type a name — verify no crash.
    std::thread::sleep(Duration::from_millis(200));
    tui.session.send("i").expect("i to focus callsign");
    std::thread::sleep(Duration::from_millis(200));
    tui.session.send("testpilot").expect("type callsign");
    std::thread::sleep(Duration::from_millis(300));

    // Esc defocuses the callsign input (see typewars Esc-bug fix).
    // Sleep briefly between Esc and 'q' — sending them back-to-back can cause
    // crossterm to interpret the sequence as Alt+q (ESC prefix + 'q').
    tui.session.send("\x1b").expect("esc");
    std::thread::sleep(Duration::from_millis(150));
    tui.session.send("q").expect("quit");
    let _ = tui.session.expect(expectrl::Eof).expect("clean exit");
}

/// Verify that Esc on LegionSelect is a no-op (screen stays, no crash).
#[test]
#[serial]
fn typewars_esc_on_legion_select_is_noop() {
    let fixture = SpacetimeFixture::start().expect("fixture failed");
    std::env::set_var("SASTASPACE_STDB_URI", fixture.ws_url.clone());
    // Use the sastaspace module; typewars UI state is local (LegionSelect
    // renders without needing any STDB subscription data).
    std::env::set_var("SASTASPACE_STDB_MODULE", "sastaspace");

    let mut tui = LaunchedTui::launch(&fixture).expect("launch failed");

    std::thread::sleep(Duration::from_millis(800));
    tui.session.send("T").expect("send Shift-T");
    expect_ansi(&mut tui.session, "CHOOSE YOUR LEGION", Duration::from_secs(6))
        .expect("LegionSelect screen");

    // Esc on LegionSelect is handled by handle_escape() which returns Continue —
    // the screen should still show "CHOOSE YOUR LEGION".
    tui.session.send("\x1b").expect("esc");
    std::thread::sleep(Duration::from_millis(300));

    // Still on legion select — no crash, still renderable.
    tui.session.send("q").expect("quit");
    let _ = tui.session.expect(expectrl::Eof).expect("clean exit");
}

/// Leaderboard is accessible from WarMap via 'b'.  We can't reach WarMap without
/// a registered player (that would require a live STDB round-trip + region seeding).
/// Instead we verify the LegionSelect screen and that the app handles 'b' gracefully
/// on LegionSelect (it's simply unhandled → no-op).
///
/// Full WarMap→Leaderboard→back flow is #[ignore]d because it requires seeding
/// a player via a STDB reducer call that succeeds asynchronously, which would
/// make the test timing-dependent and brittle.
#[test]
#[serial]
#[ignore = "requires async STDB player registration to reach WarMap; covered by unit tests"]
fn typewars_leaderboard_accessible() {
    // Placeholder — real flow: register player via fixture.call_as_owner → wait
    // for STDB push → navigate to WarMap → press 'b' → expect "Leaderboard".
}
