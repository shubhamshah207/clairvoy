# RUST_GUIDELINES.md — High-Performance Rust Coding Standards & Design Patterns for Clairvoy

This document establishes the definitive coding standards, design patterns, memory invariants, and architectural idioms for **Clairvoy**'s pure Rust deduplication engine (`clairvoy-rs`).
All developers and AI agents writing Rust code in this repository **MUST** adhere to these guidelines without exception.

---

## 1. High-Performance Design Patterns for Storage Deduplication

### 1.1. Multi-Tier Short-Circuit Pipeline Pattern
Deduplication is inherently an $O(N^2)$ candidate-matching problem. To achieve sub-second execution over millions of files, the engine employs a progressive filtering pipeline where each tier prunes the candidate space before more expensive tiers run:

```
+---------------------------------------------------------------------------------------------------------+
|                                    MULTI-TIER FILTERING PIPELINE                                        |
+---------------------------------------------------------------------------------------------------------+
|                                                                                                         |
|   All Files (N Entries)                                                                                 |
|            |                                                                                            |
|            v                                                                                            |
|   +---------------------------------------+                                                             |
|   | Tier 0: File Size Grouping            | --> Discard unique sizes (90%+ files eliminated)            |
|   +-------------------+-------------------+                                                             |
|                       |                                                                                 |
|                       v Candidate Bins (>1 file per size)                                               |
|   +---------------------------------------+                                                             |
|   | Tier 1: SIMD QuickHash (4KB XXH3)     | --> Fast preliminary bucket hashing (>10 GB/s/core)         |
|   +-------------------+-------------------+                                                             |
|                       |                                                                                 |
|                       v Matching QuickHash Bins                                                         |
|   +---------------------------------------+                                                             |
|   | Tier 2: BLAKE3 Cryptographic Full Hash| --> 100% Byte-Exact duplicate clusters                      |
|   +-------------------+-------------------+                                                             |
|                       | (Remaining un-matched media candidates)                                         |
|                       v                                                                                 |
|   +---------------------------------------+                                                             |
|   | Tier 3: Coarse Perceptual Hash (dHash)| --> Fast visual similarity pre-filter                       |
|   +-------------------+-------------------+                                                             |
|                       |                                                                                 |
|                       v Candidate Visual Pairs                                                          |
|   +---------------------------------------+                                                             |
|   | Tier 4: Neural Embeddings (ONNX/DINO) | --> High-precision cosine clustering                        |
|   +---------------------------------------+                                                             |
+---------------------------------------------------------------------------------------------------------+
```

**Rule:** Never run expensive decoding or neural embeddings on pairs that have not passed candidate binning and coarse pre-filtering.

---

### 1.2. Bounded Channel Backpressure Pattern
To enforce the **$\le 50\text{ MB}$ resident memory invariant** across filesystems with millions of files:
- Use `flume::bounded(2048)` channels between the filesystem walker and processing stages.
- The crawler thread yields when the consumer buffer is saturated, preventing unbounded heap inflation.

```rust
// CORRECT: Bounded backpressure prevents unbounded memory consumption
let (tx, rx) = flume::bounded::<FileEntry>(2048);

// WRONGLY: Unbounded channels will exhaust RAM on 1M+ file scans
// let (tx, rx) = flume::unbounded();
```

---

### 1.3. Zero-Copy & Memory-Mapped File I/O
Large files (videos, archive bundles, RAW photos) must not be read into heap buffers via `std::fs::read`.

```rust
// Pattern: Smart file hashing with mmap fallback
pub fn hash_file_efficiently(path: &Path, size_bytes: u64) -> Result<blake3::Hash, EngineError> {
    const MMAP_THRESHOLD: u64 = 16 * 1024 * 1024; // 16 MB

    if size_bytes >= MMAP_THRESHOLD {
        let file = std::fs::File::open(path)?;
        // SAFETY: The mmap is read-only and scoped to the hasher
        let mmap = unsafe { memmap2::MmapOptions::new().map(&file)? };
        let mut hasher = blake3::Hasher::new();
        hasher.update_rayon(&mmap);
        Ok(hasher.finalize())
    } else {
        let mut file = std::fs::File::open(path)?;
        let mut hasher = blake3::Hasher::new();
        let mut buffer = [0u8; 64 * 1024]; // 64KB stack buffer
        loop {
            let n = file.read(&mut buffer)?;
            if n == 0 { break; }
            hasher.update(&buffer[..n]);
        }
        Ok(hasher.finalize())
    }
}
```

---

### 1.4. Decoupled Concurrency: Rayon (CPU) vs. Tokio (Async I/O)
Clairvoy uses two distinct execution engines:
1. **Rayon**: Dedicated thread pool sized to physical CPU cores for compute-heavy hashing, image decoding, and tensor inference.
2. **Tokio**: Multi-threaded async runtime for Axum HTTP requests, Server-Sent Events (SSE) telemetry, and WebSocket streaming.

**The Golden Concurrency Rule:**
**Never perform blocking CPU operations directly inside Tokio async tasks.** Always offload compute to Rayon via `tokio::task::spawn_blocking` or bridge channels.

```rust
// CORRECT: Offload heavy pipeline compute to blocking threadpool
app.get("/api/scan/start", |State(state)| async move {
    tokio::task::spawn_blocking(move || {
        state.engine.run_scan()
    }).await??;
    Ok(StatusCode::OK)
});

// WRONG: Blocks Tokio worker thread, causing HTTP request starvation
// app.get("/api/scan/start", |State(state)| async move {
//     state.engine.run_scan(); // DEADLOCK / STARVATION RISK
// });
```

---

### 1.5. Dynamic Provider & Trait Pattern (Plug-and-Play AI)
AI models evolve rapidly. Clairvoy decouples the deduplication engine from hardcoded model weights using dynamic trait dispatch:

```rust
pub trait ModelBackend: Send + Sync {
    fn model_id(&self) -> &str;
    fn embedding_dim(&self) -> usize;
    fn input_dimensions(&self) -> (u32, u32);
    fn preprocess(&self, img: &image::DynamicImage) -> Result<ndarray::Array4<f32>, EngineError>;
    fn embed_batch(&self, tensors: ndarray::ArrayView4<f32>) -> Result<Vec<Vec<f32>>, EngineError>;
}
```

Models are configured dynamically via `~/.clairvoy/models.toml` without rebuilding the Rust binary.

---

## 2. Memory Layout & Cache Locality

### 2.1. Compact Representation (`FileEntry`)
The `FileEntry` struct is created millions of times during large scans. Its memory layout must be cache-line friendly:

```rust
#[repr(C)]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct FileEntry {
    pub path: std::path::PathBuf,      // 24 bytes
    pub size_bytes: u64,               // 8 bytes
    pub modified_epoch: u64,           // 8 bytes
    pub quick_hash: u64,               // 8 bytes (XXH3-64)
    pub is_media: bool,                // 1 byte
    pub category: ImageCategory,       // 1 byte
    // 6 bytes padding to 56 bytes (fits within a 64-byte L1 cache line)
}
```

---

## 3. Error Handling Standards

### 3.1. Domain Error Hierarchy with `thiserror`
Clairvoy libraries must **NEVER** use `anyhow` for internal domain logic. Use typed enums with `thiserror`:

```rust
use thiserror::Error;

#[derive(Debug, Error)]
pub enum EngineError {
    #[error("I/O error at '{path}': {source}")]
    Io {
        path: std::path::PathBuf,
        #[source]
        source: std::io::Error,
    },

    #[error("Security violation: Path traversal outside base '{base}': '{target}'")]
    PathTraversal {
        base: std::path::PathBuf,
        target: std::path::PathBuf,
    },

    #[error("Model inference failure [{model_id}]: {reason}")]
    ModelInference {
        model_id: String,
        reason: String,
    },

    #[error("Invalid configuration: {0}")]
    Config(String),
}

pub type EngineResult<T> = Result<T, EngineError>;
```

### 3.2. Panic Prevention Policy
- `.unwrap()` and `.expect()` are **strictly forbidden** in production library code (`clairvoy-core`, `clairvoy-scanner`, `clairvoy-engine`, `clairvoy-server`).
- All errors must be handled via `Result<T, EngineError>` with contextual propagation (`?`).
- Unhandled panics will cause process termination; Clairvoy engines must run 24/7 as reliable daemons.

---

## 4. Security & Path Traversal Guards

### 4.1. Strict Base Canonicalization
All file operations (reading, hashing, thumbnailing, deleting, quarantining) must verify that paths resolve inside the authorized root:

```rust
pub fn sanitize_path(base_dir: &Path, requested_path: &Path) -> Result<PathBuf, EngineError> {
    let canonical_base = dunce::canonicalize(base_dir).map_err(|e| EngineError::Io {
        path: base_dir.to_path_buf(),
        source: e,
    })?;
    
    let canonical_target = dunce::canonicalize(requested_path).map_err(|e| EngineError::Io {
        path: requested_path.to_path_buf(),
        source: e,
    })?;

    if !canonical_target.starts_with(&canonical_base) {
        return Err(EngineError::PathTraversal {
            base: canonical_base,
            target: canonical_target,
        });
    }

    Ok(canonical_target)
}
```

---

## 5. Polyglot Interoperability with Python

The Rust engine and existing Python codebase must be 100% interoperable through shared JSON manifest schemas:

1. **Manifest File**: `clairvoy_summary.json`
2. **Schema Invariant**:
   - Field naming: `snake_case` using `#[serde(rename_all = "snake_case")]`.
   - Float precision: GB values rounded to 4 decimal places.
   - Cluster IDs: sequential integers matching Python's indexing format.
3. Both engines can ingest manifests generated by the other without schema mismatches.

---

## 6. Code Style & Quality Checklist

Every pull request or agent commit must pass:
1. `cargo fmt --all -- --check`
2. `cargo clippy --workspace --all-targets -- -D warnings`
3. `cargo test --workspace` with 100% passing tests
4. Memory verification: scan test verifying resident memory $< 50\text{ MB}$.
