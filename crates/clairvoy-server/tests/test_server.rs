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

    let dir1 = std::env::temp_dir().join("clairvoy_test_server_1");
    let dir2 = std::env::temp_dir().join("clairvoy_test_server_2");
    let _ = std::fs::create_dir_all(&dir1);
    let _ = std::fs::create_dir_all(&dir2);

    let scan_payload = json!({
        "paths": [dir1.to_string_lossy(), dir2.to_string_lossy()]
    });

    let res_scan = server.post("/api/scan").json(&scan_payload).await;
    assert_eq!(res_scan.status_code(), 200);
    let scan_body: serde_json::Value = res_scan.json();
    assert_eq!(scan_body["status"], "started");
    assert_eq!(scan_body["paths"].as_array().unwrap().len(), 2);

    let res_status = server.get("/api/status").await;
    assert_eq!(res_status.status_code(), 200);
    let status_body: serde_json::Value = res_status.json();
    let status = status_body["status"].as_str().unwrap();
    assert!(status == "running" || status == "completed");
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
async fn test_server_browse_directories() {
    let app = build_router();
    let server = TestServer::new(app).unwrap();

    let res = server.get("/api/system/browse-directories").await;
    assert_eq!(res.status_code(), 200);
    let body: serde_json::Value = res.json();
    assert!(body["current_path"].is_string());
    assert!(body["shortcuts"].is_array());
    assert!(body["directories"].is_array());

    // Test with specific query path
    let tmp_dir = std::env::temp_dir();
    let res_tmp = server
        .get(&format!(
            "/api/system/browse-directories?path={}",
            tmp_dir.to_string_lossy()
        ))
        .await;
    assert_eq!(res_tmp.status_code(), 200);
    let tmp_body: serde_json::Value = res_tmp.json();
    assert!(tmp_body["current_path"].is_string());

    // Test with nonexistent path falls back to home without crashing
    let res_nonexistent = server
        .get("/api/system/browse-directories?path=/path/that/does/not/exist_12345")
        .await;
    assert_eq!(res_nonexistent.status_code(), 200);
}

#[tokio::test]
async fn test_server_pick_folder() {
    let app = build_router();
    let server = TestServer::new(app).unwrap();

    let res = server.post("/api/system/pick-folder").await;
    assert_eq!(res.status_code(), 200);
    let body: serde_json::Value = res.json();
    assert_eq!(body["status"], "cancelled");
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

#[tokio::test]
async fn test_server_live_progress_state() {
    let app = build_router();
    let server = TestServer::new(app).unwrap();

    let res_status = server.get("/api/status").await;
    assert_eq!(res_status.status_code(), 200);
    let body: serde_json::Value = res_status.json();
    assert!(body["stage"].is_string());
    assert!(body["progress_pct"].is_number());
    assert!(body["files_indexed"].is_number());
    assert!(body["elapsed_seconds"].is_number());
}

