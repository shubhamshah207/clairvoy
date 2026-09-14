# Clairvoy Plugin Developer Guide

Clairvoy is designed from the ground up as a pluggable, extensible deduplication platform. This guide covers how to develop, test, and register custom plugins.

---

## 1. Plugin Types & Contracts

All plugins derive from [`BasePlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/core/plugins.py):

```
                       +-------------------+
                       |    BasePlugin     |
                       +---------+---------+
                                 |
         +-----------------------+-----------------------+
         |                       |                       |
         v                       v                       v
+-------------------+   +-------------------+   +-------------------+
| BaseMatcherPlugin |   | BaseKeeperPlugin  |   | BaseActionPlugin  |
+-------------------+   +-------------------+   +-------------------+
```

### Matcher Plugin ([`BaseMatcherPlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/core/plugins.py#L42))
Implements candidate grouping and duplicate clustering.
- `plugin_id: str` (unique identifier)
- `display_name: str`
- `priority_order: int` (Determines execution order; lower runs first)
  - `10-19`: Exact byte/hash matchers ([`exact_hash`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/exact_hash.py): QuickHash + SHA-256)
  - `20-29`: Visual / neural embedding matchers ([`photo_vision`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/photo_vision.py): Meta DINOv2 ONNX for `.jpg`, `.png`, `.webp`, `.heic`, `.psd`)
  - `30-39`: Audio / video temporal matchers ([`video_matcher`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/video_matcher.py): duration + keyframes for `.mp4`, `.mkv`, `.mov`, `.ts`, `.mp`)
  - `40-49`: Container / archive inspectors ([`archive_inspector`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/archive_inspector.py): in-memory CRC32 for `.zip`, `.jar`, `.apk`, `.tar`, `.rar`)
  - `50-59`: Content-aware document & tabular matchers ([`document_matcher`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/document_matcher.py): text extraction, row sorting, token Jaccard for `.pdf`, `.docx`, `.pptx`, `.odt`, `.csv`, `.tsv`)
- `filter_supported(candidates: list[FileEntry]) -> list[FileEntry]`
- `find_duplicates(candidates, all_indexed_files, context) -> list[DuplicateCluster]`

### Keeper Strategy Plugin ([`BaseKeeperPlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/core/plugins.py#L82))
Scores files within a duplicate cluster to select which one to preserve.
- `score_entry(entry: FileEntry, cluster: DuplicateCluster) -> float`

### Action Plugin ([`BaseActionPlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/core/plugins.py#L104))
Executes resolution against duplicate records.
- `execute(records: list[DuplicateRecord], base_dirs: list[Path]) -> ActionResult`

---

## 2. Built-in Matcher Plugins

Clairvoy includes 5 default matcher plugins operating in tiered succession:

| Plugin ID | Class | Priority | Match Type | Target Formats | Core Mechanism |
|---|---|---|---|---|---|
| `exact_hash` | [`ExactHashMatcherPlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/exact_hash.py) | 10 | `EXACT_HASH` | All files | 128KB head/tail QuickHash pre-filter + full SHA-256 |
| `photo_vision` | [`PhotoVisionMatcherPlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/photo_vision.py) | 20 | `VISUAL_AI_NEAR_DUPLICATE` | `.jpg`, `.png`, `.webp`, `.heic`, `.psd` | Offline Meta DINOv2 ONNX embeddings & cosine distance |
| `video_matcher` | [`VideoKeyframeMatcherPlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/video_matcher.py) | 30 | `VIDEO_TEMPORAL_DUPLICATE` | `.mp4`, `.mkv`, `.mov`, `.ts`, `.mp` | Stream duration matching + PyAV keyframe difference hashing |
| `archive_inspector` | [`ArchiveInspectorMatcherPlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/archive_inspector.py) | 40 | `ARCHIVE_CONTENT_DUPLICATE` | `.zip`, `.jar`, `.apk`, `.tar`, `.rar` | In-memory central directory CRC32 inspection without extraction |
| `document_matcher` | [`DocumentTextMatcherPlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/document_matcher.py) | 50 | `CONTENT_NEAR_DUPLICATE` | `.pdf`, `.docx`, `.pptx`, `.odt`, `.csv`, `.tsv` | Pure-Python XML/PDF text extraction, canonical row sort, token Jaccard |

---

## 3. Tier 5: DocumentTextMatcherPlugin Specification

The [`DocumentTextMatcherPlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/document_matcher.py) is a content-aware matcher designed to discover exact and near-duplicate text across document formats and tabular data sheets.

### Plugin Metadata
- **`plugin_id`**: `"document_matcher"`
- **`display_name`**: `"Document Text & Tabular Matcher"`
- **`version`**: `"0.1.0"`
- **`author`**: `"Clairvoy Team"`
- **`priority_order`**: `50`
- **`match_type`**: `MatchType.CONTENT_NEAR_DUPLICATE`
- **`description`**: `"Discovers identical and near-duplicate documents across .pdf, .docx, .pptx, .odt, .csv, and .tsv"`

### Public Methods & API Contract

#### 1. `is_available() -> tuple[bool, str]`
Checks runtime availability of PDF extraction dependencies.
- Returns `(True, f"pypdf {PYPDF_VERSION} available")` when `pypdf>=5.0.0` is importable.
- Returns `(False, "pypdf not installed. Please install pypdf>=5.0.0")` if `pypdf` is missing.
- Note: Office XML (`.docx`, `.pptx`, `.odt`) and tabular (`.csv`, `.tsv`) extraction use standard library `zipfile`, `xml.etree.ElementTree`, and `csv`, and remain available regardless.

#### 2. `filter_supported(files: list[FileEntry]) -> list[FileEntry]`
Filters candidate files eligible for document and tabular deduplication:
- Excludes empty files (`entry.size_bytes == 0`).
- Validates lowercase file extension against `SUPPORTED_DOCUMENT_EXTENSIONS`:
  `{".pdf", ".docx", ".pptx", ".odt", ".csv", ".tsv"}`.

#### 3. `extract_document_representation(path: str) -> tuple[str, str, int] | None`
Generates a canonical content representation for a single document file.
- Returns a 3-tuple `(content_hash, preview, length)`:
  - `content_hash`: Hex-encoded SHA-256 digest of normalized body text.
  - `preview`: First 500 characters of normalized text.
  - `length`: Total character count of normalized text.
- Returns `None` if extraction fails, the document contains no text, or the file is corrupted.

#### 4. `find_duplicates(candidates: list[FileEntry], all_indexed_files: list[FileEntry], context: dict[str, Any] | None = None) -> list[DuplicateCluster]`
Clusters candidate files into duplicate and near-duplicate groups:
1. **Extraction**: Iterates over supported candidates, extracting normalized text, content hashes, and lowercase word token sets.
2. **Stage 1 (Exact Matches)**: Partitions files with identical SHA-256 content hashes into duplicate sets with similarity `1.00`.
3. **Stage 2 (Near-Duplicate Token Jaccard)**: For candidates with at least 5 tokens (`MIN_TOKENS_FOR_SIMILARITY = 5`), computes token Jaccard similarity:
   $$\text{Sim}(A, B) = \frac{|A \cap B|}{|A \cup B|}$$
   Pairs with similarity $\ge 0.90$ are joined. Files failing the $O(1)$ length ratio check ($\frac{\min(|A|, |B|)}{\max(|A|, |B|)} \ge 0.90$) are pruned prior to set calculation.
4. **Stage 3 (DSU Cluster Assembly)**: Assembles disjoint sets into [`DuplicateCluster`](file:///home/shubhamshah207/clairvoy/clairvoy/core/plugins.py) instances with member similarity scores, extension breakdowns, and content hashes.

### Tabular Permutation Invariance
Tabular data files (`.csv`, `.tsv`) receive specialized normalization:
- Cell whitespace is stripped and empty lines are removed.
- Header row (row 0) is preserved at the top.
- Data rows (rows 1..N) are **canonically sorted** (`sorted(data_rows, key=tuple)`).
- Result: Datasets containing identical records in permuted row orders produce the exact same content hash and cluster with 100% confidence.

### Memory & Offline Constraints
- **Stream/Buffer Cap**: Capped at 25 MB per file (`MAX_BUFFER_BYTES = 25 * 1024 * 1024`).
- **Word Cap**: Extracted text truncated to 50,000 words (`MAX_WORDS = 50_000`).
- **PDF Page Cap**: Restricted to first 50 pages (`MAX_PDF_PAGES = 50`).
- **Fault Tolerance**: Malformed XML, encrypted PDFs, or unreadable streams return `None` and log a `DEBUG` message without halting scans.

---

## 4. Creating a Custom Matcher

Here is an example of a custom filename-stem matcher plugin:

```python
# ~/.clairvoy/plugins/stem_matcher.py
from pathlib import Path
from clairvoy.core.models import FileEntry, MatchType
from clairvoy.core.plugins import BaseMatcherPlugin, DuplicateCluster


class StemMatcherPlugin(BaseMatcherPlugin):
    plugin_id = "stem_matcher"
    display_name = "Filename Stem Matcher"
    match_type = MatchType.SIMILAR_VISUAL
    priority_order = 45

    def is_available(self) -> tuple[bool, str]:
        return True, "Ready"

    def filter_supported(self, files: list[FileEntry]) -> list[FileEntry]:
        return files

    def find_duplicates(
        self,
        candidates: list[FileEntry],
        all_indexed_files: list[FileEntry],
        context: dict,
    ) -> list[DuplicateCluster]:
        from collections import defaultdict
        grouped = defaultdict(list)
        for f in candidates:
            stem = Path(f.path).stem.lower().strip()
            grouped[stem].append(f)

        clusters = []
        for stem, members in grouped.items():
            if len(members) > 1:
                clusters.append(
                    DuplicateCluster(
                        match_type=self.match_type,
                        members=members,
                        confidence=0.85,
                        plugin_id=self.plugin_id,
                        metadata={"stem": stem},
                    )
                )
        return clusters
```

---

## 5. Dynamic Discovery & Loading

Clairvoy discovers and loads plugins from three distinct sources:

1. **Built-in Bundled Plugins**: Loaded automatically from [`clairvoy.plugins`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/).
2. **User Plugin Directory**: Python files placed in `~/.clairvoy/plugins/` (or passed via `--plugin-dir`) are discovered dynamically via `importlib`.
3. **Setuptools Entry Points**: Third-party packages registered under the entry point group `clairvoy.plugins`:
   ```toml
   [project.entry-points."clairvoy.plugins"]
   custom_matcher = "my_package.plugins:MyCustomMatcher"
   ```

---

## 6. CLI Inspection & Toggling

### List All Plugins
```bash
clairvoy plugins list
```

### Inspect Plugin Metadata
```bash
clairvoy plugins info document_matcher
```
Output:
```
Plugin Info: document_matcher
 • ID:          document_matcher
 • Type:        Matcher
 • Name:        Document Text & Tabular Matcher
 • Version:     0.1.0
 • Author:      Clairvoy Team
 • Available:   yes (pypdf 6.18.1 available)
 • Priority:    50
 • Enabled:     yes
 • Description: Discovers identical and near-duplicate documents across .pdf, .docx, .pptx, .odt, .csv, and .tsv
```

### Scan with Plugins Enabled / Disabled
```bash
# Scan with document_matcher enabled and photo_vision disabled
clairvoy scan /media/documents --enable-plugin document_matcher --disable-plugin photo_vision

# Scan with exact_hash disabled (forces downstream fuzzy matchers on all files)
clairvoy scan /media/documents --disable-plugin exact_hash
```
