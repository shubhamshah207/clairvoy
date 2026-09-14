# Document Deduplication (Phase 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add content-aware deduplication for `.pdf`, `.docx`, `.pptx`, `.odt`, `.csv`, and `.tsv` files to Clairvoy via a new `DocumentTextMatcherPlugin`.

**Architecture:** A lightweight extractor pipeline leveraging pure-Python `pypdf`, `zipfile` XML parsing for Office documents, and `csv` row normalization. Matches documents via normalized text hashes and token Jaccard similarity without cloud calls.

**Tech Stack:** Python 3.12, `pypdf`, `xml.etree.ElementTree`, `zipfile`, `csv`, `pytest`, `ruff`.

**Spec:** [`docs/superpowers/specs/2026-09-13-document-deduplication-design.md`](file:///home/shubhamshah207/clairvoy/docs/superpowers/specs/2026-09-13-document-deduplication-design.md)

## Global Constraints

- Python 3.12+ type annotations (`T | None`, `list[T]`, `dict[K, V]`).
- 100% offline and local execution; zero unauthenticated external cloud calls.
- Memory safe: streams and text buffers capped at 25 MB / 50,000 words to prevent memory exhaustion on giant data dumps.
- Pass `/home/shubhamshah207/miniconda3/bin/pytest -v` and `/home/shubhamshah207/miniconda3/bin/ruff check .`.
- Maintain [`AGENTS.md`](file:///home/shubhamshah207/clairvoy/AGENTS.md).

---

### Task 1: Expand MatchType Schema (`clairvoy/core/models.py`)

**Files:**
- Modify: `clairvoy/core/models.py:11-15`
- Test: `tests/test_plugin_system.py`

**Interfaces:**
- Produces: `MatchType.CONTENT_NEAR_DUPLICATE = "CONTENT_NEAR_DUPLICATE"`.

- [ ] **Step 1: Write test in `tests/test_plugin_system.py`**
Verify `MatchType.CONTENT_NEAR_DUPLICATE` exists and can serialize in `DuplicateCluster`.

- [ ] **Step 2: Update `clairvoy/core/models.py`**
Add `CONTENT_NEAR_DUPLICATE = "CONTENT_NEAR_DUPLICATE"` to `MatchType`.

- [ ] **Step 3: Run pytest and commit**
`pytest tests/test_plugin_system.py -v`

---

### Task 2: Implement DocumentTextMatcherPlugin (`clairvoy/plugins/document_matcher.py`)

**Files:**
- Create: `clairvoy/plugins/document_matcher.py`
- Test: `tests/test_document_matcher.py`

**Interfaces:**
- Produces: `DocumentTextMatcherPlugin(BaseMatcherPlugin)` with `plugin_id = "document_matcher"`, priority `50`.

- [ ] **Step 1: Write failing unit tests in `tests/test_document_matcher.py`**
  - Test `.pdf` text extraction and matching.
  - Test `.docx` and `.pptx` text extraction and matching.
  - Test `.csv` and `.tsv` permutation-invariant row matching.
  - Test graceful handling of corrupted documents.

- [ ] **Step 2: Run test to verify it fails**
`pytest tests/test_document_matcher.py -v`

- [ ] **Step 3: Write `DocumentTextMatcherPlugin` implementation**
Implement extraction methods for PDF, DOCX, PPTX, ODT, CSV, TSV and normalized token clustering.

- [ ] **Step 4: Run test to verify it passes**
`pytest tests/test_document_matcher.py -v`

- [ ] **Step 5: Commit**
`git add clairvoy/plugins/document_matcher.py tests/test_document_matcher.py && git commit -m "feat(plugins): add DocumentTextMatcherPlugin for PDF, Office, and Tabular formats"`

---

### Task 3: Pipeline & CLI Registration

**Files:**
- Modify: `clairvoy/cli.py`
- Modify: `clairvoy/engines/pipeline.py`
- Modify: `pyproject.toml` (add `pypdf>=5.0.0`)

- [ ] **Step 1: Update `pyproject.toml`**
Add `pypdf>=5.0.0` to dependencies.

- [ ] **Step 2: Register plugin in `cli.py` and `pipeline.py`**
Register `DocumentTextMatcherPlugin()` in default plugin suite.

- [ ] **Step 3: Run tests and commit**
`pytest tests/test_pipeline.py -v`

---

### Task 4: Documentation & Agent Blueprint Updates

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/PLUGINS.md`

- [ ] **Step 1: Update documentation**
Document `DocumentTextMatcherPlugin` (Tier 4 / Priority 50) and supported document formats.

- [ ] **Step 2: Run full test suite & linter**
`pytest -v` and `ruff check .`

- [ ] **Step 3: Commit**
`git add AGENTS.md docs/ pyproject.toml && git commit -m "docs: document DocumentTextMatcherPlugin and update format matrices"`
