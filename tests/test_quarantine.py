"""
Unit Tests for Reversible Quarantine and Restore Engine
"""

from pathlib import Path

from clairvoy.engines.quarantine import QuarantineEngine
from clairvoy.engines.storage_engine import StorageEngine


def test_quarantine_and_restore(sample_dataset):
    root = sample_dataset["root"]
    engine = StorageEngine(paths=str(root), enable_ml=False)
    summary = engine.run()

    assert summary.exact_duplicate_groups == 1

    # Execute quarantine
    manifest = QuarantineEngine.execute(summary, base_dir=str(root))
    assert manifest.total_files_moved == 2  # 3 identical files -> 1 keeper, 2 duplicates moved
    assert Path(manifest.quarantine_dir).exists()

    # Verify duplicate files no longer in original directory
    for item in manifest.items:
        assert not Path(item.original_path).exists()
        assert Path(item.quarantined_path).exists()

    # Now restore from manifest
    manifest_file = Path(manifest.quarantine_dir) / "quarantine_manifest.json"
    restored_count = QuarantineEngine.restore(manifest_file)
    assert restored_count == 2

    # Verify files are back in original positions
    for item in manifest.items:
        assert Path(item.original_path).exists()


def test_multi_root_quarantine_and_restore(multi_root_dataset):
    root_a = multi_root_dataset["root_a"]
    root_b = multi_root_dataset["root_b"]

    engine = StorageEngine(paths=[root_a, root_b], enable_ml=False)
    summary = engine.run()

    manifest = QuarantineEngine.execute(summary)
    assert manifest.total_files_moved == 1

    # Check that the quarantined duplicate is moved
    moved_item = manifest.items[0]
    assert not Path(moved_item.original_path).exists()
    assert Path(moved_item.quarantined_path).exists()

    # Restore from manifest dict
    restored = QuarantineEngine.restore(manifest.model_dump())
    assert restored == 1
    assert Path(moved_item.original_path).exists()


def test_quarantine_prevents_destination_clobbering(temp_workspace):
    src = temp_workspace / "duplicate.txt"
    dst = temp_workspace / "quarantine" / "duplicate.txt"
    src.write_text("content to quarantine")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text("existing pre-existing file in quarantine")

    # Call _move_single_file directly
    res = QuarantineEngine._move_single_file((src, dst, 10, 1))
    assert res is not None
    # Verify pre-existing file was NOT overwritten
    assert dst.read_text() == "existing pre-existing file in quarantine"
    # Verify quarantined file was moved to a non-colliding path
    assert Path(res.quarantined_path).exists()
    assert res.quarantined_path != str(dst)
    assert Path(res.quarantined_path).read_text() == "content to quarantine"

