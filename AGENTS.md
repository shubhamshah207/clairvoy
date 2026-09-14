# AGENTS.md — Agent Working Guidelines & Repository Blueprint

This document is the single source of truth for AI agents (and human contributors) working on **Clairvoy**.
Clairvoy is an ultra-fast, 100% offline, privacy-first multimodal media deduplication and storage optimization engine.

All agents operating in this repository **MUST read this document** and **MUST maintain and update this file and linked docs** whenever architectural changes, new plugins, new patterns, or workflow modifications are introduced.

---

## 1. Quick Reference & Commands

- **Environment Python:** `/home/shubhamshah207/miniconda3/bin/python`
- **Run Tests (Full Suite):** `/home/shubhamshah207/miniconda3/bin/pytest -v`
- **Lint Check:** `/home/shubhamshah207/miniconda3/bin/ruff check .`
- **Auto-Fix Lints:** `/home/shubhamshah207/miniconda3/bin/ruff check --fix .`
- **CLI Commands:**
  ```bash
  /home/shubhamshah207/miniconda3/bin/clairvoy scan /path/to/folder
  /home/shubhamshah207/miniconda3/bin/clairvoy plugins list
  /home/shubhamshah207/miniconda3/bin/clairvoy plugins info exact_hash
  ```

---

## 2. Core Invariants & Agent Rules

1. **Maintain `AGENTS.md` Always:**
   - Any time architecture, plugins, CLI options, dependencies, or workflows change, you must update this file or its linked subdocs.
2. **ASCII Art for All Terminal/Chat Diagrams:**
   - Never output Mermaid, graphviz, or image tags for diagrams in chat responses or terminal logs. Always format diagrams as clean ASCII art with box-drawing characters (`+---`, `|`, `-->`).
3. **Clickable Links for Files & Symbols:**
   - All references to files, functions, classes, or test cases in user responses must use clickable `file://` markdown links (e.g. `[plugins.py](file:///home/shubhamshah207/clairvoy/clairvoy/core/plugins.py)`).
4. **Local-First & Zero-Clobber Invariants:**
   - Never write code that makes external unauthenticated cloud API calls.
   - Operations that alter files (quarantine, hardlinking, deleting) must never overwrite without verification and must support rollback/manifest tracking.
5. **Deep Modules (Interface-First):**
   - Keep implementation details hidden behind clean, deep public interfaces (`clairvoy.core`, `clairvoy.engines`, `clairvoy.plugins`).
   - Humans own the interface and PRDs; AI owns the implementation; test suites keep it honest.
6. **Plan Mode Guidelines:**
   - The 4-step loop: **Plan $\rightarrow$ Execute $\rightarrow$ Test $\rightarrow$ Commit**.
   - Make plans extremely concise; sacrifice grammar for the sake of concision.
   - At the end of each plan, provide a list of unresolved questions to answer, if any.
7. **Quality & Verification:**
   - Python 3.12+ type annotations (`T | None`, `list[T]`, `dict[K, V]`).
   - `pytest` suite and `ruff check .` must pass with 100% success and 0 errors.

---

## 3. High-Level Architecture Overview

```
+---------------------------------------------------------------------------------+
|                                 CLAIRVOY ENGINE                                 |
+---------------------------------------------------------------------------------+
|                                                                                 |
|   +-------------------+      +---------------------+      +-----------------+   |
|   |    CLI (Typer)    |      |    FastAPI (Web)    |      | Custom Plugins  |   |
|   |  clairvoy/cli.py  |      |   clairvoy/web/     |      | ~/.clairvoy/... |   |
|   +---------+---------+      +----------+----------+      +--------+--------+   |
|             |                           |                          |            |
|             +---------------------+     |     +--------------------+            |
|                                   v     v     v                                 |
|                        +---------------------------+                            |
|                        |       PluginRegistry      |                            |
|                        | clairvoy/core/plugins.py  |                            |
|                        +-------------+-------------+                            |
|                                      |                                          |
|                                      v                                          |
|                        +---------------------------+                            |
|                        |   DeduplicationPipeline   |                            |
|                        | clairvoy/engines/pipeline |                            |
|                        +-------------+-------------+                            |
|                                      |                                          |
|         +----------------------------+----------------------------+             |
|         |                            |                            |             |
|         v                            v                            v             |
|  [Tier 1 Matchers]          [Tier 2 Matchers]            [Tier 3 Matchers]      |
|  ExactHashMatcherPlugin     PhotoVisionMatcherPlugin     ArchiveInspector...    |
|  (QuickHash + SHA-256)      (DINOv2 Embeddings)          (ZIP/TAR in-memory)    |
|         |                            |                            |             |
|         +----------------------------+----------------------------+             |
|                                      |                                          |
|                                      v                                          |
|                        +---------------------------+                            |
|                        |  CompositeKeeperStrategy  |                            |
|                        |  (Scoring & Seniority)    |                            |
|                        +-------------+-------------+                            |
|                                      |                                          |
|                                      v                                          |
|         +----------------------------+----------------------------+             |
|         |                                                         |             |
|         v                                                         v             |
|  [Action: SafeQuarantine]                                  [Action: Hardlink]   |
|  SafeQuarantineActionPlugin                                HardlinkActionPlugin |
+---------------------------------------------------------------------------------+
```

---

## 4. Progressive Disclosure & Detailed Documentation

To preserve agent instruction budgets, in-depth guidelines are organized into dedicated documents:

- **System Architecture & Deep Modules:** [`docs/ARCHITECTURE.md`](file:///home/shubhamshah207/clairvoy/docs/ARCHITECTURE.md)
  - Details package structure, short-circuit pipeline pruning, and composite keeper scoring.
- **Plugin Developer Guide:** [`docs/PLUGINS.md`](file:///home/shubhamshah207/clairvoy/docs/PLUGINS.md)
  - Details how to create custom Matcher, Keeper, and Action plugins, priority tiers, and dynamic registration.
- **Testing & Verification Guide:** [`docs/TESTING.md`](file:///home/shubhamshah207/clairvoy/docs/TESTING.md)
  - Details test fixtures, execution options, and linter standards.
- **Enterprise Security Policy:** [`SECURITY.md`](file:///home/shubhamshah207/clairvoy/SECURITY.md)
  - Details path traversal defenses, system root isolation, and sanitized shell generation.
- **Automated Agent Guardrails:** [`scripts/agent_guard.py`](file:///home/shubhamshah207/clairvoy/scripts/agent_guard.py)
  - Deterministic pre-execution command filter preventing destructive git commands and unvirtualized python execution.

---

## 5. Agent Tool Portability

- [`CLAUDE.md`](file:///home/shubhamshah207/clairvoy/CLAUDE.md) is symlinked to `AGENTS.md`.
- [`agents.md`](file:///home/shubhamshah207/clairvoy/agents.md) is symlinked to `AGENTS.md`.
- Both ensure universal agent compatibility across Claude Code, Cursor, Windsurf, Copilot, and Antigravity.
