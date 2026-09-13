"""
Clairvoy Storage Engine
High-throughput, hybrid deduplication pipeline supporting multi-directory parallel scanning,
parallel QuickHash/SHA-256 content verification, and Vision AI clustering.
"""

import csv
import hashlib
import json
import os
import re
import time
from collections import defaultdict
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from clairvoy.core.config import (
    DEFAULT_NUM_WORKERS,
    DEFAULT_SIMILARITY_THRESHOLD,
    EXCLUDED_DIR_NAMES,
    SUPPORTED_IMAGE_EXTENSIONS,
)
from clairvoy.core.models import (
    ActionType,
    DuplicateRecord,
    FileEntry,
    MatchType,
    ScanSummary,
)
from clairvoy.core.security import generate_hardened_quarantine_script, resolve_safe_paths
from clairvoy.engines.vision_engine import HAS_ML, VisionEngine


class StorageEngine:
    """
    Two-stage deduplication engine with multi-directory concurrent traversal:
      Stage 1: Multi-root tree scan -> Size filter -> Parallel QuickHash -> Parallel SHA-256
      Stage 2: Vision AI embedding cosine similarity on unmatched media files
    """

    def __init__(
        self,
        paths: str | Path | Iterable[str | Path],
        output_dir: str | None = None,
        enable_ml: bool = True,
        ml_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        num_workers: int = DEFAULT_NUM_WORKERS,
    ):
        self.target_paths: list[Path] = resolve_safe_paths(paths, must_exist=True)
        self.base_dir: Path = self.target_paths[0]
        self.output_dir: Path = Path(output_dir or (self.base_dir / "_dedupe_reports")).resolve()
        self.enable_ml = enable_ml and HAS_ML
        self.ml_threshold = ml_threshold
        self.num_workers = num_workers
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def compute_quick_hash(path: str) -> str:
        """Reads 64KB from head and 64KB from tail to create a fast preliminary fingerprint."""
        h = hashlib.md5()
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            if size <= 128 * 1024:
                h.update(f.read())
            else:
                h.update(f.read(64 * 1024))
                f.seek(size - 64 * 1024)
                h.update(f.read(64 * 1024))
        return h.hexdigest()

    @staticmethod
    def compute_full_sha256(path: str) -> str:
        """Computes complete SHA-256 digest in 1MB buffered blocks."""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def score_file_keeper(path: str, dimensions: tuple[int, int] | None = None) -> int:
        """
        Determines which file in a duplicate cluster should be retained (higher is better).
        Favors original filenames, organized folders, and higher image resolutions.
        """
        score = 100
        norm_path = path.replace("\\", "/").lower()

        # Penalize trash / junk directories
        if "/trash/" in norm_path or "/recycle" in norm_path:
            score -= 500
        if "photos from " in norm_path:
            score += 30

        # Filename artifacts
        filename = os.path.basename(path)
        if re.search(r"\(\d+\)", filename):
            score -= 20
        if "-copy" in filename.lower():
            score -= 25
        if "-edited" in filename.lower():
            score -= 10
        if "thumb" in filename.lower():
            score -= 50

        # Higher resolution is preferred
        if dimensions and dimensions[0] > 0:
            pixels = dimensions[0] * dimensions[1]
            score += min(50, int(pixels / 100_000))

        return score

    def _scan_directory_tree(self, root_dir: Path) -> tuple[list[FileEntry], list[str]]:
        """Indexes a directory tree using os.scandir to minimize filesystem metadata latency."""
        entries: list[FileEntry] = []
        media_paths: list[str] = []

        def _traverse(current: Path):
            try:
                with os.scandir(current) as it:
                    for entry in it:
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                if entry.name not in EXCLUDED_DIR_NAMES:
                                    _traverse(Path(entry.path))
                            elif entry.is_file(follow_symlinks=False):
                                stat = entry.stat(follow_symlinks=False)
                                sz = stat.st_size
                                if sz > 0:
                                    ext = Path(entry.name).suffix.lower()
                                    is_media = ext in SUPPORTED_IMAGE_EXTENSIONS
                                    p = str(Path(entry.path).resolve())
                                    entries.append(
                                        FileEntry(
                                            path=p,
                                            size_bytes=sz,
                                            is_media=is_media,
                                        )
                                    )
                                    if is_media:
                                        media_paths.append(p)
                        except (PermissionError, OSError):
                            continue
            except (PermissionError, OSError):
                return

        _traverse(root_dir)
        return entries, media_paths

    def scan_filesystem(self) -> tuple[list[FileEntry], list[str]]:
        """
        Recursively indexes all configured paths concurrently.
        If multiple roots are provided, scans them in parallel worker threads.
        If a single root is provided, scans its top-level subdirectories in parallel.
        """
        all_entries: list[FileEntry] = []
        all_media: list[str] = []

        sub_roots: list[Path] = []
        if len(self.target_paths) > 1:
            sub_roots = self.target_paths
        else:
            single_root = self.target_paths[0]
            # Discover top-level directories to scan concurrently
            try:
                with os.scandir(single_root) as it:
                    for e in it:
                        if e.is_dir(follow_symlinks=False) and e.name not in EXCLUDED_DIR_NAMES:
                            sub_roots.append(Path(e.path))
                        elif e.is_file(follow_symlinks=False):
                            stat = e.stat(follow_symlinks=False)
                            if stat.st_size > 0:
                                ext = Path(e.name).suffix.lower()
                                is_m = ext in SUPPORTED_IMAGE_EXTENSIONS
                                p_str = str(Path(e.path).resolve())
                                all_entries.append(
                                    FileEntry(path=p_str, size_bytes=stat.st_size, is_media=is_m)
                                )
                                if is_m:
                                    all_media.append(p_str)
            except (PermissionError, OSError):
                sub_roots = [single_root]

            if not sub_roots:
                sub_roots = [single_root]

        workers = min(len(sub_roots), self.num_workers)
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            futures = [pool.submit(self._scan_directory_tree, r) for r in sub_roots]
            for fut in as_completed(futures):
                entries, media = fut.result()
                all_entries.extend(entries)
                all_media.extend(media)

        return all_entries, all_media

    def _resolve_quarantine_destination(self, file_path_str: str) -> tuple[str, str]:
        """
        Determines the quarantine path preserving relative structure under its enclosing root.
        Returns: (target_quarantine_file_path, enclosing_quarantine_directory)
        """
        p = Path(file_path_str)
        enclosing_root: Path | None = None

        for root in self.target_paths:
            try:
                if p.is_relative_to(root):
                    enclosing_root = root
                    break
            except ValueError:
                continue

        if enclosing_root:
            rel = p.relative_to(enclosing_root)
            q_dir = enclosing_root / "_duplicate_quarantine"
            return str(q_dir / rel), str(q_dir)
        else:
            q_dir = self.base_dir / "_duplicate_quarantine"
            return str(q_dir / p.name), str(q_dir)

    def run(self) -> ScanSummary:
        """Executes the full two-stage deduplication pipeline across all specified paths."""
        t_start = time.time()
        paths_display = ", ".join(str(p) for p in self.target_paths)
        print(f"[*] Scanning {len(self.target_paths)} path(s): {paths_display}")

        all_files, media_files = self.scan_filesystem()
        print(f"[*] Indexed {len(all_files):,} files ({len(media_files):,} photos/media) across all paths.")

        # Stage 1: Size grouping
        print("[*] Stage 1: Detecting exact content duplicates (Parallel SHA-256)...")
        size_groups: dict[int, list[FileEntry]] = defaultdict(list)
        for entry in all_files:
            size_groups[entry.size_bytes].append(entry)

        collision_candidates = [
            entries for entries in size_groups.values() if len(entries) > 1
        ]

        # Parallel QuickHash on candidates
        quickhash_map: dict[tuple[int, str], list[FileEntry]] = defaultdict(list)
        if collision_candidates:
            flat_candidates = [e for grp in collision_candidates for e in grp]
            with ThreadPoolExecutor(max_workers=self.num_workers) as pool:
                hashes = list(
                    pool.map(self.compute_quick_hash, [e.path for e in flat_candidates])
                )
            for entry, qh in zip(flat_candidates, hashes, strict=False):
                entry.quick_hash = qh
                quickhash_map[(entry.size_bytes, qh)].append(entry)

        # Parallel Full SHA-256 on QuickHash matches
        full_hash_map: dict[tuple[int, str], list[FileEntry]] = defaultdict(list)
        exact_candidates = [grp for grp in quickhash_map.values() if len(grp) > 1]
        if exact_candidates:
            flat_exact = [e for grp in exact_candidates for e in grp]
            with ThreadPoolExecutor(max_workers=self.num_workers) as pool:
                sha_hashes = list(
                    pool.map(self.compute_full_sha256, [e.path for e in flat_exact])
                )
            for entry, sha in zip(flat_exact, sha_hashes, strict=False):
                entry.full_sha256 = sha
                full_hash_map[(entry.size_bytes, sha)].append(entry)

        exact_duplicate_groups = [
            grp for grp in full_hash_map.values() if len(grp) > 1
        ]
        print(f"[✓] Stage 1 complete: {len(exact_duplicate_groups)} exact duplicate sets found.")

        # Stage 2: Vision AI on unmatched media files
        ml_clusters: list[tuple[list[str], list[float], list[tuple[int, int]]]] = []
        if self.enable_ml and media_files:
            exact_matched_paths = {e.path for grp in exact_duplicate_groups for e in grp}
            unmatched_media = [p for p in media_files if p not in exact_matched_paths]
            if unmatched_media:
                print(
                    f"[*] Stage 2: Running local Vision AI (DINOv2) on {len(unmatched_media):,} photos..."
                )
                try:
                    vision_engine = VisionEngine(
                        threshold=self.ml_threshold,
                        num_workers=self.num_workers,
                    )
                    ml_clusters = vision_engine.find_near_duplicates(unmatched_media)
                except Exception as e:
                    print(f"[!] Vision AI processing error: {e}")

        # Assemble Output Records & Safe Quarantine Commands
        records: list[DuplicateRecord] = []
        quarantine_moves: list[tuple[str, str]] = []
        group_id = 1
        total_wasted_bytes = 0

        # Process Stage 1 Exact Duplicates
        for grp in exact_duplicate_groups:
            scored = sorted(
                [(self.score_file_keeper(e.path), e) for e in grp],
                key=lambda x: x[0],
                reverse=True,
            )
            keeper = scored[0][1]
            dupes = [x[1] for x in scored[1:]]

            # Keeper
            records.append(
                DuplicateRecord(
                    group_id=group_id,
                    match_type=MatchType.EXACT_HASH,
                    action=ActionType.KEEP,
                    similarity="100%",
                    similarity_score=1.0,
                    size_mb=round(keeper.size_bytes / (1024 * 1024), 3),
                    path=keeper.path,
                )
            )

            # Redundant Duplicates
            for d in dupes:
                total_wasted_bytes += d.size_bytes
                records.append(
                    DuplicateRecord(
                        group_id=group_id,
                        match_type=MatchType.EXACT_HASH,
                        action=ActionType.DUPLICATE,
                        similarity="100%",
                        similarity_score=1.0,
                        size_mb=round(d.size_bytes / (1024 * 1024), 3),
                        path=d.path,
                    )
                )
                dst_quarantine, _ = self._resolve_quarantine_destination(d.path)
                quarantine_moves.append((d.path, dst_quarantine))

            group_id += 1

        # Process Stage 2 Vision AI Clusters
        for paths, scores, dims in ml_clusters:
            scored = sorted(
                [
                    (self.score_file_keeper(p, d), p, sc, d)
                    for p, sc, d in zip(paths, scores, dims, strict=False)
                ],
                key=lambda x: x[0],
                reverse=True,
            )
            keeper_path, _, keeper_dim = scored[0][1], scored[0][2], scored[0][3]
            dupes = scored[1:]
            keeper_sz = os.path.getsize(keeper_path)

            records.append(
                DuplicateRecord(
                    group_id=group_id,
                    match_type=MatchType.VISUAL_AI_NEAR_DUPLICATE,
                    action=ActionType.KEEP,
                    similarity="100%",
                    similarity_score=1.0,
                    size_mb=round(keeper_sz / (1024 * 1024), 3),
                    path=keeper_path,
                    dimensions=f"{keeper_dim[0]}x{keeper_dim[1]}" if keeper_dim[0] > 0 else None,
                )
            )

            for _, dp, sc, d in dupes:
                dsz = os.path.getsize(dp)
                total_wasted_bytes += dsz
                records.append(
                    DuplicateRecord(
                        group_id=group_id,
                        match_type=MatchType.VISUAL_AI_NEAR_DUPLICATE,
                        action=ActionType.DUPLICATE,
                        similarity=f"{sc * 100:.1f}%",
                        similarity_score=round(sc, 4),
                        size_mb=round(dsz / (1024 * 1024), 3),
                        path=dp,
                        dimensions=f"{d[0]}x{d[1]}" if d[0] > 0 else None,
                    )
                )
                dst_quarantine, _ = self._resolve_quarantine_destination(dp)
                quarantine_moves.append((dp, dst_quarantine))

            group_id += 1

        # Write CSV Report
        csv_path = self.output_dir / "duplicates_report.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "group_id",
                    "match_type",
                    "action",
                    "similarity",
                    "size_mb",
                    "path",
                    "dimensions",
                ],
            )
            writer.writeheader()
            for r in records:
                row = r.model_dump()
                row.pop("similarity_score", None)
                writer.writerow(row)

        # Write Safe Quarantine Script (Hardened & Escaped)
        sh_path = self.output_dir / "quarantine_duplicates.sh"
        script_content = generate_hardened_quarantine_script(
            moves=quarantine_moves,
            base_dir=[str(p) for p in self.target_paths],
            quarantine_dir=str(self.base_dir / "_duplicate_quarantine"),
        )
        with open(sh_path, "w", encoding="utf-8") as f:
            f.write(script_content)
        sh_path.chmod(0o755)

        elapsed = time.time() - t_start
        summary = ScanSummary(
            scanned_paths=[str(p) for p in self.target_paths],
            scanned_dir=str(self.base_dir),
            total_files_scanned=len(all_files),
            media_files_scanned=len(media_files),
            exact_duplicate_groups=len(exact_duplicate_groups),
            visual_ai_groups=len(ml_clusters),
            total_duplicate_groups=len(exact_duplicate_groups) + len(ml_clusters),
            wasted_bytes=total_wasted_bytes,
            wasted_mb=round(total_wasted_bytes / (1024 * 1024), 2),
            wasted_gb=round(total_wasted_bytes / (1024 * 1024 * 1024), 3),
            duration_seconds=round(elapsed, 2),
            csv_report=str(csv_path),
            summary_json=str(self.output_dir / "duplicates_summary.json"),
            quarantine_script=str(sh_path),
            groups=records,
        )

        # Write JSON Summary
        with open(summary.summary_json, "w", encoding="utf-8") as f:
            json.dump(summary.model_dump(), f, indent=2)

        print(f"\n[✓] Scan completed in {elapsed:.1f}s across {len(self.target_paths)} path(s)")
        print(f" • Exact Duplicate Sets: {len(exact_duplicate_groups)}")
        print(f" • Visual AI Clusters: {len(ml_clusters)}")
        print(f" • Total Recoverable Space: {summary.wasted_mb} MB ({summary.wasted_gb} GB)")
        print(f" • CSV Report: {csv_path}")
        print(f" • Summary JSON: {summary.summary_json}")
        print(f" • Safe Quarantine Script: {sh_path}")

        return summary
