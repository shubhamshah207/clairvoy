"""
Safe Quarantine Action Plugin.
Safely isolates duplicate files into a structured quarantine directory with
reversible rollback capabilities.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from clairvoy.core.models import ActionType, DuplicateGroup, DuplicateRecord, ScanSummary
from clairvoy.core.plugins import ActionResult, BaseActionPlugin
from clairvoy.engines.quarantine import QuarantineEngine

logger = logging.getLogger(__name__)


class SafeQuarantineActionPlugin(BaseActionPlugin):
    """Safely isolates duplicate files into a quarantine directory with rollback manifest."""

    plugin_id: str = "quarantine"
    action_id: str = "quarantine"
    display_name: str = "Safe Quarantine Action (Reversible Isolation)"
    version: str = "0.1.0"
    author: str = "Clairvoy Team"
    description: str = "Safely isolates duplicate files into a quarantine directory with rollback manifest"

    def is_available(self) -> tuple[bool, str]:
        """Validate system dependencies and runtime availability."""
        return (True, "Safe quarantine action is available.")

    def _extract_records(self, plan: Any) -> list[dict[str, Any]]:
        """Normalize plan items into standard dictionary records."""
        if isinstance(plan, ScanSummary):
            return [r.model_dump() for r in plan.groups]
        elif isinstance(plan, dict):
            return plan.get("groups", [])
        elif isinstance(plan, list):
            records: list[dict[str, Any]] = []
            for item in plan:
                if isinstance(item, DuplicateGroup):
                    if hasattr(item.keeper, "model_dump"):
                        records.append(item.keeper.model_dump())
                    else:
                        records.append(item.keeper)  # type: ignore[arg-type]
                    for d in item.duplicates:
                        if hasattr(d, "model_dump"):
                            records.append(d.model_dump())
                        else:
                            records.append(d)  # type: ignore[arg-type]
                elif isinstance(item, DuplicateRecord):
                    records.append(item.model_dump())
                elif isinstance(item, dict):
                    records.append(item)
                elif hasattr(item, "model_dump"):
                    records.append(item.model_dump())
                elif hasattr(item, "__dict__"):
                    records.append(vars(item))
            return records
        return []

    def execute(
        self,
        plan: list[Any] | ScanSummary | dict[str, Any],
        base_dirs: list[Path] | None = None,
        dry_run: bool = False,
    ) -> ActionResult:
        """Execute non-destructive quarantine isolation on marked duplicates."""
        records = self._extract_records(plan)

        # Normalize base_roots
        base_roots: list[Path] = []
        if base_dirs:
            base_roots = [Path(b).resolve() for b in base_dirs]
        else:
            file_paths = [
                Path(r["path"]).resolve().parent
                for r in records
                if isinstance(r, dict) and "path" in r and r.get("path")
            ]
            if file_paths:
                try:
                    common = Path(os.path.commonpath([str(p) for p in file_paths]))
                    base_roots = [common]
                except ValueError:
                    base_roots = [file_paths[0]]
            else:
                base_roots = [Path.cwd().resolve()]

        # Identify duplicate records targeted for quarantine
        dupe_records: list[dict[str, Any]] = []
        for r in records:
            action = r.get("action")
            if action in (ActionType.DUPLICATE, "DUPLICATE", "ActionType.DUPLICATE"):
                dupe_records.append(r)

        total_dupes = len(dupe_records)
        errors: list[str] = []

        # Check existence before dispatching to QuarantineEngine
        for r in dupe_records:
            src_str = r.get("path")
            if not src_str:
                errors.append("Duplicate record has missing path")
                continue
            src_path = Path(src_str).resolve()
            if not src_path.exists():
                errors.append(f"Duplicate file does not exist: {src_path}")

        summary_payload = {
            "groups": records,
            "scanned_paths": [str(b) for b in base_roots],
        }

        try:
            manifest = QuarantineEngine.execute(
                summary_or_records=summary_payload,
                base_dir=base_roots,
                dry_run=dry_run,
            )

            success_count = manifest.total_files_moved
            failed_count = max(0, total_dupes - success_count)
            bytes_processed = manifest.total_bytes_moved
            manifest_path_str: str | None = None

            if not dry_run and manifest.items:
                m_path = Path(manifest.quarantine_dir) / "quarantine_manifest.json"
                if m_path.exists():
                    manifest_path_str = str(m_path)

            return ActionResult(
                action_id=self.action_id,
                success_count=success_count,
                failed_count=failed_count,
                bytes_processed=bytes_processed,
                manifest_path=manifest_path_str,
                errors=errors,
            )
        except Exception as exc:
            logger.error("Quarantine execution failed: %s", exc)
            return ActionResult(
                action_id=self.action_id,
                success_count=0,
                failed_count=total_dupes,
                bytes_processed=0,
                manifest_path=None,
                errors=[f"Quarantine execution failed: {exc}"],
            )

    def rollback(self, manifest_path: str | Path | dict[str, Any]) -> bool:
        """Restores quarantined files from the manifest back to original paths."""
        try:
            if isinstance(manifest_path, dict):
                items = manifest_path.get("items", [])
                restored = QuarantineEngine.restore(manifest_path)
                return restored == len(items)

            manifest_file = Path(manifest_path).resolve()
            if not manifest_file.exists():
                logger.error("Quarantine manifest does not exist: %s", manifest_file)
                return False

            with open(manifest_file, encoding="utf-8") as f:
                data = json.load(f)

            items = data.get("items", [])
            restored = QuarantineEngine.restore(manifest_file)
            return restored == len(items)
        except Exception as exc:
            logger.error("Quarantine rollback failed: %s", exc)
            return False
