# Handoff Report: Pipeline, CLI, Dependency & Testing Architecture Survey

- **Author:** `explorer_survey_2`
- **Working Directory:** [`/home/shubhamshah207/clairvoy/.agents/explorer_survey_2`](file:///home/shubhamshah207/clairvoy/.agents/explorer_survey_2)
- **Target Task:** Content-Aware Document & Tabular Deduplication (`DocumentTextMatcherPlugin`)
- **Mode:** Read-Only Architectural Survey & Synthesis

---

## 1. Observation

### 1.1 `clairvoy/engines/pipeline.py` Analysis

Direct code inspection of [`clairvoy/engines/pipeline.py`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/pipeline.py) reveals:

1. **Plugin Suite Initialization** (Lines 152–163):
   ```python
   # If registry has no matchers registered, populate default matcher suite
   if len(self.registry.get_matchers(enabled_only=False)) == 0:
       self.registry.register(ExactHashMatcherPlugin())
       self.registry.register(PhotoVisionMatcherPlugin())
       self.registry.register(VideoKeyframeMatcherPlugin())
       self.registry.register(ArchiveInspectorMatcherPlugin())

   # If registry has no actions registered, populate default action suite
   if len(self.registry.get_actions(enabled_only=False)) == 0:
       self.registry.register(SafeQuarantineActionPlugin())
       self.registry.register(HardlinkActionPlugin())
   ```
   *Finding:* `DocumentTextMatcherPlugin` is not yet imported or registered in `DeduplicationPipeline`.

2. **Filesystem Traversal & Candidate Discovery** (Lines 173–257):
   ```python
   elif entry.is_file(follow_symlinks=False):
       stat = entry.stat(follow_symlinks=False)
       sz = stat.st_size
       if sz > 0:
           ext = Path(entry.name).suffix.lower()
           is_media = (
               ext in SUPPORTED_IMAGE_EXTENSIONS
               or ext in SUPPORTED_VIDEO_EXTENSIONS
           )
           p = str(Path(entry.path).resolve())
           entries.append(
               FileEntry(
                   path=p,
                   size_bytes=sz,
                   is_media=is_media,
               )
           )
           if is_media:
               media_paths.append(p)
   ```
   *Finding:* All non-empty files on the filesystem are indexed into `all_files: list[FileEntry]`. Documents (`.pdf`, `.docx`, `.pptx`, `.odt`, `.csv`, `.tsv`) are naturally indexed with `is_media=False`. The pipeline does NOT restrict candidate collection to media; media filtering is done by `is_media` only for `media_files` passed to `ClassifierEngine`.

3. **Chained Priority Matching & Short-Circuit Candidate Pruning** (Lines 305–338):
   ```python
   # Retrieve enabled and available matchers in ascending priority_order
   matchers = self.registry.get_matchers(enabled_only=True, available_only=True)
   total_matchers = len(matchers)

   all_clusters: list[DuplicateCluster] = []
   matched_paths: set[str] = set()
   next_cluster_id = 1

   for idx, matcher in enumerate(matchers):
       if progress_callback:
           progress_callback(
               f"Running matcher: {matcher.display_name}",
               idx,
               max(1, total_matchers),
           )

       # Short-circuit pruning invariant: exclude files already clustered by previous matchers
       candidates = [f for f in all_files if f.path not in matched_paths]
       supported = matcher.filter_supported(candidates)

       if not supported:
           continue

       context: dict[str, Any] = {
           "start_cluster_id": next_cluster_id,
           "num_workers": self.num_workers,
       }
       clusters = matcher.find_duplicates(supported, all_files, context=context)

       for cluster in clusters:
           matched_paths.update(m.path for m in cluster.members)
           all_clusters.append(cluster)
           next_cluster_id += 1
   ```
   *Finding:* Matchers execute strictly in ascending order of `matcher.priority_order`. Files clustered by an earlier tier are added to `matched_paths` and pruned from `candidates` passed to downstream matchers. If two `.docx` or `.csv` files are byte-for-byte identical, Tier 1 (`exact_hash`, priority 10) clusters them, and they are never sent to downstream matchers. Non-identical documents flow down to Tier 5 (`priority_order = 50`).

4. **Cluster Aggregation, Keeper Scoring, & Report Generation** (Lines 351–498):
   - Clusters are scored using `self.keeper_strategy.choose_keeper(cluster)` ([`CompositeKeeperStrategy`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/pipeline.py#L53)).
   - Clean filenames win, penalized patterns (`(1)`, `copy`, `dupe`) lose.
   - For duplicates, `total_wasted_bytes += d.size_bytes` is calculated.
   - Output files generated:
     - `clairvoy_duplicates.csv` ([`DuplicateRecord`](file:///home/shubhamshah207/clairvoy/clairvoy/core/models.py#L41) rows)
     - `clairvoy_quarantine.sh` (hardened executable bash script)
     - `clairvoy_summary.json` (serialized [`ScanSummary`](file:///home/shubhamshah207/clairvoy/clairvoy/core/models.py#L63))
   - Lines 467–473 count clusters:
     ```python
     exact_duplicate_groups = sum(
         1 for c in all_clusters if c.match_type == MatchType.EXACT_HASH
     )
     visual_ai_groups = sum(
         1 for c in all_clusters if c.match_type == MatchType.VISUAL_AI_NEAR_DUPLICATE
     )
     ```
     *Finding:* Adding `content_duplicate_groups = sum(1 for c in all_clusters if c.match_type == MatchType.CONTENT_NEAR_DUPLICATE)` to [`ScanSummary`](file:///home/shubhamshah207/clairvoy/clairvoy/core/models.py#L63) will expose document clusters in JSON summaries and CLI status output.

---

### 1.2 `clairvoy/cli.py` Analysis

Inspection of [`clairvoy/cli.py`](file:///home/shubhamshah207/clairvoy/clairvoy/cli.py) shows:

1. **Default Plugin Registration** (Lines 52–76):
   ```python
   def discover_plugins(registry: PluginRegistry | None = None) -> PluginRegistry:
       """Auto-discovers plugins: loads default suite, loads ~/.clairvoy/plugins/, loads entry points."""
       if registry is None:
           registry = PluginRegistry.get_instance()

       default_plugins: list[BasePlugin] = [
           ExactHashMatcherPlugin(),
           ArchiveInspectorMatcherPlugin(),
           PhotoVisionMatcherPlugin(),
           VideoKeyframeMatcherPlugin(),
           CompositeKeeperStrategy(),
           SafeQuarantineActionPlugin(),
           HardlinkActionPlugin(),
       ]
       for plugin in default_plugins:
           if registry.get_plugin(plugin.plugin_id) is None:
               registry.register(plugin)

       user_plugins_dir = Path.home() / ".clairvoy" / "plugins"
       if user_plugins_dir.is_dir():
           registry.load_plugins_from_directory(user_plugins_dir)

       registry.load_entry_points()
       return registry
   ```
   *Finding:* `DocumentTextMatcherPlugin` must be imported and included in `default_plugins` in `discover_plugins()`.

2. **CLI `plugins list` and `plugins info` Display** (Lines 99–172):
   - `handle_plugins_list` queries `registry.list_plugin_ids()`, sorts matchers by `priority_order`, and displays an ASCII box table:
     `Headers: ID | Type | Priority | Enabled | Available | Description`
   - When registered, `document_matcher` will appear with:
     `ID: document_matcher | Type: Matcher | Priority: 50 | Enabled: yes | Available: yes | Description: ...`
   - `handle_plugin_info` prints detailed metadata including `is_available()` reason.

3. **CLI `scan` Output** (Lines 347–359):
   ```python
   print(
       f"\n[✓] Scan completed in {summary.duration_seconds:.1f}s across {len(target_paths)} path(s)"
   )
   print(f" • Exact Duplicate Sets: {summary.exact_duplicate_groups}")
   print(f" • Visual AI Clusters: {summary.visual_ai_groups}")
   print(f" • Total Recoverable Space: {summary.wasted_mb} MB ({summary.wasted_gb} GB)")
   ```
   *Finding:* CLI can cleanly display `• Document & Tabular Clusters: {summary.content_duplicate_groups}` if added to `ScanSummary`.

---

### 1.3 `pyproject.toml` & Environment Analysis

1. **Dependency List in [`pyproject.toml`](file:///home/shubhamshah207/clairvoy/pyproject.toml)** (Lines 23–31):
   ```toml
   dependencies = [
       "typer>=0.9.0",
       "fastapi>=0.110.0",
       "uvicorn>=0.28.0",
       "pillow>=10.0.0",
       "rich>=13.0.0",
       "pydantic>=2.0.0",
       "jinja2>=3.1.0"
   ]
   ```
   *Finding:* `"pypdf>=5.0.0"` is not currently listed under `dependencies`.

2. **Runtime Environment Verification**:
   - Executed: `/home/shubhamshah207/miniconda3/bin/python -c "import pypdf; print(pypdf.__version__)"`
   - Output: `6.18.1` (Exit code: 0)
   - *Finding:* `pypdf` is already installed and available in the miniconda environment at version 6.18.1, satisfying `>=5.0.0`. No network downloads or external installs are required.

---

### 1.4 `tests/` Test Harness Analysis

1. **Current Test Status**:
   - Running full suite `/home/shubhamshah207/miniconda3/bin/pytest --ignore=tests/test_document_matcher.py -v`:
     **131 passed, 2 warnings in 6.33s** (100% success rate).
   - Running `/home/shubhamshah207/miniconda3/bin/pytest tests/test_document_matcher.py`:
     **ModuleNotFoundError: No module named 'clairvoy.plugins.document_matcher'** (Exit code: 2).

2. **Existing Draft Test [`tests/test_document_matcher.py`](file:///home/shubhamshah207/clairvoy/tests/test_document_matcher.py)**:
   - Contains:
     - `_make_dummy_docx(text: str) -> bytes`: In-memory ZIP with `word/document.xml`.
     - `_make_dummy_pptx(text: str) -> bytes`: In-memory ZIP with `ppt/slides/slide1.xml`.
     - `test_supported_document_extensions()`: Checks `.pdf`, `.docx`, `.pptx`, `.csv`, `.tsv`.
     - `test_document_matcher_availability()`: Checks `plugin.is_available()`.
     - `test_docx_duplicate_matching(tmp_path)`: Tests matching identical text across resaved `.docx`.
     - `test_pptx_duplicate_matching(tmp_path)`: Tests matching identical presentation text.
     - `test_csv_permutation_invariant_matching(tmp_path)`: Tests matching `.csv` files with shuffled rows.
     - `test_pdf_extraction_if_sample_exists()`: Verifies `extract_document_representation(path)` on `/mnt/e/ApartmentRelated/2022/Renter'sInsurance.pdf`.
   - Verified that `/mnt/e/ApartmentRelated/2022/Renter'sInsurance.pdf` exists on disk (74,015 bytes, 3 pages, contains "insurance").

3. **Existing Fixture Harness ([`tests/conftest.py`](file:///home/shubhamshah207/clairvoy/tests/conftest.py))**:
   - `temp_workspace`: Isolated temporary directory (`mkdtemp`).
   - `sample_dataset`: Populates files with exact copies and unique files.
   - `multi_root_dataset`: Populates cross-root folders.

4. **Integration Tests & Downstream Impact**:
   - [`tests/test_pipeline.py#L297`](file:///home/shubhamshah207/clairvoy/tests/test_pipeline.py#L297) checks `test_pipeline_default_registry_population`:
     `assert "exact_hash" in matcher_ids`, etc. Adding `document_matcher` will not break this test, and an assertion `assert "document_matcher" in matcher_ids` can be added.
   - [`tests/test_cli_plugins.py#L41`](file:///home/shubhamshah207/clairvoy/tests/test_cli_plugins.py#L41) checks `clairvoy plugins list`. Adding `document_matcher` will complement this without breaking existing checks.

---

## 2. Logic Chain

```
+----------------------------------------------------------------------------------------------------+
|                                    TIERED MATCHER PIPELINE                                         |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|                                       [All Files Scanned]                                          |
|                                                |                                                   |
|                                                v                                                   |
|                             +-------------------------------------+                                |
|                             | Tier 1: ExactHashMatcherPlugin      | (Priority 10)                  |
|                             | QuickHash (128KB) + Full SHA-256    |                                |
|                             +------------------+------------------+                                |
|                                                |                                                   |
|                                +---------------+---------------+                                   |
|                                |                               |                                   |
|                                v                               v                                   |
|                       [Exact Duplicates]              [Unmatched Candidates]                       |
|                       (Short-circuited)                        |                                   |
|                                                                v                                   |
|                                               +---------------------------------+                  |
|                                               | Tier 2: PhotoVisionMatcher      | (Priority 20)    |
|                                               +----------------+----------------+                  |
|                                                                |                                   |
|                                                                v                                   |
|                                               +---------------------------------+                  |
|                                               | Tier 3: VideoKeyframeMatcher    | (Priority 30)    |
|                                               +----------------+----------------+                  |
|                                                                |                                   |
|                                                                v                                   |
|                                               +---------------------------------+                  |
|                                               | Tier 4: ArchiveInspectorMatcher | (Priority 40)    |
|                                               +----------------+----------------+                  |
|                                                                |                                   |
|                                                                v                                   |
|                                               +---------------------------------+                  |
|                                               | Tier 5: DocumentTextMatcher     | (Priority 50)    |
|                                               | .pdf, .docx, .pptx, .odt,       |                  |
|                                               | .csv, .tsv                      |                  |
|                                               +----------------+----------------+                  |
|                                                                |                                   |
|                                                                v                                   |
|                                                    [Duplicate Clusters]                            |
|                                                                |                                   |
|                                                                v                                   |
|                                                +-------------------------------+                   |
|                                                |    CompositeKeeperStrategy    |                   |
|                                                +---------------+---------------+                   |
|                                                                |                                   |
|                                                                v                                   |
|                                                [Reports: CSV / JSON / Shell]                       |
+----------------------------------------------------------------------------------------------------+
```

### Step 1: Candidate Routing & Short-Circuit Pruning
- **Reasoning:** In `clairvoy/engines/pipeline.py:322`, candidates are filtered against `matched_paths`.
- Byte-identical `.pdf`, `.docx`, or `.csv` files are detected immediately by Tier 1 `ExactHashMatcherPlugin` (priority 10).
- Only non-byte-identical documents (e.g. modified timestamps, internal XML formatting differences, permuted CSV rows, or near-identical text) pass through to Tier 5 (`DocumentTextMatcherPlugin`, priority 50).
- This avoids unnecessary decompression and text extraction for identical files.

### Step 2: In-Memory Extraction & Resource Safety
- **Reasoning:**
  - Standard library `zipfile.ZipFile` opens `.docx`, `.pptx`, and `.odt` directly from file streams.
  - XML parsing using `xml.etree.ElementTree.iterparse` or regex/element text extraction avoids loading non-text media (embedded images in presentations/documents).
  - Capping buffer sizes at 25 MB / 50,000 words ensures memory safety even with gigantic files or infinite-loop decompression zip bombs.
  - PDF extraction uses `pypdf.PdfReader` with a strict page limit (`pages[:50]`) to ensure constant-time processing bounds.

### Step 3: Normalization & Permutation-Invariant Hashing
- **Text documents (`.pdf`, `.docx`, `.pptx`, `.odt`):**
  - Extract text $\rightarrow$ strip formatting/tags $\rightarrow$ lowercase $\rightarrow$ collapse whitespace $\rightarrow$ compute normalized SHA-256.
  - For near-duplicates: compute word token sets $\rightarrow$ Jaccard token similarity:
    $$\text{sim}(A, B) = \frac{|A \cap B|}{|A \cup B|}$$
    Pairs with similarity $\ge 0.90$ are clustered.
- **Tabular documents (`.csv`, `.tsv`):**
  - Read header row $\rightarrow$ clean and lowercase header names $\rightarrow$ hash header.
  - Read data rows $\rightarrow$ strip cell whitespace $\rightarrow$ hash each normalized row $\rightarrow$ sort row hashes $\rightarrow$ compute master tabular content SHA-256 digest.
  - Shuffled rows produce identical master digests $\rightarrow$ permutation-invariant duplicate detection!

### Step 4: Graceful Degradation
- Corrupted archives, encrypted PDFs, or unreadable files must not raise exceptions out of `find_duplicates` or `extract_document_representation`.
- Try/except blocks around file parsing return fallback `None` or skip the corrupted candidate, logging debug messages.

---

## 3. Caveats

1. **Read-Only Investigation Boundary:**
   - In accordance with explorer rules, no production source code in `clairvoy/` was edited during this turn.
2. **Drive E Sample PDF Dependency:**
   - The test `/mnt/e/ApartmentRelated/2022/Renter'sInsurance.pdf` exists and is accessible in the current local environment. However, CI environments or machines without `/mnt/e` will skip this test via `if real_pdf.is_file():`. Comprehensive synthetic tests (using `pypdf.PdfWriter` to write a small synthetic PDF) should also be included in `tests/test_document_matcher.py` to ensure 100% PDF test coverage in standalone environments.
3. **ODT and PPTX XML Namespace Differences:**
   - `.docx` uses `word/document.xml` with `<w:t>` tags.
   - `.pptx` uses `ppt/slides/slide*.xml` with `<a:t>` tags across multiple slide files.
   - `.odt` uses `content.xml` with `<text:p>` / `<text:span>` tags.
   - The XML extractor must handle multiple slide files in `.pptx` and appropriate text tags across formats.
4. **CSV/TSV Delimiter & Encoding Detection:**
   - CSV and TSV files may use UTF-8, UTF-8-SIG, or Latin-1 encodings. The reader should open files with `utf-8` and fallback to `latin-1` or `errors="replace"` to prevent UnicodeDecodeErrors on legacy data dumps.

---

## 4. Conclusion & Actionable Blueprint

To implement `DocumentTextMatcherPlugin` cleanly and pass all acceptance criteria, the implementer agent should execute the following steps:

### Blueprint 1: Dependency & Schema Updates
1. In [`pyproject.toml`](file:///home/shubhamshah207/clairvoy/pyproject.toml):
   - Add `"pypdf>=5.0.0"` to `dependencies`.
2. In [`clairvoy/core/models.py`](file:///home/shubhamshah207/clairvoy/clairvoy/core/models.py):
   - `MatchType.CONTENT_NEAR_DUPLICATE` already exists.
   - Add `content_duplicate_groups: int = 0` to [`ScanSummary`](file:///home/shubhamshah207/clairvoy/clairvoy/core/models.py#L63).

### Blueprint 2: Implement `DocumentTextMatcherPlugin`
Create [`clairvoy/plugins/document_matcher.py`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/document_matcher.py):
- Subclass `BaseMatcherPlugin`.
- Constants:
  - `SUPPORTED_DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".pptx", ".odt", ".csv", ".tsv"}`
- Properties:
  - `plugin_id = "document_matcher"`
  - `display_name = "Document Text & Tabular Matcher"`
  - `version = "0.1.0"`
  - `author = "Clairvoy Team"`
  - `description = "Discovers identical and near-duplicate documents across .pdf, .docx, .pptx, .odt, .csv, and .tsv"`
  - `match_type = MatchType.CONTENT_NEAR_DUPLICATE`
  - `priority_order = 50`
- Methods:
  - `is_available() -> tuple[bool, str]`: checks if `pypdf` is importable.
  - `filter_supported(files: list[FileEntry]) -> list[FileEntry]`: filters candidates with extension in `SUPPORTED_DOCUMENT_EXTENSIONS`.
  - `extract_document_representation(path: str) -> tuple[str, str, int] | None`: returns `(content_hash, preview, length)`.
  - `extract_pdf_text(path: str) -> str | None`: pure-Python `pypdf.PdfReader` up to 50 pages, caps text buffer at 25MB / 50,000 words.
  - `extract_office_text(path: str) -> str | None`: uses standard library `zipfile` to extract XML (`word/document.xml`, `ppt/slides/slide*.xml`, `content.xml`), strips XML tags.
  - `extract_tabular_digest(path: str) -> tuple[str, str, int] | None`: parses header and rows, sorts row hashes, returns deterministic content digest.
  - `find_duplicates(candidates, all_indexed_files, context) -> list[DuplicateCluster]`:
    - Groups candidates by exact content digest.
    - For remaining candidates, calculates pairwise Jaccard token similarity for pairs with size ratio $> 0.5$.
    - Groups pairs with similarity $\ge 0.90$ using Disjoint Set Union (DSU).
    - Generates `DuplicateCluster` instances with `match_type = MatchType.CONTENT_NEAR_DUPLICATE`.

### Blueprint 3: Pipeline & CLI Registration
1. In [`clairvoy/engines/pipeline.py`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/pipeline.py):
   - Import `DocumentTextMatcherPlugin` from `clairvoy.plugins.document_matcher`.
   - Register `DocumentTextMatcherPlugin()` in `DeduplicationPipeline.__init__` default matchers block.
   - Count `content_duplicate_groups = sum(1 for c in all_clusters if c.match_type == MatchType.CONTENT_NEAR_DUPLICATE)` and pass to `ScanSummary`.
   - Tag document clusters as `ImageCategory.DOCUMENT` if category is default `FILE`.
2. In [`clairvoy/cli.py`](file:///home/shubhamshah207/clairvoy/clairvoy/cli.py):
   - Import `DocumentTextMatcherPlugin` from `clairvoy.plugins.document_matcher`.
   - Register `DocumentTextMatcherPlugin()` in `discover_plugins()` default plugins list.
   - Display `Document & Tabular Clusters: {summary.content_duplicate_groups}` in `scan` command summary.

### Blueprint 4: Test Suite & Documentation Updates
1. [`tests/test_document_matcher.py`](file:///home/shubhamshah207/clairvoy/tests/test_document_matcher.py):
   - Already has DOCX, PPTX, CSV, and sample PDF tests.
   - Add tests for `.odt`, `.tsv`, token similarity clustering ($\ge 0.90$), synthetic PDF creation with `pypdf`, corrupted file handling, and word/buffer caps.
2. [`tests/test_pipeline.py`](file:///home/shubhamshah207/clairvoy/tests/test_pipeline.py):
   - Add `assert "document_matcher" in matcher_ids` to `test_pipeline_default_registry_population`.
3. Documentation:
   - Update [`AGENTS.md`](file:///home/shubhamshah207/clairvoy/AGENTS.md), [`docs/ARCHITECTURE.md`](file:///home/shubhamshah207/clairvoy/docs/ARCHITECTURE.md), and [`docs/PLUGINS.md`](file:///home/shubhamshah207/clairvoy/docs/PLUGINS.md) with Tier 5 / Priority 50 document matcher details and format matrix.

---

## 5. Verification Method

To independently verify these findings and confirm the system state:

1. **Verify Existing Tests Pass:**
   ```bash
   /home/shubhamshah207/miniconda3/bin/pytest --ignore=tests/test_document_matcher.py -v
   ```
   *Expected:* 131 passed.

2. **Verify Pending Test Failure (Missing Module):**
   ```bash
   /home/shubhamshah207/miniconda3/bin/pytest tests/test_document_matcher.py -v
   ```
   *Expected:* `ModuleNotFoundError: No module named 'clairvoy.plugins.document_matcher'`

3. **Verify `pypdf` Availability in Python Environment:**
   ```bash
   /home/shubhamshah207/miniconda3/bin/python -c "import pypdf; print(pypdf.__version__)"
   ```
   *Expected:* Version `6.18.1`.

4. **Verify Drive E Sample PDF:**
   ```bash
   /home/shubhamshah207/miniconda3/bin/python -c "from pathlib import Path; p = Path('/mnt/e/ApartmentRelated/2022/Renter\'sInsurance.pdf'); print(p.exists(), p.stat().st_size)"
   ```
   *Expected:* `True 74015`.

5. **Verify CLI Plugin Output After Implementation:**
   ```bash
   /home/shubhamshah207/miniconda3/bin/python -m clairvoy.cli plugins list
   ```
   *Expected:* ASCII table including row for `document_matcher` with Priority `50`.

6. **Verify Linter Compliance:**
   ```bash
   /home/shubhamshah207/miniconda3/bin/ruff check .
   ```
   *Expected:* 0 errors.
