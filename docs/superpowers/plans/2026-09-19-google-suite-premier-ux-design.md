# Google Suite Premier UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Google-Suite-inspired Premier UX across Clairvoy Studio, integrating the Google One Smart Clean 2-track recovery system, Google Photos Top Shot side-by-side comparison studio with synchronized zoom, Google Drive high-density table mode with breadcrumbs, and Google Cloud collapsible ambient telemetry dock.

**Architecture:** Pure Rust Axum server serving single-bundle Google Material Design 3 application (`crates/clairvoy-server/src/index.html`) backed by embedded SQLite WAL persistence (`clairvoy-core::db`), streaming real-time Server-Sent Events (`/api/status/stream`), and zero-clobber deletion engines (`/api/delete/execute`).

**Tech Stack:** Rust Edition 2021, Axum 0.7, TailwindCSS (dark M3 palette), Vanilla JavaScript (ES2022 zero-dependency), EventSource SSE, SQLite WAL via rusqlite.

**Spec:** [`docs/superpowers/specs/2026-09-19-google-suite-premier-ux-design.md`](file:///home/shubhamshah207/clairvoy/docs/superpowers/specs/2026-09-19-google-suite-premier-ux-design.md)

## Global Constraints
- Pure Rust architecture: zero Python server dependencies.
- Zero clippy warnings: `cargo clippy --workspace --all-targets -- -D warnings`.
- 100% test pass: `cargo test --workspace`.
- Material Design 3 dark palette tokens (`#131314` bg, `#1e1f20` surface, `#28292a` container, `#8ab4f8` primary, `#81c995` emerald keeper, `#fdd663` amber warning, `#f28b82` error).
- Reversible safety: soft-trash default with 30-day retention and instant undo snackbar.
- ASCII art only for all diagrammatic outputs.

---

### Task 1: Google One Smart Clean Two-Track System

**Files:**
- Modify: `crates/clairvoy-server/src/index.html`
- Test: `crates/clairvoy-server/tests/test_server.rs`

**Interfaces:**
- Produces in `index.html`:
  - `#smartCleanHero`: Upgraded Google One storage recovery card.
  - `#smartCleanProjection`: Before/after storage projection gauge.
  - `#trackExactCleanBtn`: 1-Click exact clone batch cleaner.
  - `#trackSimilarReviewBtn`: Router button to launch set-by-set review.
  - `executeExactBatchClean()`: Collects all duplicate paths in exact hash clusters and triggers `/api/delete/execute` with mode `trash`, preserving all `KEEPER` files.
  - `showUndoSnackbar(count, bytes, mode)`: Floating Google-style snackbar with reversible undo trigger.

- [ ] **Step 1: Write integration test for Google One Smart Clean elements in `test_server.rs`**

Add to `crates/clairvoy-server/tests/test_server.rs`:
```rust
#[tokio::test]
async fn test_server_smart_clean_two_track_elements() {
    let app = build_router();
    let server = TestServer::new(app).unwrap();

    let res = server.get("/").await;
    assert_eq!(res.status_code(), 200);
    let html = res.text();
    assert!(html.contains("smartCleanHero"));
    assert!(html.contains("executeExactBatchClean"));
    assert!(html.contains("trackExactCleanBtn"));
    assert!(html.contains("trackSimilarReviewBtn"));
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH" && cargo test -p clairvoy-server --test test_server test_server_smart_clean_two_track_elements`
Expected: FAIL with assertion on missing `trackExactCleanBtn` or `executeExactBatchClean`.

- [ ] **Step 3: Implement Google One Two-Track Card in `crates/clairvoy-server/src/index.html`**

Update `#smartCleanHero` in `crates/clairvoy-server/src/index.html`:
1. Render Track A (`100% Exact Clones`) with recoverable GB, file count, and prominent button `[ 🗑️ Clean All Exact Duplicates ]` that calls `executeExactBatchClean()`.
2. Render Track B (`Similar & Burst Media`) with count of reviewable groups and button `[ 🖼️ Review Similar Media ]` that filters gallery to `SIMILAR`.
3. Render visual Storage Projection Gauge showing current storage vs projected storage post-clean.
4. Implement `executeExactBatchClean()`:
   - Filters `currentClusters` where `match_type === "EXACT_HASH"`.
   - Gathers all non-keeper duplicate paths (`action === "DUPLICATE"`).
   - Confirms total count and GB with user.
   - Calls `/api/delete/execute` with `{ paths, mode: 'trash' }`.
   - Triggers `showToast("Cleaned X exact duplicates (Y GB freed)", "🗑️")` with floating undo option.
   - Refreshes cluster list and summary state.

- [ ] **Step 4: Run test to verify it passes**

Run: `export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH" && cargo test -p clairvoy-server --test test_server test_server_smart_clean_two_track_elements`
Expected: PASS.

- [ ] **Step 5: Commit changes**

```bash
git add crates/clairvoy-server/src/index.html crates/clairvoy-server/tests/test_server.rs
git commit -m "feat(ui): implement Google One 2-track smart clean recovery system"
```

---

### Task 2: Google Photos Top Shot Comparison Studio (Split-Screen Diff Lightbox)

**Files:**
- Modify: `crates/clairvoy-server/src/index.html`
- Test: `crates/clairvoy-server/tests/test_server.rs`

**Interfaces:**
- Produces in `index.html`:
  - Upgraded `#lightboxModal` into dual-pane split comparison canvas:
    - Left Pane: Candidate / Duplicate Copy.
    - Right Pane: Designated Keeper (Original).
  - Automated quality differential ribbons:
    - Resolution comparison (`🟢 Higher Resolution` / `12.2 MP vs 3.1 MP`).
    - File size & bitrate comparison (`🟢 Higher Quality` / `4.8 MB vs 1.4 MB`).
    - Date comparison (`🟢 Older Original Date`).
  - Synchronized Loupe Zoom (`syncLoupeZoom(event)`):
    - Moving cursor over candidate or keeper magnifies both images at identical relative `(x, y)` percentages.
  - 1-Click Keeper Swap (`swapKeeperRole()`):
    - Reassigns keeper to candidate and commits change via `POST /api/clusters/override-keeper`.
  - Keyboard shortcuts: `←`/`→` (prev/next cluster), `Space` (toggle delete selection), `K` (swap keeper), `Esc` (close).

- [ ] **Step 1: Write integration test for Comparison Studio in `test_server.rs`**

Add to `crates/clairvoy-server/tests/test_server.rs`:
```rust
#[tokio::test]
async fn test_server_comparison_studio_elements() {
    let app = build_router();
    let server = TestServer::new(app).unwrap();

    let res = server.get("/").await;
    assert_eq!(res.status_code(), 200);
    let html = res.text();
    assert!(html.contains("comparisonStudioModal") || html.contains("splitComparisonCanvas"));
    assert!(html.contains("syncLoupeZoom"));
    assert!(html.contains("swapKeeperFromStudio"));
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH" && cargo test -p clairvoy-server --test test_server test_server_comparison_studio_elements`
Expected: FAIL with assertion on missing `splitComparisonCanvas`.

- [ ] **Step 3: Implement Comparison Studio in `crates/clairvoy-server/src/index.html`**

1. Restructure `#lightboxModal` into a two-pane flex layout with:
   - Header showing cluster group ID, match score, category badge, and keyboard help indicator.
   - Dual visual canvases: Left canvas showing Candidate, Right canvas showing Keeper.
   - Image metadata comparison cards below each image displaying resolution, MP, filesize, and relative date.
   - Automated quality badges dynamically comparing dimensions and sizes between candidate and keeper.
2. Implement synchronized zoom loupe:
   - Listen to `mousemove` on both canvas wrappers.
   - Compute cursor percentage `(offsetX / width, offsetY / height)`.
   - Apply `transform: scale(2) translate(...)` simultaneously to both image elements.
   - Add zoom level buttons: `1x`, `2x`, `4x`.
3. Implement `swapKeeperFromStudio()`:
   - Promotes candidate to keeper.
   - Calls `POST /api/clusters/override-keeper`.
   - Re-renders comparison canvases with updated keeper badge.
4. Bind keyboard events in `window.addEventListener('keydown')`:
   - `ArrowLeft`: previous cluster.
   - `ArrowRight`: next cluster.
   - `KeyK`: swap keeper.
   - `Space`: toggle duplicate item selection.
   - `Escape`: close studio.

- [ ] **Step 4: Run test to verify it passes**

Run: `export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH" && cargo test -p clairvoy-server --test test_server test_server_comparison_studio_elements`
Expected: PASS.

- [ ] **Step 5: Commit changes**

```bash
git add crates/clairvoy-server/src/index.html crates/clairvoy-server/tests/test_server.rs
git commit -m "feat(ui): implement Google Photos Top Shot comparison studio with synchronized loupe zoom"
```

---

### Task 3: Google Drive Structured Workspace & Density Switcher

**Files:**
- Modify: `crates/clairvoy-server/src/index.html`
- Test: `crates/clairvoy-server/tests/test_server.rs`

**Interfaces:**
- Produces in `index.html`:
  - View switcher in toolbar: `[ ▦ Grid ]` and `[ ☰ Table ]`.
  - `renderTableView(clusters)`: Generates high-density tabular view with sortable columns:
    - Selection Checkbox
    - Role (`★ KEEPER` vs `⚠️ DUPLICATE`)
    - File Name & Directory Path (with copy path button)
    - File Size
    - Resolution / Dimensions
    - Match Confidence & Tier
    - Contextual Hover Action Pills (`Compare 👁️`, `Reveal in Drive 📁`, `Trash 🗑️`)
  - Breadcrumb navigation component showing folder hierarchy.

- [ ] **Step 1: Write integration test for Table View and View Switcher in `test_server.rs`**

Add to `crates/clairvoy-server/tests/test_server.rs`:
```rust
#[tokio::test]
async fn test_server_drive_structured_view_elements() {
    let app = build_router();
    let server = TestServer::new(app).unwrap();

    let res = server.get("/").await;
    assert_eq!(res.status_code(), 200);
    let html = res.text();
    assert!(html.contains("btnViewTable"));
    assert!(html.contains("renderTableView"));
    assert!(html.contains("tableSortColumn"));
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH" && cargo test -p clairvoy-server --test test_server test_server_drive_structured_view_elements`
Expected: FAIL.

- [ ] **Step 3: Implement Dense Table Mode and Density Switcher in `crates/clairvoy-server/src/index.html`**

1. Add `#btnViewGrid` and `#btnViewTable` pills to the toolbar.
2. Store `currentViewLayout: 'grid' | 'table'` in client state.
3. Implement `renderTableView(clusters)`:
   - Renders a clean Material Design 3 table with sticky headers.
   - Clicking column headers (`tableSortColumn(col)`) toggles sort order by `name`, `size`, `score`, or `role`.
   - Shows folder breadcrumbs at the top of table groups.
   - Row hover reveals quick-action pills (`Compare`, `Open Folder`, `Quick Trash`).
   - Checkbox selection seamlessly integrates with the top selection bar (`#selectionHeader`).

- [ ] **Step 4: Run test to verify it passes**

Run: `export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH" && cargo test -p clairvoy-server --test test_server test_server_drive_structured_view_elements`
Expected: PASS.

- [ ] **Step 5: Commit changes**

```bash
git add crates/clairvoy-server/src/index.html crates/clairvoy-server/tests/test_server.rs
git commit -m "feat(ui): implement Google Drive structured table workspace with sortable columns"
```

---

### Task 4: Google Cloud Ambient Telemetry Dock & Hardlink Safety Ladder

**Files:**
- Modify: `crates/clairvoy-server/src/index.html`
- Test: `crates/clairvoy-server/tests/test_server.rs`

**Interfaces:**
- Produces in `index.html`:
  - Floating bottom dock `#bottomTelemetryDock`:
    - Displays: `🟢 Watcher: Monitoring X dirs • Inotify: Listening • Last Sync: Xm ago`.
    - Expand button `[ ^ Activity Log ]` that opens collapsible drawer showing recent events and SQLite WAL sync history.
  - Hardlink action option in selection bar and trash dialogs:
    - `[ 🔗 Replace with Hardlinks (0 Byte deduction) ]` calling `/api/delete/execute` or dedicated hardlink route.

- [ ] **Step 1: Write integration test for Ambient Telemetry Dock in `test_server.rs`**

Add to `crates/clairvoy-server/tests/test_server.rs`:
```rust
#[tokio::test]
async fn test_server_ambient_telemetry_dock_elements() {
    let app = build_router();
    let server = TestServer::new(app).unwrap();

    let res = server.get("/").await;
    assert_eq!(res.status_code(), 200);
    let html = res.text();
    assert!(html.contains("bottomTelemetryDock"));
    assert!(html.contains("toggleActivityDrawer"));
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH" && cargo test -p clairvoy-server --test test_server test_server_ambient_telemetry_dock_elements`
Expected: FAIL.

- [ ] **Step 3: Implement Ambient Telemetry Dock in `crates/clairvoy-server/src/index.html`**

1. Add fixed bottom pill `#bottomTelemetryDock` with glassmorphic background (`bg-[#1e1f20]/90 backdrop-blur border border-white/10`).
2. Wire real-time telemetry from `/api/status` and `/api/status/stream`:
   - Number of active watched directories.
   - Daemon state (`Active`, `Paused`, `Standby`).
   - SQLite WAL sync status.
3. Add slide-up `#activityDrawerModal` displaying event history and timestamps.
4. Enhance selection action bar with `[ 🔗 Hardlink ]` option that preserves file references while reclaiming 100% of underlying disk blocks.

- [ ] **Step 4: Run test to verify it passes**

Run: `export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH" && cargo test -p clairvoy-server --test test_server test_server_ambient_telemetry_dock_elements`
Expected: PASS.

- [ ] **Step 5: Commit changes**

```bash
git add crates/clairvoy-server/src/index.html crates/clairvoy-server/tests/test_server.rs
git commit -m "feat(ui): implement Google Cloud ambient telemetry dock and activity drawer"
```

---

### Task 5: Full Workspace Verification & Release Build

**Files:**
- Modify: `crates/clairvoy-server/src/index.html`
- Update: `AGENTS.md` (if needed)

- [ ] **Step 1: Run full workspace test suite**

Run: `export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH" && cargo test --workspace`
Expected: 100% pass across all crates.

- [ ] **Step 2: Run Clippy with zero warnings**

Run: `export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH" && cargo clippy --workspace --all-targets -- -D warnings`
Expected: 0 warnings, 0 errors.

- [ ] **Step 3: Recompile release binary**

Run: `export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH" && cargo build --workspace --release`
Expected: Release binary compiled to `./target/release/clairvoy-rs`.

- [ ] **Step 4: Live server restart & verification**

- Restart background server on port 8000.
- Verify live UI and endpoints via curl.

- [ ] **Step 5: Final integration commit**

```bash
git add .
git commit -m "feat(system): release Google Suite premier UX design system across Clairvoy"
```
