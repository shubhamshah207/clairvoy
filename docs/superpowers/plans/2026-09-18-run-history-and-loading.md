# Run History, Listing, and Loading Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide persistent tracking, listing, and loading of past scan runs in both the Clairvoy CLI and interactive Web Dashboard so users can instantly inspect, switch, and resolve previous scan results without re-scanning.

**Architecture:** A persistent `RunManager` records scan summaries into `~/.clairvoy/runs.json` and auto-discovers unregistered reports from known directories (e.g. `~/clairvoy_drive_e_reports`). The CLI provides `clairvoy runs list` and `clairvoy runs show`, and the Web UI exposes `/api/runs` and `/api/runs/load` with an interactive dropdown and auto-hydration on page load.

**Tech Stack:** Python 3.12+, Pydantic v2, FastAPI, Uvicorn, Typer/Argparse, Tailwind CSS, Pytest.

**Spec:** In-line architectural spec approved for persistent past runs tracking and web dashboard hydration.

## Global Constraints
- 100% offline, local-first execution; no external cloud calls.
- Preserves all zero-clobber and security invariants (path traversal validation on loaded reports and thumbnails).
- Python 3.12+ type annotations (`list[T]`, `dict[K, V]`, `T | None`).
- All tests in `pytest -v` and `ruff check .` must pass with 100% success and 0 warnings/errors.
- All chat/terminal diagrams must be clean ASCII art using box-drawing characters.

---

### Task 1: Persistent `RunManager` Core Module

**Files:**
- Create: `clairvoy/core/run_manager.py`
- Test: `tests/test_run_manager.py`

**Interfaces:**
- Produces:
  - `class RunRecord(BaseModel)`: schema for a saved scan run (`run_id`, `timestamp`, `scanned_paths`, `total_files_scanned`, `total_duplicate_groups`, `wasted_mb`, `wasted_gb`, `summary_json`, `csv_report`, `quarantine_script`).
  - `class RunManager`:
    - `__init__(self, storage_path: Path | None = None)`
    - `register_run(summary: ScanSummary | dict[str, Any]) -> RunRecord`
    - `list_runs(limit: int = 20) -> list[RunRecord]`
    - `get_run(run_id: str) -> RunRecord | None`
    - `load_run_summary(run_identifier: str) -> dict[str, Any]`
    - `auto_discover_reports() -> list[RunRecord]`

- [ ] **Step 1: Write the failing unit tests for `RunManager`**
Create `tests/test_run_manager.py` testing registration, listing, retrieval, loading, and auto-discovery from an existing directory.

- [ ] **Step 2: Run tests to verify they fail**
Run: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_run_manager.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clairvoy.core.run_manager'`

- [ ] **Step 3: Implement `RunManager` in `clairvoy/core/run_manager.py`**
Implement the class, file persistence in `~/.clairvoy/runs.json`, safe serialization, and auto-discovery across `~/clairvoy_drive_e_reports`, `./_dedupe_reports`, and `~/.clairvoy/reports`.

- [ ] **Step 4: Run tests to verify they pass**
Run: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_run_manager.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add clairvoy/core/run_manager.py tests/test_run_manager.py
git commit -m "feat(core): implement persistent RunManager and report auto-discovery"
```

---

### Task 2: Auto-Registration in Pipeline & Storage Engine

**Files:**
- Modify: `clairvoy/engines/pipeline.py`
- Modify: `clairvoy/engines/storage_engine.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `RunManager.register_run(summary)`
- Produces: Automatic registration of every completed CLI or API scan into `~/.clairvoy/runs.json`.

- [ ] **Step 1: Write integration test verifying run auto-registration**
Add a test in `tests/test_pipeline.py` asserting that running the pipeline registers a new entry in `RunManager`.

- [ ] **Step 2: Run test to verify it fails**
Run: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_pipeline.py -k test_pipeline_registers_run -v`
Expected: FAIL

- [ ] **Step 3: Add registration hook to `pipeline.py` and `storage_engine.py`**
In `DeduplicationPipeline.run()` right after writing the JSON summary, call `RunManager().register_run(summary)`.
In `StorageEngine.run()` right after writing the summary, call `RunManager().register_run(summary)`.

- [ ] **Step 4: Run tests to verify they pass**
Run: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_pipeline.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add clairvoy/engines/pipeline.py clairvoy/engines/storage_engine.py tests/test_pipeline.py
git commit -m "feat(pipeline): automatically register completed scan runs with RunManager"
```

---

### Task 3: CLI Commands (`clairvoy runs list`, `show`, and `ui --report / --run`)

**Files:**
- Modify: `clairvoy/cli.py`
- Test: `tests/test_cli_runs.py`

**Interfaces:**
- CLI subcommands:
  - `clairvoy runs list`: formatted ASCII table of runs with ID, Date, Target, Duplicates, Recoverable Space, Summary Path.
  - `clairvoy runs show <RUN_ID>`: detailed inspection of a specific run.
  - `clairvoy ui --report <PATH>`: pre-loads report file into UI.
  - `clairvoy ui --run <RUN_ID>`: pre-loads run by ID into UI.
  - `clairvoy ui` (no args): auto-loads the latest run if one exists, rather than starting blank.

- [ ] **Step 1: Write CLI tests for `runs` command**
Create `tests/test_cli_runs.py` testing `runs list`, `runs show`, and `ui` options.

- [ ] **Step 2: Run test to verify it fails**
Run: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_cli_runs.py -v`
Expected: FAIL

- [ ] **Step 3: Implement CLI parser and handlers in `clairvoy/cli.py`**
Add `runs` subparser (`list`, `show`) and extend `ui` parser with `--report` and `--run`.
Pre-load the report into `clairvoy.web.app` before starting Uvicorn.

- [ ] **Step 4: Run tests to verify they pass**
Run: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_cli_runs.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add clairvoy/cli.py tests/test_cli_runs.py
git commit -m "feat(cli): add 'runs' commands and pre-loading flags for 'ui'"
```

---

### Task 4: Web UI Endpoints (`/api/runs`, `/api/runs/load`) & Thumbnail Path Whitelist

**Files:**
- Modify: `clairvoy/web/app.py`
- Test: `tests/test_web_api.py`

**Interfaces:**
- Consumes: `RunManager`
- Produces:
  - `GET /api/runs`: JSON array of all past runs with metadata.
  - `POST /api/runs/load`: loads a run by `run_id` or `path`, updates `SCAN_STATE`, and sets `target_paths` so `/api/thumbnail` functions correctly.

- [ ] **Step 1: Write tests for `/api/runs` and `/api/runs/load` in `tests/test_web_api.py`**
Assert `GET /api/runs` returns registered runs, and `POST /api/runs/load` populates `SCAN_STATE`.

- [ ] **Step 2: Run tests to verify they fail**
Run: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_web_api.py -k "test_runs" -v`
Expected: FAIL with 404 Not Found.

- [ ] **Step 3: Implement endpoints in `clairvoy/web/app.py`**
Add `/api/runs` and `/api/runs/load`, and update startup logic to auto-load the latest run if present.

- [ ] **Step 4: Run tests to verify they pass**
Run: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_web_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add clairvoy/web/app.py tests/test_web_api.py
git commit -m "feat(web): add runs listing and loading endpoints to API"
```

---

### Task 5: Interactive Web Dashboard Past Runs Selector & Auto-Hydration

**Files:**
- Modify: `clairvoy/web/app.py` (HTML/JS template in `serve_index`)
- Test: `tests/test_web_api.py`

**Interfaces:**
- Produces:
  - Header dropdown selector: "📂 Past Runs & Reports" with run ID, date, recoverable space, and duplicate count.
  - On page load (`window.addEventListener('DOMContentLoaded')`), calls `/api/status` and `/api/runs`. If a run is available, automatically hydrates the dashboard with metrics, category filters, and cluster cards without user intervention.
  - Selecting another run dynamically switches the dashboard to that run without a full page reload.

- [ ] **Step 1: Update HTML template and JS in `clairvoy/web/app.py`**
Add the dropdown in the header, add `loadRunById()`, `populateRunsDropdown()`, and `DOMContentLoaded` hook.

- [ ] **Step 2: Test endpoint and HTML response via pytest**
Run: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_web_api.py -v`
Expected: PASS

- [ ] **Step 3: Commit**
```bash
git add clairvoy/web/app.py
git commit -m "feat(ui): add past runs dropdown and automatic dashboard hydration on load"
```

---

### Task 6: Full Regression Verification & Documentation

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/ARCHITECTURE.md`

- [ ] **Step 1: Run full test suite and linter**
Run: `/home/shubhamshah207/miniconda3/bin/pytest -v`
Run: `/home/shubhamshah207/miniconda3/bin/ruff check .`
Expected: 100% pass, 0 errors.

- [ ] **Step 2: Update documentation**
Record the new `RunManager`, `clairvoy runs`, and UI past run selection in `AGENTS.md` and `docs/ARCHITECTURE.md`.

- [ ] **Step 3: Commit**
```bash
git add AGENTS.md docs/ARCHITECTURE.md
git commit -m "docs: update blueprint with RunManager, CLI runs command, and UI past reports"
```
