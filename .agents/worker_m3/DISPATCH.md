# DISPATCH — worker_m3

## Objective
Update and synchronize all repository documentation (`AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/PLUGINS.md`) with Milestone M1 and M2 additions for `DocumentTextMatcherPlugin`.

## Inputs & Authoritative Specs
- `file:///home/shubhamshah207/clairvoy/.agents/ORIGINAL_REQUEST.md` (Read this first!)
- `file:///home/shubhamshah207/clairvoy/.agents/orchestrator_1/PROJECT.md`
- Implementation: `file:///home/shubhamshah207/clairvoy/clairvoy/plugins/document_matcher.py`
- Integration: `file:///home/shubhamshah207/clairvoy/clairvoy/engines/pipeline.py`, `file:///home/shubhamshah207/clairvoy/clairvoy/cli.py`

## File Ownership
- YOU EXCLUSIVELY OWN:
  - `file:///home/shubhamshah207/clairvoy/AGENTS.md`
  - `file:///home/shubhamshah207/clairvoy/docs/ARCHITECTURE.md`
  - `file:///home/shubhamshah207/clairvoy/docs/PLUGINS.md`
- Note: `CLAUDE.md` and `agents.md` are symlinks to `AGENTS.md`; editing `AGENTS.md` automatically synchronizes them.

## Mandatory Guidelines
1. ALL diagrams MUST be formatted as clean ASCII art using box-drawing characters (`+---`, `|`, `-->`). NEVER output Mermaid or HTML image tags.
2. ALL file, class, function, and test references MUST use clickable `file://` markdown links (e.g. `[document_matcher.py](file:///home/shubhamshah207/clairvoy/clairvoy/plugins/document_matcher.py)`).
3. Update `AGENTS.md`:
   - High-Level Architecture ASCII diagram: include Tier 5: DocumentTextMatcherPlugin (.pdf, .docx, .pptx, .odt, .csv, .tsv).
   - Supported Format Matrix table: add Document & Tabular row with formats, plugin, invariant (in-memory zipfile XML inspection, pure-Python pypdf up to 50 pages, permutation-invariant row sort, token similarity >= 0.90, 25MB buffer / 50k words cap).
   - Quick reference commands: include `clairvoy plugins info document_matcher`.
4. Update `docs/ARCHITECTURE.md`:
   - Update Matching Pipeline ASCII diagram to show 5-tier architecture.
   - Add Tier 5: DocumentTextMatcherPlugin section with extraction recipes, normalization, Jaccard similarity, and memory safety.
   - Update Supported Modalities & Formats Matrix.
5. Update `docs/PLUGINS.md`:
   - Document `DocumentTextMatcherPlugin` under Built-in Matcher Plugins table and detailed section.
   - Detail methods (`is_available`, `filter_supported`, `extract_document_representation`, `find_duplicates`).
   - Add CLI usage example (`clairvoy plugins info document_matcher`).
6. Verification:
   - Run `/home/shubhamshah207/miniconda3/bin/pytest -v` to ensure no documentation or test regressions.
   - Run `/home/shubhamshah207/miniconda3/bin/ruff check .` (0 errors).

## Deliverable
Write your handoff report to `file:///home/shubhamshah207/clairvoy/.agents/worker_m3/handoff.md` and notify me via send_message.
