# Clairvoy Architecture & Deep Modules Blueprint

This document details the internal architecture, crate boundaries, data pipelines, and design invariants of Clairvoy.
Clairvoy is an ultra-fast, 100% offline, privacy-first multimodal media deduplication and storage optimization engine built in pure Rust.

---

## 1. System Architecture

Clairvoy follows the **Deep Module** philosophy (*A Philosophy of Software Design*): complex operations (multi-threaded streaming crawl, SIMD quick-hashing, perceptual AI matching, SQLite WAL persistence, background filesystem surveillance, and safe trash manipulation) are encapsulated behind simple, cohesive, and type-safe public interfaces.

```
+---------------------------------------------------------------------------------------------------+
|                                          CLAIRVOY ENGINE                                          |
+---------------------------------------------------------------------------------------------------+
|   +-------------------+          +---------------------+            +-----------------+           |
|   | CLI: clairvoy-rs  |          | Web: Axum Server    |            | Custom Plugins  |           |
|   | crates/clairvoy-cli|         | crates/clairvoy-server|          | clairvoy-plugins|           |
|   +---------+---------+          +----------+----------+            +--------+--------+           |
|             |                               |                                |                    |
|             +-------------------------+     |     +--------------------------+                    |
|                                       v     v     v                                               |
|                            +---------------------------+                                          |
|                            |   DeduplicationPipeline   |                                          |
|                            |  crates/clairvoy-engine   |                                          |
|                            +-------------+-------------+                                          |
|                                          |                                                        |
|             +----------------------------+----------------------------+                           |
|             v                                                         v                           |
|  [Tier 1: ExactHashMatcher]                              [Tier 2: PhotoVisionMatcher]             |
|  Parallel BLAKE3 SIMD Hash                               Perceptual dHash & Model Registry        |
|  (crates/clairvoy-plugins)                               (crates/clairvoy-plugins & model)        |
|             +----------------------------+----------------------------+                           |
|                                          |                                                        |
|                                          v                                                        |
|                            +---------------------------+                                          |
|                            |  CompositeKeeperStrategy  |                                          |
|                            |  (Scoring & Seniority)    |                                          |
|                            +-------------+-------------+                                          |
|                                          |                                                        |
|                                          v                                                        |
|                 +------------------------+-----------------------+                                |
|                 v                        v                       v                                |
|       [Action: Safe Trash]      [Action: Hardlink]      [Action: Perm Delete]                     |
|       .clairvoy_trash/          Zero-space hardlinking  Direct safe unlinking                     |
|       Rollback manifest         Cross-mount fallback    Enforces KEEPER safety                    |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Workspace Crate Breakdown

The repository is organized into 7 focused crates with clean directional dependencies:

```
crates/clairvoy-cli  -->  crates/clairvoy-server  -->  crates/clairvoy-engine
        |                         |                            |
        +-------------------------+                            v
                                  |                 crates/clairvoy-plugins
                                  v                            |
                        crates/clairvoy-core                   v
                                  ^                 crates/clairvoy-model
                                  |                            |
                        crates/clairvoy-scanner <--------------+
```

### 2.1. [`crates/clairvoy-core`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-core)
- **Data Models**: Canonical representations including [`FileEntry`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-core/src/models.rs), [`DuplicateRecord`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-core/src/models.rs), [`DuplicateCluster`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-core/src/models.rs), and [`ScanSummary`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-core/src/models.rs).
- **Traits**: Strong contracts for [`MatcherPlugin`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-core/src/traits.rs), [`KeeperStrategy`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-core/src/traits.rs), and [`ActionHandler`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-core/src/traits.rs).
- **Embedded SQLite Persistence Engine (`clairvoy_core::db::Database`)**:
  - Embedded SQLite database located at `~/.clairvoy/clairvoy.db`.
  - Configured with Write-Ahead Logging (`WAL` mode), `PRAGMA synchronous = NORMAL`, and memory caching for sub-millisecond queries.
  - Normalized schema: `watched_paths`, `scan_runs`, `file_index`, `duplicate_clusters`, `duplicate_items`.
  - Live synchronization APIs: [`Database::remove_duplicate_items`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-core/src/db.rs) and [`Database::prune_missing_files`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-core/src/db.rs).

### 2.2. [`crates/clairvoy-scanner`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-scanner)
- **Streaming Filesystem Crawler**: Parallel multi-threaded directory walking via `jwalk`.
- **Bounded Backpressure**: Uses `flume::bounded(2048)` to guarantee $\le 50\text{MB}$ resident RAM across multi-million file workloads.
- **SIMD XXH3 Quick-Hashing**: Instant candidate grouping using 4KB head hashing at >10 GB/s.

### 2.3. [`crates/clairvoy-model`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-model)
- **Model Runtime Abstraction**: Pluggable `ModelBackend` trait supporting perceptual and neural backends.
- **Built-in Perceptual Hash**: Zero-dependency 64-bit perceptual hash backend (`dHash`).
- **Model Registry**: Dynamic `models.toml` configuration parsing.

### 2.4. [`crates/clairvoy-plugins`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-plugins)
- **Tier 1: `ExactHashMatcherPlugin`**: Bit-for-bit exact duplicate identification using multi-threaded Rayon BLAKE3 hashing.
- **Tier 2: `PhotoVisionMatcherPlugin`**: Perceptual visual duplicate matching with configurable similarity thresholds.

### 2.5. [`crates/clairvoy-engine`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-engine)
- **`DeduplicationPipeline`**: Chained execution engine orchestrating matchers in cost-ascending order with short-circuit pruning.
- **`CompositeKeeperStrategy`**: Deterministic scoring engine evaluating folder seniority, resolution, file size, duplicate token penalties, and modification time.
- **`AutonomousWatcher`**: Real-time filesystem surveillance daemon with 5-second sliding debounce quiet window and 30-minute fallback sweep ticker.

### 2.6. [`crates/clairvoy-server`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-server)
- **High-Throughput Axum Web Server**: Exposes complete REST & SSE API for web UI.
- **Real-Time Telemetry**: Server-Sent Events stream (`/api/status/stream`) broadcasting active phases, duration, and indexed file counts.
- **Integrated Storage Operations**: Soft trash isolation with rollback manifest, permanent unlinking with keeper guards, and POSIX hardlinking.
- **Embedded Web Frontend**: Zero-dependency static SPA embedded directly into the binary (`index.html`).

### 2.7. [`crates/clairvoy-cli`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-cli)
- **Native CLI Executable (`clairvoy-rs`)**:
  - `scan`: Fast non-interactive scan with optional immediate cleaning (`--clean`, `--mode`).
  - `clean`: Process duplicates from stored database runs.
  - `ui`: Launches Axum web studio with optional `--no-daemon`, `--debounce-ms`, and `--port`.

---

## 3. Chained Pipeline & Short-Circuit Pruning

To maximize speed and minimize computation, matchers run strictly in ascending computational cost order:

```
[Candidate Files]
       |
       v
+-------------------------------+
| Tier 1: ExactHashMatcher      | (Cost: Very Low - 4KB XXH3 + Parallel BLAKE3)
+---------------+---------------+
                |
                +---> [Exact Duplicates Found]   ---> Removed from downstream pipeline
                |
                v
+-------------------------------+
| Tier 2: PhotoVisionMatcher    | (Cost: Medium - Perceptual dHash / AI Model)
+---------------+---------------+
                |
                v
       [Combined Clusters]
                |
                v
+-------------------------------+
|    CompositeKeeperStrategy    |
+---------------+---------------+
                |
                v
   [Designated Keepers & Dupes]
```

### Short-Circuit Pruning Guarantee
Once candidate files are grouped into a duplicate cluster by Tier 1 (Exact Hash), they are **immediately removed from the candidate pool** before Tier 2 (Visual AI) executes. This ensures that computationally expensive perceptual hashing is never performed on files already proven to be exact bit-for-bit clones.

---

## 4. Keeper Resolution & Scoring Engine

`CompositeKeeperStrategy` computes a deterministic integer score for each file in a cluster:

| Criteria | Scoring Adjustment | Rationale |
|---|---|---|
| **Media Resolution** | $+(\text{width} \times \text{height})$ | Always prioritize master/uncompressed assets. |
| **File Size** | $+(\text{bytes} / 1024)$ | Higher information density receives bonus. |
| **Clean Path (Seniority)** | $+50$ to $+100$ | Shorter paths and master directories preferred over deep subfolders. |
| **Duplicate Naming Penalty** | $-500$ | Penalizes files containing `copy`, `(1)`, `_1`, `dupe`, or trailing numbers. |
| **Creation/Modification Date** | Tie-breaker | Older timestamp is preserved when all other scores match. |

---

## 5. Google Suite Premier Web UI Architecture

The embedded web interface delivers a premier, 100% offline Google Suite product experience modeled after Google One, Google Photos, and Google Drive:

```
+---------------------------------------------------------------------------------------------------------+
|                                      CLAIRVOY PREMIER WEB STUDIO                                        |
+---------------------------------------------------------------------------------------------------------+
| [Header] 👁️ Clairvoy Studio  |  [ 🔍 Search duplicates... ]  |  [⚡ 1-Click Clean Exact] [⌨️ ?] [🟢 Local]|
|                                                                                                         |
| +---------------------+  +----------------------------------------------------------------------------+ |
| | GOOGLE NAV RAIL     |  | GOOGLE ONE SMART CLEAN 2-TRACK RECOVERY HERO                               | |
| |                     |  | +------------------------------------+ +---------------------------------+ | |
| | [+ New Scan]        |  | | ⚡ 100% Byte-Exact Clones          | | 🔍 Similar Candidates (Review)  | | |
| | [📂 Runs Switcher]  |  | | 0.00 GB • 0 redundant copies       | | 18.42 GB • 3,856 copies         | | |
| |                     |  | | Direct Clean Safe (Bit-for-bit)    | | Needs Human Judgement           | | |
| | VIEWS:              |  | | [⚡ 1-Click Clean Exact]           | | [🔍 Start Guided Review]        | | |
| | [📊 Dashboard]      |  | +------------------------------------+ +---------------------------------+ | |
| | [🖼️ Photos Studio]  |  +----------------------------------------------------------------------------+ |
| | [📁 Drive Table]    |  | TOP SHOT SIDE-BY-SIDE COMPARISON STUDIO                                    | |
| | [👁️ Auto Watcher]   |  | [★ KEEPER: Master 4K.jpg]    [⇄ 1-Click Swap]    [DUPLICATE: Copy (1).jpg]   | |
| |                     |  | [Synchronized Loupe Zoom]                         [Synchronized Loupe Zoom]  | |
| | STORAGE GAUGE:      |  +----------------------------------------------------------------------------+ |
| | [ 18.42 GB Clones ] |  | GOOGLE DRIVE STRUCTURED WORKSPACE                                          | |
| | 3,856 Duplicates    |  | Density: [Compact | Standard | Comfortable]  Columns: [Name | Size | Path] | |
| +---------------------+  +----------------------------------------------------------------------------+ |
+---------------------------------------------------------------------------------------------------------+
```

### Key Interactive Features:
1. **Google One 2-Track Smart Clean Recovery**:
   - **Track 1 (100% Byte-Exact Clones)**: Bit-for-bit identical hashes (`EXACT_HASH`). Can be batch cleaned into Trash or Quarantine with 1 click without manual review.
   - **Track 2 (Similar Candidates)**: Resized photos, drafts, or bursts. Single primary action: `[ 🔍 Start Guided Review ]` launching the comparison studio.
2. **Google Photos Top Shot Comparison Studio**:
   - Side-by-side split view comparing designated Keeper against duplicate candidates.
   - Synchronized loupe zoom and pan tracking cursor movement across both images simultaneously.
   - 1-click Keeper promotion (`[★ Make Keeper]`) and instant candidate trashing.
3. **Google Drive Structured Workspace**:
   - Sortable multi-column table view for bulk review across deep folder hierarchies.
   - Density switcher (`Compact`, `Standard`, `Comfortable`).
4. **Safe Deletion Engine**:
   - **Soft Delete (Trash)**: Relocates duplicate files to `.clairvoy_trash/` with a timestamped manifest for 1-click undo.
   - **Permanent Deletion**: Direct unlinking strictly asserting that keeper files can never be deleted.
   - **Zero-Space Hardlinking**: Safely substitutes duplicate files with native filesystem hardlinks.
