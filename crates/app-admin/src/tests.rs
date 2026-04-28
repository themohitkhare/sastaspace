//! Snapshot tests for the admin dashboard.
//!
//! Uses `ratatui::backend::TestBackend` + `insta` to capture the rendered
//! terminal buffer as a plain-text ASCII rectangle.
//!
//! Run with:
//!   cargo test -p app-admin
//!   cargo insta review   (to accept new snapshots)

#[cfg(test)]
mod snapshot {
    use crate::{
        Admin, ContainerRow, DeviceFlowPhase, FlaggedComment, LogLine, LogPopoverState,
        SystemMetrics,
    };
    use auth::{google_device::DeviceFlowConfig, InMemoryStore, TokenStore};
    use ratatui::{backend::TestBackend, Terminal};
    use sastaspace_core::App;
    use std::sync::Arc;
    use std::time::Instant;

    const W: u16 = 120;
    const H: u16 = 40;

    fn test_app() -> Admin {
        Admin::with_store(
            DeviceFlowConfig::for_client("test-client-id"),
            Arc::new(InMemoryStore::new()),
        )
    }

    // ── Snapshot 1: device-flow panel (not authenticated, idle) ──────────────

    #[test]
    fn snapshot_device_flow_idle() {
        let app = test_app();
        let mut term = Terminal::new(TestBackend::new(W, H)).unwrap();
        term.draw(|f| {
            let mut a = app;
            a.render(f, f.area());
        })
        .unwrap();
        insta::assert_snapshot!("device_flow_idle", term.backend().to_string());
    }

    // ── Snapshot 2: device-flow panel in Pending state ────────────────────────

    #[test]
    fn snapshot_device_flow_pending() {
        let mut app = test_app();
        app.state.device_flow = DeviceFlowPhase::Pending {
            user_code: "WDJB-MJHT".into(),
            verification_url: "https://google.com/device".into(),
            expires_in: 300,
            issued_at: Instant::now(),
        };
        let mut term = Terminal::new(TestBackend::new(W, H)).unwrap();
        term.draw(|f| {
            app.render(f, f.area());
        })
        .unwrap();
        insta::assert_snapshot!("device_flow_pending", term.backend().to_string());
    }

    // ── Snapshot 3: main dashboard with metrics ───────────────────────────────

    #[test]
    fn snapshot_metrics_panel() {
        let mut app = test_app();
        // Authenticate.
        app.state.owner_jwt = Some("fake-jwt-for-test".into());
        app.state.metrics = SystemMetrics {
            cpu_pct: 23.5,
            cores: 8,
            mem_used_gb: 7.2,
            mem_total_gb: 15.6,
            mem_pct: 46.2,
            swap_used_mb: 128,
            swap_total_mb: 2048,
            disk_used_gb: 120,
            disk_total_gb: 500,
            disk_pct: 24.0,
            net_tx_bytes: 123_456_789,
            net_rx_bytes: 987_654_321,
            uptime_s: 2 * 86400 + 3 * 3600 + 15 * 60,
            gpu_pct: Some(40),
            gpu_model: Some("NVIDIA RTX 3080".into()),
            updated_at_ms: 0,
        };
        app.state.containers = vec![
            ContainerRow {
                name: "sastaspace-stdb".into(),
                status: "Up 2 days".into(),
                image: "clockworklabs/spacetimedb:latest".into(),
                uptime_s: 2 * 86400,
                mem_used_mb: 512,
                mem_limit_mb: 2048,
                restart_count: 0,
            },
            ContainerRow {
                name: "moderator-agent".into(),
                status: "Up 12 hours".into(),
                image: "sastaspace/moderator:latest".into(),
                uptime_s: 12 * 3600,
                mem_used_mb: 64,
                mem_limit_mb: 256,
                restart_count: 1,
            },
        ];
        let mut term = Terminal::new(TestBackend::new(W, H)).unwrap();
        term.draw(|f| {
            app.render(f, f.area());
        })
        .unwrap();
        insta::assert_snapshot!("metrics_panel", term.backend().to_string());
    }

    // ── Snapshot 4: moderation queue with flagged comments ────────────────────

    #[test]
    fn snapshot_moderation_queue() {
        let mut app = test_app();
        app.state.owner_jwt = Some("fake-jwt-for-test".into());
        app.state.flagged = vec![
            FlaggedComment {
                id: 12,
                post_slug: "my-first-post".into(),
                author_name: "Alice".into(),
                body: "Buy cheap Rx at http://spam.example! Great deals.".into(),
            },
            FlaggedComment {
                id: 17,
                post_slug: "another-post".into(),
                author_name: "Bob".into(),
                body: "Inject SQL'; DROP TABLE users; --".into(),
            },
        ];
        app.state.focus = crate::state::Focus::Moderation;
        let mut term = Terminal::new(TestBackend::new(W, H)).unwrap();
        term.draw(|f| {
            app.render(f, f.area());
        })
        .unwrap();
        insta::assert_snapshot!("moderation_queue", term.backend().to_string());
    }

    // ── Snapshot 5: log popover ───────────────────────────────────────────────

    #[test]
    fn snapshot_log_popover() {
        let mut app = test_app();
        app.state.owner_jwt = Some("fake-jwt-for-test".into());
        app.state.log_popover = LogPopoverState::Open {
            container: "sastaspace-stdb".into(),
        };
        for i in 0..8 {
            app.push_log_line(LogLine {
                container: "sastaspace-stdb".into(),
                level: if i % 3 == 0 { "warn" } else { "info" }.into(),
                text: format!("Log line {i}: something happened in the module handler"),
                ts_micros: i * 1_000_000,
            });
        }
        let mut term = Terminal::new(TestBackend::new(W, H)).unwrap();
        term.draw(|f| {
            app.render(f, f.area());
        })
        .unwrap();
        insta::assert_snapshot!("log_popover", term.backend().to_string());
    }

    // ── Unit tests for state helpers ──────────────────────────────────────────

    #[test]
    fn move_flagged_selection_wraps() {
        let mut app = test_app();
        app.state.flagged = vec![
            FlaggedComment {
                id: 1,
                post_slug: "a".into(),
                author_name: "A".into(),
                body: "b".into(),
            },
            FlaggedComment {
                id: 2,
                post_slug: "b".into(),
                author_name: "B".into(),
                body: "c".into(),
            },
        ];
        app.state.flagged_selected = 0;
        app.state.move_flagged_selection(-1);
        assert_eq!(app.state.flagged_selected, 1, "should wrap to last");
        app.state.move_flagged_selection(1);
        assert_eq!(app.state.flagged_selected, 0, "should wrap to first");
    }

    #[test]
    fn move_flagged_selection_noop_when_empty() {
        let mut app = test_app();
        app.state.flagged_selected = 0;
        app.state.move_flagged_selection(1); // should not panic
    }

    #[test]
    fn log_lines_capped_at_500() {
        let mut app = test_app();
        for i in 0..600u64 {
            app.push_log_line(LogLine {
                container: "c".into(),
                level: "info".into(),
                text: format!("line {i}"),
                ts_micros: i as i64,
            });
        }
        assert_eq!(app.state.log_lines.len(), 500);
    }

    #[test]
    fn complete_device_flow_stores_jwt() {
        let store = Arc::new(InMemoryStore::new());
        let mut app = Admin::with_store(DeviceFlowConfig::for_client("cid"), store.clone());
        app.complete_device_flow("my-test-jwt".into());
        assert!(app.state.is_authenticated());
        assert_eq!(app.owner_jwt(), Some("my-test-jwt"));
        let stored = store.get(auth::keychain::TokenKind::OwnerJwt).unwrap();
        assert_eq!(stored, "my-test-jwt");
    }

    #[test]
    fn load_jwt_from_keychain_on_construction() {
        let store = Arc::new(InMemoryStore::new());
        store
            .set(auth::keychain::TokenKind::OwnerJwt, "pre-stored-jwt")
            .unwrap();
        let app = Admin::with_store(DeviceFlowConfig::for_client("cid"), store);
        assert!(app.state.is_authenticated());
        assert_eq!(app.owner_jwt(), Some("pre-stored-jwt"));
    }
}
