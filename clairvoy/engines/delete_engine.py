"""
Clairvoy Safe Deletion Engine
Provides high-performance, concurrent soft delete (Trash with 1-click restore)
and permanent deletion with strict keeper protection and immutable audit trails.
"""

import json
import os
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from clairvoy.core.config import DEFAULT_NUM_WORKERS
from clairvoy.core.models import (
    ActionType,
    DeletionItem,
    DeletionManifest,
    ScanSummary,
)
from clairvoy.core.security import SecurityError, resolve_safe_path


class DeleteEngine:
    """Handles safe, multi-worker duplicate deletion across single or multiple root trees."""

    @staticmethod
    def _trash_single_file(item: tuple[Path, Path, int, int]) -> DeletionItem | None:
        """Safely moves a single file into the trash container without clobbering."""
        src, dst, size, gid = item
        try:
            if not src.exists():
                return None
            dst.parent.mkdir(parents=True, exist_ok=True)

            target_dst = dst
            if target_dst.exists():
                stem = dst.stem
                suffix = dst.suffix
                counter = 1
                while target_dst.exists():
                    target_dst = dst.parent / f"{stem}_{counter}{suffix}"
                    counter += 1

            shutil.move(str(src), str(target_dst))
            return DeletionItem(
                original_path=str(src),
                size_bytes=size,
                group_id=gid,
                mode="trash",
                trash_path=str(target_dst),
            )
        except Exception as e:
            print(f"[!] Trash move error for {src}: {e}")
            return None

    @staticmethod
    def _permanently_delete_single_file(item: tuple[Path, int, int]) -> DeletionItem | None:
        """Permanently unlinks a duplicate file from storage."""
        src, size, gid = item
        try:
            if not src.exists():
                return None
            os.unlink(src)
            return DeletionItem(
                original_path=str(src),
                size_bytes=size,
                group_id=gid,
                mode="permanent",
                trash_path=None,
            )
        except Exception as e:
            print(f"[!] Permanent deletion error for {src}: {e}")
            return None

    @classmethod
    def execute(
        cls,
        summary_or_records: ScanSummary | dict[str, Any] | str | Path,
        selected_paths: list[str] | None = None,
        base_dir: str | Path | list[str | Path] | None = None,
        mode: str = "trash",
        num_workers: int = DEFAULT_NUM_WORKERS,
    ) -> DeletionManifest:
        """
        Executes file deletion across identified duplicates.
        Enforces strict safety invariants:
          1. Files designated as KEEP can NEVER be deleted.
          2. All deleted files must reside strictly within authorized base roots.
          3. Generates a comprehensive audit/manifest JSON file.
        """
        if mode not in {"trash", "permanent"}:
            raise ValueError(f"Invalid deletion mode '{mode}'. Must be 'trash' or 'permanent'.")

        base_roots: list[Path] = []
        if isinstance(summary_or_records, (str, Path)):
            with open(summary_or_records, encoding="utf-8") as f:
                data = json.load(f)
            records = data.get("groups", [])
            raw_paths = data.get("scanned_paths") or [data.get("scanned_dir", ".")]
            base_roots = [Path(p).resolve() for p in raw_paths]
        elif isinstance(summary_or_records, ScanSummary):
            records = [r.model_dump() for r in summary_or_records.groups]
            raw_paths = summary_or_records.scanned_paths or [summary_or_records.scanned_dir]
            base_roots = [Path(p).resolve() for p in raw_paths]
        elif isinstance(summary_or_records, dict):
            records = summary_or_records.get("groups", [])
            raw_paths = summary_or_records.get("scanned_paths") or [summary_or_records.get("scanned_dir", ".")]
            base_roots = [Path(p).resolve() for p in raw_paths]
        else:
            raise TypeError("Unsupported summary type provided to DeleteEngine.")

        if base_dir:
            if isinstance(base_dir, (str, Path)):
                base_roots = [Path(base_dir).resolve()]
            else:
                base_roots = [Path(b).resolve() for b in base_dir]

        primary_root = base_roots[0] if base_roots else Path(".").resolve()
        primary_trash = primary_root / ".clairvoy_trash"

        # 1. Identify keeper files to strictly protect
        keeper_paths = set()
        for r in records:
            action = r.get("action")
            if action in {ActionType.KEEP, "KEEP"}:
                p_str = r.get("path")
                if p_str:
                    keeper_paths.add(str(Path(p_str).resolve()))

        # 2. Filter candidates
        selected_set = {str(Path(p).resolve()) for p in selected_paths} if selected_paths is not None else None
        deletions_to_process: list[tuple[Path, int, int]] = []

        for r in records:
            action = r.get("action")
            # Only consider duplicate records
            if action not in {ActionType.DUPLICATE, "DUPLICATE"}:
                continue

            src_path_str = r.get("path")
            if not src_path_str:
                continue

            src_path = Path(src_path_str).resolve()
            src_resolved_str = str(src_path)

            # Strict Keeper Protection Invariant
            if src_resolved_str in keeper_paths:
                continue

            # If specific selection given, honor it
            if selected_set is not None and src_resolved_str not in selected_set:
                continue

            if not src_path.exists():
                continue

            # Verify within base roots
            enclosing_root: Path | None = None
            for root in base_roots:
                try:
                    if src_path.is_relative_to(root):
                        enclosing_root = root
                        break
                except ValueError:
                    continue

            if enclosing_root is None:
                raise SecurityError(
                    f"Attempted deletion of path outside authorized scanned directories: '{src_path}'"
                )

            gid = r.get("group_id", 0)
            file_size = src_path.stat().st_size
            deletions_to_process.append((src_path, file_size, gid))

        # Check for any selected paths that were not in records but were explicitly requested
        if selected_set is not None:
            processed_paths = {str(item[0]) for item in deletions_to_process}
            for sel_path_str in selected_set:
                if sel_path_str in keeper_paths:
                    continue  # Safely skipped keeper
                if sel_path_str not in processed_paths:
                    sel_p = Path(sel_path_str).resolve()
                    if sel_p.exists():
                        # Validate security root
                        is_safe = False
                        for root in base_roots:
                            try:
                                if sel_p.is_relative_to(root):
                                    is_safe = True
                                    break
                            except ValueError:
                                pass
                        if not is_safe:
                            raise SecurityError(
                                f"Attempted deletion of path outside authorized scanned directories: '{sel_p}'"
                            )
                        deletions_to_process.append((sel_p, sel_p.stat().st_size, 0))

        items: list[DeletionItem] = []
        total_bytes = 0

        ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        if mode == "trash":
            tasks: list[tuple[Path, Path, int, int]] = []
            for src_p, size, gid in deletions_to_process:
                # Resolve relative path under root
                enclosing = None
                for root in base_roots:
                    try:
                        if src_p.is_relative_to(root):
                            enclosing = root
                            break
                    except ValueError:
                        pass
                if enclosing:
                    rel = src_p.relative_to(enclosing)
                    dst = enclosing / ".clairvoy_trash" / rel
                else:
                    dst = primary_trash / src_p.name

                tasks.append((src_p, dst, size, gid))

            with ThreadPoolExecutor(max_workers=min(num_workers, len(tasks) or 1)) as pool:
                futures = [pool.submit(cls._trash_single_file, t) for t in tasks]
                for fut in as_completed(futures):
                    res = fut.result()
                    if res:
                        items.append(res)
                        total_bytes += res.size_bytes

            primary_trash.mkdir(parents=True, exist_ok=True)
            audit_file = primary_trash / f"trash_manifest_{ts_str}.json"

        else:  # permanent
            with ThreadPoolExecutor(max_workers=min(num_workers, len(deletions_to_process) or 1)) as pool:
                futures = [pool.submit(cls._permanently_delete_single_file, t) for t in deletions_to_process]
                for fut in as_completed(futures):
                    res = fut.result()
                    if res:
                        items.append(res)
                        total_bytes += res.size_bytes

            audit_dir = primary_root / "_dedupe_reports"
            audit_dir.mkdir(parents=True, exist_ok=True)
            audit_file = audit_dir / f"deletion_audit_{ts_str}.json"

        manifest = DeletionManifest(
            timestamp=datetime.now(timezone.utc).isoformat(),
            mode=mode,
            base_dirs=[str(r) for r in base_roots],
            total_files_deleted=len(items),
            total_bytes_freed=total_bytes,
            items=items,
            audit_file=str(audit_file),
        )

        with open(audit_file, "w", encoding="utf-8") as f:
            json.dump(manifest.model_dump(), f, indent=2)

        return manifest

    @classmethod
    def restore(cls, manifest_file: str | Path) -> int:
        """Restores soft-deleted files from a trash manifest back to original paths."""
        m_path = Path(manifest_file).resolve()
        if not m_path.is_file():
            raise FileNotFoundError(f"Trash manifest not found: {m_path}")

        with open(m_path, encoding="utf-8") as f:
            data = json.load(f)

        items = data.get("items", [])
        restored = 0

        for it in items:
            trash_path_str = it.get("trash_path")
            orig_path_str = it.get("original_path")
            if not trash_path_str or not orig_path_str:
                continue

            trash_p = Path(trash_path_str)
            orig_p = Path(orig_path_str)

            if not trash_p.exists():
                continue

            # Traversal validation
            resolve_safe_path(orig_p, must_exist=False)

            orig_p.parent.mkdir(parents=True, exist_ok=True)
            target = orig_p
            if target.exists():
                stem = orig_p.stem
                suffix = orig_p.suffix
                cnt = 1
                while target.exists():
                    target = orig_p.parent / f"{stem}_restored_{cnt}{suffix}"
                    cnt += 1

            shutil.move(str(trash_p), str(target))
            restored += 1

        return restored
