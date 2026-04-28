use core::config::Config;
use tempfile::tempdir;

#[test]
fn default_config_has_prod_stdb() {
    let c = Config::default();
    assert_eq!(c.stdb_uri, "wss://stdb.sastaspace.com");
    assert_eq!(c.stdb_module, "sastaspace");
    assert_eq!(c.start_screen, "portfolio");
    assert!(c.google_client_id.is_none());
}

#[test]
fn save_then_load_roundtrips() {
    let dir = tempdir().unwrap();
    let path = dir.path().join("config.toml");

    let mut c = Config::default();
    c.google_client_id = Some("test-client.apps.googleusercontent.com".into());
    c.start_screen = "typewars".into();
    c.save_to(&path).unwrap();

    let loaded = Config::load_from(&path).unwrap();
    assert_eq!(loaded, c);
}

#[test]
fn load_missing_file_returns_default() {
    let dir = tempdir().unwrap();
    let path = dir.path().join("does-not-exist.toml");
    let c = Config::load_from(&path).unwrap();
    assert_eq!(c, Config::default());
}
