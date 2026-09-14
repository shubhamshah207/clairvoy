# Document & Tabular Deduplication Design Specification (Phase 2)

- **Date:** 2026-09-13
- **Status:** Approved
- **Author:** Senior Staff Engineer / Antigravity Agent
- **Target Subsystem:** Document Matcher Plugin (`DocumentTextMatcherPlugin`)

---

## 1. Executive Summary & Problem Context

On Drive E (`/mnt/e`), non-media documents and tabular datasets occupy significant storage:
- **PDF Documents (`.pdf`):** 1,653 files (2.11 GB)
- **Tabular Data (`.csv`, `.tsv`):** 101 files (4.09 GB)
- **Office Documents (`.docx`, `.pptx`, `.odt`):** ~375 files (265.76 MB)

While identical files are caught by Tier 1 QuickHash + SHA-256, users frequently accumulate:
1. Re-saved / re-exported PDFs (e.g., downloaded multiple times with different creation timestamps or compression).
2. Word / PowerPoint drafts (`.docx`, `.pptx`) with identical body text but distinct internal metadata.
3. CSV/TSV exports with identical row contents but different row ordering or trailing whitespace.

This specification introduces the **`DocumentTextMatcherPlugin`** (Priority 50) to discover text and structural duplicates across these document formats.

---

## 2. Architecture & Document Processing Flow

```
+----------------------------------------------------------------------------------------------------+
|                                  DOCUMENT DEDUPLICATION FLOW                                       |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|                                     [Document Candidates]                                          |
|                                     .pdf, .docx, .pptx, .odt, .csv, .tsv                           |
|                                                |                                                   |
|         +--------------------------------------+--------------------------------------+            |
|         |                                      |                                      |            |
|         v                                      v                                      v            |
|  [PDF Extractor]                        [Office XML Extractor]                 [Tabular Normalizer] |
|  pypdf text extraction                  In-memory zipfile                      csv.reader           |
|  (Page-by-page text streams)            (word/document.xml, ppt/slides/...)    (Header + Row sort)  |
|         |                                      |                                      |            |
|         +--------------------------------------+--------------------------------------+            |
|                                                |                                                   |
|                                                v                                                   |
|                                    [Normalized Text & Tokens]                                      |
|                                     - Lowercase, whitespace trimmed                                |
|                                     - SHA-256 normalized hash                                      |
|                                     - Token set Jaccard similarity                                 |
|                                                |                                                   |
|                                                v                                                   |
|                                   [Disjoint Set Union (DSU)]                                       |
|                                                |                                                   |
|                                                v                                                   |
|                             [Document Duplicate Clusters (>= 90%)]                                 |
+----------------------------------------------------------------------------------------------------+
```

---

## 3. Component Details

### 3.1. Match Type Expansion
In [`clairvoy/core/models.py`](file:///home/shubhamshah207/clairvoy/clairvoy/core/models.py):
- Add `CONTENT_NEAR_DUPLICATE = "CONTENT_NEAR_DUPLICATE"` to `MatchType`.

### 3.2. Document Text Matcher Plugin
- **File:** `clairvoy/plugins/document_matcher.py`
- **Class:** `DocumentTextMatcherPlugin(BaseMatcherPlugin)`
- **Priority:** `50`
- **Supported Formats:** `.pdf`, `.docx`, `.pptx`, `.odt`, `.csv`, `.tsv` (case-insensitive).
- **Extraction Strategies:**
  1. **`.pdf`:** Extracts text per page via `pypdf.PdfReader`.
  2. **`.docx`:** Unpacks `word/document.xml` in memory via `zipfile` and reads all `<w:t>` elements.
  3. **`.pptx`:** Unpacks `ppt/slides/slide*.xml` and reads all `<a:t>` text elements.
  4. **`.odt`:** Unpacks `content.xml` and reads text nodes.
  5. **`.csv` / `.tsv`:** Reads header columns and row hashes; sorts row hashes to achieve permutation-invariant matching.
- **Clustering Heuristics:**
  - Identical normalized content hash $\rightarrow$ 1.0 similarity.
  - High token Jaccard similarity ($\ge 0.90$) $\rightarrow$ near-duplicate cluster.

---

## 4. Verification Plan
- Unit tests in `tests/test_document_matcher.py` testing PDF, DOCX, PPTX, and CSV/TSV deduplication.
- E2E pipeline integration test.
- Full pytest test suite and ruff linting pass with 100% success.
- Update `AGENTS.md`, `docs/ARCHITECTURE.md`, and `docs/PLUGINS.md`.
