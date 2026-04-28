use app_portfolio::{Portfolio, ProjectRow};
use ratatui::{backend::TestBackend, layout::Rect, Terminal};
use sastaspace_core::App;

fn fixture_projects() -> Vec<ProjectRow> {
    vec![
        ProjectRow {
            slug: "typewars".into(),
            title: "TypeWars".into(),
            blurb: "Multiplayer typing-game with a contested global warmap.".into(),
            status: "live".into(),
        },
        ProjectRow {
            slug: "notes".into(),
            title: "Notes".into(),
            blurb: "Personal workshop notes with comments and moderation.".into(),
            status: "live".into(),
        },
        ProjectRow {
            slug: "deck".into(),
            title: "Deck".into(),
            blurb: "Plain-text → ready-to-use audio packs (background, loop, notification).".into(),
            status: "beta".into(),
        },
    ]
}

fn render_to_string(app: &mut Portfolio, w: u16, h: u16) -> String {
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

#[test]
fn portfolio_empty_state_snapshot() {
    let mut app = Portfolio::new();
    let s = render_to_string(&mut app, 80, 20);
    insta::assert_snapshot!("empty", s);
}

#[test]
fn portfolio_with_projects_snapshot() {
    let mut app = Portfolio::new();
    app.set_projects(fixture_projects());
    let s = render_to_string(&mut app, 80, 20);
    insta::assert_snapshot!("with_projects", s);
}

#[test]
fn portfolio_selection_moves_with_j_k() {
    use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};
    use sastaspace_core::event::{Action, InputAction};
    let mut app = Portfolio::new();
    app.set_projects(fixture_projects());

    // Sorted alphabetically: Deck, Notes, TypeWars. Selected starts at 0 → Deck.
    let _ = app.handle(Action::Input(InputAction::Key(KeyEvent::new(
        KeyCode::Char('j'),
        KeyModifiers::empty(),
    ))));
    let s = render_to_string(&mut app, 80, 20);
    insta::assert_snapshot!("selected_notes", s);
}
