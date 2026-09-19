"""
Clairvoy Web Application Server
Production-grade FastAPI server with multi-path concurrent scanning,
hardened thumbnail streaming, in-memory caching, and 1-click safe quarantine/restore.
"""

import asyncio
import csv
import io
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, Response
from PIL import Image, ImageOps
from pydantic import BaseModel, Field

from clairvoy.core.config import (
    DEFAULT_SIMILARITY_THRESHOLD,
    SUPPORTED_MEDIA_EXTENSIONS,
    SUPPORTED_VIDEO_EXTENSIONS,
    VERSION,
)
from clairvoy.core.models import ActionType
from clairvoy.core.security import SecurityError, resolve_safe_path, resolve_safe_paths
from clairvoy.engines.delete_engine import DeleteEngine
from clairvoy.engines.quarantine import QuarantineEngine
from clairvoy.engines.vision_engine import VisionEngine

logger = logging.getLogger("clairvoy.web")

app = FastAPI(
    title="Clairvoy Web",
    description="Local-First AI Storage Deduplication Engine",
    version=VERSION,
)

# Active scan state
SCAN_STATE: dict[str, Any] = {
    "status": "idle",  # "idle" | "running" | "completed" | "failed"
    "stage": "",
    "progress_pct": 0,
    "current_step": 0,
    "total_steps": 0,
    "files_indexed": 0,
    "start_time": None,
    "elapsed_seconds": 0.0,
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
            SCAN_STATE["stage"] = "Scan summary loaded"
            SCAN_STATE["progress_pct"] = 100
            scanned = summary_data.get("scanned_paths") or [summary_data.get("scanned_dir", "")]
            SCAN_STATE["target_paths"] = scanned
            SCAN_STATE["target_dir"] = scanned[0] if scanned else ""
            groups_count = summary_data.get("total_duplicate_groups", 0)
            wasted_gb = summary_data.get("wasted_gb", 0.0)
            SCAN_STATE["files_indexed"] = summary_data.get("total_files_scanned", 0)
            SCAN_STATE["elapsed_seconds"] = summary_data.get("duration_seconds", 0.0)
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


class DeleteActionRequest(BaseModel):
    paths: list[str] | None = None
    mode: str = Field(default="trash", description="'trash' or 'permanent'")
    base_dir: str | list[str] | None = None


class RestoreTrashRequest(BaseModel):
    manifest_file: str



# In-memory thumbnail cache (max 2048 entries)
@lru_cache(maxsize=2048)
def _generate_thumbnail_bytes(resolved_path_str: str) -> bytes:
    ext = Path(resolved_path_str).suffix.lower()
    img: Image.Image | None = None

    # 1. Video files: extract keyframe using ffmpeg
    if ext in SUPPORTED_VIDEO_EXTENSIONS:
        ffmpeg_bin = shutil.which("ffmpeg") or "/home/shubhamshah207/.local/bin/ffmpeg"
        if ffmpeg_bin:
            try:
                cmd = [
                    ffmpeg_bin,
                    "-ss",
                    "0.5",
                    "-i",
                    resolved_path_str,
                    "-vframes",
                    "1",
                    "-f",
                    "image2pipe",
                    "-vcodec",
                    "mjpeg",
                    "pipe:1",
                ]
                res = subprocess.run(cmd, capture_output=True, timeout=8)
                if res.returncode == 0 and res.stdout:
                    img = Image.open(io.BytesIO(res.stdout))
            except Exception as exc:
                print(f"[!] ffmpeg video thumbnail extraction error for {resolved_path_str}: {exc}")

    # 2. Image files
    if img is None:
        try:
            img = Image.open(resolved_path_str)
            img.load()
        except Exception:
            if ext in {".heic", ".heif"}:
                img = VisionEngine._extract_frame_via_ffmpeg(resolved_path_str)

    if img is None:
        raise ValueError(f"Unable to decode media for thumbnail: {resolved_path_str}")

    img = ImageOps.exif_transpose(img)
    img.thumbnail((320, 320), Image.Resampling.BILINEAR)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=82, optimize=True)
    return buf.getvalue()


def _run_scan_worker(directories: list[str], enable_ml: bool, threshold: float):
    start_time = time.time()
    with SCAN_LOCK:
        SCAN_STATE["status"] = "running"
        SCAN_STATE["stage"] = "Initializing deduplication engine"
        SCAN_STATE["progress_pct"] = 4
        SCAN_STATE["current_step"] = 0
        SCAN_STATE["total_steps"] = 0
        SCAN_STATE["files_indexed"] = 0
        SCAN_STATE["start_time"] = start_time
        SCAN_STATE["elapsed_seconds"] = 0.0
        SCAN_STATE["message"] = f"Initializing scan across {len(directories)} directory path(s)..."
        SCAN_STATE["summary"] = None
        SCAN_STATE["error"] = None

    def _pipeline_progress(msg: str, step: int, total: int):
        with SCAN_LOCK:
            elapsed = round(time.time() - start_time, 1)
            SCAN_STATE["elapsed_seconds"] = elapsed
            if msg == "Scanning filesystem":
                SCAN_STATE["stage"] = "Stage 1/3: Traversing & indexing directory tree"
                SCAN_STATE["progress_pct"] = 8
                SCAN_STATE["message"] = f"Traversing filesystem across {len(directories)} root path(s)..."
            elif msg == "Filesystem indexed":
                SCAN_STATE["stage"] = "Stage 1/3: Filesystem indexing complete"
                SCAN_STATE["files_indexed"] = step
                SCAN_STATE["progress_pct"] = 20
                SCAN_STATE["message"] = f"Indexed {step:,} total files. Preparing classification & matchers..."
            elif msg.startswith("Classifying"):
                SCAN_STATE["stage"] = "Stage 1/3: Classifying media (EXIF & Content)"
                pct = 20 + int((step / max(1, total)) * 10)
                SCAN_STATE["progress_pct"] = min(30, max(20, pct))
                SCAN_STATE["message"] = msg
            elif msg.startswith("Running matcher:"):
                matcher_name = msg.replace("Running matcher:", "").strip()
                current_idx = step + 1
                total_matchers = max(1, total)
                SCAN_STATE["current_step"] = current_idx
                SCAN_STATE["total_steps"] = total_matchers
                pct = 30 + int((step / total_matchers) * 55)
                SCAN_STATE["progress_pct"] = min(85, max(30, pct))
                SCAN_STATE["stage"] = f"Stage 2/3: Matcher Tier {current_idx}/{total_matchers} ({matcher_name})"
                SCAN_STATE["message"] = f"Evaluating candidates against {matcher_name}..."
            elif msg == "Processing duplicate clusters":
                SCAN_STATE["stage"] = "Stage 3/3: Keeper scoring & clustering"
                SCAN_STATE["progress_pct"] = 90
                SCAN_STATE["message"] = "Calculating seniority scoring and designating keeper files..."
            else:
                SCAN_STATE["message"] = msg

    try:
        from clairvoy.core.plugins import PluginRegistry, discover_plugins
        from clairvoy.engines.pipeline import DeduplicationPipeline

        registry = discover_plugins(PluginRegistry.get_instance())
        if not enable_ml:
            registry.disable_plugin("photo_vision")
            registry.disable_plugin("video_matcher")

        pipeline = DeduplicationPipeline(
            paths=directories,
            registry=registry,
        )
        summary = pipeline.run_scan(progress_callback=_pipeline_progress, threshold=threshold)

        with SCAN_LOCK:
            elapsed = round(time.time() - start_time, 2)
            SCAN_STATE["status"] = "completed"
            SCAN_STATE["stage"] = "Scan completed successfully"
            SCAN_STATE["progress_pct"] = 100
            SCAN_STATE["files_indexed"] = summary.total_files_scanned
            SCAN_STATE["elapsed_seconds"] = elapsed
            SCAN_STATE["message"] = (
                f"Scan complete across {len(directories)} path(s) in {elapsed}s. Found {summary.total_duplicate_groups} duplicate groups ({summary.wasted_gb:.2f} GB recoverable)."
            )
            SCAN_STATE["summary"] = summary.model_dump()
            SCAN_STATE["error"] = None
    except Exception as e:
        logger.exception("Error during background scan: %s", e)
        with SCAN_LOCK:
            elapsed = round(time.time() - start_time, 2)
            SCAN_STATE["status"] = "failed"
            SCAN_STATE["stage"] = "Scan failed"
            SCAN_STATE["elapsed_seconds"] = elapsed
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
    Supports both images and videos.
    """
    try:
        allowed = SCAN_STATE.get("target_paths") or None
        safe_path = resolve_safe_path(
            user_path=path,
            allowed_roots=allowed,
            allowed_extensions=SUPPORTED_MEDIA_EXTENSIONS,
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


@app.get("/api/media")
async def get_raw_media(path: str = Query(..., description="Absolute path to media file")):
    """Streams the raw media file (images or video) for in-browser playback/preview."""
    try:
        allowed = SCAN_STATE.get("target_paths") or None
        safe_path = resolve_safe_path(
            user_path=path,
            allowed_roots=allowed,
            allowed_extensions=SUPPORTED_MEDIA_EXTENSIONS,
            must_exist=True,
        )
    except SecurityError as se:
        raise HTTPException(status_code=403, detail=str(se)) from se
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found") from None

    ext = safe_path.suffix.lower()
    media_type = "video/mp4" if ext == ".mp4" else ("image/jpeg" if ext in {".jpg", ".jpeg"} else None)
    return FileResponse(safe_path, media_type=media_type)


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
        now = time.time()
        SCAN_STATE["status"] = "running"
        SCAN_STATE["stage"] = "Initializing scan"
        SCAN_STATE["progress_pct"] = 3
        SCAN_STATE["current_step"] = 0
        SCAN_STATE["total_steps"] = 0
        SCAN_STATE["files_indexed"] = 0
        SCAN_STATE["start_time"] = now
        SCAN_STATE["elapsed_seconds"] = 0.0
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
        state = dict(SCAN_STATE)
        if state.get("status") == "running" and state.get("start_time"):
            state["elapsed_seconds"] = round(time.time() - state["start_time"], 1)
        return state


def _run_native_folder_picker() -> str | None:
    """Invokes the host OS native folder selection dialog if a display environment is available."""
    has_display = bool(
        os.environ.get("DISPLAY")
        or os.environ.get("WAYLAND_DISPLAY")
        or sys.platform in ("darwin", "win32")
    )
    if not has_display:
        return None

    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askdirectory(
            title="Select Folder to Scan - Clairvoy", initialdir=str(Path.home())
        )
        root.destroy()
        return selected if selected else None
    except Exception as e:
        logger.warning(f"Native folder picker invocation failed: {e}")
        return None


@app.post("/api/system/pick-folder")
async def pick_native_folder():
    """Launches the host OS native folder selection dialog in a worker thread."""
    selected = await asyncio.to_thread(_run_native_folder_picker)
    if selected:
        return {"status": "selected", "path": selected}
    return {"status": "cancelled", "path": None}


@app.get("/api/system/browse-directories")
async def browse_directories(path: str | None = None):
    """Lists local filesystem directories and system shortcuts for interactive folder selection."""
    home = Path.home()
    shortcuts = [
        {"name": "Home Directory", "path": str(home), "icon": "🏠"},
    ]
    for label, icon, sub in [
        ("Pictures", "📸", home / "Pictures"),
        ("Videos", "🎬", home / "Videos"),
        ("Downloads", "📥", home / "Downloads"),
        ("Documents", "📄", home / "Documents"),
    ]:
        if sub.exists() and sub.is_dir():
            shortcuts.append({"name": label, "path": str(sub), "icon": icon})

    shortcuts.append({"name": "Current Workspace", "path": str(Path.cwd()), "icon": "💻"})

    for mount_root in ["/mnt", "/media", "/Volumes"]:
        mp = Path(mount_root)
        if mp.exists() and mp.is_dir():
            try:
                for child in mp.iterdir():
                    if child.is_dir() and not child.name.startswith("."):
                        shortcuts.append({"name": f"Drive: {child.name}", "path": str(child), "icon": "💾"})
            except Exception:
                pass

    shortcuts.append({"name": "Filesystem Root (/)", "path": "/", "icon": "🗄️"})

    target_path = Path(path).resolve() if path else home
    if not target_path.exists() or not target_path.is_dir():
        target_path = home

    subdirs = []
    try:
        with os.scandir(target_path) as it:
            for entry in it:
                try:
                    if entry.is_dir(follow_symlinks=False) and not entry.name.startswith("."):
                        has_children = False
                        try:
                            with os.scandir(entry.path) as sub_it:
                                for s in sub_it:
                                    if s.is_dir(follow_symlinks=False) and not s.name.startswith("."):
                                        has_children = True
                                        break
                        except Exception:
                            pass
                        subdirs.append({
                            "name": entry.name,
                            "path": entry.path,
                            "has_children": has_children,
                        })
                except Exception:
                    continue
        subdirs.sort(key=lambda x: x["name"].lower())
        subdirs = subdirs[:300]
    except PermissionError:
        pass
    except Exception as e:
        logger.warning(f"Error scanning directory {target_path}: {e}")

    parent_path = str(target_path.parent) if target_path != target_path.parent else None

    return {
        "current_path": str(target_path),
        "parent_path": parent_path,
        "shortcuts": shortcuts,
        "directories": subdirs,
    }


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
        SCAN_STATE["stage"] = "Scan summary loaded"
        SCAN_STATE["progress_pct"] = 100
        scanned = summary_data.get("scanned_paths") or [summary_data.get("scanned_dir", "")]
        SCAN_STATE["target_paths"] = scanned
        SCAN_STATE["target_dir"] = scanned[0] if scanned else ""
        groups_count = summary_data.get("total_duplicate_groups", 0)
        wasted_gb = summary_data.get("wasted_gb", 0.0)
        SCAN_STATE["files_indexed"] = summary_data.get("total_files_scanned", 0)
        SCAN_STATE["elapsed_seconds"] = summary_data.get("duration_seconds", 0.0)
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


@app.post("/api/delete/execute")
async def execute_delete(req: DeleteActionRequest):
    """Safely executes soft trash or permanent deletion across duplicate files."""
    with SCAN_LOCK:
        if not SCAN_STATE["summary"]:
            raise HTTPException(status_code=400, detail="No active scan summary available.")
        summary_data = SCAN_STATE["summary"]

    base_dir = req.base_dir or (
        SCAN_STATE["target_paths"][0] if SCAN_STATE["target_paths"] else SCAN_STATE["target_dir"]
    )

    try:
        manifest = DeleteEngine.execute(
            summary_or_records=summary_data,
            selected_paths=req.paths,
            base_dir=base_dir,
            mode=req.mode,
        )

        # Update in-memory SCAN_STATE summary: remove deleted paths from groups
        with SCAN_LOCK:
            if SCAN_STATE["summary"] and "groups" in SCAN_STATE["summary"]:
                deleted_paths = {it.original_path for it in manifest.items}
                new_groups = [
                    g for g in SCAN_STATE["summary"]["groups"]
                    if g.get("path") not in deleted_paths
                ]
                SCAN_STATE["summary"]["groups"] = new_groups
                freed_bytes = manifest.total_bytes_freed
                old_wasted = SCAN_STATE["summary"].get("wasted_bytes", 0)
                new_wasted = max(0, old_wasted - freed_bytes)
                SCAN_STATE["summary"]["wasted_bytes"] = new_wasted
                SCAN_STATE["summary"]["wasted_mb"] = round(new_wasted / (1024 * 1024), 2)
                SCAN_STATE["summary"]["wasted_gb"] = round(new_wasted / (1024 * 1024 * 1024), 3)

        return manifest.model_dump()
    except SecurityError as se:
        raise HTTPException(status_code=403, detail=str(se)) from se
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deletion failed: {e!s}") from e


@app.post("/api/delete/restore")
async def restore_delete(req: RestoreTrashRequest):
    """Restores soft-deleted files from a trash manifest back to original paths."""
    try:
        safe_manifest = resolve_safe_path(req.manifest_file, must_exist=True)
        count = DeleteEngine.restore(safe_manifest)
        return {"status": "restored", "restored_files_count": count}
    except SecurityError as se:
        raise HTTPException(status_code=403, detail=str(se)) from se
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Trash manifest file not found.") from None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restore failed: {e!s}") from e


@app.get("/api/reports/delete-script")
async def download_delete_script(mode: str = Query(default="trash", pattern="^(trash|permanent)$")):
    """Streams or downloads a hardened deletion shell script for the active duplicate set."""
    with SCAN_LOCK:
        summary = SCAN_STATE.get("summary")
        if not summary:
            raise HTTPException(status_code=404, detail="No active scan summary available.")

        from clairvoy.core.security import generate_hardened_deletion_script

        groups = summary.get("groups", [])
        scanned_paths = summary.get("scanned_paths") or [summary.get("scanned_dir", "")]
        base_dir = scanned_paths[0] if scanned_paths else str(Path.cwd())
        trash_dir = str(Path(base_dir) / ".clairvoy_trash")

        duplicate_paths = [
            item.get("path")
            for item in groups
            if item.get("action") == ActionType.DUPLICATE.value and item.get("path")
        ]

        script_content = generate_hardened_deletion_script(
            deletions=duplicate_paths,
            base_dir=scanned_paths,
            mode=mode,
            trash_dir=trash_dir if mode == "trash" else None,
        )
        return Response(
            content=script_content,
            media_type="application/x-sh",
            headers={"Content-Disposition": f'attachment; filename="delete_duplicates_{mode}.sh"'},
        )



