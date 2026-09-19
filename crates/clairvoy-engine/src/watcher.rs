use crate::pipeline::DeduplicationPipeline;
use clairvoy_core::db::{CachedFileRecord, Database, WatchedPathRecord};
use clairvoy_core::errors::EngineError;
use clairvoy_plugins::exact_hash::ExactHashMatcherPlugin;
use clairvoy_scanner::compute_quick_hash_4kb;
use notify::{Config, Event, EventKind, RecommendedWatcher, RecursiveMode, Watcher};
use std::collections::HashSet;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, SystemTime, UNIX_EPOCH};
use tokio::sync::{mpsc, watch, Mutex as TokioMutex};
use tokio::task::JoinHandle;
use tokio::time::Instant;

/// Background autonomous filesystem surveillance daemon for Clairvoy.
///
/// Monitors configured paths in SQLite using native filesystem events (`notify`),
/// applies a sliding quiet window debounce to absorb burst modifications,
/// executes incremental delta deduplication runs, and maintains surveillance state.
pub type WatcherProgressCallback = Arc<dyn Fn(&str, usize, usize) + Send + Sync>;

#[derive(Clone)]
pub struct AutonomousWatcher {
    paused: Arc<AtomicBool>,
    trigger_tx: mpsc::Sender<()>,
    stop_tx: watch::Sender<bool>,
    join_handle: Arc<TokioMutex<Option<JoinHandle<()>>>>,
}

impl AutonomousWatcher {
    /// Start the autonomous background watcher daemon.
    pub async fn start(
        db: Arc<Mutex<Database>>,
        debounce_ms: u64,
        fallback_interval_sec: u64,
    ) -> Result<Self, EngineError> {
        Self::start_with_progress(db, debounce_ms, fallback_interval_sec, None).await
    }

    /// Start the autonomous background watcher daemon with an optional progress reporter.
    ///
    /// - `db`: Thread-safe handle to SQLite database.
    /// - `debounce_ms`: Sliding quiet window duration in milliseconds.
    /// - `fallback_interval_sec`: Periodic fallback scan interval in seconds (0 to disable).
    /// - `progress`: Optional callback reporting live scan progress (stage, current, total).
    pub async fn start_with_progress(
        db: Arc<Mutex<Database>>,
        debounce_ms: u64,
        fallback_interval_sec: u64,
        progress: Option<WatcherProgressCallback>,
    ) -> Result<Self, EngineError> {
        let (event_tx, mut event_rx) = mpsc::unbounded_channel::<notify::Result<Event>>();

        let mut watcher = RecommendedWatcher::new(
            move |res| {
                let _ = event_tx.send(res);
            },
            Config::default(),
        )
        .map_err(|e| EngineError::Config(format!("Failed to initialize inotify watcher: {e}")))?;

        // Query initially enabled watched paths and register with the watcher
        let mut currently_watched = HashSet::new();
        {
            let db_guard = db
                .lock()
                .map_err(|e| EngineError::Config(format!("Database lock error: {e}")))?;
            let watched_records = db_guard.list_watched_paths()?;
            for rec in watched_records {
                if rec.enabled {
                    let path = PathBuf::from(&rec.path);
                    if path.exists() {
                        let is_drive_root = path.parent() == Some(Path::new("/mnt"))
                            || path.parent() == Some(Path::new("/Volumes"))
                            || path == Path::new("/");
                        let mode = if rec.recursive && !is_drive_root {
                            RecursiveMode::Recursive
                        } else {
                            RecursiveMode::NonRecursive
                        };
                        if let Err(e) = watcher.watch(&path, mode) {
                            eprintln!(
                                "[clairvoy-watcher] Warning: unable to watch '{}': {e}",
                                path.display()
                            );
                        } else {
                            currently_watched.insert(path);
                        }
                    }
                }
            }
        }

        let (trigger_tx, mut trigger_rx) = mpsc::channel::<()>(16);
        let (stop_tx, mut stop_rx) = watch::channel(false);
        let paused = Arc::new(AtomicBool::new(false));
        let paused_clone = Arc::clone(&paused);

        let debounce_duration = Duration::from_millis(debounce_ms);

        let progress_for_task = progress;
        let join_handle = tokio::spawn(async move {
            let mut quiet_deadline: Option<Instant> = None;
            let mut fallback_interval = if fallback_interval_sec > 0 {
                let period = Duration::from_secs(fallback_interval_sec);
                Some(tokio::time::interval_at(Instant::now() + period, period))
            } else {
                None
            };

            loop {
                tokio::select! {
                    // 1. Shutdown signal
                    _ = stop_rx.changed() => {
                        if *stop_rx.borrow() {
                            break;
                        }
                    }

                    // 2. Explicit manual scan trigger
                    Some(()) = trigger_rx.recv() => {
                        quiet_deadline = None;
                        if let Err(e) = execute_scan_cycle(&db, &mut currently_watched, &mut watcher, progress_for_task.as_ref()).await {
                            eprintln!("[clairvoy-watcher] Triggered scan error: {e}");
                        }
                    }

                    // 3. Inotify filesystem notification
                    event_opt = event_rx.recv() => {
                        match event_opt {
                            Some(Ok(event)) => {
                                if !paused_clone.load(Ordering::SeqCst) && is_relevant_event(&event) {
                                    // Reset sliding quiet window timer
                                    quiet_deadline = Some(Instant::now() + debounce_duration);
                                }
                            }
                            Some(Err(e)) => {
                                eprintln!("[clairvoy-watcher] Notification error: {e}");
                            }
                            None => {
                                // Event channel closed
                                break;
                            }
                        }
                    }

                    // 4. Quiet window expiration
                    _ = async {
                        match quiet_deadline {
                            Some(deadline) => tokio::time::sleep_until(deadline).await,
                            None => std::future::pending().await,
                        }
                    }, if quiet_deadline.is_some() => {
                        quiet_deadline = None;
                        if !paused_clone.load(Ordering::SeqCst) {
                            if let Err(e) = execute_scan_cycle(&db, &mut currently_watched, &mut watcher, progress_for_task.as_ref()).await {
                                eprintln!("[clairvoy-watcher] Debounced scan error: {e}");
                            }
                        }
                    }

                    // 5. Periodic fallback ticker
                    _ = async {
                        match &mut fallback_interval {
                            Some(interval) => {
                                interval.tick().await;
                            }
                            None => std::future::pending().await,
                        }
                    }, if fallback_interval.is_some() => {
                        if quiet_deadline.is_none() && !paused_clone.load(Ordering::SeqCst) {
                            if let Err(e) = execute_scan_cycle(&db, &mut currently_watched, &mut watcher, progress_for_task.as_ref()).await {
                                eprintln!("[clairvoy-watcher] Fallback sweep error: {e}");
                            }
                        }
                    }
                }
            }
        });

        Ok(Self {
            paused,
            trigger_tx,
            stop_tx,
            join_handle: Arc::new(TokioMutex::new(Some(join_handle))),
        })
    }

    /// Gracefully stop the autonomous background watcher daemon.
    pub async fn stop(&self) {
        let _ = self.stop_tx.send(true);
        let mut guard = self.join_handle.lock().await;
        if let Some(handle) = guard.take() {
            let _ = handle.await;
        }
    }

    /// Pause the background watcher.
    pub fn pause(&self) {
        self.paused.store(true, Ordering::SeqCst);
    }

    /// Resume the background watcher.
    pub fn resume(&self) {
        self.paused.store(false, Ordering::SeqCst);
    }

    /// Returns whether the background watcher is currently paused.
    pub fn is_paused(&self) -> bool {
        self.paused.load(Ordering::SeqCst)
    }

    /// Trigger an immediate scan across all enabled watched paths.
    pub fn trigger_scan_now(&self) -> Result<(), EngineError> {
        match self.trigger_tx.try_send(()) {
            Ok(_) | Err(mpsc::error::TrySendError::Full(_)) => Ok(()),
            Err(mpsc::error::TrySendError::Closed(_)) => {
                Err(EngineError::Config("Watcher daemon is stopped".to_string()))
            }
        }
    }
}

/// Synchronizes filesystem watches with SQLite database and executes a deduplication scan.
async fn execute_scan_cycle(
    db: &Arc<Mutex<Database>>,
    currently_watched: &mut HashSet<PathBuf>,
    watcher: &mut RecommendedWatcher,
    progress: Option<&WatcherProgressCallback>,
) -> Result<(), EngineError> {
    let watched_records = {
        let db_guard = db
            .lock()
            .map_err(|e| EngineError::Config(format!("Database lock error: {e}")))?;
        db_guard.list_watched_paths()?
    };

    let mut desired_map = std::collections::HashMap::new();
    let mut scan_paths = Vec::new();

    for rec in &watched_records {
        if rec.enabled {
            let path = PathBuf::from(&rec.path);
            if path.exists() {
                let is_drive_root = path.parent() == Some(Path::new("/mnt"))
                    || path.parent() == Some(Path::new("/Volumes"))
                    || path == Path::new("/");
                let mode = if rec.recursive && !is_drive_root {
                    RecursiveMode::Recursive
                } else {
                    RecursiveMode::NonRecursive
                };
                desired_map.insert(path.clone(), mode);
                scan_paths.push(path);
            }
        }
    }

    // Synchronize active watches with current database state
    for (path, mode) in &desired_map {
        if !currently_watched.contains(path) {
            if let Ok(()) = watcher.watch(path, *mode) {
                currently_watched.insert(path.clone());
            }
        }
    }

    let desired_set: HashSet<PathBuf> = desired_map.into_keys().collect();
    let to_remove: Vec<PathBuf> = currently_watched
        .difference(&desired_set)
        .cloned()
        .collect();
    for path in to_remove {
        let _ = watcher.unwatch(&path);
        currently_watched.remove(&path);
    }

    if scan_paths.is_empty() {
        return Ok(());
    }

    let db_clone = Arc::clone(db);
    let progress_cb = progress.cloned();
    tokio::task::spawn_blocking(move || {
        run_delta_pipeline(&db_clone, scan_paths, &watched_records, progress_cb)
    })
    .await
    .map_err(|e| EngineError::Config(format!("Scan task execution failed: {e}")))?
}

/// Executes deduplication pipeline and saves results to SQLite.
fn run_delta_pipeline(
    db: &Arc<Mutex<Database>>,
    scan_paths: Vec<PathBuf>,
    watched_records: &[WatchedPathRecord],
    progress: Option<WatcherProgressCallback>,
) -> Result<(), EngineError> {
    if let Some(ref cb) = progress {
        cb("Crawling watched directories...", 0, 0);
    }

    let mut pipeline = DeduplicationPipeline::new(scan_paths.clone());
    pipeline.register_matcher(Arc::new(ExactHashMatcherPlugin::new()));
    let progress_for_pipe = progress.clone();
    let summary = pipeline.run(move |stage, cur, tot| {
        if let Some(ref cb) = progress_for_pipe {
            cb(stage, cur, tot);
        }
    })?;

    let run_id = format!(
        "run_{}",
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_micros()
    );

    let db_guard = db
        .lock()
        .map_err(|e| EngineError::Config(format!("Database lock error: {e}")))?;
    db_guard.save_scan_run(&run_id, &summary)?;

    for rec in watched_records {
        if rec.enabled {
            let _ = db_guard.update_watched_path_last_scanned(rec.id);
        }
    }

    if let Some(ref cb) = progress {
        cb(
            "Scan complete",
            summary.total_files_scanned,
            summary.total_files_scanned,
        );
    }

    // Delta cache indexing: crawl and update file_index
    if let Ok((files, _)) = clairvoy_scanner::scan_roots(&scan_paths) {
        for file in files {
            let path_str = file.path.to_string_lossy().to_string();
            let is_unmodified = match db_guard.get_cached_file(&path_str) {
                Ok(Some(cached)) => {
                    cached.size_bytes == file.size_bytes
                        && cached.modified_epoch == file.modified_epoch
                }
                _ => false,
            };

            if !is_unmodified {
                let quick_hash = compute_quick_hash_4kb(&file.path)
                    .map(|h| format!("{h:016x}"))
                    .unwrap_or_default();

                let cached_entry = CachedFileRecord {
                    id: 0,
                    path: path_str,
                    size_bytes: file.size_bytes,
                    modified_epoch: file.modified_epoch,
                    quick_hash,
                    full_hash: None,
                    category: format!("{:?}", file.category).to_uppercase(),
                    last_seen_run: Some(run_id.clone()),
                };
                let _ = db_guard.upsert_file_index(&cached_entry);
            }
        }
    }

    Ok(())
}

/// Checks if an inotify event should trigger debouncing.
fn is_relevant_event(event: &Event) -> bool {
    // Ignore pure file access/read operations
    if let EventKind::Access(_) = event.kind {
        return false;
    }

    if event.paths.is_empty() {
        return true;
    }

    event.paths.iter().any(|p| is_relevant_path(p))
}

/// Excludes SQLite DB files and standard ignored directories.
fn is_relevant_path(path: &Path) -> bool {
    let path_str = path.to_string_lossy();
    if path_str.ends_with(".db")
        || path_str.ends_with(".db-wal")
        || path_str.ends_with(".db-shm")
        || path_str.ends_with(".db-journal")
        || path_str.contains("clairvoy.db")
    {
        return false;
    }

    for excluded in clairvoy_scanner::EXCLUDED_DIRS {
        for component in path.components() {
            if component.as_os_str() == *excluded {
                return false;
            }
        }
    }

    true
}
