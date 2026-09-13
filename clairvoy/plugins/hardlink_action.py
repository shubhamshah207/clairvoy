"""
Hardlink Action Plugin.
Replaces duplicate files with native filesystem hardlinks pointing to keeper inodes,
reclaiming 100% of redundant disk space while preserving file paths and directory trees.
"""

from __future__ import annotations

import contextlib
import errno
import json
import logging
import os
import shutil
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from clairvoy.core.models import DuplicateGroup, ScanSummary
from clairvoy.core.plugins import ActionResult, BaseActionPlugin

logger = logging.getLogger(__name__)


class HardlinkActionPlugin(BaseActionPlugin):
    """Replaces duplicates with hardlinks to the keeper inode for instant zero-space reclamation."""

    plugin_id: str = "hardlink"
    action_id: str = "hardlink"
    display_name: str = "Hardlink Action (NTFS & POSIX Inode Unification)"
    version: str = "0.1.0"
    author: str = "Clairvoy Team"
    description: str = (
        "Replaces duplicates with hardlinks to the keeper inode for instant zero-space reclamation"
    )

    def is_available(self) -> tuple[bool, str]:
        """Validate system dependencies and runtime availability."""
        supported = hasattr(os, "link")
        msg = "Hardlinks supported via os.link" if supported else "os.link is not supported on this platform"
        return (supported, msg)

    def _get_path(self, entry: Any) -> Path:
        """Extract canonical Path from a record or string representation."""
        if hasattr(entry, "path"):
            return Path(entry.path).resolve()
        elif isinstance(entry, dict) and "path" in entry:
            return Path(entry["path"]).resolve()
        return Path(str(entry)).resolve()

    def _parse_groups(self, plan: Any) -> list[tuple[Any, list[Any]]]:
        """Parse diverse plan representations into keeper and duplicate lists per group."""
        if isinstance(plan, ScanSummary):
            records = plan.groups
        elif isinstance(plan, dict):
            records = plan.get("groups", [])
        elif isinstance(plan, list):
            records = plan
        else:
            records = []

        if not records:
            return []

        # Check if items are DuplicateGroup
        if isinstance(records[0], DuplicateGroup):
            return [(g.keeper, g.duplicates) for g in records if isinstance(g, DuplicateGroup)]

        # Otherwise, group by group_id
        group_map: dict[int, dict[str, Any]] = defaultdict(lambda: {"keeper": None, "duplicates": []})

        for idx, r in enumerate(records):
            gid = getattr(r, "group_id", None) if not isinstance(r, dict) else r.get("group_id")
            if gid is None:
                gid = idx
            action = getattr(r, "action", None) if not isinstance(r, dict) else r.get("action")
            action_str = str(action).upper()

            if action_str in ("ACTIONTYPE.KEEP", "KEEP"):
                group_map[gid]["keeper"] = r
            elif action_str in ("ACTIONTYPE.DUPLICATE", "DUPLICATE"):
                group_map[gid]["duplicates"].append(r)
            else:
                if group_map[gid]["keeper"] is None:
                    group_map[gid]["keeper"] = r
                else:
                    group_map[gid]["duplicates"].append(r)

        result_groups: list[tuple[Any, list[Any]]] = []
        for g in group_map.values():
            keeper = g["keeper"]
            dupes = g["duplicates"]
            if keeper is None and dupes:
                keeper = dupes.pop(0)
            if keeper is not None and dupes:
                result_groups.append((keeper, dupes))

        return result_groups

    def execute(
        self,
        plan: list[Any] | ScanSummary | dict[str, Any],
        base_dirs: list[Path] | None = None,
        dry_run: bool = False,
    ) -> ActionResult:
        """Replace duplicate files with atomic hardlinks pointing to keeper file inodes."""
        groups = self._parse_groups(plan)

        success_count = 0
        failed_count = 0
        bytes_processed = 0
        errors: list[str] = []
        manifest_items: list[dict[str, Any]] = []

        for keeper_entry, dupe_entries in groups:
            keeper_path = self._get_path(keeper_entry)

            if not keeper_path.exists():
                failed_count += len(dupe_entries)
                errors.append(f"Keeper file does not exist: {keeper_path}")
                continue

            try:
                k_stat = keeper_path.stat()
            except OSError as stat_err:
                failed_count += len(dupe_entries)
                errors.append(f"Failed to stat keeper file {keeper_path}: {stat_err}")
                continue

            for dupe_entry in dupe_entries:
                dupe_path = self._get_path(dupe_entry)

                if not dupe_path.exists():
                    failed_count += 1
                    errors.append(f"Duplicate file does not exist: {dupe_path}")
                    continue

                if keeper_path == dupe_path:
                    continue

                try:
                    d_stat = dupe_path.stat()
                except OSError as stat_err:
                    failed_count += 1
                    errors.append(f"Failed to stat duplicate file {dupe_path}: {stat_err}")
                    continue

                # Cross-device partition check
                if k_stat.st_dev != d_stat.st_dev:
                    failed_count += 1
                    errors.append(
                        f"Cannot hardlink across filesystem partitions: {keeper_path} "
                        f"(dev {k_stat.st_dev}) vs {dupe_path} (dev {d_stat.st_dev})"
                    )
                    continue

                if dry_run:
                    success_count += 1
                    bytes_processed += d_stat.st_size
                    manifest_items.append(
                        {
                            "keeper": str(keeper_path),
                            "duplicate": str(dupe_path),
                            "size_bytes": d_stat.st_size,
                            "inode": k_stat.st_ino,
                        }
                    )
                    continue

                # If already hardlinked to the same inode
                if k_stat.st_ino == d_stat.st_ino:
                    success_count += 1
                    bytes_processed += d_stat.st_size
                    manifest_items.append(
                        {
                            "keeper": str(keeper_path),
                            "duplicate": str(dupe_path),
                            "size_bytes": d_stat.st_size,
                            "inode": k_stat.st_ino,
                        }
                    )
                    continue

                # Atomic replacement via temporary hardlink in dupe's parent directory
                tmp_link = dupe_path.parent / f".tmp_hl_{uuid.uuid4().hex}"
                try:
                    os.link(keeper_path, tmp_link)
                    os.replace(tmp_link, dupe_path)

                    # Post-link inode verification
                    new_dupe_stat = dupe_path.stat()
                    if keeper_path.stat().st_ino != new_dupe_stat.st_ino:
                        raise OSError("Hardlink verification failed: inode mismatch after link")

                    success_count += 1
                    bytes_processed += d_stat.st_size
                    manifest_items.append(
                        {
                            "keeper": str(keeper_path),
                            "duplicate": str(dupe_path),
                            "size_bytes": d_stat.st_size,
                            "inode": new_dupe_stat.st_ino,
                        }
                    )
                except OSError as exc:
                    if tmp_link.exists():
                        with contextlib.suppress(OSError):
                            tmp_link.unlink()
                    failed_count += 1
                    if getattr(exc, "errno", None) == errno.EXDEV or "cross-device" in str(exc).lower():
                        errors.append(f"Cannot hardlink across filesystem partitions: {exc}")
                    else:
                        errors.append(f"Failed to hardlink {dupe_path} to {keeper_path}: {exc}")

        manifest_path_str: str | None = None
        if not dry_run and manifest_items:
            if base_dirs:
                manifest_dir = Path(base_dirs[0]).resolve()
            elif manifest_items:
                manifest_dir = Path(manifest_items[0]["keeper"]).parent
            else:
                manifest_dir = Path.cwd().resolve()

            manifest_dir.mkdir(parents=True, exist_ok=True)
            manifest_file = manifest_dir / "hardlink_manifest.json"
            manifest_dict = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action_id": self.action_id,
                "total_links_created": success_count,
                "bytes_reclaimed": bytes_processed,
                "items": manifest_items,
            }
            with open(manifest_file, "w", encoding="utf-8") as f:
                json.dump(manifest_dict, f, indent=2)
            manifest_path_str = str(manifest_file)

        return ActionResult(
            action_id=self.action_id,
            success_count=success_count,
            failed_count=failed_count,
            bytes_processed=bytes_processed,
            manifest_path=manifest_path_str,
            errors=errors,
        )

    def rollback(self, manifest_path: str | Path | dict[str, Any]) -> bool:
        """Restores independent duplicate files by breaking hardlinks via file copy."""
        try:
            if isinstance(manifest_path, dict):
                data = manifest_path
            else:
                manifest_file = Path(manifest_path).resolve()
                if not manifest_file.exists():
                    logger.error("Hardlink manifest does not exist: %s", manifest_file)
                    return False
                with open(manifest_file, encoding="utf-8") as f:
                    data = json.load(f)

            items = data.get("items", [])
            for item in items:
                keeper = Path(item["keeper"]).resolve()
                duplicate = Path(item["duplicate"]).resolve()

                if not keeper.exists() or not duplicate.exists():
                    continue

                # If they share the inode, restore an independent copy
                if keeper.stat().st_ino == duplicate.stat().st_ino:
                    tmp_copy = duplicate.parent / f".tmp_rb_{uuid.uuid4().hex}"
                    shutil.copy2(keeper, tmp_copy)
                    os.replace(tmp_copy, duplicate)

            return True
        except Exception as exc:
            logger.error("Hardlink rollback error: %s", exc)
            return False
