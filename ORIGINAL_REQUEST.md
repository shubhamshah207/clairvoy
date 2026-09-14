# Original User Request

## 2026-09-14T05:42:49Z

Build production-grade content-aware deduplication for document and tabular file formats (.pdf, .docx, .pptx, .csv, .tsv) in Clairvoy, discovering identical and near-duplicate documents across re-saved exports, drafts, and permuted datasets.

Working directory: /home/shubhamshah207/clairvoy
Integrity mode: development

## Requirements

### R1. Document Text & Tabular Matcher Plugin
Implement `DocumentTextMatcherPlugin` (priority order 50, match type `CONTENT_NEAR_DUPLICATE`) supporting `.pdf`, `.docx`, `.pptx`, `.odt`, `.csv`, and `.tsv`.
- Extract text content from PDF documents (via pure-Python `pypdf.PdfReader` up to 50 pages).
- Extract body text from Office documents (`.docx`, `.pptx`, `.odt`) by inspecting internal XML streams (`word/document.xml`, `ppt/slides/slide*.xml`, `content.xml`) in memory via standard library `zipfile`.
- Normalize tabular data (`.csv`, `.tsv`) by parsing headers, sorting rows, and generating permutation-invariant content digests.
- Group candidate files into duplicate clusters based on normalized text hashes and token similarity (>= 0.90).

### R2. Pluggable Pipeline & CLI Integration
- Register `DocumentTextMatcherPlugin` in `clairvoy/cli.py` and `clairvoy/engines/pipeline.py`.
- Add `pypdf>=5.0.0` to project dependencies in `pyproject.toml`.
- Ensure candidate files discovered by `pipeline.py` are routed through the matcher and output to summary reports.

### R3. Offline Execution & Memory Bounds
- 100% offline, local-first execution with zero external network or unauthenticated cloud API calls.
- Memory safe: stream readers must cap buffer sizes at 25 MB / 50,000 words to avoid memory exhaustion on massive data dumps.
- Graceful degradation: corrupted or unreadable documents must return fallback values without crashing concurrent processing.

## Verification Resources

- Test suite: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_document_matcher.py -v`
- Full regression suite: `/home/shubhamshah207/miniconda3/bin/pytest -v`
- Static linter: `/home/shubhamshah207/miniconda3/bin/ruff check .`
- Architecture & documentation guidelines: `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/PLUGINS.md`

## Acceptance Criteria

### Functionality & Accuracy
- [ ] `DocumentTextMatcherPlugin` accurately identifies identical text in `.docx` and `.pptx` documents with differing metadata or timestamps.
- [ ] `DocumentTextMatcherPlugin` clusters reordered `.csv` / `.tsv` files with identical data rows into duplicate clusters.
- [ ] `DocumentTextMatcherPlugin` extracts text from `.pdf` documents and detects duplicates.
- [ ] Malformed or corrupted document files are handled gracefully without aborting directory scans.

### Pipeline & Code Quality
- [ ] `DocumentTextMatcherPlugin` is listed and enabled in `/home/shubhamshah207/miniconda3/bin/clairvoy plugins list`.
- [ ] All unit and integration tests pass with 100% success (`pytest -v`).
- [ ] Zero lint or formatting errors (`ruff check .`).
- [ ] Documentation (`AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/PLUGINS.md`) is kept updated and synchronized.
