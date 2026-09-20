<a id="readme-top"></a>

# Clairvoy 👁️

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Rust](https://img.shields.io/badge/rust-1.78+-orange.svg)](https://www.rust-lang.org/)
[![Workspace Tests](https://img.shields.io/badge/cargo%20test-passing-brightgreen.svg)](docs/TESTING.md)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey.svg)](docs/ARCHITECTURE.md)
[![Clippy](https://img.shields.io/badge/clippy-0%20warnings-brightgreen.svg)](docs/TESTING.md)

> **Clairvoy** (*from Clairvoyance — clear perception*) is an ultra-fast, 100% offline, privacy-first media deduplication and storage optimization engine built in pure Rust.
> It unifies lightning-fast parallel BLAKE3 SIMD hashing, perceptual AI vision matching, an autonomous background surveillance daemon with SQLite WAL persistence, and a premier Google Suite web interface.

<p align="center">
  <img src="docs/assets/screenshots/dashboard_preview.png" alt="Clairvoy Web Studio Dashboard in Dark Mode" width="92%">
</p>

> [!NOTE]
> Clairvoy is 100% local-first: zero unauthenticated cloud API calls, zero telemetry tracking, and strict $\le 50\text{MB}$ RAM backpressure guarantees across multi-million file workloads.

---

## ⚡ 30-Second Quickstart

```bash
# 1. Clone repository
git clone https://github.com/shubhamshah207/clairvoy.git
cd clairvoy

# 2. Build release binary
cargo build --workspace --release

# 3. Run high-speed deduplication scan
./target/release/clairvoy-rs scan ~/Pictures ~/Downloads

# 4. Launch the interactive Google Suite Web Studio
./target/release/clairvoy-rs ui --port 8000
```

---

## 🥊 Why Clairvoy? (Feature Matrix)

| Feature | Clairvoy 👁️ | Czkawka | dupeGuru | fdupes |
|:---|:---:|:---:|:---:|:---:|
| **Pure Rust Native Binary** | ✅ | ✅ | ❌ (Python) | ❌ (C) |
| **Local-First & 100% Offline** | ✅ | ✅ | ✅ | ✅ |
| **Perceptual AI Vision Matching** | ✅ | ⚠️ (pHash only) | ❌ | ❌ |
| **Autonomous Watcher Daemon** | ✅ (notify + SQLite WAL) | ❌ | ❌ | ❌ |
| **Google Suite Premier UI** | ✅ (M3 Dark Mode) | ❌ (GTK) | ❌ (Qt) | ❌ (CLI only) |
| **Synchronized Loupe Zoom Comparison** | ✅ | ❌ | ❌ | ❌ |
| **Zero-Space NTFS/POSIX Hardlinking** | ✅ | ✅ | ❌ | ✅ |
| **Deterministic Keeper Scoring** | ✅ | ⚠️ (Manual) | ⚠️ (Manual) | ❌ |
| **Safe Trash with 1-Click Undo** | ✅ | ⚠️ | ❌ | ❌ |
| **Strict RAM Ceiling ($\le 50\text{MB}$)** | ✅ (Bounded streaming) | ⚠️ | ❌ | ❌ |

---

## 📸 Feature Showcase

### 1. Google Photos Top Shot Comparison Studio
Side-by-side visual comparison with synchronized loupe zoom and pan, live resolution badges (4K vs 720p), and instant 1-click keeper swapping.

<p align="center">
  <img src="docs/assets/screenshots/visual_diff.png" alt="Clairvoy Visual Diff Comparison" width="92%">
</p>

### 2. High-Speed Native CLI (`clairvoy-rs`)
Processes tens of thousands of files across storage volumes in seconds with SIMD XXH3 quick-hashing and multi-threaded BLAKE3 tree hashing.

<p align="center">
  <img src="docs/assets/screenshots/cli_execution.svg" alt="Clairvoy CLI Execution" width="92%">
</p>

---

## 🏛️ System Architecture

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

### Workspace Crates

- [`crates/clairvoy-core`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-core): Canonical models (`FileEntry`, `DuplicateRecord`, `ScanSummary`), traits, and embedded SQLite WAL persistence engine (`~/.clairvoy/clairvoy.db`).
- [`crates/clairvoy-scanner`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-scanner): Parallel zero-copy streaming filesystem crawler with SIMD XXH3 quick-hashing and `flume::bounded(2048)` backpressure.
- [`crates/clairvoy-model`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-model): Pluggable vision model runtime and 64-bit perceptual hashing backend (`dHash`).
- [`crates/clairvoy-plugins`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-plugins): Modular matchers (`ExactHashMatcherPlugin` with parallel BLAKE3, `PhotoVisionMatcherPlugin`).
- [`crates/clairvoy-engine`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-engine): Multi-tier `DeduplicationPipeline` orchestrator, `CompositeKeeperStrategy` rule engine, and `AutonomousWatcher` background daemon.
- [`crates/clairvoy-server`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-server): High-throughput Axum web server exposing full M3 API, SSE live progress streaming (`/api/status/stream`), and directory navigation.
- [`crates/clairvoy-cli`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-cli): Native CLI binary `clairvoy-rs` (`scan`, `clean`, `ui`).

---

## 🛠️ CLI Usage

```bash
# Scan paths and display duplicate statistics
./target/release/clairvoy-rs scan /mnt/photos /mnt/backups

# Scan and immediately clean exact duplicates into safe trash
./target/release/clairvoy-rs scan /mnt/photos --clean --mode trash

# Launch Google Suite Web UI on default port 8000
./target/release/clairvoy-rs ui

# Launch UI with custom port and host without background watcher daemon
./target/release/clairvoy-rs ui --port 8080 --host 0.0.0.0 --no-daemon
```

---

## 🛡️ Safe Deletion & Storage Optimization

Clairvoy is designed with strict **zero-clobber and zero-accidental-deletion invariants**:

1. **Safe Soft Delete (Move to Trash)**: Redundant duplicates are safely relocated to `.clairvoy_trash/` alongside an audit manifest. Any file can be restored with a single click.
2. **Permanent Deletion Enforces Keeper Assertion**: The deletion engine explicitly asserts that designated keeper files can never be deleted under any circumstances.
3. **Atomic Zero-Space Hardlinking**: Duplicate files on the same filesystem can be replaced with atomic hardlinks to the keeper inode, instantly recovering 100% of wasted space while preserving all existing directory paths.

---

## 🧪 Testing & Verification

```bash
# Run workspace tests (100% pass)
cargo test --workspace

# Run Clippy with strict zero-warning policy
cargo clippy --workspace --all-targets -- -D warnings

# Build optimized release binary
cargo build --workspace --release
```

<p align="right">(<a href="#readme-top">back to top ↑</a>)</p>

---

## 🤝 Contributing & Community

Contributions are welcome! Please read [`CONTRIBUTING.md`](CONTRIBUTING.md) for local setup, test invariants, and coding standards. For security vulnerabilities, consult [`SECURITY.md`](SECURITY.md).

---

## 📄 License

Licensed under the [Apache License, Version 2.0](LICENSE).

<p align="right">(<a href="#readme-top">back to top ↑</a>)</p>
