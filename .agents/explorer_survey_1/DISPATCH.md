# DISPATCH — explorer_survey_1

## Objective
Survey Clairvoy's core plugin architecture, matcher interfaces, data models, and existing matcher plugins.

## Path to Authoritative Request
`file:///home/shubhamshah207/clairvoy/.agents/ORIGINAL_REQUEST.md`

## Specific Areas to Investigate
1. `clairvoy/core/plugins.py`:
   - Plugin registration mechanisms (`PluginRegistry`, decorators, hooks, entrypoints).
   - Base classes: `MatcherPlugin`, `KeeperPlugin`, `ActionPlugin`.
   - Data structures: `MatchResult`, `DuplicateCluster`, `MatchType` (specifically `CONTENT_NEAR_DUPLICATE` or similar enums), priority ordering semantics (priority order 50).
   - Interface contracts for matchers: what method signature must be implemented (`match(...)`, `can_handle(...)`, etc.)?
2. Existing Matcher Plugins:
   - `clairvoy/plugins/photo_vision.py`
   - `clairvoy/plugins/exact_hash.py`
   - `clairvoy/plugins/archive_inspector.py`
   - `clairvoy/plugins/video_matcher.py`
   - How do they group candidate files, return clusters, handle errors, and declare supported file extensions?
3. Format probes and utilities:
   - `clairvoy/core/format_utils.py` and other utilities: how are mime/magic/extensions checked?

## Deliverable
Write your comprehensive findings and recommendations to `file:///home/shubhamshah207/clairvoy/.agents/explorer_survey_1/handoff.md`. Include file paths, class/function signatures, and verified evidence chains.

## 2026-09-14T05:43:52Z
You are explorer_survey_1. Your working directory is file:///home/shubhamshah207/clairvoy/.agents/explorer_survey_1. Read file:///home/shubhamshah207/clairvoy/.agents/ORIGINAL_REQUEST.md and file:///home/shubhamshah207/clairvoy/.agents/explorer_survey_1/DISPATCH.md. Investigate Clairvoy's core plugin interfaces in clairvoy/core/plugins.py and existing matcher plugins (exact_hash.py, photo_vision.py, archive_inspector.py, video_matcher.py). Report your comprehensive findings and recommendations in file:///home/shubhamshah207/clairvoy/.agents/explorer_survey_1/handoff.md and notify me via send_message.

