# TEST_READY: Document & Tabular Deduplication E2E Test Suite

This manifest declares the readiness and full verification of the comprehensive opaque-box E2E test suite for Clairvoy document and tabular deduplication (`.pdf`, `.docx`, `.pptx`, `.odt`, `.csv`, `.tsv`).

- **Test Suite Path:** [`file:///home/shubhamshah207/clairvoy/tests/test_document_e2e.py`](file:///home/shubhamshah207/clairvoy/tests/test_document_e2e.py)
- **Target Plugin:** [`DocumentTextMatcherPlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/document_matcher.py)
- **Status:** **READY & VERIFIED (83 passed in 0.98s, 100% pass rate, 0 lint errors)**
- **Test Runner Command:**
  ```bash
  /home/shubhamshah207/miniconda3/bin/pytest tests/test_document_e2e.py -v
  ```

---

## 1. Test Architecture & Tier Mapping

```
+----------------------------------------------------------------------------------------------------+
|                                    E2E TEST SUITE ARCHITECTURE                                     |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|    [Tier 1: Feature Coverage (35 Tests)]                                                           |
|    +------------------------------------------------------------------------------------------+    |
|    | PDF Deduplication (6)       | Multipage, author metadata, whitespace, triplets, API rep  |    |
|    | DOCX Deduplication (6)      | Multiparagraph, multiple runs, app metadata, API rep       |    |
|    | PPTX Deduplication (6)      | Multislide, shapes, triplets, API rep                      |    |
|    | ODT Deduplication (6)       | Headings, nested spans, triplets, API rep                  |    |
|    | CSV/TSV Tabular (6)         | Row permuted, TSV cross-match, whitespace trimming, digest |    |
|    | Token Jaccard >= 0.90 (5)   | High similarity, minor edit, disclaimer preamble, DSU      |    |
|    +------------------------------------------------------------------------------------------+    |
|                                                  |                                                 |
|                                                  v                                                 |
|    [Tier 2: Boundary & Corner Cases (32 Tests)]                                                    |
|    +------------------------------------------------------------------------------------------+    |
|    | Corrupted & Truncated (6)   | Truncated PDF, non-zip DOCX, missing XML, malformed PPTX   |    |
|    | Encrypted & Zero-Byte (6)   | Password PDF, 0-byte filtered, blank PDF, binary renamed   |    |
|    | PPTX Natural Sort (5)       | Slides 1..10 order, reverse order diff, 15 slides, 0 slide |    |
|    | CSV Delimiter & BOM (5)     | UTF-8 BOM, semicolon sniffing, explicit TSV, ragged rows   |    |
|    | Buffer & Word Caps (5)      | 25MB buffer cap, 50,000 word cap, 50-page PDF cap, preview |    |
|    | Token Similarity (5)        | Exact 0.90 pass, 0.88 reject, 0.95 pass, short text bypass |    |
|    +------------------------------------------------------------------------------------------+    |
|                                                  |                                                 |
|                                                  v                                                 |
|    [Tier 3: Cross-Feature Interactions (11 Tests)]                                                 |
|    +------------------------------------------------------------------------------------------+    |
|    | Multi-Format Matches (4)    | DOCX vs ODT, PDF vs DOCX, PPTX vs DOCX, ODT vs PDF         |    |
|    | Tabular Delimiters (2)      | Comma CSV vs Tab TSV, Semicolon CSV vs Tab TSV shuffled    |    |
|    | Multi-Way DSU Clusters (3)  | 3-way transitive chain, 2 disjoint clusters, 4-way mixed   |    |
|    | Pipeline Integration (2)    | Tier 1 ExactHash short-circuit, CompositeKeeperStrategy    |    |
|    +------------------------------------------------------------------------------------------+    |
|                                                  |                                                 |
|                                                  v                                                 |
|    [Tier 4: Real-World Application Scenarios (5 Tests)]                                            |
|    +------------------------------------------------------------------------------------------+    |
|    | Scenario 1: Corporate Rebrand | Draft DOCX vs Final Legal PDF export                     |    |
|    | Scenario 2: Sales Pipeline    | Permuted CRM CSV export vs BI Tab-delimited TSV export   |    |
|    | Scenario 3: Board Meeting     | Executive presentation v1 vs v2 with minor bullet edit   |    |
|    | Scenario 4: Academic Paper    | LibreOffice Writer .odt draft vs Word .docx camera-ready |    |
|    | Scenario 5: Mixed Directory   | Multi-file scan with valid, corrupted, encrypted, 0-byte |    |
|    +------------------------------------------------------------------------------------------+    |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Coverage Summary

| Tier | Category | Number of Tests | Pass Rate | Execution Time |
|:-----|:---------|:---------------:|:---------:|:--------------:|
| **Tier 1** | Feature Coverage (PDF, DOCX, PPTX, ODT, CSV/TSV, Token Jaccard) | 35 | 100% (35/35) | ~0.45s |
| **Tier 2** | Boundary & Corner Cases (Corruption, Encryption, Sort, BOM, Caps, Thresholds) | 32 | 100% (32/32) | ~0.35s |
| **Tier 3** | Cross-Feature Interactions (Multi-format, Shuffled CSV/TSV, DSU, Pipeline) | 11 | 100% (11/11) | ~0.10s |
| **Tier 4** | Real-World Application Scenarios (Rebrand, Sales, Board, Paper, Mixed Scan) | 5 | 100% (5/5) | ~0.08s |
| **Total** | **Full Opaque-Box E2E Test Suite** | **83** | **100% (83/83)** | **0.98s** |

---

## 3. Feature Verification Checklist

### Format Deduplication (Tier 1)
- [x] **PDF Text Extraction & Deduplication**: Identical text across different authors, multi-page PDFs (3 pages), whitespace normalization, 3-way cluster grouping, and representation API.
- [x] **Word DOCX Deduplication**: Multiparagraph body text, segmented `<w:r><w:t>` runs, application metadata variances, whitespace normalization, and representation API.
- [x] **PowerPoint PPTX Deduplication**: Natural ordered slide text across multiple shapes, presentation properties variance, 3-way cluster grouping, and representation API.
- [x] **OpenDocument ODT Deduplication**: Headings (`<text:h>`), paragraphs (`<text:p>`), nested formatting spans (`<text:span>`), 3-way cluster grouping, and representation API.
- [x] **Tabular CSV/TSV Deduplication**: Delimiter sniffing, row permutation invariance, cell whitespace trimming, cross-format matching (CSV vs TSV), and canonical digest generation.
- [x] **Token Jaccard Near-Duplicate Matching**: Threshold $\ge 0.90$, minor edits / typo corrections, preamble / disclaimer additions, similarity score preservation, and transitive DSU chain grouping.

### Boundary & Corner Cases (Tier 2)
- [x] **Corrupted & Truncated Files**: Truncated PDF, non-zip `.docx`, zip missing `document.xml`, malformed XML in `.pptx`, zip missing `content.xml` in `.odt`, and binary null bytes in `.csv`.
- [x] **Encrypted & Zero-Byte Documents**: Password-encrypted PDF graceful fallback (`None`), 0-byte candidate filtering, empty text PDF, empty body DOCX, empty CSV, and disguised binary files.
- [x] **PPTX Slide Natural Ordering**: Slides 1..10 natural numeric order, slide reversal content differentiation, multi-digit padded slide names (`slide01.xml`), 15-slide ordering, and 0-slide presentation fallback.
- [x] **CSV Delimiter Sniffing & UTF-8 BOM**: UTF-8 BOM (`\xef\xbb\xbf`) automatic strip, European semicolon (`;`) sniffer, explicit tab (`\t`) TSV parsing, ragged row handling, and single-column CSV.
- [x] **Memory Bounds & Word Caps**: 25 MB stream/buffer cap constant, 50,000 word truncation cap, divergence after 50,000 words matching, 50-page PDF page limit, and preview snippet bounding ($\le 500$ chars).
- [x] **Token Similarity Threshold Edge Cases**: Exactly 0.90 similarity passes, 0.88 similarity rejected, 0.95 similarity passes, 0.0 disjoint rejected, and short text (< 5 tokens) bypass.

### Cross-Feature & Real-World Scenarios (Tiers 3 & 4)
- [x] **Cross-Format Matching**: DOCX vs ODT, PDF vs DOCX, PPTX vs DOCX, ODT vs PDF.
- [x] **Permuted Cross-Delimiter Tabular**: Comma CSV vs Tab TSV, Semicolon CSV vs Tab TSV.
- [x] **Transitive Multi-Way Clustering**: 3-way DSU chain merging, 2 disjoint clusters isolation, 4-way quadruplet across all four document formats.
- [x] **Pipeline & Keeper Integration**: Tier 1 ExactHash short-circuit pruning, CompositeKeeperStrategy cleanest filename selection.
- [x] **Real-World Scenarios**: Corporate rebrand draft vs PDF, permuted sales CRM vs BI export, board meeting presentation revisions, academic paper draft vs camera-ready, full mixed directory scan.

---

## 4. Verification Instructions

To execute the test suite independently:

```bash
# 1. Run the full E2E test suite
/home/shubhamshah207/miniconda3/bin/pytest tests/test_document_e2e.py -v

# 2. Run static analysis and linting
/home/shubhamshah207/miniconda3/bin/ruff check tests/test_document_e2e.py
```
