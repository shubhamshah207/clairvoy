# DISPATCH — worker_m2

## Objective
Implement Milestone M2: Pluggable Pipeline, CLI Integration & Dependency Registration.

## Inputs & Authoritative Specs
- `file:///home/shubhamshah207/clairvoy/.agents/ORIGINAL_REQUEST.md` (Read this first!)
- `file:///home/shubhamshah207/clairvoy/.agents/orchestrator_1/PROJECT.md`
- `file:///home/shubhamshah207/clairvoy/.agents/explorer_survey_2/handoff.md`

## File Ownership
- YOU EXCLUSIVELY OWN:
  - `file:///home/shubhamshah207/clairvoy/clairvoy/core/models.py`
  - `file:///home/shubhamshah207/clairvoy/clairvoy/engines/pipeline.py`
  - `file:///home/shubhamshah207/clairvoy/clairvoy/cli.py`
  - `file:///home/shubhamshah207/clairvoy/pyproject.toml`
  - `file:///home/shubhamshah207/clairvoy/tests/test_pipeline.py`
- DO NOT modify `clairvoy/plugins/document_matcher.py` (M1 complete and approved) or `AGENTS.md` (reserved for M3).

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Detailed Tasks
1. `clairvoy/core/models.py`:
   - Add `content_duplicate_groups: int = 0` to `ScanSummary` model.
2. `pyproject.toml`:
   - Add `"pypdf>=5.0.0"` to `dependencies = [...]`.
3. `clairvoy/engines/pipeline.py`:
   - Import `DocumentTextMatcherPlugin` from `clairvoy.plugins.document_matcher`.
   - In `DeduplicationPipeline.__init__`: register `self.registry.register(DocumentTextMatcherPlugin())` in default matchers suite.
   - In `DeduplicationPipeline.run_scan`:
     - Count `content_duplicate_groups = sum(1 for c in all_clusters if c.match_type == MatchType.CONTENT_NEAR_DUPLICATE)` and pass to `ScanSummary`.
     - In category assignment: ensure entries in `CONTENT_NEAR_DUPLICATE` clusters have `e.category = ImageCategory.DOCUMENT` if category is `ImageCategory.FILE`.
4. `clairvoy/cli.py`:
   - Import `DocumentTextMatcherPlugin` from `clairvoy.plugins.document_matcher`.
   - In `discover_plugins()`: include `DocumentTextMatcherPlugin()` in `default_plugins`.
   - In `scan` command: display ` • Document & Tabular Clusters: {summary.content_duplicate_groups}` in summary output.
5. Tests:
   - In `tests/test_pipeline.py`: ensure `assert "document_matcher" in matcher_ids` passes in default population test.
   - Verify CLI list command: `/home/shubhamshah207/miniconda3/bin/clairvoy plugins list` outputs `document_matcher` with Priority 50, Enabled yes, Available yes.
   - Run `/home/shubhamshah207/miniconda3/bin/pytest -v` (all tests must pass).
   - Run `/home/shubhamshah207/miniconda3/bin/ruff check .` (0 errors).

## Deliverable
Write your handoff report to `file:///home/shubhamshah207/clairvoy/.agents/worker_m2/handoff.md` and notify me via send_message.

## 2026-09-14T05:58:55Z
You are worker_m2. Your working directory is file:///home/shubhamshah207/clairvoy/.agents/worker_m2. Read file:///home/shubhamshah207/clairvoy/.agents/ORIGINAL_REQUEST.md and file:///home/shubhamshah207/clairvoy/.agents/worker_m2/DISPATCH.md. Implement Milestone M2 (register DocumentTextMatcherPlugin in pipeline.py, cli.py, models.py, pyproject.toml, and update pipeline tests). Run pytest and ruff check, verify CLI plugins list, and report results in file:///home/shubhamshah207/clairvoy/.agents/worker_m2/handoff.md. Notify me via send_message when done.
