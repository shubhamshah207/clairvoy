"""
Clairvoy Command Line Interface
Local-first AI storage deduplication engine with pluggable matchers, keepers, and actions.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from clairvoy.core.config import (
    DEFAULT_NUM_WORKERS,
    DEFAULT_SIMILARITY_THRESHOLD,
    VERSION,
)
from clairvoy.core.plugins import (
    BaseActionPlugin,
    BaseKeeperPlugin,
    BaseMatcherPlugin,
    BasePlugin,
    PluginRegistry,
)
from clairvoy.core.security import SecurityError, resolve_safe_paths
from clairvoy.engines.pipeline import (
    CompositeKeeperStrategy,
    DeduplicationPipeline,
)
from clairvoy.engines.quarantine import QuarantineEngine
from clairvoy.plugins.archive_inspector import ArchiveInspectorMatcherPlugin
from clairvoy.plugins.document_matcher import DocumentTextMatcherPlugin
from clairvoy.plugins.exact_hash import ExactHashMatcherPlugin
from clairvoy.plugins.hardlink_action import HardlinkActionPlugin
from clairvoy.plugins.photo_vision import PhotoVisionMatcherPlugin
from clairvoy.plugins.quarantine_action import SafeQuarantineActionPlugin
from clairvoy.plugins.video_matcher import VideoKeyframeMatcherPlugin


def print_banner() -> None:
    banner = rf"""
   _____ _       _
  / ____| |     (_)
 | |    | | __ _ _ _ ____   _____  _   _
 | |    | |/ _` | | '__\ \ / / _ \| | | |
 | |____| | (_| | | |   \ V / (_) | |_| |
  \_____|_|\__,_|_|_|    \_/ \___/ \__, |
                                    __/ |
  Local-First AI Deduplication Engine|___/  v{VERSION}
"""
    print(banner)


def discover_plugins(registry: PluginRegistry | None = None) -> PluginRegistry:
    """Auto-discovers plugins: loads default suite, loads ~/.clairvoy/plugins/, loads entry points."""
    if registry is None:
        registry = PluginRegistry.get_instance()

    default_plugins: list[BasePlugin] = [
        ExactHashMatcherPlugin(),
        ArchiveInspectorMatcherPlugin(),
        PhotoVisionMatcherPlugin(),
        VideoKeyframeMatcherPlugin(),
        DocumentTextMatcherPlugin(),
        CompositeKeeperStrategy(),
        SafeQuarantineActionPlugin(),
        HardlinkActionPlugin(),
    ]
    for plugin in default_plugins:
        if registry.get_plugin(plugin.plugin_id) is None:
            registry.register(plugin)

    user_plugins_dir = Path.home() / ".clairvoy" / "plugins"
    if user_plugins_dir.is_dir():
        registry.load_plugins_from_directory(user_plugins_dir)

    registry.load_entry_points()
    return registry


def format_ascii_table(headers: list[str], rows: list[list[str]]) -> str:
    """Format tabular data into an ASCII art table with box-drawing borders."""
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(cell))
            else:
                col_widths.append(len(cell))

    sep_border = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    header_line = "| " + " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers)) + " |"

    lines = [sep_border, header_line, sep_border]
    for row in rows:
        padded_cells = [cell.ljust(col_widths[i]) for i, cell in enumerate(row)]
        lines.append("| " + " | ".join(padded_cells) + " |")
    lines.append(sep_border)
    return "\n".join(lines)


def handle_plugins_list(registry: PluginRegistry) -> None:
    """Displays an ASCII-formatted table with discovered plugins."""
    headers = ["ID", "Type", "Priority", "Enabled", "Available", "Description"]

    plugin_ids = registry.list_plugin_ids()
    plugins = [registry.get_plugin(pid) for pid in plugin_ids]
    valid_plugins = [p for p in plugins if p is not None]

    def _sort_key(p: BasePlugin) -> tuple[int, int, str]:
        if isinstance(p, BaseMatcherPlugin):
            return (0, p.priority_order, p.plugin_id)
        elif isinstance(p, BaseKeeperPlugin):
            return (1, 0, p.plugin_id)
        elif isinstance(p, BaseActionPlugin):
            return (2, 0, p.plugin_id)
        return (3, 0, p.plugin_id)

    sorted_plugins = sorted(valid_plugins, key=_sort_key)
    rows: list[list[str]] = []
    for p in sorted_plugins:
        ptype = (
            "Matcher"
            if isinstance(p, BaseMatcherPlugin)
            else (
                "Keeper"
                if isinstance(p, BaseKeeperPlugin)
                else ("Action" if isinstance(p, BaseActionPlugin) else "Plugin")
            )
        )
        p_priority = str(p.priority_order) if isinstance(p, BaseMatcherPlugin) else "-"
        p_enabled = "yes" if registry.is_plugin_enabled(p.plugin_id) else "no"
        is_avail, _ = p.is_available()
        p_avail = "yes" if is_avail else "no"
        p_desc = p.description or ""
        rows.append([p.plugin_id, ptype, p_priority, p_enabled, p_avail, p_desc])

    print(format_ascii_table(headers, rows))


def handle_plugin_info(plugin_id: str, registry: PluginRegistry) -> None:
    """Displays comprehensive metadata for a specific plugin."""
    plugin = registry.get_plugin(plugin_id)
    if plugin is None and hasattr(registry, "get_action"):
        plugin = registry.get_action(plugin_id)

    if plugin is None:
        print(f"[!] Error: Plugin '{plugin_id}' not found.")
        sys.exit(1)

    ptype = (
        "Matcher"
        if isinstance(plugin, BaseMatcherPlugin)
        else (
            "Keeper"
            if isinstance(plugin, BaseKeeperPlugin)
            else ("Action" if isinstance(plugin, BaseActionPlugin) else "Plugin")
        )
    )
    is_avail, reason = plugin.is_available()
    avail_str = f"{'yes' if is_avail else 'no'} ({reason})"
    enabled_str = "yes" if registry.is_plugin_enabled(plugin.plugin_id) else "no"

    print(f"Plugin Info: {plugin.plugin_id}")
    print(f" • ID:          {plugin.plugin_id}")
    print(f" • Type:        {ptype}")
    print(f" • Name:        {plugin.display_name}")
    print(f" • Version:     {plugin.version}")
    print(f" • Author:      {plugin.author}")
    print(f" • Available:   {avail_str}")
    if isinstance(plugin, BaseMatcherPlugin):
        print(f" • Priority:    {plugin.priority_order}")
    print(f" • Enabled:     {enabled_str}")
    print(f" • Description: {plugin.description}")


def build_parser() -> argparse.ArgumentParser:
    """Build and configure the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="clairvoy",
        description="Clairvoy: Local-First AI Storage Deduplication Engine",
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"clairvoy {VERSION}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # --- Scan Command ---
    scan_parser = subparsers.add_parser(
        "scan", help="Scan one or more directories for exact and visual near-duplicate files"
    )
    scan_parser.add_argument("paths", nargs="+", help="One or more directory paths to scan")
    scan_parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Directory to save report files (default: <first_target>/_dedupe_reports)",
    )
    scan_parser.add_argument(
        "--no-ml",
        action="store_true",
        help="Disable Vision AI model and only run exact hash deduplication",
    )
    scan_parser.add_argument(
        "--threshold",
        "-t",
        type=float,
        default=DEFAULT_SIMILARITY_THRESHOLD,
        help=f"Visual similarity threshold between 0.70 and 0.99 (default: {DEFAULT_SIMILARITY_THRESHOLD})",
    )
    scan_parser.add_argument(
        "--workers",
        "-w",
        type=int,
        default=DEFAULT_NUM_WORKERS,
        help=f"Number of parallel worker threads for I/O and hashing (default: {DEFAULT_NUM_WORKERS})",
    )
    scan_parser.add_argument(
        "--enable-plugin",
        action="append",
        default=[],
        help="Enable specific plugin by ID (can be specified multiple times)",
    )
    scan_parser.add_argument(
        "--disable-plugin",
        action="append",
        default=[],
        help="Disable specific plugin by ID (can be specified multiple times)",
    )
    scan_parser.add_argument(
        "--action",
        choices=["quarantine", "hardlink"],
        default=None,
        help="Execute duplicate resolution action after scan",
    )
    scan_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate execution without modifying files on disk",
    )

    # --- Plugins Command ---
    plugins_parser = subparsers.add_parser(
        "plugins", help="Inspect and manage Clairvoy matcher, keeper, and action plugins"
    )
    plugin_subparsers = plugins_parser.add_subparsers(
        dest="plugin_command", help="Plugin management subcommands"
    )
    plugin_subparsers.add_parser(
        "list", help="List all discovered plugins, types, priority, availability, and active status"
    )
    plugin_info_parser = plugin_subparsers.add_parser(
        "info", help="Show detailed information for a specific plugin"
    )
    plugin_info_parser.add_argument("plugin_id", help="Identifier of the plugin to inspect")

    # --- UI Command ---
    ui_parser = subparsers.add_parser(
        "ui", help="Launch the local interactive Web Application dashboard"
    )
    ui_parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=8000,
        help="Web server port (default: 8000)",
    )
    ui_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Web server host binding (default: 127.0.0.1)",
    )

    # --- Quarantine Command ---
    quarantine_parser = subparsers.add_parser(
        "quarantine", help="Safely move duplicates to quarantine using a summary report"
    )
    quarantine_parser.add_argument(
        "report_file",
        help="Path to duplicates_summary.json generated by scan",
    )
    quarantine_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview files that would be moved without actually moving them",
    )

    # --- Restore Command ---
    restore_parser = subparsers.add_parser(
        "restore", help="Restore quarantined files back to their original locations"
    )
    restore_parser.add_argument(
        "manifest_file",
        help="Path to quarantine_manifest.json created during quarantine",
    )
    restore_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview files that would be restored without moving them",
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        print_banner()
        parser.print_help()
        sys.exit(0)

    if args.command == "scan":
        print_banner()
        try:
            target_paths = resolve_safe_paths(args.paths, must_exist=True)
            for tp in target_paths:
                if not tp.is_dir():
                    print(f"[!] Error: Path '{tp}' is not a directory.")
                    sys.exit(1)
        except (SecurityError, FileNotFoundError) as e:
            print(f"[!] Path Error: {e}")
            sys.exit(1)

        registry = discover_plugins(PluginRegistry.get_instance())

        if args.no_ml:
            registry.disable_plugin("photo_vision")
            registry.disable_plugin("video_matcher")

        for p_id in args.disable_plugin:
            registry.disable_plugin(p_id)

        for p_id in args.enable_plugin:
            registry.enable_plugin(p_id)

        pipeline = DeduplicationPipeline(
            paths=target_paths,
            registry=registry,
            output_dir=args.output,
            num_workers=args.workers,
        )
        summary = pipeline.run_scan()

        print(
            f"\n[✓] Scan completed in {summary.duration_seconds:.1f}s across {len(target_paths)} path(s)"
        )
        print(f" • Exact Duplicate Sets: {summary.exact_duplicate_groups}")
        print(f" • Visual AI Clusters: {summary.visual_ai_groups}")
        print(f" • Document & Tabular Clusters: {summary.content_duplicate_groups}")
        print(f" • Total Recoverable Space: {summary.wasted_mb} MB ({summary.wasted_gb} GB)")
        if summary.category_breakdown:
            cat_str = " | ".join(f"{k}: {v}" for k, v in summary.category_breakdown.items())
            print(f" • Duplicates by Category: {cat_str}")
        print(f" • CSV Report: {summary.csv_report}")
        print(f" • Summary JSON: {summary.summary_json}")
        print(f" • Safe Quarantine Script: {summary.quarantine_script}")

        if args.action:
            if args.dry_run:
                print(f"[*] DRY RUN MODE: Simulating '{args.action}' action.")
            print(f"[*] Executing action '{args.action}'...")
            action_res = pipeline.execute_action(args.action, summary=summary, dry_run=args.dry_run)
            print(f"[✓] Action '{args.action}' completed:")
            print(f" • Files processed: {action_res.success_count}")
            print(
                f" • Space saved / bytes saved: {action_res.bytes_processed} bytes ({round(action_res.bytes_processed / (1024 * 1024), 2)} MB)"
            )
            print(f" • Manifest path: {action_res.manifest_path}")
            if action_res.failed_count > 0:
                print(f" • Failures: {action_res.failed_count}")

    elif args.command == "plugins":
        print_banner()
        registry = discover_plugins(PluginRegistry.get_instance())
        plugin_command = getattr(args, "plugin_command", None)
        if plugin_command == "list":
            handle_plugins_list(registry)
        elif plugin_command == "info":
            handle_plugin_info(args.plugin_id, registry)
        else:
            print("Usage: clairvoy plugins [list|info <plugin_id>]")
            sys.exit(0)

    elif args.command == "ui":
        print_banner()
        print(f"[*] Starting Clairvoy Web Server at http://{args.host}:{args.port} ...")
        print("[*] Press Ctrl+C to terminate.")
        try:
            import uvicorn

            from clairvoy.web.app import app

            uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
        except ImportError:
            print("[!] Error: Web server dependencies missing.")
            print("[*] Install with: pip install fastapi uvicorn")
            sys.exit(1)

    elif args.command == "quarantine":
        print_banner()
        report_path = Path(args.report_file).resolve()
        if not report_path.is_file():
            print(f"[!] Error: Report file '{report_path}' not found.")
            sys.exit(1)

        print(f"[*] Executing safe quarantine from: {report_path}")
        if args.dry_run:
            print("[*] DRY RUN MODE: No files will be moved.")

        manifest = QuarantineEngine.execute(report_path, dry_run=args.dry_run)
        print(f"[✓] Completed: {manifest.total_files_moved} duplicate files processed.")
        print(
            f" • Total Space Quarantined: {round(manifest.total_bytes_moved / (1024 * 1024), 2)} MB"
        )
        print(f" • Quarantine Directory: {manifest.quarantine_dir}")

    elif args.command == "restore":
        print_banner()
        manifest_path = Path(args.manifest_file).resolve()
        if not manifest_path.is_file():
            print(f"[!] Error: Manifest file '{manifest_path}' not found.")
            sys.exit(1)

        print(f"[*] Restoring files from manifest: {manifest_path}")
        if args.dry_run:
            print("[*] DRY RUN MODE: No files will be moved.")

        count = QuarantineEngine.restore(manifest_path, dry_run=args.dry_run)
        print(f"[✓] Restored {count} files back to their original locations.")


if __name__ == "__main__":
    main()
