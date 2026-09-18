"""
CLI integration tests for 'clairvoy runs' and 'clairvoy ui' report loading.
"""

import json
from pathlib import Path

import pytest

from clairvoy.cli import main
from clairvoy.core.run_manager import RunManager


@pytest.fixture
def sample_run_report(tmp_path: Path):
    summary_file = tmp_path / "clairvoy_summary.json"
    data = {
        "scanned_paths": ["/test/storage"],
        "scanned_dir": "/test/storage",
        "total_files_scanned": 120,
        "media_files_scanned": 80,
        "exact_duplicate_groups": 12,
        "visual_ai_groups": 3,
        "content_duplicate_groups": 1,
        "total_duplicate_groups": 16,
        "wasted_bytes": 52428800,
        "wasted_mb": 50.0,
        "wasted_gb": 0.049,
        "duration_seconds": 5.4,
        "csv_report": str(tmp_path / "clairvoy_duplicates.csv"),
        "summary_json": str(summary_file),
        "quarantine_script": str(tmp_path / "clairvoy_quarantine.sh"),
        "groups": [],
        "category_breakdown": {"PHOTO": 3, "FILE": 12},
    }
    summary_file.write_text(json.dumps(data), encoding="utf-8")
    return summary_file, data


def test_cli_runs_list(sample_run_report, monkeypatch, capsys, tmp_path):
    summary_file, data = sample_run_report
    history_file = tmp_path / "runs.json"
    manager = RunManager(history_file=history_file)
    rec = manager.register_run(data)

    monkeypatch.setattr("clairvoy.core.run_manager.RunManager", lambda *args, **kwargs: manager)
    monkeypatch.setattr("sys.argv", ["clairvoy", "runs", "list"])

    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0

    captured = capsys.readouterr().out
    assert rec.run_id in captured
    assert "50.0 MB" in captured or "0.05 GB" in captured or "0.049 GB" in captured


def test_cli_runs_show(sample_run_report, monkeypatch, capsys, tmp_path):
    summary_file, data = sample_run_report
    history_file = tmp_path / "runs.json"
    manager = RunManager(history_file=history_file)
    rec = manager.register_run(data)

    monkeypatch.setattr("clairvoy.core.run_manager.RunManager", lambda *args, **kwargs: manager)
    monkeypatch.setattr("sys.argv", ["clairvoy", "runs", "show", rec.run_id])

    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0

    captured = capsys.readouterr().out
    assert rec.run_id in captured
    assert "/test/storage" in captured
    assert "total_duplicate_groups: 16" in captured.lower() or "16" in captured
