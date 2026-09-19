# Pure Rust Autonomous Background Watcher & SQLite Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a 100% pure Rust autonomous background watcher daemon with a real-time reactive UI progress engine and an ACID-compliant embedded SQLite persistence layer (`~/.clairvoy/clairvoy.db`), replacing flat CSV and JSON files.

**Architecture:** Integrate `rusqlite` (bundled, WAL mode) into `crates/clairvoy-core` for relational persistence. Implement `AutonomousWatcher` using the `notify` crate with a 5-second sliding debounce queue and a 30-minute fallback sweep in `crates/clairvoy-engine`. Connect both to `crates/clairvoy-server` with Server-Sent Events (SSE) and reactive UI progress updates.

**Tech Stack:** Rust (Edition 2021), Axum 0.7, Tokio 1.38, rusqlite 0.32 (bundled), notify 6.1, Google Material Design 3 HTML5/JS.

**Spec:** [`docs/superpowers/specs/2026-09-19-rust-autonomous-watcher-and-sqlite-persistence.md`](file:///home/shubhamshah207/clairvoy/docs/superpowers/specs/2026-09-19-rust-autonomous-watcher-and-sqlite-persistence.md)

## Global Constraints
- Pure Rust architecture: zero Python server dependencies.
- Zero clippy warnings: `cargo clippy --workspace --all-targets -- -D warnings`.
- 100% test pass: `cargo test --workspace`.
- Bounded memory footprint $\le 50\text{MB}$ under continuous background surveillance.
- SQLite database location: `~/.clairvoy/clairvoy.db` with `PRAGMA journal_mode = WAL`.

---

### Task 1: Fix Real-Time Scan Progress Display in Web Dashboard

**Files:**
- Modify: `crates/clairvoy-server/src/index.html:1645-1675,3295-3325`
- Test: `crates/clairvoy-server/tests/test_server.rs`

**Interfaces:**
- Consumes: `/api/status` JSON responses (`status`, `stage`, `progress_pct`, `files_indexed`, `elapsed_seconds`).
- Produces: Smooth DOM progress bar animations, live counter updates, and continuous polling ticks during `running` state.

- [ ] **Step 1: Write failing unit test verifying server returns live progress metrics**

```rust
// In crates/clairvoy-server/tests/test_server.rs
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
```

- [ ] **Step 2: Run test to verify status payload includes all required progress fields**

Run: `export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH" && cargo test -p clairvoy-server --test test_server test_server_live_progress_state`
Expected: PASS (fields present in AppScanState)

- [ ] **Step 3: Update `pollScanStatus()` in `crates/clairvoy-server/src/index.html` to handle running status**

Modify `crates/clairvoy-server/src/index.html`:
```javascript
async function pollScanStatus() {
    try {
        const res = await fetch('/api/status');
        if (!res.ok) return;
        const state = await res.json();
        if (state.status === "completed") {
            clearInterval(pollTimer);
            pollTimer = null;
            const scanBtn = document.getElementById('scanBtn');
            if (scanBtn) scanBtn.disabled = false;
            const startScanBtn = document.getElementById('startScanBtn');
            if (startScanBtn) startScanBtn.disabled = false;
            loadSummaryState(state.summary, state.message);
        } else if (state.status === "failed") {
            clearInterval(pollTimer);
            pollTimer = null;
            const scanBtn = document.getElementById('scanBtn');
            if (scanBtn) scanBtn.disabled = false;
            const startScanBtn = document.getElementById('startScanBtn');
            if (startScanBtn) startScanBtn.disabled = false;
            alert("Scan failed: " + state.message);
        } else if (state.status === "running") {
            updateScanProgressUI(state);
        }
    } catch (e) {
        console.error("Poll error:", e);
    }
}
```

- [ ] **Step 4: Verify progress bar updates dynamically during active scans**

Run: `export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH" && cargo check -p clairvoy-server`
Expected: PASS

- [ ] **Step 5: Commit progress fix**

```bash
git add crates/clairvoy-server/src/index.html crates/clairvoy-server/tests/test_server.rs
git commit -m "fix(ui): ensure live scan progress updates continuously on poll ticks"
```

---

### Task 2: Embedded SQLite Persistence Layer (`clairvoy-core::db`)

**Files:**
- Modify: `crates/clairvoy-core/Cargo.toml`
- Create: `crates/clairvoy-core/src/db.rs`
- Modify: `crates/clairvoy-core/src/lib.rs`
- Test: `crates/clairvoy-core/tests/test_db.rs`

**Interfaces:**
- Produces: `struct Database`, `Database::open(path: Option<&Path>) -> Result<Self>`, `init_schema()`, `insert_scan_run()`, `insert_duplicate_record()`, `get_duplicate_clusters()`, `override_keeper()`, `add_watched_path()`, `list_watched_paths()`, `toggle_watched_path()`, `remove_watched_path()`.

- [ ] **Step 1: Add `rusqlite` dependency to `crates/clairvoy-core/Cargo.toml`**

```toml
rusqlite = { version = "0.32", features = ["bundled"] }
```

- [ ] **Step 2: Write failing tests for SQLite database schema and operations**

Create `crates/clairvoy-core/tests/test_db.rs`:
```rust
use clairvoy_core::db::Database;
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
```

- [ ] **Step 3: Run test to verify it fails (missing db module)**

Run: `export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH" && cargo test -p clairvoy-core --test test_db`
Expected: FAIL with "cannot find module `db`"

- [ ] **Step 4: Implement `crates/clairvoy-core/src/db.rs`**

Write `crates/clairvoy-core/src/db.rs` with WAL mode pragmas, schema initialization, and transactional queries for `watched_paths`, `scan_runs`, `file_index`, `duplicate_clusters`, and `duplicate_items`. Export `pub mod db;` in `crates/clairvoy-core/src/lib.rs`.

- [ ] **Step 5: Run tests to verify all database tests pass**

Run: `export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH" && cargo test -p clairvoy-core --test test_db`
Expected: PASS (2 tests pass)

- [ ] **Step 6: Commit SQLite persistence layer**

```bash
git add crates/clairvoy-core/Cargo.toml crates/clairvoy-core/src/db.rs crates/clairvoy-core/src/lib.rs crates/clairvoy-core/tests/test_db.rs
git commit -m "feat(core): implement high-performance SQLite WAL persistence layer"
```

---

### Task 3: Autonomous Background Watcher Daemon (`clairvoy-engine::watcher`)

**Files:**
- Modify: `crates/clairvoy-engine/Cargo.toml`
- Create: `crates/clairvoy-engine/src/watcher.rs`
- Modify: `crates/clairvoy-engine/src/lib.rs`
- Test: `crates/clairvoy-engine/tests/test_watcher.rs`

**Interfaces:**
- Produces: `struct AutonomousWatcher`, `AutonomousWatcher::start(db: Arc<Mutex<Database>>, debounce_ms: u64, fallback_interval_sec: u64) -> Self`, `stop()`.
- Dispatches: Incremental delta deduplication pipeline on quiet window expiration.

- [ ] **Step 1: Add `notify` dependency to `crates/clairvoy-engine/Cargo.toml`**

```toml
notify = "6.1"
```

- [ ] **Step 2: Write failing unit test for watcher event debouncing and delta pipeline triggering**

Create `crates/clairvoy-engine/tests/test_watcher.rs`:
```rust
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
    db.lock().unwrap().add_watched_path(watch_dir.to_str().unwrap(), true).unwrap();

    let watcher = AutonomousWatcher::start(Arc::clone(&db), 100, 3600).await.unwrap();

    // Create duplicate file
    let file1 = watch_dir.join("test1.txt");
    let file2 = watch_dir.join("test2.txt");
    std::fs::write(&file1, b"hello duplicate content").unwrap();
    std::fs::write(&file2, b"hello duplicate content").unwrap();

    // Allow debounce to fire
    tokio::time::sleep(Duration::from_millis(350)).await;

    let runs = db.lock().unwrap().list_scan_runs(10).unwrap();
    assert!(!runs.is_empty(), "Watcher should have automatically executed a scan run");

    watcher.stop().await;
}
```

- [ ] **Step 3: Run test to verify it fails (missing watcher module)**

Run: `export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH" && cargo test -p clairvoy-engine --test test_watcher`
Expected: FAIL with "cannot find module `watcher`"

- [ ] **Step 4: Implement `AutonomousWatcher` in `crates/clairvoy-engine/src/watcher.rs`**

Features:
- Channels: `tokio::sync::mpsc` for filesystem notifications.
- Debounce loop: sliding quiet window timer resetting on burst modifications.
- Incremental delta crawler: queries `db.get_cached_file()` to skip re-hashing unmodified files.
- Background Tokio task with cancellation token for graceful shutdown.

- [ ] **Step 5: Run test to verify watcher detects files and completes run**

Run: `export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH" && cargo test -p clairvoy-engine --test test_watcher`
Expected: PASS

- [ ] **Step 6: Commit autonomous watcher module**

```bash
git add crates/clairvoy-engine/Cargo.toml crates/clairvoy-engine/src/watcher.rs crates/clairvoy-engine/src/lib.rs crates/clairvoy-engine/tests/test_watcher.rs
git commit -m "feat(engine): implement pure Rust autonomous background watcher with sliding debounce"
```

---

### Task 4: Watcher API & Server-Sent Events in `clairvoy-server`

**Files:**
- Modify: `crates/clairvoy-server/src/routes.rs`
- Modify: `crates/clairvoy-server/src/state.rs`
- Test: `crates/clairvoy-server/tests/test_server.rs`

**Interfaces:**
- Produces routes:
  - `GET /api/watch/paths` — List configured paths with status
  - `POST /api/watch/paths` — Register a directory for autonomous surveillance
  - `POST /api/watch/paths/:id/toggle` — Enable/disable surveillance
  - `DELETE /api/watch/paths/:id` — Deregister a directory
  - `GET /api/status/stream` — Real-time Server-Sent Events (SSE) stream

- [ ] **Step 1: Write failing tests for watch paths management and SSE stream**

Add to `crates/clairvoy-server/tests/test_server.rs`:
```rust
#[tokio::test]
async fn test_server_watch_paths_crud() {
    let app = build_router();
    let server = TestServer::new(app).unwrap();

    let tmp = std::env::temp_dir().join("clairvoy_watch_test");
    let _ = std::fs::create_dir_all(&tmp);

    let res_add = server
        .post("/api/watch/paths")
        .json(&serde_json::json!({ "path": tmp.to_string_lossy(), "recursive": true }))
        .await;
    assert_eq!(res_add.status_code(), 200);

    let res_list = server.get("/api/watch/paths").await;
    assert_eq!(res_list.status_code(), 200);
    let list_body: serde_json::Value = res_list.json();
    assert!(list_body.as_array().unwrap().len() >= 1);
}
```

- [ ] **Step 2: Run test to verify it fails (404 on missing route)**

Run: `export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH" && cargo test -p clairvoy-server --test test_server test_server_watch_paths_crud`
Expected: FAIL with status code 404

- [ ] **Step 3: Implement watch routes and SSE streaming in `crates/clairvoy-server/src/routes.rs`**

- Wire `Database` into `SharedScanState`.
- Implement `handle_watch_paths_list`, `handle_watch_paths_add`, `handle_watch_paths_toggle`, `handle_watch_paths_delete`.
- Implement `handle_status_stream` using `axum::response::sse::{Event, Sse}` with 500ms heartbeat.

- [ ] **Step 4: Run test to verify routes succeed**

Run: `export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH" && cargo test -p clairvoy-server --test test_server test_server_watch_paths_crud`
Expected: PASS

- [ ] **Step 5: Commit server endpoints**

```bash
git add crates/clairvoy-server/src/routes.rs crates/clairvoy-server/src/state.rs crates/clairvoy-server/tests/test_server.rs
git commit -m "feat(server): expose watch targets management and SSE live progress stream"
```

---

### Task 5: Web UI Integration — Autonomous Watcher & SQLite Explorer

**Files:**
- Modify: `crates/clairvoy-server/src/index.html`

**Interfaces:**
- Adds UI:
  - "Autonomous Watcher" configuration section in settings/drawer.
  - Interactive "Watch Folder" button integrated with the directory browser.
  - Active surveillance cards with live status badges (`🟢 Watching`, `🟡 Scanning Delta`).
  - Toggle and remove buttons with immediate state synchronization.

- [ ] **Step 1: Add Autonomous Watcher modal / card in `crates/clairvoy-server/src/index.html`**

Create UI components for:
- Viewing all configured watched directories.
- Adding current browsed folder directly into the autonomous watcher.
- Displaying watcher status (`Active`, `Last scanned: 2 mins ago`).

- [ ] **Step 2: Add client-side JavaScript to fetch `/api/watch/paths` and trigger toggles**

```javascript
async function loadWatchedPaths() {
    try {
        const res = await fetch('/api/watch/paths');
        if (!res.ok) return;
        const paths = await res.json();
        renderWatchedPaths(paths);
    } catch (e) {
        console.error("Failed to load watched paths:", e);
    }
}

async function addCurrentFolderToWatcher() {
    if (!currentBrowsedPath) return;
    const res = await fetch('/api/watch/paths', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: currentBrowsedPath, recursive: true })
    });
    if (res.ok) {
        showToast(`Added ${currentBrowsedPath} to Autonomous Watcher!`, "👁️");
        loadWatchedPaths();
    }
}
```

- [ ] **Step 3: Connect SSE stream listener for real-time progress updates**

```javascript
function initStatusStream() {
    if (!!window.EventSource) {
        const source = new EventSource('/api/status/stream');
        source.onmessage = function(event) {
            try {
                const state = JSON.parse(event.data);
                if (state.status === "running") {
                    updateScanProgressUI(state);
                } else if (state.status === "completed" && state.summary) {
                    loadSummaryState(state.summary, state.message);
                }
            } catch (err) {
                console.error("SSE parse error", err);
            }
        };
    }
}
```

- [ ] **Step 4: Commit UI integration**

```bash
git add crates/clairvoy-server/src/index.html
git commit -m "feat(ui): add autonomous watcher controls and SSE live stream listener"
```

---

### Task 6: Full Workspace Verification & Binary Recompilation

**Files:**
- Modify: `crates/clairvoy-cli/src/main.rs` (start watcher daemon on `ui` command)

- [ ] **Step 1: Initialize `AutonomousWatcher` when `clairvoy-rs ui` starts**

In `crates/clairvoy-cli/src/main.rs`, spawn the `AutonomousWatcher` background service alongside the Axum server.

- [ ] **Step 2: Run full workspace test suite**

Run: `export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH" && cargo test --workspace`
Expected: 100% pass across all crates.

- [ ] **Step 3: Run Clippy with zero warnings**

Run: `export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH" && cargo clippy --workspace --all-targets -- -D warnings`
Expected: 0 errors, 0 warnings.

- [ ] **Step 4: Recompile release binary**

Run: `export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH" && cargo build --workspace --release`
Expected: Release binary generated at `target/release/clairvoy-rs`.

- [ ] **Step 5: Restart server and verify live endpoints**

- Stop previous daemon.
- Launch `./target/release/clairvoy-rs ui --port 8000 --host 0.0.0.0`.
- Verify `GET /api/status`, `GET /api/watch/paths`, and `GET /api/system/browse-directories`.

- [ ] **Step 6: Commit full workspace integration**

```bash
git add .
git commit -m "feat(system): full pure Rust autonomous watcher and SQLite persistence release"
```
