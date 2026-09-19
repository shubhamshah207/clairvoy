"""
Unit and integration tests for DeleteEngine:
Soft delete (Trash + 1-click restore) and Permanent Deletion with audit logging.
"""

import json
from pathlib import Path
import pytest

from clairvoy.core.models import ActionType, DuplicateRecord, MatchType, ScanSummary
from clairvoy.core.security import SecurityError
from clairvoy.engines.delete_engine import DeleteEngine


@pytest.fixture
def delete_test_dataset(tmp_path: Path):
    root_dir = tmp_path / "dataset"
    root_dir.mkdir(parents=True, exist_ok=True)

    file_keeper = root_dir / "photo_original.jpg"
    file_keeper.write_text("keeper high-res content original photo")

    file_dupe1 = root_dir / "photo_copy1.jpg"
    file_dupe1.write_text("duplicate photo copy 1")

    file_dupe2 = root_dir / "subfolder" / "photo_copy2.jpg"
    file_dupe2.parent.mkdir(parents=True, exist_ok=True)
    file_dupe2.write_text("duplicate photo copy 2 in subfolder")

    summary = ScanSummary(
        scanned_paths=[str(root_dir)],
        scanned_dir=str(root_dir),
        total_files_scanned=3,
        media_files_scanned=3,
        exact_duplicate_groups=1,
        visual_ai_groups=0,
        content_duplicate_groups=0,
        total_duplicate_groups=1,
        wasted_bytes=len(file_dupe1.read_bytes()) + len(file_dupe2.read_bytes()),
        wasted_mb=0.001,
        wasted_gb=0.0,
        duration_seconds=0.1,
        csv_report=str(root_dir / "duplicates.csv"),
        summary_json=str(root_dir / "summary.json"),
        quarantine_script=str(root_dir / "quarantine.sh"),
        groups=[
            DuplicateRecord(
                group_id=1,
                match_type=MatchType.EXACT_HASH,
                action=ActionType.KEEP,
                similarity="100%",
                similarity_score=1.0,
                size_mb=0.001,
                path=str(file_keeper),
            ),
            DuplicateRecord(
                group_id=1,
                match_type=MatchType.EXACT_HASH,
                action=ActionType.DUPLICATE,
                similarity="100%",
                similarity_score=1.0,
                size_mb=0.001,
                path=str(file_dupe1),
            ),
            DuplicateRecord(
                group_id=1,
                match_type=MatchType.EXACT_HASH,
                action=ActionType.DUPLICATE,
                similarity="100%",
                similarity_score=1.0,
                size_mb=0.001,
                path=str(file_dupe2),
            ),
        ],
    )

    return {
        "root": root_dir,
        "keeper": file_keeper,
        "dupe1": file_dupe1,
        "dupe2": file_dupe2,
        "summary": summary,
    }


def test_soft_trash_deletion_and_restore(delete_test_dataset):
    ds = delete_test_dataset
    manifest = DeleteEngine.execute(
        summary_or_records=ds["summary"],
        base_dir=ds["root"],
        mode="trash",
    )

    assert manifest.total_files_deleted == 2
    assert manifest.total_bytes_freed > 0
    assert manifest.mode == "trash"
    assert not ds["dupe1"].exists()
    assert not ds["dupe2"].exists()
    assert ds["keeper"].exists()  # Keeper must never be deleted!

    # Check that trash files exist
    assert any(Path(item.trash_path).exists() for item in manifest.items if item.trash_path)

    # Now restore from trash
    restored_count = DeleteEngine.restore(manifest.audit_file)
    assert restored_count == 2
    assert ds["dupe1"].exists()
    assert ds["dupe2"].exists()
    assert ds["keeper"].exists()


def test_permanent_deletion_unlinks_files_and_writes_audit(delete_test_dataset):
    ds = delete_test_dataset
    manifest = DeleteEngine.execute(
        summary_or_records=ds["summary"],
        base_dir=ds["root"],
        mode="permanent",
    )

    assert manifest.total_files_deleted == 2
    assert manifest.mode == "permanent"
    assert not ds["dupe1"].exists()
    assert not ds["dupe2"].exists()
    assert ds["keeper"].exists()

    # Audit file must exist and contain entries
    audit_file = Path(manifest.audit_file)
    assert audit_file.exists()
    with open(audit_file, encoding="utf-8") as f:
        data = json.load(f)
    assert data["total_files_deleted"] == 2
    assert data["mode"] == "permanent"


def test_keeper_file_is_strictly_protected_against_deletion(delete_test_dataset):
    ds = delete_test_dataset
    # Force attempt to delete keeper by explicitly selecting it
    manifest = DeleteEngine.execute(
        summary_or_records=ds["summary"],
        selected_paths=[str(ds["keeper"]), str(ds["dupe1"])],
        base_dir=ds["root"],
        mode="trash",
    )

    # Keeper must NOT be deleted
    assert ds["keeper"].exists()
    assert not ds["dupe1"].exists()
    assert manifest.total_files_deleted == 1
    assert all(item.original_path != str(ds["keeper"]) for item in manifest.items)


def test_path_traversal_or_unauthorized_path_rejected(delete_test_dataset, tmp_path):
    ds = delete_test_dataset
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("critical outside file")

    with pytest.raises(SecurityError):
        DeleteEngine.execute(
            summary_or_records=ds["summary"],
            selected_paths=[str(outside_file)],
            base_dir=ds["root"],
            mode="permanent",
        )

    assert outside_file.exists()
