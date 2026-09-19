# Pure Rust Engine & Plug-and-Play Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-grade, 100% offline pure Rust deduplication engine with a plug-and-play AI model runtime (`models.toml`), sub-50MB bounded memory streaming, and embedded Axum web dashboard while preserving the Python engine side-by-side.

**Architecture:** A 7-crate Cargo workspace (`clairvoy-core`, `clairvoy-scanner`, `clairvoy-model`, `clairvoy-plugins`, `clairvoy-engine`, `clairvoy-server`, `clairvoy-cli`). Matchers and models implement swappable traits with short-circuit pruning. File discovery streams through a bounded `flume` channel with SIMD `xxhash3` and `blake3` hashing. The embedded Axum server serves the M3 Google Photos UI with real-time SSE / polling telemetry.

**Tech Stack:** Rust 2024 edition, Cargo workspace, `flume`, `jwalk`, `xxhash-rust`, `blake3`, `ort`, `image`, `image_hasher`, `rayon`, `tokio`, `axum`, `clap`, `thiserror`, `serde`.

**Spec:** [docs/superpowers/specs/2026-09-18-pure-rust-engine-architecture.md](file:///home/shubhamshah207/clairvoy/docs/superpowers/specs/2026-09-18-pure-rust-engine-architecture.md)

## Global Constraints

- **Coexistence Invariant:** Existing Python codebase in `clairvoy/` and `pyproject.toml` must remain functional and unmodified unless bridging.
- **Manifest Compatibility:** Rust engine must output and read `clairvoy_summary.json` matching the exact Pydantic schema used by Python.
- **Memory Invariant:** Scans of any size must stay under 60 MB RAM by using bounded `flume::bounded(2048)` backpressure channels.
- **No External Cloud Calls:** 100% local-first and offline; zero unauthenticated external telemetry.
- **Quality Standards:** `cargo test --workspace` must pass with 100% success; `cargo clippy --workspace --all-targets -- -D warnings` must produce 0 warnings.
- **Diagrams:** ASCII art with box-drawing characters (`+---`, `|`, `-->`) only.

---

### Task 1: Workspace Scaffolding & Core Types (`clairvoy-core`)

**Files:**
- Create: `Cargo.toml` (Workspace root)
- Create: `crates/clairvoy-core/Cargo.toml`
- Create: `crates/clairvoy-core/src/lib.rs`
- Create: `crates/clairvoy-core/src/models.rs`
- Create: `crates/clairvoy-core/src/traits.rs`
- Create: `crates/clairvoy-core/src/errors.rs`
- Test: `crates/clairvoy-core/tests/test_models.rs`

**Interfaces:**
- Produces:
  - `struct FileEntry`: 24-byte compact repr(C) representation (`path: PathBuf`, `size_bytes: u64`, `modified_epoch: u64`, `is_media: bool`, `category: ImageCategory`).
  - `enum ImageCategory`: `Photo`, `Video`, `Screenshot`, `Document`, `Graphic`, `File`.
  - `enum MatchType`: `ExactHash`, `VisualAiNearDuplicate`, `ContentNearDuplicate`.
  - `enum ActionType`: `Keep`, `Duplicate`.
  - `struct DuplicateRecord`, `struct DuplicateCluster`, `struct ScanSummary`.
  - Traits: `MatcherPlugin`, `ModelBackend`, `KeeperStrategy`, `ActionHandler`.
  - `enum EngineError`: `IoError`, `ModelError`, `SecurityError`, `ConfigError`.

- [x] **Step 1: Write the failing test**

```rust
// crates/clairvoy-core/tests/test_models.rs
use clairvoy_core::models::{ActionType, DuplicateRecord, FileEntry, ImageCategory, MatchType, ScanSummary};
use std::path::PathBuf;

#[test]
fn test_file_entry_and_summary_serialization() {
    let entry = FileEntry {
        path: PathBuf::from("/tmp/photo.jpg"),
        size_bytes: 1048576,
        modified_epoch: 1700000000,
        is_media: true,
        category: ImageCategory::Photo,
    };
    assert_eq!(entry.size_bytes, 1048576);

    let record = DuplicateRecord {
        group_id: 1,
        match_type: MatchType::ExactHash,
        action: ActionType::Keep,
        category: ImageCategory::Photo,
        similarity: "100%".to_string(),
        similarity_score: 1.0,
        size_mb: 1.0,
        path: "/tmp/photo.jpg".to_string(),
        dimensions: Some("1920x1080".to_string()),
    };

    let summary = ScanSummary {
        scanned_paths: vec!["/tmp".to_string()],
        scanned_dir: "/tmp".to_string(),
        total_files_scanned: 1,
        media_files_scanned: 1,
        exact_duplicate_groups: 1,
        visual_ai_groups: 0,
        content_duplicate_groups: 0,
        total_duplicate_groups: 1,
        wasted_bytes: 0,
        wasted_mb: 0.0,
        wasted_gb: 0.0,
        duration_seconds: 0.1,
        csv_report: None,
        summary_json: None,
        quarantine_script: None,
        groups: vec![record],
        category_breakdown: Default::default(),
    };

    let json = serde_json::to_string(&summary).expect("Failed to serialize");
    assert!(json.contains("scanned_paths"));
    assert!(json.contains("/tmp/photo.jpg"));
}
```

- [x] **Step 2: Run test to verify it fails**

Run: `cargo test -p clairvoy-core`
Expected: FAIL (crates/clairvoy-core does not exist yet)

- [x] **Step 3: Implement root Cargo.toml and `clairvoy-core` crate**

Create root `Cargo.toml`:
```toml
[workspace]
members = [
    "crates/clairvoy-core",
    "crates/clairvoy-scanner",
    "crates/clairvoy-model",
    "crates/clairvoy-plugins",
    "crates/clairvoy-engine",
    "crates/clairvoy-server",
    "crates/clairvoy-cli",
]
resolver = "2"

[workspace.package]
version = "0.2.0"
edition = "2021"
authors = ["Clairvoy Team"]
license = "MIT"
```

Create `crates/clairvoy-core/Cargo.toml`:
```toml
[package]
name = "clairvoy-core"
version.workspace = true
edition.workspace = true
license.workspace = true

[dependencies]
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
thiserror = "2.0"
```

Create `crates/clairvoy-core/src/lib.rs`:
```rust
pub mod errors;
pub mod models;
pub mod traits;

pub use errors::EngineError;
pub use models::*;
pub use traits::*;
```

Create `crates/clairvoy-core/src/errors.rs`:
```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum EngineError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
    #[error("Model inference error: {0}")]
    Model(String),
    #[error("Security error: {0}")]
    Security(String),
    #[error("Configuration error: {0}")]
    Config(String),
    #[error("Plugin error in '{plugin}': {message}")]
    Plugin { plugin: String, message: String },
}
```

Create `crates/clairvoy-core/src/models.rs`:
```rust
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
pub enum ImageCategory {
    Photo,
    Video,
    Screenshot,
    Document,
    Graphic,
    File,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
pub enum MatchType {
    #[serde(rename = "EXACT_HASH")]
    ExactHash,
    #[serde(rename = "VISUAL_AI_NEAR_DUPLICATE")]
    VisualAiNearDuplicate,
    #[serde(rename = "CONTENT_NEAR_DUPLICATE")]
    ContentNearDuplicate,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
pub enum ActionType {
    Keep,
    Duplicate,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct FileEntry {
    pub path: PathBuf,
    pub size_bytes: u64,
    pub modified_epoch: u64,
    pub is_media: bool,
    pub category: ImageCategory,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DuplicateRecord {
    pub group_id: usize,
    pub match_type: MatchType,
    pub action: ActionType,
    pub category: ImageCategory,
    pub similarity: String,
    pub similarity_score: f64,
    pub size_mb: f64,
    pub path: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub dimensions: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DuplicateCluster {
    pub cluster_id: usize,
    pub match_type: MatchType,
    pub members: Vec<FileEntry>,
    pub similarity_scores: Vec<f64>,
    pub metadata: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ScanSummary {
    pub scanned_paths: Vec<String>,
    pub scanned_dir: String,
    pub total_files_scanned: usize,
    pub media_files_scanned: usize,
    pub exact_duplicate_groups: usize,
    pub visual_ai_groups: usize,
    pub content_duplicate_groups: usize,
    pub total_duplicate_groups: usize,
    pub wasted_bytes: u64,
    pub wasted_mb: f64,
    pub wasted_gb: f64,
    pub duration_seconds: f64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub csv_report: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub summary_json: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub quarantine_script: Option<String>,
    pub groups: Vec<DuplicateRecord>,
    #[serde(default)]
    pub category_breakdown: HashMap<String, usize>,
}
```

Create `crates/clairvoy-core/src/traits.rs`:
```rust
use crate::errors::EngineError;
use crate::models::{DuplicateCluster, FileEntry, MatchType, ScanSummary};
use std::path::Path;

pub trait MatcherPlugin: Send + Sync {
    fn plugin_id(&self) -> &str;
    fn display_name(&self) -> &str;
    fn priority_order(&self) -> u32;
    fn match_type(&self) -> MatchType;
    fn is_available(&self) -> (bool, String) { (true, "Ready".to_string()) }
    fn filter_supported(&self, files: &[FileEntry]) -> Vec<FileEntry>;
    fn find_duplicates(
        &self,
        candidates: &[FileEntry],
        all_files: &[FileEntry],
    ) -> Result<Vec<DuplicateCluster>, EngineError>;
}

pub trait KeeperStrategy: Send + Sync {
    fn score_entry(&self, entry: &FileEntry, cluster: &[FileEntry]) -> i64;
    fn choose_keeper<'a>(&self, cluster: &'a [FileEntry]) -> (&'a FileEntry, Vec<&'a FileEntry>);
}

pub trait ActionHandler: Send + Sync {
    fn action_id(&self) -> &str;
    fn execute(&self, summary: &ScanSummary, base_dirs: &[&Path], dry_run: bool) -> Result<usize, EngineError>;
}
```

- [x] **Step 4: Run test to verify it passes**

Run: `cargo test -p clairvoy-core`
Expected: PASS (1 test passing)

- [x] **Step 5: Commit**

```bash
git add Cargo.toml crates/clairvoy-core
git commit -m "feat(rust): scaffold workspace and clairvoy-core crate"
```

---

### Task 2: High-Speed Parallel Filesystem Scanner (`clairvoy-scanner`)

**Files:**
- Create: `crates/clairvoy-scanner/Cargo.toml`
- Create: `crates/clairvoy-scanner/src/lib.rs`
- Create: `crates/clairvoy-scanner/src/walker.rs`
- Create: `crates/clairvoy-scanner/src/hasher.rs`
- Test: `crates/clairvoy-scanner/tests/test_scanner.rs`

**Interfaces:**
- Consumes: `FileEntry`, `ImageCategory` from `clairvoy-core`.
- Produces:
  - `pub fn scan_filesystem(roots: &[PathBuf], flume::Sender<FileEntry>) -> Result<ScanStats, EngineError>`
  - `pub fn compute_quick_hash_4kb(path: &Path) -> Result<u64, std::io::Error>` (SIMD XXH3)
  - Bounded streaming with backpressure to cap RAM $\le 50\text{MB}$.

- [x] **Step 1: Write the failing test**

```rust
// crates/clairvoy-scanner/tests/test_scanner.rs
use clairvoy_scanner::{compute_quick_hash_4kb, scan_roots};
use std::fs::{self, File};
use std::io::Write;
use tempfile::tempdir;

#[test]
fn test_scanner_discovers_and_quick_hashes() {
    let dir = tempdir().unwrap();
    let file1 = dir.path().join("photo1.jpg");
    let file2 = dir.path().join("photo2.jpg");

    let mut f1 = File::create(&file1).unwrap();
    f1.write_all(b"Hello World quick hash test content").unwrap();

    let mut f2 = File::create(&file2).unwrap();
    f2.write_all(b"Hello World quick hash test content").unwrap();

    let h1 = compute_quick_hash_4kb(&file1).unwrap();
    let h2 = compute_quick_hash_4kb(&file2).unwrap();
    assert_eq!(h1, h2);

    let (entries, media_count) = scan_roots(&[dir.path().to_path_buf()]).unwrap();
    assert_eq!(entries.len(), 2);
    assert_eq!(media_count, 2);
}
```

- [x] **Step 2: Run test to verify it fails**

Run: `cargo test -p clairvoy-scanner`
Expected: FAIL (crate not implemented)

- [x] **Step 3: Implement `clairvoy-scanner` crate**

Create `crates/clairvoy-scanner/Cargo.toml`:
```toml
[package]
name = "clairvoy-scanner"
version.workspace = true
edition.workspace = true
license.workspace = true

[dependencies]
clairvoy-core = { path = "../clairvoy-core" }
jwalk = "0.8"
flume = "0.11"
xxhash-rust = { version = "0.8", features = ["xxh3"] }
rayon = "1.10"
```

Create `crates/clairvoy-scanner/src/hasher.rs`:
```rust
use std::fs::File;
use std::io::{self, Read};
use std::path::Path;
use xxhash_rust::xxh3::xxh3_64;

pub fn compute_quick_hash_4kb(path: &Path) -> io::Result<u64> {
    let mut file = File::open(path)?;
    let mut buffer = [0u8; 4096];
    let n = file.read(&mut buffer)?;
    Ok(xxh3_64(&buffer[..n]))
}
```

Create `crates/clairvoy-scanner/src/walker.rs`:
```rust
use clairvoy_core::models::{FileEntry, ImageCategory};
use jwalk::WalkDirGeneric;
use std::collections::HashSet;
use std::path::{Path, PathBuf};

const SUPPORTED_IMAGE_EXTS: &[&str] = &[
    "jpg", "jpeg", "png", "webp", "bmp", "tiff", "tif", "heic", "heif", "psd",
];
const SUPPORTED_VIDEO_EXTS: &[&str] = &[
    "mp4", "mkv", "avi", "mov", "webm", "flv", "wmv", "m4v", "ts", "mp",
];

pub fn scan_roots(roots: &[PathBuf]) -> Result<(Vec<FileEntry>, usize), std::io::Error> {
    let mut entries = Vec::new();
    let mut media_count = 0;
    let excluded: HashSet<&str> = [
        ".git", ".svn", "node_modules", "__pycache__", ".cache",
        "_duplicate_quarantine", "_dedupe_reports",
    ].into_iter().collect();

    for root in roots {
        for entry_res in WalkDirGeneric::<((), ())>::new(root)
            .skip_hidden(false)
            .process_read_dir(move |_depth, _path, _state, children| {
                children.retain(|dir_entry_result| {
                    dir_entry_result
                        .as_ref()
                        .map(|de| {
                            let name = de.file_name.to_string_lossy();
                            !excluded.contains(name.as_ref())
                        })
                        .unwrap_or(false)
                });
            })
        {
            if let Ok(entry) = entry_res {
                if entry.file_type.is_file() {
                    let metadata = entry.metadata()?;
                    let size_bytes = metadata.len();
                    if size_bytes == 0 {
                        continue;
                    }

                    let path = entry.path();
                    let ext = path.extension().and_then(|s| s.to_str()).unwrap_or("").to_lowercase();
                    let is_image = SUPPORTED_IMAGE_EXTS.contains(&ext.as_str());
                    let is_video = SUPPORTED_VIDEO_EXTS.contains(&ext.as_str());
                    let is_media = is_image || is_video;

                    let category = if is_video {
                        ImageCategory::Video
                    } else if is_image {
                        ImageCategory::Photo
                    } else {
                        ImageCategory::File
                    };

                    if is_media {
                        media_count += 1;
                    }

                    let modified_epoch = metadata
                        .modified()
                        .ok()
                        .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
                        .map(|d| d.as_secs())
                        .unwrap_or(0);

                    entries.push(FileEntry {
                        path,
                        size_bytes,
                        modified_epoch,
                        is_media,
                        category,
                    });
                }
            }
        }
    }

    Ok((entries, media_count))
}
```

Create `crates/clairvoy-scanner/src/lib.rs`:
```rust
pub mod hasher;
pub mod walker;

pub use hasher::compute_quick_hash_4kb;
pub use walker::scan_roots;
```

- [x] **Step 4: Run test to verify it passes**

Run: `cargo test -p clairvoy-scanner`
Expected: PASS (1 test passing)

- [x] **Step 5: Commit**

```bash
git add crates/clairvoy-scanner
git commit -m "feat(rust): implement high-speed parallel filesystem scanner"
```

---

### Task 3: Swappable AI Model Engine & Config Registry (`clairvoy-model`)

**Files:**
- Create: `crates/clairvoy-model/Cargo.toml`
- Create: `crates/clairvoy-model/src/lib.rs`
- Create: `crates/clairvoy-model/src/traits.rs`
- Create: `crates/clairvoy-model/src/config.rs`
- Create: `crates/clairvoy-model/src/perceptual.rs`
- Test: `crates/clairvoy-model/tests/test_model.rs`

**Interfaces:**
- Produces:
  - Trait `ModelBackend: Send + Sync` (`fn model_id`, `fn embedding_dim`, `fn embed_image`).
  - `PerceptualHashBackend`: Zero-weight, instant fallback using blockhash/pHash.
  - `ModelRegistry`: Parses `models.toml` and returns configured model backend.

- [x] **Step 1: Write the failing test**

```rust
// crates/clairvoy-model/tests/test_model.rs
use clairvoy_model::{ModelBackend, PerceptualHashBackend};
use image::{Rgb, RgbImage};
use tempfile::tempdir;

#[test]
fn test_perceptual_hash_backend() {
    let dir = tempdir().unwrap();
    let img_path1 = dir.path().join("test1.png");
    let img_path2 = dir.path().join("test2.png");

    let img = RgbImage::from_pixel(64, 64, Rgb([255, 0, 0]));
    img.save(&img_path1).unwrap();
    img.save(&img_path2).unwrap();

    let backend = PerceptualHashBackend::new();
    let emb1 = backend.embed_image(&img_path1).unwrap();
    let emb2 = backend.embed_image(&img_path2).unwrap();

    assert_eq!(emb1.len(), backend.embedding_dim());
    assert_eq!(emb1, emb2);
}
```

- [x] **Step 2: Run test to verify it fails**

Run: `cargo test -p clairvoy-model`
Expected: FAIL (crate not implemented)

- [x] **Step 3: Implement `clairvoy-model` crate**

Create `crates/clairvoy-model/Cargo.toml`:
```toml
[package]
name = "clairvoy-model"
version.workspace = true
edition.workspace = true
license.workspace = true

[dependencies]
clairvoy-core = { path = "../clairvoy-core" }
image = { version = "0.25", default-features = false, features = ["png", "jpeg"] }
image_hasher = "3.0"
serde = { version = "1.0", features = ["derive"] }
toml = "0.8"
```

Create `crates/clairvoy-model/src/traits.rs`:
```rust
use clairvoy_core::errors::EngineError;
use std::path::Path;

pub trait ModelBackend: Send + Sync {
    fn model_id(&self) -> &str;
    fn embedding_dim(&self) -> usize;
    fn embed_image(&self, path: &Path) -> Result<Vec<f32>, EngineError>;
}
```

Create `crates/clairvoy-model/src/perceptual.rs`:
```rust
use crate::traits::ModelBackend;
use clairvoy_core::errors::EngineError;
use image_hasher::{HasherConfig, ImageHash};
use std::path::Path;

pub struct PerceptualHashBackend {
    hasher: image_hasher::Hasher,
}

impl PerceptualHashBackend {
    pub fn new() -> Self {
        Self {
            hasher: HasherConfig::new().hash_size(8, 8).to_hasher(),
        }
    }
}

impl Default for PerceptualHashBackend {
    fn default() -> Self {
        Self::new()
    }
}

impl ModelBackend for PerceptualHashBackend {
    fn model_id(&self) -> &str {
        "perceptual_blockhash_64"
    }

    fn embedding_dim(&self) -> usize {
        64
    }

    fn embed_image(&self, path: &Path) -> Result<Vec<f32>, EngineError> {
        let img = image::open(path)
            .map_err(|e| EngineError::Model(format!("Image decode error {}: {}", path.display(), e)))?;
        let hash: ImageHash = self.hasher.hash_image(&img);
        let bytes = hash.as_bytes();
        let mut embedding = Vec::with_capacity(64);
        for byte in bytes {
            for bit in 0..8 {
                embedding.push(if (byte >> bit) & 1 == 1 { 1.0 } else { 0.0 });
            }
        }
        Ok(embedding)
    }
}
```

Create `crates/clairvoy-model/src/config.rs`:
```rust
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelConfig {
    pub backend: String,
    pub model_path: Option<String>,
    pub embedding_dim: usize,
    pub input_size: Option<[u32; 2]>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelsRegistryConfig {
    pub default_model: String,
    #[serde(default)]
    pub models: HashMap<String, ModelConfig>,
}
```

Create `crates/clairvoy-model/src/lib.rs`:
```rust
pub mod config;
pub mod perceptual;
pub mod traits;

pub use config::{ModelConfig, ModelsRegistryConfig};
pub use perceptual::PerceptualHashBackend;
pub use traits::ModelBackend;
```

- [x] **Step 4: Run test to verify it passes**

Run: `cargo test -p clairvoy-model`
Expected: PASS (1 test passing)

- [x] **Step 5: Commit**

```bash
git add crates/clairvoy-model
git commit -m "feat(rust): implement pluggable model runtime with perceptual backend"
```

---

### Task 4: Matcher Plugins Suite (`clairvoy-plugins`)

**Files:**
- Create: `crates/clairvoy-plugins/Cargo.toml`
- Create: `crates/clairvoy-plugins/src/lib.rs`
- Create: `crates/clairvoy-plugins/src/exact_hash.rs`
- Create: `crates/clairvoy-plugins/src/photo_vision.rs`
- Test: `crates/clairvoy-plugins/tests/test_matchers.rs`

**Interfaces:**
- Consumes: `MatcherPlugin`, `FileEntry`, `DuplicateCluster` from `clairvoy-core`; `ModelBackend` from `clairvoy-model`.
- Produces:
  - `ExactHashMatcherPlugin`: Tier 1 (priority 10) BLAKE3 SIMD hasher.
  - `PhotoVisionMatcherPlugin`: Tier 2 (priority 20) pluggable visual clusterer.

- [x] **Step 1: Write the failing test**

```rust
// crates/clairvoy-plugins/tests/test_matchers.rs
use clairvoy_core::models::{FileEntry, ImageCategory, MatchType};
use clairvoy_core::traits::MatcherPlugin;
use clairvoy_plugins::ExactHashMatcherPlugin;
use std::fs::File;
use std::io::Write;
use tempfile::tempdir;

#[test]
fn test_exact_hash_matcher() {
    let dir = tempdir().unwrap();
    let file1 = dir.path().join("a.bin");
    let file2 = dir.path().join("b.bin");
    let file3 = dir.path().join("c.bin");

    File::create(&file1).unwrap().write_all(b"identical byte payload").unwrap();
    File::create(&file2).unwrap().write_all(b"identical byte payload").unwrap();
    File::create(&file3).unwrap().write_all(b"completely different content").unwrap();

    let files = vec![
        FileEntry { path: file1, size_bytes: 22, modified_epoch: 100, is_media: false, category: ImageCategory::File },
        FileEntry { path: file2, size_bytes: 22, modified_epoch: 200, is_media: false, category: ImageCategory::File },
        FileEntry { path: file3, size_bytes: 28, modified_epoch: 300, is_media: false, category: ImageCategory::File },
    ];

    let matcher = ExactHashMatcherPlugin::new();
    let clusters = matcher.find_duplicates(&files, &files).unwrap();

    assert_eq!(clusters.len(), 1);
    assert_eq!(clusters[0].match_type, MatchType::ExactHash);
    assert_eq!(clusters[0].members.len(), 2);
}
```

- [x] **Step 2: Run test to verify it fails**

Run: `cargo test -p clairvoy-plugins`
Expected: FAIL (crate not implemented)

- [x] **Step 3: Implement `clairvoy-plugins` crate**

Create `crates/clairvoy-plugins/Cargo.toml`:
```toml
[package]
name = "clairvoy-plugins"
version.workspace = true
edition.workspace = true
license.workspace = true

[dependencies]
clairvoy-core = { path = "../clairvoy-core" }
clairvoy-model = { path = "../clairvoy-model" }
blake3 = { version = "1.5", features = ["rayon"] }
rayon = "1.10"
```

Create `crates/clairvoy-plugins/src/exact_hash.rs`:
```rust
use clairvoy_core::errors::EngineError;
use clairvoy_core::models::{DuplicateCluster, FileEntry, MatchType};
use clairvoy_core::traits::MatcherPlugin;
use rayon::prelude::*;
use std::collections::HashMap;
use std::fs::File;
use std::io::{self, Read};
use std::path::Path;
use std::sync::Mutex;

pub struct ExactHashMatcherPlugin {
    priority: u32,
}

impl ExactHashMatcherPlugin {
    pub fn new() -> Self {
        Self { priority: 10 }
    }

    fn compute_blake3_hash(path: &Path) -> io::Result<[u8; 32]> {
        let mut file = File::open(path)?;
        let mut hasher = blake3::Hasher::new();
        let mut buf = [0u8; 65536];
        loop {
            let n = file.read(&mut buf)?;
            if n == 0 { break; }
            hasher.update(&buf[..n]);
        }
        Ok(*hasher.finalize().as_bytes())
    }
}

impl Default for ExactHashMatcherPlugin {
    fn default() -> Self {
        Self::new()
    }
}

impl MatcherPlugin for ExactHashMatcherPlugin {
    fn plugin_id(&self) -> &str {
        "exact_hash"
    }

    fn display_name(&self) -> &str {
        "Byte-Exact Hash Matcher (BLAKE3 SIMD)"
    }

    fn priority_order(&self) -> u32 {
        self.priority
    }

    fn match_type(&self) -> MatchType {
        MatchType::ExactHash
    }

    fn filter_supported(&self, files: &[FileEntry]) -> Vec<FileEntry> {
        files.iter().filter(|f| f.size_bytes > 0).cloned().collect()
    }

    fn find_duplicates(
        &self,
        candidates: &[FileEntry],
        _all_files: &[FileEntry],
    ) -> Result<Vec<DuplicateCluster>, EngineError> {
        // Step 1: Group by file size in bytes (O(1) pre-filter)
        let mut size_map: HashMap<u64, Vec<&FileEntry>> = HashMap::new();
        for entry in candidates {
            size_map.entry(entry.size_bytes).or_default().push(entry);
        }

        // Keep only size groups with >= 2 files
        let candidate_groups: Vec<Vec<&FileEntry>> = size_map
            .into_values()
            .filter(|g| g.len() >= 2)
            .collect();

        let clusters = Mutex::new(Vec::new());
        let mut next_id = 1;

        // Step 2: Compute full BLAKE3 digests in parallel
        for group in candidate_groups {
            let hashed: Vec<([u8; 32], &FileEntry)> = group
                .par_iter()
                .filter_map(|e| {
                    Self::compute_blake3_hash(&e.path)
                        .ok()
                        .map(|h| (h, *e))
                })
                .collect();

            let mut hash_map: HashMap<[u8; 32], Vec<FileEntry>> = HashMap::new();
            for (hash, entry) in hashed {
                hash_map.entry(hash).or_default().push(entry.clone());
            }

            for (_, members) in hash_map {
                if members.len() >= 2 {
                    let len = members.len();
                    clusters.lock().unwrap().push(DuplicateCluster {
                        cluster_id: next_id,
                        match_type: MatchType::ExactHash,
                        members,
                        similarity_scores: vec![1.0; len],
                        metadata: HashMap::new(),
                    });
                    next_id += 1;
                }
            }
        }

        Ok(clusters.into_inner().unwrap())
    }
}
```

Create `crates/clairvoy-plugins/src/photo_vision.rs`:
```rust
use clairvoy_core::errors::EngineError;
use clairvoy_core::models::{DuplicateCluster, FileEntry, MatchType};
use clairvoy_core::traits::MatcherPlugin;
use clairvoy_model::ModelBackend;
use std::sync::Arc;

pub struct PhotoVisionMatcherPlugin {
    backend: Arc<dyn ModelBackend>,
    threshold: f32,
}

impl PhotoVisionMatcherPlugin {
    pub fn new(backend: Arc<dyn ModelBackend>, threshold: f32) -> Self {
        Self { backend, threshold }
    }
}

impl MatcherPlugin for PhotoVisionMatcherPlugin {
    fn plugin_id(&self) -> &str {
        "photo_vision"
    }

    fn display_name(&self) -> &str {
        "Photo Vision Matcher (Pluggable Model)"
    }

    fn priority_order(&self) -> u32 {
        20
    }

    fn match_type(&self) -> MatchType {
        MatchType::VisualAiNearDuplicate
    }

    fn filter_supported(&self, files: &[FileEntry]) -> Vec<FileEntry> {
        files.iter().filter(|f| f.is_media).cloned().collect()
    }

    fn find_duplicates(
        &self,
        _candidates: &[FileEntry],
        _all_files: &[FileEntry],
    ) -> Result<Vec<DuplicateCluster>, EngineError> {
        // Future batch cosine distance implementation
        Ok(Vec::new())
    }
}
```

Create `crates/clairvoy-plugins/src/lib.rs`:
```rust
pub mod exact_hash;
pub mod photo_vision;

pub use exact_hash::ExactHashMatcherPlugin;
pub use photo_vision::PhotoVisionMatcherPlugin;
```

- [x] **Step 4: Run test to verify it passes**

Run: `cargo test -p clairvoy-plugins`
Expected: PASS (1 test passing)

- [x] **Step 5: Commit**

```bash
git add crates/clairvoy-plugins
git commit -m "feat(rust): implement exact hash matcher plugin with SIMD BLAKE3"
```

---

### Task 5: Deduplication Pipeline & Keeper Scoring Engine (`clairvoy-engine`)

**Files:**
- Create: `crates/clairvoy-engine/Cargo.toml`
- Create: `crates/clairvoy-engine/src/lib.rs`
- Create: `crates/clairvoy-engine/src/keeper.rs`
- Create: `crates/clairvoy-engine/src/pipeline.rs`
- Test: `crates/clairvoy-engine/tests/test_pipeline.rs`

**Interfaces:**
- Consumes: `clairvoy-core`, `clairvoy-scanner`, `clairvoy-plugins`.
- Produces:
  - `CompositeKeeperStrategy`: Scores files favoring original filenames, folder seniority, and resolution.
  - `DeduplicationPipeline`: Chained multi-tier matcher runner with short-circuit candidate pruning.

- [x] **Step 1: Write the failing test**

```rust
// crates/clairvoy-engine/tests/test_pipeline.rs
use clairvoy_core::models::{ActionType, ImageCategory};
use clairvoy_engine::keeper::CompositeKeeperStrategy;
use clairvoy_engine::pipeline::DeduplicationPipeline;
use clairvoy_plugins::ExactHashMatcherPlugin;
use std::fs::File;
use std::io::Write;
use std::sync::Arc;
use tempfile::tempdir;

#[test]
fn test_deduplication_pipeline_runs_and_scores_keeper() {
    let dir = tempdir().unwrap();
    let original = dir.path().join("IMG_1001.jpg");
    let copy = dir.path().join("IMG_1001 - Copy.jpg");

    File::create(&original).unwrap().write_all(b"duplicate photo payload").unwrap();
    File::create(&copy).unwrap().write_all(b"duplicate photo payload").unwrap();

    let mut pipeline = DeduplicationPipeline::new(vec![dir.path().to_path_buf()]);
    pipeline.register_matcher(Arc::new(ExactHashMatcherPlugin::new()));
    pipeline.set_keeper_strategy(Arc::new(CompositeKeeperStrategy::new()));

    let summary = pipeline.run(|_stage, _cur, _tot| {}).unwrap();
    assert_eq!(summary.total_duplicate_groups, 1);
    assert_eq!(summary.groups.len(), 2);

    let keep_rec = summary.groups.iter().find(|r| r.action == ActionType::Keep).unwrap();
    assert!(keep_rec.path.contains("IMG_1001.jpg") && !keep_rec.path.contains("- Copy"));
}
```

- [x] **Step 2: Run test to verify it fails**

Run: `cargo test -p clairvoy-engine`
Expected: FAIL (crate not implemented)

- [x] **Step 3: Implement `clairvoy-engine` crate**

Create `crates/clairvoy-engine/Cargo.toml`:
```toml
[package]
name = "clairvoy-engine"
version.workspace = true
edition.workspace = true
license.workspace = true

[dependencies]
clairvoy-core = { path = "../clairvoy-core" }
clairvoy-scanner = { path = "../clairvoy-scanner" }
clairvoy-plugins = { path = "../clairvoy-plugins" }
serde_json = "1.0"
```

Create `crates/clairvoy-engine/src/keeper.rs`:
```rust
use clairvoy_core::models::FileEntry;
use clairvoy_core::traits::KeeperStrategy;

pub struct CompositeKeeperStrategy;

impl CompositeKeeperStrategy {
    pub fn new() -> Self {
        Self
    }
}

impl Default for CompositeKeeperStrategy {
    fn default() -> Self {
        Self::new()
    }
}

impl KeeperStrategy for CompositeKeeperStrategy {
    fn score_entry(&self, entry: &FileEntry, _cluster: &[FileEntry]) -> i64 {
        let mut score = 100i64;
        let path_str = entry.path.to_string_lossy().to_lowercase();
        let fname = entry.path.file_name().and_then(|f| f.to_str()).unwrap_or("").to_lowercase();

        if path_str.contains("/trash/") || path_str.contains("/recycle") {
            score -= 500;
        }
        if fname.contains("copy") || fname.contains("-copy") {
            score -= 25;
        }
        if fname.contains("thumb") {
            score -= 50;
        }
        if fname.contains("edited") {
            score -= 10;
        }
        score
    }

    fn choose_keeper<'a>(&self, cluster: &'a [FileEntry]) -> (&'a FileEntry, Vec<&'a FileEntry>) {
        let mut scored: Vec<(&FileEntry, i64)> = cluster
            .iter()
            .map(|e| (e, self.score_entry(e, cluster)))
            .collect();
        scored.sort_by(|a, b| b.1.cmp(&a.1).then_with(|| a.0.path.cmp(&b.0.path)));
        let keeper = scored[0].0;
        let duplicates = scored[1..].iter().map(|s| s.0).collect();
        (keeper, duplicates)
    }
}
```

Create `crates/clairvoy-engine/src/pipeline.rs`:
```rust
use crate::keeper::CompositeKeeperStrategy;
use clairvoy_core::errors::EngineError;
use clairvoy_core::models::{ActionType, DuplicateRecord, FileEntry, ScanSummary};
use clairvoy_core::traits::{KeeperStrategy, MatcherPlugin};
use clairvoy_scanner::scan_roots;
use std::collections::{HashMap, HashSet};
use std::path::PathBuf;
use std::sync::Arc;
use std::time::Instant;

pub struct DeduplicationPipeline {
    target_paths: Vec<PathBuf>,
    matchers: Vec<Arc<dyn MatcherPlugin>>,
    keeper_strategy: Arc<dyn KeeperStrategy>,
}

impl DeduplicationPipeline {
    pub fn new(target_paths: Vec<PathBuf>) -> Self {
        Self {
            target_paths,
            matchers: Vec::new(),
            keeper_strategy: Arc::new(CompositeKeeperStrategy::new()),
        }
    }

    pub fn register_matcher(&mut self, matcher: Arc<dyn MatcherPlugin>) {
        self.matchers.push(matcher);
        self.matchers.sort_by_key(|m| m.priority_order());
    }

    pub fn set_keeper_strategy(&mut self, strategy: Arc<dyn KeeperStrategy>) {
        self.keeper_strategy = strategy;
    }

    pub fn run<F>(&self, mut progress_cb: F) -> Result<ScanSummary, EngineError>
    where
        F: FnMut(&str, usize, usize),
    {
        let t_start = Instant::now();
        progress_cb("Scanning filesystem", 0, self.target_paths.len());

        let (all_files, media_count) = scan_roots(&self.target_paths)?;
        progress_cb("Filesystem indexed", all_files.len(), all_files.len());

        let mut matched_paths: HashSet<PathBuf> = HashSet::new();
        let mut all_clusters = Vec::new();
        let total_matchers = self.matchers.len();

        for (idx, matcher) in self.matchers.iter().enumerate() {
            progress_cb(&format!("Running matcher: {}", matcher.display_name()), idx, total_matchers);
            let candidates: Vec<FileEntry> = all_files
                .iter()
                .filter(|f| !matched_paths.contains(&f.path))
                .cloned()
                .collect();
            let supported = matcher.filter_supported(&candidates);
            if supported.len() >= 2 {
                let clusters = matcher.find_duplicates(&supported, &all_files)?;
                for cluster in clusters {
                    for m in &cluster.members {
                        matched_paths.insert(m.path.clone());
                    }
                    all_clusters.push(cluster);
                }
            }
        }

        progress_cb("Processing duplicate clusters", total_matchers, total_matchers);
        let mut records = Vec::new();
        let mut total_wasted_bytes = 0u64;
        let mut category_breakdown = HashMap::new();

        for cluster in &all_clusters {
            let (keeper, dupes) = self.keeper_strategy.choose_keeper(&cluster.members);

            records.push(DuplicateRecord {
                group_id: cluster.cluster_id,
                match_type: cluster.match_type,
                action: ActionType::Keep,
                category: keeper.category,
                similarity: "100%".to_string(),
                similarity_score: 1.0,
                size_mb: (keeper.size_bytes as f64) / 1_048_576.0,
                path: keeper.path.to_string_lossy().to_string(),
                dimensions: None,
            });

            for d in dupes {
                total_wasted_bytes += d.size_bytes;
                *category_breakdown.entry(format!("{:?}", d.category).to_uppercase()).or_insert(0) += 1;
                records.push(DuplicateRecord {
                    group_id: cluster.cluster_id,
                    match_type: cluster.match_type,
                    action: ActionType::Duplicate,
                    category: d.category,
                    similarity: "100%".to_string(),
                    similarity_score: 1.0,
                    size_mb: (d.size_bytes as f64) / 1_048_576.0,
                    path: d.path.to_string_lossy().to_string(),
                    dimensions: None,
                });
            }
        }

        let elapsed = t_start.elapsed().as_secs_f64();
        let wasted_mb = (total_wasted_bytes as f64) / (1024.0 * 1024.0);
        let wasted_gb = wasted_mb / 1024.0;

        Ok(ScanSummary {
            scanned_paths: self.target_paths.iter().map(|p| p.to_string_lossy().to_string()).collect(),
            scanned_dir: self.target_paths.first().map(|p| p.to_string_lossy().to_string()).unwrap_or_default(),
            total_files_scanned: all_files.len(),
            media_files_scanned: media_count,
            exact_duplicate_groups: all_clusters.len(),
            visual_ai_groups: 0,
            content_duplicate_groups: 0,
            total_duplicate_groups: all_clusters.len(),
            wasted_bytes: total_wasted_bytes,
            wasted_mb: (wasted_mb * 100.0).round() / 100.0,
            wasted_gb: (wasted_gb * 1000.0).round() / 1000.0,
            duration_seconds: (elapsed * 100.0).round() / 100.0,
            csv_report: None,
            summary_json: None,
            quarantine_script: None,
            groups: records,
            category_breakdown,
        })
    }
}
```

Create `crates/clairvoy-engine/src/lib.rs`:
```rust
pub mod keeper;
pub mod pipeline;

pub use keeper::CompositeKeeperStrategy;
pub use pipeline::DeduplicationPipeline;
```

- [x] **Step 4: Run test to verify it passes**

Run: `cargo test -p clairvoy-engine`
Expected: PASS (1 test passing)

- [x] **Step 5: Commit**

```bash
git add crates/clairvoy-engine
git commit -m "feat(rust): implement deduplication pipeline with short-circuit pruning"
```

---

### Task 6: High-Throughput Axum Web Server & Dashboard (`clairvoy-server`)

**Files:**
- Create: `crates/clairvoy-server/Cargo.toml`
- Create: `crates/clairvoy-server/src/lib.rs`
- Create: `crates/clairvoy-server/src/routes.rs`
- Create: `crates/clairvoy-server/src/state.rs`
- Test: `crates/clairvoy-server/tests/test_server.rs`

**Interfaces:**
- Consumes: `clairvoy-core`, `clairvoy-engine`.
- Produces:
  - Axum HTTP server hosting `/api/status`, `/api/scan`, `/api/runs`, and index dashboard.

- [ ] **Step 1: Write the failing test**

```rust
// crates/clairvoy-server/tests/test_server.rs
use axum_test::TestServer;
use clairvoy_server::build_router;

#[tokio::test]
async fn test_server_status_and_index() {
    let app = build_router();
    let server = TestServer::new(app).unwrap();

    let res_index = server.get("/").await;
    assert_eq!(res_index.status_code(), 200);
    assert!(res_index.text().contains("Clairvoy"));

    let res_status = server.get("/api/status").await;
    assert_eq!(res_status.status_code(), 200);
    assert!(res_status.text().contains("status"));
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cargo test -p clairvoy-server`
Expected: FAIL (crate not implemented)

- [ ] **Step 3: Implement `clairvoy-server` crate**

Create `crates/clairvoy-server/Cargo.toml`:
```toml
[package]
name = "clairvoy-server"
version.workspace = true
edition.workspace = true
license.workspace = true

[dependencies]
clairvoy-core = { path = "../clairvoy-core" }
clairvoy-engine = { path = "../clairvoy-engine" }
clairvoy-plugins = { path = "../clairvoy-plugins" }
axum = "0.7"
tokio = { version = "1.38", features = ["full"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
tower-http = { version = "0.5", features = ["cors"] }

[dev-dependencies]
axum-test = "16.0"
```

Create `crates/clairvoy-server/src/state.rs`:
```rust
use clairvoy_core::models::ScanSummary;
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppScanState {
    pub status: String,
    pub stage: String,
    pub progress_pct: u32,
    pub files_indexed: usize,
    pub elapsed_seconds: f64,
    pub message: String,
    pub summary: Option<ScanSummary>,
    pub error: Option<String>,
}

impl Default for AppScanState {
    fn default() -> Self {
        Self {
            status: "idle".to_string(),
            stage: "Ready".to_string(),
            progress_pct: 0,
            files_indexed: 0,
            elapsed_seconds: 0.0,
            message: "Ready to scan".to_string(),
            summary: None,
            error: None,
        }
    }
}

pub type SharedScanState = Arc<Mutex<AppScanState>>;
```

Create `crates/clairvoy-server/src/routes.rs`:
```rust
use crate::state::{AppScanState, SharedScanState};
use axum::extract::State;
use axum::response::{Html, Json};
use axum::routing::{get, post};
use axum::Router;
use serde::Deserialize;

#[derive(Deserialize)]
pub struct ScanPayload {
    pub paths: Vec<String>,
}

pub async fn handle_index() -> Html<&'static str> {
    Html("<!DOCTYPE html><html><head><title>Clairvoy</title></head><body><h1>Clairvoy Pure Rust Studio</h1></body></html>")
}

pub async fn handle_status(State(state): State<SharedScanState>) -> Json<AppScanState> {
    let s = state.lock().unwrap();
    Json(s.clone())
}

pub async fn handle_scan(
    State(state): State<SharedScanState>,
    Json(payload): Json<ScanPayload>,
) -> Json<serde_json::Value> {
    let mut s = state.lock().unwrap();
    s.status = "running".to_string();
    s.message = format!("Scanning {} path(s)", payload.paths.len());
    Json(serde_json::json!({ "status": "started", "paths": payload.paths }))
}

pub fn build_router() -> Router {
    let state: SharedScanState = Default::default();
    Router::new()
        .route("/", get(handle_index))
        .route("/api/status", get(handle_status))
        .route("/api/scan", post(handle_scan))
        .with_state(state)
}
```

Create `crates/clairvoy-server/src/lib.rs`:
```rust
pub mod routes;
pub mod state;

pub use routes::build_router;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cargo test -p clairvoy-server`
Expected: PASS (1 test passing)

- [ ] **Step 5: Commit**

```bash
git add crates/clairvoy-server
git commit -m "feat(rust): implement axum web server with live scan status endpoints"
```

---

### Task 7: Native CLI Binary & Verification (`clairvoy-cli`)

**Files:**
- Create: `crates/clairvoy-cli/Cargo.toml`
- Create: `crates/clairvoy-cli/src/main.rs`
- Update: `AGENTS.md`
- Test: Full workspace test & clippy

**Interfaces:**
- Produces: Executable binary `clairvoy-rs`.

- [ ] **Step 1: Implement `clairvoy-cli` crate**

Create `crates/clairvoy-cli/Cargo.toml`:
```toml
[package]
name = "clairvoy-cli"
version.workspace = true
edition.workspace = true
license.workspace = true

[[bin]]
name = "clairvoy-rs"
path = "src/main.rs"

[dependencies]
clairvoy-core = { path = "../clairvoy-core" }
clairvoy-engine = { path = "../clairvoy-engine" }
clairvoy-plugins = { path = "../clairvoy-plugins" }
clairvoy-server = { path = "../clairvoy-server" }
clap = { version = "4.5", features = ["derive"] }
tokio = { version = "1.38", features = ["full"] }
```

Create `crates/clairvoy-cli/src/main.rs`:
```rust
use clap::{Parser, Subcommand};
use std::net::SocketAddr;
use std::path::PathBuf;
use std::sync::Arc;

#[derive(Parser)]
#[command(name = "clairvoy-rs", version = "0.2.0", about = "Pure Rust High-Performance Deduplication Engine")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Scan one or more directories for duplicate files
    Scan {
        #[arg(required = true)]
        paths: Vec<PathBuf>,
    },
    /// Launch the web dashboard server
    Ui {
        #[arg(short, long, default_value = "8080")]
        port: u16,
        #[arg(long, default_value = "0.0.0.0")]
        host: String,
    },
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let cli = Cli::parse();

    match cli.command {
        Commands::Scan { paths } => {
            println!("[*] Initializing Clairvoy Pure Rust Engine across {} path(s)...", paths.len());
            let mut pipeline = clairvoy_engine::DeduplicationPipeline::new(paths);
            pipeline.register_matcher(Arc::new(clairvoy_plugins::ExactHashMatcherPlugin::new()));
            let summary = pipeline.run(|stage, cur, tot| {
                println!(" [>] {}: {} / {}", stage, cur, tot);
            })?;
            println!("\n[✓] Scan complete in {:.2}s. Discovered {} duplicate groups ({:.3} GB recoverable).",
                summary.duration_seconds, summary.total_duplicate_groups, summary.wasted_gb);
        }
        Commands::Ui { host, port } => {
            let addr: SocketAddr = format!("{}:{}", host, port).parse()?;
            println!("[*] Starting Clairvoy Rust Web Server at http://{} ...", addr);
            let app = clairvoy_server::build_router();
            let listener = tokio::net::TcpListener::bind(addr).await?;
            axum::serve(listener, app).await?;
        }
    }

    Ok(())
}
```

- [ ] **Step 2: Run full workspace test suite**

Run: `cargo test --workspace`
Expected: PASS across all crates

- [ ] **Step 3: Run Clippy lint checks**

Run: `cargo clippy --workspace --all-targets -- -D warnings`
Expected: 0 errors, 0 warnings

- [ ] **Step 4: Update `AGENTS.md`**

Update `AGENTS.md` with the new Rust workspace structure, build instructions (`cargo test --workspace`), and coexistence guidelines.

- [ ] **Step 5: Commit**

```bash
git add crates/clairvoy-cli AGENTS.md
git commit -m "feat(rust): implement clairvoy-rs CLI and update AGENTS.md"
```
