"""
Clairvoy Web App Server (FastAPI)
"""

import os
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from clairvoy.engines.storage_engine import StorageEngine

app = FastAPI(title="Clairvoy", description="Local-first AI storage deduplication engine")

CURRENT_SCAN = {
    "status": "idle",
    "summary": None,
    "target_dir": ""
}

class ScanRequest(BaseModel):
    directory: str
    quarantine: bool = False

@app.get("/", response_class=HTMLResponse)
async def index():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Clairvoy | Local Storage Deduplicator</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body { background-color: #0f172a; color: #e2e8f0; font-family: ui-sans-serif, system-ui, -apple-system; }
        </style>
    </head>
    <body class="p-8">
        <div class="max-w-6xl mx-auto">
            <!-- Header -->
            <header class="flex justify-between items-center pb-6 border-b border-slate-700 mb-8">
                <div>
                    <h1 class="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
                        <span>👁️</span> Clairvoy
                    </h1>
                    <p class="text-sm text-slate-400 mt-1">Local-first AI Deduplication & Storage Curation</p>
                </div>
                <div class="text-xs bg-slate-800 border border-slate-700 px-3 py-1.5 rounded-full text-emerald-400 font-mono">
                    ● Local Core Active
                </div>
            </header>

            <!-- Scan Card -->
            <div class="bg-slate-800/80 border border-slate-700 rounded-2xl p-6 mb-8 shadow-xl">
                <h2 class="text-lg font-semibold text-white mb-4">Start Storage Scan</h2>
                <div class="flex gap-4">
                    <input id="dirInput" type="text" placeholder="/mnt/e/Remotes" value="/mnt/e/Remotes" 
                           class="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-indigo-500 text-slate-200">
                    <button onclick="startScan()" class="bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-6 py-3 rounded-xl transition shadow-lg shadow-indigo-600/20">
                        Scan Storage
                    </button>
                </div>
                <p id="scanStatus" class="text-xs text-slate-400 mt-3"></p>
            </div>

            <!-- Stats Grid -->
            <div id="statsGrid" class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8 hidden">
                <div class="bg-slate-800/50 border border-slate-700/80 p-5 rounded-2xl">
                    <div class="text-xs uppercase tracking-wider text-slate-400 font-medium">Files Scanned</div>
                    <div id="statFiles" class="text-3xl font-bold text-white mt-1">0</div>
                </div>
                <div class="bg-slate-800/50 border border-slate-700/80 p-5 rounded-2xl">
                    <div class="text-xs uppercase tracking-wider text-slate-400 font-medium">Duplicate Sets</div>
                    <div id="statGroups" class="text-3xl font-bold text-amber-400 mt-1">0</div>
                </div>
                <div class="bg-slate-800/50 border border-slate-700/80 p-5 rounded-2xl">
                    <div class="text-xs uppercase tracking-wider text-slate-400 font-medium">Recoverable Space</div>
                    <div id="statSpace" class="text-3xl font-bold text-emerald-400 mt-1">0 MB</div>
                </div>
            </div>

            <!-- Results Preview -->
            <div id="resultsCard" class="bg-slate-800/80 border border-slate-700 rounded-2xl p-6 shadow-xl hidden">
                <div class="flex justify-between items-center mb-6">
                    <h2 class="text-lg font-semibold text-white">Duplicate Breakdown</h2>
                    <span class="text-xs text-slate-400">Reports exported to _dedupe_reports/</span>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-sm text-slate-300">
                        <thead class="bg-slate-900/60 text-xs text-slate-400 uppercase tracking-wider">
                            <tr>
                                <th class="p-3 rounded-l-lg">Group</th>
                                <th class="p-3">Action</th>
                                <th class="p-3">Size (MB)</th>
                                <th class="p-3 rounded-r-lg">Path</th>
                            </tr>
                        </thead>
                        <tbody id="duplicatesTable" class="divide-y divide-slate-700/50 font-mono text-xs">
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <script>
            async function startScan() {
                const dir = document.getElementById('dirInput').value.trim();
                if (!dir) return;
                const status = document.getElementById('scanStatus');
                status.innerText = "Scanning in progress... please wait.";
                
                try {
                    const res = await fetch('/api/scan', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({directory: dir})
                    });
                    const data = await res.json();
                    status.innerText = "Scan completed!";
                    document.getElementById('statsGrid').classList.remove('hidden');
                    document.getElementById('statFiles').innerText = data.total_files_scanned;
                    document.getElementById('statGroups').innerText = data.duplicate_groups;
                    document.getElementById('statSpace').innerText = data.wasted_mb + " MB (" + data.wasted_gb + " GB)";
                } catch(e) {
                    status.innerText = "Error during scan: " + e;
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/api/scan")
async def trigger_scan(req: ScanRequest):
    if not os.path.isdir(req.directory):
        raise HTTPException(status_code=400, detail=f"Directory '{req.directory}' not found")
    
    engine = StorageEngine(req.directory)
    summary = engine.run()
    CURRENT_SCAN["status"] = "completed"
    CURRENT_SCAN["summary"] = summary
    CURRENT_SCAN["target_dir"] = req.directory
    return summary

@app.get("/api/status")
async def get_status():
    return CURRENT_SCAN
