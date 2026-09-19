use clairvoy_core::db::Database;
use clairvoy_engine::watcher::AutonomousWatcher;
use std::sync::{Arc, Mutex};
use std::time::Duration;
use tempfile::tempdir;

#[tokio::test]
async fn test_watcher_detects_file_creation_and_debounces() {
    let dir = tempdir().unwrap();
    let db_file = dir.path().join("test.db");
    let db = Arc::new(Mutex::new(Database::open(Some(&db_file)).unwrap()));

    let watch_dir = dir.path().join("watched");
    std::fs::create_dir_all(&watch_dir).unwrap();
    db.lock()
        .unwrap()
        .add_watched_path(watch_dir.to_str().unwrap(), true)
        .unwrap();

    let watcher = AutonomousWatcher::start(Arc::clone(&db), 100, 3600)
        .await
        .unwrap();

    // Create duplicate file
    let file1 = watch_dir.join("test1.txt");
    let file2 = watch_dir.join("test2.txt");
    std::fs::write(&file1, b"hello duplicate content").unwrap();
    std::fs::write(&file2, b"hello duplicate content").unwrap();

    // Allow debounce to fire
    tokio::time::sleep(Duration::from_millis(350)).await;

    let runs = db.lock().unwrap().list_scan_runs(10).unwrap();
    assert!(
        !runs.is_empty(),
        "Watcher should have automatically executed a scan run"
    );

    // Verify file_index was populated with cached entries
    let cached = db
        .lock()
        .unwrap()
        .get_cached_file(file1.to_str().unwrap())
        .unwrap();
    assert!(cached.is_some(), "File index should cache scanned files");

    watcher.stop().await;
}

#[tokio::test]
async fn test_watcher_pause_resume_and_trigger_scan() {
    let dir = tempdir().unwrap();
    let db_file = dir.path().join("test_controls.db");
    let db = Arc::new(Mutex::new(Database::open(Some(&db_file)).unwrap()));

    let watch_dir = dir.path().join("watched_controls");
    std::fs::create_dir_all(&watch_dir).unwrap();
    db.lock()
        .unwrap()
        .add_watched_path(watch_dir.to_str().unwrap(), true)
        .unwrap();

    let watcher = AutonomousWatcher::start(Arc::clone(&db), 100, 3600)
        .await
        .unwrap();

    assert!(!watcher.is_paused());
    watcher.pause();
    assert!(watcher.is_paused());

    // While paused, create a file
    let file1 = watch_dir.join("sample1.txt");
    std::fs::write(&file1, b"sample content").unwrap();
    tokio::time::sleep(Duration::from_millis(250)).await;

    // Paused watcher should not have executed scan
    let runs_paused = db.lock().unwrap().list_scan_runs(10).unwrap();
    assert!(runs_paused.is_empty());

    // Resume
    watcher.resume();
    assert!(!watcher.is_paused());

    // Manual trigger scan
    watcher.trigger_scan_now().unwrap();
    tokio::time::sleep(Duration::from_millis(150)).await;

    let runs_triggered = db.lock().unwrap().list_scan_runs(10).unwrap();
    assert_eq!(runs_triggered.len(), 1);

    watcher.stop().await;
    // Calling stop twice should be idempotent
    watcher.stop().await;
}

#[tokio::test]
async fn test_watcher_fallback_periodic_sweep() {
    let dir = tempdir().unwrap();
    let db_file = dir.path().join("test_fallback.db");
    let db = Arc::new(Mutex::new(Database::open(Some(&db_file)).unwrap()));

    let watch_dir = dir.path().join("watched_fallback");
    std::fs::create_dir_all(&watch_dir).unwrap();
    db.lock()
        .unwrap()
        .add_watched_path(watch_dir.to_str().unwrap(), true)
        .unwrap();

    // Start with 1-second fallback interval
    let watcher = AutonomousWatcher::start(Arc::clone(&db), 100, 1)
        .await
        .unwrap();

    let file1 = watch_dir.join("fallback_test.txt");
    std::fs::write(&file1, b"fallback content").unwrap();

    // Sleep 1.3s to allow the 1-second fallback ticker to fire
    tokio::time::sleep(Duration::from_millis(1300)).await;

    let runs = db.lock().unwrap().list_scan_runs(10).unwrap();
    assert!(
        !runs.is_empty(),
        "Fallback ticker should have triggered a scan run"
    );

    watcher.stop().await;
}

#[tokio::test]
async fn test_watcher_reports_progress_callback() {
    let dir = tempdir().unwrap();
    let db_file = dir.path().join("test_progress.db");
    let db = Arc::new(Mutex::new(Database::open(Some(&db_file)).unwrap()));

    let watch_dir = dir.path().join("watched_progress");
    std::fs::create_dir_all(&watch_dir).unwrap();
    db.lock()
        .unwrap()
        .add_watched_path(watch_dir.to_str().unwrap(), true)
        .unwrap();

    let progress_events = Arc::new(Mutex::new(Vec::new()));
    let progress_events_cb = Arc::clone(&progress_events);
    let progress_cb = Arc::new(move |stage: &str, cur: usize, tot: usize| {
        progress_events_cb
            .lock()
            .unwrap()
            .push((stage.to_string(), cur, tot));
    });

    let watcher =
        AutonomousWatcher::start_with_progress(Arc::clone(&db), 100, 3600, Some(progress_cb))
            .await
            .unwrap();

    let file1 = watch_dir.join("f1.txt");
    let file2 = watch_dir.join("f2.txt");
    std::fs::write(&file1, b"identical data").unwrap();
    std::fs::write(&file2, b"identical data").unwrap();

    tokio::time::sleep(Duration::from_millis(350)).await;

    let events = progress_events.lock().unwrap().clone();
    assert!(
        !events.is_empty(),
        "Progress callback should have received events during scan"
    );

    watcher.stop().await;
}
