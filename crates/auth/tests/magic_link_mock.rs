use auth::magic_link::{request, verify, MagicLinkConfig, MagicLinkError};
use std::time::Duration;
use wiremock::matchers::{method, path};
use wiremock::{Mock, MockServer, ResponseTemplate};

fn cfg(server: &MockServer) -> MagicLinkConfig {
    MagicLinkConfig {
        stdb_http_base: server.uri(),
        module: "sastaspace".into(),
        http_timeout: Duration::from_secs(2),
    }
}

#[tokio::test]
async fn request_happy_path_calls_reducer() {
    let server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/v1/database/sastaspace/call/request_magic_link"))
        .respond_with(ResponseTemplate::new(200))
        .expect(1)
        .mount(&server)
        .await;

    request(&cfg(&server), "user@example.com").await.unwrap();
}

#[tokio::test]
async fn request_invalid_email_short_circuits() {
    let server = MockServer::start().await;
    // No mock — if the function tried to call the server it'd be a 404.
    let err = request(&cfg(&server), "no-at-sign").await.unwrap_err();
    assert!(matches!(err, MagicLinkError::InvalidEmail));
}

#[tokio::test]
async fn request_surfaces_reducer_error_body() {
    let server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/v1/database/sastaspace/call/request_magic_link"))
        .respond_with(ResponseTemplate::new(400).set_body_string(r#"{"error":"invalid email"}"#))
        .mount(&server)
        .await;
    let err = request(&cfg(&server), "user@example.com")
        .await
        .unwrap_err();
    match err {
        MagicLinkError::Reducer(m) => assert!(m.contains("invalid email")),
        other => panic!("expected Reducer error, got {other:?}"),
    }
}

#[tokio::test]
async fn verify_happy_path_returns_bearer() {
    let server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/v1/database/sastaspace/call/verify_token"))
        .respond_with(ResponseTemplate::new(200).set_body_string(r#"{"value":"bearer-xyz"}"#))
        .mount(&server)
        .await;
    let bearer = verify(&cfg(&server), "ABCDEFGH", "Mohit").await.unwrap();
    assert_eq!(bearer, "bearer-xyz");
}

#[tokio::test]
async fn verify_surfaces_4xx() {
    let server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/v1/database/sastaspace/call/verify_token"))
        .respond_with(ResponseTemplate::new(400).set_body_string("bad token"))
        .mount(&server)
        .await;
    let err = verify(&cfg(&server), "bad", "Mohit").await.unwrap_err();
    assert!(matches!(err, MagicLinkError::Verify(_)));
}
