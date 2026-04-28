use app_notes::{CommentRow, NoteRow, Notes};
use ratatui::{backend::TestBackend, layout::Rect, Terminal};
use sastaspace_core::App;

fn fixture_notes() -> Vec<NoteRow> {
    vec![
        NoteRow {
            slug: "rust-ownership".into(),
            title: "Rust Ownership".into(),
            body: "Ownership is Rust's most unique feature.\nEvery value has an owner.".into(),
            status: "live".into(),
            tags: vec!["rust".into(), "language".into()],
            url: "".into(),
        },
        NoteRow {
            slug: "async-await".into(),
            title: "Async Await".into(),
            body: "Async functions return a Future.".into(),
            status: "draft".into(),
            tags: vec!["rust".into(), "async".into()],
            url: "".into(),
        },
    ]
}

fn fixture_comments() -> Vec<CommentRow> {
    vec![
        CommentRow {
            id: 1,
            post_slug: "async-await".into(),
            author_name: "alice".into(),
            body: "Great explanation!".into(),
            status: "approved".into(),
        },
        CommentRow {
            id: 2,
            post_slug: "async-await".into(),
            author_name: "bob".into(),
            body: "Could you add an example with tokio?".into(),
            status: "approved".into(),
        },
    ]
}

fn render_to_string(app: &mut Notes, w: u16, h: u16) -> String {
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
fn notes_empty_state_snapshot() {
    let mut app = Notes::new();
    let s = render_to_string(&mut app, 80, 24);
    insta::assert_snapshot!("empty", s);
}

#[test]
fn notes_list_selected_snapshot() {
    let mut app = Notes::new();
    app.set_notes(fixture_notes());
    let s = render_to_string(&mut app, 80, 24);
    insta::assert_snapshot!("list_selected", s);
}

#[test]
fn notes_editor_focused_snapshot() {
    use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};
    use sastaspace_core::event::{Action, InputAction};

    let mut app = Notes::new();
    app.set_notes(fixture_notes());
    // Press Tab to move focus to editor
    app.handle(Action::Input(InputAction::Key(KeyEvent::new(
        KeyCode::Tab,
        KeyModifiers::empty(),
    ))));
    let s = render_to_string(&mut app, 80, 24);
    insta::assert_snapshot!("editor_focused", s);
}

#[test]
fn notes_insert_mode_snapshot() {
    use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};
    use sastaspace_core::event::{Action, InputAction};

    let mut app = Notes::new();
    app.set_notes(fixture_notes());
    app.set_authenticated(true);
    // Tab to editor
    app.handle(Action::Input(InputAction::Key(KeyEvent::new(
        KeyCode::Tab,
        KeyModifiers::empty(),
    ))));
    // i to enter insert mode
    app.handle(Action::Input(InputAction::Key(KeyEvent::new(
        KeyCode::Char('i'),
        KeyModifiers::empty(),
    ))));
    let s = render_to_string(&mut app, 80, 24);
    insta::assert_snapshot!("insert_mode", s);
}

#[test]
fn notes_comments_open_snapshot() {
    use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};
    use sastaspace_core::event::{Action, InputAction};

    let mut app = Notes::new();
    app.set_notes(fixture_notes());
    app.set_comments(fixture_comments());
    // Sorted: Async Await (0), Rust Ownership (1) → press 'j' to select Async Await (which has comments).
    // Actually sorted alphabetically: Async Await is index 0 already.
    // Press 'c' to open comments.
    app.handle(Action::Input(InputAction::Key(KeyEvent::new(
        KeyCode::Char('c'),
        KeyModifiers::empty(),
    ))));
    let s = render_to_string(&mut app, 80, 24);
    insta::assert_snapshot!("comments_open", s);
}

#[test]
fn notes_unauthenticated_insert_queues_login() {
    use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};
    use sastaspace_core::event::{Action, InputAction};

    let mut app = Notes::new();
    app.set_notes(fixture_notes());
    // NOT calling set_authenticated(true)
    // Tab to editor
    app.handle(Action::Input(InputAction::Key(KeyEvent::new(
        KeyCode::Tab,
        KeyModifiers::empty(),
    ))));
    // Try to enter insert mode — should queue NeedLogin
    app.handle(Action::Input(InputAction::Key(KeyEvent::new(
        KeyCode::Char('i'),
        KeyModifiers::empty(),
    ))));
    let pending = app.take_pending();
    assert!(
        matches!(pending, Some(app_notes::PendingAction::NeedLogin)),
        "expected NeedLogin, got {pending:?}"
    );
}
