# Clairvoy Architecture & Deep Modules Blueprint

This document details the internal architecture, module boundaries, and data pipelines of Clairvoy.
Refer to this document for architectural patterns and deep module design.

---

## 1. System Architecture

Clairvoy follows the **Deep Module** philosophy (*A Philosophy of Software Design*): complex operations are encapsulated behind simple, cohesive, and type-safe public interfaces.

```
+---------------------------------------------------------------------------------------------------------+
|                                             CLAIRVOY ENGINE                                             |
+---------------------------------------------------------------------------------------------------------+
|                                                                                                         |
|   +-------------------+            +---------------------+              +-----------------+             |
|   |    CLI (Typer)    |            |    FastAPI (Web)    |              | Custom Plugins  |             |
|   |  clairvoy/cli.py  |            |   clairvoy/web/     |              | ~/.clairvoy/... |             |
|   +---------+---------+            +----------+----------+              +--------+--------+             |
|             |                                 |                                  |                      |
|             +---------------------------+     |     +----------------------------+                      |
|                                         v     v     v                                                   |
|                              +---------------------------+                                              |
|                              |       PluginRegistry      |                                              |
|                              | clairvoy/core/plugins.py  |                                              |
|                              +-------------+-------------+                                              |
|                                            |                                                            |
|                                            v                                                            |
|                              +---------------------------+                                              |
|                              |   DeduplicationPipeline   |                                              |
|                              | clairvoy/engines/pipeline |                                              |
|                              +-------------+-------------+                                              |
|                                            |                                                            |
|        +------------------+----------------+-----------------+------------------+                       |
|        |                  |                |                 |                  |                       |
|        v                  v                v                 v                  v                       |
| [Tier 1: Byte Exact][Tier 2: Visual AI] [Tier 3: Video]  [Tier 4: Archives] [Tier 5: Documents]         |
| ExactHashMatcher    PhotoVisionMatcher  VideoKeyframe... ArchiveInspector.. DocumentTextMatcher         |
| (QuickHash+SHA-256) (DINOv2: .heic,..)  (Frames: .mp4..) (In-Memory: .zip)  (.pdf, .docx, .csv)         |
|        |                  |                |                 |                  |                       |
|        +------------------+----------------+-----------------+------------------+                       |
|                                            |                                                            |
|                                            v                                                            |
|                              +---------------------------+                                              |
|                              |  CompositeKeeperStrategy  |                                              |
|                              |  (Scoring & Seniority)    |                                              |
|                              +-------------+-------------+                                              |
|                                            |                                                            |
|                                            v                                                            |
|                              +-------------+-------------+                                              |
|                              |                           |                                              |
|                              v                           v                                              |
|                 [Action: SafeQuarantine]          [Action: Hardlink]                                    |
|                 SafeQuarantineActionPlugin        HardlinkActionPlugin                                  |
+---------------------------------------------------------------------------------------------------------+
```

---

## 2. Deep Module Organization

The codebase is strictly structured into 4 cohesive packages with minimal cross-talk:

### `clairvoy.core` (Data Domain, Security, Contracts)
- [`models.py`](file:///home/shubhamshah207/clairvoy/clairvoy/core/models.py): Canonical Pydantic v2 schemas (`FileEntry`, `DuplicateRecord`, `DuplicateCluster`, `ScanSummary`, `ActionResult`).
- [`format_utils.py`](file:///home/shubhamshah207/clairvoy/clairvoy/core/format_utils.py): $O(1)$ stream header validators (`is_mpeg_ts`, `is_motion_photo_video`, `is_rar_archive`) discriminating media streams from ambiguous source files.
- [`plugins.py`](file:///home/shubhamshah207/clairvoy/clairvoy/core/plugins.py): Base plugin ABCs (`BasePlugin`, `BaseMatcherPlugin`, `BaseKeeperPlugin`, `BaseActionPlugin`) and thread-safe `PluginRegistry`.
- [`security.py`](file:///home/shubhamshah207/clairvoy/clairvoy/core/security.py): Enterprise filesystem defenses: path traversal verification, system root protection, sanitized shell command generation.
- [`config.py`](file:///home/shubhamshah207/clairvoy/clairvoy/core/config.py): Global configuration defaults and environment variable overrides.

### `clairvoy.engines` (Computation, Inference, Orchestration)
- [`pipeline.py`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/pipeline.py): `DeduplicationPipeline` coordinating chained matchers with short-circuit pruning, plus `CompositeKeeperStrategy`.
- [`storage_engine.py`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/storage_engine.py): Multi-threaded filesystem scanner, 128KB head/tail QuickHash, and SHA-256 digests.
- [`vision_engine.py`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/vision_engine.py): 100% offline Meta DINOv2 ONNX Runtime embedding inference, dual-path HEIC frame decoding, and Disjoint Set Union (DSU) graph clustering.
- [`classifier_engine.py`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/classifier_engine.py): Fast cosine distance classifier categorizing media into Photo, Screenshot, Meme, or Document.
- [`quarantine.py`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/quarantine.py): Manifest-backed non-destructive quarantine isolation engine with automated rollback generator.

### `clairvoy.plugins` (Bundled Default Extensions)
- [`exact_hash.py`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/exact_hash.py): Tier 1 byte-for-byte deduplication (Priority 10).
- [`photo_vision.py`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/photo_vision.py): Tier 2 visual similarity deduplication supporting `.jpg`, `.png`, `.webp`, `.heic`, and `.psd` (Priority 20).
- [`video_matcher.py`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/video_matcher.py): Tier 3 video keyframe hash deduplication supporting `.mp4`, `.mkv`, `.mov`, `.ts`, and `.mp` (Priority 30).
- [`archive_inspector.py`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/archive_inspector.py): Tier 4 in-memory ZIP/TAR/JAR/APK central directory inspector (Priority 40).
- [`document_matcher.py`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/document_matcher.py): Tier 5 content-aware document and tabular deduplication supporting `.pdf`, `.docx`, `.pptx`, `.odt`, `.csv`, and `.tsv` (Priority 50).
- [`quarantine_action.py`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/quarantine_action.py): Safe reversible quarantine action.
- [`hardlink_action.py`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/hardlink_action.py): Cross-filesystem safe hardlink replacement action.

### `clairvoy.cli` & `clairvoy.web` (Presentation & Interfaces)
- [`cli.py`](file:///home/shubhamshah207/clairvoy/clairvoy/cli.py): Typer CLI with `scan`, `review`, `quarantine`, `restore`, `plugins list`, and `plugins info`.
- [`web/app.py`](file:///home/shubhamshah207/clairvoy/clairvoy/web/app.py): FastAPI backend serving interactive UI for side-by-side visual diffs and manual reviews.

---

## 3. Chained Pipeline & Short-Circuit Pruning

To maximize speed and minimize compute, matchers run strictly in ascending computational cost order:

```
[Candidate Files]
       |
       v
+-------------------------------+
| Tier 1: ExactHashMatcher      | (Cost: Very Low - 128KB QuickHash + SHA-256)
+---------------+---------------+
                |
                +---> [Exact Duplicates Found]   ---> Removed from downstream pipeline
                |
                v
+-------------------------------+
| Tier 2: PhotoVisionMatcher    | (Cost: Medium - Local ONNX DINOv2)
+---------------+---------------+
                |
                +---> [Visual Duplicates Found]  ---> Removed from downstream pipeline
                |
                v
+-------------------------------+
| Tier 3: VideoKeyframeMatcher  | (Cost: High - PyAV keyframe extraction)
+---------------+---------------+
                |
                +---> [Video Duplicates Found]   ---> Removed from downstream pipeline
                |
                v
+-------------------------------+
| Tier 4: ArchiveInspector      | (Cost: Low/Medium - In-memory ZIP/TAR CRC32 parse)
+---------------+---------------+
                |
                +---> [Archive Duplicates Found] ---> Removed from downstream pipeline
                |
                v
+-------------------------------+
| Tier 5: DocumentTextMatcher   | (Cost: Low/Medium - Text extraction & token Jaccard)
+---------------+---------------+
                |
                v
       [Combined Clusters]
```

### Short-Circuit Pruning Guarantee
Once a file is identified as a member of a duplicate cluster in an earlier tier, it is **pruned from the candidate pool** for all subsequent tiers. This prevents expensive neural embedding inference, video frame decoding, or document text parsing on files that are already proven exact duplicates.

---

## 4. Supported Modalities & Formats Matrix

| Modality | Formats Handled | Engine / Plugin | Key Invariant / Discriminator |
|---|---|---|---|
| **Photos & Raster** | `.jpg`, `.png`, `.webp`, `.bmp`, `.tiff`, `.tif`, `.heic`, `.psd` | [`PhotoVisionMatcherPlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/photo_vision.py) & [`VisionEngine`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/vision_engine.py) | Native Pillow PSD composite; dual-path HEIC (Pillow / ffmpeg pipe). |
| **Video & Motion** | `.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`, `.flv`, `.wmv`, `.m4v`, `.ts`, `.mp` | [`VideoKeyframeMatcherPlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/video_matcher.py) | $O(1)$ sync byte `0x47` distinguishes MPEG-TS from TypeScript; `ftyp` box detects `.mp` Motion Photos. |
| **In-Memory Archives** | `.zip`, `.jar`, `.apk`, `.tar`, `.tar.gz`, `.tgz`, `.tar.bz2`, `.tbz2`, `.rar` | [`ArchiveInspectorMatcherPlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/archive_inspector.py) | In-memory central directory CRC32 inspection without disk extraction. |
| **Documents & Tabular** | `.pdf`, `.docx`, `.pptx`, `.odt`, `.csv`, `.tsv` | [`DocumentTextMatcherPlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/document_matcher.py) | In-memory `zipfile` XML inspection; pure-Python `pypdf` up to 50 pages; permutation-invariant tabular row sort; token Jaccard similarity $\ge 0.90$; 25MB buffer / 50k words cap. |
| **Stream Utils** | Binary magic-byte probes | [`format_utils.py`](file:///home/shubhamshah207/clairvoy/clairvoy/core/format_utils.py) | `is_mpeg_ts`, `is_motion_photo_video`, `is_rar_archive`. |

---

## 5. Tier 5: Document & Tabular Matcher (`DocumentTextMatcherPlugin`)

The [`DocumentTextMatcherPlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/document_matcher.py) operates at **Priority 50** with match type `MatchType.CONTENT_NEAR_DUPLICATE`. It detects identical and near-duplicate text across re-saved exports, converted office documents, draft revisions, and permuted datasets.

### Extraction Recipes by Format

1. **PDF Documents (`.pdf`)**:
   - Extracted using pure-Python [`pypdf.PdfReader`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/document_matcher.py#L171).
   - Inspects up to the first 50 pages (`MAX_PDF_PAGES = 50`) to avoid memory bottlenecks on large books or manuals.
   - Automatically attempts decryption with an empty password string `""` for softly protected PDFs.
   - Accumulates text up to a strict 25 MB byte ceiling (`MAX_BUFFER_BYTES`).

2. **Microsoft Word (`.docx`)**:
   - Treated as an in-memory ZIP package using standard library `zipfile.ZipFile`.
   - Directly parses `word/document.xml` using `xml.etree.ElementTree`.
   - Iterates over paragraph structures (`<w:p>`) and extracts text runs (`<w:t>`), reconstructing body paragraphs without requiring heavyweight external office runtimes.

3. **Microsoft PowerPoint (`.pptx`)**:
   - In-memory ZIP inspection of `ppt/slides/slide*.xml`.
   - Employs natural numerical sorting (`re.search(r"ppt/slides/slide(\d+)\.xml$")`) so slides are ordered as `slide1.xml`, `slide2.xml`, ..., `slide10.xml` rather than lexicographical order.
   - Extracts slide text runs (`<a:t>`) and aggregates them into slide-separated text blocks.

4. **OpenDocument Text (`.odt`)**:
   - In-memory ZIP inspection of `content.xml`.
   - Uses XML element tree text iteration (`root.itertext()`) to extract all narrative paragraphs and headings.

5. **Tabular Datasets (`.csv`, `.tsv`)**:
   - Delimiter detection via `csv.Sniffer` sampling the first 8 KB with fallback to extension defaults (`\t` for `.tsv`, `,` for `.csv`).
   - Normalizes whitespace across all cells and filters out blank lines.
   - Preserves header row at index 0, then **canonically sorts all data rows** (`sorted(data_rows, key=tuple)`).
   - Produces a **permutation-invariant canonical text digest**: datasets with identical records shuffled in different row orders produce identical content hashes.

### Deduplication & Clustering Pipeline

```
[Supported Candidate Files]
             |
             v
+----------------------------+
|  Text / Table Extraction   | ---> (Cap at 25MB buffer / 50k words)
+-------------+--------------+
             |
             v
+----------------------------+
|  Stage 1: Hash Matching    | ---> Identical normalized text hash -> Similarity 1.00
+-------------+--------------+
             |
             v
+----------------------------+
|  Stage 2: Jaccard Matching | ---> O(1) ratio pre-filtering: min_len / max_len >= 0.90
|                            | ---> Word token Jaccard similarity: |A ∩ B| / |A ∪ B| >= 0.90
+-------------+--------------+
             |
             v
+----------------------------+
|  Stage 3: DSU Clustering   | ---> Disjoint Set Union with path compression & rank union
+-------------+--------------+
             |
             v
 [Duplicate Clusters Emitted]
```

1. **Exact Normalized Hash Matching**: Computes SHA-256 over normalized body text. Files with identical normalized text receive similarity `1.00`.
2. **Near-Duplicate Token Jaccard Similarity**:
   - Documents with at least 5 tokens (`MIN_TOKENS_FOR_SIMILARITY = 5`) are compared via word-level Jaccard similarity: $\text{Sim}(A, B) = \frac{|A \cap B|}{|A \cup B|}$.
   - Pairs meeting the threshold $\text{Sim}(A, B) \ge 0.90$ are joined into duplicate clusters.
   - **$O(1)$ Length Ratio Pre-Filtering**: To avoid expensive set operations on mismatched files, pairs with $\frac{\min(|A|, |B|)}{\max(|A|, |B|)} < 0.90$ are pruned immediately before computing intersections.
3. **Disjoint Set Union (DSU) Clustering**:
   - Groups candidates into connected components using path compression and union-by-rank.
   - Emits structured [`DuplicateCluster`](file:///home/shubhamshah207/clairvoy/clairvoy/core/plugins.py) instances with member similarity scores, extension breakdowns, and content hashes.

### Memory Safety & Offline Invariants

- **100% Offline**: Pure Python execution relying solely on `pypdf` and standard libraries (`zipfile`, `csv`, `xml.etree.ElementTree`). Zero network calls or external cloud services.
- **Strict Memory Ceilings**:
  - Max buffer read: 25 MB (`MAX_BUFFER_BYTES = 25 * 1024 * 1024`).
  - Max words extracted: 50,000 words (`MAX_WORDS = 50_000`).
  - Max PDF pages: 50 pages (`MAX_PDF_PAGES = 50`).
- **Graceful Fault Tolerance**: Corrupted archives, binary files renamed with document extensions, unreadable streams, or encrypted PDFs without empty passwords safely return `None` and are logged at `DEBUG` level without crashing the pipeline.

---

## 6. Keeper Resolution & Scoring Engine

When duplicate clusters are identified, `CompositeKeeperStrategy` determines which file to keep (`ActionType.KEEP`) and which to flag as duplicates (`ActionType.DUPLICATE`).

### Scoring Criteria:
1. **Resolution & Media Dimensions**: Higher resolution receives higher score.
2. **File Size & Bitrate**: Higher information density receives bonus.
3. **Duplicate Token Penalties**: Filenames containing `copy`, `(1)`, `_1`, `dupe`, or trailing numeric suffixes receive severe penalties.
4. **Directory Seniority / Clean Path Bonus**: Shorter, cleaner directory paths receive preference over deeply nested temp folders.
5. **Modification Time Tie-Breaking**: When scores are identical, the oldest original file is preserved.
6. **Document Categorization**: Clusters tagged with `MatchType.CONTENT_NEAR_DUPLICATE` are classified as `ImageCategory.DOCUMENT` in duplicate records and scan summaries.

---

## 7. Persistent Run Management & History Architecture

Clairvoy automatically maintains scan run history and provides instant report hydration across CLI and Web environments via [`RunManager`](file:///home/shubhamshah207/clairvoy/clairvoy/core/run_manager.py).

```
+-----------------------------------------------------------------------------------------+
|                               RUN MANAGEMENT ARCHITECTURE                               |
+-----------------------------------------------------------------------------------------+
|                                                                                         |
|   Scan Completion (CLI / Web Engine)                                                    |
|          |                                                                              |
|          v                                                                              |
|   RunManager.register_run(summary)                                                      |
|          |                                                                              |
|          v                                                                              |
|   Persistent Storage (~/.clairvoy/runs.json) <---> Auto-Discovery (known directories)   |
|          |                                                                              |
|          +--------------------------------------+---------------------------------------+
|          |                                                              |
|          v                                                              v
|   CLI Interface (`clairvoy runs list / show`)              Web UI API (`/api/runs`, `/load`)
|   * Clean ASCII table listing past scan runs              * Top header "📂 Runs:" dropdown
|   * Deep inspection of run metrics                        * 1-click run switching without rescan
|   * Launch UI loaded to specific run (`--run`)            * Auto-hydrates latest run on load
+-----------------------------------------------------------------------------------------+
```

### Key Components:
- **`RunRecord` Schema**: Serializes `run_id`, ISO timestamp, `scanned_paths`, duplicate counts, recoverable space (MB/GB), category breakdown, and paths to `clairvoy_summary.json`, `clairvoy_duplicates.csv`, and `clairvoy_quarantine.sh`.
- **Auto-Discovery**: Automatically inspects well-known directories (`~/clairvoy_drive_e_reports`, `./_dedupe_reports`, `~/.clairvoy/reports`) to index preexisting scan runs without requiring manual re-scanning.
- **CLI Commands**:
  - `clairvoy runs list`: Formats past scan runs in an ASCII table.
  - `clairvoy runs show <RUN_ID>`: Displays detailed metrics, breakdown, and file paths.
  - `clairvoy ui --report <PATH>` / `clairvoy ui --run <RUN_ID>`: Pre-loads specific scan data into the web dashboard.
- **Web UI Hydration**:
  - `GET /api/runs`: Lists available runs ordered by newest first.
  - `POST /api/runs/load`: Dynamically swaps the active dashboard state and updates path traversal whitelists for media thumbnails.
  - Automatically loads the latest run on page load if the server was idle.
