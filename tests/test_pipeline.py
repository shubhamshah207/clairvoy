"""
Unit & Integration Tests for Clairvoy Deduplication Pipeline & Composite Keeper Strategy.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from clairvoy.core.models import ActionType, FileEntry, ImageCategory, MatchType
from clairvoy.core.plugins import (
    BaseKeeperPlugin,
    BaseMatcherPlugin,
    DuplicateCluster,
    PluginRegistry,
)
from clairvoy.engines.pipeline import CompositeKeeperStrategy, DeduplicationPipeline
from clairvoy.plugins.exact_hash import ExactHashMatcherPlugin
from clairvoy.plugins.quarantine_action import SafeQuarantineActionPlugin


def test_pipeline_end_to_end(sample_dataset):
    """Verifies end-to-end pipeline run produces correct scan summary, groups, and reports."""
    root = sample_dataset["root"]
    registry = PluginRegistry()
    registry.register(ExactHashMatcherPlugin())
    registry.register(SafeQuarantineActionPlugin())

    pipeline = DeduplicationPipeline(paths=[root], registry=registry)
    summary = pipeline.run_scan()

    assert summary.total_files_scanned >= 3
    assert summary.exact_duplicate_groups == 1
    assert summary.total_duplicate_groups == 1
    assert summary.wasted_bytes > 0
    assert len(summary.groups) == 3  # 1 keeper + 2 duplicates

    # Check generated reports exist
    assert Path(summary.csv_report).exists()
    assert Path(summary.summary_json).exists()
    assert Path(summary.quarantine_script).exists()
    assert summary.csv_report.endswith("clairvoy_duplicates.csv")
    assert summary.summary_json.endswith("clairvoy_summary.json")
    assert summary.quarantine_script.endswith("clairvoy_quarantine.sh")

    # Check keeper record vs duplicate records
    keepers = [r for r in summary.groups if r.action == ActionType.KEEP]
    dupes = [r for r in summary.groups if r.action == ActionType.DUPLICATE]
    assert len(keepers) == 1
    assert len(dupes) == 2
    assert keepers[0].similarity == "100%"
    assert keepers[0].similarity_score == 1.0
    assert keepers[0].match_type == MatchType.EXACT_HASH


def test_pipeline_short_circuit_pruning(sample_dataset):
    """Verifies files clustered by earlier matchers are pruned from downstream candidate lists."""
    root = sample_dataset["root"]

    class TrackingMatcherPlugin(BaseMatcherPlugin):
        plugin_id = "tracker_matcher"
        display_name = "Tracking Matcher"
        priority_order = 50

        def __init__(self) -> None:
            super().__init__()
            self.received_candidates: list[str] = []

        def is_available(self) -> tuple[bool, str]:
            return True, "Tracking matcher is available."

        def filter_supported(self, files: list[FileEntry]) -> list[FileEntry]:
            return files

        def find_duplicates(
            self,
            candidates: list[FileEntry],
            all_indexed_files: list[FileEntry],
            context: dict[str, Any] | None = None,
        ) -> list[DuplicateCluster]:
            self.received_candidates = [f.path for f in candidates]
            return []

    registry = PluginRegistry()
    exact_matcher = ExactHashMatcherPlugin()  # priority 10
    tracker = TrackingMatcherPlugin()  # priority 50
    registry.register(exact_matcher)
    registry.register(tracker)

    pipeline = DeduplicationPipeline(paths=[root], registry=registry)
    summary = pipeline.run_scan()

    assert summary.exact_duplicate_groups == 1

    # In sample_dataset: document_original.txt, document_copy (1).txt, and another_copy.txt are exact duplicates.
    # unique_report.txt is unique.
    # Therefore, the 3 duplicate files must be pruned and NEVER passed to tracker!
    received_filenames = [Path(p).name for p in tracker.received_candidates]
    assert "document_original.txt" not in received_filenames
    assert "document_copy (1).txt" not in received_filenames
    assert "another_copy.txt" not in received_filenames
    assert "unique_report.txt" in received_filenames


def test_pipeline_composite_keeper(sample_dataset):
    """Verifies CompositeKeeperStrategy prefers clean original filenames over copy artifacts."""
    strategy = CompositeKeeperStrategy()
    assert strategy.plugin_id == "composite_keeper"
    assert strategy.is_available()[0] is True

    # Direct cluster test
    entry_orig = FileEntry(path="/photos/document_original.txt", size_bytes=1024)
    entry_copy = FileEntry(path="/photos/document_copy (1).txt", size_bytes=1024)
    cluster = DuplicateCluster(
        cluster_id=1,
        match_type=MatchType.EXACT_HASH,
        members=[entry_copy, entry_orig],
    )

    keeper, dupes = strategy.choose_keeper(cluster)
    assert Path(keeper.path).name == "document_original.txt"
    assert len(dupes) == 1
    assert Path(dupes[0].path).name == "document_copy (1).txt"

    # End-to-end pipeline keeper verification
    root = sample_dataset["root"]
    pipeline = DeduplicationPipeline(paths=[root])
    summary = pipeline.run_scan()

    keeper_record = next(r for r in summary.groups if r.action == ActionType.KEEP)
    assert Path(keeper_record.path).name == "document_original.txt"


def test_composite_keeper_scoring_penalties_and_bonuses():
    """Validates individual scoring rules of CompositeKeeperStrategy."""
    strategy = CompositeKeeperStrategy()

    clean = FileEntry(path="/storage/vacation/photo.jpg", size_bytes=2048)
    assert strategy.score_entry(clean, [clean]) == 100

    trash = FileEntry(path="/storage/trash/photo.jpg", size_bytes=2048)
    assert strategy.score_entry(trash, [trash]) == 100 - 500

    recycle = FileEntry(path="/storage/$recycle.bin/photo.jpg", size_bytes=2048)
    assert strategy.score_entry(recycle, [recycle]) == 100 - 500

    copy_paren = FileEntry(path="/storage/photo (2).jpg", size_bytes=2048)
    assert strategy.score_entry(copy_paren, [copy_paren]) == 100 - 20

    copy_dash = FileEntry(path="/storage/photo-copy.jpg", size_bytes=2048)
    assert strategy.score_entry(copy_dash, [copy_dash]) == 100 - 25

    edited = FileEntry(path="/storage/photo-edited.jpg", size_bytes=2048)
    assert strategy.score_entry(edited, [edited]) == 100 - 10

    thumb = FileEntry(path="/storage/photo_thumb.jpg", size_bytes=2048)
    assert strategy.score_entry(thumb, [thumb]) == 100 - 50

    photos_from = FileEntry(path="/storage/photos from 2024/photo.jpg", size_bytes=2048)
    assert strategy.score_entry(photos_from, [photos_from]) == 100 + 30


def test_composite_keeper_tie_breaking():
    """Verifies that between two otherwise equally scored files, the shorter filename wins."""
    strategy = CompositeKeeperStrategy()

    short_name = FileEntry(path="/storage/report.pdf", size_bytes=5000)
    long_name = FileEntry(path="/storage/report_final_final_v3.pdf", size_bytes=5000)

    cluster = DuplicateCluster(
        cluster_id=1,
        match_type=MatchType.EXACT_HASH,
        members=[long_name, short_name],
    )

    keeper, dupes = strategy.choose_keeper(cluster)
    assert keeper.path == short_name.path
    assert dupes[0].path == long_name.path


def test_pipeline_action_dispatch(sample_dataset):
    """Verifies execute_action('quarantine') safely moves duplicates and creates a manifest."""
    root = sample_dataset["root"]
    registry = PluginRegistry()
    registry.register(ExactHashMatcherPlugin())
    registry.register(SafeQuarantineActionPlugin())

    pipeline = DeduplicationPipeline(paths=[root], registry=registry)
    summary = pipeline.run_scan()

    result = pipeline.execute_action("quarantine", summary=summary)
    assert result.action_id == "quarantine"
    assert result.success_count == 2
    assert result.failed_count == 0
    assert result.manifest_path is not None
    assert Path(result.manifest_path).exists()

    # Verify keeper remained in place
    orig_file = root / "document_original.txt"
    assert orig_file.exists()

    # Verify duplicates were moved
    copy_file = root / "document_copy (1).txt"
    assert not copy_file.exists()
    nested_copy = root / "nested_folder" / "another_copy.txt"
    assert not nested_copy.exists()


def test_pipeline_action_hardlink(temp_workspace):
    """Verifies execute_action('hardlink') unifies duplicate inodes."""
    folder = temp_workspace / "hardlink_test"
    folder.mkdir()

    f1 = folder / "data_a.bin"
    f2 = folder / "data_b.bin"
    content = b"Hardlink test content payload 12345" * 100
    f1.write_bytes(content)
    f2.write_bytes(content)

    assert f1.stat().st_ino != f2.stat().st_ino

    pipeline = DeduplicationPipeline(paths=[folder])
    summary = pipeline.run_scan()

    assert summary.exact_duplicate_groups == 1

    result = pipeline.execute_action("hardlink", summary=summary)
    assert result.action_id == "hardlink"
    assert result.success_count == 1
    assert result.failed_count == 0

    # Inodes must now match
    assert f1.stat().st_ino == f2.stat().st_ino


def test_pipeline_multi_root(multi_root_dataset):
    """Verifies pipeline correctly handles multiple directory roots simultaneously."""
    root_a = multi_root_dataset["root_a"]
    root_b = multi_root_dataset["root_b"]

    pipeline = DeduplicationPipeline(paths=[root_a, root_b])
    summary = pipeline.run_scan()

    assert summary.total_files_scanned == 4
    assert summary.exact_duplicate_groups == 1
    assert summary.total_duplicate_groups == 1
    assert str(root_a) in summary.scanned_paths
    assert str(root_b) in summary.scanned_paths


def test_pipeline_progress_callback(sample_dataset):
    """Verifies the progress callback is called with stage, current, and total during execution."""
    root = sample_dataset["root"]
    events: list[tuple[str, int, int]] = []

    def callback(stage: str, current: int, total: int) -> None:
        events.append((stage, current, total))

    pipeline = DeduplicationPipeline(paths=[root])
    summary = pipeline.run_scan(progress_callback=callback)

    assert summary.total_files_scanned >= 3
    assert len(events) >= 3
    for stage, current, total in events:
        assert isinstance(stage, str)
        assert isinstance(current, int)
        assert isinstance(total, int)
        assert total >= current >= 0


def test_pipeline_custom_keeper_strategy(sample_dataset):
    """Verifies that passing a custom keeper strategy overrides default scoring behavior."""
    root = sample_dataset["root"]

    class ReverseKeeperStrategy(BaseKeeperPlugin):
        plugin_id = "reverse_keeper"

        def is_available(self) -> tuple[bool, str]:
            return True, "ok"

        def score_entry(self, entry: FileEntry, cluster: list[FileEntry]) -> int:
            # Explicitly favor copy filenames
            if "(1)" in entry.path:
                return 1000
            return 10

    custom_keeper = ReverseKeeperStrategy()
    pipeline = DeduplicationPipeline(paths=[root], keeper_strategy=custom_keeper)
    summary = pipeline.run_scan()

    keeper_record = next(r for r in summary.groups if r.action == ActionType.KEEP)
    assert "(1)" in keeper_record.path


def test_pipeline_default_registry_population(sample_dataset):
    """Verifies that an unconfigured pipeline automatically registers the default matcher & action suite."""
    root = sample_dataset["root"]
    pipeline = DeduplicationPipeline(paths=[root])

    matcher_ids = [m.plugin_id for m in pipeline.registry.get_matchers(enabled_only=False)]
    assert "exact_hash" in matcher_ids
    assert "photo_vision" in matcher_ids
    assert "video_matcher" in matcher_ids
    assert "archive_inspector" in matcher_ids
    assert "document_matcher" in matcher_ids

    action_ids = [a.plugin_id for a in pipeline.registry.get_actions(enabled_only=False)]
    assert "quarantine" in action_ids
    assert "hardlink" in action_ids


def test_pipeline_empty_and_no_duplicates(temp_workspace):
    """Verifies behavior on empty directory and directory with zero duplicates."""
    empty_dir = temp_workspace / "empty"
    empty_dir.mkdir()

    pipeline_empty = DeduplicationPipeline(paths=[empty_dir])
    summary_empty = pipeline_empty.run_scan()
    assert summary_empty.total_files_scanned == 0
    assert summary_empty.total_duplicate_groups == 0
    assert summary_empty.wasted_bytes == 0

    unique_dir = temp_workspace / "unique"
    unique_dir.mkdir()
    (unique_dir / "file1.txt").write_text("hello 1")
    (unique_dir / "file2.txt").write_text("world 2")

    pipeline_unique = DeduplicationPipeline(paths=[unique_dir])
    summary_unique = pipeline_unique.run_scan()
    assert summary_unique.total_files_scanned == 2
    assert summary_unique.total_duplicate_groups == 0


def test_pipeline_action_errors(sample_dataset):
    """Verifies error handling for missing actions and missing summaries."""
    root = sample_dataset["root"]
    pipeline = DeduplicationPipeline(paths=[root])

    with pytest.raises(ValueError, match="not found in registry"):
        pipeline.execute_action("nonexistent_action")

    # Action without scan run or summary
    fresh_pipeline = DeduplicationPipeline(paths=[root])
    with pytest.raises(ValueError, match="No scan summary or duplicate records provided"):
        fresh_pipeline.execute_action("quarantine")


def test_pipeline_document_matcher_integration(temp_workspace):
    """Verifies that DeduplicationPipeline correctly routes document files to DocumentTextMatcherPlugin,
    clusters content duplicates, updates content_duplicate_groups, and categorizes them as DOCUMENT.
    """
    doc_dir = temp_workspace / "docs"
    doc_dir.mkdir()

    csv_a = doc_dir / "data_a.csv"
    csv_b = doc_dir / "data_b.csv"
    csv_unique = doc_dir / "unique.csv"

    csv_a.write_text("id,name,value\n1,alpha,100\n2,beta,200\n3,gamma,300\n", encoding="utf-8")
    # csv_b has permuted rows so exact_hash will NOT match, but document_matcher will
    csv_b.write_text("id,name,value\n3,gamma,300\n1,alpha,100\n2,beta,200\n", encoding="utf-8")
    csv_unique.write_text("id,name,value\n9,omega,999\n", encoding="utf-8")

    pipeline = DeduplicationPipeline(paths=[doc_dir])
    summary = pipeline.run_scan()

    assert summary.total_files_scanned == 3
    assert summary.exact_duplicate_groups == 0
    assert summary.content_duplicate_groups == 1
    assert summary.total_duplicate_groups == 1
    assert summary.wasted_bytes > 0
    assert len(summary.groups) == 2  # 1 keeper + 1 duplicate

    keeper = next(r for r in summary.groups if r.action == ActionType.KEEP)
    dupe = next(r for r in summary.groups if r.action == ActionType.DUPLICATE)

    assert keeper.match_type == MatchType.CONTENT_NEAR_DUPLICATE
    assert dupe.match_type == MatchType.CONTENT_NEAR_DUPLICATE
    assert keeper.category == ImageCategory.DOCUMENT
    assert dupe.category == ImageCategory.DOCUMENT
    assert summary.category_breakdown.get(ImageCategory.DOCUMENT.value, 0) == 1


def test_pipeline_registers_run(sample_dataset, monkeypatch, tmp_path):
    """Verifies that running pipeline registers the scan run with RunManager."""
    from clairvoy.core.run_manager import RunManager

    test_history = tmp_path / "custom_runs.json"
    manager = RunManager(history_file=test_history)
    monkeypatch.setattr("clairvoy.core.run_manager.RunManager", lambda *args, **kwargs: manager)

    root = sample_dataset["root"]
    pipeline = DeduplicationPipeline(paths=[root])
    pipeline.run_scan()

    runs = manager.list_runs(auto_discover=False)
    assert len(runs) >= 1
    assert runs[0].total_duplicate_groups == 1
