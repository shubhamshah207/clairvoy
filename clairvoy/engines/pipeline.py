"""
Clairvoy Pluggable Deduplication Engine Pipeline & Composite Keeper Strategy.

Orchestrates multi-root filesystem traversal, priority-ordered matcher dispatching with
short-circuit candidate pruning, keeper retention scoring, report generation, and action resolution.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import re
import time
from collections import defaultdict
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from clairvoy.core.config import (
    DEFAULT_NUM_WORKERS,
    EXCLUDED_DIR_NAMES,
    SUPPORTED_IMAGE_EXTENSIONS,
)
from clairvoy.core.models import (
    ActionType,
    DuplicateRecord,
    FileEntry,
    ImageCategory,
    MatchType,
    ScanSummary,
)
from clairvoy.core.plugins import (
    ActionResult,
    BaseKeeperPlugin,
    DuplicateCluster,
    PluginRegistry,
)
from clairvoy.core.security import generate_hardened_quarantine_script, resolve_safe_paths
from clairvoy.engines.classifier_engine import ClassifierEngine
from clairvoy.plugins.archive_inspector import ArchiveInspectorMatcherPlugin
from clairvoy.plugins.document_matcher import DocumentTextMatcherPlugin
from clairvoy.plugins.exact_hash import ExactHashMatcherPlugin
from clairvoy.plugins.hardlink_action import HardlinkActionPlugin
from clairvoy.plugins.photo_vision import PhotoVisionMatcherPlugin
from clairvoy.plugins.quarantine_action import SafeQuarantineActionPlugin
from clairvoy.plugins.video_matcher import SUPPORTED_VIDEO_EXTENSIONS, VideoKeyframeMatcherPlugin

logger = logging.getLogger(__name__)


class CompositeKeeperStrategy(BaseKeeperPlugin):
    """Keeper retention strategy scoring candidate files based on filename cleanliness and directory seniority."""

    plugin_id: str = "composite_keeper"
    display_name: str = "Composite Keeper Strategy"
    version: str = "0.1.0"
    author: str = "Clairvoy Team"
    description: str = "Scores files based on filename cleanliness, directory seniority, and media resolution"

    def is_available(self) -> tuple[bool, str]:
        """Validate system dependencies and runtime availability."""
        return True, "Composite keeper strategy is available."

    def score_entry(self, entry: FileEntry, cluster: list[FileEntry] | None = None) -> int:
        """Score an entry within a cluster. Higher integer score indicates a preferred keeper."""
        score = 100
        norm_path = entry.path.replace("\\", "/").lower()
        filename = Path(entry.path).name
        lower_name = filename.lower()

        # Penalize trash / recycle junk directories
        if "/trash/" in norm_path or "trash" in norm_path or "recycle" in norm_path:
            score -= 500

        # Bonus for organized photo folders
        if "photos from" in norm_path:
            score += 30

        # Filename artifacts
        stem = Path(filename).stem
        if re.search(r"\(\d+\)|[-_ ]\d+$", stem):
            score -= 20
        if re.search(r"[-_ ]copy|\bcopy\b|[-_ ]dupe|\bdupe\b|\bduplicate\b", lower_name):
            score -= 25
        if "-edited" in lower_name:
            score -= 10
        if "thumb" in lower_name:
            score -= 50

        entry.keeper_score = score
        return score

    def choose_keeper(self, cluster: DuplicateCluster) -> tuple[FileEntry, list[FileEntry]]:
        """Score all cluster members and designate the highest-scoring file as the keeper."""
        if not cluster.members:
            raise ValueError("Cannot choose keeper from an empty cluster")

        dims_map = cluster.metadata.get("dimensions", {})

        def _sort_key(e: FileEntry) -> tuple[int, int, int, str]:
            base_score = self.score_entry(e, cluster.members)
            dim = dims_map.get(e.path)
            res_bonus = 0
            if dim and isinstance(dim, (list, tuple)) and len(dim) >= 2 and dim[0] > 0:
                pixels = dim[0] * dim[1]
                res_bonus = min(50, int(pixels / 100_000))
            final_score = base_score + res_bonus
            e.keeper_score = final_score
            # Sort order:
            # 1. Higher score first (-final_score)
            # 2. Directory seniority (shallower path first -> len(parts))
            # 3. Shorter filename first (len(name))
            # 4. Alphabetical tie-breaker (e.path)
            return (-final_score, len(Path(e.path).parts), len(Path(e.path).name), e.path)

        scored = sorted(cluster.members, key=_sort_key)
        return scored[0], scored[1:]


class DeduplicationPipeline:
    """Orchestrator for tiered duplicate matching, keeper scoring, and action dispatching."""

    def __init__(
        self,
        paths: str | Path | Iterable[str | Path],
        registry: PluginRegistry | None = None,
        keeper_strategy: BaseKeeperPlugin | None = None,
        output_dir: str | Path | None = None,
        num_workers: int = DEFAULT_NUM_WORKERS,
    ) -> None:
        self.target_paths: list[Path] = resolve_safe_paths(paths, must_exist=True)
        if not self.target_paths:
            raise ValueError("At least one valid target path must be provided")

        self.base_dir: Path = self.target_paths[0]
        self.output_dir: Path = (
            Path(output_dir).resolve()
            if output_dir is not None
            else (self.base_dir / "_dedupe_reports").resolve()
        )
        self.num_workers = num_workers
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Set up dynamic registry
        if registry is not None:
            self.registry = registry
        else:
            self.registry = PluginRegistry.get_instance()

        # If registry has no matchers registered, populate default matcher suite
        if len(self.registry.get_matchers(enabled_only=False)) == 0:
            self.registry.register(ExactHashMatcherPlugin())
            self.registry.register(PhotoVisionMatcherPlugin())
            self.registry.register(VideoKeyframeMatcherPlugin())
            self.registry.register(ArchiveInspectorMatcherPlugin())
            self.registry.register(DocumentTextMatcherPlugin())

        # If registry has no actions registered, populate default action suite
        if len(self.registry.get_actions(enabled_only=False)) == 0:
            self.registry.register(SafeQuarantineActionPlugin())
            self.registry.register(HardlinkActionPlugin())

        # Set up keeper strategy
        self.keeper_strategy: BaseKeeperPlugin = (
            keeper_strategy if keeper_strategy is not None else CompositeKeeperStrategy()
        )
        if self.registry.get_plugin(self.keeper_strategy.plugin_id) is None:
            self.registry.register(self.keeper_strategy)

        self._last_summary: ScanSummary | None = None

    def _scan_directory_tree(self, root_dir: Path) -> tuple[list[FileEntry], list[str]]:
        """Indexes a directory tree using os.scandir for high metadata throughput."""
        entries: list[FileEntry] = []
        media_paths: list[str] = []

        def _traverse(current: Path) -> None:
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
                                    is_media = (
                                        ext in SUPPORTED_IMAGE_EXTENSIONS
                                        or ext in SUPPORTED_VIDEO_EXTENSIONS
                                    )
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
        """Concurrently indexes all configured target paths."""
        all_entries: list[FileEntry] = []
        all_media: list[str] = []

        sub_roots: list[Path] = []
        if len(self.target_paths) > 1:
            sub_roots = self.target_paths
        else:
            single_root = self.target_paths[0]
            try:
                with os.scandir(single_root) as it:
                    for e in it:
                        if e.is_dir(follow_symlinks=False) and e.name not in EXCLUDED_DIR_NAMES:
                            sub_roots.append(Path(e.path))
                        elif e.is_file(follow_symlinks=False):
                            try:
                                stat = e.stat(follow_symlinks=False)
                                if stat.st_size > 0:
                                    ext = Path(e.name).suffix.lower()
                                    is_m = (
                                        ext in SUPPORTED_IMAGE_EXTENSIONS
                                        or ext in SUPPORTED_VIDEO_EXTENSIONS
                                    )
                                    p_str = str(Path(e.path).resolve())
                                    all_entries.append(
                                        FileEntry(path=p_str, size_bytes=stat.st_size, is_media=is_m)
                                    )
                                    if is_m:
                                        all_media.append(p_str)
                            except (PermissionError, OSError):
                                continue
            except (PermissionError, OSError):
                sub_roots = []

        if sub_roots:
            workers = min(len(sub_roots), self.num_workers)
            total_sub = len(sub_roots)
            done_sub = 0
            with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
                futures = [pool.submit(self._scan_directory_tree, r) for r in sub_roots]
                for fut in as_completed(futures):
                    entries, media = fut.result()
                    all_entries.extend(entries)
                    all_media.extend(media)
                    done_sub += 1
                    print(
                        f"\r    [>] Indexed {done_sub}/{total_sub} top-level folders ({len(all_entries):,} files)...",
                        end="",
                        flush=True,
                    )
            print()

        return all_entries, all_media

    def _resolve_quarantine_destination(self, file_path_str: str) -> tuple[str, str]:
        """Resolves target path under the enclosing root's _duplicate_quarantine directory."""
        p = Path(file_path_str)
        enclosing_root: Path | None = None

        for root in self.target_paths:
            try:
                if p.is_relative_to(root):
                    enclosing_root = root
                    break
            except (ValueError, TypeError):
                continue

        if enclosing_root:
            rel = p.relative_to(enclosing_root)
            q_dir = enclosing_root / "_duplicate_quarantine"
            return str(q_dir / rel), str(q_dir)
        else:
            q_dir = self.base_dir / "_duplicate_quarantine"
            return str(q_dir / p.name), str(q_dir)

    def run_scan(
        self,
        progress_callback: Callable[[str, int, int], None] | None = None,
    ) -> ScanSummary:
        """Executes the deduplication scan using chained matchers and keeper scoring."""
        t_start = time.time()
        print(f"[*] Stage 1/3: Traversing & indexing filesystem tree across {len(self.target_paths)} target path(s)...")
        if progress_callback:
            progress_callback("Scanning filesystem", 0, len(self.target_paths))

        all_files, media_files = self.scan_filesystem()
        print(f"    [✓] Filesystem indexed: {len(all_files):,} files ({len(media_files):,} media items) in {time.time() - t_start:.1f}s.\n")

        if progress_callback:
            progress_callback("Filesystem indexed", len(all_files), max(1, len(all_files)))

        # Classify media files
        classification_map: dict[str, ImageCategory] = {}
        if media_files:
            print(f"[*] Pre-classifying {len(media_files):,} media items (EXIF & Content Type)...")
            try:
                classification_map = ClassifierEngine.classify_batch(
                    media_files,
                    num_workers=self.num_workers,
                )
                print("    [✓] Media classification complete.\n")
            except Exception as exc:
                logger.warning("Error during batch classification: %s", exc)

        # Retrieve enabled and available matchers in ascending priority_order
        matchers = self.registry.get_matchers(enabled_only=True, available_only=True)
        total_matchers = len(matchers)

        print(f"[*] Stage 2/3: Executing Chained Matcher Tiers ({total_matchers} tiers active):")

        all_clusters: list[DuplicateCluster] = []
        matched_paths: set[str] = set()
        next_cluster_id = 1

        for idx, matcher in enumerate(matchers, start=1):
            if progress_callback:
                progress_callback(
                    f"Running matcher: {matcher.display_name}",
                    idx - 1,
                    max(1, total_matchers),
                )

            # Short-circuit pruning invariant: exclude files already clustered by previous matchers
            candidates = [f for f in all_files if f.path not in matched_paths]
            supported = matcher.filter_supported(candidates)

            print(f" [>] Tier {idx}/{total_matchers}: {matcher.display_name} (Priority {matcher.priority_order})...")

            if not supported:
                print(f"     [-] No matching candidate files for {matcher.plugin_id}. Skipped.")
                continue

            print(f"     Evaluating {len(supported):,} candidate files against {matcher.plugin_id}...")
            t_mat = time.time()
            context: dict[str, Any] = {
                "start_cluster_id": next_cluster_id,
                "num_workers": self.num_workers,
            }
            clusters = matcher.find_duplicates(supported, all_files, context=context)

            for cluster in clusters:
                matched_paths.update(m.path for m in cluster.members)
                all_clusters.append(cluster)
                next_cluster_id += 1

            print(f"     [✓] Tier {idx} complete: Found {len(clusters):,} duplicate cluster(s) in {time.time() - t_mat:.1f}s.")

        print("\n[*] Stage 3/3: Evaluating Keepers & Designating Duplicates...")
        if progress_callback:
            progress_callback(
                "Processing duplicate clusters",
                total_matchers,
                max(1, total_matchers),
            )

        records: list[DuplicateRecord] = []
        quarantine_moves: list[tuple[str, str]] = []
        total_wasted_bytes = 0
        category_breakdown: dict[str, int] = defaultdict(int)

        for cluster in all_clusters:
            if hasattr(self.keeper_strategy, "choose_keeper"):
                keeper, dupes = self.keeper_strategy.choose_keeper(cluster)
            else:
                scored = sorted(
                    cluster.members,
                    key=lambda e: (
                        -self.keeper_strategy.score_entry(e, cluster.members),
                        len(Path(e.path).name),
                        e.path,
                    ),
                )
                keeper, dupes = scored[0], scored[1:]

            # Map similarity scores
            member_sim_map = {}
            if len(cluster.similarity_scores) == len(cluster.members):
                member_sim_map = {
                    m.path: sim
                    for m, sim in zip(cluster.members, cluster.similarity_scores, strict=False)
                }

            dims_map = cluster.metadata.get("dimensions", {})

            def _get_dim_str(path: str, dm: dict[str, Any]) -> str | None:
                d = dm.get(path)
                if d and isinstance(d, (list, tuple)) and len(d) >= 2 and d[0] > 0:
                    return f"{d[0]}x{d[1]}"
                return None

            # Keeper record
            k_cat = classification_map.get(
                keeper.path,
                ImageCategory.PHOTO if keeper.is_media else ImageCategory.FILE,
            )
            if cluster.match_type == MatchType.CONTENT_NEAR_DUPLICATE:
                if keeper.category == ImageCategory.FILE:
                    keeper.category = ImageCategory.DOCUMENT
                if k_cat == ImageCategory.FILE:
                    k_cat = ImageCategory.DOCUMENT
            records.append(
                DuplicateRecord(
                    group_id=cluster.cluster_id,
                    match_type=cluster.match_type,
                    action=ActionType.KEEP,
                    similarity="100%",
                    similarity_score=1.0,
                    size_mb=round(keeper.size_bytes / (1024 * 1024), 3),
                    path=keeper.path,
                    dimensions=_get_dim_str(keeper.path, dims_map),
                    category=k_cat,
                )
            )

            # Duplicate records
            for d in dupes:
                d_cat = classification_map.get(
                    d.path,
                    ImageCategory.PHOTO if d.is_media else ImageCategory.FILE,
                )
                if cluster.match_type == MatchType.CONTENT_NEAR_DUPLICATE:
                    if d.category == ImageCategory.FILE:
                        d.category = ImageCategory.DOCUMENT
                    if d_cat == ImageCategory.FILE:
                        d_cat = ImageCategory.DOCUMENT
                category_breakdown[d_cat.value] += 1
                total_wasted_bytes += d.size_bytes

                sim_score = member_sim_map.get(d.path, 1.0)
                if cluster.match_type == MatchType.EXACT_HASH or sim_score >= 0.9999:
                    sim_str = "100%"
                else:
                    sim_str = f"{sim_score * 100:.1f}%"

                records.append(
                    DuplicateRecord(
                        group_id=cluster.cluster_id,
                        match_type=cluster.match_type,
                        action=ActionType.DUPLICATE,
                        similarity=sim_str,
                        similarity_score=round(sim_score, 4),
                        size_mb=round(d.size_bytes / (1024 * 1024), 3),
                        path=d.path,
                        dimensions=_get_dim_str(d.path, dims_map),
                        category=d_cat,
                    )
                )

                if "::" not in d.path:
                    dst_quarantine, _ = self._resolve_quarantine_destination(d.path)
                    quarantine_moves.append((d.path, dst_quarantine))

        # Write CSV report
        csv_path = self.output_dir / "clairvoy_duplicates.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "group_id",
                    "match_type",
                    "action",
                    "category",
                    "similarity",
                    "size_mb",
                    "path",
                    "dimensions",
                ],
            )
            writer.writeheader()
            for r in records:
                row = r.model_dump()
                row = {k: v for k, v in row.items() if k in writer.fieldnames}
                writer.writerow(row)

        # Write Safe Quarantine Script
        sh_path = self.output_dir / "clairvoy_quarantine.sh"
        script_content = generate_hardened_quarantine_script(
            moves=quarantine_moves,
            base_dir=[str(p) for p in self.target_paths],
            quarantine_dir=str(self.base_dir / "_duplicate_quarantine"),
        )
        with open(sh_path, "w", encoding="utf-8") as f:
            f.write(script_content)
        sh_path.chmod(0o755)

        elapsed = time.time() - t_start
        exact_duplicate_groups = sum(
            1 for c in all_clusters if c.match_type == MatchType.EXACT_HASH
        )
        visual_ai_groups = sum(
            1 for c in all_clusters if c.match_type == MatchType.VISUAL_AI_NEAR_DUPLICATE
        )
        content_duplicate_groups = sum(
            1 for c in all_clusters if c.match_type == MatchType.CONTENT_NEAR_DUPLICATE
        )

        summary_json_path = self.output_dir / "clairvoy_summary.json"
        summary = ScanSummary(
            scanned_paths=[str(p) for p in self.target_paths],
            scanned_dir=str(self.base_dir),
            total_files_scanned=len(all_files),
            media_files_scanned=len(media_files),
            exact_duplicate_groups=exact_duplicate_groups,
            visual_ai_groups=visual_ai_groups,
            content_duplicate_groups=content_duplicate_groups,
            total_duplicate_groups=len(all_clusters),
            wasted_bytes=total_wasted_bytes,
            wasted_mb=round(total_wasted_bytes / (1024 * 1024), 2),
            wasted_gb=round(total_wasted_bytes / (1024 * 1024 * 1024), 3),
            duration_seconds=round(elapsed, 2),
            csv_report=str(csv_path),
            summary_json=str(summary_json_path),
            quarantine_script=str(sh_path),
            groups=records,
            category_breakdown=dict(category_breakdown),
        )

        # Write JSON Summary
        with open(summary_json_path, "w", encoding="utf-8") as f:
            json.dump(summary.model_dump(), f, indent=2)

        try:
            from clairvoy.core.run_manager import RunManager

            RunManager().register_run(summary)
        except Exception as e:
            logger.warning("Failed to register run with RunManager: %s", e)

        self._last_summary = summary
        return summary

    def execute_action(
        self,
        action_id: str,
        summary: ScanSummary | list[DuplicateRecord] | None = None,
        dry_run: bool = False,
    ) -> ActionResult:
        """Dispatches duplicate resolution to the registered action plugin."""
        action = self.registry.get_action(action_id)
        if action is None:
            raise ValueError(f"Action plugin '{action_id}' not found in registry")

        plan = summary if summary is not None else self._last_summary
        if plan is None:
            raise ValueError("No scan summary or duplicate records provided to execute action on")

        return action.execute(
            plan=plan,
            base_dirs=self.target_paths,
            dry_run=dry_run,
        )


__all__ = [
    "CompositeKeeperStrategy",
    "DeduplicationPipeline",
]
