"""
Unit and integration tests for RunManager and RunRecord.
"""

import json
from pathlib import Path

import pytest

from clairvoy.core.run_manager import RunManager, RunRecord


@pytest.fixture
def temp_history_file(tmp_path: Path) -> Path:
    return tmp_path / "test_runs.json"


@pytest.fixture
def mock_summary_data(tmp_path: Path) -> dict:
    report_file = tmp_path / "clairvoy_summary.json"
    data = {
        "scanned_paths": ["/mock/path"],
        "scanned_dir": "/mock/path",
        "total_files_scanned": 150,
        "media_files_scanned": 100,
        "exact_duplicate_groups": 10,
        "visual_ai_groups": 5,
        "content_duplicate_groups": 2,
        "total_duplicate_groups": 17,
        "wasted_bytes": 10485760,
        "wasted_mb": 10.0,
        "wasted_gb": 0.01,
        "duration_seconds": 12.34,
        "csv_report": str(tmp_path / "clairvoy_duplicates.csv"),
        "summary_json": str(report_file),
        "quarantine_script": str(tmp_path / "clairvoy_quarantine.sh"),
        "groups": [],
        "category_breakdown": {"PHOTO": 5, "FILE": 10},
    }
    report_file.write_text(json.dumps(data), encoding="utf-8")
    return data


def test_register_and_list_runs(temp_history_file: Path, mock_summary_data: dict):
    manager = RunManager(history_file=temp_history_file)
    assert manager.list_runs(auto_discover=False) == []

    record = manager.register_run(mock_summary_data)
    assert isinstance(record, RunRecord)
    assert record.total_duplicate_groups == 17
    assert record.wasted_gb == 0.01

    runs = manager.list_runs(auto_discover=False)
    assert len(runs) == 1
    assert runs[0].run_id == record.run_id


def test_get_run_and_load_summary(temp_history_file: Path, mock_summary_data: dict):
    manager = RunManager(history_file=temp_history_file)
    record = manager.register_run(mock_summary_data)

    retrieved = manager.get_run(record.run_id, auto_discover=False)
    assert retrieved is not None
    assert retrieved.run_id == record.run_id

    loaded_summary = manager.load_run_summary(record.run_id)
    assert loaded_summary["total_files_scanned"] == 150
    assert loaded_summary["total_duplicate_groups"] == 17


def test_load_summary_by_direct_path(temp_history_file: Path, mock_summary_data: dict):
    manager = RunManager(history_file=temp_history_file)
    direct_path = mock_summary_data["summary_json"]

    loaded = manager.load_run_summary(direct_path)
    assert loaded["scanned_paths"] == ["/mock/path"]


def test_auto_discover_reports(tmp_path: Path):
    history_file = tmp_path / "history.json"
    manager = RunManager(history_file=history_file)

    discovered_dir = tmp_path / "auto_discovered"
    discovered_dir.mkdir()
    summary_path = discovered_dir / "clairvoy_summary.json"
    summary_path.write_text(
        json.dumps({
            "scanned_paths": ["/discovered/folder"],
            "total_files_scanned": 50,
            "total_duplicate_groups": 3,
            "wasted_bytes": 1048576,
            "wasted_mb": 1.0,
            "wasted_gb": 0.001,
            "summary_json": str(summary_path),
        }),
        encoding="utf-8",
    )

    # Supply search dir to auto_discover
    discovered = manager.auto_discover_reports(search_dirs=[discovered_dir])
    assert len(discovered) == 1
    assert discovered[0].scanned_paths == ["/discovered/folder"]
