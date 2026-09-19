"""
Clairvoy Security & Hardening Module
Provides path canonicalization, traversal defense, shell escaping, and I/O safety.
"""

import shlex
from pathlib import Path

# Sensitive directories that should never be accessed or served via web endpoints
DISALLOWED_ROOT_PATHS = {
    Path("/"),
    Path("/etc"),
    Path("/proc"),
    Path("/sys"),
    Path("/dev"),
    Path("/boot"),
    Path("/root"),
    Path("/bin"),
    Path("/sbin"),
    Path("/lib"),
    Path("/lib64"),
    Path("/usr"),
    Path("/var"),
    Path.home() / ".ssh",
    Path.home() / ".gnupg",
    Path.home() / ".aws",
    Path.home() / ".config" / "rclone",
}


class SecurityError(Exception):
    """Raised when a path or operation violates security constraints."""


def resolve_safe_path(
    user_path: str | Path,
    allowed_roots: str | Path | list[str | Path] | set[str | Path] | None = None,
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

    # Check against root directory anchor
    if resolved == Path("/") or resolved == Path(resolved.anchor):
        raise SecurityError("Direct access or scanning of filesystem root directory is forbidden.")

    # Check against restricted system paths
    for disallowed in DISALLOWED_ROOT_PATHS:
        try:
            if resolved == disallowed or (disallowed != Path("/") and resolved.is_relative_to(disallowed)):
                raise SecurityError(f"Access denied: Path is inside restricted system directory: {disallowed}")
        except ValueError:
            continue

    # Enforce confinement if allowed_roots is provided
    if allowed_roots is not None:
        if isinstance(allowed_roots, (str, Path)):
            root_list = [Path(allowed_roots).expanduser().resolve()]
        else:
            root_list = [Path(r).expanduser().resolve() for r in allowed_roots]

        within_any = False
        for root in root_list:
            try:
                if resolved.is_relative_to(root):
                    within_any = True
                    break
            except ValueError:
                continue

        if not within_any:
            roots_str = ", ".join(f"'{r}'" for r in root_list)
            raise SecurityError(
                f"Directory traversal detected: '{resolved}' is outside permitted root boundaries [{roots_str}]"
            )

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


def resolve_safe_paths(
    user_paths: str | Path | list[str | Path] | set[str | Path],
    allowed_roots: str | Path | list[str | Path] | set[str | Path] | None = None,
    must_exist: bool = True,
) -> list[Path]:
    """
    Resolves and validates multiple input paths.
    Accepts lists, sets, or comma/newline-separated strings.
    Automatically prunes redundant nested child paths.
    """
    raw_list: list[str | Path] = []
    if isinstance(user_paths, (str, Path)):
        # Support comma or newline separated multi-path string input
        parts = [p.strip() for p in str(user_paths).replace("\r", "\n").replace(",", "\n").split("\n") if p.strip()]
        raw_list = parts if parts else [user_paths]
    else:
        raw_list = list(user_paths)

    resolved_list: list[Path] = []
    seen = set()
    for p in raw_list:
        resolved = resolve_safe_path(p, allowed_roots=allowed_roots, must_exist=must_exist)
        if resolved not in seen:
            seen.add(resolved)
            resolved_list.append(resolved)

    # Prune redundant nested child paths (e.g. if ['/a', '/a/b'] is provided, keep only parent '/a')
    pruned_list: list[Path] = []
    sorted_candidates = sorted(resolved_list, key=lambda x: len(x.parts))
    for candidate in sorted_candidates:
        if not any(candidate.is_relative_to(parent) and candidate != parent for parent in pruned_list):
            pruned_list.append(candidate)

    if not pruned_list:
        raise SecurityError("No valid directories or paths provided.")

    return pruned_list



def safe_sh_quote(path_or_cmd: str | Path) -> str:
    """Safely escapes a path or argument for shell execution using POSIX standard."""
    return shlex.quote(str(path_or_cmd))


def generate_hardened_quarantine_script(
    moves: list[tuple[str, str]],  # (source_path, dest_path)
    base_dir: str | list[str],
    quarantine_dir: str,
) -> str:
    """
    Generates a secure, idempotent bash script to execute file quarantine.
    Guarantees:
      - Uses `set -euo pipefail` to abort immediately on error.
      - Posix shlex quoting on all paths (no injection possible).
      - Uses `mv -n --` (no clobber) to prevent accidental overwrites.
    """
    base_dirs = [base_dir] if isinstance(base_dir, str) else base_dir
    base_dirs_str = ", ".join(safe_sh_quote(b) for b in base_dirs)

    lines = [
        "#!/usr/bin/env bash",
        "# Generated automatically by Clairvoy Local Storage Engine",
        "# Safe Quarantine Execution Script",
        "set -euo pipefail",
        "",
        'echo "[*] Initiating Clairvoy Safe Quarantine..."',
        f'echo "[*] Base Directories: {base_dirs_str}"',
        f'echo "[*] Quarantine Target: {safe_sh_quote(quarantine_dir)}"',
        "",
        f"mkdir -p -- {safe_sh_quote(quarantine_dir)}",
        "",
        "MOVED_COUNT=0",
        "",
    ]

    for src, dst in moves:
        dst_dir = str(Path(dst).parent)
        lines.append(f"mkdir -p -- {safe_sh_quote(dst_dir)}")
        lines.append(f"if [ -f {safe_sh_quote(src)} ]; then")
        lines.append(f"    mv -n -- {safe_sh_quote(src)} {safe_sh_quote(dst)}")
        lines.append("    MOVED_COUNT=$((MOVED_COUNT + 1))")
        lines.append("fi")

    lines.append("")
    lines.append('echo "[✓] Successfully quarantined $MOVED_COUNT duplicate files."')
    lines.append("")
    return "\n".join(lines)


def generate_hardened_deletion_script(
    deletions: list[str],
    base_dir: str | list[str],
    mode: str = "trash",
    trash_dir: str | None = None,
) -> str:
    """
    Generates a secure, idempotent bash script to safely delete or trash duplicate files.
    Guarantees:
      - Uses `set -euo pipefail` to abort immediately on error.
      - Posix shlex quoting on all paths (no injection possible).
      - In 'trash' mode: safely moves files to trash directory using `mv -n --`.
      - In 'permanent' mode: removes files safely using `rm -f --`.
    """
    base_dirs = [base_dir] if isinstance(base_dir, str) else base_dir
    base_dirs_str = ", ".join(safe_sh_quote(b) for b in base_dirs)

    lines = [
        "#!/usr/bin/env bash",
        "# Generated automatically by Clairvoy Local Storage Engine",
        f"# Safe Deletion Execution Script (Mode: {mode.upper()})",
        "set -euo pipefail",
        "",
        f'echo "[*] Initiating Clairvoy Safe Deletion ({mode.upper()} mode)..."',
        f'echo "[*] Base Directories: {base_dirs_str}"',
    ]

    if mode == "trash" and trash_dir:
        lines.append(f'echo "[*] Trash Target: {safe_sh_quote(trash_dir)}"')
        lines.append(f"mkdir -p -- {safe_sh_quote(trash_dir)}")

    lines.extend([
        "",
        "ACTION_COUNT=0",
        "",
    ])

    for path in deletions:
        quoted_path = safe_sh_quote(path)
        lines.append(f"if [ -f {quoted_path} ]; then")
        if mode == "trash" and trash_dir:
            p_obj = Path(path)
            dst = str(Path(trash_dir) / p_obj.name)
            quoted_dst = safe_sh_quote(dst)
            lines.append(f"    mv -n -- {quoted_path} {quoted_dst}")
        else:
            lines.append(f"    rm -f -- {quoted_path}")
        lines.append("    ACTION_COUNT=$((ACTION_COUNT + 1))")
        lines.append("fi")

    lines.append("")
    lines.append(f'echo "[✓] Successfully processed $ACTION_COUNT files ({mode} mode)."')
    lines.append("")
    return "\n".join(lines)

