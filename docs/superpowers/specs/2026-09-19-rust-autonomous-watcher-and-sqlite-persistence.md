# Pure Rust Autonomous Background Watcher & SQLite Persistence Specification

**Status:** Proposed  
**Date:** 2026-09-19  
**Author:** Antigravity Team  
**Scope:** `crates/clairvoy-server`, `crates/clairvoy-engine`, `crates/clairvoy-core`, `crates/clairvoy-cli`, Embedded Web Dashboard  

---

## 1. Executive Summary & Vision

Clairvoy is focusing exclusively on its **pure Rust engine and web server**, deprecating the legacy Python server implementation. To deliver a true "set-it-and-forget-it" storage optimization experience, this specification details three core architectural capabilities:

1. **Live Real-Time Run Progress Engine:**
   Eliminate polling silent failures in the Google Material Design 3 single-page application so that active crawl rates, SIMD hashing stages, files indexed, and percentage bars update live with zero lag.

2. **Autonomous Background Watcher Daemon (Hybrid inotify + Sweep):**
   Allow users to configure directory paths in the dashboard or CLI. The pure Rust daemon continuously monitors these paths in the background using OS filesystem events (`notify` crate / Linux `inotify`), batches changes with a 5-second quiet window debounce, runs incremental delta deduplication, and performs a 30-minute fallback sweep without requiring manual scan clicks.

3. **High-Performance SQLite Persistence (`~/.clairvoy/clairvoy.db`):**
   Replace flat CSV report files and multi-megabyte monolithic JSON files (`clairvoy_summary.json` and `runs.json`) with an ACID-compliant embedded SQLite database operating in Write-Ahead Logging (`WAL`) mode via `rusqlite`. Provides sub-millisecond query performance, paginated cluster browsing, instant keeper swaps, and transactional consistency.

---

## 2. High-Level Architecture Overview

```
+----------------------------------------------------------------------------------------------------+
|                                    AUTONOMOUS CONTINUOUS CLAIRVOY                                  |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|  [Web UI / Config Panel (Google Material Design 3 SPA)]                                            |
|  * Watch Paths Manager: Add, toggle, and view active surveillance roots                             |
|  * Real-Time Progress Stream: Live files counter, progress %, hashing rate, active stage            |
|  * Instant SQLite Duplicate Browser: Sub-millisecond category filtering, cluster pagination         |
|                                         ^                                                          |
|                                         | REST & Server-Sent Events (SSE)                          |
|                                         v                                                          |
|  [Pure Rust Axum Web Server (crates/clairvoy-server)]                                              |
|  +----------------------------------------------------------------------------------------------+  |
|  | Autonomous Background Watcher Service                                                        |  |
|  |  * Real-Time OS inotify (via `notify` crate) -> captures Create/Modify/Remove/Rename          |  |
|  |  * Tokio Debounce Queue (5s quiet buffer prevents thrashing during active file copies)        |  |
|  |  * Periodic Fallback Consistency Sweeper (every 30m) handles dropped buffer events           |  |
|  +----------------------------------------------------------------------------------------------+  |
|                                         |                                                          |
|                                         v                                                          |
|  [Incremental Delta Deduplication Pipeline (crates/clairvoy-engine)]                               |
|  * Queries SQLite File Index: if (path, mtime, size) unchanged -> Skip disk hashing ($O(1)$)      |
|  * Only hashes new/modified files via XXH3 SIMD + BLAKE3                                           |
|  * Incrementally computes duplicate clusters and keeper recommendations                            |
|                                         |                                                          |
|                                         v                                                          |
|  [Embedded SQLite Database: ~/.clairvoy/clairvoy.db (rusqlite)]                                    |
|  * PRAGMA journal_mode = WAL; PRAGMA synchronous = NORMAL; PRAGMA temp_store = MEMORY;             |
|  * Tables: `watched_paths`, `scan_runs`, `file_index`, `duplicate_clusters`, `duplicate_items`     |
|  * Completely replaces monolithic CSV exports and large JSON files                                 |
+----------------------------------------------------------------------------------------------------+
```

---

## 3. Subsystem Specifications

### Subsystem A: Live Progress Display & State Streaming

#### Current Defect & Root Cause
In `crates/clairvoy-server/src/index.html`, `pollScanStatus()` evaluates:
```javascript
if (state.status === "completed") { ... }
else if (state.status === "failed") { ... }
```
When `state.status === "running"`, the handler was completely omitted. Consequently, polling responses were received by the browser but silently discarded, leaving the progress bar frozen at its initial 3% state.

#### Architectural Rectification
1. **Frontend Polling Fix:**
   - Add explicit `else if (state.status === "running") { updateScanProgressUI(state); }`.
   - Ensure progress percentage, indexed files counter, elapsed duration, and stage description (`Phase 1: Scanning Filesystem`, `Phase 2: BLAKE3 Content Hashing`) animate smoothly.
   - Synchronize modal dismiss and drawer trigger buttons (`#startScanBtn`, `#scanBtn`).
2. **Server-Sent Events (SSE) Endpoint:**
   - Expose `GET /api/status/stream` via `axum::response::sse::Sse`.
   - Pushes live status frames on every state transition or progress tick without HTTP polling overhead.
   - Keep `GET /api/status` polling as a fallback.

---

### Subsystem B: Autonomous Background Watcher Daemon

#### Objectives
- Allow users to specify one or more directories to watch (e.g. `/mnt/e/Photos`, `/mnt/e/Downloads`).
- Automatically detect new, modified, or deleted files without requiring manual "Start Scan" actions.
- Never freeze the UI or thrash storage during active downloads, unzips, or multi-gigabyte transfers.

#### Components
1. **Watch Registry:**
   - Stored in SQLite table `watched_paths`.
   - REST API:
     - `GET /api/watch/paths` — List all configured watch roots and their live status (`Active`, `Idle`, `Scanning`).
     - `POST /api/watch/paths` — Add a directory to watch (validates path exists and is a directory).
     - `POST /api/watch/paths/:id/toggle` — Enable/disable surveillance for a path.
     - `DELETE /api/watch/paths/:id` — Remove a watched directory.
2. **Hybrid Watcher Implementation:**
   - **Real-time Event Stream:** Uses `notify::RecommendedWatcher` with non-blocking event channel. Subscribes to recursive events on all enabled paths.
   - **Debounce Queue:** Events are forwarded to a Tokio channel with a 5-second sliding debounce timer. If new filesystem events arrive within 5 seconds, the timer resets. Once the quiet period expires, the batched set of changed paths is sent to the delta deduplicator.
   - **Periodic Fallback Consistency Sweep:** A background Tokio interval (default: 30 minutes) performs an incremental crawler check across watched paths, catching any events dropped due to inotify queue saturation.
3. **Incremental Delta Deduplication:**
   - For every candidate file, queries SQLite `file_index` by `(path, size_bytes, modified_epoch)`.
   - If metadata matches an existing entry, the cached quick-hash and full-hash are reused with zero disk reads.
   - Only genuinely new or modified files undergo SIMD XXH3 / BLAKE3 hashing.
   - Deleted files are pruned from clusters; clusters are dynamically updated in SQLite.

---

### Subsystem C: High-Performance SQLite Persistence Engine

#### Objectives
- Replace flat CSV exports and massive JSON summary files with an indexed, transactional, zero-bloat embedded database at `~/.clairvoy/clairvoy.db`.
- Sub-millisecond query performance for filtering duplicates by category, similarity score, size, or path.
- Zero risk of JSON parse corruption or high memory consumption on large (50,000+ files) workloads.

#### Database Configuration
Using `rusqlite` bundled with SQLite 3.45+:
```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA temp_store = MEMORY;
PRAGMA cache_size = -64000; -- 64MB cache
PRAGMA foreign_keys = ON;
```

#### Relational Schema
```sql
CREATE TABLE IF NOT EXISTS watched_paths (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    recursive BOOLEAN NOT NULL DEFAULT 1,
    enabled BOOLEAN NOT NULL DEFAULT 1,
    last_scanned_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scan_runs (
    run_id TEXT PRIMARY KEY,
    timestamp DATETIME NOT NULL,
    scanned_paths TEXT NOT NULL, -- JSON array of target paths
    total_files INTEGER NOT NULL DEFAULT 0,
    duplicate_groups INTEGER NOT NULL DEFAULT 0,
    wasted_bytes INTEGER NOT NULL DEFAULT 0,
    duration_seconds REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'completed'
);

CREATE TABLE IF NOT EXISTS file_index (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    size_bytes INTEGER NOT NULL,
    modified_epoch INTEGER NOT NULL,
    quick_hash TEXT NOT NULL,
    full_hash TEXT,
    category TEXT NOT NULL,
    last_seen_run TEXT,
    FOREIGN KEY(last_seen_run) REFERENCES scan_runs(run_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_file_index_lookup ON file_index(path, size_bytes, modified_epoch);
CREATE INDEX IF NOT EXISTS idx_file_index_hashes ON file_index(quick_hash, full_hash);
CREATE INDEX IF NOT EXISTS idx_file_index_category ON file_index(category);

CREATE TABLE IF NOT EXISTS duplicate_clusters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    cluster_id INTEGER NOT NULL,
    match_type TEXT NOT NULL,
    category TEXT NOT NULL,
    similarity_score REAL NOT NULL,
    FOREIGN KEY(run_id) REFERENCES scan_runs(run_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_clusters_run_cat ON duplicate_clusters(run_id, category);

CREATE TABLE IF NOT EXISTS duplicate_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_id INTEGER NOT NULL,
    path TEXT NOT NULL,
    action TEXT NOT NULL, -- 'KEEP' | 'DUPLICATE'
    size_bytes INTEGER NOT NULL,
    dimensions TEXT,
    FOREIGN KEY(cluster_id) REFERENCES duplicate_clusters(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_duplicate_items_cluster ON duplicate_items(cluster_id);
CREATE INDEX IF NOT EXISTS idx_duplicate_items_path ON duplicate_items(path);
```

---

## 4. API Endpoints Specification

| Method | Route | Description |
|---|---|---|
| `GET` | `/api/status` | Current scan and watcher daemon status |
| `GET` | `/api/status/stream` | Server-Sent Events (SSE) live progress feed |
| `POST` | `/api/scan` | Initiate an immediate parallel scan across targets |
| `GET` | `/api/watch/paths` | List all configured watched folders and live statuses |
| `POST` | `/api/watch/paths` | Add new folder to background surveillance |
| `POST` | `/api/watch/paths/:id/toggle` | Enable or disable surveillance for a path |
| `DELETE` | `/api/watch/paths/:id` | Remove a folder from background surveillance |
| `GET` | `/api/duplicates` | Paginated query of duplicate clusters from SQLite (`?run_id=&category=&page=&limit=`) |
| `POST` | `/api/clusters/override-keeper` | Update designated keeper file in SQLite transaction |
| `POST` | `/api/delete/execute` | Soft-trash or permanently unlink duplicate files |
| `POST` | `/api/quarantine/execute` | Move duplicate files to quarantine directory |
| `GET` | `/api/runs` | Fetch historical scan runs from SQLite |

---

## 5. Migration Strategy & Python Server Deprecation

1. **Python Server Deprecation:**
   - The Python server (`clairvoy/web/app.py`) is marked deprecated.
   - CLI invocation `clairvoy ui` directly starts the pure Rust release binary.
   - All background watcher daemon tasks and SQLite persistence are written natively in Rust.
2. **Backward Compatibility:**
   - `ScanSummary` JSON serialization remains supported for export/import compatibility.
   - On first startup, the Rust server checks for existing `~/.clairvoy/runs.json` and automatically migrates past records into `~/.clairvoy/clairvoy.db`.

---

## 6. Verification & Test Plan

1. **Unit Tests:**
   - Database migration and CRUD operations (`test_sqlite_persistence.rs`).
   - Debounce queue logic with simulated fast-burst file operations.
   - Delta file index matching with unmodified metadata ($O(1)$ skip test).
2. **Integration Tests:**
   - Real-time inotify watcher triggers delta deduplication upon creating duplicate files in a watched directory.
   - Fallback sweep correctly synchronizes changes made while watcher was paused.
   - SSE and REST status endpoints verify progress reporting during active crawls.
3. **Quality Standards:**
   - Zero clippy warnings: `cargo clippy --workspace --all-targets -- -D warnings`.
   - 100% test pass: `cargo test --workspace`.
   - Memory resident set size $\le 50\text{MB}$ under continuous watching.
