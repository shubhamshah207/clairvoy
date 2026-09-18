"""
Clairvoy Persistent Run Manager
Tracks, lists, auto-discovers, and loads scan run summaries for both CLI and Web UI.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RunRecord(BaseModel):
    """Metadata summary of an executed deduplication scan run."""
    run_id: str
    timestamp: str
    scanned_paths: list[str]
    total_files_scanned: int
    exact_duplicate_groups: int = 0
    visual_ai_groups: int = 0
    content_duplicate_groups: int = 0
    total_duplicate_groups: int = 0
    wasted_bytes: int = 0
    wasted_mb: float = 0.0
    wasted_gb: float = 0.0
    duration_seconds: float = 0.0
    summary_json: str
    csv_report: str | None = None
    quarantine_script: str | None = None
    category_breakdown: dict[str, int] = Field(default_factory=dict)


class RunManager:
    """Manages persistent history, listing, and loading of Clairvoy scan runs."""

    def __init__(self, history_file: Path | None = None):
        if history_file is None:
            config_dir = Path.home() / ".clairvoy"
            config_dir.mkdir(parents=True, exist_ok=True)
            self.history_file = config_dir / "runs.json"
        else:
            self.history_file = Path(history_file)
            self.history_file.parent.mkdir(parents=True, exist_ok=True)

    def _read_history(self) -> list[dict[str, Any]]:
        if not self.history_file.exists():
            return []
        try:
            with open(self.history_file, encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning("Failed to read runs history: %s", e)
            return []

    def _write_history(self, runs: list[dict[str, Any]]) -> None:
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(runs, f, indent=2)
        except Exception as e:
            logger.warning("Failed to write runs history: %s", e)

    def register_run(self, summary: Any) -> RunRecord:
        """
        Registers a ScanSummary instance or summary dict into persistent run history.
        """
        if hasattr(summary, "model_dump"):
            data = summary.model_dump()
        elif isinstance(summary, dict):
            data = summary
        else:
            raise TypeError("Expected ScanSummary or dict")

        ts_now = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_id = f"run_{ts_now}"

        # Resolve paths
        scanned = data.get("scanned_paths")
        if not scanned:
            scanned_dir = data.get("scanned_dir")
            scanned = [scanned_dir] if scanned_dir else []

        record = RunRecord(
            run_id=run_id,
            timestamp=datetime.now().isoformat(),
            scanned_paths=scanned,
            total_files_scanned=data.get("total_files_scanned", 0),
            exact_duplicate_groups=data.get("exact_duplicate_groups", 0),
            visual_ai_groups=data.get("visual_ai_groups", 0),
            content_duplicate_groups=data.get("content_duplicate_groups", 0),
            total_duplicate_groups=data.get("total_duplicate_groups", 0),
            wasted_bytes=data.get("wasted_bytes", 0),
            wasted_mb=data.get("wasted_mb", 0.0),
            wasted_gb=data.get("wasted_gb", 0.0),
            duration_seconds=data.get("duration_seconds", 0.0),
            summary_json=str(Path(data["summary_json"]).resolve()) if "summary_json" in data else "",
            csv_report=str(Path(data["csv_report"]).resolve()) if "csv_report" in data else None,
            quarantine_script=str(Path(data["quarantine_script"]).resolve()) if "quarantine_script" in data else None,
            category_breakdown=data.get("category_breakdown", {}),
        )

        runs = self._read_history()
        # Avoid duplicate summary_json entries; update if existing
        runs = [r for r in runs if r.get("summary_json") != record.summary_json]
        runs.insert(0, record.model_dump())
        # Keep top 50 runs
        self._write_history(runs[:50])
        return record

    def list_runs(
        self, limit: int = 20, auto_discover: bool = True, auto_discover_dirs: list[Path] | None = None
    ) -> list[RunRecord]:
        """Returns registered runs, newest first, optionally auto-discovering unindexed reports."""
        if auto_discover:
            self.auto_discover_reports(search_dirs=auto_discover_dirs)
        raw_runs = self._read_history()
        records: list[RunRecord] = []
        for r in raw_runs:
            try:
                records.append(RunRecord(**r))
            except Exception:
                continue
        return records[:limit]

    def get_run(self, run_id: str, auto_discover: bool = False) -> RunRecord | None:
        """Retrieves a single RunRecord by run_id."""
        for record in self.list_runs(limit=100, auto_discover=auto_discover):
            if record.run_id == run_id:
                return record
        return None

    def load_run_summary(self, run_identifier: str) -> dict[str, Any]:
        """
        Loads the complete summary JSON dict from a run_id or a direct file path.
        """
        target_path: Path | None = None
        # Check if identifier is a direct existing file
        candidate_file = Path(run_identifier).expanduser()
        if candidate_file.is_file():
            target_path = candidate_file
        else:
            # Look up run by ID
            record = self.get_run(run_identifier)
            if record and record.summary_json:
                p = Path(record.summary_json)
                if p.is_file():
                    target_path = p

        if not target_path or not target_path.is_file():
            raise FileNotFoundError(f"Scan summary report not found for '{run_identifier}'")

        with open(target_path, encoding="utf-8") as f:
            return json.load(f)

    def auto_discover_reports(self, search_dirs: list[Path] | None = None) -> list[RunRecord]:
        """
        Auto-discovers unregistered 'clairvoy_summary.json' reports from well-known directories.
        """
        if search_dirs is None:
            search_dirs = [
                Path.home() / "clairvoy_drive_e_reports",
                Path.cwd() / "_dedupe_reports",
                Path.cwd(),
                Path.home() / ".clairvoy" / "reports",
                Path("/mnt/e/_dedupe_reports"),
            ]

        registered = {r.get("summary_json") for r in self._read_history()}
        new_records: list[RunRecord] = []

        for base_dir in search_dirs:
            if not base_dir.exists() or not base_dir.is_dir():
                continue

            candidate_paths = [
                base_dir / "clairvoy_summary.json",
                base_dir / "duplicates_summary.json",
            ]
            for cp in candidate_paths:
                resolved_str = str(cp.resolve())
                if cp.is_file() and resolved_str not in registered:
                    try:
                        with open(cp, encoding="utf-8") as f:
                            data = json.load(f)
                        if "total_files_scanned" in data:
                            data["summary_json"] = resolved_str
                            rec = self.register_run(data)
                            registered.add(resolved_str)
                            new_records.append(rec)
                    except Exception as e:
                        logger.debug("Could not auto-index %s: %s", cp, e)

        return new_records
