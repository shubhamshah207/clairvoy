# Google Material Design 3 UI & Safe Deletion Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform Clairvoy's UI into a Google Photos, Google Drive, and Google Files-inspired Material Design 3 (M3) experience with a dual view mode (Photos Grid vs Drive List), contextual selection action bar, and a first-class Safe Deletion Engine supporting both soft delete (Trash with 1-click restore) and permanent deletion with audit logging.

**Architecture:** 
- Backend: Implement `DeleteEngine` (`clairvoy/engines/delete_engine.py`) with zero-clobber keeper protection, strict root confinement, multi-worker concurrency, and audit logging. Add endpoints `/api/delete/execute`, `/api/delete/restore`, and `/api/reports/delete-script` in `clairvoy/web/app.py`.
- Frontend: Redesign `clairvoy/web/ui.py` into a Google Material Design 3 interface featuring a floating pill search bar, left navigation rail, Google Photos photo tiles with circular checkmark chips, Google Drive compact table view, Google One Clean Up hero card, and contextual top action bar.

**Tech Stack:** Python 3.12+, FastAPI, Tailwind CSS + Material Design 3 design tokens, Pure Vanilla JavaScript (100% offline, zero external dependencies), Pytest.

**Spec:** [`docs/superpowers/specs/2026-09-18-google-material-design-system.md`](file:///home/shubhamshah207/clairvoy/docs/superpowers/specs/2026-09-18-google-material-design-system.md)

## Global Constraints
- 100% offline, local-first execution; zero external cloud calls or CDN dependencies that fail offline.
- Zero-clobber safety invariants: KEEPER files can NEVER be deleted under any circumstances.
- Python 3.12+ type annotations (`T | None`, `list[T]`, `dict[K, V]`).
- Full test suite in `pytest -v` and `ruff check .` must pass with 100% success and 0 errors.
- All chat/terminal diagrams must be clean ASCII art using box-drawing characters.

---

### Task 1: Core Models & Deletion Engine (`clairvoy/engines/delete_engine.py`)

**Files:**
- Modify: `clairvoy/core/models.py`
- Modify: `clairvoy/core/security.py`
- Create: `clairvoy/engines/delete_engine.py`
- Test: `tests/test_delete_engine.py`

**Interfaces:**
- Produces:
  - `DeletionItem`, `DeletionManifest` in `clairvoy/core/models.py`.
  - `generate_hardened_deletion_script(deletions: list[str], base_dir: str | list[str]) -> str` in `clairvoy/core/security.py`.
  - `DeleteEngine.execute(...) -> DeletionManifest` and `DeleteEngine.restore(...) -> int` in `clairvoy/engines/delete_engine.py`.

- [x] **Step 1: Add Deletion models to `clairvoy/core/models.py`**
- [x] **Step 2: Add `generate_hardened_deletion_script` in `clairvoy/core/security.py`**
- [x] **Step 3: Write comprehensive unit tests in `tests/test_delete_engine.py`**
- [x] **Step 4: Implement `DeleteEngine` in `clairvoy/engines/delete_engine.py`**
- [x] **Step 5: Run tests and verify 100% pass**
```bash
/home/shubhamshah207/miniconda3/bin/pytest tests/test_delete_engine.py -v
```
- [x] **Step 6: Commit**
```bash
git add clairvoy/core/models.py clairvoy/core/security.py clairvoy/engines/delete_engine.py tests/test_delete_engine.py
git commit -m "feat(engine): implement DeleteEngine with soft trash, permanent deletion, and audit trail"
```

---

### Task 2: Web API Endpoints for Deletion (`clairvoy/web/app.py`)

**Files:**
- Modify: `clairvoy/web/app.py`
- Modify: `tests/test_web_api.py`

**Interfaces:**
- Produces:
  - `POST /api/delete/execute`: executes deletion (trash or permanent), updates active `SCAN_STATE` summary.
  - `POST /api/delete/restore`: restores files from a trash manifest.
  - `GET /api/reports/delete-script`: downloads generated shell script `delete_duplicates.sh`.

- [x] **Step 1: Write API tests in `tests/test_web_api.py` for delete endpoints**
- [x] **Step 2: Implement delete request models and endpoints in `clairvoy/web/app.py`**
- [x] **Step 3: Run web API tests and verify 100% pass**
```bash
/home/shubhamshah207/miniconda3/bin/pytest tests/test_web_api.py -v
```
- [x] **Step 4: Commit**
```bash
git add clairvoy/web/app.py tests/test_web_api.py
git commit -m "feat(web): add /api/delete/execute, /api/delete/restore, and /api/reports/delete-script endpoints"
```

---

### Task 3: Google Material Design 3 Design System & App Bar (`clairvoy/web/ui.py`)

**Files:**
- Modify: `clairvoy/web/ui.py`

**Interfaces:**
- Produces:
  - Material Design 3 CSS tokens: `--md-sys-color-background`, `--md-sys-color-surface`, `--md-sys-color-primary` (Google Blue `#8ab4f8`), etc.
  - Google App Bar: Google 4-color dot logo, centered floating pill search bar, Dataset Chip, and Scan Drawer toggle.
  - Google Navigation Rail (Desktop) / Nav Tabs (*Clean up*, *Photos*, *Drive Files*, *All Duplicates*, *Trash*).
  - Google One Clean Up Storage Hero Card with Google-color segmented bar.

- [x] **Step 1: Structure M3 CSS tokens, typography, and base layout in `clairvoy/web/ui.py`**
- [x] **Step 2: Implement Google App Bar and Left Navigation Rail components**
- [x] **Step 3: Implement Google One Clean-Up Hero Card**
- [x] **Step 4: Verify web app renders cleanly via pytest**
```bash
/home/shubhamshah207/miniconda3/bin/pytest tests/test_web_api.py -v
```
- [x] **Step 5: Commit**
```bash
git add clairvoy/web/ui.py
git commit -m "feat(ui): implement Google Material Design 3 app bar, navigation rail, and storage hero"
```

---

### Task 4: Google Photos & Drive Dual View Modes & Contextual Selection Bar (`clairvoy/web/ui.py`)

**Files:**
- Modify: `clairvoy/web/ui.py`

**Interfaces:**
- Produces:
  - Google Photos Grid View: photo tiles with top-left circular checkmark selection chips, keeper badge, and hover scale.
  - Google Drive List View: dense tabular view with file names, sizes, match types, timestamps, and row actions.
  - View mode toggle button: instant switch between `Photos (Grid)` and `Drive (List)`.
  - Google Photos-style floating Contextual Selection Action Bar: appears when items are selected with live count, Select All, and bulk actions.

- [x] **Step 1: Implement Google Photos Grid View card rendering with circular checkmarks**
- [x] **Step 2: Implement Google Drive List View table rendering**
- [x] **Step 3: Implement view toggle state and event handlers in JavaScript**
- [x] **Step 4: Implement Google Photos-style floating Contextual Selection Action Bar**
- [x] **Step 5: Verify tests pass**
```bash
/home/shubhamshah207/miniconda3/bin/pytest tests/test_web_api.py -v
```
- [x] **Step 6: Commit**
```bash
git add clairvoy/web/ui.py
git commit -m "feat(ui): add Google Photos grid view, Google Drive list view, and contextual action bar"
```

---

### Task 5: Google-Style Deletion & Confirmation Dialogs (`clairvoy/web/ui.py`)

**Files:**
- Modify: `clairvoy/web/ui.py`

**Interfaces:**
- Produces:
  - M3 Dialog for "Move to Trash" (soft delete with undo explanation).
  - M3 Dialog for "Delete Permanently" (high-visibility danger modal with exact space freed).
  - Integration with `/api/delete/execute` and live DOM updates.

- [x] **Step 1: Add HTML markup for Google M3 Trash and Permanent Delete confirmation dialogs**
- [x] **Step 2: Wire JavaScript deletion execution and dynamic card removal/updates**
- [x] **Step 3: Verify tests pass**
```bash
/home/shubhamshah207/miniconda3/bin/pytest tests/test_web_api.py -v
```
- [x] **Step 4: Commit**
```bash
git add clairvoy/web/ui.py
git commit -m "feat(ui): add Google M3 trash and permanent delete confirmation dialogs"
```

---

### Task 6: Full Verification, Documentation & Live Restart

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/ARCHITECTURE.md`

- [x] **Step 1: Run full regression test suite and static linter**
```bash
/home/shubhamshah207/miniconda3/bin/pytest -v
/home/shubhamshah207/miniconda3/bin/ruff check .
```
- [x] **Step 2: Update documentation (`AGENTS.md` and `docs/ARCHITECTURE.md`)**
- [x] **Step 3: Restart web server on port 8000 and verify live responsiveness**
- [x] **Step 4: Git commit and push to origin main**
```bash
git add AGENTS.md docs/ARCHITECTURE.md docs/superpowers/
git commit -m "docs: document Google Material Design 3 UI and Safe Deletion Engine"
git push origin main
```
