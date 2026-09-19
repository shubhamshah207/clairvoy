# AGENTS.md — Agent Working Guidelines & Repository Blueprint

This document is the single source of truth for AI agents and human contributors working on **Clairvoy**.
Clairvoy is an ultra-fast, 100% offline, privacy-first multimodal media deduplication and storage optimization engine featuring dual Python and pure Rust architectures.

All agents operating in this repository **MUST read this document** and **MUST maintain and update this file and linked docs** whenever architectural changes, new plugins, new patterns, or workflow modifications are introduced.

---

## 1. Quick Reference & Commands

### Python Environment & Commands
- **Environment Python:** `/home/shubhamshah207/miniconda3/bin/python`
- **Run Tests (Full Suite):** `/home/shubhamshah207/miniconda3/bin/pytest -v`
- **Lint Check:** `/home/shubhamshah207/miniconda3/bin/ruff check .`
- **Auto-Fix Lints:** `/home/shubhamshah207/miniconda3/bin/ruff check --fix .`
- **Python CLI:**
  ```bash
  /home/shubhamshah207/miniconda3/bin/clairvoy scan /path/to/folder
  /home/shubhamshah207/miniconda3/bin/clairvoy runs list
  /home/shubhamshah207/miniconda3/bin/clairvoy runs show <RUN_ID>
  /home/shubhamshah207/miniconda3/bin/clairvoy ui --report /path/to/clairvoy_summary.json
  /home/shubhamshah207/miniconda3/bin/clairvoy ui --run <RUN_ID>
  /home/shubhamshah207/miniconda3/bin/clairvoy plugins list
  /home/shubhamshah207/miniconda3/bin/clairvoy plugins info exact_hash
  /home/shubhamshah207/miniconda3/bin/clairvoy plugins info document_matcher
  ```

### Rust Workspace & Commands
- **Cargo Path:** `export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"`
- **Run Workspace Tests:** `cargo test --workspace`
- **Lint Check (Clippy):** `cargo clippy --workspace --all-targets -- -D warnings`
- **Build Release:** `cargo build --workspace --release`
- **Rust Native CLI (`clairvoy-rs`):**
  ```bash
  cargo run --bin clairvoy-rs -- scan /path/to/folder
  cargo run --bin clairvoy-rs -- ui --port 8080 --host 0.0.0.0
  ```

---

## 2. Core Invariants & Agent Rules

1. **Maintain `AGENTS.md` Always:**
   - Keep this file and subdocs synchronized with architecture and tooling changes.
   - Keep `AGENTS.md` strictly under 15KB per instruction budget tests.
2. **ASCII Art for All Terminal/Chat Diagrams:**
   - Never output Mermaid, graphviz, or image tags in chat or terminal logs. Use clean box-drawing ASCII art (`+---`, `|`, `-->`).
3. **Clickable Links for Files & Symbols:**
   - All references to files, functions, classes, or tests in responses must use clickable `file://` markdown links (e.g. `[plugins.py](file:///home/shubhamshah207/clairvoy/clairvoy/core/plugins.py)`).
4. **Local-First & Zero-Clobber Invariants:**
   - Zero unauthenticated cloud API calls.
   - Destructive operations (quarantine, hardlinking, deleting) must never overwrite without verification and manifest tracking.
5. **Deep Modules (Interface-First):**
   - Keep implementation details encapsulated behind clean public interfaces (`clairvoy.core`, `clairvoy.engines`, `clairvoy.plugins`, `crates/*`).
   - Humans own the interface; AI owns the implementation; test suites keep it honest.
6. **Plan Mode Guidelines:**
   - The 4-step loop: **Plan $\rightarrow$ Execute $\rightarrow$ Test $\rightarrow$ Commit**. Keep plans concise.
7. **Quality & Verification:**
   - Python: 3.12+ type annotations (`T | None`, `list[T]`), 100% `pytest` & `ruff` pass.
   - Rust: Edition 2021, `cargo test --workspace` & `cargo clippy --workspace --all-targets -- -D warnings` pass with 0 warnings, $\le 50\text{MB}$ memory invariant.

---

## 3. High-Level Architecture Overview

```
+---------------------------------------------------------------------------------------------------+
|                                          CLAIRVOY ENGINE                                          |
+---------------------------------------------------------------------------------------------------+
|   +-------------------+          +---------------------+            +-----------------+           |
|   | CLI: Python / Rust|          | Web: FastAPI / Axum |            | Custom Plugins  |           |
|   | clairvoy/cli.py   |          | clairvoy/web/       |            | ~/.clairvoy/... |           |
|   | clairvoy-rs (CLI) |          | clairvoy-server     |            | clairvoy-plugins|           |
|   +---------+---------+          +----------+----------+            +--------+--------+           |
|             |                               |                                |                    |
|             +-------------------------+     |     +--------------------------+                    |
|                                       v     v     v                                               |
|                            +---------------------------+                                          |
|                            |      PluginRegistry       |                                          |
|                            | clairvoy/core/plugins.py  |                                          |
|                            | clairvoy-engine / plugins |                                          |
|                            +-------------+-------------+                                          |
|                                          v                                                        |
|                            +---------------------------+                                          |
|                            |   DeduplicationPipeline   |                                          |
|                            | clairvoy/engines/pipeline |                                          |
|                            | crates/clairvoy-engine    |                                          |
|                            +-------------+-------------+                                          |
|                                          |                                                        |
|       +------------------+---------------+---------------+------------------+                     |
|       v                  v                               v                  v                     |
| [Tier 1: Byte Exact][Tier 2: Visual AI]             [Tier 3: Video]    [Tier 4: Docs & Zip]       |
| ExactHashMatcher    PhotoVisionMatcher              VideoKeyframe...   Archive & Document Matchers|
| (QuickHash+SHA/B3)  (DINOv2 / dHash)                (Frames: .mp4..)   (.zip, .pdf, .docx, .csv)  |
|       +------------------+---------------+---------------+------------------+                     |
|                                          v                                                        |
|                            +---------------------------+                                          |
|                            |  CompositeKeeperStrategy  |                                          |
|                            |  (Scoring & Seniority)    |                                          |
|                            +-------------+-------------+                                          |
|                                          v                                                        |
|                 +------------------------+-----------------------+                                |
|                 v                        v                       v                                |
|       [Action: Quarantine]      [Action: Hardlink]      [Action: SafeDelete]                      |
|       SafeQuarantinePlugin      HardlinkActionPlugin    DeleteEngine (Trash & Permanent)          |
+---------------------------------------------------------------------------------------------------+
```

### Supported Format Matrix & Tier Mapping

| Modality | Formats Handled | Engine / Plugin | Key Invariant / Discriminator |
|---|---|---|---|
| **Photos & Raster** | `.jpg`, `.png`, `.webp`, `.bmp`, `.tiff`, `.tif`, `.heic`, `.psd` | [`PhotoVisionMatcherPlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/photo_vision.py) & [`VisionEngine`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/vision_engine.py) | Native Pillow PSD; dual-path HEIC; `MALLOC_ARENA_MAX=2`; JPEG draft decoding; 4-worker pool. |
| **Video & Motion** | `.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`, `.flv`, `.wmv`, `.m4v`, `.ts`, `.mp` | [`VideoKeyframeMatcherPlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/video_matcher.py) | $O(1)$ sync byte `0x47` distinguishes MPEG-TS; `ftyp` detects `.mp` Motion Photos. |
| **In-Memory Archives** | `.zip`, `.jar`, `.apk`, `.tar`, `.tar.gz`, `.tgz`, `.tar.bz2`, `.tbz2`, `.rar` | [`ArchiveInspectorMatcherPlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/archive_inspector.py) | In-memory central directory CRC32 inspection without disk extraction. |
| **Documents & Tabular** | `.pdf`, `.docx`, `.pptx`, `.odt`, `.csv`, `.tsv` | [`DocumentTextMatcherPlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/document_matcher.py) | In-memory `zipfile` XML; pure-Python `pypdf`; permutation-invariant tabular sort; 25MB cap. |
| **Stream Utils** | Binary magic-byte probes | [`format_utils.py`](file:///home/shubhamshah207/clairvoy/clairvoy/core/format_utils.py) | `is_mpeg_ts`, `is_motion_photo_video`, `is_rar_archive`. |

---

## 4. Rust Workspace & Coexistence Guidelines

### Workspace Crates (`crates/`)
- [`crates/clairvoy-core`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-core): Canonical data models (`FileEntry`, `DuplicateRecord`, `ScanSummary`), plugin traits (`MatcherPlugin`, `KeeperStrategy`), typed errors (`EngineError`), and embedded SQLite persistence engine (`clairvoy_core::db::Database` with WAL mode at `~/.clairvoy/clairvoy.db`).
- [`crates/clairvoy-scanner`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-scanner): Zero-copy bounded streaming filesystem crawler (`scan_roots`, `scan_filesystem`) with XXH3 4KB SIMD hashing.
- [`crates/clairvoy-model`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-model): Pluggable vision model runtime, perceptual `dHash` backend, `models.toml` registry.
- [`crates/clairvoy-plugins`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-plugins): Modular matchers (`ExactHashMatcherPlugin` with BLAKE3, `PhotoVisionMatcherPlugin`).
- [`crates/clairvoy-engine`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-engine): Multi-tier `DeduplicationPipeline` orchestrator, `CompositeKeeperStrategy` rule engine, and `AutonomousWatcher` background daemon.
- [`crates/clairvoy-server`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-server): High-throughput Axum web server exposing full M3 API, SSE progress streaming, and directory navigation.
- [`crates/clairvoy-cli`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-cli): Native CLI executable `clairvoy-rs` (`scan`, `ui` with optional `--no-daemon`).

### Coexistence & Primacy Invariants
1. **Rust Engine Primacy:** Pure Rust is the default and primary runtime; Python web server is deprecated and planned for removal.
2. **Flag-Based Daemon:** The autonomous watcher daemon can be disabled via `--no-daemon`, while interactive on-the-fly scanning remains 100% available.
3. **Memory Invariant:** Rust crawler strictly uses `flume::bounded(2048)` to guarantee $\le 50\text{MB}$ resident RAM across multi-million file workloads.
4. **Verification Parity:** Changes must pass `cargo test --workspace`, `cargo clippy --workspace --all-targets -- -D warnings`, and Python `pytest -v`.

---

## 5. Progressive Disclosure & Detailed Documentation

In-depth guidelines are organized into dedicated documents:

- **System Architecture & Deep Modules:** [`docs/ARCHITECTURE.md`](file:///home/shubhamshah207/clairvoy/docs/ARCHITECTURE.md)
  - Package structure, short-circuit pipeline pruning, composite keeper scoring, DeleteEngine, and Google Photos Product Studio.
- **Google Material Design 3 Spec & Plans:** [`docs/superpowers/specs/2026-09-18-google-material-design-system.md`](file:///home/shubhamshah207/clairvoy/docs/superpowers/specs/2026-09-18-google-material-design-system.md) & [`docs/superpowers/plans/2026-09-18-google-material-ui-and-delete.md`](file:///home/shubhamshah207/clairvoy/docs/superpowers/plans/2026-09-18-google-material-ui-and-delete.md)
  - Details Google Photos interface, Top Selection Bar, category navigation, storage indicator, thumbnail/media streaming, and Safe Trash & Permanent Deletion engine.
- **Premier UX Design System Spec & Plans:** [`docs/superpowers/specs/2026-09-18-premier-ux-design-system.md`](file:///home/shubhamshah207/clairvoy/docs/superpowers/specs/2026-09-18-premier-ux-design-system.md) & [`docs/superpowers/plans/2026-09-18-premier-ux-redesign.md`](file:///home/shubhamshah207/clairvoy/docs/superpowers/plans/2026-09-18-premier-ux-redesign.md)
  - Dark-mode UI, Smart Clean Hero Banner (split exact vs. similar tracks), Google Drive left rail architecture, `#newScanModal` with native folder picker, emerald keeper highlights, and toast notifications.
- **Plugin Developer Guide:** [`docs/PLUGINS.md`](file:///home/shubhamshah207/clairvoy/docs/PLUGINS.md)
  - Creating custom Matcher, Keeper, and Action plugins, priority tiers, and dynamic registration.
- **Testing & Verification Guide:** [`docs/TESTING.md`](file:///home/shubhamshah207/clairvoy/docs/TESTING.md)
  - Test fixtures, execution options, and linter standards.
- **Rust High-Performance Guidelines:** [`docs/RUST_GUIDELINES.md`](file:///home/shubhamshah207/clairvoy/docs/RUST_GUIDELINES.md)
  - Zero-copy memory patterns, bounded queue backpressure, SIMD hashing, Rayon/Tokio boundaries, and `thiserror` domain errors.
- **Performance Benchmarks & Analysis:** [`docs/BENCHMARKS.md`](file:///home/shubhamshah207/clairvoy/docs/BENCHMARKS.md)
  - Empirical comparisons across real-world workloads, SIMD profiling, and memory invariants.
- **Enterprise Security Policy:** [`SECURITY.md`](file:///home/shubhamshah207/clairvoy/SECURITY.md)
  - Path traversal defenses, system root isolation, and sanitized shell generation.
- **Automated Agent Guardrails:** [`scripts/agent_guard.py`](file:///home/shubhamshah207/clairvoy/scripts/agent_guard.py)
  - Deterministic pre-execution command filter preventing destructive git commands and unvirtualized python execution.

---

## 6. Agent Tool Portability

- [`CLAUDE.md`](file:///home/shubhamshah207/clairvoy/CLAUDE.md) is symlinked to `AGENTS.md`.
- [`agents.md`](file:///home/shubhamshah207/clairvoy/agents.md) is symlinked to `AGENTS.md`.
- Both ensure universal agent compatibility across Claude Code, Cursor, Windsurf, Copilot, and Antigravity.
