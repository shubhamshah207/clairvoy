# AGENTS.md — Agent Working Guidelines & Repository Blueprint

This document is the single source of truth for AI agents (and human contributors) working on **{{PROJECT_NAME}}**.
{{PROJECT_NAME}} is {{ONE_SENTENCE_PROJECT_DESCRIPTION}}.

All agents operating in this repository **MUST read this document** and **MUST maintain and update this file and linked docs** whenever architectural changes, new patterns, or workflow modifications are introduced.

---

## 1. Quick Reference & Commands

- **Environment Runtime:** `{{RUNTIME_OR_INTERPRETER_PATH}}`
- **Run Tests:** `{{TEST_COMMAND}}`
- **Lint Check:** `{{LINT_COMMAND}}`
- **Auto-Fix Formatting:** `{{LINT_FIX_COMMAND}}`
- **Build / Run:** `{{BUILD_COMMAND}}`

---

## 2. Core Invariants & Agent Rules

1. **Maintain `AGENTS.md` Always:**
   - Whenever architecture, CLI options, dependencies, or workflows change, update this file or its linked subdocs.
2. **ASCII Art for All Terminal/Chat Diagrams:**
   - Format all diagrams as clean ASCII art (`+---`, `|`, `-->`) for direct terminal readability without graphic renderers.
3. **Clickable Links for Files & Symbols:**
   - Reference files and symbols using clickable markdown links (e.g. `[main.py](file:///path/to/main.py)`).
4. **Zero-Clobber Safety:**
   - Operations that alter files must never overwrite without verification and must support rollback tracking.
5. **Deep Modules (Interface-First):**
   - Keep implementation details hidden behind clean, deep public interfaces.
   - Humans own the interface and specifications; AI owns the implementation; tests keep it honest.
6. **Plan Mode Guidelines:**
   - The 4-step loop: **Plan $\rightarrow$ Execute $\rightarrow$ Test $\rightarrow$ Commit**.
   - Make plans extremely concise; sacrifice grammar for the sake of concision.
   - Conclude each plan with a list of unresolved questions to answer, if any.
7. **Verification Invariant:**
   - Run tests and linters before declaring any task complete.

---

## 3. High-Level Architecture Overview

```
+-----------------------------------------------------------------------------+
|                          {{PROJECT_NAME}} OVERVIEW                          |
+-----------------------------------------------------------------------------+
|  [Client / Entrypoints] ---> [Core Engine / Services] ---> [Storage / Output]
+-----------------------------------------------------------------------------+
```

---

## 4. Progressive Disclosure & Detailed Documentation

To preserve agent instruction budgets, in-depth guidelines are organized into dedicated documents:

- **System Architecture & Deep Modules:** `docs/ARCHITECTURE.md`
- **Testing & Verification Guide:** `docs/TESTING.md`
- **Security & Permissions Policy:** `SECURITY.md`

---

## 5. Agent Tool Portability

- `CLAUDE.md` is symlinked to `AGENTS.md`.
- `agents.md` is symlinked to `AGENTS.md`.
- Ensures universal agent compatibility across Claude Code, Cursor, Windsurf, Copilot, and Antigravity.
