use clairvoy_core::models::ScanSummary;
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppScanState {
    pub status: String,
    pub stage: String,
    pub progress_pct: u32,
    pub files_indexed: usize,
    pub elapsed_seconds: f64,
    pub message: String,
    pub summary: Option<ScanSummary>,
    pub error: Option<String>,
    #[serde(default)]
    pub run_id: Option<String>,
    #[serde(default)]
    pub bytes_scanned: u64,
    #[serde(default)]
    pub scanned_mb: f64,
    #[serde(default)]
    pub scanned_gb: f64,
    #[serde(default)]
    pub wasted_bytes: u64,
    #[serde(default)]
    pub wasted_mb: f64,
    #[serde(default)]
    pub wasted_gb: f64,
}

impl Default for AppScanState {
    fn default() -> Self {
        Self {
            status: "idle".to_string(),
            stage: "Ready".to_string(),
            progress_pct: 0,
            files_indexed: 0,
            elapsed_seconds: 0.0,
            message: "Ready to scan".to_string(),
            summary: None,
            error: None,
            run_id: None,
            bytes_scanned: 0,
            scanned_mb: 0.0,
            scanned_gb: 0.0,
            wasted_bytes: 0,
            wasted_mb: 0.0,
            wasted_gb: 0.0,
        }
    }
}

pub type SharedScanState = Arc<Mutex<AppScanState>>;

use clairvoy_core::db::Database;
use clairvoy_engine::watcher::AutonomousWatcher;

#[derive(Clone)]
pub struct ServerState {
    pub scan_state: SharedScanState,
    pub db: Arc<Mutex<Database>>,
    pub watcher: Option<Arc<AutonomousWatcher>>,
}
