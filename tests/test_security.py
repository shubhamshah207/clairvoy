"""
Unit Tests for Security Hardening and Path Validation
"""


import pytest

from clairvoy.core.security import (
    SecurityError,
    generate_hardened_deletion_script,
    generate_hardened_quarantine_script,
    resolve_safe_path,
    resolve_safe_paths,
    safe_sh_quote,
)


def test_resolve_safe_path_valid(temp_workspace):
    test_file = temp_workspace / "valid.txt"
    test_file.write_text("safe content")

    resolved = resolve_safe_path(test_file, must_exist=True)
    assert resolved == test_file.resolve()


def test_resolve_safe_path_traversal_detection(temp_workspace):
    allowed_dir = temp_workspace / "safe_sandbox"
    allowed_dir.mkdir()

    outside_file = temp_workspace / "secret.txt"
    outside_file.write_text("secret")

    with pytest.raises(SecurityError, match="Directory traversal detected"):
        resolve_safe_path(outside_file, allowed_roots=allowed_dir)


def test_resolve_safe_path_disallowed_system_root():
    with pytest.raises(SecurityError, match="restricted system directory"):
        resolve_safe_path("/etc/passwd", must_exist=False)


def test_resolve_safe_path_extension_whitelist(temp_workspace):
    bad_file = temp_workspace / "malicious.sh"
    bad_file.write_text("echo hacked")

    with pytest.raises(SecurityError, match="File extension '.sh' is not permitted"):
        resolve_safe_path(bad_file, allowed_extensions={".jpg", ".png"})


def test_resolve_safe_path_null_bytes():
    with pytest.raises(SecurityError, match="contains null bytes"):
        resolve_safe_path("folder/file\0.jpg")


def test_resolve_safe_paths_multiple(temp_workspace):
    d1 = temp_workspace / "dir1"
    d2 = temp_workspace / "dir2"
    d1.mkdir()
    d2.mkdir()

    paths = resolve_safe_paths([d1, d2])
    assert len(paths) == 2
    assert d1.resolve() in paths
    assert d2.resolve() in paths

    # Test comma-separated string
    comma_paths = resolve_safe_paths(f"{d1}, {d2}")
    assert len(comma_paths) == 2


def test_safe_sh_quote_injection_prevention():
    malicious_path = '/tmp/test"; rm -rf / ; echo "'
    quoted = safe_sh_quote(malicious_path)
    assert ";" not in quoted or quoted.startswith("'")
    assert quoted.startswith("'") and quoted.endswith("'")


def test_generate_hardened_quarantine_script():
    moves = [("/path/to/source file.jpg", "/quarantine/dest file.jpg")]
    script = generate_hardened_quarantine_script(moves, "/path/to", "/quarantine")
    assert "set -euo pipefail" in script
    assert "mv -n --" in script
    assert "'/path/to/source file.jpg'" in script


def test_resolve_safe_path_filesystem_root_rejected():
    with pytest.raises(SecurityError, match="root directory"):
        resolve_safe_path("/", must_exist=False)


def test_resolve_safe_paths_prunes_nested_descendants(temp_workspace):
    parent = temp_workspace / "parent"
    child = parent / "child"
    parent.mkdir()
    child.mkdir()

    paths = resolve_safe_paths([parent, child])
    assert len(paths) == 1
    assert paths[0] == parent.resolve()


def test_generate_hardened_deletion_script():
    deletions = ["/path/to/dupe 1.jpg", "/path/to/dupe 2.jpg"]
    script_trash = generate_hardened_deletion_script(
        deletions=deletions,
        base_dir="/path/to",
        mode="trash",
        trash_dir="/path/to/.clairvoy_trash",
    )
    assert "set -euo pipefail" in script_trash
    assert "TRASH mode" in script_trash
    assert "mv -n --" in script_trash

    script_perm = generate_hardened_deletion_script(
        deletions=deletions,
        base_dir="/path/to",
        mode="permanent",
    )
    assert "set -euo pipefail" in script_perm
    assert "PERMANENT mode" in script_perm
    assert "rm -f --" in script_perm


