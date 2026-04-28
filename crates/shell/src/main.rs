//! sastaspace TUI binary entry point.

mod login;
mod router;
mod terminal;

use auth::{keychain::KeychainStore, magic_link::MagicLinkConfig};
use color_eyre::eyre::Result;
use crossterm::event::{Event, EventStream};
use directories::ProjectDirs;
use futures::StreamExt;
use login::{LoginModal, LoginOutcome};
use sastaspace_core::{
    config::Config,
    event::{Action, InputAction, StdbEvent},
    keymap::{classify, GlobalKey},
};
use std::sync::Arc;
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

    let stdb = match connect_stdb(&cfg, tx.clone()).await {
        Ok(h) => Some(h),
        Err(e) => {
            // Don't crash on startup if STDB is down — show empty portfolio + a toast.
            error!(err = %e, "stdb connect failed; running in offline mode");
            None
        }
    };

    let mut router = router::Router::new("portfolio");
    router.register(Box::new(app_portfolio::Portfolio::new()));

    // Admin app — owner-gated. Device-flow client_id from config or env.
    let google_client_id = std::env::var("GOOGLE_CLIENT_ID").unwrap_or_default();
    let admin_device_cfg = auth::google_device::DeviceFlowConfig::for_client(google_client_id);
    router.register(Box::new(app_admin::Admin::new(admin_device_cfg)));

    let store = Arc::new(KeychainStore::new());
    let magic_cfg = MagicLinkConfig {
        stdb_http_base: cfg
            .stdb_uri
            .replace("ws://", "http://")
            .replace("wss://", "https://"),
        module: cfg.stdb_module.clone(),
        http_timeout: Duration::from_secs(10),
    };
    let mut modal: Option<LoginModal> = None;

    loop {
        // Render base + modal.
        term.draw(|f| {
            router.current().render(f, f.area());
            if let Some(m) = &modal {
                m.render(f, f.area());
            }
        })?;

        let action = match rx.recv().await {
            Some(a) => a,
            None => break,
        };

        if let Action::Input(InputAction::Key(k)) = &action {
            // Modal eats keys when open.
            if let Some(m) = modal.as_mut() {
                if let LoginOutcome::Closed = m.handle_key(*k).await {
                    modal = None;
                }
                continue;
            }
            // Open modal on Shift-L (full :login palette comes later).
            if matches!(k.code, crossterm::event::KeyCode::Char('L')) && k.modifiers.is_empty() {
                modal = Some(LoginModal::new(magic_cfg.clone(), store.clone()));
                continue;
            }
            if let Some(GlobalKey::Quit) = classify(*k) {
                break;
            }
        }

        if let Action::Stdb(StdbEvent::Updated("project")) = &action {
            if let Some(handle) = stdb.as_ref() {
                let projects = stdb_client::sub_helpers::read_projects(&handle.conn);
                if let Some(app) = router.app_mut("portfolio") {
                    if let Some(p) = app.as_any_mut().downcast_mut::<app_portfolio::Portfolio>() {
                        p.set_projects(projects);
                    }
                }
            }
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
