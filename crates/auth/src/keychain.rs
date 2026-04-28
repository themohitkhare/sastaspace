//! Wraps `keyring` so the rest of the workspace doesn't import it directly.
//! Lets us swap in a fake store for tests / CI without a real OS keychain.

use thiserror::Error;

pub const SERVICE: &str = "sastaspace";

/// Which token to load/store.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum TokenKind {
    /// Magic-link auth token — bearer for STDB connection.
    Auth,
    /// Google id_token JWT — owner identity for admin reducers.
    OwnerJwt,
}

impl TokenKind {
    fn account(self) -> &'static str {
        match self {
            TokenKind::Auth => "auth_token",
            TokenKind::OwnerJwt => "owner_id_token",
        }
    }
}

#[derive(Debug, Error)]
pub enum StoreError {
    #[error("keychain error: {0}")]
    Backend(String),
    #[error("no token stored for {0:?}")]
    Missing(TokenKind),
}

/// Generic storage interface. Apps depend on this trait, not on `keyring`.
pub trait TokenStore: Send + Sync {
    fn get(&self, kind: TokenKind) -> Result<String, StoreError>;
    fn set(&self, kind: TokenKind, token: &str) -> Result<(), StoreError>;
    fn clear(&self, kind: TokenKind) -> Result<(), StoreError>;
}

/// Production impl using the OS keychain.
pub struct KeychainStore;

impl KeychainStore {
    pub fn new() -> Self {
        Self
    }

    fn entry(kind: TokenKind) -> Result<keyring::Entry, StoreError> {
        keyring::Entry::new(SERVICE, kind.account())
            .map_err(|e| StoreError::Backend(e.to_string()))
    }
}

impl Default for KeychainStore {
    fn default() -> Self {
        Self::new()
    }
}

impl TokenStore for KeychainStore {
    fn get(&self, kind: TokenKind) -> Result<String, StoreError> {
        match Self::entry(kind)?.get_password() {
            Ok(s) => Ok(s),
            Err(keyring::Error::NoEntry) => Err(StoreError::Missing(kind)),
            Err(e) => Err(StoreError::Backend(e.to_string())),
        }
    }

    fn set(&self, kind: TokenKind, token: &str) -> Result<(), StoreError> {
        Self::entry(kind)?
            .set_password(token)
            .map_err(|e| StoreError::Backend(e.to_string()))
    }

    fn clear(&self, kind: TokenKind) -> Result<(), StoreError> {
        match Self::entry(kind)?.delete_credential() {
            Ok(()) => Ok(()),
            Err(keyring::Error::NoEntry) => Ok(()),
            Err(e) => Err(StoreError::Backend(e.to_string())),
        }
    }
}

/// In-memory store for tests + CI.
pub struct InMemoryStore {
    inner: std::sync::Mutex<std::collections::HashMap<TokenKind, String>>,
}

impl InMemoryStore {
    pub fn new() -> Self {
        Self { inner: std::sync::Mutex::new(Default::default()) }
    }
}

impl Default for InMemoryStore {
    fn default() -> Self {
        Self::new()
    }
}

impl TokenStore for InMemoryStore {
    fn get(&self, kind: TokenKind) -> Result<String, StoreError> {
        self.inner.lock().unwrap()
            .get(&kind)
            .cloned()
            .ok_or(StoreError::Missing(kind))
    }
    fn set(&self, kind: TokenKind, token: &str) -> Result<(), StoreError> {
        self.inner.lock().unwrap().insert(kind, token.to_string());
        Ok(())
    }
    fn clear(&self, kind: TokenKind) -> Result<(), StoreError> {
        self.inner.lock().unwrap().remove(&kind);
        Ok(())
    }
}
