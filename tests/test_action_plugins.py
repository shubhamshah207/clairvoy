"""
Unit tests for Clairvoy Action Plugins:
- SafeQuarantineActionPlugin
- HardlinkActionPlugin
"""

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from clairvoy.core.models import (
    ActionType,
    DuplicateGroup,
    DuplicateRecord,
    ImageCategory,
    MatchType,
    ScanSummary,
)
from clairvoy.core.plugins import ActionResult, PluginRegistry
from clairvoy.plugins.hardlink_action import HardlinkActionPlugin
from clairvoy.plugins.quarantine_action import SafeQuarantineActionPlugin


def test_action_plugin_metadata():
    """Verify required metadata attributes on action plugins."""
    q = SafeQuarantineActionPlugin()
    assert q.plugin_id == "quarantine"
    assert q.action_id == "quarantine"
    assert q.display_name == "Safe Quarantine Action (Reversible Isolation)"
    assert q.version == "0.1.0"
    assert q.author == "Clairvoy Team"
    assert "quarantine directory with rollback manifest" in q.description
    avail, msg = q.is_available()
    assert avail is True
    assert msg == "Safe quarantine action is available."

    hl = HardlinkActionPlugin()
    assert hl.plugin_id == "hardlink"
    assert hl.action_id == "hardlink"
    assert hl.display_name == "Hardlink Action (NTFS & POSIX Inode Unification)"
    assert hl.version == "0.1.0"
    assert hl.author == "Clairvoy Team"
    assert "hardlinks to the keeper inode" in hl.description
    hl_avail, hl_msg = hl.is_available()
    assert hl_avail == hasattr(os, "link")
    assert "Hardlinks supported via os.link" in hl_msg


def test_quarantine_action_execute(temp_workspace: Path):
    """Moves duplicate file, leaves keeper intact, generates manifest."""
    keeper = temp_workspace / "keeper.txt"
    dupe = temp_workspace / "dupe.txt"
    keeper.write_text("identical payload")
    dupe.write_text("identical payload")

    records = [
        DuplicateRecord(
            group_id=1,
            match_type=MatchType.EXACT_HASH,
            action=ActionType.KEEP,
            similarity="100%",
            similarity_score=1.0,
            size_mb=0.001,
            path=str(keeper),
            category=ImageCategory.FILE,
        ),
        DuplicateRecord(
            group_id=1,
            match_type=MatchType.EXACT_HASH,
            action=ActionType.DUPLICATE,
            similarity="100%",
            similarity_score=1.0,
            size_mb=0.001,
            path=str(dupe),
            category=ImageCategory.FILE,
        ),
    ]

    action = SafeQuarantineActionPlugin()
    result = action.execute(records, base_dirs=[temp_workspace], dry_run=False)

    assert isinstance(result, ActionResult)
    assert result.action_id == "quarantine"
    assert result.success_count == 1
    assert result.failed_count == 0
    assert result.bytes_processed == len("identical payload")
    assert result.manifest_path is not None
    assert Path(result.manifest_path).exists()
    assert len(result.errors) == 0

    # Keeper intact, dupe moved
    assert keeper.exists()
    assert not dupe.exists()


def test_quarantine_action_dry_run(temp_workspace: Path):
    """Files remain in original location during dry run."""
    keeper = temp_workspace / "keeper.txt"
    dupe = temp_workspace / "dupe.txt"
    keeper.write_text("identical payload")
    dupe.write_text("identical payload")

    records = [
        DuplicateRecord(
            group_id=1,
            match_type=MatchType.EXACT_HASH,
            action=ActionType.KEEP,
            similarity="100%",
            similarity_score=1.0,
            size_mb=0.001,
            path=str(keeper),
            category=ImageCategory.FILE,
        ),
        DuplicateRecord(
            group_id=1,
            match_type=MatchType.EXACT_HASH,
            action=ActionType.DUPLICATE,
            similarity="100%",
            similarity_score=1.0,
            size_mb=0.001,
            path=str(dupe),
            category=ImageCategory.FILE,
        ),
    ]

    action = SafeQuarantineActionPlugin()
    result = action.execute(records, base_dirs=[temp_workspace], dry_run=True)

    assert result.action_id == "quarantine"
    assert result.success_count == 1
    assert result.failed_count == 0
    assert result.bytes_processed == len("identical payload")

    # Files must not be moved during dry run
    assert keeper.exists()
    assert dupe.exists()
    assert not (temp_workspace / "_duplicate_quarantine").exists()


def test_quarantine_action_rollback(temp_workspace: Path):
    """Quarantined files restored safely via rollback."""
    keeper = temp_workspace / "keeper.txt"
    dupe = temp_workspace / "dupe.txt"
    payload = "duplicate content to isolate and restore"
    keeper.write_text(payload)
    dupe.write_text(payload)

    records = [
        DuplicateRecord(
            group_id=1,
            match_type=MatchType.EXACT_HASH,
            action=ActionType.KEEP,
            similarity="100%",
            similarity_score=1.0,
            size_mb=0.001,
            path=str(keeper),
            category=ImageCategory.FILE,
        ),
        DuplicateRecord(
            group_id=1,
            match_type=MatchType.EXACT_HASH,
            action=ActionType.DUPLICATE,
            similarity="100%",
            similarity_score=1.0,
            size_mb=0.001,
            path=str(dupe),
            category=ImageCategory.FILE,
        ),
    ]

    action = SafeQuarantineActionPlugin()
    result = action.execute(records, base_dirs=[temp_workspace], dry_run=False)
    assert not dupe.exists()
    assert result.manifest_path is not None

    # Rollback quarantine
    success = action.rollback(result.manifest_path)
    assert success is True
    assert dupe.exists()
    assert dupe.read_text() == payload


def test_quarantine_action_with_scan_summary(temp_workspace: Path):
    """Accepts ScanSummary object as plan input."""
    keeper = temp_workspace / "orig.txt"
    dupe = temp_workspace / "copy.txt"
    keeper.write_text("scan summary payload")
    dupe.write_text("scan summary payload")

    summary = ScanSummary(
        scanned_paths=[str(temp_workspace)],
        scanned_dir=str(temp_workspace),
        total_files_scanned=2,
        media_files_scanned=0,
        exact_duplicate_groups=1,
        visual_ai_groups=0,
        total_duplicate_groups=1,
        wasted_bytes=len("scan summary payload"),
        wasted_mb=0.0001,
        wasted_gb=0.0,
        duration_seconds=0.1,
        csv_report="",
        summary_json="",
        quarantine_script="",
        groups=[
            DuplicateRecord(
                group_id=1,
                match_type=MatchType.EXACT_HASH,
                action=ActionType.KEEP,
                similarity="100%",
                similarity_score=1.0,
                size_mb=0.0001,
                path=str(keeper),
                category=ImageCategory.FILE,
            ),
            DuplicateRecord(
                group_id=1,
                match_type=MatchType.EXACT_HASH,
                action=ActionType.DUPLICATE,
                similarity="100%",
                similarity_score=1.0,
                size_mb=0.0001,
                path=str(dupe),
                category=ImageCategory.FILE,
            ),
        ],
    )

    action = SafeQuarantineActionPlugin()
    result = action.execute(summary, base_dirs=[temp_workspace], dry_run=False)
    assert result.success_count == 1
    assert not dupe.exists()
    assert keeper.exists()


def test_hardlink_action(temp_workspace: Path):
    """Duplicate replaced by hardlink, verified keeper.stat().st_ino == dupe.stat().st_ino."""
    keeper = temp_workspace / "keeper.jpg"
    dupe = temp_workspace / "dupe.jpg"
    payload = "sample media payload bytes for hardlinking"
    keeper.write_text(payload)
    dupe.write_text(payload)

    # Initial inodes must be distinct
    assert keeper.stat().st_ino != dupe.stat().st_ino

    records = [
        DuplicateRecord(
            group_id=1,
            match_type=MatchType.EXACT_HASH,
            action=ActionType.KEEP,
            similarity="100%",
            similarity_score=1.0,
            size_mb=0.001,
            path=str(keeper),
            category=ImageCategory.PHOTO,
        ),
        DuplicateRecord(
            group_id=1,
            match_type=MatchType.EXACT_HASH,
            action=ActionType.DUPLICATE,
            similarity="100%",
            similarity_score=1.0,
            size_mb=0.001,
            path=str(dupe),
            category=ImageCategory.PHOTO,
        ),
    ]

    action = HardlinkActionPlugin()
    result = action.execute(records, base_dirs=[temp_workspace], dry_run=False)

    assert isinstance(result, ActionResult)
    assert result.action_id == "hardlink"
    assert result.success_count == 1
    assert result.failed_count == 0
    assert result.bytes_processed == len(payload)
    assert result.manifest_path is not None
    assert Path(result.manifest_path).exists()
    assert len(result.errors) == 0

    # Inodes must now be identical
    assert keeper.stat().st_ino == dupe.stat().st_ino
    assert dupe.read_text() == payload


def test_hardlink_action_dry_run(temp_workspace: Path):
    """Inodes remain distinct during dry run."""
    keeper = temp_workspace / "keeper.jpg"
    dupe = temp_workspace / "dupe.jpg"
    payload = "dry run hardlink payload"
    keeper.write_text(payload)
    dupe.write_text(payload)

    initial_dupe_ino = dupe.stat().st_ino

    records = [
        DuplicateRecord(
            group_id=1,
            match_type=MatchType.EXACT_HASH,
            action=ActionType.KEEP,
            similarity="100%",
            similarity_score=1.0,
            size_mb=0.001,
            path=str(keeper),
            category=ImageCategory.PHOTO,
        ),
        DuplicateRecord(
            group_id=1,
            match_type=MatchType.EXACT_HASH,
            action=ActionType.DUPLICATE,
            similarity="100%",
            similarity_score=1.0,
            size_mb=0.001,
            path=str(dupe),
            category=ImageCategory.PHOTO,
        ),
    ]

    action = HardlinkActionPlugin()
    result = action.execute(records, base_dirs=[temp_workspace], dry_run=True)

    assert result.action_id == "hardlink"
    assert result.success_count == 1
    assert result.failed_count == 0
    assert result.bytes_processed == len(payload)

    # Inodes remain distinct and dupe file untouched
    assert keeper.stat().st_ino != dupe.stat().st_ino
    assert dupe.stat().st_ino == initial_dupe_ino


def test_hardlink_action_missing_file(temp_workspace: Path):
    """Handles missing file gracefully with error logging."""
    keeper = temp_workspace / "keeper.jpg"
    keeper.write_text("keeper exists")
    missing_dupe = temp_workspace / "non_existent_dupe.jpg"

    records = [
        DuplicateRecord(
            group_id=1,
            match_type=MatchType.EXACT_HASH,
            action=ActionType.KEEP,
            similarity="100%",
            similarity_score=1.0,
            size_mb=0.001,
            path=str(keeper),
            category=ImageCategory.PHOTO,
        ),
        DuplicateRecord(
            group_id=1,
            match_type=MatchType.EXACT_HASH,
            action=ActionType.DUPLICATE,
            similarity="100%",
            similarity_score=1.0,
            size_mb=0.001,
            path=str(missing_dupe),
            category=ImageCategory.PHOTO,
        ),
    ]

    action = HardlinkActionPlugin()
    result = action.execute(records, base_dirs=[temp_workspace], dry_run=False)

    assert result.action_id == "hardlink"
    assert result.success_count == 0
    assert result.failed_count == 1
    assert len(result.errors) == 1
    assert "does not exist" in result.errors[0].lower()


def test_hardlink_cross_device_fallback(temp_workspace: Path, monkeypatch: pytest.MonkeyPatch):
    """Simulates cross-device boundary error handling."""
    keeper = temp_workspace / "keeper.jpg"
    dupe = temp_workspace / "dupe.jpg"
    keeper.write_text("keeper payload")
    dupe.write_text("dupe payload")

    records = [
        DuplicateRecord(
            group_id=1,
            match_type=MatchType.EXACT_HASH,
            action=ActionType.KEEP,
            similarity="100%",
            similarity_score=1.0,
            size_mb=0.001,
            path=str(keeper),
            category=ImageCategory.PHOTO,
        ),
        DuplicateRecord(
            group_id=1,
            match_type=MatchType.EXACT_HASH,
            action=ActionType.DUPLICATE,
            similarity="100%",
            similarity_score=1.0,
            size_mb=0.001,
            path=str(dupe),
            category=ImageCategory.PHOTO,
        ),
    ]

    # Monkeypatch stat to return different st_dev for keeper and dupe
    real_stat = Path.stat

    def fake_stat(self: Path, *args, **kwargs):
        st = real_stat(self, *args, **kwargs)
        if self.name == "keeper.jpg":
            mock_st = MagicMock(wraps=st)
            mock_st.st_dev = 11111
            mock_st.st_ino = st.st_ino
            mock_st.st_size = st.st_size
            return mock_st
        elif self.name == "dupe.jpg":
            mock_st = MagicMock(wraps=st)
            mock_st.st_dev = 22222
            mock_st.st_ino = st.st_ino
            mock_st.st_size = st.st_size
            return mock_st
        return st

    monkeypatch.setattr(Path, "stat", fake_stat)

    action = HardlinkActionPlugin()
    result = action.execute(records, base_dirs=[temp_workspace], dry_run=False)

    assert result.action_id == "hardlink"
    assert result.success_count == 0
    assert result.failed_count == 1
    assert len(result.errors) >= 1
    assert any("Cannot hardlink across filesystem partitions" in err for err in result.errors)
    # File must not be destroyed
    assert dupe.exists()


def test_hardlink_action_with_duplicate_groups(temp_workspace: Path):
    """Executes hardlinking using DuplicateGroup objects."""
    keeper = temp_workspace / "group_keeper.txt"
    dupe1 = temp_workspace / "group_dupe1.txt"
    dupe2 = temp_workspace / "group_dupe2.txt"
    payload = "group deduplication payload"
    keeper.write_text(payload)
    dupe1.write_text(payload)
    dupe2.write_text(payload)

    group = DuplicateGroup(
        group_id=42,
        match_type=MatchType.EXACT_HASH,
        keeper=DuplicateRecord(
            group_id=42,
            match_type=MatchType.EXACT_HASH,
            action=ActionType.KEEP,
            similarity="100%",
            similarity_score=1.0,
            size_mb=0.001,
            path=str(keeper),
            category=ImageCategory.FILE,
        ),
        duplicates=[
            DuplicateRecord(
                group_id=42,
                match_type=MatchType.EXACT_HASH,
                action=ActionType.DUPLICATE,
                similarity="100%",
                similarity_score=1.0,
                size_mb=0.001,
                path=str(dupe1),
                category=ImageCategory.FILE,
            ),
            DuplicateRecord(
                group_id=42,
                match_type=MatchType.EXACT_HASH,
                action=ActionType.DUPLICATE,
                similarity="100%",
                similarity_score=1.0,
                size_mb=0.001,
                path=str(dupe2),
                category=ImageCategory.FILE,
            ),
        ],
    )

    action = HardlinkActionPlugin()
    result = action.execute([group], base_dirs=[temp_workspace], dry_run=False)

    assert result.success_count == 2
    assert result.failed_count == 0
    assert keeper.stat().st_ino == dupe1.stat().st_ino
    assert keeper.stat().st_ino == dupe2.stat().st_ino

    # Test hardlink rollback breaking the links
    rollback_ok = action.rollback(result.manifest_path)
    assert rollback_ok is True
    # Now they should have distinct inodes after rollback
    assert keeper.stat().st_ino != dupe1.stat().st_ino
    assert keeper.stat().st_ino != dupe2.stat().st_ino
    assert dupe1.read_text() == payload
    assert dupe2.read_text() == payload


def test_action_registry_integration():
    """Validates registration and retrieval via registry.get_action."""
    registry = PluginRegistry()
    q = SafeQuarantineActionPlugin()
    hl = HardlinkActionPlugin()

    registry.register(q)
    registry.register(hl)

    assert registry.get_action("quarantine") is q
    assert registry.get_action("hardlink") is hl
    assert registry.get_plugin("quarantine") is q
    assert registry.get_plugin("hardlink") is hl

    actions = registry.get_actions(enabled_only=True, available_only=True)
    assert len(actions) == 2
    action_ids = {a.action_id for a in actions}
    assert "quarantine" in action_ids
    assert "hardlink" in action_ids


def test_action_plugins_directory_discovery():
    """Validates dynamic discovery of action plugins from clairvoy/plugins directory."""
    registry = PluginRegistry()
    plugins_dir = Path(__file__).parent.parent / "clairvoy" / "plugins"
    loaded = registry.load_plugins_from_directory(plugins_dir)
    loaded_ids = {p.plugin_id for p in loaded}

    assert "quarantine" in loaded_ids
    assert "hardlink" in loaded_ids

    assert registry.get_action("quarantine") is not None
    assert registry.get_action("hardlink") is not None

