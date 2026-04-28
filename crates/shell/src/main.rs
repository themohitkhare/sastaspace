//! sastaspace TUI binary entry point.

mod router;
mod terminal;

use color_eyre::eyre::Result;
use sastaspace_core::{
    config::Config,
    event::{Action, InputAction, StdbEvent},
    keymap::{classify, GlobalKey},
};
use crossterm::event::{Event, EventStream};
use directories::ProjectDirs;
use futures::StreamExt;
use std::time::Duration;
use stdb_client::{StdbConfig, StdbHandle};
use tokio::sync::mpsc::{unbounded_channel, UnboundedSender};
use tracing::{error, info};
use tracing_subscriber::EnvFilter;

const TICK_MS: u64 = 16;

#[tokio::main(flavor = "multi_thread")]
async fn main() -> Result<()> {
    install_panic_hook()?;
    init_tracing();

    let cfg = Config::load()?;
    info!(stdb_uri = %cfg.stdb_uri, "config loaded");

    let mut term = terminal::enter()?;
    let _guard = terminal::TerminalGuard;

    let result = run(&mut term, cfg).await;

    drop(_guard); // explicit so the leave order is clear

    if let Err(ref e) = result {
        error!(err = %e, "shell exited with error");
    }
    result
}

async fn run(term: &mut terminal::Tui, cfg: Config) -> Result<()> {
    let (tx, mut rx) = unbounded_channel::<Action>();

    spawn_input_task(tx.clone());
    spawn_tick_task(tx.clone());

    let _stdb = match connect_stdb(&cfg, tx.clone()).await {
        Ok(h) => Some(h),
        Err(e) => {
            // Don't crash on startup if STDB is down — show empty portfolio + a toast.
            error!(err = %e, "stdb connect failed; running in offline mode");
            None
        }
    };

    let mut router = router::Router::new("portfolio");
    router.register(Box::new(app_portfolio::Portfolio::new()));

    loop {
        // Render.
        term.draw(|f| router.current().render(f, f.area()))?;

        // Drain available actions (don't block forever — the tick task wakes us).
        let action = match rx.recv().await {
            Some(a) => a,
            None => break,
        };

        // Global key dispatch first.
        if let Action::Input(InputAction::Key(k)) = &action {
            if let Some(GlobalKey::Quit) = classify(*k) {
                break;
            }
        }

        // STDB project updates pushed into the portfolio app — F11 wires
        // the actual table read. For F8 we just confirm the channel works.
        if let Action::Stdb(StdbEvent::Updated("project")) = &action {
            // F11: read projects from stdb_client and push into the portfolio app.
        }

        let result = router.current().handle(action);
        if !router.dispatch(result) {
            break;
        }
    }

    Ok(())
}

fn spawn_input_task(tx: UnboundedSender<Action>) {
    tokio::spawn(async move {
        let mut stream = EventStream::new();
        while let Some(Ok(ev)) = stream.next().await {
            let action = match ev {
                Event::Key(k) => Action::Input(InputAction::Key(k)),
                Event::Resize(w, h) => Action::Input(InputAction::Resize(w, h)),
                _ => continue,
            };
            if tx.send(action).is_err() {
                return;
            }
        }
    });
}

fn spawn_tick_task(tx: UnboundedSender<Action>) {
    tokio::spawn(async move {
        let mut interval = tokio::time::interval(Duration::from_millis(TICK_MS));
        loop {
            interval.tick().await;
            if tx.send(Action::Tick).is_err() {
                return;
            }
        }
    });
}

async fn connect_stdb(cfg: &Config, tx: UnboundedSender<Action>) -> Result<StdbHandle> {
    let creds_path = ProjectDirs::from("com", "sastaspace", "sastaspace")
        .map(|d| d.data_dir().join("credentials.json"))
        .unwrap_or_else(|| std::path::PathBuf::from(".sastaspace-credentials.json"));
    let stdb_cfg = StdbConfig {
        uri: cfg.stdb_uri.clone(),
        module: cfg.stdb_module.clone(),
        token: None, // foundations: anon. Auth wires in once login lands (F10).
        credentials_path: creds_path,
    };
    Ok(StdbHandle::connect(stdb_cfg, tx).await?)
}

fn init_tracing() {
    let log_dir = ProjectDirs::from("com", "sastaspace", "sastaspace")
        .map(|d| d.data_dir().join("logs"))
        .unwrap_or_else(|| std::path::PathBuf::from(".sastaspace-logs"));
    let _ = std::fs::create_dir_all(&log_dir);
    let file = tracing_appender::rolling::daily(log_dir, "sastaspace.log");
    let filter = EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info"));
    tracing_subscriber::fmt()
        .with_env_filter(filter)
        .with_writer(file)
        .with_ansi(false)
        .init();
}

fn install_panic_hook() -> Result<()> {
    let (panic_hook, eyre_hook) = color_eyre::config::HookBuilder::default().into_hooks();
    eyre_hook.install()?;
    let panic_hook = panic_hook.into_panic_hook();
    std::panic::set_hook(Box::new(move |info| {
        let _ = terminal::leave();
        panic_hook(info);
    }));
    Ok(())
}
