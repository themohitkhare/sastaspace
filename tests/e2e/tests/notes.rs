//! E2E tests for the notes app.
//!
//! Navigation: the shell's global Shift-N shortcut switches to the notes app.
//! The notes app renders a two-pane split: " notes " list pane on the left,
//! " editor " pane on the right.

use e2e::{expect_ansi, LaunchedTui, SpacetimeFixture};
use serial_test::serial;
use std::time::Duration;

#[test]
#[serial]
fn notes_two_pane_renders() {
    let fixture = SpacetimeFixture::start().expect("fixture failed");
    std::env::set_var("SASTASPACE_STDB_URI", fixture.ws_url.clone());
    std::env::set_var("SASTASPACE_STDB_MODULE", "sastaspace");

    let mut tui = LaunchedTui::launch(&fixture).expect("launch failed");

    // Give portfolio time to draw, then navigate to notes via Shift-N.
    std::thread::sleep(Duration::from_millis(800));
    tui.session.send("N").expect("send Shift-N");

    // The notes view always shows a " notes " list pane title.
    expect_ansi(&mut tui.session, "notes", Duration::from_secs(6))
        .expect("notes pane title not found");

    tui.session.send("q").expect("quit");
    let _ = tui.session.expect(expectrl::Eof);
}

#[test]
#[serial]
fn notes_editor_normal_mode_indicator() {
    let fixture = SpacetimeFixture::start().expect("fixture failed");
    std::env::set_var("SASTASPACE_STDB_URI", fixture.ws_url.clone());
    std::env::set_var("SASTASPACE_STDB_MODULE", "sastaspace");

    let mut tui = LaunchedTui::launch(&fixture).expect("launch failed");

    // Navigate to notes.
    std::thread::sleep(Duration::from_millis(800));
    tui.session.send("N").expect("send Shift-N");
    expect_ansi(&mut tui.session, "notes", Duration::from_secs(6)).expect("notes app");

    // Tab into the editor pane.
    // Small sleep lets the render loop process the navigation before further input.
    std::thread::sleep(Duration::from_millis(200));
    tui.session.send("\t").expect("tab to editor");

    // The editor title shows "[NORMAL]" when focused (no auth required for mode indicator).
    expect_ansi(&mut tui.session, "NORMAL", Duration::from_secs(6))
        .expect("NORMAL mode indicator not found after Tab to editor");

    tui.session.send("q").expect("quit");
    let _ = tui.session.expect(expectrl::Eof);
}

/// Pressing 'i' in editor focus triggers a NeedLogin action (shell opens the
/// login modal) rather than entering INSERT mode — because `enter_insert()` in
/// `NotesState` requires `self.authenticated == true`.  This is by design: notes
/// editing is authenticated-only.  We #[ignore] the INSERT mode test since
/// seeding auth state from the fixture requires a full magic-link round-trip
/// that is covered by `magic_link_round_trip` in `magic_link.rs`.
#[test]
#[serial]
#[ignore = "INSERT mode requires authenticated session; covered indirectly by magic_link_round_trip"]
fn notes_insert_mode_requires_auth() {
    // Placeholder — real flow: complete magic-link auth, then Tab + i, expect INSERT.
}

/// When no notes are loaded (empty STDB), the comments popover can't be opened
/// (the 'c' key is guarded by `current_note().is_some()`).  We verify the list
/// pane renders and that pressing 'c' in an empty state is silently ignored.
#[test]
#[serial]
fn notes_quit_cleanly() {
    let fixture = SpacetimeFixture::start().expect("fixture failed");
    std::env::set_var("SASTASPACE_STDB_URI", fixture.ws_url.clone());
    std::env::set_var("SASTASPACE_STDB_MODULE", "sastaspace");

    let mut tui = LaunchedTui::launch(&fixture).expect("launch failed");

    std::thread::sleep(Duration::from_millis(800));
    tui.session.send("N").expect("send Shift-N");
    expect_ansi(&mut tui.session, "notes", Duration::from_secs(6)).expect("notes app");

    // Press 'c' with no note selected — should be a no-op.
    tui.session.send("c").expect("send c");

    // Send q — should exit cleanly.
    tui.session.send("q").expect("quit");
    let _ = tui.session.expect(expectrl::Eof).expect("clean exit after q");
}
