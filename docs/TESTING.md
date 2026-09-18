# Clairvoy Testing & Verification Guide

This document outlines the testing conventions, fixtures, fast feedback loops, and linting standards for Clairvoy.

---

## 1. Environment & Fast Feedback Loop

Tests are run using `pytest` with `pytest-asyncio`. Python 3.12+ in the project conda environment must be used.

```bash
# Run entire test suite (fast execution under 4 seconds)
/home/shubhamshah207/miniconda3/bin/pytest -v

# Run only matcher plugin tests
/home/shubhamshah207/miniconda3/bin/pytest tests/test_matcher_plugins.py -v

# Run only pipeline integration tests
/home/shubhamshah207/miniconda3/bin/pytest tests/test_pipeline.py -v

# Run documentation & asset integrity tests
/home/shubhamshah207/miniconda3/bin/pytest tests/test_docs_integrity.py -v
```

---

## 2. Test Suite Structure

- [`tests/test_plugin_system.py`](file:///home/shubhamshah207/clairvoy/tests/test_plugin_system.py): Plugin contracts, registration, dynamic directory loading, entry points, thread safety.
- [`tests/test_matcher_plugins.py`](file:///home/shubhamshah207/clairvoy/tests/test_matcher_plugins.py): ExactHashMatcher and ArchiveInspector plugins.
- [`tests/test_media_matchers.py`](file:///home/shubhamshah207/clairvoy/tests/test_media_matchers.py): PhotoVision (DINOv2) and VideoKeyframe matcher plugins.
- [`tests/test_action_plugins.py`](file:///home/shubhamshah207/clairvoy/tests/test_action_plugins.py): SafeQuarantine and Hardlink action plugins.
- [`tests/test_pipeline.py`](file:///home/shubhamshah207/clairvoy/tests/test_pipeline.py): End-to-end deduplication pipeline, short-circuit pruning, composite keeper scoring.
- [`tests/test_cli_plugins.py`](file:///home/shubhamshah207/clairvoy/tests/test_cli_plugins.py): Typer CLI commands (`plugins list`, `plugins info`, `--enable-plugin`, `--action`).
- [`tests/test_security.py`](file:///home/shubhamshah207/clairvoy/tests/test_security.py): Enterprise security tests: path traversal, root safety, shell argument escaping.
- [`tests/test_storage_engine.py`](file:///home/shubhamshah207/clairvoy/tests/test_storage_engine.py): Multi-threaded file scanner, 128KB QuickHash, SHA-256 digests.
- [`tests/test_vision_engine.py`](file:///home/shubhamshah207/clairvoy/tests/test_vision_engine.py): ONNX Runtime embedding inference, cosine distance, DSU clustering.
- [`tests/test_document_matcher.py`](file:///home/shubhamshah207/clairvoy/tests/test_document_matcher.py): Tier 5 document text and tabular row-permutation matching (.pdf, .docx, .csv, .tsv).
- [`tests/test_run_manager.py`](file:///home/shubhamshah207/clairvoy/tests/test_run_manager.py): Persistent RunManager, history recording, and report auto-discovery.
- [`tests/test_cli_runs.py`](file:///home/shubhamshah207/clairvoy/tests/test_cli_runs.py): CLI commands `clairvoy runs list`, `clairvoy runs show`, and UI run preloading flags.
- [`tests/test_web_api.py`](file:///home/shubhamshah207/clairvoy/tests/test_web_api.py): FastAPI backend endpoints, thumbnail security, scan triggers, runs listing, and report loading.
- [`tests/test_docs_integrity.py`](file:///home/shubhamshah207/clairvoy/tests/test_docs_integrity.py): Verification of README, screenshots, AGENTS.md, symlinks, diagrams.

---

## 3. Linting & Formatting Standards

Linting must pass with 0 errors or warnings before any pull request or commit.

```bash
# Check code style & lints
/home/shubhamshah207/miniconda3/bin/ruff check .

# Automatically fix fixable lints
/home/shubhamshah207/miniconda3/bin/ruff check --fix .
```

---

## 4. Testing Invariants

1. **Zero-Destruction**: Tests must use temporary workspaces (`tmp_path` fixture) and never operate on real user files.
2. **Local Execution**: All tests must pass completely offline without internet connectivity.
3. **Graceful Degradation**: Video and ML tests must verify graceful fallbacks when optional native libraries or models are absent.
