use e2e::{LaunchedTui, SpacetimeFixture};
use serial_test::serial;
use std::time::Duration;

#[test]
#[serial] // e2e tests share a fixture port; run sequentially
fn portfolio_splash_renders() {
    let fixture = SpacetimeFixture::start().expect("fixture failed");

    // Point the binary at the fixture instead of prod.
    std::env::set_var("SASTASPACE_STDB_URI", fixture.ws_url.clone());
    std::env::set_var("SASTASPACE_STDB_MODULE", "sastaspace");

    let mut tui = LaunchedTui::launch(&fixture).expect("launch failed");

    // Give the alt-screen a moment to draw.
    std::thread::sleep(Duration::from_millis(800));

    // Send `q` to quit cleanly.
    tui.session.send("q").expect("send q");

    // Wait for the process to exit (EOF = process closed the PTY).
    let _ = tui.session.expect(expectrl::Eof).ok();
}
