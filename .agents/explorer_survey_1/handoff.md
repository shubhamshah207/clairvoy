# Architectural Survey & Plugin Interface Findings for Document Deduplication

## 1. Observation

### 1.1. Core Plugin Architecture & Contracts in [`clairvoy/core/plugins.py`](file:///home/shubhamshah207/clairvoy/clairvoy/core/plugins.py)

Direct observation of [`plugins.py`](file:///home/shubhamshah207/clairvoy/clairvoy/core/plugins.py):
- **Base Plugin Hierarchy**:
  - [`BasePlugin(ABC)`](file:///home/shubhamshah207/clairvoy/clairvoy/core/plugins.py#L52):
    ```python
    class BasePlugin(ABC):
        plugin_id: str = ""
        display_name: str = ""
        version: str = "0.1.0"
        author: str = "Clairvoy"
        description: str = ""
        enabled_by_default: bool = True

        @abstractmethod
        def is_available(self) -> tuple[bool, str]: ...
        def initialize(self, context: dict[str, Any]) -> None: pass
        def shutdown(self) -> None: pass
    ```
  - [`BaseMatcherPlugin(BasePlugin)`](file:///home/shubhamshah207/clairvoy/clairvoy/core/plugins.py#L84):
    ```python
    class BaseMatcherPlugin(BasePlugin):
        match_type: MatchType = MatchType.EXACT_HASH
        priority_order: int = 100

        @abstractmethod
        def filter_supported(self, files: list[FileEntry]) -> list[FileEntry]: ...

        @abstractmethod
        def find_duplicates(
            self,
            candidates: list[FileEntry],
            all_indexed_files: list[FileEntry],
            context: dict[str, Any],
        ) -> list[DuplicateCluster]: ...
    ```
  - [`BaseKeeperPlugin(BasePlugin)`](file:///home/shubhamshah207/clairvoy/clairvoy/core/plugins.py#L106): `score_entry(entry: FileEntry, cluster: list[FileEntry]) -> int`.
  - [`BaseActionPlugin(BasePlugin)`](file:///home/shubhamshah207/clairvoy/clairvoy/core/plugins.py#L115): `action_id: str = ""`, `execute(plan: list[Any], base_dirs: list[Path], dry_run: bool = False) -> ActionResult`.
- **Core Data Structures**:
  - [`DuplicateCluster`](file:///home/shubhamshah207/clairvoy/clairvoy/core/plugins.py#L31):
    ```python
    class DuplicateCluster(BaseModel):
        cluster_id: int
        match_type: MatchType
        members: list[FileEntry]
        similarity_scores: list[float] = Field(default_factory=list)
        metadata: dict[str, Any] = Field(default_factory=dict)
    ```
  - [`FileEntry`](file:///home/shubhamshah207/clairvoy/clairvoy/core/models.py#L30):
    ```python
    class FileEntry(BaseModel):
        path: str
        size_bytes: int
        is_media: bool = False
        quick_hash: str | None = None
        full_sha256: str | None = None
        keeper_score: int = 100
        category: ImageCategory = ImageCategory.FILE
    ```
  - [`MatchType`](file:///home/shubhamshah207/clairvoy/clairvoy/core/models.py#L11):
    ```python
    class MatchType(str, Enum):
        EXACT_HASH = "EXACT_HASH"
        VISUAL_AI_NEAR_DUPLICATE = "VISUAL_AI_NEAR_DUPLICATE"
        CONTENT_NEAR_DUPLICATE = "CONTENT_NEAR_DUPLICATE"
    ```
    *Note*: `MatchType.CONTENT_NEAR_DUPLICATE` is already defined in [`models.py`](file:///home/shubhamshah207/clairvoy/clairvoy/core/models.py#L14) and verified in [`tests/test_plugin_system.py`](file:///home/shubhamshah207/clairvoy/tests/test_plugin_system.py#L171).
  - Note regarding `MatchResult`: `plugins.py` defines `DuplicateCluster` (cluster of duplicate files) and `ActionResult` (action execution metrics). Matchers return `list[DuplicateCluster]`.
- **PluginRegistry Mechanics**:
  - Process-wide singleton accessed via `PluginRegistry.get_instance()` and `PluginRegistry.reset_instance()`.
  - Dynamic registration via `registry.register(plugin: BasePlugin)`.
  - Matcher priority ordering: `registry.get_matchers(enabled_only=True, available_only=False)` sorts matchers by `priority_order` ascending (`sorted(matchers, key=lambda p: p.priority_order)`). Lower integer priority orders run first in the pipeline.
  - Discovery hooks:
    1. Directory loading: `load_plugins_from_directory(dir_path)` dynamically imports `*.py` from `~/.clairvoy/plugins/` using `importlib.util.spec_from_file_location`.
    2. Entry point loading: `load_entry_points(group="clairvoy.plugins")` queries Python package entry points via `importlib.metadata.entry_points`.

---

### 1.2. Existing Matcher Plugins Survey

| Plugin Class | File Path | Priority | MatchType | Handled Formats | Clustering / Matching Mechanism | Error Handling |
|---|---|---|---|---|---|---|
| [`ExactHashMatcherPlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/exact_hash.py#L20) | [`exact_hash.py`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/exact_hash.py) | 10 | `EXACT_HASH` | All non-empty files (`size_bytes > 0`) | 3-stage pruning: (1) `size_bytes`, (2) 128KB header QuickHash, (3) 64KB streaming SHA-256. | Catches `(OSError, PermissionError)` in hashing, returns `None` and skips. |
| [`PhotoVisionMatcherPlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/photo_vision.py#L33) | [`photo_vision.py`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/photo_vision.py) | 20 | `VISUAL_AI_NEAR_DUPLICATE` | `.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`, `.tiff`, `.tif`, `.heic`, `.psd` | Meta DINOv2 ONNX Runtime 384-d normalized embeddings; cosine similarity threshold (default 0.92); DSU connected components. | `is_available()` returns `False` if `HAS_ML` is False. Truncated image loading enabled. |
| [`VideoKeyframeMatcherPlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/video_matcher.py#L41) | [`video_matcher.py`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/video_matcher.py) | 30 | `VISUAL_AI_NEAR_DUPLICATE` | `.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`, `.flv`, `.wmv`, `.m4v`, `.ts`, `.mp` | Stream duration tolerance ($\pm 1.5\%$ / $\pm 1.0s$), sampled keyframe extraction at 10%, 50%, 90% via ffmpeg/cv2 pipe, 64-bit dHash Hamming distance, DSU clustering. | Checks `shutil.which("ffprobe")`, `ffmpeg`, or `cv2`. Timeouts (15s) and subprocess error trapping. Ambiguity filtering (`is_mpeg_ts`, `is_motion_photo_video`). |
| [`ArchiveInspectorMatcherPlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/archive_inspector.py#L35) | [`archive_inspector.py`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/archive_inspector.py) | 40 | `EXACT_HASH` | `.zip`, `.jar`, `.apk`, `.tar`, `.tar.gz`, `.tgz`, `.tar.bz2`, `.tbz2`, `.rar` | Central directory in-memory inspection without disk extraction. Matches archive member size against candidates on disk, then compares `zlib.crc32`. | Catches `(zipfile.BadZipFile, tarfile.TarError, OSError, PermissionError, EOFError)`, logs debug warnings, skips corrupt archives. |

---

### 1.3. Pipeline Orchestration & Short-Circuit Pruning in [`clairvoy/engines/pipeline.py`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/pipeline.py)

- **Default Registry Population** ([`pipeline.py:152-158`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/pipeline.py#L152)):
  ```python
  if len(self.registry.get_matchers(enabled_only=False)) == 0:
      self.registry.register(ExactHashMatcherPlugin())
      self.registry.register(PhotoVisionMatcherPlugin())
      self.registry.register(VideoKeyframeMatcherPlugin())
      self.registry.register(ArchiveInspectorMatcherPlugin())
  ```
- **CLI Discovery** ([`clairvoy/cli.py:57-65`](file:///home/shubhamshah207/clairvoy/clairvoy/cli.py#L57)):
  ```python
  default_plugins: list[BasePlugin] = [
      ExactHashMatcherPlugin(),
      ArchiveInspectorMatcherPlugin(),
      PhotoVisionMatcherPlugin(),
      VideoKeyframeMatcherPlugin(),
      CompositeKeeperStrategy(),
      SafeQuarantineActionPlugin(),
      HardlinkActionPlugin(),
  ]
  ```
- **Short-Circuit Pruning Invariant** ([`pipeline.py:321-337`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/pipeline.py#L321)):
  ```python
  candidates = [f for f in all_files if f.path not in matched_paths]
  supported = matcher.filter_supported(candidates)
  ...
  clusters = matcher.find_duplicates(supported, all_files, context=context)
  for cluster in clusters:
      matched_paths.update(m.path for m in cluster.members)
      all_clusters.append(cluster)
      next_cluster_id += 1
  ```
  *Significance*: Matchers run strictly in ascending `priority_order` (10 $\rightarrow$ 20 $\rightarrow$ 30 $\rightarrow$ 40 $\rightarrow$ 50). Any document files that are bit-for-bit identical are clustered first by `ExactHashMatcherPlugin` (priority 10) and pruned from `candidates`. `DocumentTextMatcherPlugin` (priority 50) only receives non-identical candidates to inspect for content/text/tabular near-duplication.

---

### 1.4. Format Probes in [`clairvoy/core/format_utils.py`](file:///home/shubhamshah207/clairvoy/clairvoy/core/format_utils.py)

Direct observation of format utilities:
- `is_mpeg_ts(path: str) -> bool`: Checks 188-byte packet sync byte `0x47` at offset 0 and 188.
- `is_motion_photo_video(path: str) -> bool`: Checks `b"ftyp"` ISO box header for Google Pixel motion photos.
- `is_rar_archive(path: str) -> bool`: Checks `b"Rar!\x1a\x07"`.

---

### 1.5. Existing Test Suite Status & Sample Files

- Running baseline pytest (excluding `test_document_matcher.py`):
  `/home/shubhamshah207/miniconda3/bin/pytest --ignore=tests/test_document_matcher.py -v` $\rightarrow$ **131 passed, 2 warnings in 3.51s**.
- Running pytest on [`tests/test_document_matcher.py`](file:///home/shubhamshah207/clairvoy/tests/test_document_matcher.py):
  Fails with `ModuleNotFoundError: No module named 'clairvoy.plugins.document_matcher'` because the plugin file has not been created yet.
- Verifying sample PDF:
  `/mnt/e/ApartmentRelated/2022/Renter'sInsurance.pdf` exists (74,015 bytes).
  Executing `pypdf.PdfReader` on this file extracts 3 pages; page 1 contains `"Quote Number 74366603 Renter's Insurance Quote for September 12, 2022"`.
- Ruff linter check:
  `/home/shubhamshah207/miniconda3/bin/ruff check .` reports 1 fixable error:
  `I001 [*] Import block is un-sorted or un-formatted --> tests/test_document_matcher.py:3:1`.

---

## 2. Logic Chain

```
+----------------------------------------------------------------------------------------------------+
|                                    MATCHING PIPELINE PRIORITY TIERS                                |
+----------------------------------------------------------------------------------------------------+
| Tier 1: ExactHashMatcherPlugin (Priority 10)                                                      |
|         -> Discovers exact byte duplicates (QuickHash + SHA-256)                                   |
|         -> Prunes matched paths from candidates                                                    |
|                                     |                                                              |
|                                     v                                                              |
| Tier 2: PhotoVisionMatcherPlugin (Priority 20)                                                     |
|         -> Discovers visual duplicates (.jpg, .png, .webp, .heic, .psd)                            |
|         -> Prunes matched paths from candidates                                                    |
|                                     |                                                              |
|                                     v                                                              |
| Tier 3: VideoKeyframeMatcherPlugin (Priority 30)                                                   |
|         -> Discovers video duplicates (.mp4, .mkv, .mov, .ts, .mp)                                 |
|         -> Prunes matched paths from candidates                                                    |
|                                     |                                                              |
|                                     v                                                              |
| Tier 4: ArchiveInspectorMatcherPlugin (Priority 40)                                                |
|         -> Discovers uncompressed candidate matches inside archives (.zip, .tar, .apk)             |
|         -> Prunes matched paths from candidates                                                    |
|                                     |                                                              |
|                                     v                                                              |
| Tier 5: DocumentTextMatcherPlugin (Priority 50) [TARGET]                                           |
|         -> Extracts text & tabular structures (.pdf, .docx, .pptx, .odt, .csv, .tsv)               |
|         -> Matches identical normalized content (1.0) & token Jaccard similarity (>= 0.90)         |
|         -> MatchType.CONTENT_NEAR_DUPLICATE                                                        |
+----------------------------------------------------------------------------------------------------+
```

1. **Subclassing Contract**:
   From Observation 1.1, `DocumentTextMatcherPlugin` must inherit from [`BaseMatcherPlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/core/plugins.py#L84), define `plugin_id = "document_matcher"`, `match_type = MatchType.CONTENT_NEAR_DUPLICATE`, `priority_order = 50`, and implement `is_available()`, `filter_supported()`, and `find_duplicates()`.
2. **Contract Requirements from Existing Tests**:
   From Observation 1.5, [`tests/test_document_matcher.py`](file:///home/shubhamshah207/clairvoy/tests/test_document_matcher.py) expects:
   - Module: `clairvoy.plugins.document_matcher`
   - Constant: `SUPPORTED_DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".pptx", ".odt", ".csv", ".tsv"}`
   - Method: `extract_document_representation(path: str) -> tuple[str, str, int] | None` returning `(content_hash, preview, length)`.
   - `is_available() -> tuple[bool, str]` returning `(True, reason)` where `"available" in reason.lower()`.
3. **Extraction Implementations**:
   - **`.pdf`**: Use `pypdf.PdfReader`. Read up to 50 pages. Join text, cap at 25 MB / 50,000 words.
   - **`.docx`**: Open via standard library `zipfile.ZipFile(path, "r")`. Read `word/document.xml`. Parse with `xml.etree.ElementTree`. Extract text from `<w:t>` elements or `root.itertext()`.
   - **`.pptx`**: Open via `zipfile.ZipFile(path, "r")`. Read `ppt/slides/slide*.xml`. Extract text from `<a:t>` elements or `root.itertext()`.
   - **`.odt`**: Open via `zipfile.ZipFile(path, "r")`. Read `content.xml`. Extract text using `root.itertext()`.
   - **`.csv` / `.tsv`**: Use `csv.reader`. Parse header and rows. Normalize whitespace per cell. Filter empty rows. Sort rows lexicographically to achieve permutation-invariant content digests.
4. **Clustering & Graph Resolution**:
   - Group files with exact matching `content_hash` $\rightarrow$ `similarity_score = 1.0`.
   - Compute token sets `set(re.findall(r"\b\w+\b", norm_text))`. Compute pairwise Jaccard similarity `len(a & b) / len(a | b)`. If `sim >= 0.90`, union members using [`DisjointSetUnion`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/vision_engine.py#L35).
   - Construct [`DuplicateCluster`](file:///home/shubhamshah207/clairvoy/clairvoy/core/plugins.py#L31) with `match_type = MatchType.CONTENT_NEAR_DUPLICATE`.
5. **Registration & Integration**:
   - Register in [`clairvoy/engines/pipeline.py`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/pipeline.py#L158) under default matchers.
   - Register in [`clairvoy/cli.py`](file:///home/shubhamshah207/clairvoy/clairvoy/cli.py#L62) under `default_plugins`.
   - Add `pypdf>=5.0.0` to `dependencies` in [`pyproject.toml`](file:///home/shubhamshah207/clairvoy/pyproject.toml#L24).
   - Fix import sorting in [`tests/test_document_matcher.py`](file:///home/shubhamshah207/clairvoy/tests/test_document_matcher.py#L1) using `ruff check --fix .`.

---

## 3. Caveats

1. **OCR / Scanned Images inside PDFs**:
   `pypdf.PdfReader` extracts embedded text streams. Scanned raster-only PDFs (containing only page images without an OCR text layer) will yield empty text strings. In accordance with R1 and R3, offline execution without cloud APIs or heavy Tesseract OCR dependencies is required, so scanned raster PDFs should safely produce empty/None representation and gracefully bypass text matching.
2. **Column Permutation vs Row Permutation**:
   R1 specifies "parsing headers, sorting rows, and generating permutation-invariant content digests". Row sorting makes the digest invariant to row reordering. If column ordering also varies in future exports, column sorting based on normalized header names can be optionally applied; however, sorting rows preserves column semantics when headers match.
3. **Password-Protected / Encrypted Documents**:
   Encountering password-protected PDFs or encrypted Office files must be caught gracefully (`pypdf.errors.FileNotDecryptedError`, `zipfile.BadZipFile`, etc.) returning `None` and logging at `debug` level to avoid aborting concurrent batch processing.

---

## 4. Conclusion

All prerequisites for implementing [`DocumentTextMatcherPlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/document_matcher.py) are clearly defined and aligned across the codebase:
1. `MatchType.CONTENT_NEAR_DUPLICATE` is already defined in [`clairvoy/core/models.py`](file:///home/shubhamshah207/clairvoy/clairvoy/core/models.py).
2. Priority order `50` slots cleanly after `archive_inspector` (40) and respects short-circuit pruning.
3. The pure-Python extraction approach (`pypdf`, `zipfile`, `xml.etree.ElementTree`, `csv`) requires zero external system dependencies and runs 100% offline.
4. Existing test specification in [`tests/test_document_matcher.py`](file:///home/shubhamshah207/clairvoy/tests/test_document_matcher.py) provides a direct verification contract.

---

## 5. Verification Method

### 5.1. Verification Commands
To verify the implementation once coded:
1. Run document matcher unit tests:
   ```bash
   /home/shubhamshah207/miniconda3/bin/pytest tests/test_document_matcher.py -v
   ```
2. Run full test suite:
   ```bash
   /home/shubhamshah207/miniconda3/bin/pytest -v
   ```
3. Run static linter:
   ```bash
   /home/shubhamshah207/miniconda3/bin/ruff check .
   ```
4. Verify CLI discovery table:
   ```bash
   /home/shubhamshah207/miniconda3/bin/clairvoy plugins list
   /home/shubhamshah207/miniconda3/bin/clairvoy plugins info document_matcher
   ```

### 5.2. Files to Inspect
- [`clairvoy/plugins/document_matcher.py`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/document_matcher.py) (new plugin implementation)
- [`clairvoy/engines/pipeline.py`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/pipeline.py) (registry population)
- [`clairvoy/cli.py`](file:///home/shubhamshah207/clairvoy/clairvoy/cli.py) (`discover_plugins()`)
- [`pyproject.toml`](file:///home/shubhamshah207/clairvoy/pyproject.toml) (`pypdf>=5.0.0` dependency)
- [`AGENTS.md`](file:///home/shubhamshah207/clairvoy/AGENTS.md), [`docs/ARCHITECTURE.md`](file:///home/shubhamshah207/clairvoy/docs/ARCHITECTURE.md), [`docs/PLUGINS.md`](file:///home/shubhamshah207/clairvoy/docs/PLUGINS.md) (documentation updates)

### 5.3. Invalidation Conditions
- If `pypdf` is missing from the environment, `is_available()` returns `False` and tests fail.
- If memory bounds (25 MB / 50,000 words / 50 pages) are exceeded or omitted, large files could exhaust memory.
- If corrupted files throw unhandled exceptions instead of returning `None`, batch scans will abort.
