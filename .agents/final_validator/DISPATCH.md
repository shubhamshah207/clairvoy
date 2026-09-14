# DISPATCH — final_validator

## Objective
Execute final end-to-end repository validation across all requirements, test suites, CLI tools, and linters for Clairvoy Document & Tabular Deduplication.

## Inputs
- Authoritative Request: `file:///home/shubhamshah207/clairvoy/.agents/ORIGINAL_REQUEST.md` (Read this first!)
- Project Scope: `file:///home/shubhamshah207/clairvoy/.agents/orchestrator_1/PROJECT.md`
- Test Ready Manifest: `file:///home/shubhamshah207/clairvoy/TEST_READY.md`

## Verification Checks to Execute
1. Unit test suite:
   ```bash
   /home/shubhamshah207/miniconda3/bin/pytest tests/test_document_matcher.py -v
   ```
2. Opaque-box E2E test suite (Tiers 1-4):
   ```bash
   /home/shubhamshah207/miniconda3/bin/pytest tests/test_document_e2e.py -v
   ```
3. Adversarial stress test suites (Tier 5):
   ```bash
   /home/shubhamshah207/miniconda3/bin/pytest tests/test_adversarial_m1.py tests/test_adversarial_m1_2.py -v
   ```
4. Full repository regression suite:
   ```bash
   /home/shubhamshah207/miniconda3/bin/pytest -v
   ```
5. Static linter:
   ```bash
   /home/shubhamshah207/miniconda3/bin/ruff check .
   ```
6. CLI tool verification:
   ```bash
   /home/shubhamshah207/miniconda3/bin/clairvoy plugins list
   /home/shubhamshah207/miniconda3/bin/clairvoy plugins info document_matcher
   ```
7. Acceptance criteria checklist verification from `ORIGINAL_REQUEST.md`:
   - [ ] DocumentTextMatcherPlugin accurately identifies identical text in .docx and .pptx documents with differing metadata or timestamps.
   - [ ] DocumentTextMatcherPlugin clusters reordered .csv / .tsv files with identical data rows into duplicate clusters.
   - [ ] DocumentTextMatcherPlugin extracts text from .pdf documents and detects duplicates.
   - [ ] Malformed or corrupted document files are handled gracefully without aborting directory scans.
   - [ ] DocumentTextMatcherPlugin is listed and enabled in clairvoy plugins list.
   - [ ] All unit and integration tests pass with 100% success.
   - [ ] Zero lint or formatting errors.
   - [ ] Documentation (AGENTS.md, docs/ARCHITECTURE.md, docs/PLUGINS.md) is kept updated and synchronized.

## Deliverable
Write your final verification report to `file:///home/shubhamshah207/clairvoy/.agents/final_validator/handoff.md` and notify me via send_message.

## 2026-09-14T06:11:30Z
You are final_validator. Your working directory is file:///home/shubhamshah207/clairvoy/.agents/final_validator. Read file:///home/shubhamshah207/clairvoy/.agents/ORIGINAL_REQUEST.md and file:///home/shubhamshah207/clairvoy/.agents/final_validator/DISPATCH.md. Execute the complete verification protocol across all test suites (unit, E2E, adversarial, full regression), CLI tools, linters, and the acceptance criteria checklist. Report your findings and explicit verdict in file:///home/shubhamshah207/clairvoy/.agents/final_validator/handoff.md and notify me via send_message when done.

