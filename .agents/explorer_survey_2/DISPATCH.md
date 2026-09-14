# DISPATCH — explorer_survey_2

## Objective
Survey Clairvoy's pipeline engine (`clairvoy/engines/pipeline.py`), CLI commands (`clairvoy/cli.py`), project dependencies (`pyproject.toml`), and current testing patterns.

## Path to Authoritative Request
`file:///home/shubhamshah207/clairvoy/.agents/ORIGINAL_REQUEST.md`

## Specific Areas to Investigate
1. `clairvoy/engines/pipeline.py`:
   - How does `DeduplicationPipeline` initialize plugins and discover candidates?
   - How does candidate pruning and routing across tiers work?
   - How are match results aggregated into clusters and summary reports?
   - How should `DocumentTextMatcherPlugin` be registered and called?
2. `clairvoy/cli.py`:
   - How does the Typer CLI command (`clairvoy scan`, `clairvoy plugins list`, etc.) register plugins?
   - Where are default plugins registered or discovered?
   - How does `plugins list` display plugin status?
3. `pyproject.toml`:
   - Current dependencies and structure. Where should `pypdf>=5.0.0` be added?
   - Is `pypdf` already installed in the environment (`/home/shubhamshah207/miniconda3/bin/python`)?
4. Existing Test Harnesses (`tests/`):
   - How are plugins tested? Look at existing test files (e.g., `tests/test_exact_hash.py`, `tests/test_archive_inspector.py`, `tests/test_pipeline.py`).
   - How are fixtures and sample files constructed?

## Deliverable
Write your comprehensive findings and recommendations to `file:///home/shubhamshah207/clairvoy/.agents/explorer_survey_2/handoff.md`. Include file paths, code snippets, and verified evidence chains.

## 2026-09-14T05:43:52Z
You are explorer_survey_2. Your working directory is file:///home/shubhamshah207/clairvoy/.agents/explorer_survey_2. Read file:///home/shubhamshah207/clairvoy/.agents/ORIGINAL_REQUEST.md and file:///home/shubhamshah207/clairvoy/.agents/explorer_survey_2/DISPATCH.md. Investigate clairvoy/engines/pipeline.py, clairvoy/cli.py, pyproject.toml, and tests/. Report your comprehensive findings and recommendations in file:///home/shubhamshah207/clairvoy/.agents/explorer_survey_2/handoff.md and notify me via send_message.
