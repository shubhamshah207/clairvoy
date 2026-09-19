use clairvoy_core::models::{
    ActionType, DuplicateRecord, FileEntry, ImageCategory, MatchType, ScanSummary,
};
use std::path::PathBuf;

#[test]
fn test_file_entry_and_summary_serialization() {
    let entry = FileEntry {
        path: PathBuf::from("/tmp/photo.jpg"),
        size_bytes: 1048576,
        modified_epoch: 1700000000,
        is_media: true,
        category: ImageCategory::Photo,
    };
    assert_eq!(entry.size_bytes, 1048576);

    let record = DuplicateRecord {
        group_id: 1,
        match_type: MatchType::ExactHash,
        action: ActionType::Keep,
        category: ImageCategory::Photo,
        similarity: "100%".to_string(),
        similarity_score: 1.0,
        size_mb: 1.0,
        path: "/tmp/photo.jpg".to_string(),
        dimensions: Some("1920x1080".to_string()),
    };

    let summary = ScanSummary {
        scanned_paths: vec!["/tmp".to_string()],
        scanned_dir: "/tmp".to_string(),
        total_files_scanned: 1,
        media_files_scanned: 1,
        exact_duplicate_groups: 1,
        visual_ai_groups: 0,
        content_duplicate_groups: 0,
        total_duplicate_groups: 1,
        wasted_bytes: 0,
        wasted_mb: 0.0,
        wasted_gb: 0.0,
        duration_seconds: 0.1,
        csv_report: None,
        summary_json: None,
        quarantine_script: None,
        groups: vec![record],
        category_breakdown: Default::default(),
    };

    let json = serde_json::to_string(&summary).expect("Failed to serialize");
    assert!(json.contains("scanned_paths"));
    assert!(json.contains("/tmp/photo.jpg"));
    assert!(json.contains("\"csv_report\":\"\""));
    assert!(json.contains("\"summary_json\":\"\""));
    assert!(json.contains("\"quarantine_script\":\"\""));

    let deserialized: ScanSummary = serde_json::from_str(&json).expect("Failed to deserialize");
    assert_eq!(summary, deserialized);
}
