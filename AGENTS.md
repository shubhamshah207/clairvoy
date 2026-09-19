# AGENTS.md — Agent Working Guidelines & Repository Blueprint

This document is the single source of truth for AI agents and human contributors working on **Clairvoy**.
Clairvoy is an ultra-fast, 100% offline, privacy-first multimodal media deduplication and storage optimization engine built in pure Rust.

All agents operating in this repository **MUST read this document** and **MUST maintain and update this file and linked docs** whenever architectural changes, new plugins, new patterns, or workflow modifications are introduced.

---

## 1. Quick Reference & Commands

### Rust Workspace Commands
- **Cargo Path:** `export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"`
- **Run Workspace Tests:** `cargo test --workspace`
- **Lint Check (Clippy):** `cargo clippy --workspace --all-targets -- -D warnings`
- **Format Verification:** `cargo fmt --all -- --check`
- **Build Release Binary:** `cargo build --workspace --release`

### Rust Native CLI (`clairvoy-rs`)
```bash
# Scan paths and display duplicate statistics
cargo run --bin clairvoy-rs -- scan /path/to/folder

# Scan and immediately clean exact duplicates into safe trash
cargo run --bin clairvoy-rs -- scan /path/to/folder --clean --mode trash

# Launch interactive Google Suite Web Studio
cargo run --bin clairvoy-rs -- ui --port 8000 --host 0.0.0.0

# Launch Web Studio without background autonomous watcher daemon
cargo run --bin clairvoy-rs -- ui --no-daemon
```

---

## 2. Core Invariants & Agent Rules

1. **Maintain `AGENTS.md` Always:**
   - Keep this file and subdocs synchronized with architecture and tooling changes.
   - Keep `AGENTS.md` strictly under 15KB per instruction budget tests (`wc -c AGENTS.md < 15000`).
2. **ASCII Art for All Terminal/Chat Diagrams:**
   - Never output Mermaid, graphviz, or image tags in chat or terminal logs. Use clean box-drawing ASCII art (`+---`, `|`, `-->`).
3. **Clickable Links for Files & Symbols:**
   - All references to files, functions, classes, or tests in responses must use clickable `file://` markdown links (e.g. [`db.rs`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-core/src/db.rs)).
4. **Local-First & Zero-Clobber Invariants:**
   - Zero unauthenticated cloud API calls. 100% offline execution.
   - Destructive operations (trash, hardlinking, deleting) must never overwrite without verification and manifest tracking. Keeper files must never be unlinked.
5. **Pure Rust Primacy:**
   - Pure Rust architecture across all 7 workspace crates. Zero Python runtime dependencies.
6. **Strict Memory Ceiling:**
   - Filesystem traversal must strictly use bounded backpressure (`flume::bounded(2048)`) guaranteeing $\le 50\text{MB}$ resident RAM across multi-million file workloads.
7. **Strict Quality Standards:**
   - Rust 2021 edition. `cargo test --workspace` (100% pass) and `cargo clippy --workspace --all-targets -- -D warnings` (0 warnings).

---

## 3. High-Level Architecture Overview

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

## 4. Workspace Crates (`crates/`)

- [`crates/clairvoy-core`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-core): Canonical data models ([`FileEntry`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-core/src/models.rs), [`DuplicateRecord`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-core/src/models.rs), [`ScanSummary`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-core/src/models.rs)), plugin traits ([`MatcherPlugin`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-core/src/traits.rs), [`KeeperStrategy`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-core/src/traits.rs)), typed errors ([`EngineError`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-core/src/errors.rs)), and embedded SQLite persistence engine ([`Database`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-core/src/db.rs) with WAL mode at `~/.clairvoy/clairvoy.db`).
- [`crates/clairvoy-scanner`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-scanner): Zero-copy bounded streaming filesystem crawler with XXH3 4KB SIMD hashing and `flume::bounded(2048)` backpressure.
- [`crates/clairvoy-model`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-model): Pluggable vision model runtime, perceptual `dHash` backend, and `models.toml` registry.
- [`crates/clairvoy-plugins`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-plugins): Modular matchers ([`ExactHashMatcherPlugin`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-plugins/src/exact_hash.rs) with parallel BLAKE3, [`PhotoVisionMatcherPlugin`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-plugins/src/photo_vision.rs)).
- [`crates/clairvoy-engine`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-engine): Multi-tier [`DeduplicationPipeline`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-engine/src/pipeline.rs) orchestrator, [`CompositeKeeperStrategy`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-engine/src/pipeline.rs) rule engine, and [`AutonomousWatcher`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-engine/src/watcher.rs) background daemon.
- [`crates/clairvoy-server`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-server): High-throughput Axum web server exposing full M3 API, SSE progress streaming, and directory navigation.
- [`crates/clairvoy-cli`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-cli): Native CLI executable `clairvoy-rs` (`scan`, `clean`, `ui` with optional `--no-daemon`).

---

## 5. Progressive Disclosure & Detailed Documentation

In-depth guidelines are organized into dedicated documents:

- **System Architecture & Deep Modules:** [`docs/ARCHITECTURE.md`](file:///home/shubhamshah207/clairvoy/docs/ARCHITECTURE.md)
  - Crate structure, short-circuit pipeline pruning, composite keeper scoring, DeleteEngine, and Google Photos Product Studio.
- **Google Suite Premier UX Spec & Plans:** [`docs/superpowers/specs/2026-09-19-google-suite-premier-ux-design.md`](file:///home/shubhamshah207/clairvoy/docs/superpowers/specs/2026-09-19-google-suite-premier-ux-design.md) & [`docs/superpowers/plans/2026-09-19-google-suite-premier-ux-design.md`](file:///home/shubhamshah207/clairvoy/docs/superpowers/plans/2026-09-19-google-suite-premier-ux-design.md)
  - Dark-mode UI, 2-track Smart Clean hero (exact batch prune vs. AI similar inspection), Top Shot comparison studio with sync zoom/pan, Drive table view with density toggle, safe hardlinking modal, and global Escape navigation.
- **Autonomous Watcher & SQLite Persistence Spec & Plans:** [`docs/superpowers/specs/2026-09-19-rust-autonomous-watcher-and-sqlite-persistence.md`](file:///home/shubhamshah207/clairvoy/docs/superpowers/specs/2026-09-19-rust-autonomous-watcher-and-sqlite-persistence.md) & [`docs/superpowers/plans/2026-09-19-rust-autonomous-watcher-and-sqlite-persistence.md`](file:///home/shubhamshah207/clairvoy/docs/superpowers/plans/2026-09-19-rust-autonomous-watcher-and-sqlite-persistence.md)
  - Details SQLite WAL database at `~/.clairvoy/clairvoy.db`, inotify background surveillance daemon, sliding quiet window, and SSE event streaming.
- **Plugin Developer Guide:** [`docs/PLUGINS.md`](file:///home/shubhamshah207/clairvoy/docs/PLUGINS.md)
  - Creating custom Matcher, Keeper, and Action plugins via Rust traits.
- **Testing & Verification Guide:** [`docs/TESTING.md`](file:///home/shubhamshah207/clairvoy/docs/TESTING.md)
  - Workspace test execution, Clippy standards, and testing invariants.
- **Rust High-Performance Guidelines:** [`docs/RUST_GUIDELINES.md`](file:///home/shubhamshah207/clairvoy/docs/RUST_GUIDELINES.md)
  - Zero-copy memory patterns, bounded queue backpressure, SIMD hashing, Rayon/Tokio boundaries, and `thiserror` domain errors.
- **Performance Benchmarks & Analysis:** [`docs/BENCHMARKS.md`](file:///home/shubhamshah207/clairvoy/docs/BENCHMARKS.md)
  - Empirical comparisons across real-world workloads, SIMD profiling, and memory invariants.
- **Enterprise Security Policy:** [`SECURITY.md`](file:///home/shubhamshah207/clairvoy/SECURITY.md)
  - Path traversal defenses, system root isolation, and sanitized shell generation.

---

## 6. Agent Tool Portability

- [`CLAUDE.md`](file:///home/shubhamshah207/clairvoy/CLAUDE.md) is symlinked to `AGENTS.md`.
- [`agents.md`](file:///home/shubhamshah207/clairvoy/agents.md) is symlinked to `AGENTS.md`.
- Both ensure universal agent compatibility across Claude Code, Cursor, Windsurf, Copilot, and Antigravity.
