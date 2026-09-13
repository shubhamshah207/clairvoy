"""
Clairvoy Quarantine & Restore Engine
Safely and concurrently isolates duplicate files across single or multiple root paths,
with automated reversible rollback manifests.
"""

import json
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from clairvoy.core.config import DEFAULT_NUM_WORKERS
from clairvoy.core.models import (
    ActionType,
    QuarantineItem,
    QuarantineManifest,
    ScanSummary,
)


class QuarantineEngine:
    """Handles reversible, parallel file quarantining across one or multiple root directories."""

    @staticmethod
    def _move_single_file(item: tuple[Path, Path, int, int]) -> QuarantineItem | None:
        """Moves a single file to its quarantine location without clobbering existing files."""
        src, dst, size, gid = item
        try:
            if not src.exists():
                return None
            dst.parent.mkdir(parents=True, exist_ok=True)

            # Prevent overwriting if destination already exists
            target_dst = dst
            if target_dst.exists():
                stem = dst.stem
                suffix = dst.suffix
                counter = 1
                while target_dst.exists():
                    target_dst = dst.parent / f"{stem}_{counter}{suffix}"
                    counter += 1

            shutil.move(str(src), str(target_dst))
            return QuarantineItem(
                original_path=str(src),
                quarantined_path=str(target_dst),
                size_bytes=size,
                group_id=gid,
            )
        except Exception as e:
            print(f"[!] Quarantine move error for {src}: {e}")
            return None

    @staticmethod
    def _restore_single_file(item: dict) -> bool:
        """Restores a single quarantined file back to its original location safely."""
        q_path = Path(item["quarantined_path"])
        orig_path = Path(item["original_path"])
        try:
            if not q_path.exists():
                return False

            # Verify original path is not inside forbidden system root
            from clairvoy.core.security import resolve_safe_path

            resolve_safe_path(orig_path, must_exist=False)

            orig_path.parent.mkdir(parents=True, exist_ok=True)
            target_orig = orig_path
            if target_orig.exists():
                stem = orig_path.stem
                suffix = orig_path.suffix
                counter = 1
                while target_orig.exists():
                    target_orig = orig_path.parent / f"{stem}_restored_{counter}{suffix}"
                    counter += 1

            shutil.move(str(q_path), str(target_orig))
            return True
        except Exception as e:
            print(f"[!] Restore move error for {q_path}: {e}")
            return False


    @classmethod
    def execute(
        cls,
        summary_or_records: ScanSummary | dict | str | Path,
        base_dir: str | Path | list[str | Path] | None = None,
        dry_run: bool = False,
        num_workers: int = DEFAULT_NUM_WORKERS,
    ) -> QuarantineManifest:
        """
        Moves all marked duplicate files into a structured `_duplicate_quarantine` directory.
        Preserves original subfolder structures under each respective root directory.
        Saves `quarantine_manifest.json` for rollback.
        """
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
            raise TypeError("Unsupported summary type provided to QuarantineEngine.")

        if base_dir:
            if isinstance(base_dir, (str, Path)):
                base_roots = [Path(base_dir).resolve()]
            else:
                base_roots = [Path(b).resolve() for b in base_dir]

        primary_root = base_roots[0] if base_roots else Path(".").resolve()
        primary_quarantine = primary_root / "_duplicate_quarantine"

        move_tasks: list[tuple[Path, Path, int, int]] = []
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

            # Find enclosing root to preserve relative hierarchy
            enclosing_root: Path | None = None
            for root in base_roots:
                try:
                    if src_path.is_relative_to(root):
                        enclosing_root = root
                        break
                except ValueError:
                    continue

            if enclosing_root:
                rel = src_path.relative_to(enclosing_root)
                dst_path = enclosing_root / "_duplicate_quarantine" / rel
            else:
                dst_path = primary_quarantine / src_path.name

            file_size = src_path.stat().st_size
            total_bytes += file_size
            move_tasks.append((src_path, dst_path, file_size, r.get("group_id", 0)))

        if not dry_run:
            # Parallelize file movement for speed across thousands of files
            workers = min(len(move_tasks), num_workers)
            with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
                futures = [pool.submit(cls._move_single_file, task) for task in move_tasks]
                for fut in as_completed(futures):
                    res = fut.result()
                    if res:
                        manifest_items.append(res)
        else:
            for src, dst, sz, gid in move_tasks:
                manifest_items.append(
                    QuarantineItem(
                        original_path=str(src),
                        quarantined_path=str(dst),
                        size_bytes=sz,
                        group_id=gid,
                    )
                )

        actual_bytes = sum(item.size_bytes for item in manifest_items)
        manifest = QuarantineManifest(
            timestamp=datetime.now(timezone.utc).isoformat(),
            base_dirs=[str(b) for b in base_roots],
            base_dir=str(primary_root),
            quarantine_dir=str(primary_quarantine),
            total_files_moved=len(manifest_items),
            total_bytes_moved=actual_bytes,
            items=manifest_items,
        )

        if not dry_run and manifest_items:
            primary_quarantine.mkdir(parents=True, exist_ok=True)
            manifest_path = primary_quarantine / "quarantine_manifest.json"
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest.model_dump(), f, indent=2)

        return manifest

    @classmethod
    def restore(
        cls,
        manifest_path_or_dict: str | Path | dict,
        dry_run: bool = False,
        num_workers: int = DEFAULT_NUM_WORKERS,
    ) -> int:
        """
        Reverses a previous quarantine in parallel using the saved manifest.
        Restores all duplicate files to their exact original locations.
        """
        if isinstance(manifest_path_or_dict, (str, Path)):
            from clairvoy.core.security import resolve_safe_path

            manifest_file = resolve_safe_path(manifest_path_or_dict, must_exist=True)
            with open(manifest_file, encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = manifest_path_or_dict

        items = data.get("items", [])

        if dry_run:
            return len(items)

        restored_count = 0
        workers = min(len(items), num_workers)
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            futures = [pool.submit(cls._restore_single_file, item) for item in items]
            for fut in as_completed(futures):
                if fut.result():
                    restored_count += 1

        return restored_count
