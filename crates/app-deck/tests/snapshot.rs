//! Snapshot tests for the deck app — one per major state.

use app_deck::{DeckApp, GenerateStatus, PlanStatus, PlannedTrack, Screen};
use ratatui::{backend::TestBackend, layout::Rect, Terminal};
use sastaspace_core::App;

fn render_to_string(app: &mut DeckApp, w: u16, h: u16) -> String {
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

fn fixture_tracks() -> Vec<PlannedTrack> {
    vec![
        PlannedTrack {
            name: "Main Theme".into(),
            kind: "background".into(),
            length: 120,
            desc: "Sweeping orchestral backdrop".into(),
            tempo: "moderate".into(),
            instruments: "strings, brass".into(),
            mood: "epic".into(),
        },
        PlannedTrack {
            name: "Battle Loop".into(),
            kind: "loop".into(),
            length: 30,
            desc: "Intense percussion-driven loop".into(),
            tempo: "fast".into(),
            instruments: "drums, synth".into(),
            mood: "tense".into(),
        },
        PlannedTrack {
            name: "Victory".into(),
            kind: "notification".into(),
            length: 5,
            desc: "Short triumph sting".into(),
            tempo: "fast".into(),
            instruments: "brass, bells".into(),
            mood: "triumphant".into(),
        },
    ]
}

// ── Snapshot 1: Plan screen, idle (empty description) ────────────────────────
#[test]
fn plan_idle_snapshot() {
    let mut app = DeckApp::new();
    let s = render_to_string(&mut app, 100, 30);
    insta::assert_snapshot!("plan_idle", s);
}

// ── Snapshot 2: Plan screen, pending (waiting for AI planner) ────────────────
#[test]
fn plan_pending_snapshot() {
    let mut app = DeckApp::new();
    app.state_mut().description = "A sci-fi exploration game with dynamic soundtrack".into();
    app.state_mut().description_cursor = app.state().description.len();
    app.state_mut().track_count = 5;
    app.state_mut().plan_status = PlanStatus::Pending;
    let s = render_to_string(&mut app, 100, 30);
    insta::assert_snapshot!("plan_pending", s);
}

// ── Snapshot 3: Plan screen, done (tracks rendered) ──────────────────────────
#[test]
fn plan_done_snapshot() {
    let mut app = DeckApp::new();
    app.state_mut().description = "A sci-fi exploration game with dynamic soundtrack".into();
    app.state_mut().description_cursor = app.state().description.len();
    app.state_mut().track_count = 3;
    app.state_mut().plan_status = PlanStatus::Done;
    app.state_mut().plan_request_id = Some(42);
    app.state_mut().planned_tracks = fixture_tracks();
    app.state_mut().status_msg = Some("Plan ready — press :approve or 'g' to generate".into());
    let s = render_to_string(&mut app, 100, 30);
    insta::assert_snapshot!("plan_done", s);
}

// ── Snapshot 4: Generate screen, idle ────────────────────────────────────────
#[test]
fn generate_idle_snapshot() {
    let mut app = DeckApp::new();
    app.state_mut().screen = Screen::Generate;
    app.state_mut().planned_tracks = fixture_tracks();
    app.state_mut().plan_request_id = Some(42);
    let s = render_to_string(&mut app, 100, 30);
    insta::assert_snapshot!("generate_idle", s);
}

// ── Snapshot 5: Generate screen, done + downloaded ───────────────────────────
#[test]
fn generate_downloaded_snapshot() {
    let mut app = DeckApp::new();
    app.state_mut().screen = Screen::Generate;
    app.state_mut().planned_tracks = fixture_tracks();
    app.state_mut().plan_request_id = Some(42);
    app.state_mut().generate_job_id = Some(99);
    app.state_mut().generate_status = GenerateStatus::Downloaded {
        path: "/Users/mohit/Music/sastaspace/99".into(),
    };
    app.state_mut().status_msg = Some("Saved to /Users/mohit/Music/sastaspace/99".into());
    let s = render_to_string(&mut app, 100, 30);
    insta::assert_snapshot!("generate_downloaded", s);
}

// ── Snapshot 6: Plan screen, failed ──────────────────────────────────────────
#[test]
fn plan_failed_snapshot() {
    let mut app = DeckApp::new();
    app.state_mut().description = "hi".into();
    app.state_mut().description_cursor = 2;
    app.state_mut().plan_status = PlanStatus::Failed("description too short (min 4 chars)".into());
    let s = render_to_string(&mut app, 100, 30);
    insta::assert_snapshot!("plan_failed", s);
}
