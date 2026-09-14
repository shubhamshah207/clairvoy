# Project: Clairvoy Content-Aware Document & Tabular Deduplication

## Architecture

```
+----------------------------------------------------------------------------------------------------+
|                                    MATCHING PIPELINE PRIORITY TIERS                                |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|                                       [Filesystem Scanner / All Files]                             |
|                                                      |                                             |
|                                                      v                                             |
|                                   +--------------------------------------+                         |
|                                   | Tier 1: ExactHashMatcherPlugin       | (Priority 10)           |
|                                   | QuickHash (128KB) + Full SHA-256     |                         |
|                                   +------------------+-------------------+                         |
|                                                      |                                             |
|                                      +---------------+---------------+                             |
|                                      |                               |                             |
|                                      v                               v                             |
|                             [Exact Duplicates]              [Unmatched Candidates]                 |
|                             (Short-Circuited)                        |                             |
|                                                                      v                             |
|                                                     +---------------------------------+            |
|                                                     | Tier 2: PhotoVisionMatcher      | (Prio 20)  |
|                                                     +----------------+----------------+            |
|                                                                      |                             |
|                                                                      v                             |
|                                                     +---------------------------------+            |
|                                                     | Tier 3: VideoKeyframeMatcher    | (Prio 30)  |
|                                                     +----------------+----------------+            |
|                                                                      |                             |
|                                                                      v                             |
|                                                     +---------------------------------+            |
|                                                     | Tier 4: ArchiveInspectorMatcher | (Prio 40)  |
|                                                     +----------------+----------------+            |
|                                                                      |                             |
|                                                                      v                             |
|                                                     +---------------------------------+            |
|                                                     | Tier 5: DocumentTextMatcher     | (Prio 50)  |
|                                                     | .pdf, .docx, .pptx, .odt,       |            |
|                                                     | .csv, .tsv                      |            |
|                                                     +----------------+----------------+            |
|                                                                      |                             |
|                                                                      v                             |
|                                                          [Duplicate Clusters]                      |
|                                                      (CONTENT_NEAR_DUPLICATE)                      |
|                                                                      |                             |
|                                                                      v                             |
|                                                     +---------------------------------+            |
|                                                     |     CompositeKeeperStrategy     |            |
|                                                     +----------------+----------------+            |
|                                                                      |                             |
|                                                                      v                             |
|                                                      [Summary Reports / Quarantine]                |
+----------------------------------------------------------------------------------------------------+
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | PDF Text Extraction | Pure-Python `pypdf.PdfReader` up to 50 pages, catching stream/encryption errors | M1 | survey / spec |
| 2 | Word DOCX Extraction | In-memory `zipfile` reading `word/document.xml`, extracting `<w:t>` body text | M1 | survey / spec |
| 3 | PowerPoint PPTX Extraction | In-memory `zipfile` reading `ppt/slides/slide*.xml` with natural slide sorting | M1 | survey / spec |
| 4 | OpenDocument ODT Extraction | In-memory `zipfile` reading `content.xml`, extracting `<text:p>` and `<text:h>` | M1 | survey / spec |
| 5 | Tabular CSV/TSV Normalization | Sniff delimiter (`,` or `\t`), strip cell whitespace, sort data rows | M1 | survey / spec |
| 6 | Permutation-Invariant Content Digest | SHA-256 digest of canonically sorted rows for `.csv` and `.tsv` | M1 | survey / spec |
| 7 | Memory Buffer & Word Caps | Cap stream reading at 25 MB and extracted text at 50,000 words | M1 | survey / spec |
| 8 | Offline Local-First Execution | 100% offline, zero network requests or external cloud APIs | M1 | survey / spec |
| 9 | Document Representation API | `extract_document_representation(path)` -> `(content_hash, preview, length)` | M1 | survey / spec |
| 10 | Exact Normalized Match | MatchType `CONTENT_NEAR_DUPLICATE` with similarity 1.0 on identical hash | M1 | survey / spec |
| 11 | Token Jaccard Similarity | Compute token Jaccard similarity >= 0.90 for near-duplicate documents | M1 | survey / spec |
| 12 | Ratio-Based Fast Pruning | Mathematical $O(1)$ pruning if $\min(\|A\|, \|B\|) / \max(\|A\|, \|B\|) < 0.90$ | M1 | survey / spec |
| 13 | Multi-Way DSU Clustering | Disjoint Set Union clustering of duplicate/near-duplicate document groups | M1 | survey / spec |
| 14 | Plugin Lifecycle & Introspection | `is_available()` returning dependency status (`pypdf`) and version | M1 | survey / spec |
| 15 | Plugin Registry & CLI Integration | Registered in `cli.py:discover_plugins()`, listed in `clairvoy plugins list` | M2 | survey / spec |
| 16 | Pipeline Tiered Pruning Integration | Registered in `pipeline.py:__init__()`, short-circuit candidate pruning | M2 | survey / spec |
| 17 | Keeper Strategy & Scan Summary | Expose `content_duplicate_groups` in `ScanSummary` and CLI scan summary | M2 | survey / spec |
| 18 | Dependency Registration | Add `pypdf>=5.0.0` to `dependencies` in `pyproject.toml` | M2 | survey / spec |
| 19 | Documentation Synchronization | Update `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/PLUGINS.md` | M3 | survey / spec |
| 20 | E2E Regression & Adversarial Hardening | Pass 100% E2E test suite (Tiers 1-4) and Phase 2 white-box adversarial stress | M4 | survey / spec |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | DocumentTextMatcherPlugin Core Engine & Parsers | Implement `clairvoy/plugins/document_matcher.py` with all extractors, memory bounds, normalization, Jaccard similarity, DSU clustering, and unit tests in `tests/test_document_matcher.py` | none | DONE |
| M2 | Pipeline, CLI & Dependency Integration | Register in `clairvoy/engines/pipeline.py`, `clairvoy/cli.py`, add `content_duplicate_groups` in `clairvoy/core/models.py`, update `pyproject.toml` | M1 | DONE |
| M3 | Documentation Synchronization | Update `AGENTS.md`, `docs/ARCHITECTURE.md`, and `docs/PLUGINS.md` with Tier 5 / Priority 50 specs and ASCII architecture | M2 | DONE |
| M4 | Final Milestone: 100% E2E Pass & Adversarial Hardening | Pass 100% E2E test suite from E2E Testing Track (`TEST_READY.md`), then run Phase 2 Challenger adversarial coverage hardening | M1, M2, M3 | DONE |

## Interface Contracts
### `DocumentTextMatcherPlugin` Contract
- Module: `file:///home/shubhamshah207/clairvoy/clairvoy/plugins/document_matcher.py`
- Base Class: `BaseMatcherPlugin` in `file:///home/shubhamshah207/clairvoy/clairvoy/core/plugins.py`
- Constants:
  - `SUPPORTED_DOCUMENT_EXTENSIONS: set[str] = {".pdf", ".docx", ".pptx", ".odt", ".csv", ".tsv"}`
- Attributes:
  - `plugin_id: str = "document_matcher"`
  - `display_name: str = "Document Text & Tabular Matcher"`
  - `version: str = "0.1.0"`
  - `author: str = "Clairvoy Team"`
  - `description: str = "Discovers identical and near-duplicate documents across .pdf, .docx, .pptx, .odt, .csv, and .tsv"`
  - `match_type: MatchType = MatchType.CONTENT_NEAR_DUPLICATE`
  - `priority_order: int = 50`
- Public Methods:
  - `is_available() -> tuple[bool, str]`
  - `filter_supported(files: list[FileEntry]) -> list[FileEntry]`
  - `extract_document_representation(path: str) -> tuple[str, str, int] | None`
  - `find_duplicates(candidates: list[FileEntry], all_indexed_files: list[FileEntry], context: dict[str, Any] | None = None) -> list[DuplicateCluster]`

### `ScanSummary` Contract
- Attribute added: `content_duplicate_groups: int = 0`

## Code Layout
- Implementation:
  - `file:///home/shubhamshah207/clairvoy/clairvoy/plugins/document_matcher.py` (New file)
  - `file:///home/shubhamshah207/clairvoy/clairvoy/engines/pipeline.py` (Integration)
  - `file:///home/shubhamshah207/clairvoy/clairvoy/cli.py` (Integration)
  - `file:///home/shubhamshah207/clairvoy/clairvoy/core/models.py` (Model extension)
  - `file:///home/shubhamshah207/clairvoy/pyproject.toml` (Dependency)
- Testing:
  - `file:///home/shubhamshah207/clairvoy/tests/test_document_matcher.py` (Unit & format tests)
  - `file:///home/shubhamshah207/clairvoy/tests/test_document_e2e.py` (E2E & edge-case suite)
- Documentation:
  - `file:///home/shubhamshah207/clairvoy/AGENTS.md`
  - `file:///home/shubhamshah207/clairvoy/docs/ARCHITECTURE.md`
  - `file:///home/shubhamshah207/clairvoy/docs/PLUGINS.md`
