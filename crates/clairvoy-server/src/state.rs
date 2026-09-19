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
        }
    }
}

pub type SharedScanState = Arc<Mutex<AppScanState>>;
