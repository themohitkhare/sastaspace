use auth::google_device::{poll, start, DeviceCode, DeviceFlowConfig, DeviceFlowError};
use std::time::Duration;
use wiremock::matchers::{body_string_contains, method, path};
use wiremock::{Mock, MockServer, ResponseTemplate};

fn cfg(server: &MockServer) -> DeviceFlowConfig {
    DeviceFlowConfig {
        client_id: "test-client".into(),
        device_url: format!("{}/device/code", server.uri()),
        token_url: format!("{}/token", server.uri()),
        poll_timeout: Duration::from_secs(2),
    }
}

#[tokio::test]
async fn start_returns_device_code() {
    let server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/device/code"))
        .respond_with(ResponseTemplate::new(200).set_body_string(
            r#"{"device_code":"D","user_code":"WDJB-MJHT","verification_url":"https://google.com/device","expires_in":600,"interval":1}"#,
        ))
        .mount(&server)
        .await;
    let dc = start(&cfg(&server)).await.unwrap();
    assert_eq!(dc.user_code, "WDJB-MJHT");
    assert_eq!(dc.interval, 1);
}

#[tokio::test]
async fn poll_returns_id_token_on_success() {
    let server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/token"))
        .and(body_string_contains("device_code=ABC"))
        .respond_with(ResponseTemplate::new(200).set_body_string(r#"{"id_token":"jwt-xyz"}"#))
        .mount(&server)
        .await;
    let dc = DeviceCode {
        device_code: "ABC".into(),
        user_code: "U".into(),
        verification_url: "u".into(),
        expires_in: 60,
        interval: 1,
    };
    let token = poll(&cfg(&server), &dc).await.unwrap();
    assert_eq!(token, "jwt-xyz");
}

#[tokio::test]
async fn poll_surfaces_denial() {
    let server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/token"))
        .respond_with(
            ResponseTemplate::new(400).set_body_string(r#"{"error":"access_denied"}"#),
        )
        .mount(&server)
        .await;
    let dc = DeviceCode {
        device_code: "ABC".into(),
        user_code: "U".into(),
        verification_url: "u".into(),
        expires_in: 60,
        interval: 1,
    };
    let err = poll(&cfg(&server), &dc).await.unwrap_err();
    assert!(matches!(err, DeviceFlowError::Denied));
}
