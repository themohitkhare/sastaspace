use auth::keychain::{InMemoryStore, StoreError, TokenKind, TokenStore};

#[test]
fn in_memory_store_roundtrip() {
    let s = InMemoryStore::new();

    // Initially empty.
    assert!(matches!(
        s.get(TokenKind::Auth),
        Err(StoreError::Missing(_))
    ));

    // Set + get + clear.
    s.set(TokenKind::Auth, "abc123").unwrap();
    assert_eq!(s.get(TokenKind::Auth).unwrap(), "abc123");
    s.clear(TokenKind::Auth).unwrap();
    assert!(matches!(
        s.get(TokenKind::Auth),
        Err(StoreError::Missing(_))
    ));

    // Clearing a missing token is idempotent.
    s.clear(TokenKind::OwnerJwt).unwrap();
}

#[test]
fn token_kinds_use_distinct_accounts() {
    let s = InMemoryStore::new();
    s.set(TokenKind::Auth, "auth-tok").unwrap();
    s.set(TokenKind::OwnerJwt, "jwt-tok").unwrap();
    assert_eq!(s.get(TokenKind::Auth).unwrap(), "auth-tok");
    assert_eq!(s.get(TokenKind::OwnerJwt).unwrap(), "jwt-tok");
}
