#!/bin/bash
# Clairvoy PreToolUse hook for Claude Code
# Intercepts bash tool calls to block destructive actions deterministically.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [ -f "$REPO_ROOT/scripts/agent_guard.py" ]; then
  exec python3 "$REPO_ROOT/scripts/agent_guard.py"
fi
exit 0
