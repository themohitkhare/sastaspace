//! On-disk config — `~/.config/sastaspace/config.toml`.

use directories::ProjectDirs;
use serde::{Deserialize, Serialize};
use std::{fs, io, path::PathBuf};
use thiserror::Error;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(default, deny_unknown_fields)]
pub struct Config {
    /// Where to connect for SpacetimeDB. Override per-environment.
    pub stdb_uri: String,
    /// Module name on that STDB instance.
    pub stdb_module: String,
    /// Identity (Google client) for the owner OAuth device flow.
    pub google_client_id: Option<String>,
    /// Default starting screen when the binary launches.
    pub start_screen: String,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            stdb_uri: "wss://stdb.sastaspace.com".into(),
            stdb_module: "sastaspace".into(),
            google_client_id: None,
            start_screen: "portfolio".into(),
        }
    }
}

#[derive(Debug, Error)]
pub enum ConfigError {
    #[error("could not locate platform config directory")]
    NoConfigDir,
    #[error("io: {0}")]
    Io(#[from] io::Error),
    #[error("toml parse: {0}")]
    Parse(#[from] toml::de::Error),
    #[error("toml serialize: {0}")]
    Serialize(#[from] toml::ser::Error),
}

impl Config {
    /// `~/.config/sastaspace/config.toml` on linux/mac, `%APPDATA%\sastaspace\config.toml` on windows.
    pub fn path() -> Result<PathBuf, ConfigError> {
        let dirs =
            ProjectDirs::from("com", "sastaspace", "sastaspace").ok_or(ConfigError::NoConfigDir)?;
        Ok(dirs.config_dir().join("config.toml"))
    }

    /// Load the config; returns `Default` if the file doesn't exist yet.
    /// Honors env overrides `SASTASPACE_STDB_URI` and `SASTASPACE_STDB_MODULE`.
    pub fn load() -> Result<Self, ConfigError> {
        let p = Self::path()?;
        let mut c = if p.exists() {
            let s = fs::read_to_string(&p)?;
            toml::from_str::<Self>(&s)?
        } else {
            Self::default()
        };
        if let Ok(v) = std::env::var("SASTASPACE_STDB_URI") {
            c.stdb_uri = v;
        }
        if let Ok(v) = std::env::var("SASTASPACE_STDB_MODULE") {
            c.stdb_module = v;
        }
        Ok(c)
    }

    /// Write atomically (`config.toml.tmp` → rename). Creates the dir if needed.
    pub fn save(&self) -> Result<(), ConfigError> {
        let p = Self::path()?;
        if let Some(parent) = p.parent() {
            fs::create_dir_all(parent)?;
        }
        let body = toml::to_string_pretty(self)?;
        let tmp = p.with_extension("toml.tmp");
        fs::write(&tmp, body)?;
        fs::rename(tmp, p)?;
        Ok(())
    }

    /// Test-only: load from a specific path. Lets tests use a tempdir.
    #[doc(hidden)]
    pub fn load_from(path: &PathBuf) -> Result<Self, ConfigError> {
        if !path.exists() {
            return Ok(Self::default());
        }
        let s = fs::read_to_string(path)?;
        Ok(toml::from_str(&s)?)
    }

    /// Test-only counterpart to `load_from`.
    #[doc(hidden)]
    pub fn save_to(&self, path: &PathBuf) -> Result<(), ConfigError> {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        fs::write(path, toml::to_string_pretty(self)?)?;
        Ok(())
    }
}
