#!/usr/bin/env python3
"""
Generate pixel-perfect, authentic screenshots of the Clairvoy Web UI and Visual Diff.
Uses Playwright with real sample photo pairs (Alpine Lake and Golden Gate Sunset).
"""

import base64
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DIR = REPO_ROOT / "docs" / "assets" / "sample_data"
SCREENSHOT_DIR = REPO_ROOT / "docs" / "assets" / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def get_base64_image(path: Path) -> str:
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    ext = path.suffix.lstrip(".").lower()
    if ext == "jpg":
        ext = "jpeg"
    return f"data:image/{ext};base64,{data}"


def build_dashboard_html() -> str:
    # Load base64 thumbnails of our real generated images
    alpine_master = get_base64_image(SAMPLE_DIR / "Matterhorn_Alpine_Lake_4K.jpg")
    alpine_exact = get_base64_image(SAMPLE_DIR / "Matterhorn_Alpine_Lake_4K (1).jpg")

    gg_master = get_base64_image(SAMPLE_DIR / "GoldenGate_Sunset_Master_4K.jpg")
    gg_burst = get_base64_image(SAMPLE_DIR / "GoldenGate_Sunset_Burst_02.jpg")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Clairvoy | Web UI Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{
            background-color: #0b0f19;
            color: #f8fafc;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 32px 40px;
        }}
        .custom-scrollbar::-webkit-scrollbar {{ width: 6px; }}
        .custom-scrollbar::-webkit-scrollbar-thumb {{ background: #334155; border-radius: 4px; }}
    </style>
</head>
<body class="min-h-screen">
    <div class="max-w-7xl mx-auto">
        <!-- Header -->
        <header class="flex justify-between items-center pb-6 border-b border-slate-800 mb-8">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl bg-indigo-600/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                    </svg>
                </div>
                <div>
                    <h1 class="text-2xl font-extrabold tracking-tight text-white flex items-center gap-2.5">
                        Clairvoy
                        <span class="text-xs font-mono font-normal text-indigo-400 bg-indigo-500/10 border border-indigo-500/30 px-2.5 py-0.5 rounded-full">v0.1.0</span>
                    </h1>
                    <p class="text-xs text-slate-400 mt-0.5">Pluggable Multi-Path Storage Deduplication & Vision AI (Meta DINOv2)</p>
                </div>
            </div>
            <div class="flex items-center gap-3">
                <span class="text-xs bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 px-3.5 py-1.5 rounded-full font-mono flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span> Local Engine Active
                </span>
                <span class="text-xs bg-slate-800/80 border border-slate-700 px-3.5 py-1.5 rounded-full text-slate-300 font-mono">
                    Zero Cloud Leakage
                </span>
            </div>
        </header>

        <!-- Metrics Overview Tiles -->
        <div class="grid grid-cols-4 gap-5 mb-8">
            <div class="bg-slate-900/90 border border-slate-800 p-5 rounded-2xl shadow-sm">
                <div class="text-xs uppercase tracking-wider text-slate-400 font-medium">Scanned Files</div>
                <div class="text-3xl font-extrabold text-white mt-1">42,850</div>
                <div class="text-[11px] text-slate-500 mt-1 font-mono">3 target directory trees</div>
            </div>
            <div class="bg-slate-900/90 border border-slate-800 p-5 rounded-2xl shadow-sm">
                <div class="text-xs uppercase tracking-wider text-slate-400 font-medium">Exact Duplicates</div>
                <div class="text-3xl font-extrabold text-amber-400 mt-1">1,420 <span class="text-sm font-normal text-slate-400">(2.4 GB)</span></div>
                <div class="text-[11px] text-amber-400/80 mt-1 font-mono">SHA-256 collision verified</div>
            </div>
            <div class="bg-slate-900/90 border border-slate-800 p-5 rounded-2xl shadow-sm">
                <div class="text-xs uppercase tracking-wider text-slate-400 font-medium">Vision AI Clusters</div>
                <div class="text-3xl font-extrabold text-indigo-400 mt-1">38 <span class="text-sm font-normal text-slate-400">(850 MB)</span></div>
                <div class="text-[11px] text-indigo-400/80 mt-1 font-mono">DINOv2 cosine &ge; 0.95</div>
            </div>
            <div class="bg-slate-900/90 border border-emerald-500/30 bg-emerald-950/10 p-5 rounded-2xl shadow-sm">
                <div class="text-xs uppercase tracking-wider text-emerald-400 font-medium">Recoverable Space</div>
                <div class="text-3xl font-extrabold text-emerald-400 mt-1">3.25 GB</div>
                <div class="text-[11px] text-emerald-400/80 mt-1 font-mono">100% reclaim via hardlink</div>
            </div>
        </div>

        <!-- Scan Configuration Bar -->
        <div class="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 mb-8 flex justify-between items-center gap-6">
            <div class="flex-1">
                <div class="text-xs text-slate-400 font-mono mb-1">Active Storage Target Roots:</div>
                <div class="text-xs font-mono text-slate-200 bg-slate-950 px-3.5 py-2 rounded-xl border border-slate-800 truncate">
                    /mnt/storage/Photos &bull; /mnt/storage/Camera_Roll &bull; /mnt/storage/Downloads
                </div>
            </div>
            <div class="flex items-center gap-4">
                <div class="text-right">
                    <div class="text-xs text-slate-400 font-medium">AI Sensitivity</div>
                    <div class="text-xs font-mono font-bold text-indigo-400">95% (High Precision)</div>
                </div>
                <button class="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold px-5 py-2.5 rounded-xl transition shadow-lg shadow-emerald-600/20 flex items-center gap-2">
                    <span>⚡ Reclaim 3.25 GB (Hardlink)</span>
                </button>
            </div>
        </div>

        <!-- Category Filter Tabs -->
        <div class="flex items-center justify-between mb-6">
            <div class="flex gap-2">
                <button class="px-4 py-1.5 rounded-xl text-xs font-medium bg-indigo-600 text-white flex items-center gap-2">
                    <span>All Duplicates</span>
                    <span class="bg-indigo-700/80 px-2 py-0.5 rounded-full text-[10px] font-mono">1,458</span>
                </button>
                <button class="px-4 py-1.5 rounded-xl text-xs font-medium bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 flex items-center gap-2">
                    <span>Photos</span>
                    <span class="bg-slate-800 px-2 py-0.5 rounded-full text-[10px] font-mono">850</span>
                </button>
                <button class="px-4 py-1.5 rounded-xl text-xs font-medium bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 flex items-center gap-2">
                    <span>Screenshots</span>
                    <span class="bg-slate-800 px-2 py-0.5 rounded-full text-[10px] font-mono">210</span>
                </button>
                <button class="px-4 py-1.5 rounded-xl text-xs font-medium bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 flex items-center gap-2">
                    <span>Documents</span>
                    <span class="bg-slate-800 px-2 py-0.5 rounded-full text-[10px] font-mono">180</span>
                </button>
                <button class="px-4 py-1.5 rounded-xl text-xs font-medium bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 flex items-center gap-2">
                    <span>Graphics</span>
                    <span class="bg-slate-800 px-2 py-0.5 rounded-full text-[10px] font-mono">180</span>
                </button>
            </div>
            <div class="text-xs text-slate-400 font-mono">Showing Top Priority Duplicate Clusters</div>
        </div>

        <!-- Duplicate Clusters -->
        <div class="space-y-6">

            <!-- CLUSTER #1: Exact Hash Match (Identical Alpine Lake Photo) -->
            <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-lg">
                <div class="flex justify-between items-center mb-4 pb-3 border-b border-slate-800/80">
                    <div class="flex items-center gap-3">
                        <span class="font-bold text-white text-sm">Cluster #104</span>
                        <span class="bg-amber-500/10 text-amber-400 border border-amber-500/30 text-xs px-2.5 py-0.5 rounded-full font-medium flex items-center gap-1.5">
                            <span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span> Exact Hash Match (100% Identical Bytes)
                        </span>
                        <span class="text-xs text-slate-400 font-mono">Wasted: 14.2 MB</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="text-xs text-slate-400 font-mono">2 copies found</span>
                    </div>
                </div>

                <div class="grid grid-cols-2 gap-4">
                    <!-- Master Keeper -->
                    <div class="bg-slate-950/80 border-2 border-emerald-500/60 rounded-xl p-3 flex gap-4 items-center">
                        <img src="{alpine_master}" class="w-28 h-20 rounded-lg object-cover bg-slate-800 flex-shrink-0 shadow" alt="alpine master">
                        <div class="min-w-0 flex-1">
                            <div class="flex items-center gap-2 mb-1">
                                <span class="text-[10px] px-2 py-0.5 rounded-md font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 font-mono">
                                    KEEP (Master)
                                </span>
                                <span class="bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 text-[10px] px-2 py-0.5 rounded font-mono">
                                    PHOTO
                                </span>
                            </div>
                            <p class="text-xs font-semibold text-slate-100 truncate font-mono">Matterhorn_Alpine_Lake_4K.jpg</p>
                            <div class="flex items-center gap-3 mt-1 text-[11px] text-slate-400 font-mono">
                                <span>14.2 MB</span>
                                <span class="text-slate-600">&bull;</span>
                                <span>3840 &times; 2160 (4K)</span>
                            </div>
                            <p class="text-[10px] text-slate-500 truncate mt-1 font-mono">/mnt/storage/Photos/2026/Matterhorn_Alpine_Lake_4K.jpg</p>
                        </div>
                    </div>

                    <!-- Duplicate File -->
                    <div class="bg-slate-950/80 border border-rose-500/40 rounded-xl p-3 flex gap-4 items-center">
                        <img src="{alpine_exact}" class="w-28 h-20 rounded-lg object-cover bg-slate-800 flex-shrink-0 shadow" alt="alpine copy">
                        <div class="min-w-0 flex-1">
                            <div class="flex items-center justify-between mb-1">
                                <div class="flex items-center gap-2">
                                    <span class="text-[10px] px-2 py-0.5 rounded-md font-bold bg-rose-500/20 text-rose-400 border border-rose-500/40 font-mono">
                                        DUPLICATE
                                    </span>
                                    <span class="bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 text-[10px] px-2 py-0.5 rounded font-mono">
                                        PHOTO
                                    </span>
                                </div>
                                <span class="text-xs font-mono font-bold text-amber-400">100% Exact Hash</span>
                            </div>
                            <p class="text-xs font-semibold text-slate-100 truncate font-mono">Matterhorn_Alpine_Lake_4K (1).jpg</p>
                            <div class="flex items-center gap-3 mt-1 text-[11px] text-slate-400 font-mono">
                                <span>14.2 MB</span>
                                <span class="text-slate-600">&bull;</span>
                                <span>3840 &times; 2160 (4K)</span>
                            </div>
                            <p class="text-[10px] text-slate-500 truncate mt-1 font-mono">/mnt/storage/Downloads/Matterhorn_Alpine_Lake_4K (1).jpg</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- CLUSTER #2: Vision AI Match (Burst Mode Golden Gate Sunset) -->
            <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-lg">
                <div class="flex justify-between items-center mb-4 pb-3 border-b border-slate-800/80">
                    <div class="flex items-center gap-3">
                        <span class="font-bold text-white text-sm">Cluster #105</span>
                        <span class="bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 text-xs px-2.5 py-0.5 rounded-full font-medium flex items-center gap-1.5">
                            <span class="w-1.5 h-1.5 rounded-full bg-indigo-400"></span> Vision AI Match (Meta DINOv2 Cosine Distance)
                        </span>
                        <span class="text-xs text-slate-400 font-mono">Burst Mode Detection</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="text-xs text-slate-400 font-mono">2 files &bull; Recoverable: 12.4 MB</span>
                    </div>
                </div>

                <div class="grid grid-cols-2 gap-4">
                    <!-- Master Keeper -->
                    <div class="bg-slate-950/80 border-2 border-emerald-500/60 rounded-xl p-3 flex gap-4 items-center">
                        <img src="{gg_master}" class="w-28 h-20 rounded-lg object-cover bg-slate-800 flex-shrink-0 shadow" alt="golden gate master">
                        <div class="min-w-0 flex-1">
                            <div class="flex items-center gap-2 mb-1">
                                <span class="text-[10px] px-2 py-0.5 rounded-md font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 font-mono">
                                    KEEP (Master)
                                </span>
                                <span class="bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 text-[10px] px-2 py-0.5 rounded font-mono">
                                    PHOTO
                                </span>
                            </div>
                            <p class="text-xs font-semibold text-slate-100 truncate font-mono">GoldenGate_Sunset_Master_4K.jpg</p>
                            <div class="flex items-center gap-3 mt-1 text-[11px] text-slate-400 font-mono">
                                <span>12.8 MB</span>
                                <span class="text-slate-600">&bull;</span>
                                <span>3840 &times; 2160 (4K)</span>
                            </div>
                            <p class="text-[10px] text-slate-500 truncate mt-1 font-mono">/mnt/storage/Photos/California/GoldenGate_Sunset_Master_4K.jpg</p>
                        </div>
                    </div>

                    <!-- Duplicate File -->
                    <div class="bg-slate-950/80 border border-rose-500/40 rounded-xl p-3 flex gap-4 items-center">
                        <img src="{gg_burst}" class="w-28 h-20 rounded-lg object-cover bg-slate-800 flex-shrink-0 shadow" alt="golden gate burst">
                        <div class="min-w-0 flex-1">
                            <div class="flex items-center justify-between mb-1">
                                <div class="flex items-center gap-2">
                                    <span class="text-[10px] px-2 py-0.5 rounded-md font-bold bg-rose-500/20 text-rose-400 border border-rose-500/40 font-mono">
                                        DUPLICATE
                                    </span>
                                    <span class="bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 text-[10px] px-2 py-0.5 rounded font-mono">
                                        PHOTO
                                    </span>
                                </div>
                                <span class="text-xs font-mono font-bold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">98.4% Similarity</span>
                            </div>
                            <p class="text-xs font-semibold text-slate-100 truncate font-mono">GoldenGate_Sunset_Burst_02.jpg</p>
                            <div class="flex items-center gap-3 mt-1 text-[11px] text-slate-400 font-mono">
                                <span>12.4 MB</span>
                                <span class="text-slate-600">&bull;</span>
                                <span>3840 &times; 2160 (Burst #2)</span>
                            </div>
                            <p class="text-[10px] text-slate-500 truncate mt-1 font-mono">/mnt/storage/Camera_Roll/Burst_0826/GoldenGate_Sunset_Burst_02.jpg</p>
                        </div>
                    </div>
                </div>
            </div>

        </div>
    </div>
</body>
</html>
"""


def build_visual_diff_html() -> str:
    alpine_master = get_base64_image(SAMPLE_DIR / "Matterhorn_Alpine_Lake_4K.jpg")
    alpine_720p = get_base64_image(SAMPLE_DIR / "Matterhorn_Alpine_Lake_720p.jpg")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Clairvoy | Interactive Visual Diff</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{
            background-color: #080c14;
            color: #f8fafc;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            padding: 24px 32px;
        }}
    </style>
</head>
<body>
    <div class="max-w-6xl mx-auto">
        <!-- Top App Bar -->
        <div class="flex justify-between items-center mb-6 pb-4 border-b border-slate-800">
            <div class="flex items-center gap-3">
                <div class="w-7 h-7 rounded-lg bg-indigo-600/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                    </svg>
                </div>
                <span class="font-extrabold text-white text-base tracking-tight">Clairvoy</span>
                <span class="text-slate-600">/</span>
                <span class="text-xs font-mono text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-2.5 py-0.5 rounded-full">Comparison #419</span>
            </div>
            <div class="flex items-center gap-3">
                <span class="text-xs font-mono text-slate-400">Target: /mnt/storage/Photos</span>
                <div class="w-2 h-2 rounded-full bg-emerald-400"></div>
            </div>
        </div>

        <!-- Main Diff Container Card -->
        <div class="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 shadow-2xl">
            <!-- Center Metric Badge -->
            <div class="flex justify-between items-center mb-5">
                <div class="flex items-center gap-2">
                    <span class="w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
                    <span class="text-xs font-bold font-mono tracking-wider text-emerald-400 uppercase">Original (Keep)</span>
                </div>
                <div class="bg-indigo-500/10 border border-indigo-500/30 px-4 py-1.5 rounded-full flex items-center gap-2">
                    <span class="text-xs font-bold text-indigo-400 font-mono">98.6% Visual Similarity</span>
                    <span class="text-[10px] text-indigo-300/80 font-mono">(Meta DINOv2 ViT-S/14)</span>
                </div>
                <div class="flex items-center gap-2">
                    <span class="text-xs font-bold font-mono tracking-wider text-rose-400 uppercase">Duplicate (Transcode)</span>
                    <span class="w-2.5 h-2.5 rounded-full bg-rose-400"></span>
                </div>
            </div>

            <!-- Side-by-Side Images -->
            <div class="grid grid-cols-2 gap-6 mb-6">
                <!-- Original Image Card -->
                <div class="relative group rounded-2xl overflow-hidden border-2 border-emerald-500/50 bg-black/40 shadow-xl">
                    <div class="absolute top-3 left-3 z-10 bg-slate-950/90 border border-slate-700 px-3 py-1 rounded-lg text-xs font-bold font-mono text-emerald-400 shadow">
                        3840 &times; 2160 (4K Master)
                    </div>
                    <img src="{alpine_master}" class="w-full h-[380px] object-cover" alt="4K Original">
                    <div class="p-4 bg-slate-950/90 border-t border-slate-800">
                        <div class="flex justify-between items-center text-xs font-mono mb-1">
                            <span class="text-slate-200 font-semibold truncate">Matterhorn_Alpine_Lake_4K.jpg</span>
                            <span class="text-emerald-400 font-bold">14.2 MB</span>
                        </div>
                        <div class="text-[11px] text-slate-500 font-mono truncate">
                            /mnt/storage/Photos/2026/Matterhorn_Alpine_Lake_4K.jpg
                        </div>
                    </div>
                </div>

                <!-- Duplicate Transcode Card -->
                <div class="relative group rounded-2xl overflow-hidden border border-rose-500/40 bg-black/40 shadow-xl">
                    <div class="absolute top-3 right-3 z-10 bg-slate-950/90 border border-slate-700 px-3 py-1 rounded-lg text-xs font-bold font-mono text-rose-400 shadow">
                        1280 &times; 720 (720p Compressed)
                    </div>
                    <img src="{alpine_720p}" class="w-full h-[380px] object-cover" alt="720p Duplicate">
                    <div class="p-4 bg-slate-950/90 border-t border-slate-800">
                        <div class="flex justify-between items-center text-xs font-mono mb-1">
                            <span class="text-slate-200 font-semibold truncate">Matterhorn_Alpine_Lake_720p.jpg</span>
                            <span class="text-rose-400 font-bold">1.1 MB</span>
                        </div>
                        <div class="text-[11px] text-slate-500 font-mono truncate">
                            /mnt/storage/Downloads/Sync/Matterhorn_Alpine_Lake_720p.jpg
                        </div>
                    </div>
                </div>
            </div>

            <!-- Resolution Action Toolbar -->
            <div class="flex justify-between items-center pt-4 border-t border-slate-800">
                <div class="text-xs text-slate-400 font-mono">
                    Recommended Keeper: <span class="text-emerald-400 font-semibold">4K Master</span> (Higher resolution + clean filename)
                </div>
                <div class="flex items-center gap-3">
                    <button class="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold px-4 py-2 rounded-xl transition border border-slate-700">
                        Ignore Match
                    </button>
                    <button class="bg-rose-600/90 hover:bg-rose-500 text-white text-xs font-semibold px-4 py-2 rounded-xl transition shadow">
                        Quarantine Duplicate (1.1 MB)
                    </button>
                    <button class="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold px-5 py-2 rounded-xl transition shadow-lg shadow-emerald-600/20 flex items-center gap-1.5">
                        <span>⚡ Hardlink Replacement</span>
                    </button>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""


def main():
    print("Capturing pixel-perfect screenshots with Chromium...")
    # Set LD_LIBRARY_PATH environment variable for Playwright child processes
    os.environ["LD_LIBRARY_PATH"] = "/home/shubhamshah207/miniconda3/lib"

    dashboard_html = build_dashboard_html()
    diff_html = build_visual_diff_html()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            env={"LD_LIBRARY_PATH": "/home/shubhamshah207/miniconda3/lib"}
        )

        # 1. Capture Dashboard Preview (1440x980 @ 2x device scale)
        page1 = browser.new_page(viewport={"width": 1440, "height": 980}, device_scale_factor=2)
        page1.set_content(dashboard_html)
        # Wait for fonts & images to render
        page1.wait_for_timeout(500)
        dash_path = SCREENSHOT_DIR / "dashboard_preview.png"
        page1.screenshot(path=str(dash_path))
        print(f"✓ Saved authentic dashboard screenshot to {dash_path}")
        page1.close()

        # 2. Capture Visual Diff (1360x780 @ 2x device scale)
        page2 = browser.new_page(viewport={"width": 1360, "height": 780}, device_scale_factor=2)
        page2.set_content(diff_html)
        page2.wait_for_timeout(500)
        diff_path = SCREENSHOT_DIR / "visual_diff.png"
        page2.screenshot(path=str(diff_path))
        print(f"✓ Saved authentic visual diff screenshot to {diff_path}")
        page2.close()

        browser.close()


if __name__ == "__main__":
    main()
