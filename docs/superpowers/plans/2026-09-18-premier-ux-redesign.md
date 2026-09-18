# Premier UX Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Overhaul Clairvoy's Web Interface into a premier, CleanMyMac & Immich-inspired storage optimization studio featuring a Hero Storage Meter, interactive category tabs, side-by-side comparison lightbox, manual keeper overrides, instant search, fast pagination, and a sticky quarantine action dock.

**Architecture:** Extend FastAPI backend with a cluster keeper-override endpoint (`/api/clusters/override-keeper`) and rebuild the frontend in `clairvoy/web/app.py` with modern Tailwind CSS, client-side pagination over 10,000+ clusters, interactive modal overlays, and responsive micro-interactions.

**Tech Stack:** Python 3.12+, FastAPI, Uvicorn, Tailwind CSS, Pure Vanilla JavaScript (zero external dependencies for 100% offline air-gapped security), Pytest.

**Spec:** [`docs/superpowers/specs/2026-09-18-premier-ux-design-system.md`](file:///home/shubhamshah207/clairvoy/docs/superpowers/specs/2026-09-18-premier-ux-design-system.md)

## Global Constraints
- 100% offline, local-first execution; no external cloud calls or CDN dependencies that fail offline.
- Zero-clobber safety invariants preserved.
- Python 3.12+ type annotations.
- Full test suite in `pytest -v` and `ruff check .` must pass with 100% success and 0 errors.
- All chat/terminal diagrams must be clean ASCII art using box-drawing characters.

---

### Task 1: Backend Keeper Override Endpoint (`/api/clusters/override-keeper`)

**Files:**
- Modify: `clairvoy/web/app.py`
- Test: `tests/test_web_api.py`

**Interfaces:**
- Produces:
  - `POST /api/clusters/override-keeper`: accepts `{"group_id": int, "new_keeper_path": str}`, updates `SCAN_STATE["summary"]` in place, swapping the former keeper to `DUPLICATE` and designating the chosen file as `KEEP`.

- [x] **Step 1: Write unit test for keeper override endpoint**
In `tests/test_web_api.py`, add `test_override_keeper_endpoint` testing that swapping a keeper in an active summary updates records and actions correctly.

- [x] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_web_api.py -k test_override_keeper_endpoint -v`
Expected: FAIL (404 Not Found)

- [x] **Step 3: Implement endpoint in `clairvoy/web/app.py`**
Implement `KeeperOverrideRequest` model and `POST /api/clusters/override-keeper`.

- [x] **Step 4: Run test to verify it passes**
Run: `pytest tests/test_web_api.py -k test_override_keeper_endpoint -v`
Expected: PASS

- [x] **Step 5: Commit**
```bash
git add clairvoy/web/app.py tests/test_web_api.py
git commit -m "feat(web): add /api/clusters/override-keeper endpoint"
```

---

### Task 2: Hero Storage Meter & Category Distribution Component

**Files:**
- Modify: `clairvoy/web/app.py`

**Interfaces:**
- Produces:
  - Large Hero Storage Banner displaying total reclaimable space with animated progress bar segmented by category (Photos, Documents, Screenshots, Graphics, Files) with distinct colors and percentage tooltips.
  - KPI Stat Grid: Total Scanned Files, Exact Duplicates, AI Near-Duplicates, Reclaimable Space.

- [x] **Step 1: Build HTML template and CSS for Hero Storage Meter**
Implement in `clairvoy/web/app.py` inside `serve_index()`.

- [x] **Step 2: Implement JS dynamic computation of category percentages**
Update `renderSummary()` in JS to calculate and render the multi-colored segmented bar based on category wasted bytes.

- [x] **Step 3: Verify page renders cleanly via pytest**
Run: `pytest tests/test_web_api.py -v`
Expected: PASS

- [x] **Step 4: Commit**
```bash
git add clairvoy/web/app.py
git commit -m "feat(ui): add CleanMyMac-inspired Hero Storage Meter and category breakdown bar"
```

---

### Task 3: Interactive Filter Toolbar, Search, & High-Performance Pagination

**Files:**
- Modify: `clairvoy/web/app.py`

**Interfaces:**
- Produces:
  - Modality Filter Tabs with live item counts: All, Photos, Screenshots, Documents, Graphics, Files.
  - Match Type dropdown: All, Exact Hash (100%), Vision AI (95%+), Content Near-Duplicate.
  - Sort selector: Largest Wasted Size, Most Duplicates, Similarity Score.
  - Instant search input with debouncing across file names and parent folder paths.
  - Client-side pagination engine rendering 25, 50, or 100 clusters per page smoothly.

- [x] **Step 1: Add HTML markup for tabs, search bar, sort dropdown, and pagination controls**
In `clairvoy/web/app.py`.

- [x] **Step 2: Implement client-side filtering, searching, and pagination state in JavaScript**
Add `filterAndPaginateClusters()`, `onSearchChange()`, `changePage()`, and `onPerPageChange()`.

- [x] **Step 3: Verify tests pass**
Run: `pytest tests/test_web_api.py -v`
Expected: PASS

- [x] **Step 4: Commit**
```bash
git add clairvoy/web/app.py
git commit -m "feat(ui): implement multi-facet filtering, instant search, and fast pagination"
```

---

### Task 4: Cluster Cards with "Make Keeper" Overrides & Side-by-Side Lightbox Modal

**Files:**
- Modify: `clairvoy/web/app.py`

**Interfaces:**
- Produces:
  - Redesigned cluster cards with visual differentiation between `KEEP` (emerald border, star badge) and `DUPLICATE` (amber/rose badge with quarantine inclusion checkbox).
  - In-card "★ Make Keeper" button that calls `/api/clusters/override-keeper` and live-updates the cluster UI without page reload.
  - Comparison Lightbox Modal: Side-by-side synchronized view comparing Keeper vs Duplicate with full metadata diff table (resolution, size, mtime, path).

- [x] **Step 1: Implement Cluster Card HTML/JS rendering with keeper/duplicate styling**
In `clairvoy/web/app.py`.

- [x] **Step 2: Implement Side-by-Side Lightbox Modal HTML and JS open/close/inspect logic**
Add `openComparisonModal(groupId, itemIndex)` and `closeComparisonModal()`.

- [x] **Step 3: Implement client-side keeper override wiring**
Add `setKeeper(groupId, itemPath)`.

- [x] **Step 4: Verify tests pass**
Run: `pytest tests/test_web_api.py -v`
Expected: PASS

- [x] **Step 5: Commit**
```bash
git add clairvoy/web/app.py
git commit -m "feat(ui): add interactive keeper swapping and side-by-side comparison lightbox"
```

---

### Task 5: Sticky Action Dock & Safe Quarantine Staging

**Files:**
- Modify: `clairvoy/web/app.py`

**Interfaces:**
- Produces:
  - Sticky bottom floating bar showing exact live count and gigabytes currently marked for quarantine.
  - Quick action buttons: Download CSV, View Shell Script, Execute Reversible Quarantine.
  - Confirmation modal explaining the zero-clobber safety guarantees and rollback manifest.

- [x] **Step 1: Add Sticky Action Dock markup and CSS**
In `clairvoy/web/app.py`.

- [x] **Step 2: Wire selective quarantine toggle and execution**
In JavaScript, track excluded file paths, and update live counters on checkbox change.

- [x] **Step 3: Verify tests pass**
Run: `pytest tests/test_web_api.py -v`
Expected: PASS

- [x] **Step 4: Commit**
```bash
git add clairvoy/web/app.py
git commit -m "feat(ui): add sticky action dock and selective quarantine staging"
```

---

### Task 6: Full Verification, Documentation & Live Restart

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/ARCHITECTURE.md`

- [x] **Step 1: Run full regression test suite and linter**
Run: `/home/shubhamshah207/miniconda3/bin/pytest -v`
Run: `/home/shubhamshah207/miniconda3/bin/ruff check .`
Expected: 100% pass, 0 errors.

- [x] **Step 2: Update documentation**
Update `AGENTS.md` and `docs/ARCHITECTURE.md` with the premier UX capabilities.

- [x] **Step 3: Restart live Web UI background server**
Kill previous instance on port 8000 and launch updated server.

- [x] **Step 4: Commit & push to origin main**
```bash
git add AGENTS.md docs/ARCHITECTURE.md docs/superpowers/plans/
git commit -m "docs: document premier CleanMyMac-inspired UX redesign"
git push origin main
```
