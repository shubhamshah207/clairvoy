# DISPATCH — worker_m1

## Objective
Implement Milestone M1: `DocumentTextMatcherPlugin` core engine, format extractors, memory safety caps, normalization, token Jaccard similarity, and DSU clustering in `clairvoy/plugins/document_matcher.py`. Fix and verify unit tests in `tests/test_document_matcher.py`.

## Authoritative User Request & Scope
- `file:///home/shubhamshah207/clairvoy/.agents/ORIGINAL_REQUEST.md` (Read this first!)
- `file:///home/shubhamshah207/clairvoy/.agents/orchestrator_1/PROJECT.md`
- Survey blueprints:
  - `file:///home/shubhamshah207/clairvoy/.agents/explorer_survey_1/handoff.md`
  - `file:///home/shubhamshah207/clairvoy/.agents/explorer_survey_2/handoff.md`
  - `file:///home/shubhamshah207/clairvoy/.agents/spec_miner_survey/handoff.md`

## File Ownership
- YOU EXCLUSIVELY OWN:
  - `file:///home/shubhamshah207/clairvoy/clairvoy/plugins/document_matcher.py`
  - `file:///home/shubhamshah207/clairvoy/tests/test_document_matcher.py`
- DO NOT edit pipeline.py, cli.py, or other files yet (assigned to Milestone M2).

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Detailed Requirements
1. Class `DocumentTextMatcherPlugin(BaseMatcherPlugin)` in `clairvoy/plugins/document_matcher.py`:
   - `plugin_id = "document_matcher"`
   - `display_name = "Document Text & Tabular Matcher"`
   - `version = "0.1.0"`
   - `author = "Clairvoy Team"`
   - `description = "Discovers identical and near-duplicate documents across .pdf, .docx, .pptx, .odt, .csv, and .tsv"`
   - `match_type = MatchType.CONTENT_NEAR_DUPLICATE`
   - `priority_order = 50`
   - `SUPPORTED_DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".pptx", ".odt", ".csv", ".tsv"}`
2. Methods:
   - `is_available() -> tuple[bool, str]`: checks if `pypdf` is available, returning `(True, f"pypdf {pypdf.__version__} available")`.
   - `filter_supported(files: list[FileEntry]) -> list[FileEntry]`: filters candidates by `SUPPORTED_DOCUMENT_EXTENSIONS` and `size_bytes > 0`.
   - `extract_document_representation(path: str) -> tuple[str, str, int] | None`: returns `(content_hash, preview, length)`.
   - Format extractors:
     - PDF: pure-Python `pypdf.PdfReader` up to 50 pages (`reader.pages[:50]`). Handle encrypted/corrupted/empty PDFs gracefully returning `None`.
     - DOCX: `zipfile.ZipFile`, read `word/document.xml`, parse with `xml.etree.ElementTree`, extract `<w:t>` text runs.
     - PPTX: `zipfile.ZipFile`, read `ppt/slides/slide*.xml` with natural slide sorting `re.search(r'slide(\d+)\.xml$', name)`, extract `<a:t>`.
     - ODT: `zipfile.ZipFile`, read `content.xml`, extract text via `root.itertext()`.
     - CSV/TSV: Delimiter detection (`csv.Sniffer` with fallback to `,` or `\t`), `encoding="utf-8-sig"`, strip whitespace per cell, sort data rows canonically (`sorted(data_rows, key=tuple)`), compute permutation-invariant SHA-256 content digest.
   - Memory bounds:
     - Cap file read buffer at 25 MB (`25 * 1024 * 1024`).
     - Cap extracted text at 50,000 words (`" ".join(words[:50000])`).
     - 100% offline, local-first.
   - Similarity & Clustering:
     - Exact match: identical content digest -> similarity 1.0.
     - Near-duplicate match: token Jaccard similarity >= 0.90 (`len(A & B) / len(A | B)`).
     - $O(1)$ pruning: skip if `min(len(A), len(B)) / max(len(A), len(B)) < 0.90`.
     - Cluster grouping using Disjoint Set Union (DSU) or connected components. Return `list[DuplicateCluster]`.
3. Verification:
   - Run `/home/shubhamshah207/miniconda3/bin/pytest tests/test_document_matcher.py -v`
   - Run `/home/shubhamshah207/miniconda3/bin/ruff check .` (and fix any import order issues)
   - Ensure all tests in `tests/test_document_matcher.py` pass.

## Deliverable
Write your completion report to `file:///home/shubhamshah207/clairvoy/.agents/worker_m1/handoff.md` and notify me via send_message.

## 2026-09-14T05:49:40Z
You are worker_m1. Your working directory is file:///home/shubhamshah207/clairvoy/.agents/worker_m1. Read file:///home/shubhamshah207/clairvoy/.agents/ORIGINAL_REQUEST.md and file:///home/shubhamshah207/clairvoy/.agents/worker_m1/DISPATCH.md. Implement DocumentTextMatcherPlugin in clairvoy/plugins/document_matcher.py, fix tests/test_document_matcher.py, run tests and ruff lint, and report results in file:///home/shubhamshah207/clairvoy/.agents/worker_m1/handoff.md. Notify me via send_message when done.
