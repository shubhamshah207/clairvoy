"""
Tests for CLI Plugin Management Commands and Scan Action Flags.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from clairvoy.cli import build_parser, main
from clairvoy.core.plugins import PluginRegistry


@pytest.fixture(autouse=True)
def clean_registry():
    """Ensure PluginRegistry singleton is fresh for each test."""
    PluginRegistry.reset_instance()
    yield
    PluginRegistry.reset_instance()


def test_build_parser_options():
    """Verifies that the CLI parser correctly configures scan and plugin options."""
    parser = build_parser()
    scan_args = parser.parse_args(
        ["scan", "/tmp", "--enable-plugin", "foo", "--action", "hardlink", "--dry-run"]
    )
    assert scan_args.command == "scan"
    assert "foo" in scan_args.enable_plugin
    assert scan_args.action == "hardlink"
    assert scan_args.dry_run is True

    plugin_args = parser.parse_args(["plugins", "info", "exact_hash"])
    assert plugin_args.command == "plugins"
    assert plugin_args.plugin_command == "info"
    assert plugin_args.plugin_id == "exact_hash"


def test_cli_plugins_list(capsys):
    """Verifies 'clairvoy plugins list' prints all core plugins in an ASCII table."""
    main(["plugins", "list"])
    captured = capsys.readouterr()
    out = captured.out

    # Check table headers
    assert "ID" in out
    assert "Type" in out
    assert "Priority" in out
    assert "Enabled" in out
    assert "Available" in out
    assert "Description" in out

    # Check ASCII box borders
    assert "+---" in out or "+-" in out
    assert "|" in out

    # Check core plugins
    assert "exact_hash" in out
    assert "photo_vision" in out
    assert "video_matcher" in out
    assert "archive_inspector" in out
    assert "quarantine" in out
    assert "hardlink" in out
    assert "composite_keeper" in out


def test_cli_plugins_info(capsys):
    """Verifies 'clairvoy plugins info exact_hash' prints detailed metadata."""
    main(["plugins", "info", "exact_hash"])
    captured = capsys.readouterr()
    out = captured.out

    assert "exact_hash" in out
    assert "Matcher" in out
    assert "Priority" in out
    assert "10" in out
    assert "Available" in out
    assert "Description" in out
    assert "Version" in out
    assert "Author" in out

    # Test info on action plugin (should not have priority)
    main(["plugins", "info", "hardlink"])
    captured_action = capsys.readouterr()
    assert "hardlink" in captured_action.out
    assert "Action" in captured_action.out
    assert "Priority" not in captured_action.out

    # Test info on non-existent plugin exits with error
    with pytest.raises(SystemExit) as excinfo:
        main(["plugins", "info", "nonexistent_plugin_xyz"])
    assert excinfo.value.code != 0


def test_cli_scan_with_plugin_toggles(sample_dataset, capsys):
    """Verifies --disable-plugin, --enable-plugin, and --no-ml toggles on scan."""
    root = str(sample_dataset["root"])

    # Test --disable-plugin photo_vision
    main(["scan", root, "--disable-plugin", "photo_vision"])
    reg = PluginRegistry.get_instance()
    assert reg.is_plugin_enabled("photo_vision") is False
    assert reg.is_plugin_enabled("exact_hash") is True

    # Test --enable-plugin photo_vision
    main(["scan", root, "--enable-plugin", "photo_vision"])
    assert reg.is_plugin_enabled("photo_vision") is True

    # Test --no-ml disables both photo_vision and video_matcher
    main(["scan", root, "--no-ml"])
    assert reg.is_plugin_enabled("photo_vision") is False
    assert reg.is_plugin_enabled("video_matcher") is False


def test_cli_scan_with_action_hardlink(sample_dataset, capsys):
    """Verifies scan with --action hardlink --dry-run executes action and prints results."""
    root = str(sample_dataset["root"])
    main(["scan", root, "--action", "hardlink", "--dry-run"])
    captured = capsys.readouterr()
    out = captured.out

    assert "hardlink" in out.lower()
    assert "dry run" in out.lower()
    assert "files processed" in out.lower()
    assert "space saved" in out.lower() or "bytes saved" in out.lower()
    assert "manifest" in out.lower()


def test_cli_scan_with_action_quarantine(sample_dataset, capsys):
    """Verifies scan with --action quarantine --dry-run executes action and prints results."""
    root = str(sample_dataset["root"])
    main(["scan", root, "--action", "quarantine", "--dry-run"])
    captured = capsys.readouterr()
    out = captured.out

    assert "quarantine" in out.lower()
    assert "dry run" in out.lower()
    assert "files processed" in out.lower()
    assert "space saved" in out.lower() or "bytes saved" in out.lower()
    assert "manifest" in out.lower()


def test_cli_plugins_list_subprocess():
    """Verifies that the CLI works as an external process command."""
    proc = subprocess.run(
        [sys.executable, "-m", "clairvoy.cli", "plugins", "list"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "exact_hash" in proc.stdout
    assert "quarantine" in proc.stdout
    assert "hardlink" in proc.stdout
