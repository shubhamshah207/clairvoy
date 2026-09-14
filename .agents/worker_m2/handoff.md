# Milestone M2 Handoff Report: Pluggable Pipeline, CLI Integration & Dependency Registration

- **Author:** `worker_m2`
- **Working Directory:** [`/home/shubhamshah207/clairvoy/.agents/worker_m2`](file:///home/shubhamshah207/clairvoy/.agents/worker_m2)
- **Objective:** Implement Milestone M2 (register [`DocumentTextMatcherPlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/document_matcher.py) in [`pipeline.py`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/pipeline.py), [`cli.py`](file:///home/shubhamshah207/clairvoy/clairvoy/cli.py), [`models.py`](file:///home/shubhamshah207/clairvoy/clairvoy/core/models.py), [`pyproject.toml`](file:///home/shubhamshah207/clairvoy/pyproject.toml), and update pipeline tests in [`test_pipeline.py`](file:///home/shubhamshah207/clairvoy/tests/test_pipeline.py)).
- **Date:** 2026-09-14T06:03:00Z
- **Handoff Type:** Hard (Task Complete)

---

## 1. Observation

### 1.1 Requirements & Initial State
Per [`DISPATCH.md`](file:///home/shubhamshah207/clairvoy/.agents/worker_m2/DISPATCH.md) and [`ORIGINAL_REQUEST.md`](file:///home/shubhamshah207/clairvoy/.agents/ORIGINAL_REQUEST.md):
- Milestone M2 required:
  1. [`clairvoy/core/models.py`](file:///home/shubhamshah207/clairvoy/clairvoy/core/models.py): Add `content_duplicate_groups: int = 0` to [`ScanSummary`](file:///home/shubhamshah207/clairvoy/clairvoy/core/models.py).
  2. [`pyproject.toml`](file:///home/shubhamshah207/clairvoy/pyproject.toml): Add `"pypdf>=5.0.0"` to `dependencies`.
  3. [`clairvoy/engines/pipeline.py`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/pipeline.py): Import and register [`DocumentTextMatcherPlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/document_matcher.py) in default matchers suite, count `content_duplicate_groups`, and ensure `CONTENT_NEAR_DUPLICATE` members get `category = ImageCategory.DOCUMENT`.
  4. [`clairvoy/cli.py`](file:///home/shubhamshah207/clairvoy/clairvoy/cli.py): Import and include [`DocumentTextMatcherPlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/document_matcher.py) in `discover_plugins()` default plugins, and display ` • Document & Tabular Clusters: {summary.content_duplicate_groups}` in `scan` summary output.
  5. [`tests/test_pipeline.py`](file:///home/shubhamshah207/clairvoy/tests/test_pipeline.py): Ensure `assert "document_matcher" in matcher_ids` passes in default population test and add integration tests.

### 1.2 Implemented Changes
The following modifications were executed strictly within the agent's owned files:

1. **[`clairvoy/core/models.py`](file:///home/shubhamshah207/clairvoy/clairvoy/core/models.py):**
   - Added `content_duplicate_groups: int = 0` to [`ScanSummary`](file:///home/shubhamshah207/clairvoy/clairvoy/core/models.py#L63) model to support serialization and CLI display.

2. **[`pyproject.toml`](file:///home/shubhamshah207/clairvoy/pyproject.toml):**
   - Appended `"pypdf>=5.0.0"` to `project.dependencies`.

3. **[`clairvoy/engines/pipeline.py`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/pipeline.py):**
   - Imported [`DocumentTextMatcherPlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/document_matcher.py) from `clairvoy.plugins.document_matcher`.
   - In [`DeduplicationPipeline.__init__`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/pipeline.py#L125), registered `self.registry.register(DocumentTextMatcherPlugin())` in the default matchers suite.
   - In [`DeduplicationPipeline.run_scan`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/pipeline.py#L305), ensured entries in `CONTENT_NEAR_DUPLICATE` clusters are categorized as `ImageCategory.DOCUMENT` when initial category is `ImageCategory.FILE`.
   - Counted `content_duplicate_groups = sum(1 for c in all_clusters if c.match_type == MatchType.CONTENT_NEAR_DUPLICATE)` and forwarded to [`ScanSummary`](file:///home/shubhamshah207/clairvoy/clairvoy/core/models.py#L63).

4. **[`clairvoy/cli.py`](file:///home/shubhamshah207/clairvoy/clairvoy/cli.py):**
   - Imported [`DocumentTextMatcherPlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/document_matcher.py).
   - Added `DocumentTextMatcherPlugin()` to `default_plugins` in [`discover_plugins()`](file:///home/shubhamshah207/clairvoy/clairvoy/cli.py#L52).
   - In `scan` command completion handler, added output line:
     `print(f" • Document & Tabular Clusters: {summary.content_duplicate_groups}")`.

5. **[`tests/test_pipeline.py`](file:///home/shubhamshah207/clairvoy/tests/test_pipeline.py):**
   - In `test_pipeline_default_registry_population`, added `assert "document_matcher" in matcher_ids`.
   - Added `test_pipeline_document_matcher_integration` verifying that permuted tabular data files (.csv) flow through the pipeline to Tier 5, generate a `CONTENT_NEAR_DUPLICATE` cluster, increment `content_duplicate_groups`, and set member categories to `ImageCategory.DOCUMENT`.

### 1.3 Execution Verifications & Tool Outputs

- **CLI Plugin List Command:**
  Command: `/home/shubhamshah207/miniconda3/bin/clairvoy plugins list`
  Output:
  ```
  +-------------------+---------+----------+---------+-----------+--------------------------------------------------------------------------------------------------+
  | ID                | Type    | Priority | Enabled | Available | Description                                                                                      |
  +-------------------+---------+----------+---------+-----------+--------------------------------------------------------------------------------------------------+
  | exact_hash        | Matcher | 10       | yes     | yes       | High-performance 2-stage hash matching via 128KB QuickHash and full SHA-256                      |
  | photo_vision      | Matcher | 20       | yes     | yes       | Local AI visual similarity clustering powered by Meta DINOv2 ONNX                                |
  | video_matcher     | Matcher | 30       | yes     | yes       | Matches video transcodes and duplicates via stream duration and sampled keyframes                |
  | archive_inspector | Matcher | 40       | yes     | yes       | Peeks inside ZIP and TAR central directories without extracting to match files on disk           |
  | document_matcher  | Matcher | 50       | yes     | yes       | Discovers identical and near-duplicate documents across .pdf, .docx, .pptx, .odt, .csv, and .tsv |
  | composite_keeper  | Keeper  | -        | yes     | yes       | Scores files based on filename cleanliness, directory seniority, and media resolution            |
  | hardlink          | Action  | -        | yes     | yes       | Replaces duplicates with hardlinks to the keeper inode for instant zero-space reclamation        |
  | quarantine        | Action  | -        | yes     | yes       | Safely isolates duplicate files into a quarantine directory with rollback manifest               |
  +-------------------+---------+----------+---------+-----------+--------------------------------------------------------------------------------------------------+
  ```

- **CLI Plugin Info Command:**
  Command: `/home/shubhamshah207/miniconda3/bin/clairvoy plugins info document_matcher`
  Output:
  ```
  Plugin Info: document_matcher
   • ID:          document_matcher
   • Type:        Matcher
   • Name:        Document Text & Tabular Matcher
   • Version:     0.1.0
   • Author:      Clairvoy Team
   • Available:   yes (pypdf 6.18.1 available)
   • Priority:    50
   • Enabled:     yes
   • Description: Discovers identical and near-duplicate documents across .pdf, .docx, .pptx, .odt, .csv, and .tsv
  ```

- **Pipeline Unit & Integration Tests:**
  Command: `/home/shubhamshah207/miniconda3/bin/pytest tests/test_pipeline.py -v`
  Output: `14 passed in 0.61s` (Exit code: 0).

- **Full Test Suite:**
  Command: `/home/shubhamshah207/miniconda3/bin/pytest -v`
  Output: `253 passed, 2 warnings in 8.19s` (Exit code: 0).

- **Static Linter Check:**
  Command: `/home/shubhamshah207/miniconda3/bin/ruff check .`
  Output: `All checks passed!` (Exit code: 0).

---

## 2. Logic Chain

```
+----------------------------------------------------------------------------------------------------+
|                                    TIERED MATCHER ARCHITECTURE                                     |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|                                       [Filesystem Scanner / All Files]                             |
|                                                      |                                             |
|                                                      v                                             |
|                                   +--------------------------------------+                         |
|                                   | Tier 1: ExactHashMatcherPlugin       | (Priority 10)           |
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

1. **Priority Ordering & Short-Circuit Pruning:**
   - As observed in Section 1.3, [`DocumentTextMatcherPlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/document_matcher.py) is registered at `priority_order = 50`.
   - Files with identical byte hashes are caught by Tier 1 (`exact_hash`, priority 10) and pruned from downstream matching via `matched_paths`.
   - Remaining un-matched candidates are routed to Tier 5 if their extensions match `.pdf`, `.docx`, `.pptx`, `.odt`, `.csv`, or `.tsv`.
2. **Schema & Model Consistency:**
   - Setting `content_duplicate_groups: int = 0` in [`ScanSummary`](file:///home/shubhamshah207/clairvoy/clairvoy/core/models.py) ensures both new scans and existing tests or saved JSON summaries remain structurally valid without deserialization regressions.
3. **Category Assignment Invariant:**
   - Default non-media files are initialized as `ImageCategory.FILE`. When clustered by `DocumentTextMatcherPlugin` under `MatchType.CONTENT_NEAR_DUPLICATE`, the pipeline assigns `ImageCategory.DOCUMENT` to both the `FileEntry` and `DuplicateRecord`. This populates `summary.category_breakdown` accurately (`DOCUMENT: N`) for CLI and reporting consumers.
4. **CLI User Experience:**
   - Auto-discovery in `discover_plugins()` exposes `document_matcher` in `clairvoy plugins list` and `clairvoy plugins info document_matcher`.
   - During `clairvoy scan`, `summary.content_duplicate_groups` is displayed alongside exact duplicate sets and visual AI clusters.

---

## 3. Caveats

- **Scope Boundary:** No edits were made to [`clairvoy/plugins/document_matcher.py`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/document_matcher.py) (Milestone M1 scope) or [`AGENTS.md`](file:///home/shubhamshah207/clairvoy/AGENTS.md) (Milestone M3 scope).
- **Environment Dependency:** `pypdf` is listed in `pyproject.toml` dependencies and is pre-installed at version `6.18.1` in the miniconda environment.

---

## 4. Conclusion

Milestone M2 is **100% complete and fully verified**:
- [`DocumentTextMatcherPlugin`](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/document_matcher.py) is integrated into [`DeduplicationPipeline`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/pipeline.py), [`clairvoy.cli`](file:///home/shubhamshah207/clairvoy/clairvoy/cli.py), [`ScanSummary`](file:///home/shubhamshah207/clairvoy/clairvoy/core/models.py), and [`pyproject.toml`](file:///home/shubhamshah207/clairvoy/pyproject.toml).
- `test_pipeline_document_matcher_integration` tests end-to-end routing, clustering, and categorization.
- All 253 tests across the entire test suite pass with 100% success.
- Static linter passes with 0 violations (`ruff check .`).
- CLI plugins table correctly displays `document_matcher` at Priority 50 as Enabled and Available.

---

## 5. Verification Method

To independently verify Milestone M2:

1. **Verify Default Plugin Registration in CLI:**
   ```bash
   /home/shubhamshah207/miniconda3/bin/clairvoy plugins list
   /home/shubhamshah207/miniconda3/bin/clairvoy plugins info document_matcher
   ```
   *Expected:* `document_matcher` row in ASCII table with Priority 50, Enabled yes, Available yes.

2. **Verify Pipeline Test Suite:**
   ```bash
   /home/shubhamshah207/miniconda3/bin/pytest tests/test_pipeline.py -v
   ```
   *Expected:* 14 passed in <1.0s.

3. **Verify Full Regression Test Suite:**
   ```bash
   /home/shubhamshah207/miniconda3/bin/pytest -v
   ```
   *Expected:* 253 passed, 0 failures.

4. **Verify Static Linter:**
   ```bash
   /home/shubhamshah207/miniconda3/bin/ruff check .
   ```
   *Expected:* `All checks passed!`.

5. **Files to Inspect:**
   - [`clairvoy/core/models.py`](file:///home/shubhamshah207/clairvoy/clairvoy/core/models.py)
   - [`clairvoy/engines/pipeline.py`](file:///home/shubhamshah207/clairvoy/clairvoy/engines/pipeline.py)
   - [`clairvoy/cli.py`](file:///home/shubhamshah207/clairvoy/clairvoy/cli.py)
   - [`pyproject.toml`](file:///home/shubhamshah207/clairvoy/pyproject.toml)
   - [`tests/test_pipeline.py`](file:///home/shubhamshah207/clairvoy/tests/test_pipeline.py)
