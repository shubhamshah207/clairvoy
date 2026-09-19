use crate::state::{AppScanState, SharedScanState};
use axum::extract::State;
use axum::response::{Html, Json};
use axum::routing::{get, post};
use axum::Router;
use serde::Deserialize;
use tower_http::cors::CorsLayer;

#[derive(Debug, Clone, Deserialize)]
pub struct ScanPayload {
    pub paths: Vec<String>,
}

pub async fn handle_index() -> Html<&'static str> {
    Html("<!DOCTYPE html><html><head><title>Clairvoy</title></head><body><h1>Clairvoy Pure Rust Studio</h1></body></html>")
}

pub async fn handle_status(State(state): State<SharedScanState>) -> Json<AppScanState> {
    let s = state.lock().unwrap();
    Json(s.clone())
}

pub async fn handle_scan(
    State(state): State<SharedScanState>,
    Json(payload): Json<ScanPayload>,
) -> Json<serde_json::Value> {
    let mut s = state.lock().unwrap();
    s.status = "running".to_string();
    s.message = format!("Scanning {} path(s)", payload.paths.len());
    Json(serde_json::json!({ "status": "started", "paths": payload.paths }))
}

pub async fn handle_runs() -> Json<serde_json::Value> {
    Json(serde_json::json!([]))
}

pub fn build_router() -> Router {
    let state: SharedScanState = Default::default();
    build_router_with_state(state)
}

pub fn build_router_with_state(state: SharedScanState) -> Router {
    Router::new()
        .route("/", get(handle_index))
        .route("/api/status", get(handle_status))
        .route("/api/scan", post(handle_scan))
        .route("/api/runs", get(handle_runs))
        .layer(CorsLayer::permissive())
        .with_state(state)
}
