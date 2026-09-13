# Clairvoy Pluggable Deduplication Engine Architecture Spec

- **Author**: Staff Software Engineer
- **Date**: 2026-09-13
- **Status**: Draft (Under Review)
- **Target Version**: 0.2.0

---

## 1. Executive Summary & Objective

Clairvoy is transitioning from a monolithic deduplication pipeline into a modular, extensible, plugin-driven deduplication engine. The architecture adheres to proven enterprise and Gang-of-Four (GoF) design patterns to ensure:

1. **High Cohesion & Low Coupling**: Each file modality (exact hashes, visual photos, videos, archives, audio) is encapsulated in an isolated plugin.
2. **Extensibility**: Users and developers can introduce custom matchers, keeper rules, or resolution actions by placing a `.py` file into `~/.clairvoy/plugins/` or installing a Python package with zero modification to core code.
3. **Graceful Degradation**: Plugins declare runtime dependency checks (`is_available()`). Missing optional dependencies (such as `ffmpeg`) emit user-friendly advisory diagnostics without crashing the broader scan.
4. **Sub-millisecond Performance & Thread-Safety**: Pipeline execution leverages vectorized batch processing and thread-safe registries with bounded memory profiles.

---

## 2. Design Patterns Applied

```
+------------------------------+-------------------------------------------------------------------------+
| Design Pattern               | Architectural Application in Clairvoy                                   |
+------------------------------+-------------------------------------------------------------------------+
| Pipeline / Chain of Resp.    | Files pass through tiered Matcher Plugins (cheap hashes -> heavy AI)     |
| Strategy Pattern             | Interchangeable Keeper Strategies (EXIF, resolution) & Action Strategies|
| Registry & Service Locator   | Centralized PluginRegistry for dynamic discovery and lifecycle tracking |
| Template Method              | BaseMatcherPlugin enforces lifecycle, error isolation, & metrics        |
| Observer Pattern             | Event emitter decoupling scan progress from CLI and Web UI renderers    |
+------------------------------+-------------------------------------------------------------------------+
```

### 2.1. Pipeline / Chain of Responsibility Pattern (Matching Engine)
Deduplication is inherently hierarchical. Running an expensive neural transformer on files that could have been eliminated via a 128KB QuickHash is an anti-pattern. Matcher plugins form a typed execution chain where each stage consumes unmatched candidates from the previous stage:

```
                          [ All Discovered Files ]
                                     |
                                     v
                 +---------------------------------------+
                 | Stage 1: ExactHashMatcher             |
                 | (Size -> QuickHash -> SHA-256)        |
                 +---------------------------------------+
                        /                         \
           [Exact Duplicates Found]        [Unmatched Files]
                      |                            |
                      v                            v
             {Exact Cluster Set}       +---------------------------------------+
                                       | Stage 2: PhotoVisionMatcher (DINOv2)  |
                                       +---------------------------------------+
                                              /                         \
                                 [Look-Alikes Found]             [Unmatched Files]
                                            |                            |
                                            v                            v
                                   {Photo Cluster Set}      +---------------------------------------+
                                                            | Stage 3: VideoKeyframeMatcher         |
                                                            +---------------------------------------+
                                                                   /                         \
                                                      [Transcodes Found]              [Unmatched Files]
                                                                 |                            |
                                                                 v                            v
                                                        {Video Cluster Set}      +---------------------------------------+
                                                                                 | Stage 4: ArchiveInspectorMatcher      |
                                                                                 +---------------------------------------+
```

### 2.2. Strategy Pattern (Keeper Ranking & Action Execution)
- **`KeeperStrategy`**: Decouples the decision of which duplicate to retain. Implementations include:
  - `MetadataIntegrityKeeperStrategy`: Prefers files with authentic camera EXIF tags over stripped files.
  - `QualityKeeperStrategy`: Prefers higher pixel counts, higher video bitrates, and lossless formats.
  - `DirectorySeniorityKeeperStrategy`: Penalizes temporary directories (`/Downloads/`, `/trash/`).
  - `CompositeKeeperStrategy`: Evaluates weighted scores across all active keeper strategies.
- **`ActionStrategy`**: Decouples how duplicate records are resolved:
  - `QuarantineAction`: Non-destructive move with auto-collision naming and rollback manifest.
  - `HardlinkAction`: Replaces duplicate files with NTFS/Linux hardlinks, achieving 100% space recovery without modifying application directory trees.

### 2.3. Registry & Dynamic Service Locator Pattern
The `PluginRegistry` maintains an active catalog of plugins discovered via:
1. **Built-in Plugins**: Core matchers and actions distributed with the package.
2. **Drop-in Directory**: `~/.clairvoy/plugins/*.py` dynamically loaded via `importlib.util.spec_from_file_location`.
3. **Setuptools Entry-Points**: Third-party packages registered under `clairvoy.plugins`.

---

## 3. Class Hierarchy & Interface Contracts

```
                                  +-------------------+
                                  |    BasePlugin     |
                                  +-------------------+
                                  | plugin_id: str    |
                                  | name: str         |
                                  | is_available()    |
                                  +-------------------+
                                    /       |       \
                                   /        |        \
                                  v         v         v
                 +-------------------+  +-------------------+  +-------------------+
                 | BaseMatcherPlugin |  | BaseKeeperPlugin  |  | BaseActionPlugin  |
                 +-------------------+  +-------------------+  +-------------------+
                 | match_type        |  | score_entry()     |  | action_id         |
                 | find_duplicates() |  +-------------------+  | execute()         |
                 +-------------------+                         +-------------------+
```

### 3.1. `BasePlugin` Specification
```python
class BasePlugin(ABC):
    plugin_id: str
    display_name: str
    version: str
    author: str
    description: str
    enabled_by_default: bool = True

    @abstractmethod
    def is_available(self) -> tuple[bool, str]:
        """
        Validates hardware and system dependencies (e.g. ffmpeg, ONNX runtime).
        Returns (True, "Ready") or (False, "Missing dependency: <details>").
        """
        ...

    def initialize(self, context: dict[str, Any]) -> None:
        """Lifecycle hook invoked before scan commences."""
        pass

    def shutdown(self) -> None:
        """Lifecycle hook invoked on completion to release file handles and memory."""
        pass
```

### 3.2. `BaseMatcherPlugin` Specification
```python
class BaseMatcherPlugin(BasePlugin):
    match_type: MatchType
    priority_order: int = 100  # Lower runs earlier in the pipeline chain

    @abstractmethod
    def filter_supported(self, files: list[FileEntry]) -> list[FileEntry]:
        """Returns subset of files that this plugin can evaluate (e.g. media extension filter)."""
        ...

    @abstractmethod
    def find_duplicates(
        self,
        candidates: list[FileEntry],
        all_indexed_files: list[FileEntry],
        context: PipelineContext,
    ) -> list[DuplicateGroup]:
        """Executes similarity clustering and returns discovered duplicate groups."""
        ...
```

### 3.3. `BaseKeeperPlugin` Specification
```python
class BaseKeeperPlugin(BasePlugin):
    @abstractmethod
    def score_entry(self, entry: FileEntry, cluster: list[FileEntry]) -> int:
        """Returns an integer score (higher wins)."""
        ...
```

### 3.4. `BaseActionPlugin` Specification
```python
class BaseActionPlugin(BasePlugin):
    action_id: str

    @abstractmethod
    def execute(
        self,
        plan: list[DuplicateRecord],
        base_dirs: list[Path],
        dry_run: bool = False,
    ) -> ActionResult:
        """Executes file modification or relocation with complete rollback logging."""
        ...
```

---

## 4. Default Core Plugin Suite

The system bundles 6 production-grade default plugins:

1. **`ExactHashMatcherPlugin`** (`exact_hash`):
   - Level 1: Size grouping.
   - Level 2: 128KB parallel QuickHash.
   - Level 3: 1MB block buffered SHA-256.
2. **`PhotoVisionMatcherPlugin`** (`photo_vision`):
   - Uses quantized Meta DINOv2 ONNX.
   - Vectorized 2048-chunk dot products with Disjoint Set Union clustering.
3. **`VideoKeyframeMatcherPlugin`** (`video_matcher`):
   - Validates container stream duration (tolerance: ±1.5%).
   - Extracts 3 keyframes (10%, 50%, 90%) using OpenCV or fallback lightweight header parser.
   - Detects resolution transcodes (e.g. 4K original vs. 720p WhatsApp share).
4. **`ArchiveInspectorMatcherPlugin`** (`archive_inspector`):
   - Peeks inside `.zip` and `.tar` central directories without extracting to disk.
   - Matches extracted files on disk against identical files trapped inside archives.
5. **`SafeQuarantineActionPlugin`** (`quarantine`):
   - Reversible move with automatic non-clobbering destination renaming (`_1`, `_2`).
   - Generates machine-readable `quarantine_manifest.json` for 1-click restore.
6. **`HardlinkActionPlugin`** (`hardlink`):
   - Native NTFS (Windows) and POSIX (Linux) hardlink replacement.
   - Replaces redundant duplicates with pointers to the keeper inode, recovering 100% of wasted bytes while preserving all file paths.

---

## 5. Security & Isolation Considerations

1. **Sandboxed Plugin Loading**:
   - Disallowed plugin paths: `~/.clairvoy/plugins/` must not allow symlink breakouts into system directories.
   - Loaded plugins are checked for required protocol interfaces before activation.
2. **Safe Action Boundaries**:
   - `HardlinkActionPlugin` verifies cross-device boundary constraints (hardlinks cannot cross filesystem partitions). If across partitions, gracefully falls back to copy-or-quarantine.
3. **Non-destructive Invariants**:
   - No plugin may permanently delete a file without an explicit `--force-delete` CLI override. Default resolution is strictly reversible quarantine or hardlinking.

---

## 6. Verification & Testing Strategy

1. **Unit Test Suite**:
   - Test plugin registration and auto-discovery from temporary directories.
   - Test graceful degradation when a plugin reports `is_available() -> False`.
   - Test pipeline chain execution order: exact matches filtered before visual matchers.
2. **Integration Test Suite**:
   - Multi-format test dataset containing identical hashes, look-alike photos, video transcodes, and zip archives.
   - Verify hardlink inode unification on NTFS / ext4.
   - Verify quarantine rollback restores identical state.
