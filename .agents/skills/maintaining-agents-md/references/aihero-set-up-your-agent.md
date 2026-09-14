# Reference: AI Hero "Set Up Your Agent" Blog Series

Author: **Matt Pocock** ([AI Hero](https://www.aihero.dev/topics/set-up-your-agent))  
Topic URL: https://www.aihero.dev/topics/set-up-your-agent

This document synthesizes the 9 foundational articles published in Matt Pocock's "Set Up Your Agent" curriculum, explaining the theoretical and practical foundations of agent-ready software engineering.

---

## 1. A Complete Guide To AGENTS.md
- **URL**: https://www.aihero.dev/a-complete-guide-to-agents-md
- **Core Insights**:
  - **Instruction Budget**: Frontier thinking LLMs follow ~150–300 instructions with high consistency. Every token in `AGENTS.md` is loaded at the start of *every single prompt turn*.
  - **The "Ball of Mud" Anti-Pattern**: If developers add ad-hoc rules every time an agent makes a mistake without pruning, `AGENTS.md` becomes a bloated, conflicting ball of mud that actively degrades agent intelligence.
  - **Progressive Disclosure**: Keep the root `AGENTS.md` minimal (one-sentence project scope, package manager, primary test/lint commands) and link to specialized sub-documents (e.g., `docs/TYPESCRIPT.md`, `docs/TESTING.md`, `docs/ARCHITECTURE.md`) which the agent loads only when relevant.
  - **Avoid Stale File Paths**: Documenting volatile micro-paths (`src/auth/handlers.ts`) poisons context when files move. Instead, describe module capabilities and boundaries.
  - **Universal Symlinks**: Claude Code looks for `CLAUDE.md`, others look for `AGENTS.md`. Maintain `ln -s AGENTS.md CLAUDE.md` and `ln -s AGENTS.md agents.md`.

---

## 2. My AGENTS.md File for Building Plans You Actually Read
- **URL**: https://www.aihero.dev/my-agents-md-file-for-building-plans-you-actually-read
- **Core Insights**:
  - **The 4-Step Plan Loop**:
    1. **Plan**: Iterate with the AI before writing code.
    2. **Execute**: Ask AI to write code strictly implementing the agreed plan.
    3. **Test**: Run test suites, verify type safety, validate behavior.
    4. **Commit**: Checkpoint code and restart loop for next chunk.
  - **Plan Concision Rule**: *"Make the plan extremely concise. Sacrifice grammar for the sake of concision."*
  - **Unresolved Questions Checkpoint**: *"At the end of each plan, give me a list of unresolved questions to answer, if any."*

---

## 3. How To Make Codebases AI Agents Love
- **URL**: https://www.aihero.dev/how-to-make-codebases-ai-agents-love
- **Core Insights**:
  - **AI is a New Starter with No Memory**: Every spawned agent is like the protagonist of *Memento* stepping in for the first time.
  - **Deep Modules (*A Philosophy of Software Design* by John Ousterhout)**:
    - Shallow modules (hundreds of small files importing each other arbitrarily) cause hallucinations, cognitive burnout, and lost context.
    - Deep modules provide lots of functionality behind a simple, cohesive, controllable interface.
  - **Grey Box Modules**: Humans own the interface, architecture, and PRDs; AI owns internal implementation; automated tests keep it honest.

---

## 4. Never Run Claude /init
- **URL**: https://www.aihero.dev/never-run-claude-init
- **Core Insights**:
  - Auto-generated `/init` dumps flood the system prompt with generic commands and trivial boilerplate (e.g. dumping entire `package.json` scripts).
  - Exploration, implementation, and testing context phases are flexible; but the system prompt is hardwired and permanent.
  - A handcrafted, minimal progressive-disclosure file preserves instruction budgets for difficult problem-solving.

---

## 5. How To Use Claude Code Hooks To Enforce The Right CLI
- **URL**: https://www.aihero.dev/how-to-use-claude-code-hooks-to-enforce-the-right-cli
- **Core Insights**:
  - Instructing an agent in `CLAUDE.md` / `AGENTS.md` ("Please use pnpm instead of npm") wastes instruction budget on every request and is non-deterministic.
  - **Deterministic Hooks**: Use `PreToolUse` in `.claude/settings.json`.
  - When a hook script exits with **code 2**, the tool call is blocked and stderr is fed directly back to the agent as actionable feedback.
  ```json
  {
    "hooks": {
      "PreToolUse": [
        {
          "matcher": "Bash",
          "hooks": [{ "type": "command", "command": ".claude/hooks/guard.sh" }]
        }
      ]
    }
  }
  ```

---

## 6. This Hook Stops Claude Code Running Dangerous Git Commands
- **URL**: https://www.aihero.dev/this-hook-stops-claude-code-running-dangerous-git-commands
- **Core Insights**:
  - Sandboxes isolate where agents run, but cannot stop agents from destroying local git history with `git reset --hard`, `git push --force`, or `git clean -fd`.
  - A `PreToolUse` hook deterministically intercepts bash commands matching dangerous git patterns, exits with code 2, and preserves git integrity.

---

## 7. An Introduction To Plan Mode
- **URL**: https://www.aihero.dev/plan-mode-introduction
- **Core Insights**:
  - Entering plan mode (`--permission-mode plan` or `/plan`) restricts write permissions and forces context priming.
  - During planning, the agent reads relevant files and maps architecture. When execution begins, context is already primed.
  - Pair plan mode with dictation for fast, messy human intent capture that the agent refines into structured plans.

---

## 8. Connect Claude Code To A GitHub MCP Server
- **URL**: https://www.aihero.dev/connect-claude-code-to-github
- **Core Insights**:
  - Model Context Protocol (MCP) enables terminal agents to query pull requests, read issues, check CI status, and push commits across repositories.
  - Scoping MCP servers at project level (`claude mcp add`) keeps credentials and capabilities contained.

---

## 9. Creating The Perfect Claude Code Status Line
- **URL**: https://www.aihero.dev/creating-the-perfect-claude-code-status-line
- **Core Insights**:
  - Status lines provide visual transparency into agent session context tokens, git branch state, and active tool operations.
