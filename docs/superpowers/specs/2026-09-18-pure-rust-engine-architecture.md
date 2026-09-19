# Pure Rust Engine & Plug-and-Play Architecture Specification

**Status:** Approved  
**Date:** 2026-09-18  
**Author:** Antigravity Team  
**Scope:** Core Engine, Pluggable Model Runtime, Parallel Scanner, Axum Web Server, CLI  

---

## 1. Executive Summary & Vision

Clairvoy is transitioning its core storage deduplication and multimodal clustering engine to **Pure Rust** while maintaining full polyglot coexistence with the existing Python codebase during the migration. 

### Core Objectives
1. **Unrivaled Resource Efficiency**: Reduce peak memory consumption by 12x–20x (from ~650 MB to <50 MB for 50,000+ files) and cold startup time to <15ms.
2. **Fearless 16-Core Parallelism**: Eliminate the Python Global Interpreter Lock (GIL) and saturate all available hardware threads (e.g. 16 threads on Intel Core i7-12700H) using Rayon work-stealing and async Tokio I/O.
3. **Plug-and-Play Model & Plugin Architecture**: Decouple the deduplication pipeline from specific AI models. As modern vision models evolve (Meta DINOv2 $\rightarrow$ OpenAI CLIP $\rightarrow$ Google SigLIP $\rightarrow$ Apple FastViT), users can swap weights and configs dynamically via `models.toml` without recompilation.
4. **Standalone Native Distribution**: Package the engine and Google Material Design 3 dashboard into a single static, self-contained binary (`clairvoy-rs`) with zero host dependencies (no Conda, Python, or external package managers required).
5. **Polyglot Coexistence**: Maintain both Python and Rust side-by-side. Both systems produce and consume identical `clairvoy_summary.json` run manifests.

---

## 2. High-Level Architecture Overview

```
+---------------------------------------------------------------------------------------------------------+
|                                    CLAIRVOY RUST ENGINE ARCHITECTURE                                    |
+---------------------------------------------------------------------------------------------------------+
|                                                                                                         |
|   +-------------------+            +---------------------+              +-----------------+             |
|   |  CLI (`clap`)     |            |  Web Server (`axum`)|              | Custom Plugins  |             |
|   |  clairvoy-cli     |            |  clairvoy-server    |              | Wasm / Dynamic  |             |
|   +---------+---------+            +----------+----------+              +--------+--------+             |
|             |                                 |                                  |                      |
|             +---------------------------+     |     +----------------------------+                      |
|                                         v     v     v                                                   |
|                              +---------------------------+                                              |
|                              |       PluginRegistry      |                                              |
|                              | (Dynamic & Static Traits) |                                              |
|                              +-------------+-------------+                                              |
|                                            |                                                            |
|                                            v                                                            |
|                              +---------------------------+                                              |
|                              |   DeduplicationPipeline   |                                              |
|                              | clairvoy-engine (Channel) |                                              |
|                              +-------------+-------------+                                              |
|                                            |                                                            |
|        +------------------+----------------+-----------------+------------------+                       |
|        |                  |                |                 |                  |                       |
|        v                  v                v                 v                  v                       |
| [Tier 1: Byte Exact][Tier 2: Visual AI] [Tier 3: Video]  [Tier 4: Archives] [Tier 5: Documents]         |
| ExactHashMatcher    PhotoVisionMatcher  VideoKeyframe... ArchiveInspector.. DocumentTextMatcher         |
| (XXH3 + BLAKE3 SIMD)(Swappable Backend) (Frames + AI)    (In-Memory Zip/Tar)(PDF, XML, CSV)             |
|        |                  |                |                 |                  |                       |
|        +------------------+----------------+-----------------+------------------+                       |
|                                   |                                                                     |
|                                   v                                                                     |
|                      +---------------------------+                                                      |
|                      |    Trait: ModelBackend    |                                                      |
|                      |  Swappable AI Embeddings  |                                                      |
|                      +-------------+-------------+                                                      |
|                                    |                                                                    |
|             +----------------------+----------------------+                                             |
|             v                                             v                                             |
|   [OnnxRuntimeBackend (`ort`)]                  [PerceptualHashBackend]                                 |
|   DINOv2, CLIP, SigLIP via models.toml          dHash, pHash zero-weight fallback                       |
|                                                                                                         |
|                                            |                                                            |
|                                            v                                                            |
|                              +---------------------------+                                              |
|                              |  CompositeKeeperStrategy  |                                              |
|                              |  (Seniority & Resolution) |                                              |
|                              +-------------+-------------+                                              |
|                                            |                                                            |
|                                            v                                                            |
|                              +---------------------------+                                              |
|                              |      Action Handlers      |                                              |
|                              | SafeQuarantine | Hardlink |                                              |
|                              | TrashEngine    | PermDel  |                                              |
|                              +---------------------------+                                              |
+---------------------------------------------------------------------------------------------------------+
```

---

## 3. Cargo Workspace & Crate Topology

The Rust implementation is decomposed into focused, single-responsibility crates within a Cargo workspace:

```
clairvoy/
├── Cargo.toml                  # Workspace definition
├── crates/
│   ├── clairvoy-core/          # Domain models, error enums, core traits
│   ├── clairvoy-scanner/       # Parallel filesystem indexer, xxhash3 pre-filter, flume channels
│   ├── clairvoy-model/         # Pluggable model runtime (ort ONNX, Candle, perceptual)
│   ├── clairvoy-plugins/       # Built-in matchers (Exact, Vision, Video, Archive, Document)
│   ├── clairvoy-engine/        # Pipeline coordinator, keeper scoring, action dispatchers
│   ├── clairvoy-server/        # Axum async HTTP server, SSE progress telemetry, static UI
│   └── clairvoy-cli/           # Command-line interface binary (`clairvoy-rs`)
├── clairvoy/                   # Existing Python package (preserved for coexistence)
└── pyproject.toml              # Existing Python build configuration
```

### Crate Responsibilities

| Crate | Primary Crates / Dependencies | Responsibility |
|---|---|---|
| **`clairvoy-core`** | `serde`, `serde_json`, `thiserror` | Data structures (`FileEntry`, `DuplicateCluster`, `ScanSummary`), constants, and public traits (`MatcherPlugin`, `ModelBackend`, `KeeperStrategy`, `ActionHandler`). |
| **`clairvoy-scanner`** | `jwalk`, `flume`, `xxhash-rust` | Multi-threaded directory traversal; size-indexed candidate grouping; 4KB SIMD pre-filter hashing; bounded queue backpressure. |
| **`clairvoy-model`** | `ort`, `image`, `ndarray`, `image_hasher` | Swappable AI model engine; dynamic ONNX model loader; batch tensor pre-processing; cosine similarity clustering. |
| **`clairvoy-plugins`** | `blake3`, `zip`, `tar`, `pdf-extract`, `quick-xml` | The 5 standard matcher tiers; short-circuit candidate pruning; archive central-directory inspection. |
| **`clairvoy-engine`** | `rayon`, `crossbeam` | Pipeline orchestration; keeper seniority scoring; safe quarantine and deletion engines. |
| **`clairvoy-server`** | `axum`, `tokio`, `tower-http`, `mime_guess` | Web dashboard server; real-time scan progress endpoint; thumbnail generator with LRU cache; video streaming. |
| **`clairvoy-cli`** | `clap` | Native CLI binary with `scan`, `ui`, `runs`, and `plugins` subcommands. |

---

## 4. Plug-and-Play Model & Plugin Architecture

### 4.1. Swappable AI Model Engine (`ModelBackend`)

```rust
pub trait ModelBackend: Send + Sync {
    /// Unique identifier for this model (e.g. "dinov2_vits14", "clip_vit_b32").
    fn model_id(&self) -> &str;

    /// Expected embedding dimension (e.g. 384, 512, 768).
    fn embedding_dim(&self) -> usize;

    /// Input resolution requirements: (width, height).
    fn input_dimensions(&self) -> (u32, u32);

    /// Pre-processes an image directly into a normalized float tensor.
    fn preprocess(&self, img: &image::DynamicImage) -> Result<ndarray::Array4<f32>, EngineError>;

    /// Executes batched inference across input tensors.
    fn embed_batch(&self, tensors: ndarray::ArrayView4<f32>) -> Result<Vec<Vec<f32>>, EngineError>;
}
```

### 4.2. Configuration-Driven Model Registry (`models.toml`)

Users can drop new ONNX models into `~/.clairvoy/models/` and register them via `~/.clairvoy/models.toml`:

```toml
[active_model]
default = "dinov2_vits14"

[models.dinov2_vits14]
backend = "onnx"
model_path = "~/.clairvoy/models/dinov2_vits14.onnx"
embedding_dim = 384
input_size = [224, 224]
normalization = { mean = [0.485, 0.456, 0.406], std = [0.229, 0.224, 0.225] }

[models.clip_vit_b32]
backend = "onnx"
model_path = "~/.clairvoy/models/clip_vit_b32.onnx"
embedding_dim = 512
input_size = [224, 224]
normalization = { mean = [0.48145466, 0.4578275, 0.40821073], std = [0.26862954, 0.26130258, 0.27577711] }

[models.siglip2_patch16]
backend = "onnx"
model_path = "~/.clairvoy/models/siglip2_patch16_384.onnx"
embedding_dim = 768
input_size = [384, 384]
normalization = { mean = [0.5, 0.5, 0.5], std = [0.5, 0.5, 0.5] }
```

### 4.3. Swappable Matcher Tiers (`MatcherPlugin`)

```rust
pub trait MatcherPlugin: Send + Sync {
    fn plugin_id(&self) -> &str;
    fn display_name(&self) -> &str;
    fn priority_order(&self) -> u32;
    fn match_type(&self) -> MatchType;
    
    /// Checks if plugin dependencies are satisfied.
    fn is_available(&self) -> (bool, String);

    /// Fast pre-filter determining if a file entry is supported by this plugin.
    fn filter_supported(&self, files: &[FileEntry]) -> Vec<FileEntry>;

    /// Discovers duplicate clusters among supported candidate files.
    fn find_duplicates(
        &self,
        candidates: &[FileEntry],
        all_files: &[FileEntry],
        ctx: &ScanContext,
    ) -> Result<Vec<DuplicateCluster>, EngineError>;
}
```

---

## 5. Resource Footprint & Performance Invariants

```
+-----------------------------------------------------------------------------------------------------------------+
| RESOURCE / METRIC             | PYTHON BASELINE                | RUST TARGET SPEC               | ENFORCEMENT   |
+-----------------------------------------------------------------------------------------------------------------+
| Idle Memory                   | ~150 MB                        | < 20 MB                        | Zero GC heap  |
| Peak RAM (50,000 files)       | ~620 MB                        | < 50 MB                        | Bounded queue |
| Scan Traversal Speed          | ~15,000 files/sec              | > 200,000 files/sec            | `jwalk` SIMD  |
| Quick Hashing Bandwidth       | ~480 MB/sec (SHA-256)          | > 10 GB/sec per core (XXH3)    | AVX2/AVX-512  |
| Full Hash Bandwidth           | ~480 MB/sec (SHA-256)          | > 5.5 GB/sec per core (BLAKE3) | SIMD tree hash|
| Startup Time                  | ~1,500 ms                      | < 12 ms                        | Native binary |
| Binary Size (Stripped)        | ~1.2 GB (Miniconda environment)| ~25 MB - 35 MB (Standalone)    | Link-time opt |
+-----------------------------------------------------------------------------------------------------------------+
```

### Memory Safety & Bounded Queue Invariant
To prevent memory exhaustion during scans of millions of files:
- Scanner writes discovered file entries into a `flume::bounded(2048)` channel.
- If matchers or hashers cannot consume entries as fast as the filesystem scanner discovers them, the scanner thread blocks until the channel has capacity.
- Maximum resident memory allocated to in-flight file buffers is strictly capped at $\le 2048 \times 24\text{ bytes} \approx 49\text{ KB}$.

---

## 6. Coexistence Strategy

During the migration and verification period:

1. **Both Systems Functional**:
   - Python: `/home/shubhamshah207/miniconda3/bin/clairvoy ui` (runs FastAPI server on port 8000).
   - Rust: `cargo run --release -p clairvoy-cli -- ui --port 8080` (runs Axum server on port 8080).
2. **Universal Manifest Interoperability**:
   - Both engines read and write identical `clairvoy_summary.json` schemas.
   - A scan completed in Rust can be viewed in the Python UI, and vice versa.
3. **Audit & Rollback**:
   - All destructive or altering actions (quarantine, trash, permanent deletion) generate identical JSON audit manifests compatible with both Python and Rust restore endpoints.

---

## 7. Verification & Quality Standards

- **Unit & Integration Tests**: `cargo test --workspace` must pass with 100% success.
- **Static Linter**: `cargo clippy --workspace --all-targets -- -D warnings` with 0 warnings.
- **Formatting**: `cargo fmt --all -- --check` adhering to Rust 2024 edition conventions.
- **Documentation**: All public traits and functions must have docstrings (`///`). `AGENTS.md` must be maintained continuously.
