"""
Unit Tests for Storage Engine and Hashing
"""

from pathlib import Path

from clairvoy.core.models import ActionType
from clairvoy.engines.storage_engine import StorageEngine


def test_quick_hash_and_sha256(temp_workspace):
    p = temp_workspace / "sample.bin"
    p.write_bytes(b"hello world" * 1000)

    qh = StorageEngine.compute_quick_hash(str(p))
    sha = StorageEngine.compute_full_sha256(str(p))

    assert len(qh) == 32  # MD5 hex
    assert len(sha) == 64  # SHA256 hex


def test_keeper_scoring():
    # Regular file
    score_orig = StorageEngine.score_file_keeper("/path/to/photos/vacation.jpg")
    # File with (1)
    score_dupe = StorageEngine.score_file_keeper("/path/to/photos/vacation (1).jpg")
    # File in trash
    score_trash = StorageEngine.score_file_keeper("/path/to/trash/vacation.jpg")

    assert score_orig > score_dupe
    assert score_orig > score_trash


def test_storage_engine_exact_dedup(sample_dataset):
    root = sample_dataset["root"]
    engine = StorageEngine(paths=str(root), enable_ml=False)
    summary = engine.run()

    assert summary.total_files_scanned == 4
    assert summary.exact_duplicate_groups == 1
    assert summary.visual_ai_groups == 0
    assert summary.total_duplicate_groups == 1
    assert summary.wasted_bytes > 0

    # Verify report files were created
    assert Path(summary.csv_report).exists()
    assert Path(summary.summary_json).exists()
    assert Path(summary.quarantine_script).exists()

    # Check that keep vs duplicate actions are tagged
    actions = [r.action for r in summary.groups]
    assert ActionType.KEEP in actions
    assert ActionType.DUPLICATE in actions


def test_storage_engine_multi_root_parallel(multi_root_dataset):
    root_a = multi_root_dataset["root_a"]
    root_b = multi_root_dataset["root_b"]

    engine = StorageEngine(paths=[root_a, root_b], enable_ml=False)
    summary = engine.run()

    assert summary.total_files_scanned == 4
    assert summary.exact_duplicate_groups == 1
    assert len(summary.scanned_paths) == 2
    assert str(root_a.resolve()) in summary.scanned_paths
    assert str(root_b.resolve()) in summary.scanned_paths

    # Verify cross-folder duplicate was detected
    paths_in_dupes = [r.path for r in summary.groups]
    assert str(multi_root_dataset["shared_file_a"].resolve()) in paths_in_dupes
    assert str(multi_root_dataset["shared_file_b"].resolve()) in paths_in_dupes


def test_storage_engine_flat_directory_no_duplicates(temp_workspace):
    # Tests that flat directories with unique files are not double-scanned
    (temp_workspace / "u1.txt").write_text("unique content 1")
    (temp_workspace / "u2.txt").write_text("unique content 2")
    (temp_workspace / "u3.txt").write_text("unique content 3")

    engine = StorageEngine(paths=temp_workspace, enable_ml=False)
    summary = engine.run()

    assert summary.total_files_scanned == 3
    assert summary.total_duplicate_groups == 0

