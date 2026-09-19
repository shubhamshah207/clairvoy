# Clairvoy Rust Plugin Developer Guide

Clairvoy is built around modular, trait-based extensibility in pure Rust. All deduplication matchers, keeper resolution strategies, and storage action handlers adhere to strongly-typed traits defined in [`clairvoy-core::traits`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-core/src/traits.rs).

---

## 1. Plugin Traits & Contracts

```
                       +----------------------+
                       | clairvoy_core::traits|
                       +----------+-----------+
                                  |
         +------------------------+------------------------+
         |                        |                        |
         v                        v                        v
+------------------+     +------------------+     +------------------+
|  MatcherPlugin   |     |  KeeperStrategy  |     |  ActionHandler   |
+------------------+     +------------------+     +------------------+
```

### Matcher Plugin ([`MatcherPlugin`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-core/src/traits.rs#L5-L27))
Implements candidate grouping and duplicate clustering:
```rust
pub trait MatcherPlugin: Send + Sync {
    fn plugin_id(&self) -> &str;
    fn display_name(&self) -> &str;
    fn priority_order(&self) -> u32;
    fn match_type(&self) -> MatchType;
    fn is_available(&self) -> (bool, String) {
        (true, "Ready".to_string())
    }
    fn filter_supported(&self, files: &[FileEntry]) -> Vec<FileEntry>;
    fn find_duplicates(
        &self,
        candidates: &[FileEntry],
        all_files: &[FileEntry],
    ) -> Result<Vec<DuplicateCluster>, EngineError>;
    fn find_duplicates_with_progress(
        &self,
        candidates: &[FileEntry],
        all_files: &[FileEntry],
        progress: &mut dyn FnMut(usize, usize),
    ) -> Result<Vec<DuplicateCluster>, EngineError>;
}
```

- **Execution Priority**: Lower numbers run first.
  - `10-19`: Exact byte/hash matchers ([`ExactHashMatcherPlugin`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-plugins/src/exact_hash.rs) with parallel Rayon BLAKE3).
  - `20-29`: Visual perceptual similarity matchers ([`PhotoVisionMatcherPlugin`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-plugins/src/photo_vision.rs) with pluggable model backends).

### Keeper Strategy ([`KeeperStrategy`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-core/src/traits.rs#L29-L32))
Evaluates files within a duplicate cluster and deterministically designates the primary preserved copy:
```rust
pub trait KeeperStrategy: Send + Sync {
    fn score_entry(&self, entry: &FileEntry, cluster: &[FileEntry]) -> i64;
    fn choose_keeper<'a>(&self, cluster: &'a [FileEntry]) -> (&'a FileEntry, Vec<&'a FileEntry>);
}
```

The default implementation [`CompositeKeeperStrategy`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-engine/src/pipeline.rs) awards bonuses for:
1. Higher resolution and file size.
2. Shorter, cleaner directory paths (folder seniority).
3. Penalties for duplicate naming tokens (`(1)`, `copy`, `_1`, `dupe`).
4. Oldest modification timestamp for tie-breaking.

### Action Handler ([`ActionHandler`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-core/src/traits.rs#L34-L42))
Executes post-deduplication storage optimization (e.g. moving to trash, hardlink replacement):
```rust
pub trait ActionHandler: Send + Sync {
    fn action_id(&self) -> &str;
    fn execute(
        &self,
        summary: &ScanSummary,
        base_dirs: &[&Path],
        dry_run: bool,
    ) -> Result<usize, EngineError>;
}
```

---

## 2. Implementing a Custom Matcher Plugin

To implement a new matcher in `crates/clairvoy-plugins`:

```rust
use clairvoy_core::{EngineError, FileEntry, MatchType, DuplicateCluster};
use clairvoy_core::traits::MatcherPlugin;

pub struct CustomDocumentMatcherPlugin {
    pub priority: u32,
}

impl MatcherPlugin for CustomDocumentMatcherPlugin {
    fn plugin_id(&self) -> &str {
        "custom_document_matcher"
    }

    fn display_name(&self) -> &str {
        "Custom Document Matcher"
    }

    fn priority_order(&self) -> u32 {
        self.priority
    }

    fn match_type(&self) -> MatchType {
        MatchType::ContentNearDuplicate
    }

    fn filter_supported(&self, files: &[FileEntry]) -> Vec<FileEntry> {
        files.iter()
            .filter(|f| f.size_bytes > 0 && f.path.ends_with(".txt"))
            .cloned()
            .collect()
    }

    fn find_duplicates(
        &self,
        candidates: &[FileEntry],
        _all_files: &[FileEntry],
    ) -> Result<Vec<DuplicateCluster>, EngineError> {
        // Group candidates into duplicate clusters
        Ok(Vec::new())
    }
}
```

Register your matcher in [`DeduplicationPipeline::builder()`](file:///home/shubhamshah207/clairvoy/crates/clairvoy-engine/src/pipeline.rs) to include it in deduplication runs.
