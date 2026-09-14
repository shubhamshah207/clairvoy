# AGENTS.md — Agent Working Guidelines & Repository Blueprint

This document is the single source of truth for AI agents (and human contributors) working on **Clairvoy**.
Agents working on this repository **MUST read this document** and **MUST maintain and update this file** whenever architectural changes, new plugins, new patterns, or workflow modifications are introduced.

---

## 1. Project Overview & Core Philosophy

**Clairvoy** is an ultra-fast, 100% offline, privacy-first multimodal media deduplication and storage optimization engine.
- **Local-first execution:** Zero cloud API dependencies; runs models (DINOv2 ONNX Runtime) and media tools (PyAV / FFmpeg) locally.
- **Pluggable architecture:** Modular matcher, keeper strategy, and action plugin system dynamically loaded from built-ins or `~/.clairvoy/plugins/`.
- **Zero-clobber safety:** Non-destructive duplicate resolution (reversible quarantine with manifest tracking and cross-filesystem hardlinking).
- **Multi-tiered pipeline:** Progressive filtering from cheapest computational cost (Exact Hash) to highest (Visual/Video Analysis) with short-circuit pruning.

---

## 2. Architecture & Directory Structure

```
+---------------------------------------------------------------------------------+
|                                 CLAIRVOY ENGINE                                 |
+---------------------------------------------------------------------------------+
|                                                                                 |
|   +-------------------+      +---------------------+      +-----------------+   |
|   |    CLI (Typer)    |      |    FastAPI (Web)    |      | Custom Plugins  |   |
|   |  clairvoy/cli.py  |      |   clairvoy/web/     |      | ~/.clairvoy/... |   |
|   +---------+---------+      +----------+----------+      +--------+--------+   |
|             |                           |                          |            |
|             +---------------------+     |     +--------------------+            |
|                                   v     v     v                                 |
|                        +---------------------------+                            |
|                        |       PluginRegistry      |                            |
|                        | clairvoy/core/plugins.py  |                            |
|                        +-------------+-------------+                            |
|                                      |                                          |
|                                      v                                          |
|                        +---------------------------+                            |
|                        |   DeduplicationPipeline   |                            |
|                        | clairvoy/engines/pipeline |                            |
|                        +-------------+-------------+                            |
|                                      |                                          |
|         +----------------------------+----------------------------+             |
|         |                            |                            |             |
|         v                            v                            v             |
|  [Tier 1 Matchers]          [Tier 2 Matchers]            [Tier 3 Matchers]      |
|  ExactHashMatcherPlugin     PhotoVisionMatcherPlugin     ArchiveInspector...    |
|  (QuickHash + SHA-256)      (DINOv2 Embeddings)          (ZIP/TAR in-memory)    |
|         |                            |                            |             |
|         +----------------------------+----------------------------+             |
|                                      |                                          |
|                                      v                                          |
|                        +---------------------------+                            |
|                        |  CompositeKeeperStrategy  |                            |
|                        |  (Scoring & Seniority)    |                            |
|                        +-------------+-------------+                            |
|                                      |                                          |
|                                      v                                          |
|         +----------------------------+----------------------------+             |
|         |                                                         |             |
|         v                                                         v             |
|  [Action: SafeQuarantine]                                  [Action: Hardlink]   |
|  SafeQuarantineActionPlugin                                HardlinkActionPlugin |
+---------------------------------------------------------------------------------+
```

### Module Blueprint
- [`clairvoy/core/`](file:///home/shubhamshah207/clairvoy/clairvoy/core):
  - [`models.py`](file:///home/shubhamshah207/clairvoy/clairvoy/core/models.py): Canonical Pydantic v2 domain schemas (`FileEntry`, `DuplicateRecord`, `DuplicateCluster`, `ScanSummary`, `ActionResult`, `MatchType`, `ActionType`).
  - [`plugins.py`](file:///home/shubhamshah207/clairvoy/clairvoy/core/plugins.py): Plugin contracts (`BasePlugin`, `BaseMatcherPlugin`, `BaseKeeperPlugin`, `BaseActionPlugin`) and thread-safe `PluginRegistry`.
  - [`security.py`](file:///home/shubhamshah207/clairvoy/clairvoy/core/security.py): Enterprise security defenses: path traversal verification, system root protection, sanitized shell command generation.
  - [`config.py`](file:///home/shubhamshah207/clairvoy/clairvoy/core/config.py): App configurations, constants, thresholds.
  - [`classifier_data.py`](file:///home/shubhamshah207/clairvoy/clairvoy/core/classifier_data.py): Embedded prototype vectors for semantic categories (Screenshot, Photo, Meme, Document).
- [`clairvoy/engines/`](file:///home/shubhamshah207/clairvoy/clairvoy/engines):
  - [`pipeline.py`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/pipeline.py): `DeduplicationPipeline` orchestrator, `CompositeKeeperStrategy` prioritizing resolution and quality.
  - [`storage_engine.py`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/storage_engine.py): Multi-threaded filesystem scanner, 128KB head/tail QuickHash and SHA-256 digests.
  - [`vision_engine.py`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/vision_engine.py): Local ONNX Runtime DINOv2 inference and Disjoint Set Union (DSU) clustering.
  - [`classifier_engine.py`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/classifier_engine.py): Local cosine classifier categorizing media files.
  - [`quarantine.py`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/quarantine.py): Manifest-backed non-destructive quarantine isolation and restoration engine.
- [`clairvoy/plugins/`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins):
  - [`exact_hash.py`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/exact_hash.py): `ExactHashMatcherPlugin` (priority 10).
  - [`photo_vision.py`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/photo_vision.py): `PhotoVisionMatcherPlugin` (priority 20).
  - [`video_matcher.py`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/video_matcher.py): `VideoKeyframeMatcherPlugin` (priority 30).
  - [`archive_inspector.py`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/archive_inspector.py): `ArchiveInspectorMatcherPlugin` (priority 40).
  - [`quarantine_action.py`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/quarantine_action.py): `SafeQuarantineActionPlugin`.
  - [`hardlink_action.py`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/hardlink_action.py): `HardlinkActionPlugin`.
- [`clairvoy/cli.py`](file:///home/shubhamshah207/clairvoy/clairvoy/cli.py): CLI commands (`scan`, `review`, `quarantine`, `restore`, `plugins list`, `plugins info`).
- [`clairvoy/web/`](file:///home/shubhamshah207/clairvoy/clairvoy/web): FastAPI backend (`app.py`) and static interactive UI.
- [`tests/`](file:///home/shubhamshah207/clairvoy/tests): Test suite (110 tests covering all features and documentation integrity).

---

## 3. Agent Operating Rules & Invariants

All agents operating in this repository must strictly adhere to these rules:

1. **Maintain `AGENTS.md` Always:**
   - Any time you add a new plugin, modify core architecture, update CLI options, change dependencies, or alter verification workflows, **you must update this file**.
2. **ASCII Art for All Terminal/Chat Diagrams:**
   - Never output Mermaid, graphviz, or image tags for diagrams in chat responses or terminal logs. Always format diagrams as clean ASCII art with box-drawing characters (`+---`, `|`, `-->`).
3. **Clickable Links for Files & Symbols:**
   - All references to files, functions, classes, or test cases in user responses must use clickable `file://` markdown links (e.g. `[plugins.py](file:///home/shubhamshah207/clairvoy/clairvoy/core/plugins.py)`).
4. **Local-First & Zero-Clobber Invariants:**
   - Never write code that makes external unauthenticated cloud API calls.
   - Operations that alter files (quarantine, hardlinking, deleting) must never overwrite without verification and must support rollback/manifest tracking.
5. **Type Safety & Style:**
   - Python 3.12+ type annotations (`T | None`, `list[T]`, `dict[K, V]`).
   - Linting must strictly pass `ruff check .` with zero errors or warnings.
6. **Testing Verification:**
   - Every feature or fix must be accompanied by comprehensive `pytest` test cases.
   - All tests must pass: `110 passed`.

---

## 4. Environment & Tooling Commands

- **Python Interpreter:** `/home/shubhamshah207/miniconda3/bin/python`
- **Run Full Test Suite:**
  ```bash
  /home/shubhamshah207/miniconda3/bin/pytest -v
  ```
- **Run Linting:**
  ```bash
  /home/shubhamshah207/miniconda3/bin/ruff check .
  ```
- **Run Auto-Fix Formatting / Linting:**
  ```bash
  /home/shubhamshah207/miniconda3/bin/ruff check --fix .
  ```
- **CLI Commands (Typer):**
  ```bash
  /home/shubhamshah207/miniconda3/bin/clairvoy scan /path/to/folder
  /home/shubhamshah207/miniconda3/bin/clairvoy plugins list
  /home/shubhamshah207/miniconda3/bin/clairvoy plugins info exact_hash
  /home/shubhamshah207/miniconda3/bin/clairvoy review /path/to/manifest.json
  ```
- **Generate Screenshots / Diagrams:**
  ```bash
  /home/shubhamshah207/miniconda3/bin/python scripts/generate_screenshots.py
  /home/shubhamshah207/miniconda3/bin/python scripts/generate_architecture_diagram.py
  ```

---

## 5. Current Progress Status (as of Sep 13, 2026)

- **Completed:**
  - Pluggable Engine Architecture (Tasks 1-6 fully implemented and merged).
  - 6 Default Plugins:
    1. `ExactHashMatcherPlugin` (QuickHash + SHA-256)
    2. `PhotoVisionMatcherPlugin` (DINOv2 local visual embedding)
    3. `VideoKeyframeMatcherPlugin` (Duration grouping + keyframe hash)
    4. `ArchiveInspectorMatcherPlugin` (In-memory ZIP/TAR inspection)
    5. `SafeQuarantineActionPlugin` (Manifest-backed isolation)
    6. `HardlinkActionPlugin` (Cross-device safe hardlinking)
  - `DeduplicationPipeline` with short-circuit pruning, priority ordering, and `CompositeKeeperStrategy`.
  - CLI `plugins list` and `plugins info <id>`, plus scan options (`--enable-plugin`, `--disable-plugin`, `--action`).
  - Web UI & FastAPI backend with side-by-side visual diffing.
  - ByteByteGo-style architecture SVG diagram and Playwright screenshot generation pipeline.
  - 100% test coverage with 110 passing tests in `pytest` and clean `ruff` linter checks.
- **Active / Next Steps:**
  - Maintain `AGENTS.md` across future feature requests.
  - Expand additional community plugins (e.g. audio fingerprinting, EXIF geocoding clusters).
