use clairvoy_core::db::{CachedFileRecord, Database};
use clairvoy_core::models::{ActionType, DuplicateRecord, ImageCategory, MatchType, ScanSummary};
use tempfile::NamedTempFile;

#[test]
fn test_db_init_and_watched_paths() {
    let tmp = NamedTempFile::new().unwrap();
    let db = Database::open(Some(tmp.path())).expect("Should open db");

    let id = db.add_watched_path("/tmp/photos", true).expect("Add path");
    let paths = db.list_watched_paths().expect("List paths");
    assert_eq!(paths.len(), 1);
    assert_eq!(paths[0].path, "/tmp/photos");
    assert!(paths[0].enabled);

    db.toggle_watched_path(id, false).expect("Toggle");
    let updated = db.list_watched_paths().expect("List paths");
    assert!(!updated[0].enabled);

    db.remove_watched_path(id).expect("Remove");
    assert_eq!(db.list_watched_paths().unwrap().len(), 0);
}

#[test]
fn test_db_save_and_query_scan_run() {
    let tmp = NamedTempFile::new().unwrap();
    let db = Database::open(Some(tmp.path())).expect("Should open db");

    let summary = ScanSummary {
        scanned_paths: vec!["/tmp/test".to_string()],
        scanned_dir: "/tmp/test".to_string(),
        total_files_scanned: 10,
        total_duplicate_groups: 1,
        wasted_bytes: 1024,
        wasted_mb: 0.001,
        wasted_gb: 0.0,
        duration_seconds: 0.5,
        groups: vec![
            DuplicateRecord {
                group_id: 1,
                match_type: MatchType::ExactHash,
                action: ActionType::Keep,
                category: ImageCategory::Photo,
                similarity: "100%".to_string(),
                similarity_score: 1.0,
                size_mb: 0.001,
                path: "/tmp/test/img1.jpg".to_string(),
                dimensions: None,
            },
            DuplicateRecord {
                group_id: 1,
                match_type: MatchType::ExactHash,
                action: ActionType::Duplicate,
                category: ImageCategory::Photo,
                similarity: "100%".to_string(),
                similarity_score: 1.0,
                size_mb: 0.001,
                path: "/tmp/test/img2.jpg".to_string(),
                dimensions: None,
            },
        ],
        ..Default::default()
    };

    db.save_scan_run("run_1", &summary).expect("Save run");
    let runs = db.list_scan_runs(10).expect("List runs");
    assert_eq!(runs.len(), 1);
    assert_eq!(runs[0].run_id, "run_1");

    let clusters = db.get_clusters_for_run("run_1", None, 0, 50).expect("Get clusters");
    assert_eq!(clusters.len(), 1);
    assert_eq!(clusters[0].items.len(), 2);
}

#[test]
fn test_db_override_keeper() {
    let tmp = NamedTempFile::new().unwrap();
    let db = Database::open(Some(tmp.path())).expect("Should open db");

    let summary = ScanSummary {
        scanned_paths: vec!["/tmp/test".to_string()],
        scanned_dir: "/tmp/test".to_string(),
        total_files_scanned: 10,
        total_duplicate_groups: 1,
        wasted_bytes: 2048,
        wasted_mb: 0.002,
        wasted_gb: 0.0,
        duration_seconds: 0.5,
        groups: vec![
            DuplicateRecord {
                group_id: 1,
                match_type: MatchType::ExactHash,
                action: ActionType::Keep,
                category: ImageCategory::Photo,
                similarity: "100%".to_string(),
                similarity_score: 1.0,
                size_mb: 0.001,
                path: "/tmp/test/img1.jpg".to_string(),
                dimensions: None,
            },
            DuplicateRecord {
                group_id: 1,
                match_type: MatchType::ExactHash,
                action: ActionType::Duplicate,
                category: ImageCategory::Photo,
                similarity: "100%".to_string(),
                similarity_score: 1.0,
                size_mb: 0.001,
                path: "/tmp/test/img2.jpg".to_string(),
                dimensions: None,
            },
        ],
        ..Default::default()
    };

    db.save_scan_run("run_override", &summary).expect("Save run");
    let clusters = db.get_clusters_for_run("run_override", None, 0, 10).expect("Get clusters");
    assert_eq!(clusters.len(), 1);
    let cluster_id = clusters[0].id;

    // Initially img1 is KEEP, img2 is DUPLICATE
    let item1 = clusters[0].items.iter().find(|i| i.path == "/tmp/test/img1.jpg").unwrap();
    let item2 = clusters[0].items.iter().find(|i| i.path == "/tmp/test/img2.jpg").unwrap();
    assert_eq!(item1.action, "KEEP");
    assert_eq!(item2.action, "DUPLICATE");

    // Override keeper to img2
    db.override_keeper(cluster_id, "/tmp/test/img2.jpg").expect("Override keeper");

    let updated_clusters = db.get_clusters_for_run("run_override", None, 0, 10).expect("Get updated clusters");
    let updated_item1 = updated_clusters[0].items.iter().find(|i| i.path == "/tmp/test/img1.jpg").unwrap();
    let updated_item2 = updated_clusters[0].items.iter().find(|i| i.path == "/tmp/test/img2.jpg").unwrap();
    assert_eq!(updated_item1.action, "DUPLICATE");
    assert_eq!(updated_item2.action, "KEEP");
}

#[test]
fn test_db_file_index_caching() {
    let tmp = NamedTempFile::new().unwrap();
    let db = Database::open(Some(tmp.path())).expect("Should open db");

    db.save_scan_run("run_cache_1", &ScanSummary::default()).expect("Save scan run");

    let entry = CachedFileRecord {
        id: 0,
        path: "/tmp/test/cached.png".to_string(),
        size_bytes: 4096,
        modified_epoch: 1726700000,
        quick_hash: "xxh3_quick_123".to_string(),
        full_hash: Some("b3_full_456".to_string()),
        category: "PHOTO".to_string(),
        last_seen_run: Some("run_cache_1".to_string()),
    };

    db.upsert_file_index(&entry).expect("Upsert file index");

    let cached = db.get_cached_file("/tmp/test/cached.png").expect("Get cached");
    assert!(cached.is_some());
    let retrieved = cached.unwrap();
    assert_eq!(retrieved.path, "/tmp/test/cached.png");
    assert_eq!(retrieved.size_bytes, 4096);
    assert_eq!(retrieved.modified_epoch, 1726700000);
    assert_eq!(retrieved.quick_hash, "xxh3_quick_123");
    assert_eq!(retrieved.full_hash.as_deref(), Some("b3_full_456"));
    assert_eq!(retrieved.category, "PHOTO");

    // Non-existent file
    let missing = db.get_cached_file("/tmp/test/nonexistent.jpg").expect("Query missing");
    assert!(missing.is_none());
}

#[test]
fn test_db_get_scan_summary() {
    let tmp = NamedTempFile::new().unwrap();
    let db = Database::open(Some(tmp.path())).expect("Should open db");

    let summary = ScanSummary {
        scanned_paths: vec!["/tmp/test/storage".to_string()],
        scanned_dir: "/tmp/test/storage".to_string(),
        total_files_scanned: 10,
        media_files_scanned: 10,
        exact_duplicate_groups: 1,
        visual_ai_groups: 0,
        content_duplicate_groups: 0,
        total_duplicate_groups: 1,
        wasted_bytes: 10_485_760, // exactly 10 MB
        wasted_mb: 10.0,
        wasted_gb: 10.0 / 1024.0,
        duration_seconds: 1.25,
        csv_report: None,
        summary_json: None,
        quarantine_script: None,
        groups: vec![
            DuplicateRecord {
                group_id: 1,
                match_type: MatchType::ExactHash,
                action: ActionType::Keep,
                category: ImageCategory::Photo,
                similarity: "100%".to_string(),
                similarity_score: 1.0,
                size_mb: 10.0,
                path: "/tmp/test/storage/photo_keep.jpg".to_string(),
                dimensions: Some("1920x1080".to_string()),
            },
            DuplicateRecord {
                group_id: 1,
                match_type: MatchType::ExactHash,
                action: ActionType::Duplicate,
                category: ImageCategory::Photo,
                similarity: "100%".to_string(),
                similarity_score: 1.0,
                size_mb: 10.0,
                path: "/tmp/test/storage/photo_dupe.jpg".to_string(),
                dimensions: Some("1920x1080".to_string()),
            },
        ],
        category_breakdown: [("PHOTO".to_string(), 1)].into_iter().collect(),
    };

    db.save_scan_run("run_summary_test", &summary).expect("Save scan run");

    let loaded = db.get_scan_summary("run_summary_test").expect("Get scan summary");
    assert!(loaded.is_some());
    let loaded_summary = loaded.unwrap();
    assert_eq!(loaded_summary.total_files_scanned, 10);
    assert_eq!(loaded_summary.total_duplicate_groups, 1);
    assert_eq!(loaded_summary.wasted_bytes, 10_485_760);
    assert!((loaded_summary.wasted_mb - 10.0).abs() < 1e-4);
    assert_eq!(loaded_summary.groups.len(), 2);
    assert_eq!(loaded_summary.groups[0].action, ActionType::Keep);
    assert_eq!(loaded_summary.groups[1].action, ActionType::Duplicate);
    assert_eq!(loaded_summary.category_breakdown.get("PHOTO"), Some(&1));
}

