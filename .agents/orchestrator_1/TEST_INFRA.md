# E2E Test Infra: Clairvoy Document Deduplication

## Test Philosophy
- Opaque-box, requirement-driven. Derived strictly from ORIGINAL_REQUEST.md and user specifications.
- Methodology: Category-Partition + Boundary Value Analysis (BVA) + Pairwise Combinatorial + Real-World Workload Testing.

## Feature Inventory & Test Coverage Matrix
| # | Feature | Source | Tier 1 (Feature) | Tier 2 (Boundary) | Tier 3 (Cross-Feature) |
|---|---------|--------|:----------------:|:-----------------:|:----------------------:|
| 1 | PDF Text Deduplication (.pdf) | ORIGINAL_REQUEST §R1 | 5 cases | 5 cases (encrypted, truncated, 0-byte, >50 pgs, scanned image) | Pairwise |
| 2 | Word DOCX Deduplication (.docx) | ORIGINAL_REQUEST §R1 | 5 cases | 5 cases (non-zip, empty zip, missing document.xml, malformed XML, whitespace runs) | Pairwise |
| 3 | PowerPoint PPTX Deduplication (.pptx) | ORIGINAL_REQUEST §R1 | 5 cases | 5 cases (slide sorting 1..10, 0 slides, non-zip, malformed XML, large slides) | Pairwise |
| 4 | OpenDocument ODT Deduplication (.odt) | ORIGINAL_REQUEST §R1 | 5 cases | 5 cases (nested spans, missing content.xml, non-zip, malformed XML, empty paragraphs) | Pairwise |
| 5 | Tabular CSV/TSV Normalization | ORIGINAL_REQUEST §R1 | 5 cases | 5 cases (permuted rows, UTF-8 BOM, tab vs comma, null bytes, ragged rows) | Pairwise |
| 6 | Token Jaccard Similarity (>= 0.90) | ORIGINAL_REQUEST §R1 | 5 cases | 5 cases (exactly 0.90, 0.89 rejection, 0.95 pass, short text <5 words, identical 1.0) | Pairwise |
| 7 | Memory Bounds (25MB, 50k words) | ORIGINAL_REQUEST §R3 | 5 cases | 5 cases (>25MB buffer truncation, >50k words cap, fast return, no memory leak) | Pairwise |
| 8 | Pipeline Short-Circuit & CLI Listing | ORIGINAL_REQUEST §R2 | 5 cases | 5 cases (byte-exact short circuit, CLI plugins list, scan output, quarantine, keeper scoring) | Pairwise |

## Test Architecture
- Test Runner: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_document_e2e.py -v`
- Execution semantics: All tests pass with exit code 0.
- Directory layout:
  - `tests/test_document_matcher.py` (Unit tests for plugin methods & extractors)
  - `tests/test_document_e2e.py` (Opaque-box E2E test suite covering Tiers 1-4)

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Multi-format company rebrand (DOCX draft vs finalized PDF export with identical text) | F1, F2, F6, F8 | High |
| 2 | Sales pipeline dataset exported twice (CSV permuted row order vs TSV tab-delimited) | F5, F6, F8 | Medium |
| 3 | Board meeting presentation drafts (.pptx revised with 2 words changed, >= 0.90 Jaccard) | F3, F6, F8 | Medium |
| 4 | Academic paper draft versions (.odt vs .docx near-duplicate clustering) | F2, F4, F6, F8 | High |
| 5 | Mass directory scan with mixed corrupted/encrypted files alongside valid documents | F1, F2, F3, F4, F5, F7, F8 | High |

## Coverage Thresholds
- Tier 1: ≥5 per feature
- Tier 2: ≥5 per feature (where boundaries exist)
- Tier 3: Pairwise coverage of major feature interactions
- Tier 4: ≥5 realistic application scenarios
- Acceptance: 100% passing opaque-box tests
