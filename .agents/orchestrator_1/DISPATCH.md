# DISPATCH Log

## 2026-09-14T05:43:16Z

You are the Project Orchestrator for Clairvoy.

Your working directory is: `/home/shubhamshah207/clairvoy/.agents/orchestrator_1`
The authoritative user request is recorded at: `/home/shubhamshah207/clairvoy/.agents/ORIGINAL_REQUEST.md`

Your mission:
Lead the end-to-end execution to build production-grade content-aware deduplication for document and tabular file formats (.pdf, .docx, .pptx, .csv, .tsv) in Clairvoy, discovering identical and near-duplicate documents across re-saved exports, drafts, and permuted datasets.

Requirements summary:
1. R1: Implement `DocumentTextMatcherPlugin` (priority order 50, match type `CONTENT_NEAR_DUPLICATE`) supporting `.pdf`, `.docx`, `.pptx`, `.odt`, `.csv`, and `.tsv`.
   - Pure-Python `pypdf.PdfReader` up to 50 pages for PDF.
   - Extract body text from Office documents (`.docx`, `.pptx`, `.odt`) by inspecting internal XML streams (`word/document.xml`, `ppt/slides/slide*.xml`, `content.xml`) in memory via standard library `zipfile`.
   - Normalize tabular data (`.csv`, `.tsv`) by parsing headers, sorting rows, and generating permutation-invariant content digests.
   - Group candidate files into duplicate clusters based on normalized text hashes and token similarity (>= 0.90).
2. R2: Pluggable Pipeline & CLI Integration:
   - Register `DocumentTextMatcherPlugin` in `clairvoy/cli.py` and `clairvoy/engines/pipeline.py`.
   - Add `pypdf>=5.0.0` to project dependencies in `pyproject.toml`.
   - Ensure candidate files discovered by `pipeline.py` are routed through the matcher and output to summary reports.
3. R3: Offline Execution & Memory Bounds:
   - 100% offline, local-first execution with zero external network or unauthenticated cloud API calls.
   - Memory safe: stream readers cap buffer sizes at 25 MB / 50,000 words.
   - Graceful degradation: corrupted/unreadable documents return fallback values without crashing concurrent processing.

Verification & Quality standards:
- All unit and integration tests must pass: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_document_matcher.py -v` and `/home/shubhamshah207/miniconda3/bin/pytest -v`
- Static linter must pass with 0 errors: `/home/shubhamshah207/miniconda3/bin/ruff check .`
- CLI check: `/home/shubhamshah207/miniconda3/bin/clairvoy plugins list` must list and enable `DocumentTextMatcherPlugin`.
- Update and synchronize documentation: `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/PLUGINS.md`.
- All visual diagrams in chat, logs, and comments must be clean ASCII art.
- File references in summaries must use clickable file:// markdown links.
