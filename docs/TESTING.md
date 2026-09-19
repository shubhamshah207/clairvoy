# Clairvoy Testing & Verification Guide

This document outlines the testing conventions, fixtures, fast feedback loops, and linter standards for the pure Rust Clairvoy workspace.

---

## 1. Fast Feedback Loop & Commands

Clairvoy is built as a pure Rust cargo workspace. Tests and linter verification run via standard Cargo commands:

```bash
# Set Cargo path if needed
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

# Run entire workspace test suite
cargo test --workspace

# Run tests for a specific crate
cargo test -p clairvoy-core
cargo test -p clairvoy-server
cargo test -p clairvoy-engine

# Run a specific integration test file
cargo test -p clairvoy-server --test test_server
cargo test -p clairvoy-engine --test test_watcher

# Run with verbose stdout capture
cargo test --workspace -- --nocapture

# Run workspace Clippy with strict zero-warning policy
cargo clippy --workspace --all-targets -- -D warnings

# Build release binary
cargo build --workspace --release
```

---

## 2. Test Suite Structure by Crate

```
+---------------------------------------------------------------------------------------------------------+
|                                    CLAIRVOY TEST SUITE STRUCTURE                                        |
+---------------------------------------------------------------------------------------------------------+
| [crates/clairvoy-core]                                                                                  |
|   └── tests/test_database.rs       : SQLite WAL mode, schema migration, transactions, missing file prune|
| [crates/clairvoy-scanner]                                                                               |
|   └── tests/test_scanner.rs        : Parallel crawler, SIMD XXH3 quickhash, bounded flume backpressure  |
| [crates/clairvoy-model]                                                                                 |
|   └── tests/test_model.rs          : Perceptual dHash backend, model registry parsing, distances       |
| [crates/clairvoy-plugins]                                                                               |
|   ├── tests/test_exact_hash.rs     : BLAKE3 SIMD hashing, 0-byte file filtering, exact clusters        |
|   └── tests/test_photo_vision.rs   : Perceptual photo similarity clustering, cosine distance thresholds |
| [crates/clairvoy-engine]                                                                                |
|   ├── tests/test_pipeline.rs       : Chained multi-tier deduplication, short-circuit pruning, scoring   |
|   └── tests/test_watcher.rs        : Autonomous watcher daemon, sliding debounce quiet window, sweeps   |
| [crates/clairvoy-server]                                                                                |
|   └── tests/test_server.rs         : Axum API endpoints, SSE streams, watch targets CRUD, Smart Clean  |
| [crates/clairvoy-cli]                                                                                   |
|   └── tests/test_cli.rs            : CLI argument parsing, --no-daemon flag parsing, subcommands        |
+---------------------------------------------------------------------------------------------------------+
```

### Detailed Crate Responsibilities

- [`crates/clairvoy-core`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-core): Validates canonical data structures (`FileEntry`, `DuplicateRecord`, `ScanSummary`), plugin traits, and `Database` SQLite persistence (storing scan runs, duplicate clusters, file index, and atomic item removal).
- [`crates/clairvoy-scanner`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-scanner): Validates high-speed directory walking via `jwalk`, bounded queue streaming (`flume::bounded(2048)`), and rapid candidate discrimination via 4KB XXH3 hashing.
- [`crates/clairvoy-model`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-model): Validates pluggable model runtimes and zero-dependency 64-bit perceptual hashing.
- [`crates/clairvoy-plugins`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-plugins): Validates Tier 1 exact BLAKE3 deduplication and Tier 2 visual perceptual similarity clustering.
- [`crates/clairvoy-engine`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-engine): Validates multi-tier execution orchestration, short-circuit candidate pruning, `CompositeKeeperStrategy` score calculations, and background filesystem surveillance via `AutonomousWatcher`.
- [`crates/clairvoy-server`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-server): Validates Axum endpoints (`/api/status`, `/api/scan`, `/api/runs`, `/api/watch/paths`, `/api/status/stream`), safe trash isolation, and single-page application delivery.
- [`crates/clairvoy-cli`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-cli): Validates CLI command-line interface invocation and argument parsing for `clairvoy-rs`.

---

## 3. Linter & Static Analysis Standards

All code submitted to the repository must pass Rust's strict Clippy checks without warnings:

```bash
cargo clippy --workspace --all-targets -- -D warnings
```

Format verification:
```bash
cargo fmt --all -- --check
```

---

## 4. Testing Invariants

1. **Zero-Destruction Guarantee**: Tests must strictly use temporary directories (`tempfile::TempDir`) and never operate on live user directories.
2. **100% Offline Execution**: All unit, integration, and mock tests must pass without external internet connectivity or unauthenticated network requests.
3. **Memory Ceiling ($\le 50\text{MB}$)**: Scanner and pipeline tests assert bounded queue backpressure and memory consumption across synthetic workloads.
4. **Idempotence & Safety**: Safe deletion and quarantine actions must verify rollback logs and enforce that designated keeper files can never be removed.
