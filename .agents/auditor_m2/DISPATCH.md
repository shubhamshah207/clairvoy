# DISPATCH — auditor_m2

## Objective
Perform forensic integrity verification of Milestone M2 (`clairvoy/engines/pipeline.py`, `clairvoy/cli.py`, `clairvoy/core/models.py`, and `pyproject.toml`).

## Inputs
- Authoritative Request: `file:///home/shubhamshah207/clairvoy/.agents/ORIGINAL_REQUEST.md` (Read this first!)
- Worker M2 Handoff: `file:///home/shubhamshah207/clairvoy/.agents/worker_m2/handoff.md`

## Forensic Audit Checks (Zero Tolerance)
1. Static analysis:
   - Verify `DocumentTextMatcherPlugin` is genuinely registered in `clairvoy/engines/pipeline.py` and `clairvoy/cli.py`.
   - Verify `"pypdf>=5.0.0"` is present in `pyproject.toml`.
   - Ensure no hardcoded test values, facades, or test bypasses exist.
2. Runtime tracing & CLI validation:
   - Run `/home/shubhamshah207/miniconda3/bin/clairvoy plugins list` and verify the ASCII table output contains `document_matcher` with Priority 50.
   - Run `/home/shubhamshah207/miniconda3/bin/clairvoy plugins info document_matcher` and verify output.
   - Verify that `DeduplicationPipeline` executes `DocumentTextMatcherPlugin` dynamically when scanning documents.
3. Regression verification:
   - Run `/home/shubhamshah207/miniconda3/bin/pytest -v`.
   - Run `/home/shubhamshah207/miniconda3/bin/ruff check .`.

## Deliverable
In your handoff report (`file:///home/shubhamshah207/clairvoy/.agents/auditor_m2/handoff.md`), provide full forensic evidence and state an explicit binary verdict: `CLEAN` or `INTEGRITY VIOLATION`. Notify me via send_message.

## 2026-09-14T06:02:57Z
You are auditor_m2. Your working directory is file:///home/shubhamshah207/clairvoy/.agents/auditor_m2. Read file:///home/shubhamshah207/clairvoy/.agents/ORIGINAL_REQUEST.md and file:///home/shubhamshah207/clairvoy/.agents/auditor_m2/DISPATCH.md. Perform forensic integrity auditing on Milestone M2. Report your findings and explicit binary verdict (CLEAN or INTEGRITY VIOLATION) in file:///home/shubhamshah207/clairvoy/.agents/auditor_m2/handoff.md and notify me via send_message.

