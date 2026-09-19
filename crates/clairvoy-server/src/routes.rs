use crate::state::{AppScanState, ServerState, SharedScanState};
use axum::body::Body;
use axum::extract::{Path as AxumPath, Query, State};
use axum::http::{header, StatusCode};
use axum::response::{
    sse::{Event, KeepAlive, Sse},
    Html, Json, Response,
};
use axum::routing::{delete, get, post};
use axum::Router;
use clairvoy_core::db::{Database, DuplicateClusterRecord, WatchedPathRecord};
use clairvoy_engine::watcher::AutonomousWatcher;
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::convert::Infallible;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use std::time::Duration;
use tokio_stream::Stream;
use tower_http::cors::CorsLayer;

static INDEX_HTML: &str = include_str!("index.html");

#[derive(Debug, Clone, Deserialize)]
pub struct ScanPayload {
    #[serde(default)]
    pub paths: Option<Vec<String>>,
    #[serde(default)]
    pub directory: Option<String>,
    #[serde(default)]
    pub enable_ml: Option<bool>,
    #[serde(default)]
    pub threshold: Option<f64>,
}

#[derive(Debug, Deserialize)]
pub struct BrowseQuery {
    pub path: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct SystemShortcut {
    pub name: String,
    pub path: String,
    pub icon: String,
}

#[derive(Debug, Serialize)]
pub struct DirectoryItem {
    pub name: String,
    pub path: String,
    pub has_children: bool,
}

#[derive(Debug, Serialize)]
pub struct BrowseResponse {
    pub current_path: String,
    pub parent_path: Option<String>,
    pub shortcuts: Vec<SystemShortcut>,
    pub directories: Vec<DirectoryItem>,
}

#[derive(Debug, Serialize)]
pub struct PickFolderResponse {
    pub status: String,
    pub path: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct RunsQuery {
    pub limit: Option<usize>,
}

#[derive(Debug, Deserialize)]
pub struct LoadRunRequest {
    pub run_id: Option<String>,
    pub path: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct MediaPathQuery {
    pub path: String,
}

#[derive(Debug, Deserialize)]
pub struct OverrideKeeperRequest {
    pub group_id: usize,
    pub new_keeper_path: String,
}

#[derive(Debug, Deserialize)]
pub struct DeleteRequest {
    pub paths: Vec<String>,
    pub base_dir: Option<String>,
    #[serde(default = "default_trash_mode")]
    pub mode: String,
}

fn default_trash_mode() -> String {
    "trash".to_string()
}

#[derive(Debug, Deserialize)]
pub struct QuarantineRequest {
    pub summary_file: Option<String>,
    pub base_dir: Option<String>,
    pub dry_run: Option<bool>,
}

#[derive(Debug, Deserialize)]
pub struct DeleteScriptQuery {
    pub mode: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct WatchPathPayload {
    pub path: String,
    pub recursive: Option<bool>,
}

#[derive(Debug, Default, Deserialize)]
pub struct WatchTogglePayload {
    pub enabled: Option<bool>,
}

#[derive(Debug, Default, Deserialize)]
pub struct DaemonTogglePayload {
    pub action: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct DuplicatesQuery {
    pub run_id: Option<String>,
    pub category: Option<String>,
    pub offset: Option<usize>,
    pub limit: Option<usize>,
}

fn get_mime_type(path: &Path) -> &'static str {
    match path
        .extension()
        .and_then(|e| e.to_str())
        .map(|e| e.to_ascii_lowercase())
        .as_deref()
    {
        Some("jpg") | Some("jpeg") => "image/jpeg",
        Some("png") => "image/png",
        Some("webp") => "image/webp",
        Some("gif") => "image/gif",
        Some("bmp") => "image/bmp",
        Some("svg") => "image/svg+xml",
        Some("mp4") => "video/mp4",
        Some("webm") => "video/webm",
        Some("mov") => "video/quicktime",
        Some("mkv") => "video/x-matroska",
        Some("pdf") => "application/pdf",
        Some("csv") => "text/csv",
        Some("sh") => "application/x-sh",
        _ => "application/octet-stream",
    }
}

fn get_system_shortcuts(home: &Path) -> Vec<SystemShortcut> {
    let mut shortcuts = Vec::new();
    shortcuts.push(SystemShortcut {
        name: "Home Directory".to_string(),
        path: home.to_string_lossy().to_string(),
        icon: "🏠".to_string(),
    });

    for (label, icon, sub_name) in [
        ("Pictures", "📸", "Pictures"),
        ("Videos", "🎬", "Videos"),
        ("Downloads", "📥", "Downloads"),
        ("Documents", "📄", "Documents"),
    ] {
        let sub = home.join(sub_name);
        if sub.is_dir() {
            shortcuts.push(SystemShortcut {
                name: label.to_string(),
                path: sub.to_string_lossy().to_string(),
                icon: icon.to_string(),
            });
        }
    }

    if let Ok(cwd) = std::env::current_dir() {
        shortcuts.push(SystemShortcut {
            name: "Current Workspace".to_string(),
            path: cwd.to_string_lossy().to_string(),
            icon: "💻".to_string(),
        });
    }

    for mount_root in ["/mnt", "/media", "/Volumes"] {
        let mp = Path::new(mount_root);
        if mp.is_dir() {
            if let Ok(entries) = std::fs::read_dir(mp) {
                for entry in entries.flatten() {
                    if let Ok(ft) = entry.file_type() {
                        if ft.is_dir() {
                            let name = entry.file_name().to_string_lossy().to_string();
                            if !name.starts_with('.') {
                                shortcuts.push(SystemShortcut {
                                    name: format!("Drive: {}", name),
                                    path: entry.path().to_string_lossy().to_string(),
                                    icon: "💾".to_string(),
                                });
                            }
                        }
                    }
                }
            }
        }
    }

    shortcuts.push(SystemShortcut {
        name: "Filesystem Root (/)".to_string(),
        path: "/".to_string(),
        icon: "🗄️".to_string(),
    });

    shortcuts
}

pub async fn handle_index() -> Html<&'static str> {
    Html(INDEX_HTML)
}

pub async fn handle_status(State(state): State<ServerState>) -> Json<AppScanState> {
    let mut s = state.scan_state.lock().unwrap().clone();
    if s.status == "idle" || s.status == "completed" {
        if let Ok(db_guard) = state.db.lock() {
            if let Ok(runs) = db_guard.list_scan_runs(1) {
                if let Some(latest) = runs.into_iter().next() {
                    let should_update = match &s.run_id {
                        Some(current_run) => current_run != &latest.run_id,
                        None => s.summary.is_none(),
                    };
                    if should_update {
                        let wasted_mb = latest.wasted_bytes as f64 / 1_048_576.0;
                        let wasted_gb = latest.wasted_bytes as f64 / 1_073_741_824.0;
                        s.run_id = Some(latest.run_id.clone());
                        s.wasted_bytes = latest.wasted_bytes;
                        s.wasted_mb = wasted_mb;
                        s.wasted_gb = wasted_gb;
                        s.files_indexed = latest.total_files;
                        s.status = "completed".to_string();
                        s.stage = "Database updated".to_string();
                        s.message = format!(
                            "Latest scan: {} duplicate groups ({:.2} MB / {:.3} GB recoverable)",
                            latest.duplicate_groups, wasted_mb, wasted_gb
                        );
                        if let Ok(Some(summary)) = db_guard.get_scan_summary(&latest.run_id) {
                            s.summary = Some(summary);
                        }
                        if let Ok(mut guard) = state.scan_state.lock() {
                            *guard = s.clone();
                        }
                    }
                }
            }
        }
    }
    Json(s)
}

pub async fn handle_status_stream(
    State(state): State<ServerState>,
) -> Sse<impl Stream<Item = Result<Event, Infallible>>> {
    let stream = async_stream::stream! {
        let mut interval = tokio::time::interval(Duration::from_millis(500));
        let mut last_seen_run_id: Option<String> = None;
        loop {
            interval.tick().await;
            let mut current_state = {
                let s = state.scan_state.lock().unwrap();
                s.clone()
            };

            // If idle or summary is missing, check if a new scan run was saved to SQLite!
            if current_state.status == "idle" || current_state.status == "completed" {
                if let Ok(db_guard) = state.db.lock() {
                    if let Ok(runs) = db_guard.list_scan_runs(1) {
                        if let Some(latest) = runs.into_iter().next() {
                            let is_new_run = match (&last_seen_run_id, &current_state.run_id) {
                                (Some(last), _) => last != &latest.run_id,
                                (None, Some(active_run)) => active_run != &latest.run_id,
                                (None, None) => current_state.summary.is_none(),
                            };
                            if is_new_run {
                                let wasted_mb = latest.wasted_bytes as f64 / 1_048_576.0;
                                let wasted_gb = latest.wasted_bytes as f64 / 1_073_741_824.0;
                                last_seen_run_id = Some(latest.run_id.clone());
                                current_state.run_id = Some(latest.run_id.clone());
                                current_state.wasted_bytes = latest.wasted_bytes;
                                current_state.wasted_mb = wasted_mb;
                                current_state.wasted_gb = wasted_gb;
                                current_state.files_indexed = latest.total_files;
                                current_state.status = "completed".to_string();
                                current_state.stage = "Database updated".to_string();
                                current_state.message = format!(
                                    "Database updated: {} duplicate groups ({:.2} MB / {:.3} GB recoverable)",
                                    latest.duplicate_groups, wasted_mb, wasted_gb
                                );
                                if let Ok(Some(summary)) = db_guard.get_scan_summary(&latest.run_id) {
                                    current_state.summary = Some(summary);
                                }
                                if let Ok(mut guard) = state.scan_state.lock() {
                                    *guard = current_state.clone();
                                }
                            }
                        }
                    }
                }
            }

            if let Ok(json_str) = serde_json::to_string(&current_state) {
                yield Ok(Event::default().data(json_str));
            }
        }
    };

    Sse::new(stream).keep_alive(KeepAlive::default())
}

pub async fn handle_scan(
    State(state): State<ServerState>,
    Json(payload): Json<ScanPayload>,
) -> Json<serde_json::Value> {
    let paths: Vec<PathBuf> = if let Some(ref p_list) = payload.paths {
        p_list.iter().map(PathBuf::from).collect()
    } else if let Some(ref dir) = payload.directory {
        vec![PathBuf::from(dir)]
    } else {
        vec![]
    };

    if paths.is_empty() {
        return Json(serde_json::json!({ "status": "error", "message": "No paths provided" }));
    }

    let paths_strings: Vec<String> = paths.iter().map(|p| p.to_string_lossy().to_string()).collect();

    {
        let mut s = state.scan_state.lock().unwrap();
        s.status = "running".to_string();
        s.stage = "Initializing scan".to_string();
        s.progress_pct = 0;
        s.files_indexed = 0;
        s.elapsed_seconds = 0.0;
        s.run_id = None;
        s.wasted_bytes = 0;
        s.wasted_mb = 0.0;
        s.wasted_gb = 0.0;
        s.message = format!("Scanning {} path(s)", paths.len());
        s.error = None;
    }

    let state_clone = Arc::clone(&state.scan_state);
    let db_clone = Arc::clone(&state.db);
    let paths_clone = paths.clone();

    tokio::task::spawn_blocking(move || {
        let mut pipeline = clairvoy_engine::DeduplicationPipeline::new(paths_clone);
        pipeline.register_matcher(Arc::new(clairvoy_plugins::ExactHashMatcherPlugin::new()));

        let state_progress = Arc::clone(&state_clone);
        let start_time = std::time::Instant::now();
        let run_res = pipeline.run(move |stage, cur, tot| {
            if let Ok(mut s) = state_progress.lock() {
                s.stage = stage.to_string();
                s.elapsed_seconds = start_time.elapsed().as_secs_f64();
                s.progress_pct = if tot > 0 {
                    ((cur as f64 / tot as f64) * 100.0).min(100.0) as u32
                } else {
                    0
                };
                if stage.contains("Crawling") || stage.contains("Filesystem") {
                    s.files_indexed = cur;
                }
            }
        });

        match run_res {
            Ok(summary) => {
                let run_id = format!(
                    "run_{}",
                    std::time::SystemTime::now()
                        .duration_since(std::time::UNIX_EPOCH)
                        .unwrap_or_default()
                        .as_micros()
                );
                if let Ok(db_guard) = db_clone.lock() {
                    let _ = db_guard.save_scan_run(&run_id, &summary);
                }
                if let Ok(mut s) = state_clone.lock() {
                    s.status = "completed".to_string();
                    s.stage = "Scan completed".to_string();
                    s.progress_pct = 100;
                    s.files_indexed = summary.total_files_scanned;
                    s.elapsed_seconds = summary.duration_seconds;
                    s.run_id = Some(run_id.clone());
                    s.wasted_bytes = summary.wasted_bytes;
                    s.wasted_mb = summary.wasted_mb;
                    s.wasted_gb = summary.wasted_gb;
                    s.message = format!(
                        "Scan completed: {} duplicate groups ({:.2} MB / {:.3} GB recoverable)",
                        summary.total_duplicate_groups, summary.wasted_mb, summary.wasted_gb
                    );
                    s.summary = Some(summary);
                    s.error = None;
                }
            }
            Err(e) => {
                if let Ok(mut s) = state_clone.lock() {
                    s.status = "failed".to_string();
                    s.stage = "Scan failed".to_string();
                    s.error = Some(e.to_string());
                    s.message = format!("Scan failed: {}", e);
                }
            }
        }
    });

    Json(serde_json::json!({ "status": "started", "paths": paths_strings }))
}

pub async fn handle_runs(
    State(state): State<ServerState>,
    Query(query): Query<RunsQuery>,
) -> Json<serde_json::Value> {
    let limit = query.limit.unwrap_or(50);
    if let Ok(db_guard) = state.db.lock() {
        if let Ok(runs) = db_guard.list_scan_runs(limit) {
            if !runs.is_empty() {
                return Json(serde_json::to_value(runs).unwrap_or_else(|_| serde_json::json!([])));
            }
        }
    }

    let home = std::env::var("HOME")
        .or_else(|_| std::env::var("USERPROFILE"))
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("."));

    let history_file = home.join(".clairvoy").join("runs.json");
    if history_file.is_file() {
        if let Ok(content) = std::fs::read_to_string(&history_file) {
            if let Ok(mut json_arr) = serde_json::from_str::<Vec<serde_json::Value>>(&content) {
                if json_arr.len() > limit {
                    json_arr.truncate(limit);
                }
                return Json(serde_json::Value::Array(json_arr));
            }
        }
    }
    Json(serde_json::json!([]))
}

pub async fn handle_runs_load(
    State(state): State<ServerState>,
    Json(payload): Json<LoadRunRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    if let Some(ref run_id) = payload.run_id {
        if let Ok(db_guard) = state.db.lock() {
            if let Ok(Some(summary)) = db_guard.get_scan_summary(run_id) {
                let mut s = state.scan_state.lock().unwrap();
                s.status = "completed".to_string();
                s.stage = "Scan summary loaded".to_string();
                s.progress_pct = 100;
                s.files_indexed = summary.total_files_scanned;
                s.elapsed_seconds = summary.duration_seconds;
                s.run_id = Some(run_id.clone());
                s.wasted_bytes = summary.wasted_bytes;
                s.wasted_mb = summary.wasted_mb;
                s.wasted_gb = summary.wasted_gb;
                s.message = format!(
                    "Loaded scan summary ({} duplicate groups, {:.2} GB recoverable)",
                    summary.total_duplicate_groups, summary.wasted_gb
                );
                s.summary = Some(summary.clone());
                s.error = None;
                return Ok(Json(serde_json::json!({ "status": "loaded", "summary": summary })));
            }
        }
    }

    let summary_path: Option<PathBuf> = if let Some(ref p) = payload.path {
        Some(PathBuf::from(p))
    } else if let Some(ref run_id) = payload.run_id {
        let home = std::env::var("HOME")
            .or_else(|_| std::env::var("USERPROFILE"))
            .map(PathBuf::from)
            .unwrap_or_else(|_| PathBuf::from("."));
        let history_file = home.join(".clairvoy").join("runs.json");
        if history_file.is_file() {
            if let Ok(content) = std::fs::read_to_string(&history_file) {
                if let Ok(runs) = serde_json::from_str::<Vec<serde_json::Value>>(&content) {
                    runs.iter()
                        .find(|r| r.get("run_id").and_then(|id| id.as_str()) == Some(run_id.as_str()))
                        .and_then(|r| r.get("summary_json").and_then(|s| s.as_str()))
                        .map(PathBuf::from)
                } else {
                    None
                }
            } else {
                None
            }
        } else {
            None
        }
    } else {
        None
    };

    let path_to_load = summary_path.ok_or_else(|| {
        (
            StatusCode::NOT_FOUND,
            Json(serde_json::json!({ "status": "error", "message": "Run or path not found" })),
        )
    })?;

    if !path_to_load.is_file() {
        return Err((
            StatusCode::NOT_FOUND,
            Json(serde_json::json!({
                "status": "error",
                "message": format!("Summary file '{}' not found", path_to_load.display())
            })),
        ));
    }

    let file_content = std::fs::read_to_string(&path_to_load).map_err(|e| {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(serde_json::json!({ "status": "error", "message": e.to_string() })),
        )
    })?;

    let summary: clairvoy_core::models::ScanSummary = serde_json::from_str(&file_content).map_err(|e| {
        (
            StatusCode::BAD_REQUEST,
            Json(serde_json::json!({
                "status": "error",
                "message": format!("Invalid summary schema: {}", e)
            })),
        )
    })?;

    {
        let mut s = state.scan_state.lock().unwrap();
        s.status = "completed".to_string();
        s.stage = "Scan summary loaded".to_string();
        s.progress_pct = 100;
        s.files_indexed = summary.total_files_scanned;
        s.elapsed_seconds = summary.duration_seconds;
        s.message = format!(
            "Loaded scan summary ({} duplicate groups, {:.2} GB recoverable)",
            summary.total_duplicate_groups, summary.wasted_gb
        );
        s.summary = Some(summary.clone());
        s.error = None;
    }

    Ok(Json(serde_json::json!({ "status": "loaded", "summary": summary })))
}

pub async fn handle_duplicates(
    State(state): State<ServerState>,
    Query(query): Query<DuplicatesQuery>,
) -> Result<Json<Vec<DuplicateClusterRecord>>, (StatusCode, String)> {
    let db = state
        .db
        .lock()
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    let run_id = match query.run_id {
        Some(id) => id,
        None => {
            let latest = db
                .list_scan_runs(1)
                .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
            match latest.into_iter().next() {
                Some(r) => r.run_id,
                None => return Ok(Json(Vec::new())),
            }
        }
    };
    let offset = query.offset.unwrap_or(0);
    let limit = query.limit.unwrap_or(50);
    let category = query.category.as_deref();

    let clusters = db
        .get_duplicate_clusters(&run_id, category, offset, limit)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    Ok(Json(clusters))
}

pub async fn handle_watch_paths_list(
    State(state): State<ServerState>,
) -> Result<Json<Vec<WatchedPathRecord>>, (StatusCode, String)> {
    let db = state
        .db
        .lock()
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    let paths = db
        .list_watched_paths()
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    Ok(Json(paths))
}

pub async fn handle_watch_paths_add(
    State(state): State<ServerState>,
    Json(payload): Json<WatchPathPayload>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let db = state
        .db
        .lock()
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    let id = db
        .add_watched_path(&payload.path, payload.recursive.unwrap_or(true))
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    drop(db);

    {
        let mut s = state.scan_state.lock().unwrap();
        s.status = "running".to_string();
        s.stage = format!("Initial baseline surveillance scan for '{}'...", payload.path);
        s.progress_pct = 0;
        s.files_indexed = 0;
        s.elapsed_seconds = 0.0;
        s.message = format!("Baseline indexing: {}", payload.path);
        s.error = None;
    }

    if let Some(ref watcher) = state.watcher {
        let _ = watcher.trigger_scan_now();
    }

    Ok(Json(serde_json::json!({
        "status": "watching",
        "id": id,
        "path": payload.path,
    })))
}

pub async fn handle_watch_paths_toggle(
    State(state): State<ServerState>,
    AxumPath(id): AxumPath<i64>,
    payload: Option<Json<WatchTogglePayload>>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let db = state
        .db
        .lock()
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    let explicit_enabled = payload.and_then(|Json(p)| p.enabled);
    let paths = db
        .list_watched_paths()
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    let record = paths
        .into_iter()
        .find(|p| p.id == id)
        .ok_or_else(|| (StatusCode::NOT_FOUND, format!("Watched path {} not found", id)))?;

    let new_enabled = explicit_enabled.unwrap_or(!record.enabled);
    db.toggle_watched_path(id, new_enabled)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    drop(db);

    if let Some(ref watcher) = state.watcher {
        let _ = watcher.trigger_scan_now();
    }

    Ok(Json(serde_json::json!({
        "status": "updated",
        "id": id,
        "enabled": new_enabled,
    })))
}

pub async fn handle_watch_paths_delete(
    State(state): State<ServerState>,
    AxumPath(id): AxumPath<i64>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let db = state
        .db
        .lock()
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    db.remove_watched_path(id)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    Ok(Json(serde_json::json!({ "status": "deleted", "id": id })))
}

pub async fn handle_watch_daemon_toggle(
    State(state): State<ServerState>,
    payload: Option<Json<DaemonTogglePayload>>,
) -> Json<serde_json::Value> {
    if let Some(ref watcher) = state.watcher {
        let action = payload
            .and_then(|Json(p)| p.action)
            .unwrap_or_else(|| "toggle".to_string());

        match action.to_lowercase().as_str() {
            "pause" => watcher.pause(),
            "resume" => watcher.resume(),
            _ => {
                if watcher.is_paused() {
                    watcher.resume();
                } else {
                    watcher.pause();
                }
            }
        }
        let is_paused = watcher.is_paused();
        Json(serde_json::json!({
            "status": "ok",
            "paused": is_paused,
            "active": true,
        }))
    } else {
        Json(serde_json::json!({
            "status": "disabled",
            "paused": true,
            "active": false,
        }))
    }
}

pub async fn handle_browse_directories(
    Query(query): Query<BrowseQuery>,
) -> Json<BrowseResponse> {
    let home = std::env::var("HOME")
        .or_else(|_| std::env::var("USERPROFILE"))
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("/"));

    let target_path = match query.path {
        Some(ref p) if !p.trim().is_empty() => {
            let pb = PathBuf::from(p.trim());
            if pb.is_dir() {
                pb.canonicalize().unwrap_or(pb)
            } else {
                home.clone()
            }
        }
        _ => home.clone(),
    };

    let shortcuts = get_system_shortcuts(&home);
    let mut directories = Vec::new();

    if let Ok(entries) = std::fs::read_dir(&target_path) {
        for entry in entries.flatten() {
            if let Ok(ft) = entry.file_type() {
                if ft.is_dir() {
                    let name = entry.file_name().to_string_lossy().to_string();
                    if !name.starts_with('.') {
                        let path = entry.path();
                        let has_children = std::fs::read_dir(&path)
                            .map(|mut r| {
                                r.any(|e| {
                                    e.map(|sub| sub.file_type().map(|st| st.is_dir()).unwrap_or(false))
                                        .unwrap_or(false)
                                })
                            })
                            .unwrap_or(false);

                        directories.push(DirectoryItem {
                            name,
                            path: path.to_string_lossy().to_string(),
                            has_children,
                        });
                    }
                }
            }
        }
    }

    directories.sort_by_key(|a| a.name.to_lowercase());
    if directories.len() > 300 {
        directories.truncate(300);
    }

    let parent_path = target_path.parent().map(|p| p.to_string_lossy().to_string());

    Json(BrowseResponse {
        current_path: target_path.to_string_lossy().to_string(),
        parent_path,
        shortcuts,
        directories,
    })
}

pub async fn handle_pick_folder() -> Json<PickFolderResponse> {
    Json(PickFolderResponse {
        status: "cancelled".to_string(),
        path: None,
    })
}

pub async fn handle_thumbnail_or_media(
    Query(query): Query<MediaPathQuery>,
) -> Result<Response, (StatusCode, &'static str)> {
    let path = Path::new(&query.path);
    if !path.is_file() {
        return Err((StatusCode::NOT_FOUND, "File not found"));
    }

    let bytes = tokio::fs::read(path)
        .await
        .map_err(|_| (StatusCode::FORBIDDEN, "Cannot read file"))?;
    let mime = get_mime_type(path);

    Response::builder()
        .header(header::CONTENT_TYPE, mime)
        .header(header::CACHE_CONTROL, "public, max-age=86400")
        .body(Body::from(bytes))
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, "Failed to build response"))
}

pub async fn handle_override_keeper(
    State(state): State<ServerState>,
    Json(payload): Json<OverrideKeeperRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, &'static str)> {
    let mut s = state.scan_state.lock().unwrap();
    if let Some(ref mut summary) = s.summary {
        let mut cluster_found = false;
        let mut target_found = false;
        for record in &mut summary.groups {
            if record.group_id == payload.group_id {
                cluster_found = true;
                if record.path == payload.new_keeper_path {
                    record.action = clairvoy_core::models::ActionType::Keep;
                    target_found = true;
                } else {
                    record.action = clairvoy_core::models::ActionType::Duplicate;
                }
            }
        }
        if !cluster_found {
            return Err((StatusCode::NOT_FOUND, "Cluster not found"));
        }
        if !target_found {
            return Err((StatusCode::NOT_FOUND, "Keeper path not found in cluster"));
        }
        Ok(Json(serde_json::json!({
            "status": "updated",
            "group_id": payload.group_id,
            "new_keeper": payload.new_keeper_path
        })))
    } else {
        Err((StatusCode::BAD_REQUEST, "No active scan summary available"))
    }
}

pub async fn handle_delete_execute(
    State(state): State<ServerState>,
    Json(payload): Json<DeleteRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    let mut deleted_count = 0;
    let mut freed_bytes: u64 = 0;
    let mut deleted_paths = HashSet::new();

    let is_hardlink = payload.mode == "hardlink";
    let trash_dir = if payload.mode == "trash" {
        let base = payload.base_dir.clone().unwrap_or_else(|| ".".to_string());
        let t_dir = PathBuf::from(base).join(".clairvoy_trash");
        let _ = std::fs::create_dir_all(&t_dir);
        Some(t_dir)
    } else {
        None
    };

    let keeper_map: HashMap<String, String> = if is_hardlink {
        let s = state.scan_state.lock().unwrap();
        if let Some(ref summary) = s.summary {
            let mut group_to_keeper = HashMap::new();
            for g in &summary.groups {
                if g.action == clairvoy_core::models::ActionType::Keep {
                    group_to_keeper.insert(g.group_id, g.path.clone());
                }
            }
            let mut map = HashMap::new();
            for g in &summary.groups {
                if g.action == clairvoy_core::models::ActionType::Duplicate {
                    if let Some(k_path) = group_to_keeper.get(&g.group_id) {
                        map.insert(g.path.clone(), k_path.clone());
                    }
                }
            }
            map
        } else {
            HashMap::new()
        }
    } else {
        HashMap::new()
    };

    for path_str in &payload.paths {
        let p = Path::new(path_str);
        if p.is_file() {
            let size = p.metadata().map(|m| m.len()).unwrap_or(0);
            let success = if let Some(ref t_dir) = trash_dir {
                let file_name = p.file_name().unwrap_or_default();
                let dst = t_dir.join(file_name);
                std::fs::rename(p, dst).is_ok()
            } else if is_hardlink {
                if let Some(keeper_str) = keeper_map.get(path_str) {
                    let keeper = Path::new(keeper_str);
                    if keeper.is_file() && keeper != p {
                        let temp_name = format!("{}.clairvoy_hl_tmp", path_str);
                        let temp_p = Path::new(&temp_name);
                        let _ = std::fs::remove_file(temp_p);
                        if std::fs::hard_link(keeper, temp_p).is_ok() {
                            std::fs::rename(temp_p, p).is_ok()
                        } else {
                            false
                        }
                    } else {
                        false
                    }
                } else {
                    false
                }
            } else {
                std::fs::remove_file(p).is_ok()
            };

            if success {
                deleted_count += 1;
                freed_bytes += size;
                deleted_paths.insert(path_str.clone());
            }
        }
    }

    {
        let mut s = state.scan_state.lock().unwrap();
        if let Some(ref mut summary) = s.summary {
            summary.groups.retain(|g| !deleted_paths.contains(&g.path));
            summary.wasted_bytes = summary.wasted_bytes.saturating_sub(freed_bytes);
            summary.wasted_mb = (summary.wasted_bytes as f64) / (1024.0 * 1024.0);
            summary.wasted_gb = summary.wasted_mb / 1024.0;
        }
    }

    Ok(Json(serde_json::json!({
        "status": "success",
        "total_files_freed": deleted_count,
        "total_bytes_freed": freed_bytes,
        "mode": payload.mode,
    })))
}

pub async fn handle_quarantine_execute(
    State(state): State<ServerState>,
    Json(payload): Json<QuarantineRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<serde_json::Value>)> {
    let s = state.scan_state.lock().unwrap();
    let summary = match s.summary {
        Some(ref sm) => sm.clone(),
        None => {
            return Err((
                StatusCode::BAD_REQUEST,
                Json(serde_json::json!({
                    "status": "error",
                    "message": "No active scan summary available."
                })),
            ));
        }
    };
    drop(s);

    let base_dir = payload
        .base_dir
        .or_else(|| summary.scanned_paths.first().cloned())
        .unwrap_or_else(|| ".".to_string());
    let q_dir = PathBuf::from(&base_dir).join("_duplicate_quarantine");
    let is_dry_run = payload.dry_run.unwrap_or(false);

    if !is_dry_run {
        let _ = std::fs::create_dir_all(&q_dir);
    }

    let mut moved_count = 0;
    let mut bytes_moved: u64 = 0;

    for g in &summary.groups {
        if g.action == clairvoy_core::models::ActionType::Duplicate {
            let p = Path::new(&g.path);
            if p.is_file() {
                let size = p.metadata().map(|m| m.len()).unwrap_or(0);
                if !is_dry_run {
                    if let Some(file_name) = p.file_name() {
                        let dst = q_dir.join(file_name);
                        if std::fs::rename(p, dst).is_ok() {
                            moved_count += 1;
                            bytes_moved += size;
                        }
                    }
                } else {
                    moved_count += 1;
                    bytes_moved += size;
                }
            }
        }
    }

    Ok(Json(serde_json::json!({
        "status": "success",
        "total_files_moved": moved_count,
        "total_bytes_moved": bytes_moved,
        "quarantine_dir": q_dir.to_string_lossy().to_string(),
        "dry_run": is_dry_run,
    })))
}

pub async fn handle_reports_csv(
    State(state): State<ServerState>,
) -> Result<Response, (StatusCode, &'static str)> {
    let s = state.scan_state.lock().unwrap();
    let summary = s.summary.as_ref().ok_or((StatusCode::NOT_FOUND, "No active scan summary"))?;

    let mut csv = String::from("group_id,match_type,action,category,similarity,size_mb,path,dimensions\n");
    for g in &summary.groups {
        csv.push_str(&format!(
            "{},{:?},{:?},{:?},{},{:.2},\"{}\",\"{}\"\n",
            g.group_id,
            g.match_type,
            g.action,
            g.category,
            g.similarity,
            g.size_mb,
            g.path.replace('"', "\"\""),
            g.dimensions.as_deref().unwrap_or("")
        ));
    }

    Response::builder()
        .header(header::CONTENT_TYPE, "text/csv")
        .header(
            header::CONTENT_DISPOSITION,
            "attachment; filename=\"clairvoy_duplicates.csv\"",
        )
        .body(Body::from(csv))
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, "Failed to create CSV response"))
}

pub async fn handle_delete_script(
    State(state): State<ServerState>,
    Query(query): Query<DeleteScriptQuery>,
) -> Result<Response, (StatusCode, &'static str)> {
    let s = state.scan_state.lock().unwrap();
    let summary = s.summary.as_ref().ok_or((StatusCode::NOT_FOUND, "No active scan summary"))?;
    let mode = query.mode.unwrap_or_else(|| "trash".to_string());

    let mut script = String::from("#!/usr/bin/env bash\n# Clairvoy Duplicate Removal Script\nset -euo pipefail\n\n");
    if mode == "trash" {
        script.push_str("TRASH_DIR=\"./.clairvoy_trash\"\nmkdir -p \"$TRASH_DIR\"\n\n");
    }

    for g in &summary.groups {
        if g.action == clairvoy_core::models::ActionType::Duplicate {
            let escaped = g.path.replace('"', "\\\"");
            if mode == "trash" {
                script.push_str(&format!("mv \"{}\" \"$TRASH_DIR/\"\n", escaped));
            } else {
                script.push_str(&format!("rm -f \"{}\"\n", escaped));
            }
        }
    }

    Response::builder()
        .header(header::CONTENT_TYPE, "application/x-sh")
        .header(
            header::CONTENT_DISPOSITION,
            format!("attachment; filename=\"delete_duplicates_{}.sh\"", mode),
        )
        .body(Body::from(script))
        .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, "Failed to create script response"))
}

pub fn auto_load_recent_run(state: &SharedScanState) {
    let home = std::env::var("HOME")
        .or_else(|_| std::env::var("USERPROFILE"))
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("."));
    let history_file = home.join(".clairvoy").join("runs.json");
    if !history_file.is_file() {
        return;
    }
    if let Ok(content) = std::fs::read_to_string(&history_file) {
        if let Ok(runs) = serde_json::from_str::<Vec<serde_json::Value>>(&content) {
            for r in runs {
                if let Some(summary_path_str) = r.get("summary_json").and_then(|s| s.as_str()) {
                    let p = PathBuf::from(summary_path_str);
                    if p.is_file() {
                        if let Ok(sc_content) = std::fs::read_to_string(&p) {
                            if let Ok(summary) =
                                serde_json::from_str::<clairvoy_core::models::ScanSummary>(&sc_content)
                            {
                                if let Ok(mut s) = state.lock() {
                                    s.status = "completed".to_string();
                                    s.stage = "Scan summary loaded".to_string();
                                    s.progress_pct = 100;
                                    s.files_indexed = summary.total_files_scanned;
                                    s.elapsed_seconds = summary.duration_seconds;
                                    s.message = format!(
                                        "Loaded scan summary ({} duplicate groups, {:.2} GB recoverable)",
                                        summary.total_duplicate_groups, summary.wasted_gb
                                    );
                                    s.summary = Some(summary);
                                    s.error = None;
                                    break;
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

pub fn build_router_with_state(state: SharedScanState) -> Router {
    let db = Arc::new(Mutex::new(
        Database::open(None).unwrap_or_else(|_| Database::open_in_memory().unwrap()),
    ));
    build_router_full(ServerState {
        scan_state: state,
        db,
        watcher: None,
    })
}

pub fn build_router() -> Router {
    let state: SharedScanState = Default::default();
    auto_load_recent_run(&state);
    build_router_with_state(state)
}

pub fn build_router_with_services(
    state: SharedScanState,
    db: Arc<Mutex<Database>>,
    watcher: Option<Arc<AutonomousWatcher>>,
) -> Router {
    build_router_full(ServerState {
        scan_state: state,
        db,
        watcher,
    })
}

pub fn build_router_full(state: ServerState) -> Router {
    Router::new()
        .route("/", get(handle_index))
        .route("/api/status", get(handle_status))
        .route("/api/status/stream", get(handle_status_stream))
        .route("/api/scan", post(handle_scan))
        .route("/api/runs", get(handle_runs))
        .route("/api/runs/load", post(handle_runs_load))
        .route("/api/duplicates", get(handle_duplicates))
        .route("/api/watch/paths", get(handle_watch_paths_list).post(handle_watch_paths_add))
        .route("/api/watch/paths/:id/toggle", post(handle_watch_paths_toggle))
        .route("/api/watch/paths/:id", delete(handle_watch_paths_delete))
        .route("/api/watch/daemon/toggle", post(handle_watch_daemon_toggle))
        .route("/api/system/browse-directories", get(handle_browse_directories))
        .route("/api/system/pick-folder", post(handle_pick_folder))
        .route("/api/thumbnail", get(handle_thumbnail_or_media))
        .route("/api/media", get(handle_thumbnail_or_media))
        .route("/api/clusters/override-keeper", post(handle_override_keeper))
        .route("/api/delete/execute", post(handle_delete_execute))
        .route("/api/quarantine/execute", post(handle_quarantine_execute))
        .route("/api/reports/csv", get(handle_reports_csv))
        .route("/api/reports/delete-script", get(handle_delete_script))
        .layer(CorsLayer::permissive())
        .with_state(state)
}
