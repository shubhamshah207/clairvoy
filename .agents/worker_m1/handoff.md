# Milestone M1 Handoff Report: DocumentTextMatcherPlugin Core Engine & Unit Tests

- **Author:** `worker_m1`
- **Working Directory:** [`/home/shubhamshah207/clairvoy/.agents/worker_m1`](file:///home/shubhamshah207/clairvoy/.agents/worker_m1)
- **Objective:** Implement `DocumentTextMatcherPlugin` core engine, format extractors (.pdf, .docx, .pptx, .odt, .csv, .tsv), memory safety caps, normalization, token Jaccard similarity, and DSU clustering in [`clairvoy/plugins/document_matcher.py`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/document_matcher.py). Fix and expand unit tests in [`tests/test_document_matcher.py`](file:///home/shubhamshah207/clairvoy/tests/test_document_matcher.py).
- **Date:** 2026-09-14T05:54:00Z
- **Handoff Type:** Hard (Task Complete)

---

## 1. Observation

### 1.1 Initial State & Requirements Verification
- [`ORIGINAL_REQUEST.md`](file:///home/shubhamshah207/clairvoy/.agents/ORIGINAL_REQUEST.md) specified:
  - `DocumentTextMatcherPlugin` (priority order 50, match type `CONTENT_NEAR_DUPLICATE`) supporting `.pdf`, `.docx`, `.pptx`, `.odt`, `.csv`, `.tsv`.
  - PDF text extraction via pure-Python `pypdf.PdfReader` up to 50 pages.
  - Office XML text inspection (`word/document.xml`, `ppt/slides/slide*.xml`, `content.xml`) in memory via `zipfile`.
  - Tabular normalization (.csv, .tsv) by delimiter sniffing, row sorting, and permutation-invariant content digests.
  - Token Jaccard similarity threshold $\ge 0.90$ for near-duplicate documents with $O(1)$ ratio pruning.
  - Memory bounds: 25 MB stream read cap, 50,000 words extracted text cap, 100% offline local-first execution.
- Baseline test state before implementation:
  - Running `/home/shubhamshah207/miniconda3/bin/pytest tests/test_document_matcher.py`:
    `ModuleNotFoundError: No module named 'clairvoy.plugins.document_matcher'`
  - Existing suite excluding target:
    `/home/shubhamshah207/miniconda3/bin/pytest --ignore=tests/test_document_matcher.py -v` $\rightarrow$ `131 passed, 2 warnings in 3.51s`.
  - Static linter check:
    `/home/shubhamshah207/miniconda3/bin/ruff check .` $\rightarrow$ `I001 Import block is un-sorted or un-formatted --> tests/test_document_matcher.py:3:1`.

### 1.2 Implemented Components
1. [`clairvoy/plugins/document_matcher.py`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/document_matcher.py):
   - Created class `DocumentTextMatcherPlugin(BaseMatcherPlugin)`:
     - `plugin_id = "document_matcher"`
     - `display_name = "Document Text & Tabular Matcher"`
     - `version = "0.1.0"`
     - `author = "Clairvoy Team"`
     - `description = "Discovers identical and near-duplicate documents across .pdf, .docx, .pptx, .odt, .csv, and .tsv"`
     - `match_type = MatchType.CONTENT_NEAR_DUPLICATE`
     - `priority_order = 50`
     - `SUPPORTED_DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".pptx", ".odt", ".csv", ".tsv"}`
   - Implemented `is_available() -> tuple[bool, str]`: checks `pypdf` availability and returns `(True, f"pypdf {PYPDF_VERSION} available")`.
   - Implemented `filter_supported(files: list[FileEntry]) -> list[FileEntry]`: filters candidate entries by extension and `size_bytes > 0`.
   - Implemented `extract_document_representation(path: str) -> tuple[str, str, int] | None`: returns `(content_hash, preview, length)`.
   - Implemented format extractors:
     - PDF: `_extract_pdf_text` uses `pypdf.PdfReader`, slices `reader.pages[:50]`, handles encrypted/corrupt/empty files gracefully, caps at 25 MB.
     - DOCX: `_extract_docx_text` reads `word/document.xml` via `zipfile`, parses XML with `ElementTree`, extracts `<w:t>` runs grouped by `<w:p>` paragraphs.
     - PPTX: `_extract_pptx_text` finds `ppt/slides/slide*.xml` with natural slide sorting `re.search(r'slide(\d+)\.xml$', name)`, extracts `<a:t>` runs across slides.
     - ODT: `_extract_odt_text` reads `content.xml` via `zipfile`, extracts text with `root.itertext()`.
     - CSV/TSV: `_extract_tabular_text` reads up to 25 MB, decodes `utf-8-sig` (stripping BOM), detects binary null bytes, sniffs delimiter, strips per-cell whitespace, sorts data rows canonically via `sorted(data_rows, key=tuple)`, and emits canonical string.
   - Text normalization and caps:
     - Whitespace collapsed via `re.sub(r'\s+', ' ', text).strip()`.
     - Extracted words capped at 50,000 words (`words[:50000]`).
     - SHA-256 canonical digest computed over normalized representation.
   - Similarity & DSU clustering in `find_duplicates`:
     - Stage 1: Group by identical `content_hash` $\rightarrow$ similarity 1.0.
     - Stage 2: Token Jaccard similarity for candidate pairs with $\ge 5$ tokens:
       $O(1)$ pruning check: `min_len / max_len < 0.90` skips pairwise set computation.
       `len(A & B) / len(A | B) >= 0.90` matches near-duplicate documents.
     - Disjoint Set Union (`DisjointSetUnion`) with path compression and rank union merges connected components.
     - Returns `list[DuplicateCluster]` with `match_type = MatchType.CONTENT_NEAR_DUPLICATE`.

2. [`tests/test_document_matcher.py`](file:///home/shubhamshah207/clairvoy/tests/test_document_matcher.py):
   - Fixed imports to satisfy ruff linter.
   - Preserved and verified existing test cases:
     - `test_supported_document_extensions`
     - `test_document_matcher_availability`
     - `test_docx_duplicate_matching`
     - `test_pptx_duplicate_matching`
     - `test_csv_permutation_invariant_matching`
     - `test_pdf_extraction_if_sample_exists`
   - Added comprehensive test coverage:
     - `test_filter_supported`: validates extension filtering and 0-byte exclusion.
     - `test_odt_duplicate_matching`: validates OpenDocument text extraction and duplicate clustering.
     - `test_tsv_and_cross_format_tabular_matching`: validates TSV row permutation invariance and cross-format CSV/TSV deduplication.
     - `test_synthetic_pdf_extraction_and_matching`: tests standalone PDF deduplication via self-contained synthetic PDF stream generator without external file dependency.
     - `test_near_duplicate_token_jaccard_matching`: validates clustering of near-duplicate document revisions ($\ge 0.90$ token overlap) while excluding low-overlap files (< 0.90).
     - `test_corrupted_documents_graceful_handling`: tests graceful return of `None` on corrupted docx, corrupted pdf, binary csv containing null bytes, and empty docx.
     - `test_word_cap_truncation`: validates 50,000-word truncation cap on massive documents.
     - `test_multi_cluster_grouping`: validates DSU partitioning of multiple distinct duplicate clusters.

### 1.3 Execution Results
- Unit tests:
  ```
  /home/shubhamshah207/miniconda3/bin/pytest tests/test_document_matcher.py -v
  ============================== 14 passed in 0.69s ==============================
  ```
- Full test suite:
  ```
  /home/shubhamshah207/miniconda3/bin/pytest -v
  ======================= 145 passed, 2 warnings in 5.58s ========================
  ```
- Static linter:
  ```
  /home/shubhamshah207/miniconda3/bin/ruff check .
  All checks passed!
  ```

---

## 2. Logic Chain

```
+----------------------------------------------------------------------------------------------------+
|                         DOCUMENT TEXT & TABULAR MATCHER ENGINE (M1)                                |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|                                       [Candidate Files]                                            |
|                                (.pdf, .docx, .pptx, .odt, .csv, .tsv)                              |
|                                                  |                                                 |
|                                                  v                                                 |
|                                     [filter_supported()]                                           |
|                                   (size > 0 & ext whitelist)                                       |
|                                                  |                                                 |
|         +-----------------------+----------------+----------------+-----------------------+        |
|         |                       |                                 |                       |        |
|         v                       v                                 v                       v        |
|    [PDF Extractor]       [DOCX Extractor]                  [PPTX/ODT Extractor]    [Tabular Extractor] |
|   pypdf.PdfReader       zipfile in-memory                 zipfile in-memory        csv.Sniffer/reader  |
|    (Cap 50 pgs)        (word/document.xml)             (ppt/slides/*.xml, content)  (Header+Row Sort)  |
|         |                       |                                 |                       |        |
|         +-----------------------+----------------+----------------+-----------------------+        |
|                                                  |                                                 |
|                                                  v                                                 |
|                                      [Memory Safety Guardrails]                                    |
|                                       - Buffer Cap: 25 MB                                          |
|                                       - Word Cap: 50,000 words                                     |
|                                                  |                                                 |
|                                                  v                                                 |
|                                    [Normalized Text Representation]                                |
|                                      - Canonical SHA-256 Digest                                    |
|                                      - Word Token Set (Regex \b\w+\b)                              |
|                                                  |                                                 |
|                                                  v                                                 |
|                                 [Stage 1: Exact Normalized Hash]                                   |
|                                     (Identical Digest -> sim 1.0)                                  |
|                                                  |                                                 |
|                                                  v                                                 |
|                                [Stage 2: Token Jaccard Similarity]                                 |
|                                   - Fast ratio prune: min/max < 0.90                               |
|                                   - |A & B| / |A | B| >= 0.90                                      |
|                                                  |                                                 |
|                                                  v                                                 |
|                                     [DisjointSetUnion (DSU)]                                       |
|                                                  |                                                 |
|                                                  v                                                 |
|                                     [list[DuplicateCluster]]                                       |
|                                 (CONTENT_NEAR_DUPLICATE, Prio 50)                                  |
+----------------------------------------------------------------------------------------------------+
```

1. **Extraction Completeness:**
   - Supported extensions `.pdf`, `.docx`, `.pptx`, `.odt`, `.csv`, `.tsv` match Requirement R1.
   - Pure-Python `pypdf` extracts up to 50 pages without OCR dependencies.
   - In-memory `zipfile` inspection parses XML without extracting to disk, preventing filesystem bloat.
   - Natural slide sorting (`ppt/slides/slide(\d+).xml`) prevents slide ordering anomalies in PPTX files.
2. **Permutation Invariance for Tabular Data:**
   - Data rows are stripped of leading/trailing whitespace and sorted canonically using `sorted(data_rows, key=tuple)`.
   - As observed in `test_csv_permutation_invariant_matching` and `test_tsv_and_cross_format_tabular_matching`, permuted rows produce identical canonical text representations and matching SHA-256 digests.
3. **Memory Safety & Graceful Degradation:**
   - Stream reads cap at 25 MB buffer size, preventing zip bombs or massive file memory exhaustion.
   - Extracted text is capped at 50,000 words, bounding memory consumed during tokenization.
   - Corrupted or encrypted files trigger debug-level logging and return `None` gracefully, preventing pipeline aborts.
4. **Fast Similarity Pruning & Clustering:**
   - Pairwise comparisons between token sets $A$ and $B$ are pruned if $\frac{\min(|A|, |B|)}{\max(|A|, |B|)} < 0.90$, guaranteeing $O(1)$ rejection of dissimilar documents before performing set intersections.
   - Connected components are resolved via `DisjointSetUnion`, cleanly grouping multi-way duplicate clusters.

---

## 3. Caveats

- **Scanned / Raster-Only PDFs:** `pypdf.PdfReader` extracts embedded digital text streams. Scanned PDFs lacking an OCR text layer return `None` and are intentionally not matched by text similarity, avoiding false positives on un-indexed images.
- **Tabular Column Order:** R1 requires row permutation invariance. Column order is intentionally preserved with headers to retain table column semantics.
- **Downstream Integration (M2 Scope):** Per DISPATCH constraints, `clairvoy/engines/pipeline.py` and `clairvoy/cli.py` were not modified in Milestone M1 and remain assigned to worker Milestone M2.

---

## 4. Conclusion

Milestone M1 is **100% complete**:
- [`DocumentTextMatcherPlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/document_matcher.py) is implemented with deep module boundaries, robust error handling, memory caps, and full format support.
- [`tests/test_document_matcher.py`](file:///home/shubhamshah207/clairvoy/tests/test_document_matcher.py) contains 14 passing unit tests covering all formats, error cases, and similarity clustering.
- Full test suite passes at 145/145 tests with 0 ruff linter errors.
- Milestone M2 (Pipeline & CLI Integration) can now proceed cleanly.

---

## 5. Verification Method

### 5.1 Commands to Run
1. Run target unit tests:
   ```bash
   /home/shubhamshah207/miniconda3/bin/pytest tests/test_document_matcher.py -v
   ```
   *Expected:* `14 passed in <1.0s`.
2. Run full regression test suite:
   ```bash
   /home/shubhamshah207/miniconda3/bin/pytest -v
   ```
   *Expected:* `145 passed, 2 warnings in ~5.5s`.
3. Run static linter:
   ```bash
   /home/shubhamshah207/miniconda3/bin/ruff check .
   ```
   *Expected:* `All checks passed!`.

### 5.2 Files to Inspect
- [`clairvoy/plugins/document_matcher.py`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/document_matcher.py)
- [`tests/test_document_matcher.py`](file:///home/shubhamshah207/clairvoy/tests/test_document_matcher.py)
- [`BRIEFING.md`](file:///home/shubhamshah207/clairvoy/.agents/worker_m1/BRIEFING.md)
- [`progress.md`](file:///home/shubhamshah207/clairvoy/.agents/worker_m1/progress.md)

### 5.3 Invalidation Conditions
- Any failure in `tests/test_document_matcher.py`.
- Any error from `/home/shubhamshah207/miniconda3/bin/ruff check .`.
- Any regression in the core pipeline or existing matchers.
