"""
Clairvoy Quarantine & Restore Engine
Safely isolates duplicate files into quarantine folders with a reversible manifest.
"""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from clairvoy.core.models import (
    ActionType,
    QuarantineItem,
    QuarantineManifest,
    ScanSummary,
)


class QuarantineEngine:
    """Handles reversible, atomic file quarantining."""

    @staticmethod
    def execute(
        summary_or_records: ScanSummary | dict | str | Path,
        base_dir: str | Path | None = None,
        dry_run: bool = False,
    ) -> QuarantineManifest:
        """
        Moves all marked duplicate files into a structured `_duplicate_quarantine` directory.
        Saves `quarantine_manifest.json` for rollback.
        """
        # Load records
        if isinstance(summary_or_records, (str, Path)):
            with open(summary_or_records, encoding="utf-8") as f:
                data = json.load(f)
            records = data.get("groups", [])
            root_dir = Path(base_dir or data.get("scanned_dir", ".")).resolve()
        elif isinstance(summary_or_records, ScanSummary):
            records = [r.model_dump() for r in summary_or_records.groups]
            root_dir = Path(base_dir or summary_or_records.scanned_dir).resolve()
        elif isinstance(summary_or_records, dict):
            records = summary_or_records.get("groups", [])
            root_dir = Path(base_dir or summary_or_records.get("scanned_dir", ".")).resolve()
        else:
            raise TypeError("Unsupported summary type provided to QuarantineEngine.")

        quarantine_root = root_dir / "_duplicate_quarantine"
        manifest_items: list[QuarantineItem] = []
        total_bytes = 0

        for r in records:
            action = r.get("action")
            if action != ActionType.DUPLICATE and action != "DUPLICATE":
                continue

            src_path_str = r.get("path")
            if not src_path_str:
                continue

            src_path = Path(src_path_str).resolve()
            if not src_path.exists():
                continue

            # Compute relative path to preserve hierarchy
            try:
                rel_path = src_path.relative_to(root_dir)
            except ValueError:
                rel_path = Path(src_path.name)

            dst_path = quarantine_root / rel_path
            file_size = src_path.stat().st_size

            manifest_items.append(
                QuarantineItem(
                    original_path=str(src_path),
                    quarantined_path=str(dst_path),
                    size_bytes=file_size,
                    group_id=r.get("group_id", 0),
                )
            )
            total_bytes += file_size

            if not dry_run:
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src_path), str(dst_path))

        manifest = QuarantineManifest(
            timestamp=datetime.now(timezone.utc).isoformat(),
            base_dir=str(root_dir),
            quarantine_dir=str(quarantine_root),
            total_files_moved=len(manifest_items),
            total_bytes_moved=total_bytes,
            items=manifest_items,
        )

        if not dry_run and manifest_items:
            manifest_path = quarantine_root / "quarantine_manifest.json"
            quarantine_root.mkdir(parents=True, exist_ok=True)
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest.model_dump(), f, indent=2)

        return manifest

    @staticmethod
    def restore(
        manifest_path_or_dict: str | Path | dict,
        dry_run: bool = False,
    ) -> int:
        """
        Reverses a previous quarantine using the saved manifest.
        Restores all duplicate files to their exact original locations.
        """
        if isinstance(manifest_path_or_dict, (str, Path)):
            manifest_file = Path(manifest_path_or_dict).resolve()
            with open(manifest_file, encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = manifest_path_or_dict

        items = data.get("items", [])
        restored_count = 0

        for item in items:
            q_path = Path(item["quarantined_path"])
            orig_path = Path(item["original_path"])

            if not q_path.exists():
                continue

            if not dry_run:
                orig_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(q_path), str(orig_path))

            restored_count += 1

        return restored_count
