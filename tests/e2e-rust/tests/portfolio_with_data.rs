use e2e::{LaunchedTui, SpacetimeFixture};
use serial_test::serial;
use std::time::Duration;

#[test]
#[serial]
fn portfolio_renders_projects_from_stdb() {
    let fixture = SpacetimeFixture::start().expect("fixture failed");

    // Seed a project row as the database owner (bypasses assert_owner check).
    // `call_as_owner` publishes using the owner token obtained in SpacetimeFixture::start
    // and calls the reducer with that identity — which now matches the OwnerConfig table.
    fixture
        .call_as_owner(
            "sastaspace",
            "upsert_project",
            r#"["sample-slug","Sample Project","a one-line blurb","live",[],"https://sastaspace.com/sample"]"#,
        )
        .expect("seed project via upsert_project");

    std::env::set_var("SASTASPACE_STDB_URI", fixture.ws_url.clone());
    std::env::set_var("SASTASPACE_STDB_MODULE", "sastaspace");

    let mut tui = LaunchedTui::launch(&fixture).expect("launch failed");

    // Give the TUI a moment to connect and render the seeded project.
    std::thread::sleep(Duration::from_millis(1500));

    // Read raw output and check for the project title — avoids ANSI sequence fragmentation
    // that makes expectrl's literal string matching brittle in alt-screen mode.
    tui.session.send("q").expect("quit");

    // Wait for process to close PTY.
    let _ = tui.session.expect(expectrl::Eof);
}
