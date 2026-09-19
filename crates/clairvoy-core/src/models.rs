use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
pub enum ImageCategory {
    Photo,
    Video,
    Screenshot,
    Document,
    Graphic,
    File,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
pub enum MatchType {
    #[serde(rename = "EXACT_HASH")]
    ExactHash,
    #[serde(rename = "VISUAL_AI_NEAR_DUPLICATE")]
    VisualAiNearDuplicate,
    #[serde(rename = "CONTENT_NEAR_DUPLICATE")]
    ContentNearDuplicate,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
pub enum ActionType {
    Keep,
    Duplicate,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct FileEntry {
    pub path: PathBuf,
    pub size_bytes: u64,
    pub modified_epoch: u64,
    pub is_media: bool,
    pub category: ImageCategory,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DuplicateRecord {
    pub group_id: usize,
    pub match_type: MatchType,
    pub action: ActionType,
    pub category: ImageCategory,
    pub similarity: String,
    pub similarity_score: f64,
    pub size_mb: f64,
    pub path: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub dimensions: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DuplicateCluster {
    pub cluster_id: usize,
    pub match_type: MatchType,
    pub members: Vec<FileEntry>,
    pub similarity_scores: Vec<f64>,
    pub metadata: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ScanSummary {
    pub scanned_paths: Vec<String>,
    pub scanned_dir: String,
    pub total_files_scanned: usize,
    pub media_files_scanned: usize,
    pub exact_duplicate_groups: usize,
    pub visual_ai_groups: usize,
    pub content_duplicate_groups: usize,
    pub total_duplicate_groups: usize,
    pub wasted_bytes: u64,
    pub wasted_mb: f64,
    pub wasted_gb: f64,
    pub duration_seconds: f64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub csv_report: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub summary_json: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub quarantine_script: Option<String>,
    pub groups: Vec<DuplicateRecord>,
    #[serde(default)]
    pub category_breakdown: HashMap<String, usize>,
}
