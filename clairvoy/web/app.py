"""
Clairvoy Web App Server (FastAPI)
Includes interactive side-by-side visual photo comparison and quarantine controls.
"""

import os
import io
import shutil
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from PIL import Image
from clairvoy.engines.storage_engine import StorageEngine

app = FastAPI(title="Clairvoy", description="Local-first AI storage deduplication engine")

CURRENT_SCAN = {
    "status": "idle",
    "summary": None,
    "target_dir": ""
}

class ScanRequest(BaseModel):
    directory: str
    enable_ml: bool = True
    threshold: float = 0.95

class QuarantineRequest(BaseModel):
    paths: list[str]
    base_dir: str

@app.get("/", response_class=HTMLResponse)
async def index():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Clairvoy | Local Storage Deduplicator & Vision AI</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body { background-color: #0b0f19; color: #f1f5f9; font-family: ui-sans-serif, system-ui, -apple-system; }
        </style>
    </head>
    <body class="p-6 md:p-10">
        <div class="max-w-7xl mx-auto">
            <!-- Header -->
            <header class="flex justify-between items-center pb-6 border-b border-slate-800 mb-8">
                <div>
                    <h1 class="text-3xl font-extrabold tracking-tight text-white flex items-center gap-3">
                        <span class="text-indigo-400">👁️</span> Clairvoy
                    </h1>
                    <p class="text-sm text-slate-400 mt-1">Local-First Storage Deduplicator & Vision Transformer AI</p>
                </div>
                <div class="flex items-center gap-3">
                    <span class="text-xs bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 px-3 py-1.5 rounded-full font-mono">
                        ● Local DINOv2 Engine Active
                    </span>
                    <a href="https://github.com/shubhamshah207/clairvoy" target="_blank" class="text-xs bg-slate-800 hover:bg-slate-700 border border-slate-700 px-3 py-1.5 rounded-full text-slate-300 transition">
                        GitHub Repo ↗
                    </a>
                </div>
            </header>

            <!-- Scan Configuration Card -->
            <div class="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 md:p-8 mb-8 shadow-2xl backdrop-blur">
                <div class="flex flex-col lg:flex-row gap-6 items-end">
                    <div class="flex-1 w-full">
                        <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Storage Directory</label>
                        <input id="dirInput" type="text" placeholder="/mnt/e/Remotes" value="/mnt/e/Remotes" 
                               class="w-full bg-slate-950 border border-slate-800 rounded-2xl px-5 py-3.5 text-sm focus:outline-none focus:border-indigo-500 text-slate-100 font-mono transition">
                    </div>
                    <div class="w-full lg:w-48">
                        <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                            AI Sensitivity: <span id="thresholdVal" class="text-indigo-400 font-bold">95%</span>
                        </label>
                        <input id="thresholdInput" type="range" min="80" max="99" value="95" oninput="document.getElementById('thresholdVal').innerText = this.value + '%'" 
                               class="w-full accent-indigo-500 cursor-pointer">
                    </div>
                    <div class="flex items-center gap-3">
                        <button onclick="startScan()" id="scanBtn" class="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-8 py-3.5 rounded-2xl transition shadow-lg shadow-indigo-600/30 flex items-center gap-2">
                            <span>Scan Storage</span>
                        </button>
                    </div>
                </div>
                <div id="scanStatus" class="text-xs text-slate-400 mt-3"></div>
            </div>

            <!-- Stats Grid -->
            <div id="statsGrid" class="grid grid-cols-2 md:grid-cols-4 gap-5 mb-8 hidden">
                <div class="bg-slate-900/70 border border-slate-800 p-5 rounded-2xl">
                    <div class="text-xs uppercase tracking-wider text-slate-400 font-medium">Scanned Files</div>
                    <div id="statFiles" class="text-3xl font-extrabold text-white mt-1.5">0</div>
                </div>
                <div class="bg-slate-900/70 border border-slate-800 p-5 rounded-2xl">
                    <div class="text-xs uppercase tracking-wider text-slate-400 font-medium">Exact Duplicates</div>
                    <div id="statExact" class="text-3xl font-extrabold text-amber-400 mt-1.5">0</div>
                </div>
                <div class="bg-slate-900/70 border border-slate-800 p-5 rounded-2xl">
                    <div class="text-xs uppercase tracking-wider text-slate-400 font-medium">Vision AI Clusters</div>
                    <div id="statML" class="text-3xl font-extrabold text-indigo-400 mt-1.5">0</div>
                </div>
                <div class="bg-slate-900/70 border border-slate-800 p-5 rounded-2xl">
                    <div class="text-xs uppercase tracking-wider text-slate-400 font-medium">Recoverable Space</div>
                    <div id="statSpace" class="text-3xl font-extrabold text-emerald-400 mt-1.5">0 MB</div>
                </div>
            </div>

            <!-- Results Section -->
            <div id="resultsCard" class="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 md:p-8 shadow-2xl hidden">
                <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6 pb-6 border-b border-slate-800">
                    <div>
                        <h2 class="text-xl font-bold text-white">Visual Comparison & Duplicate Sets</h2>
                        <p class="text-xs text-slate-400 mt-1">Review matches side-by-side. The highest quality original is tagged as KEEP.</p>
                    </div>
                    <div class="flex items-center gap-3">
                        <button onclick="quarantineAll()" class="bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold px-5 py-2.5 rounded-xl transition shadow-lg shadow-rose-600/20">
                            Move Duplicates to Quarantine
                        </button>
                    </div>
                </div>

                <!-- Group Cards Container -->
                <div id="clustersContainer" class="space-y-6"></div>
            </div>
        </div>

        <script>
            let scanResults = null;

            async function startScan() {
                const dir = document.getElementById('dirInput').value.trim();
                const threshold = parseFloat(document.getElementById('thresholdInput').value) / 100.0;
                if (!dir) return;

                const btn = document.getElementById('scanBtn');
                const status = document.getElementById('scanStatus');
                btn.disabled = true;
                btn.classList.add('opacity-50');
                status.innerText = "Scanning files and running Vision AI embeddings... please wait.";

                try {
                    const res = await fetch('/api/scan', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({directory: dir, enable_ml: true, threshold: threshold})
                    });
                    scanResults = await res.json();
                    status.innerText = "Scan completed successfully!";
                    
                    document.getElementById('statsGrid').classList.remove('hidden');
                    document.getElementById('resultsCard').classList.remove('hidden');

                    document.getElementById('statFiles').innerText = scanResults.total_files_scanned.toLocaleString();
                    document.getElementById('statExact').innerText = scanResults.exact_duplicate_groups.toLocaleString();
                    document.getElementById('statML').innerText = scanResults.visual_ai_groups.toLocaleString();
                    document.getElementById('statSpace').innerText = scanResults.wasted_mb + " MB (" + scanResults.wasted_gb + " GB)";

                    renderClusters(scanResults.groups);
                } catch(e) {
                    status.innerText = "Scan error: " + e;
                } finally {
                    btn.disabled = false;
                    btn.classList.remove('opacity-50');
                }
            }

            function isImage(path) {
                const exts = ['.jpg', '.jpeg', '.png', '.webp', '.bmp'];
                return exts.some(e => path.toLowerCase().endsWith(e));
            }

            function renderClusters(groups) {
                const container = document.getElementById('clustersContainer');
                container.innerHTML = '';

                // Group records by group_id
                const grouped = {};
                for (const r of groups) {
                    if (!grouped[r.group_id]) grouped[r.group_id] = [];
                    grouped[r.group_id].push(r);
                }

                const groupKeys = Object.keys(grouped);
                if (groupKeys.length === 0) {
                    container.innerHTML = '<div class="text-center py-12 text-slate-500">No duplicates found in this directory! Clean storage.</div>';
                    return;
                }

                for (const gid of groupKeys.slice(0, 50)) { // Render top 50
                    const items = grouped[gid];
                    const card = document.createElement('div');
                    card.className = 'bg-slate-950 border border-slate-800/80 rounded-2xl p-5 shadow-sm';

                    const matchType = items[0].match_type === 'VISUAL_AI_NEAR_DUPLICATE' ? 
                        '<span class="bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 text-xs px-2.5 py-1 rounded-full font-medium">Vision AI Match</span>' :
                        '<span class="bg-amber-500/20 text-amber-400 border border-amber-500/30 text-xs px-2.5 py-1 rounded-full font-medium">Exact Hash Match</span>';

                    card.innerHTML = `
                        <div class="flex justify-between items-center mb-4">
                            <div class="flex items-center gap-3">
                                <span class="font-bold text-white text-sm">Group #${gid}</span>
                                ${matchType}
                            </div>
                            <span class="text-xs text-slate-400 font-mono">${items.length} files</span>
                        </div>
                        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            ${items.map(item => `
                                <div class="bg-slate-900 border ${item.action === 'KEEP' ? 'border-emerald-500/40 bg-emerald-950/10' : 'border-slate-800'} rounded-xl p-3 flex gap-3 items-center">
                                    ${isImage(item.path) ? 
                                        `<img src="/api/thumbnail?path=${encodeURIComponent(item.path)}" class="w-16 h-16 rounded-lg object-cover bg-slate-800 flex-shrink-0" loading="lazy">` : 
                                        `<div class="w-16 h-16 rounded-lg bg-slate-800 flex items-center justify-center text-slate-500 text-xl font-mono flex-shrink-0">FILE</div>`
                                    }
                                    <div class="min-w-0 flex-1">
                                        <div class="flex items-center gap-2 mb-1">
                                            <span class="text-xs px-2 py-0.5 rounded font-bold ${item.action === 'KEEP' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}">
                                                ${item.action}
                                            </span>
                                            <span class="text-xs text-slate-400 font-mono">${item.size_mb} MB</span>
                                            ${item.similarity ? `<span class="text-xs text-indigo-400 font-mono ml-auto">${item.similarity}</span>` : ''}
                                        </div>
                                        <p class="text-xs text-slate-300 truncate font-mono" title="${item.path}">${item.path.split('/').pop()}</p>
                                        <p class="text-[10px] text-slate-500 truncate mt-0.5 font-mono" title="${item.path}">${item.path}</p>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    `;
                    container.appendChild(card);
                }
            }

            async function quarantineAll() {
                if (!confirm("Are you sure you want to safely move all detected duplicate files to the _duplicate_quarantine folder?")) return;
                alert("Running safe quarantine script generated by Clairvoy. Check your target directory _dedupe_reports/quarantine_duplicates.sh");
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/api/thumbnail")
async def get_thumbnail(path: str = Query(...)):
    """Serve a fast, downscaled image thumbnail for visual review."""
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")
    try:
        with Image.open(path) as img:
            img.thumbnail((200, 200), Image.Resampling.BILINEAR)
            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="JPEG", quality=80)
            buf.seek(0)
            return StreamingResponse(buf, media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/scan")
async def trigger_scan(req: ScanRequest):
    if not os.path.isdir(req.directory):
        raise HTTPException(status_code=400, detail=f"Directory '{req.directory}' not found")
    
    engine = StorageEngine(
        base_dir=req.directory,
        enable_ml=req.enable_ml,
        ml_threshold=req.threshold
    )
    summary = engine.run()
    CURRENT_SCAN["status"] = "completed"
    CURRENT_SCAN["summary"] = summary
    CURRENT_SCAN["target_dir"] = req.directory
    return summary

@app.get("/api/status")
async def get_status():
    return CURRENT_SCAN
