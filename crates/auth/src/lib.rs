//! sastaspace TUI auth: token storage + magic-link + Google device flow.

pub mod google_device;
pub mod keychain;
pub mod magic_link;

pub use keychain::{InMemoryStore, KeychainStore, StoreError, TokenKind, TokenStore};
