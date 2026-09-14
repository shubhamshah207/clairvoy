#!/usr/bin/env python3
"""
Reusable Deterministic Agent Guardrail Script.
Intercepts tool commands, blocks destructive actions (exit 2), and allows safe ones (exit 0).
"""

import json
import re
import sys

DANGEROUS_PATTERNS: list[tuple[str, str]] = [
    (r"\bgit\s+push\b", "Direct git push blocked. Use manual PR workflow."),
    (r"\bgit\s+reset\s+--hard\b", "git reset --hard blocked. Use reversible stash/rollback."),
    (r"\bgit\s+clean\s+-[a-zA-Z]*f", "git clean -f blocked to prevent unrecoverable deletion."),
    (r"\bgit\s+branch\s+-D\b", "Force branch deletion (git branch -D) blocked."),
    (r"\bgit\s+(?:checkout|restore)\s+\.\s*$", "Bulk working directory overwrite blocked."),
]


def check_command(cmd_str: str) -> tuple[bool, str]:
    cmd = cmd_str.strip()
    for pattern, reason in DANGEROUS_PATTERNS:
        if re.search(pattern, cmd):
            return False, f"GUARDRAIL BLOCKED: {reason}"
    return True, "Allowed"


def main() -> int:
    cmd_to_check = ""
    if len(sys.argv) > 1:
        cmd_to_check = " ".join(sys.argv[1:])
    else:
        raw = sys.stdin.read().strip()
        if not raw:
            return 0
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                cmd_to_check = data.get("tool_input", {}).get("command") or data.get("command", "")
            else:
                cmd_to_check = str(data)
        except Exception:
            cmd_to_check = raw

    if not cmd_to_check:
        return 0

    allowed, reason = check_command(cmd_to_check)
    if not allowed:
        sys.stderr.write(f"\n[Agent Guard] {reason}\nViolating command: {cmd_to_check}\n\n")
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
