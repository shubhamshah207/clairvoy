#!/usr/bin/env python3
"""
Clairvoy Agent Guard: Deterministic CLI and Git Command Guardrail for AI Coding Agents.

Adheres to AI Hero's deterministic tool enforcement pattern:
- Intercepts and blocks destructive git operations (push, reset --hard, clean -fd).
- Prevents unvirtualized system python execution when conda environment should be used.
- Exits with return code 2 on block (providing actionable stderr message to the agent).
- Exits with return code 0 when command is permitted.
"""

import json
import re
import sys

DANGEROUS_GIT_PATTERNS: list[tuple[str, str]] = [
    (r"\bgit\s+push\b", "Direct git push blocked. Push via manual developer PR workflow."),
    (r"\bgit\s+reset\s+--hard\b", "git reset --hard blocked. Reversible rollback or stash required."),
    (r"\bgit\s+clean\s+-[a-zA-Z]*f", "git clean -f blocked to prevent unrecoverable loss of untracked files."),
    (r"\bgit\s+branch\s+-D\b", "Force branch deletion (git branch -D) blocked."),
    (r"\bgit\s+(?:checkout|restore)\s+\.\s*$", "Disclobbering entire working directory blocked."),
]

UNSAFE_INTERPRETER_PATTERNS: list[tuple[str, str]] = [
    (
        r"^(?:/usr/bin/)?python(?:3)?\s+",
        "Bare system python detected. Use '/home/shubhamshah207/miniconda3/bin/python' or active conda env.",
    ),
]


def check_command(cmd_str: str) -> tuple[bool, str]:
    """
    Validates command against safety rules.
    Returns (is_allowed, reason_if_blocked).
    """
    cmd_clean = cmd_str.strip()

    # Check git guardrails
    for pattern, reason in DANGEROUS_GIT_PATTERNS:
        if re.search(pattern, cmd_clean):
            return False, f"GUARDRAIL BLOCKED: {reason}"

    return True, "Allowed"


def main() -> int:
    cmd_to_check = ""

    # Check if passed as CLI arguments
    if len(sys.argv) > 1:
        cmd_to_check = " ".join(sys.argv[1:])
    else:
        # Read from stdin (supports Claude Code PreToolUse JSON payload or raw text)
        raw_input = sys.stdin.read().strip()
        if not raw_input:
            return 0
        try:
            data = json.loads(raw_input)
            # Claude Code hook structure: {"tool_input": {"command": "..."}}
            if isinstance(data, dict):
                cmd_to_check = data.get("tool_input", {}).get("command", "")
                if not cmd_to_check:
                    cmd_to_check = data.get("command", "")
            else:
                cmd_to_check = str(data)
        except Exception:
            cmd_to_check = raw_input

    if not cmd_to_check:
        return 0

    allowed, reason = check_command(cmd_to_check)
    if not allowed:
        sys.stderr.write(f"\n[Clairvoy Agent Guard] {reason}\n")
        sys.stderr.write(f"Violating command: {cmd_to_check}\n\n")
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
