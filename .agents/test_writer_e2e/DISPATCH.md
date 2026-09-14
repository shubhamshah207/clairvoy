# DISPATCH — test_writer_e2e

## Objective
Design and implement a comprehensive opaque-box E2E test suite in `tests/test_document_e2e.py` covering all 4 tiers outlined in `TEST_INFRA.md`. Publish `TEST_READY.md` upon completion.

## Authoritative User Request & Scope
- `file:///home/shubhamshah207/clairvoy/.agents/ORIGINAL_REQUEST.md` (Read this first!)
- `file:///home/shubhamshah207/clairvoy/.agents/orchestrator_1/PROJECT.md`
- `file:///home/shubhamshah207/clairvoy/.agents/orchestrator_1/TEST_INFRA.md`
- `file:///home/shubhamshah207/clairvoy/.agents/spec_miner_survey/handoff.md`

## File Ownership
- YOU EXCLUSIVELY OWN:
  - `file:///home/shubhamshah207/clairvoy/tests/test_document_e2e.py`
  - `file:///home/shubhamshah207/clairvoy/TEST_READY.md` (publish when tests are written)
- DO NOT edit `clairvoy/plugins/document_matcher.py` or existing test files.

## Mandatory Test Suite Design (4 Tiers)
1. **Tier 1 — Feature Coverage (>=5 per feature)**:
   - PDF deduplication
   - DOCX deduplication
   - PPTX deduplication
   - ODT deduplication
   - CSV / TSV row-permuted deduplication
   - Token Jaccard near-duplicate deduplication (>= 0.90)
2. **Tier 2 — Boundary & Corner Cases (>=5 per feature)**:
   - Corrupted/truncated ZIP and PDF
   - Password encrypted / zero-byte documents
   - PPTX slide natural ordering (1..10)
   - CSV delimiter sniffing (comma, tab, semicolon) and UTF-8 BOM
   - Buffer caps (25MB) and word truncation (50,000 words)
   - Token similarity edge cases (exact 0.90, 0.89 rejection, 0.95 pass)
3. **Tier 3 — Cross-Feature Interactions**:
   - Multi-format matches (e.g. identical text across DOCX and ODT)
   - Row-shuffled CSV vs TSV
   - Multi-way cluster groupings (3+ files in a cluster)
4. **Tier 4 — Real-World Application Scenarios**:
   - Rebrand document revision draft vs final
   - Permuted sales export dataset
   - Presentation revision with minor slide edits
   - Directory scan with mixed valid and corrupted documents

## Coordination: Publish `TEST_READY.md`
When `tests/test_document_e2e.py` is written and syntax-checked, publish `file:///home/shubhamshah207/clairvoy/TEST_READY.md` with:
- Test runner command (`/home/shubhamshah207/miniconda3/bin/pytest tests/test_document_e2e.py -v`)
- Coverage summary across Tiers 1-4
- Feature checklist

## Deliverable
Write your completion report to `file:///home/shubhamshah207/clairvoy/.agents/test_writer_e2e/handoff.md` and notify me via send_message.

## 2026-09-14T05:49:40Z
You are test_writer_e2e. Your working directory is file:///home/shubhamshah207/clairvoy/.agents/test_writer_e2e. Read file:///home/shubhamshah207/clairvoy/.agents/ORIGINAL_REQUEST.md and file:///home/shubhamshah207/clairvoy/.agents/test_writer_e2e/DISPATCH.md. Author the comprehensive opaque-box E2E test suite in tests/test_document_e2e.py covering Tiers 1-4. Publish file:///home/shubhamshah207/clairvoy/TEST_READY.md when done, report results in file:///home/shubhamshah207/clairvoy/.agents/test_writer_e2e/handoff.md, and notify me via send_message.

