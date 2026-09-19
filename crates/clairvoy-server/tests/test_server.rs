// crates/clairvoy-server/tests/test_server.rs
use axum_test::TestServer;
use clairvoy_server::{build_router, build_router_with_state, AppScanState, SharedScanState};
use serde_json::json;
use std::sync::{Arc, Mutex};

#[tokio::test]
async fn test_server_status_and_index() {
    let app = build_router();
    let server = TestServer::new(app).unwrap();

    let res_index = server.get("/").await;
    assert_eq!(res_index.status_code(), 200);
    assert!(res_index.text().contains("Clairvoy"));

    let res_status = server.get("/api/status").await;
    assert_eq!(res_status.status_code(), 200);
    assert!(res_status.text().contains("status"));
}

#[tokio::test]
async fn test_server_scan_endpoint() {
    let app = build_router();
    let server = TestServer::new(app).unwrap();

    let scan_payload = json!({
        "paths": ["/tmp/test_dir_1", "/tmp/test_dir_2"]
    });

    let res_scan = server.post("/api/scan").json(&scan_payload).await;
    assert_eq!(res_scan.status_code(), 200);
    let scan_body: serde_json::Value = res_scan.json();
    assert_eq!(scan_body["status"], "started");
    assert_eq!(scan_body["paths"].as_array().unwrap().len(), 2);

    let res_status = server.get("/api/status").await;
    assert_eq!(res_status.status_code(), 200);
    let status_body: serde_json::Value = res_status.json();
    assert_eq!(status_body["status"], "running");
    assert!(status_body["message"]
        .as_str()
        .unwrap()
        .contains("2 path(s)"));
}

#[tokio::test]
async fn test_server_runs_endpoint() {
    let app = build_router();
    let server = TestServer::new(app).unwrap();

    let res_runs = server.get("/api/runs").await;
    assert_eq!(res_runs.status_code(), 200);
    let runs_body: serde_json::Value = res_runs.json();
    assert!(runs_body.is_array());
}

#[tokio::test]
async fn test_custom_shared_state() {
    let custom_state: SharedScanState = Arc::new(Mutex::new(AppScanState {
        status: "custom_init".to_string(),
        stage: "Analysis".to_string(),
        progress_pct: 42,
        files_indexed: 100,
        elapsed_seconds: 5.5,
        message: "Custom state message".to_string(),
        summary: None,
        error: None,
    }));

    let app = build_router_with_state(custom_state);
    let server = TestServer::new(app).unwrap();

    let res_status = server.get("/api/status").await;
    assert_eq!(res_status.status_code(), 200);
    let status_body: serde_json::Value = res_status.json();
    assert_eq!(status_body["status"], "custom_init");
    assert_eq!(status_body["progress_pct"], 42);
    assert_eq!(status_body["files_indexed"], 100);
}
