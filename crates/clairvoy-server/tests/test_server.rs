// crates/clairvoy-server/tests/test_server.rs
use axum_test::TestServer;
use clairvoy_core::db::Database;
use clairvoy_engine::watcher::AutonomousWatcher;
use clairvoy_server::{
    build_router, build_router_with_services, build_router_with_state, AppScanState, SharedScanState,
};
use serde_json::json;
use std::sync::{Arc, Mutex};

#[tokio::test]
async fn test_server_status_and_index() {
    let app = build_router();
    let server = TestServer::new(app).unwrap();

    let res_index = server.get("/").await;
    assert_eq!(res_index.status_code(), 200);
    let index_html = res_index.text();
    assert!(index_html.contains("Clairvoy"));
    assert!(index_html.contains("Autonomous Watcher"));
    assert!(index_html.contains("renderWatcherSection"));
    assert!(index_html.contains("initStatusStream"));
    assert!(index_html.contains("addCurrentFolderToWatcher"));

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

#[tokio::test]
async fn test_server_watch_paths_crud() {
    let db = Arc::new(Mutex::new(Database::open_in_memory().unwrap()));
    let state: SharedScanState = Default::default();
    let app = build_router_with_services(state, Arc::clone(&db), None);
    let server = TestServer::new(app).unwrap();

    // 1. Initially empty
    let res = server.get("/api/watch/paths").await;
    assert_eq!(res.status_code(), 200);
    let list: Vec<serde_json::Value> = res.json();
    assert!(list.is_empty());

    // 2. Add a watched path
    let payload = json!({
        "path": "/tmp/clairvoy_test_watch_crud",
        "recursive": true
    });
    let res_add = server.post("/api/watch/paths").json(&payload).await;
    assert_eq!(res_add.status_code(), 200);
    let add_body: serde_json::Value = res_add.json();
    assert_eq!(add_body["status"], "watching");
    let id = add_body["id"].as_i64().unwrap();
    assert_eq!(add_body["path"], "/tmp/clairvoy_test_watch_crud");

    // 3. List contains the new path
    let res_list = server.get("/api/watch/paths").await;
    assert_eq!(res_list.status_code(), 200);
    let list: Vec<serde_json::Value> = res_list.json();
    assert_eq!(list.len(), 1);
    assert_eq!(list[0]["id"], id);
    assert_eq!(list[0]["path"], "/tmp/clairvoy_test_watch_crud");
    assert_eq!(list[0]["enabled"], true);

    // 4. Toggle to disabled explicitly
    let toggle_payload = json!({ "enabled": false });
    let res_toggle = server
        .post(&format!("/api/watch/paths/{}/toggle", id))
        .json(&toggle_payload)
        .await;
    assert_eq!(res_toggle.status_code(), 200);
    let toggle_body: serde_json::Value = res_toggle.json();
    assert_eq!(toggle_body["status"], "updated");
    assert_eq!(toggle_body["enabled"], false);

    // 5. Toggle without payload inverts status back to enabled
    let res_toggle2 = server
        .post(&format!("/api/watch/paths/{}/toggle", id))
        .await;
    assert_eq!(res_toggle2.status_code(), 200);
    let toggle_body2: serde_json::Value = res_toggle2.json();
    assert_eq!(toggle_body2["status"], "updated");
    assert_eq!(toggle_body2["enabled"], true);

    // 6. Delete path
    let res_delete = server.delete(&format!("/api/watch/paths/{}", id)).await;
    assert_eq!(res_delete.status_code(), 200);
    let del_body: serde_json::Value = res_delete.json();
    assert_eq!(del_body["status"], "deleted");

    // 7. Verify list is empty again
    let res_final = server.get("/api/watch/paths").await;
    assert_eq!(res_final.status_code(), 200);
    let list_final: Vec<serde_json::Value> = res_final.json();
    assert!(list_final.is_empty());
}

#[tokio::test]
async fn test_server_watch_daemon_toggle() {
    let db = Arc::new(Mutex::new(Database::open_in_memory().unwrap()));
    let state: SharedScanState = Default::default();

    // Test with no watcher attached (disabled)
    let app_no_watcher = build_router_with_services(Arc::clone(&state), Arc::clone(&db), None);
    let server_no_watcher = TestServer::new(app_no_watcher).unwrap();

    let res = server_no_watcher.post("/api/watch/daemon/toggle").await;
    assert_eq!(res.status_code(), 200);
    let body: serde_json::Value = res.json();
    assert_eq!(body["status"], "disabled");
    assert_eq!(body["active"], false);
    assert_eq!(body["paused"], true);

    // Test with active watcher attached
    let watcher = Arc::new(AutonomousWatcher::start(Arc::clone(&db), 100, 0).await.unwrap());
    let app_watcher = build_router_with_services(
        Arc::clone(&state),
        Arc::clone(&db),
        Some(Arc::clone(&watcher)),
    );
    let server_watcher = TestServer::new(app_watcher).unwrap();

    // 1. Explicit pause
    let res_pause = server_watcher
        .post("/api/watch/daemon/toggle")
        .json(&json!({ "action": "pause" }))
        .await;
    assert_eq!(res_pause.status_code(), 200);
    let body_pause: serde_json::Value = res_pause.json();
    assert_eq!(body_pause["status"], "ok");
    assert_eq!(body_pause["paused"], true);
    assert_eq!(body_pause["active"], true);
    assert!(watcher.is_paused());

    // 2. Explicit resume
    let res_resume = server_watcher
        .post("/api/watch/daemon/toggle")
        .json(&json!({ "action": "resume" }))
        .await;
    assert_eq!(res_resume.status_code(), 200);
    let body_resume: serde_json::Value = res_resume.json();
    assert_eq!(body_resume["status"], "ok");
    assert_eq!(body_resume["paused"], false);
    assert_eq!(body_resume["active"], true);
    assert!(!watcher.is_paused());

    // 3. Toggle (from active/false -> paused/true)
    let res_toggle = server_watcher.post("/api/watch/daemon/toggle").await;
    assert_eq!(res_toggle.status_code(), 200);
    let body_toggle: serde_json::Value = res_toggle.json();
    assert_eq!(body_toggle["status"], "ok");
    assert_eq!(body_toggle["paused"], true);
    assert!(watcher.is_paused());

    watcher.stop().await;
}

#[tokio::test]
async fn test_server_status_stream() {
    use http_body_util::BodyExt;
    use tower::ServiceExt;

    let app = build_router();
    let req = axum::http::Request::builder()
        .uri("/api/status/stream")
        .body(axum::body::Body::empty())
        .unwrap();

    let res = app.oneshot(req).await.unwrap();
    assert_eq!(res.status(), axum::http::StatusCode::OK);
    assert_eq!(
        res.headers().get("content-type").unwrap(),
        "text/event-stream"
    );

    let mut body = res.into_body();
    let frame = tokio::time::timeout(std::time::Duration::from_secs(3), body.frame())
        .await
        .expect("Timed out waiting for SSE frame")
        .expect("Expected frame from body")
        .expect("Frame error");

    let data = frame.into_data().expect("Expected data frame");
    let text = String::from_utf8_lossy(&data);
    assert!(text.contains("data:"));
    assert!(text.contains("status"));
}

#[tokio::test]
async fn test_server_duplicates_and_runs_sqlite() {
    let db = Arc::new(Mutex::new(Database::open_in_memory().unwrap()));
    let state: SharedScanState = Default::default();
    let app = build_router_with_services(state, Arc::clone(&db), None);
    let server = TestServer::new(app).unwrap();

    // 1. With empty DB, /api/duplicates returns empty array
    let res_empty = server.get("/api/duplicates").await;
    assert_eq!(res_empty.status_code(), 200);
    let list_empty: Vec<serde_json::Value> = res_empty.json();
    assert!(list_empty.is_empty());

    // 2. Insert a scan run with a duplicate cluster into SQLite
    let summary = clairvoy_core::models::ScanSummary {
        total_files_scanned: 5,
        total_duplicate_groups: 1,
        wasted_bytes: 2048,
        wasted_mb: 0.002,
        wasted_gb: 0.000002,
        duration_seconds: 0.25,
        scanned_paths: vec!["/tmp/test_dir".to_string()],
        groups: vec![
            clairvoy_core::models::DuplicateRecord {
                group_id: 1,
                match_type: clairvoy_core::models::MatchType::ExactHash,
                action: clairvoy_core::models::ActionType::Keep,
                category: clairvoy_core::models::ImageCategory::Photo,
                similarity_score: 1.0,
                similarity: "100%".to_string(),
                size_mb: 0.001,
                path: "/tmp/test_dir/photo1.jpg".to_string(),
                dimensions: Some("1920x1080".to_string()),
            },
            clairvoy_core::models::DuplicateRecord {
                group_id: 1,
                match_type: clairvoy_core::models::MatchType::ExactHash,
                action: clairvoy_core::models::ActionType::Duplicate,
                category: clairvoy_core::models::ImageCategory::Photo,
                similarity_score: 1.0,
                similarity: "100%".to_string(),
                size_mb: 0.001,
                path: "/tmp/test_dir/photo2.jpg".to_string(),
                dimensions: Some("1920x1080".to_string()),
            },
        ],
        ..Default::default()
    };

    db.lock()
        .unwrap()
        .save_scan_run("run_sqlite_test", &summary)
        .unwrap();

    // 3. /api/runs queries SQLite and returns the run
    let res_runs = server.get("/api/runs").await;
    assert_eq!(res_runs.status_code(), 200);
    let runs_body: Vec<serde_json::Value> = res_runs.json();
    assert_eq!(runs_body.len(), 1);
    assert_eq!(runs_body[0]["run_id"], "run_sqlite_test");
    assert_eq!(runs_body[0]["total_files"], 5);

    // 4. /api/duplicates queries by run_id
    let res_dup = server
        .get("/api/duplicates?run_id=run_sqlite_test")
        .await;
    assert_eq!(res_dup.status_code(), 200);
    let clusters: Vec<serde_json::Value> = res_dup.json();
    assert_eq!(clusters.len(), 1);
    assert_eq!(clusters[0]["cluster_id"], 1);
    assert_eq!(clusters[0]["category"], "PHOTO");
    assert_eq!(clusters[0]["items"].as_array().unwrap().len(), 2);

    // 5. /api/duplicates without run_id resolves to the latest run
    let res_dup_latest = server.get("/api/duplicates").await;
    assert_eq!(res_dup_latest.status_code(), 200);
    let clusters_latest: Vec<serde_json::Value> = res_dup_latest.json();
    assert_eq!(clusters_latest.len(), 1);
    assert_eq!(clusters_latest[0]["cluster_id"], 1);
}
