"""
Unit Tests for Reversible Quarantine and Restore Engine
"""

from pathlib import Path

from clairvoy.engines.quarantine import QuarantineEngine
from clairvoy.engines.storage_engine import StorageEngine


def test_quarantine_and_restore(sample_dataset):
    root = sample_dataset["root"]
    engine = StorageEngine(base_dir=str(root), enable_ml=False)
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
