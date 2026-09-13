"""
Clairvoy Web Application Server
Production-grade FastAPI server with multi-path concurrent scanning,
hardened thumbnail streaming, in-memory caching, and 1-click safe quarantine/restore.
"""

import io
import threading
from functools import lru_cache
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from PIL import Image, ImageOps
from pydantic import BaseModel, Field

from clairvoy.core.config import (
    DEFAULT_SIMILARITY_THRESHOLD,
    SUPPORTED_IMAGE_EXTENSIONS,
    VERSION,
)
from clairvoy.core.security import SecurityError, resolve_safe_path, resolve_safe_paths
from clairvoy.engines.quarantine import QuarantineEngine
from clairvoy.engines.storage_engine import StorageEngine

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


# In-memory thumbnail cache (max 1024 entries)
@lru_cache(maxsize=1024)
def _generate_thumbnail_bytes(resolved_path_str: str) -> bytes:
    with Image.open(resolved_path_str) as img:
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
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Clairvoy | Multi-Storage & Vision AI Deduplicator</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body {{ background-color: #0b0f19; color: #f8fafc; font-family: ui-sans-serif, system-ui, -apple-system; }}
            .custom-scrollbar::-webkit-scrollbar {{ width: 6px; }}
            .custom-scrollbar::-webkit-scrollbar-thumb {{ background: #334155; border-radius: 4px; }}
        </style>
    </head>
    <body class="p-4 md:p-8 min-h-screen">
        <div class="max-w-7xl mx-auto">
            <!-- Header -->
            <header class="flex flex-col sm:flex-row justify-between items-start sm:items-center pb-6 border-b border-slate-800 mb-8 gap-4">
                <div>
                    <h1 class="text-3xl font-extrabold tracking-tight text-white flex items-center gap-3">
                        <span class="text-indigo-400">👁️</span> Clairvoy
                        <span class="text-xs font-mono font-normal text-indigo-400 bg-indigo-500/10 border border-indigo-500/30 px-2.5 py-0.5 rounded-full">v{VERSION}</span>
                    </h1>
                    <p class="text-xs text-slate-400 mt-1">Multi-Path Storage Deduplication & Cross-Folder Vision AI (Meta DINOv2)</p>
                </div>
                <div class="flex items-center gap-3">
                    <span class="text-xs bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 px-3 py-1.5 rounded-full font-mono flex items-center gap-1.5">
                        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span> Multi-Tree Parallel Active
                    </span>
                    <a href="https://github.com/shubhamshah207/clairvoy" target="_blank" class="text-xs bg-slate-800 hover:bg-slate-700 border border-slate-700 px-3.5 py-1.5 rounded-full text-slate-300 transition">
                        GitHub ↗
                    </a>
                </div>
            </header>

            <!-- Scan Configuration Dashboard -->
            <div class="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 md:p-8 mb-8 shadow-2xl backdrop-blur">
                <div class="grid grid-cols-1 lg:grid-cols-12 gap-5 items-end">
                    <div class="lg:col-span-7">
                        <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                            Target Storage Directories <span class="text-slate-500 font-normal lowercase">(separate multiple folders with commas or newlines)</span>
                        </label>
                        <textarea id="dirInput" rows="2" placeholder="/mnt/e/Remotes/gdrive-srshah207&#10;/mnt/e/Remotes/gphotos-shubhamshah207"
                               class="w-full bg-slate-950 border border-slate-800 rounded-2xl px-4 py-2.5 text-sm focus:outline-none focus:border-indigo-500 text-slate-100 font-mono transition custom-scrollbar resize-y">/mnt/e/Remotes</textarea>
                    </div>
                    <div class="lg:col-span-3">
                        <div class="flex justify-between items-center mb-2">
                            <label class="text-xs font-semibold uppercase tracking-wider text-slate-400">AI Sensitivity</label>
                            <span id="thresholdDisplay" class="text-xs font-mono font-bold text-indigo-400">95%</span>
                        </div>
                        <input id="thresholdInput" type="range" min="80" max="99" value="95" oninput="document.getElementById('thresholdDisplay').innerText = this.value + '%'"
                               class="w-full accent-indigo-500 cursor-pointer">
                    </div>
                    <div class="lg:col-span-2 flex gap-3">
                        <button onclick="triggerScan()" id="scanBtn" class="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-3 px-6 rounded-2xl transition shadow-lg shadow-indigo-600/30 flex items-center justify-center gap-2">
                            <span>Start Scan</span>
                        </button>
                    </div>
                </div>

                <!-- Progress / Status Ticker -->
                <div id="statusContainer" class="mt-4 pt-4 border-t border-slate-800/80 flex items-center gap-3">
                    <div id="statusDot" class="w-2.5 h-2.5 rounded-full bg-slate-500"></div>
                    <div id="statusMessage" class="text-xs text-slate-400 font-mono">Ready to scan storage paths.</div>
                </div>
            </div>

            <!-- Metrics Overview -->
            <div id="metricsRow" class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8 hidden">
                <div class="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl">
                    <div class="text-xs uppercase tracking-wider text-slate-400 font-medium">Scanned Files</div>
                    <div id="metricFiles" class="text-3xl font-extrabold text-white mt-1">0</div>
                </div>
                <div class="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl">
                    <div class="text-xs uppercase tracking-wider text-slate-400 font-medium">Exact Duplicates</div>
                    <div id="metricExact" class="text-3xl font-extrabold text-amber-400 mt-1">0</div>
                </div>
                <div class="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl">
                    <div class="text-xs uppercase tracking-wider text-slate-400 font-medium">Vision AI Matches</div>
                    <div id="metricML" class="text-3xl font-extrabold text-indigo-400 mt-1">0</div>
                </div>
                <div class="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl">
                    <div class="text-xs uppercase tracking-wider text-slate-400 font-medium">Recoverable Space</div>
                    <div id="metricSpace" class="text-3xl font-extrabold text-emerald-400 mt-1">0 MB</div>
                </div>
            </div>

            <!-- Results View -->
            <div id="resultsCard" class="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 md:p-8 shadow-2xl hidden">
                <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6 pb-6 border-b border-slate-800">
                    <div>
                        <h2 class="text-xl font-bold text-white">Visual Comparison & Multi-Folder Deduplication</h2>
                        <p class="text-xs text-slate-400 mt-1">Review original files (KEEP) side-by-side with detected redundant duplicates (DUPLICATE) across all paths.</p>
                    </div>
                    <div class="flex items-center gap-3">
                        <button onclick="executeSafeQuarantine()" id="quarantineBtn" class="bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold px-5 py-2.5 rounded-xl transition shadow-lg shadow-rose-600/20">
                            Move Duplicates to Quarantine
                        </button>
                    </div>
                </div>

                <!-- Category Filter Bar -->
                <div class="flex flex-wrap gap-2 mb-6" id="categoryFilterBar">
                    <button onclick="setCategoryFilter('ALL')" id="filterBtn_ALL" class="cat-filter-btn px-3.5 py-1.5 rounded-full text-xs font-medium bg-indigo-600 text-white transition flex items-center gap-1.5">
                        <span>All Duplicates</span>
                        <span id="count_ALL" class="bg-indigo-700/60 px-1.5 py-0.2 rounded-full text-[10px] font-mono">0</span>
                    </button>
                    <button onclick="setCategoryFilter('PHOTO')" id="filterBtn_PHOTO" class="cat-filter-btn px-3.5 py-1.5 rounded-full text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 transition flex items-center gap-1.5">
                        <span>📷 Photos</span>
                        <span id="count_PHOTO" class="bg-slate-700 px-1.5 py-0.2 rounded-full text-[10px] font-mono">0</span>
                    </button>
                    <button onclick="setCategoryFilter('SCREENSHOT')" id="filterBtn_SCREENSHOT" class="cat-filter-btn px-3.5 py-1.5 rounded-full text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 transition flex items-center gap-1.5">
                        <span>📱 Screenshots</span>
                        <span id="count_SCREENSHOT" class="bg-slate-700 px-1.5 py-0.2 rounded-full text-[10px] font-mono">0</span>
                    </button>
                    <button onclick="setCategoryFilter('DOCUMENT')" id="filterBtn_DOCUMENT" class="cat-filter-btn px-3.5 py-1.5 rounded-full text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 transition flex items-center gap-1.5">
                        <span>📄 Documents & Receipts</span>
                        <span id="count_DOCUMENT" class="bg-slate-700 px-1.5 py-0.2 rounded-full text-[10px] font-mono">0</span>
                    </button>
                    <button onclick="setCategoryFilter('GRAPHIC')" id="filterBtn_GRAPHIC" class="cat-filter-btn px-3.5 py-1.5 rounded-full text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 transition flex items-center gap-1.5">
                        <span>🎨 Graphics & Memes</span>
                        <span id="count_GRAPHIC" class="bg-slate-700 px-1.5 py-0.2 rounded-full text-[10px] font-mono">0</span>
                    </button>
                </div>

                <div id="groupsContainer" class="space-y-6"></div>
            </div>
        </div>

        <script>
            let pollTimer = null;
            let currentSummary = null;
            let activeCategoryFilter = 'ALL';

            function setCategoryFilter(category) {{
                activeCategoryFilter = category;
                document.querySelectorAll('.cat-filter-btn').forEach(btn => {{
                    btn.classList.remove('bg-indigo-600', 'text-white');
                    btn.classList.add('bg-slate-800', 'text-slate-300');
                }});
                const activeBtn = document.getElementById('filterBtn_' + category);
                if (activeBtn) {{
                    activeBtn.classList.remove('bg-slate-800', 'text-slate-300');
                    activeBtn.classList.add('bg-indigo-600', 'text-white');
                }}
                if (currentSummary && currentSummary.groups) {{
                    renderDuplicateGroups(currentSummary.groups, activeCategoryFilter);
                }}
            }}

            async function triggerScan() {{
                const dirText = document.getElementById('dirInput').value.trim();
                const paths = dirText.split(/[\\n,]+/).map(s => s.trim()).filter(Boolean);
                const threshold = parseFloat(document.getElementById('thresholdInput').value) / 100.0;
                if (paths.length === 0) return;

                const btn = document.getElementById('scanBtn');
                btn.disabled = true;
                btn.classList.add('opacity-50');

                updateStatus("running", `Initiating parallel scan across ${{paths.length}} directory tree(s)...`);

                try {{
                    const res = await fetch('/api/scan', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ paths: paths, enable_ml: true, threshold: threshold }})
                    }});
                    const data = await res.json();
                    if (!res.ok) throw new Error(data.detail || "Scan request failed");

                    if (pollTimer) clearInterval(pollTimer);
                    pollTimer = setInterval(pollScanStatus, 1000);
                }} catch (e) {{
                    updateStatus("failed", "Error: " + e.message);
                    btn.disabled = false;
                    btn.classList.remove('opacity-50');
                }}
            }}

            async function pollScanStatus() {{
                try {{
                    const res = await fetch('/api/status');
                    const state = await res.json();

                    if (state.status === "running") {{
                        updateStatus("running", "Scanning files, classifying images, and computing DINOv2 embeddings...");
                    }} else if (state.status === "completed") {{
                        clearInterval(pollTimer);
                        pollTimer = null;
                        document.getElementById('scanBtn').disabled = false;
                        document.getElementById('scanBtn').classList.remove('opacity-50');
                        updateStatus("completed", state.message);
                        currentSummary = state.summary;
                        renderSummary(state.summary);
                    }} else if (state.status === "failed") {{
                        clearInterval(pollTimer);
                        pollTimer = null;
                        document.getElementById('scanBtn').disabled = false;
                        document.getElementById('scanBtn').classList.remove('opacity-50');
                        updateStatus("failed", state.message);
                    }}
                }} catch (e) {{
                    console.error("Polling error:", e);
                }}
            }}

            function updateStatus(type, msg) {{
                const dot = document.getElementById('statusDot');
                const text = document.getElementById('statusMessage');
                text.innerText = msg;

                if (type === "running") {{
                    dot.className = "w-2.5 h-2.5 rounded-full bg-indigo-500 animate-ping";
                }} else if (type === "completed") {{
                    dot.className = "w-2.5 h-2.5 rounded-full bg-emerald-400";
                }} else if (type === "failed") {{
                    dot.className = "w-2.5 h-2.5 rounded-full bg-rose-500";
                }} else {{
                    dot.className = "w-2.5 h-2.5 rounded-full bg-slate-500";
                }}
            }}

            function renderSummary(summary) {{
                if (!summary) return;
                document.getElementById('metricsRow').classList.remove('hidden');
                document.getElementById('resultsCard').classList.remove('hidden');

                document.getElementById('metricFiles').innerText = summary.total_files_scanned.toLocaleString();
                document.getElementById('metricExact').innerText = summary.exact_duplicate_groups.toLocaleString();
                document.getElementById('metricML').innerText = summary.visual_ai_groups.toLocaleString();
                document.getElementById('metricSpace').innerText = summary.wasted_mb + " MB (" + summary.wasted_gb + " GB)";

                // Update category counts
                const cb = summary.category_breakdown || {{}};
                const totalDupes = summary.groups ? summary.groups.filter(g => g.action === 'DUPLICATE').length : 0;
                document.getElementById('count_ALL').innerText = totalDupes;
                document.getElementById('count_PHOTO').innerText = cb.PHOTO || 0;
                document.getElementById('count_SCREENSHOT').innerText = cb.SCREENSHOT || 0;
                document.getElementById('count_DOCUMENT').innerText = cb.DOCUMENT || 0;
                document.getElementById('count_GRAPHIC').innerText = cb.GRAPHIC || 0;

                renderDuplicateGroups(summary.groups, activeCategoryFilter);
            }}

            function isImageFile(path) {{
                const exts = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'];
                return exts.some(e => path.toLowerCase().endsWith(e));
            }}

            function getCategoryBadge(cat) {{
                switch(cat) {{
                    case 'SCREENSHOT':
                        return '<span class="bg-purple-500/20 text-purple-300 border border-purple-500/30 text-[10px] px-2 py-0.5 rounded font-mono font-medium">📱 SCREENSHOT</span>';
                    case 'DOCUMENT':
                        return '<span class="bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[10px] px-2 py-0.5 rounded font-mono font-medium">📄 DOCUMENT</span>';
                    case 'GRAPHIC':
                        return '<span class="bg-pink-500/20 text-pink-300 border border-pink-500/30 text-[10px] px-2 py-0.5 rounded font-mono font-medium">🎨 GRAPHIC</span>';
                    case 'PHOTO':
                        return '<span class="bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 text-[10px] px-2 py-0.5 rounded font-mono font-medium">📷 PHOTO</span>';
                    default:
                        return '<span class="bg-slate-800 text-slate-400 border border-slate-700 text-[10px] px-2 py-0.5 rounded font-mono">FILE</span>';
                }}
            }}

            function renderDuplicateGroups(records, filterCategory = 'ALL') {{
                const container = document.getElementById('groupsContainer');
                container.innerHTML = '';

                const groups = {{}};
                for (const r of records) {{
                    if (!groups[r.group_id]) groups[r.group_id] = [];
                    groups[r.group_id].push(r);
                }}

                let groupIds = Object.keys(groups);

                // Apply Category Filter if not 'ALL'
                if (filterCategory !== 'ALL') {{
                    groupIds = groupIds.filter(gid => groups[gid].some(item => item.category === filterCategory));
                }}

                if (groupIds.length === 0) {{
                    container.innerHTML = `<div class="text-center py-16 text-slate-500 font-mono">No duplicate clusters found matching category: ${{filterCategory}}</div>`;
                    return;
                }}

                // Render top 100 groups
                for (const gid of groupIds.slice(0, 100)) {{
                    const items = groups[gid];
                    const card = document.createElement('div');
                    card.className = "bg-slate-950/80 border border-slate-800 rounded-2xl p-5 shadow-sm";

                    const isAI = items[0].match_type === 'VISUAL_AI_NEAR_DUPLICATE';
                    const badge = isAI ?
                        '<span class="bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 text-xs px-2.5 py-1 rounded-full font-medium">Vision AI Match</span>' :
                        '<span class="bg-amber-500/20 text-amber-400 border border-amber-500/30 text-xs px-2.5 py-1 rounded-full font-medium">Exact Hash Match</span>';

                    card.innerHTML = `
                        <div class="flex justify-between items-center mb-4">
                            <div class="flex items-center gap-3">
                                <span class="font-bold text-white text-sm">Cluster #${{gid}}</span>
                                ${{badge}}
                            </div>
                            <span class="text-xs text-slate-400 font-mono">${{items.length}} files</span>
                        </div>
                        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            ${{items.map(item => `
                                <div class="bg-slate-900 border ${{item.action === 'KEEP' ? 'border-emerald-500/50 bg-emerald-950/10' : 'border-slate-800'}} rounded-xl p-3 flex gap-3 items-center">
                                    ${{isImageFile(item.path) ?
                                        `<img src="/api/thumbnail?path=${{encodeURIComponent(item.path)}}" class="w-16 h-16 rounded-lg object-cover bg-slate-800 flex-shrink-0" loading="lazy" alt="preview">` :
                                        `<div class="w-16 h-16 rounded-lg bg-slate-800 flex items-center justify-center text-slate-500 text-xs font-mono flex-shrink-0">FILE</div>`
                                    }}
                                    <div class="min-w-0 flex-1">
                                        <div class="flex flex-wrap items-center gap-1.5 mb-1.5">
                                            <span class="text-[11px] px-2 py-0.5 rounded font-bold ${{item.action === 'KEEP' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}}">
                                                ${{item.action}}
                                            </span>
                                            ${{getCategoryBadge(item.category)}}
                                            ${{item.similarity && item.action === 'DUPLICATE' ? `<span class="text-xs text-indigo-400 font-mono font-bold ml-auto">${{item.similarity}}</span>` : ''}}
                                        </div>
                                        <p class="text-xs text-slate-200 truncate font-mono" title="${{item.path}}">${{item.path.split('/').pop()}}</p>
                                        <div class="flex items-center gap-2 mt-1">
                                            <span class="text-xs text-slate-400 font-mono">${{item.size_mb}} MB</span>
                                            ${{item.dimensions ? `<span class="text-[10px] text-slate-500 font-mono">${{item.dimensions}}</span>` : ''}}
                                        </div>
                                        <p class="text-[10px] text-slate-500 truncate mt-0.5 font-mono" title="${{item.path}}">${{item.path}}</p>
                                    </div>
                                </div>
                            `).join('')}}
                        </div>
                    `;
                    container.appendChild(card);
                }}
            }}

            async function executeSafeQuarantine() {{
                if (!currentSummary) return;
                if (!confirm("Safely move all detected duplicate files across all paths to '_duplicate_quarantine'? A reversible rollback manifest will be created.")) return;

                const btn = document.getElementById('quarantineBtn');
                btn.disabled = true;
                btn.innerText = "Quarantining...";

                try {{
                    const res = await fetch('/api/quarantine/execute', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ summary_file: currentSummary.summary_json, base_dir: currentSummary.scanned_paths || currentSummary.scanned_dir }})
                    }});
                    const data = await res.json();
                    alert(`Successfully quarantined ${{data.total_files_moved}} files (${{(data.total_bytes_moved / (1024*1024)).toFixed(2)}} MB) across ${{data.base_dirs ? data.base_dirs.length : 1}} root folder(s).`);
                }} catch (e) {{
                    alert("Quarantine error: " + e.message);
                }} finally {{
                    btn.disabled = false;
                    btn.innerText = "Move Duplicates to Quarantine";
                }}
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


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

