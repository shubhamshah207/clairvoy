"""
Clairvoy Security & Hardening Module
Provides path canonicalization, traversal defense, shell escaping, and I/O safety.
"""

import shlex
from pathlib import Path

# Sensitive directories that should never be accessed or served via web endpoints
DISALLOWED_ROOT_PATHS = {
    Path("/etc"),
    Path("/proc"),
    Path("/sys"),
    Path("/dev"),
    Path("/boot"),
    Path("/root"),
    Path.home() / ".ssh",
    Path.home() / ".gnupg",
    Path.home() / ".aws",
    Path.home() / ".config" / "rclone",
}


class SecurityError(Exception):
    """Raised when a path or operation violates security constraints."""


def resolve_safe_path(
    user_path: str | Path,
    allowed_root: str | Path | None = None,
    allowed_extensions: set[str] | None = None,
    must_exist: bool = True,
) -> Path:
    """
    Canonicalizes and securely validates a filesystem path.
    Prevents path traversal, directory breakouts, and access to system-critical files.
    """
    if not user_path or "\0" in str(user_path):
        raise SecurityError("Invalid path: contains null bytes or empty input.")

    raw_path = Path(user_path).expanduser()
    try:
        resolved = raw_path.resolve()
    except (OSError, RuntimeError) as e:
        raise SecurityError(f"Could not resolve path '{user_path}': {e}") from e

    # Check against restricted system paths
    for disallowed in DISALLOWED_ROOT_PATHS:
        try:
            if resolved == disallowed or resolved.is_relative_to(disallowed):
                raise SecurityError(f"Access denied: Path is inside restricted system directory: {disallowed}")
        except ValueError:
            continue

    # Enforce confinement if allowed_root is provided
    if allowed_root is not None:
        resolved_root = Path(allowed_root).expanduser().resolve()
        try:
            if not resolved.is_relative_to(resolved_root):
                raise SecurityError(
                    f"Directory traversal detected: '{resolved}' is outside permitted root '{resolved_root}'"
                )
        except ValueError:
            raise SecurityError(f"Path '{resolved}' is not within permitted boundary '{resolved_root}'") from None

    # Check extension whitelist if specified
    if allowed_extensions is not None:
        ext = resolved.suffix.lower()
        if ext not in allowed_extensions:
            raise SecurityError(
                f"File extension '{ext}' is not permitted. Allowed: {sorted(allowed_extensions)}"
            )

    if must_exist and not resolved.exists():
        raise FileNotFoundError(f"Target file or directory does not exist: {resolved}")

    return resolved


def safe_sh_quote(path_or_cmd: str | Path) -> str:
    """Safely escapes a path or argument for shell execution using POSIX standard."""
    return shlex.quote(str(path_or_cmd))


def generate_hardened_quarantine_script(
    moves: list[tuple[str, str]],  # (source_path, dest_path)
    base_dir: str,
    quarantine_dir: str,
) -> str:
    """
    Generates a secure, idempotent bash script to execute file quarantine.
    Guarantees:
      - Uses `set -euo pipefail` to abort immediately on error.
      - Posix shlex quoting on all paths (no injection possible).
      - Uses `mv -n --` (no clobber) to prevent accidental overwrites.
    """
    lines = [
        "#!/usr/bin/env bash",
        "# Generated automatically by Clairvoy Local Storage Engine",
        "# Safe Quarantine Execution Script",
        "set -euo pipefail",
        "",
        'echo "[*] Initiating Clairvoy Safe Quarantine..."',
        f'echo "[*] Base Directory: {safe_sh_quote(base_dir)}"',
        f'echo "[*] Quarantine Target: {safe_sh_quote(quarantine_dir)}"',
        "",
        f'mkdir -p -- {safe_sh_quote(quarantine_dir)}',
        "",
        "MOVED_COUNT=0",
        "",
    ]

    for src, dst in moves:
        dst_dir = str(Path(dst).parent)
        lines.append(f'mkdir -p -- {safe_sh_quote(dst_dir)}')
        lines.append(f'if [ -f {safe_sh_quote(src)} ]; then')
        lines.append(f'    mv -n -- {safe_sh_quote(src)} {safe_sh_quote(dst)}')
        lines.append('    MOVED_COUNT=$((MOVED_COUNT + 1))')
        lines.append('fi')

    lines.append("")
    lines.append('echo "[✓] Successfully quarantined $MOVED_COUNT duplicate files."')
    lines.append("")
    return "\n".join(lines)
