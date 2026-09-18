"""
Clairvoy Web Application Server
Production-grade FastAPI server with multi-path concurrent scanning,
hardened thumbnail streaming, in-memory caching, and 1-click safe quarantine/restore.
"""

import csv
import io
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, Response
from PIL import Image, ImageOps
from pydantic import BaseModel, Field

from clairvoy.core.config import (
    DEFAULT_SIMILARITY_THRESHOLD,
    SUPPORTED_IMAGE_EXTENSIONS,
    VERSION,
)
from clairvoy.core.models import ActionType
from clairvoy.core.security import SecurityError, resolve_safe_path, resolve_safe_paths
from clairvoy.engines.quarantine import QuarantineEngine
from clairvoy.engines.storage_engine import StorageEngine
from clairvoy.engines.vision_engine import VisionEngine

app = FastAPI(
    title="Clairvoy Web",
    description="Local-First AI Storage Deduplication Engine",
    version=VERSION,
)

# Active scan state
SCAN_STATE: dict[str, Any] = {
    "status": "idle",  # "idle" | "running" | "completed" | "failed"
    "target_paths": [],
    "target_dir": "",
    "message": "Ready to scan",
    "summary": None,
    "error": None,
}
SCAN_LOCK = threading.Lock()


def load_initial_run(run_target: str | None = None) -> bool:
    """
    Pre-loads a scan summary into SCAN_STATE.
    If run_target is given (path or run_id), loads that run.
    If run_target is None, auto-discovers and loads the most recent run if available.
    """
    from clairvoy.core.run_manager import RunManager

    manager = RunManager()
    summary_data = None
    if run_target:
        try:
            summary_data = manager.load_run_summary(run_target)
        except Exception as e:
            print(f"[!] Warning: Could not load requested run '{run_target}': {e}")
            return False
    else:
        runs = manager.list_runs(limit=10, auto_discover=True)
        for r in runs:
            try:
                summary_data = manager.load_run_summary(r.run_id)
                if summary_data:
                    break
            except Exception as e:
                logger_msg = f"[!] Warning: Could not auto-load run '{r.run_id}': {e}"
                print(logger_msg)
                continue

    if summary_data:
        with SCAN_LOCK:
            SCAN_STATE["status"] = "completed"
            scanned = summary_data.get("scanned_paths") or [summary_data.get("scanned_dir", "")]
            SCAN_STATE["target_paths"] = scanned
            SCAN_STATE["target_dir"] = scanned[0] if scanned else ""
            groups_count = summary_data.get("total_duplicate_groups", 0)
            wasted_gb = summary_data.get("wasted_gb", 0.0)
            SCAN_STATE["message"] = (
                f"Loaded scan summary ({groups_count:,} duplicate groups, {wasted_gb:.2f} GB recoverable)"
            )
            SCAN_STATE["summary"] = summary_data
            SCAN_STATE["error"] = None
        return True
    return False


class ScanRequest(BaseModel):
    paths: list[str] | str | None = Field(
        default=None,
        description="One or more directory paths to scan concurrently",
    )
    directory: str | None = Field(
        default=None,
        description="Single target directory (backward compatibility)",
    )
    enable_ml: bool = Field(default=True, description="Enable local Vision AI model")
    threshold: float = Field(
        default=DEFAULT_SIMILARITY_THRESHOLD,
        ge=0.70,
        le=0.99,
        description="Visual similarity threshold (0.70 to 0.99)",
    )

    def get_path_list(self) -> list[str]:
        if self.paths:
            if isinstance(self.paths, list):
                return [p.strip() for p in self.paths if p.strip()]
            return [
                p.strip()
                for p in self.paths.replace("\r", "\n").replace(",", "\n").split("\n")
                if p.strip()
            ]
        if self.directory:
            return [
                p.strip()
                for p in self.directory.replace("\r", "\n").replace(",", "\n").split("\n")
                if p.strip()
            ]
        return []


class QuarantineActionRequest(BaseModel):
    summary_file: str | None = None
    base_dir: str | list[str] | None = None


class RestoreActionRequest(BaseModel):
    manifest_file: str


class LoadRunRequest(BaseModel):
    run_id: str | None = Field(default=None, description="Run ID to load")
    path: str | None = Field(default=None, description="Direct path to summary JSON to load")


class KeeperOverrideRequest(BaseModel):
    group_id: int
    new_keeper_path: str


# In-memory thumbnail cache (max 1024 entries)
@lru_cache(maxsize=1024)
def _generate_thumbnail_bytes(resolved_path_str: str) -> bytes:
    img: Image.Image | None = None
    try:
        img = Image.open(resolved_path_str)
        img.load()
    except Exception:
        ext = Path(resolved_path_str).suffix.lower()
        if ext in {".heic", ".heif"}:
            img = VisionEngine._extract_frame_via_ffmpeg(resolved_path_str)

    if img is None:
        raise ValueError(f"Unable to decode image for thumbnail: {resolved_path_str}")

    img = ImageOps.exif_transpose(img)
    img.thumbnail((256, 256), Image.Resampling.BILINEAR)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=82, optimize=True)
    return buf.getvalue()


def _run_scan_worker(directories: list[str], enable_ml: bool, threshold: float):
    try:
        engine = StorageEngine(
            paths=directories,
            enable_ml=enable_ml,
            ml_threshold=threshold,
        )
        summary = engine.run()
        with SCAN_LOCK:
            SCAN_STATE["status"] = "completed"
            SCAN_STATE["message"] = (
                f"Scan complete across {len(directories)} path(s). Found {summary.total_duplicate_groups} duplicate groups."
            )
            SCAN_STATE["summary"] = summary.model_dump()
            SCAN_STATE["error"] = None
    except Exception as e:
        with SCAN_LOCK:
            SCAN_STATE["status"] = "failed"
            SCAN_STATE["message"] = f"Scan failed: {e!s}"
            SCAN_STATE["error"] = str(e)


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    from clairvoy.web.ui import get_index_html

    return HTMLResponse(content=get_index_html())


@app.get("/api/thumbnail")
async def get_thumbnail(path: str = Query(..., description="Absolute path to media file")):
    """
    Serves a downscaled, securely validated thumbnail image with LRU caching.
    Guarantees strict directory traversal and extension bounds checking across all scanned roots.
    """
    try:
        allowed = SCAN_STATE.get("target_paths") or None
        safe_path = resolve_safe_path(
            user_path=path,
            allowed_roots=allowed,
            allowed_extensions=SUPPORTED_IMAGE_EXTENSIONS,
            must_exist=True,
        )
    except SecurityError as se:
        raise HTTPException(status_code=403, detail=str(se)) from se
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found") from None

    try:
        thumb_bytes = _generate_thumbnail_bytes(str(safe_path))
        return Response(
            content=thumb_bytes,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=86400"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image decode error: {e!s}") from e


@app.post("/api/scan")
async def start_scan(req: ScanRequest, background_tasks: BackgroundTasks):
    """Triggers an asynchronous scan job across single or multiple directories in parallel."""
    target_paths = req.get_path_list()
    if not target_paths:
        raise HTTPException(status_code=400, detail="No directories provided for scan.")

    try:
        resolved_dirs = resolve_safe_paths(target_paths, must_exist=True)
        for rd in resolved_dirs:
            if not rd.is_dir():
                raise HTTPException(status_code=400, detail=f"Specified path '{rd}' is not a directory.")
    except (SecurityError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    with SCAN_LOCK:
        if SCAN_STATE["status"] == "running":
            raise HTTPException(status_code=409, detail="A scan is already actively running.")
        SCAN_STATE["status"] = "running"
        SCAN_STATE["target_paths"] = [str(d) for d in resolved_dirs]
        SCAN_STATE["target_dir"] = str(resolved_dirs[0])
        SCAN_STATE["message"] = f"Initializing parallel scan across {len(resolved_dirs)} directory tree(s)..."
        SCAN_STATE["summary"] = None
        SCAN_STATE["error"] = None

    background_tasks.add_task(
        _run_scan_worker,
        directories=[str(d) for d in resolved_dirs],
        enable_ml=req.enable_ml,
        threshold=req.threshold,
    )
    return {
        "status": "started",
        "target_paths": [str(d) for d in resolved_dirs],
        "count": len(resolved_dirs),
    }


@app.get("/api/status")
async def get_scan_status():
    """Returns the live state and summary of the background scan."""
    with SCAN_LOCK:
        return SCAN_STATE


@app.post("/api/quarantine/execute")
async def execute_quarantine(req: QuarantineActionRequest):
    """Safely isolates duplicate files into quarantine directories in parallel."""
    if not req.summary_file and not req.base_dir:
        with SCAN_LOCK:
            if not SCAN_STATE["summary"]:
                raise HTTPException(status_code=400, detail="No active scan summary available.")
            summary_data = SCAN_STATE["summary"]
    else:
        if req.summary_file:
            try:
                safe_summary = resolve_safe_path(req.summary_file, must_exist=True)
                summary_data = str(safe_summary)
            except SecurityError as se:
                raise HTTPException(status_code=403, detail=str(se)) from se
            except FileNotFoundError:
                raise HTTPException(status_code=404, detail="Summary file not found.") from None
        else:
            summary_data = req.base_dir

    try:
        manifest = QuarantineEngine.execute(
            summary_or_records=summary_data,
            base_dir=req.base_dir,
        )
        return manifest.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quarantine failed: {e!s}") from e


@app.post("/api/quarantine/restore")
async def restore_quarantine(req: RestoreActionRequest):
    """Restores quarantined files from a manifest back to original paths in parallel."""
    try:
        safe_manifest = resolve_safe_path(req.manifest_file, must_exist=True)
        count = QuarantineEngine.restore(safe_manifest)
        return {"status": "restored", "restored_files_count": count}
    except SecurityError as se:
        raise HTTPException(status_code=403, detail=str(se)) from se
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Manifest file not found.") from None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restore failed: {e!s}") from e


@app.get("/api/runs")
async def list_runs(limit: int = Query(default=20, ge=1, le=100)):
    """Returns list of past scan runs ordered by newest first."""
    from clairvoy.core.run_manager import RunManager

    manager = RunManager()
    runs = manager.list_runs(limit=limit, auto_discover=True)
    return [r.model_dump() for r in runs]


@app.post("/api/runs/load")
async def load_run(req: LoadRunRequest):
    """Loads a specific run into SCAN_STATE by run_id or direct JSON path."""
    target = req.run_id or req.path
    if not target:
        raise HTTPException(status_code=400, detail="Must provide either run_id or path.")

    from clairvoy.core.run_manager import RunManager

    manager = RunManager()
    try:
        summary_data = manager.load_run_summary(target)
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=404, detail=str(fnf)) from fnf
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load run: {e!s}") from e

    with SCAN_LOCK:
        SCAN_STATE["status"] = "completed"
        scanned = summary_data.get("scanned_paths") or [summary_data.get("scanned_dir", "")]
        SCAN_STATE["target_paths"] = scanned
        SCAN_STATE["target_dir"] = scanned[0] if scanned else ""
        groups_count = summary_data.get("total_duplicate_groups", 0)
        wasted_gb = summary_data.get("wasted_gb", 0.0)
        SCAN_STATE["message"] = (
            f"Loaded scan summary ({groups_count:,} duplicate groups, {wasted_gb:.2f} GB recoverable)"
        )
        SCAN_STATE["summary"] = summary_data
        SCAN_STATE["error"] = None

    return {"status": "loaded", "summary": summary_data}


@app.post("/api/clusters/override-keeper")
async def override_cluster_keeper(req: KeeperOverrideRequest):
    """
    Overrides the designated KEEP file within a specific duplicate cluster.
    Updates the active in-memory summary so that the target file is marked KEEP
    and all other members of the cluster are marked DUPLICATE.
    """
    with SCAN_LOCK:
        summary = SCAN_STATE.get("summary")
        if not summary or "groups" not in summary:
            raise HTTPException(status_code=400, detail="No active scan summary available.")

        groups = summary["groups"]
        cluster_found = False
        target_found = False

        for item in groups:
            if item.get("group_id") == req.group_id:
                cluster_found = True
                if item.get("path") == req.new_keeper_path:
                    item["action"] = ActionType.KEEP.value
                    target_found = True
                else:
                    item["action"] = ActionType.DUPLICATE.value

        if not cluster_found:
            raise HTTPException(status_code=404, detail=f"Cluster #{req.group_id} not found.")
        if not target_found:
            raise HTTPException(
                status_code=404, detail=f"Path '{req.new_keeper_path}' not found in cluster #{req.group_id}."
            )

        return {"status": "updated", "group_id": req.group_id, "new_keeper": req.new_keeper_path}


@app.get("/api/reports/csv")
async def download_csv_report():
    """Streams or downloads the CSV duplicate report for the active scan summary."""
    with SCAN_LOCK:
        summary = SCAN_STATE.get("summary")
        if not summary:
            raise HTTPException(status_code=404, detail="No active scan summary available.")

        csv_path_str = summary.get("csv_report")
        if csv_path_str and Path(csv_path_str).is_file():
            return FileResponse(
                path=csv_path_str,
                filename="clairvoy_duplicates.csv",
                media_type="text/csv",
            )

        groups = summary.get("groups", [])
        output = io.StringIO()
        fieldnames = [
            "group_id",
            "match_type",
            "action",
            "category",
            "similarity",
            "size_mb",
            "path",
            "dimensions",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for item in groups:
            writer.writerow(item)

        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="clairvoy_duplicates.csv"'},
        )


@app.get("/api/reports/script")
async def download_quarantine_script():
    """Streams or downloads the hardened quarantine shell script for the active scan summary."""
    with SCAN_LOCK:
        summary = SCAN_STATE.get("summary")
        if not summary:
            raise HTTPException(status_code=404, detail="No active scan summary available.")

        script_path_str = summary.get("quarantine_script")
        if script_path_str and Path(script_path_str).is_file():
            return FileResponse(
                path=script_path_str,
                filename="quarantine_duplicates.sh",
                media_type="application/x-sh",
            )

        from clairvoy.core.security import generate_hardened_quarantine_script

        groups = summary.get("groups", [])
        scanned_paths = summary.get("scanned_paths") or [summary.get("scanned_dir", "")]
        base_dir = scanned_paths[0] if scanned_paths else str(Path.cwd())
        quarantine_dir = str(Path(base_dir) / "_duplicate_quarantine")

        quarantine_moves = []
        for item in groups:
            if item.get("action") == ActionType.DUPLICATE.value:
                src_path = item.get("path")
                if src_path:
                    src_p = Path(src_path)
                    dst = str(Path(quarantine_dir) / src_p.name)
                    quarantine_moves.append((src_path, dst))

        script_content = generate_hardened_quarantine_script(
            moves=quarantine_moves,
            base_dir=scanned_paths,
            quarantine_dir=quarantine_dir,
        )
        return Response(
            content=script_content,
            media_type="application/x-sh",
            headers={"Content-Disposition": 'attachment; filename="quarantine_duplicates.sh"'},
        )


