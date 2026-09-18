"""
Clairvoy Web UI Component
Premier, CleanMyMac & Immich inspired storage deduplication interface.
100% offline, zero-dependency modern dark design with high-performance pagination,
hero storage meter, side-by-side comparison lightbox, and interactive keeper overrides.
"""

from clairvoy.core.config import VERSION


def get_index_html() -> str:
    """Renders the comprehensive, modern single-page dashboard."""
    return f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Clairvoy | Local-First AI Storage Optimization Studio</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {{
            darkMode: 'class',
            theme: {{
                extend: {{
                    colors: {{
                        slate: {{
                            850: '#151e2e',
                            950: '#070b14',
                        }}
                    }}
                }}
            }}
        }}
    </script>
    <style>
        body {{
            background-color: #070b14;
            color: #f1f5f9;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            overflow-x: hidden;
        }}
        .custom-scrollbar::-webkit-scrollbar {{ width: 6px; height: 6px; }}
        .custom-scrollbar::-webkit-scrollbar-thumb {{ background: #334155; border-radius: 4px; }}
        .custom-scrollbar::-webkit-scrollbar-track {{ background: transparent; }}
        .glass-panel {{
            background: rgba(15, 23, 42, 0.85);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(51, 65, 85, 0.6);
        }}
        .glass-panel-subtle {{
            background: rgba(15, 23, 42, 0.6);
            backdrop-filter: blur(8px);
            border: 1px solid rgba(51, 65, 85, 0.4);
        }}
        .glow-emerald {{
            box-shadow: 0 0 20px -3px rgba(16, 185, 129, 0.25);
        }}
        .glow-indigo {{
            box-shadow: 0 0 25px -4px rgba(99, 102, 241, 0.35);
        }}
        @keyframes pulse-slow {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.4; }}
        }}
        .animate-pulse-slow {{ animation: pulse-slow 3s cubic-bezier(0.4, 0, 0.6, 1) infinite; }}
    </style>
</head>
<body class="min-h-screen pb-28 custom-scrollbar">

    <!-- Top Navigation Bar -->
    <header class="sticky top-0 z-40 glass-panel border-b border-slate-800/80 px-6 py-3.5 mb-6">
        <div class="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
            <div class="flex items-center gap-4">
                <div class="flex items-center gap-2.5">
                    <span class="text-2xl filter drop-shadow">👁️</span>
                    <span class="text-xl font-black tracking-tight text-white flex items-center gap-2">
                        Clairvoy
                        <span class="text-[11px] font-mono font-medium text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 rounded-full">v{VERSION}</span>
                    </span>
                </div>
                <div class="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-mono">
                    <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                    <span>100% Offline & Local</span>
                </div>
            </div>

            <!-- Run Selector & New Scan Button -->
            <div class="flex flex-wrap items-center gap-3">
                <div class="flex items-center bg-slate-900 border border-slate-700/80 rounded-xl px-3 py-1.5 shadow-sm">
                    <span class="text-xs font-mono text-indigo-400 mr-2 flex items-center gap-1">📂 <span>Runs:</span></span>
                    <select id="runsDropdown" onchange="onRunSelected(this.value)" class="bg-transparent text-xs text-slate-200 focus:outline-none font-mono cursor-pointer max-w-[280px] truncate">
                        <option value="" class="bg-slate-900 text-slate-400">Loading past runs...</option>
                    </select>
                </div>

                <button onclick="toggleScanDrawer()" id="toggleScanBtn" class="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium px-3.5 py-1.5 rounded-xl transition flex items-center gap-1.5">
                    <span>⚡</span> <span>New Scan</span>
                </button>

                <a href="https://github.com/shubhamshah207/clairvoy" target="_blank" class="text-xs text-slate-400 hover:text-white transition px-2">
                    GitHub ↗
                </a>
            </div>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 sm:px-6">

        <!-- Collapsible Scan Configuration Drawer -->
        <div id="scanDrawer" class="hidden glass-panel rounded-3xl p-6 mb-8 border border-indigo-500/30 glow-indigo transition-all">
            <div class="flex justify-between items-center mb-4 pb-3 border-b border-slate-800">
                <div class="flex items-center gap-2">
                    <span class="text-lg">🔍</span>
                    <h2 class="text-base font-bold text-white">Start New Storage Scan</h2>
                </div>
                <button onclick="toggleScanDrawer()" class="text-slate-400 hover:text-white text-xs font-mono">✕ Close</button>
            </div>
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-5 items-end">
                <div class="lg:col-span-7">
                    <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                        Target Storage Directories <span class="text-slate-500 font-normal lowercase">(separate multiple folders with commas or newlines)</span>
                    </label>
                    <textarea id="dirInput" rows="2" placeholder="/mnt/e/Photos&#10;/mnt/e/Backups"
                           class="w-full bg-slate-950 border border-slate-800 rounded-2xl px-4 py-2.5 text-sm focus:outline-none focus:border-indigo-500 text-slate-100 font-mono transition custom-scrollbar resize-y">/mnt/e</textarea>
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
                    <button onclick="triggerScan()" id="scanBtn" class="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-2.5 px-4 rounded-xl transition shadow-lg shadow-indigo-600/30 flex items-center justify-center gap-2 text-sm">
                        <span>Launch Scan</span>
                    </button>
                </div>
            </div>
        </div>

        <!-- Global Status / Notification Ticker -->
        <div id="statusTicker" class="mb-6 flex items-center gap-3 px-4 py-2.5 rounded-xl bg-slate-900/60 border border-slate-800 text-xs font-mono">
            <div id="statusDot" class="w-2 h-2 rounded-full bg-emerald-400"></div>
            <div id="statusMessage" class="text-slate-300 truncate">Ready to optimize storage.</div>
        </div>

        <!-- Hero Storage Meter & Analytics Section -->
        <section id="heroStorageSection" class="glass-panel rounded-3xl p-6 sm:p-8 mb-8 relative overflow-hidden">
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
                <!-- Reclaimable Space Headline -->
                <div class="lg:col-span-5">
                    <div class="text-xs uppercase tracking-widest font-bold text-indigo-400 mb-1 flex items-center gap-1.5">
                        <span class="w-2 h-2 rounded-full bg-indigo-400"></span> Reclaimable Storage Space
                    </div>
                    <div class="flex items-baseline gap-3 my-2">
                        <span id="heroWastedGb" class="text-5xl sm:text-6xl font-black tracking-tight text-white">0.00</span>
                        <span class="text-2xl sm:text-3xl font-bold text-slate-400">GB</span>
                    </div>
                    <p id="heroWastedMb" class="text-xs text-slate-400 font-mono">0.0 MB recoverable across duplicates</p>

                    <div class="mt-4 flex flex-wrap gap-2 text-xs">
                        <span id="heroFileCount" class="px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300 font-mono">0 files analyzed</span>
                        <span id="heroClusterCount" class="px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300 font-mono">0 duplicate clusters</span>
                    </div>
                </div>

                <!-- CleanMyMac-Style Segmented Distribution Bar -->
                <div class="lg:col-span-7">
                    <div class="flex justify-between items-center text-xs font-mono text-slate-400 mb-2">
                        <span>Storage Distribution by Modality</span>
                        <span id="heroPercentageSummary" class="text-indigo-400 font-bold">100% Duplicates Breakdown</span>
                    </div>

                    <!-- Visual Segmented Bar -->
                    <div class="w-full h-5 rounded-xl bg-slate-950 border border-slate-800 p-0.5 flex overflow-hidden shadow-inner mb-4">
                        <div id="segPhoto" class="h-full bg-cyan-400 hover:brightness-110 transition-all rounded-l" style="width: 0%" title="Photos"></div>
                        <div id="segScreenshot" class="h-full bg-purple-500 hover:brightness-110 transition-all" style="width: 0%" title="Screenshots"></div>
                        <div id="segDocument" class="h-full bg-amber-400 hover:brightness-110 transition-all" style="width: 0%" title="Documents"></div>
                        <div id="segGraphic" class="h-full bg-pink-500 hover:brightness-110 transition-all" style="width: 0%" title="Graphics"></div>
                        <div id="segFile" class="h-full bg-slate-500 hover:brightness-110 transition-all rounded-r" style="width: 0%" title="Other Files"></div>
                    </div>

                    <!-- Category Legend Tags -->
                    <div class="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs font-mono">
                        <div class="flex items-center gap-2 text-slate-300">
                            <span class="w-2.5 h-2.5 rounded-full bg-cyan-400"></span>
                            <span>📷 Photos: <b id="legendPhoto">0 MB</b></span>
                        </div>
                        <div class="flex items-center gap-2 text-slate-300">
                            <span class="w-2.5 h-2.5 rounded-full bg-purple-500"></span>
                            <span>📱 Screens: <b id="legendScreenshot">0 MB</b></span>
                        </div>
                        <div class="flex items-center gap-2 text-slate-300">
                            <span class="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
                            <span>📄 Docs: <b id="legendDocument">0 MB</b></span>
                        </div>
                        <div class="flex items-center gap-2 text-slate-300">
                            <span class="w-2.5 h-2.5 rounded-full bg-pink-500"></span>
                            <span>🎨 Graphic: <b id="legendGraphic">0 MB</b></span>
                        </div>
                        <div class="flex items-center gap-2 text-slate-300">
                            <span class="w-2.5 h-2.5 rounded-full bg-slate-500"></span>
                            <span>📁 Files: <b id="legendFile">0 MB</b></span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- KPI Cards Row -->
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 pt-6 border-t border-slate-800/80">
                <div class="bg-slate-900/60 border border-slate-800/80 p-4 rounded-2xl">
                    <div class="text-[11px] uppercase tracking-wider text-slate-400 font-medium">Scanned Total</div>
                    <div id="kpiFiles" class="text-2xl font-black text-white mt-1">0</div>
                    <div class="text-[10px] text-slate-500 font-mono mt-0.5">Discovered files</div>
                </div>
                <div class="bg-slate-900/60 border border-slate-800/80 p-4 rounded-2xl">
                    <div class="text-[11px] uppercase tracking-wider text-slate-400 font-medium">Exact Hash Sets</div>
                    <div id="kpiExact" class="text-2xl font-black text-amber-400 mt-1">0</div>
                    <div class="text-[10px] text-slate-500 font-mono mt-0.5">100% SHA-256 matches</div>
                </div>
                <div class="bg-slate-900/60 border border-slate-800/80 p-4 rounded-2xl">
                    <div class="text-[11px] uppercase tracking-wider text-slate-400 font-medium">Vision AI Sets</div>
                    <div id="kpiVision" class="text-2xl font-black text-indigo-400 mt-1">0</div>
                    <div class="text-[10px] text-slate-500 font-mono mt-0.5">Meta DINOv2 near-dupes</div>
                </div>
                <div class="bg-slate-900/60 border border-slate-800/80 p-4 rounded-2xl">
                    <div class="text-[11px] uppercase tracking-wider text-slate-400 font-medium">Content / Tabular</div>
                    <div id="kpiContent" class="text-2xl font-black text-emerald-400 mt-1">0</div>
                    <div class="text-[10px] text-slate-500 font-mono mt-0.5">Doc & permuted row matches</div>
                </div>
            </div>
        </section>

        <!-- Studio Control Toolbar -->
        <section class="mb-6 space-y-4">
            <!-- Modality Filter Tabs -->
            <div class="flex flex-wrap items-center gap-2" id="modalityTabs">
                <button onclick="setModalityTab('ALL')" id="tab_ALL" class="modality-tab px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 text-white shadow-md shadow-indigo-600/20 transition flex items-center gap-2">
                    <span>All Clusters</span>
                    <span id="tabCount_ALL" class="bg-indigo-700/80 px-2 py-0.5 rounded-full text-[10px] font-mono">0</span>
                </button>
                <button onclick="setModalityTab('PHOTO')" id="tab_PHOTO" class="modality-tab px-4 py-2 rounded-xl text-xs font-semibold bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition flex items-center gap-2">
                    <span>📷 Photos</span>
                    <span id="tabCount_PHOTO" class="bg-slate-800 px-2 py-0.5 rounded-full text-[10px] font-mono">0</span>
                </button>
                <button onclick="setModalityTab('SCREENSHOT')" id="tab_SCREENSHOT" class="modality-tab px-4 py-2 rounded-xl text-xs font-semibold bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition flex items-center gap-2">
                    <span>📱 Screenshots</span>
                    <span id="tabCount_SCREENSHOT" class="bg-slate-800 px-2 py-0.5 rounded-full text-[10px] font-mono">0</span>
                </button>
                <button onclick="setModalityTab('DOCUMENT')" id="tab_DOCUMENT" class="modality-tab px-4 py-2 rounded-xl text-xs font-semibold bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition flex items-center gap-2">
                    <span>📄 Documents</span>
                    <span id="tabCount_DOCUMENT" class="bg-slate-800 px-2 py-0.5 rounded-full text-[10px] font-mono">0</span>
                </button>
                <button onclick="setModalityTab('GRAPHIC')" id="tab_GRAPHIC" class="modality-tab px-4 py-2 rounded-xl text-xs font-semibold bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition flex items-center gap-2">
                    <span>🎨 Graphics</span>
                    <span id="tabCount_GRAPHIC" class="bg-slate-800 px-2 py-0.5 rounded-full text-[10px] font-mono">0</span>
                </button>
                <button onclick="setModalityTab('FILE')" id="tab_FILE" class="modality-tab px-4 py-2 rounded-xl text-xs font-semibold bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition flex items-center gap-2">
                    <span>📁 Other Files</span>
                    <span id="tabCount_FILE" class="bg-slate-800 px-2 py-0.5 rounded-full text-[10px] font-mono">0</span>
                </button>
            </div>

            <!-- Filter, Sort & Search Actions Bar -->
            <div class="glass-panel rounded-2xl p-4 flex flex-col md:flex-row justify-between items-stretch md:items-center gap-4">
                <!-- Search Input -->
                <div class="relative flex-1">
                    <span class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400 text-xs">🔍</span>
                    <input type="text" id="searchInput" oninput="onSearchInput(this.value)" placeholder="Search files by name or folder path..."
                           class="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-8 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono transition">
                    <button id="clearSearchBtn" onclick="clearSearch()" class="hidden absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-white text-xs">✕</button>
                </div>

                <!-- Secondary Filters -->
                <div class="flex flex-wrap items-center gap-3">
                    <!-- Match Type Filter -->
                    <div class="flex items-center bg-slate-950 border border-slate-800 rounded-xl px-2.5 py-1.5">
                        <span class="text-[11px] font-mono text-slate-400 mr-2">Match:</span>
                        <select id="matchTypeSelect" onchange="onMatchTypeChange(this.value)" class="bg-transparent text-xs text-slate-200 focus:outline-none font-mono cursor-pointer">
                            <option value="ALL" class="bg-slate-900">All Matches</option>
                            <option value="EXACT_HASH" class="bg-slate-900">Exact Hash (100%)</option>
                            <option value="VISUAL_AI_NEAR_DUPLICATE" class="bg-slate-900">Vision AI (DINOv2)</option>
                            <option value="CONTENT_NEAR_DUPLICATE" class="bg-slate-900">Content / Tabular</option>
                        </select>
                    </div>

                    <!-- Sort Order -->
                    <div class="flex items-center bg-slate-950 border border-slate-800 rounded-xl px-2.5 py-1.5">
                        <span class="text-[11px] font-mono text-slate-400 mr-2">Sort:</span>
                        <select id="sortOrderSelect" onchange="onSortOrderChange(this.value)" class="bg-transparent text-xs text-slate-200 focus:outline-none font-mono cursor-pointer">
                            <option value="SIZE_DESC" class="bg-slate-900">Largest Wasted Space</option>
                            <option value="DUPES_DESC" class="bg-slate-900">Most Duplicates</option>
                            <option value="SIMILARITY_DESC" class="bg-slate-900">Highest Similarity</option>
                            <option value="ID_ASC" class="bg-slate-900">Cluster ID (Default)</option>
                        </select>
                    </div>

                    <!-- Selection Rules -->
                    <div class="flex items-center bg-slate-950 border border-slate-800 rounded-xl px-2.5 py-1.5">
                        <span class="text-[11px] font-mono text-slate-400 mr-2">Select:</span>
                        <select id="selectionRuleSelect" onchange="applySelectionRule(this.value)" class="bg-transparent text-xs text-indigo-400 focus:outline-none font-mono cursor-pointer">
                            <option value="AUTO" class="bg-slate-900 text-indigo-300">Auto-Select Duplicates</option>
                            <option value="ALL" class="bg-slate-900 text-slate-200">Select All</option>
                            <option value="NONE" class="bg-slate-900 text-slate-200">Deselect All</option>
                        </select>
                    </div>
                </div>
            </div>
        </section>

        <!-- Pagination Header Info -->
        <div class="flex flex-col sm:flex-row justify-between items-center text-xs font-mono text-slate-400 mb-4 px-1 gap-2">
            <div id="paginationSummary">Showing clusters 1–25 of 0</div>
            <div class="flex items-center gap-3">
                <span>Clusters per page:</span>
                <select id="perPageSelect" onchange="onPerPageChange(parseInt(this.value))" class="bg-slate-900 border border-slate-800 rounded-lg px-2 py-1 text-slate-200 text-xs focus:outline-none font-mono">
                    <option value="25">25</option>
                    <option value="50">50</option>
                    <option value="100">100</option>
                </select>
            </div>
        </div>

        <!-- Dynamic Cluster Gallery -->
        <div id="clustersGallery" class="space-y-6 mb-8">
            <div class="text-center py-24 glass-panel rounded-3xl text-slate-500 font-mono">
                <span class="text-3xl block mb-2">👁️</span>
                No scan results loaded yet. Select a past run or launch a scan.
            </div>
        </div>

        <!-- Pagination Footer Controls -->
        <div id="paginationControls" class="flex justify-center items-center gap-3 my-8 text-xs font-mono">
            <button onclick="changePage(currentPage - 1)" id="prevPageBtn" class="px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition">
                ← Previous
            </button>
            <span id="pageIndicator" class="px-4 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-200">
                Page 1 of 1
            </span>
            <button onclick="changePage(currentPage + 1)" id="nextPageBtn" class="px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition">
                Next →
            </button>
        </div>

    </main>

    <!-- CleanMyMac-Style Sticky Action Dock (Bottom Bar) -->
    <div id="actionDock" class="fixed bottom-4 left-1/2 transform -translate-x-1/2 w-11/12 max-w-6xl z-50 glass-panel rounded-2xl p-4 shadow-2xl flex flex-col sm:flex-row justify-between items-center gap-4 glow-indigo border border-indigo-500/30">
        <div class="flex items-center gap-3">
            <div class="w-3 h-3 rounded-full bg-emerald-400 animate-pulse"></div>
            <div>
                <div class="text-xs font-bold text-white flex items-center gap-2">
                    <span>Reclaimable:</span>
                    <span id="dockSelectedSpace" class="text-emerald-400 text-sm font-extrabold font-mono">0.0 MB</span>
                </div>
                <div class="text-[11px] text-slate-400 font-mono" id="dockSelectedCount">
                    0 duplicate files staged for quarantine
                </div>
            </div>
        </div>

        <div class="flex items-center gap-2.5">
            <a id="downloadCsvBtn" href="/api/reports/csv" download class="bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 px-3 py-2 rounded-xl text-xs font-mono transition flex items-center gap-1">
                <span>📄</span> CSV
            </a>
            <a id="downloadScriptBtn" href="/api/reports/script" download class="bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 px-3 py-2 rounded-xl text-xs font-mono transition flex items-center gap-1">
                <span>📜</span> Script
            </a>
            <button onclick="openQuarantineModal()" id="dockQuarantineBtn" class="bg-rose-600 hover:bg-rose-500 text-white font-bold px-5 py-2.5 rounded-xl text-xs shadow-lg shadow-rose-600/30 transition flex items-center gap-2">
                <span>⚡</span> <span>Move Duplicates to Quarantine</span>
            </button>
        </div>
    </div>

    <!-- Side-by-Side Comparison Lightbox Modal -->
    <div id="comparisonModal" class="hidden fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4">
        <div class="bg-slate-900 border border-slate-800 w-full max-w-5xl rounded-3xl p-6 shadow-2xl flex flex-col max-h-[92vh] overflow-hidden">
            <!-- Modal Header -->
            <div class="flex justify-between items-center pb-4 border-b border-slate-800 mb-4">
                <div class="flex items-center gap-3">
                    <span class="text-indigo-400 text-lg">🔍</span>
                    <div>
                        <h3 class="text-base font-bold text-white" id="modalClusterTitle">Side-by-Side Comparison</h3>
                        <p class="text-xs text-slate-400 font-mono" id="modalClusterSubtitle">Inspect differences between Keeper and Duplicate</p>
                    </div>
                </div>
                <button onclick="closeComparisonModal()" class="text-slate-400 hover:text-white text-lg font-mono px-3 py-1 rounded-xl hover:bg-slate-800 transition">✕</button>
            </div>

            <!-- Comparison Body -->
            <div class="flex-1 overflow-y-auto custom-scrollbar grid grid-cols-1 md:grid-cols-2 gap-6 p-2">
                <!-- Left: Keeper File -->
                <div class="bg-slate-950 border-2 border-emerald-500/60 rounded-2xl p-4 flex flex-col items-center">
                    <div class="w-full flex justify-between items-center mb-3">
                        <span class="bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[11px] px-2.5 py-0.5 rounded-full font-bold">★ CURRENT KEEPER</span>
                        <span id="modalKeeperCategory" class="text-[10px] font-mono text-slate-400">PHOTO</span>
                    </div>
                    <div id="modalKeeperPreview" class="w-full h-64 bg-slate-900 rounded-xl flex items-center justify-center overflow-hidden mb-4 border border-slate-800">
                        <!-- Preview loaded dynamically -->
                    </div>
                    <div class="w-full text-xs font-mono space-y-1.5 text-slate-300">
                        <div class="text-white font-bold truncate" id="modalKeeperName">filename.jpg</div>
                        <div class="text-[10px] text-slate-500 truncate" id="modalKeeperPath">/path/to/file</div>
                        <div class="flex justify-between pt-2 border-t border-slate-800 text-[11px]">
                            <span class="text-slate-500">Resolution:</span>
                            <span id="modalKeeperDim" class="font-bold text-white">-</span>
                        </div>
                        <div class="flex justify-between text-[11px]">
                            <span class="text-slate-500">File Size:</span>
                            <span id="modalKeeperSize" class="font-bold text-emerald-400">-</span>
                        </div>
                    </div>
                </div>

                <!-- Right: Duplicate File -->
                <div class="bg-slate-950 border border-slate-800 rounded-2xl p-4 flex flex-col items-center">
                    <div class="w-full flex justify-between items-center mb-3">
                        <span class="bg-rose-500/20 text-rose-300 border border-rose-500/30 text-[11px] px-2.5 py-0.5 rounded-full font-bold">⌧ CANDIDATE DUPLICATE</span>
                        <span id="modalDupeSimilarity" class="text-[10px] font-mono text-indigo-400">98% Match</span>
                    </div>
                    <div id="modalDupePreview" class="w-full h-64 bg-slate-900 rounded-xl flex items-center justify-center overflow-hidden mb-4 border border-slate-800">
                        <!-- Preview loaded dynamically -->
                    </div>
                    <div class="w-full text-xs font-mono space-y-1.5 text-slate-300">
                        <div class="text-white font-bold truncate" id="modalDupeName">filename_copy.jpg</div>
                        <div class="text-[10px] text-slate-500 truncate" id="modalDupePath">/path/to/copy</div>
                        <div class="flex justify-between pt-2 border-t border-slate-800 text-[11px]">
                            <span class="text-slate-500">Resolution:</span>
                            <span id="modalDupeDim" class="font-bold text-white">-</span>
                        </div>
                        <div class="flex justify-between text-[11px]">
                            <span class="text-slate-500">File Size:</span>
                            <span id="modalDupeSize" class="font-bold text-rose-400">-</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Modal Footer Controls -->
            <div class="pt-4 mt-4 border-t border-slate-800 flex justify-between items-center">
                <div id="modalDiffNotice" class="text-xs font-mono text-slate-400">
                    Both files evaluated identically in quality scoring.
                </div>
                <div class="flex gap-3">
                    <button id="modalSwapKeeperBtn" onclick="swapKeeperInModal()" class="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-4 py-2 rounded-xl transition shadow">
                        ★ Make This The Keeper Instead
                    </button>
                    <button onclick="closeComparisonModal()" class="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs px-4 py-2 rounded-xl transition">
                        Done
                    </button>
                </div>
            </div>
        </div>
    </div>

    <!-- Quarantine Confirmation Modal -->
    <div id="quarantineModal" class="hidden fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4">
        <div class="bg-slate-900 border border-slate-800 w-full max-w-lg rounded-3xl p-6 shadow-2xl">
            <div class="flex items-center gap-3 mb-4 pb-3 border-b border-slate-800">
                <span class="text-2xl">🛡️</span>
                <div>
                    <h3 class="text-base font-bold text-white">Safe Quarantine Confirmation</h3>
                    <p class="text-xs text-slate-400 font-mono">Zero-Clobber Safety & Reversible Tracking</p>
                </div>
            </div>

            <p class="text-xs text-slate-300 leading-relaxed mb-4">
                Selected duplicate files will be safely moved to <code class="bg-slate-950 px-2 py-0.5 rounded text-indigo-400 font-mono">_duplicate_quarantine</code>, preserving original folder structures.
            </p>

            <ul class="text-xs text-slate-400 space-y-2 mb-6 font-mono bg-slate-950/60 p-4 rounded-xl border border-slate-800/80">
                <li class="flex items-center gap-2 text-emerald-400">
                    <span>✓</span> <span>Zero deletions (files only moved)</span>
                </li>
                <li class="flex items-center gap-2 text-emerald-400">
                    <span>✓</span> <span>No overwrites (<code class="text-white">mv -n --</code> guarded)</span>
                </li>
                <li class="flex items-center gap-2 text-emerald-400">
                    <span>✓</span> <span>Reversible manifest created for 1-click restore</span>
                </li>
            </ul>

            <div class="flex justify-end gap-3">
                <button onclick="closeQuarantineModal()" class="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs px-4 py-2.5 rounded-xl transition">
                    Cancel
                </button>
                <button onclick="executeConfirmedQuarantine()" id="confirmQuarantineBtn" class="bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs px-5 py-2.5 rounded-xl shadow-lg shadow-rose-600/30 transition">
                    Confirm & Move Duplicates
                </button>
            </div>
        </div>
    </div>

    <!-- Frontend Studio Logic -->
    <script>
        // State Management
        let currentSummary = null;
        let allClusters = [];       // Array of grouped cluster objects
        let filteredClusters = [];  // Filtered & searched clusters
        let activeModality = 'ALL';
        let activeMatchType = 'ALL';
        let activeSortOrder = 'SIZE_DESC';
        let searchQuery = '';
        let currentPage = 1;
        let perPage = 25;
        let pollTimer = null;

        // Selective quarantine tracking (set of paths excluded by user)
        let excludedPaths = new Set();

        // Comparison modal active targets
        let modalActiveCluster = null;
        let modalActiveDupe = null;

        // Initialization
        window.addEventListener('DOMContentLoaded', async () => {{
            await loadPastRunsList();
            try {{
                const res = await fetch('/api/status');
                const state = await res.json();
                if (state.status === "completed" && state.summary) {{
                    loadSummaryState(state.summary, state.message);
                }} else if (state.status === "running") {{
                    pollTimer = setInterval(pollScanStatus, 1000);
                    updateStatus("running", state.message);
                }} else {{
                    const dropdown = document.getElementById('runsDropdown');
                    if (dropdown && dropdown.value && dropdown.value !== "__custom__") {{
                        await onRunSelected(dropdown.value);
                    }}
                }}
            }} catch (e) {{
                console.error("Initial status check error:", e);
            }}
        }});

        function toggleScanDrawer() {{
            const drawer = document.getElementById('scanDrawer');
            drawer.classList.toggle('hidden');
        }}

        function updateStatus(type, msg) {{
            const dot = document.getElementById('statusDot');
            const text = document.getElementById('statusMessage');
            text.innerText = msg;
            if (type === "running") {{
                dot.className = "w-2 h-2 rounded-full bg-indigo-500 animate-ping";
            }} else if (type === "completed") {{
                dot.className = "w-2 h-2 rounded-full bg-emerald-400";
            }} else if (type === "failed") {{
                dot.className = "w-2 h-2 rounded-full bg-rose-500";
            }} else {{
                dot.className = "w-2 h-2 rounded-full bg-slate-500";
            }}
        }}

        async function loadPastRunsList(selectedRunId = null) {{
            const dropdown = document.getElementById('runsDropdown');
            try {{
                const res = await fetch('/api/runs?limit=30');
                if (!res.ok) return;
                const runs = await res.json();
                dropdown.innerHTML = '';
                if (runs.length === 0) {{
                    dropdown.innerHTML = '<option value="">No past runs found</option>';
                }} else {{
                    for (const r of runs) {{
                        const opt = document.createElement('option');
                        opt.value = r.run_id;
                        opt.className = "bg-slate-900 text-slate-100";
                        const target = r.scanned_paths && r.scanned_paths.length > 0 ? r.scanned_paths[0] : "Target";
                        const shortTarget = target.length > 20 ? target.slice(0, 18) + ".." : target;
                        const dateStr = r.timestamp ? r.timestamp.slice(0, 10) : "";
                        opt.innerText = `${{shortTarget}} • ${{r.wasted_gb.toFixed(2)}} GB (${{r.total_duplicate_groups.toLocaleString()}} dupes) [${{dateStr}}]`;
                        dropdown.appendChild(opt);
                    }}
                }}
                const customOpt = document.createElement('option');
                customOpt.value = "__custom__";
                customOpt.className = "bg-slate-900 text-indigo-400 font-bold";
                customOpt.innerText = "➕ Load custom report path...";
                dropdown.appendChild(customOpt);

                if (selectedRunId) {{
                    dropdown.value = selectedRunId;
                }}
            }} catch (e) {{
                console.error("Failed to load runs list:", e);
            }}
        }}

        async function onRunSelected(val) {{
            if (!val) return;
            if (val === "__custom__") {{
                const path = prompt("Enter full absolute path to clairvoy_summary.json:");
                if (!path) {{
                    await loadPastRunsList();
                    return;
                }}
                await loadRunReport({{ path: path.trim() }});
            }} else {{
                await loadRunReport({{ run_id: val }});
            }}
        }}

        async function loadRunReport(payload) {{
            updateStatus("running", "Loading scan report...");
            try {{
                const res = await fetch('/api/runs/load', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(payload)
                }});
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || "Failed to load run");
                loadSummaryState(data.summary, `Loaded run: ${{data.summary.scanned_paths ? data.summary.scanned_paths[0] : ""}} (${{data.summary.total_duplicate_groups.toLocaleString()}} groups, ${{data.summary.wasted_gb}} GB)`);
                await loadPastRunsList(payload.run_id);
            }} catch (e) {{
                updateStatus("failed", "Error loading report: " + e.message);
            }}
        }}

        function loadSummaryState(summary, msg) {{
            currentSummary = summary;
            excludedPaths.clear();
            updateStatus("completed", msg || "Scan summary loaded.");

            // Organize items into structured cluster objects
            allClusters = groupRecordsIntoClusters(summary.groups || []);

            renderHeroStorageMeter(summary);
            renderModalityTabCounts(summary);
            applyFiltersAndSort();
            updateDockMetrics();
        }}

        function groupRecordsIntoClusters(records) {{
            const clusterMap = {{}};
            for (const r of records) {{
                const gid = r.group_id;
                if (!clusterMap[gid]) {{
                    clusterMap[gid] = {{
                        group_id: gid,
                        match_type: r.match_type,
                        items: [],
                        keeper: null,
                        duplicates: [],
                        totalWastedBytes: 0,
                        category: r.category || 'FILE'
                    }};
                }}
                clusterMap[gid].items.push(r);
                if (r.action === 'KEEP') {{
                    clusterMap[gid].keeper = r;
                }} else {{
                    clusterMap[gid].duplicates.push(r);
                    clusterMap[gid].totalWastedBytes += Math.round((r.size_mb || 0) * 1024 * 1024);
                }}
                if (r.category && r.category !== 'FILE') {{
                    clusterMap[gid].category = r.category;
                }}
            }}
            return Object.values(clusterMap);
        }}

        function renderHeroStorageMeter(summary) {{
            document.getElementById('heroWastedGb').innerText = (summary.wasted_gb || 0).toFixed(3);
            document.getElementById('heroWastedMb').innerText = `${{(summary.wasted_mb || 0).toLocaleString()}} MB recoverable storage`;
            document.getElementById('heroFileCount').innerText = `${{(summary.total_files_scanned || 0).toLocaleString()}} files analyzed`;
            document.getElementById('heroClusterCount').innerText = `${{(summary.total_duplicate_groups || 0).toLocaleString()}} duplicate clusters`;

            document.getElementById('kpiFiles').innerText = (summary.total_files_scanned || 0).toLocaleString();
            document.getElementById('kpiExact').innerText = (summary.exact_duplicate_groups || 0).toLocaleString();
            document.getElementById('kpiVision').innerText = (summary.visual_ai_groups || 0).toLocaleString();
            document.getElementById('kpiContent').innerText = (summary.content_duplicate_groups || 0).toLocaleString();

            // Calculate category breakdown
            const cb = summary.category_breakdown || {{}};
            const totalWasted = summary.wasted_bytes || 1;

            // Approximate proportion by duplicate file count if byte size by category is not explicitly separated
            const totalDupes = Math.max(1, (summary.groups ? summary.groups.filter(g => g.action === 'DUPLICATE').length : 1));
            const pPhoto = ((cb.PHOTO || 0) / totalDupes) * 100;
            const pScreens = ((cb.SCREENSHOT || 0) / totalDupes) * 100;
            const pDoc = ((cb.DOCUMENT || 0) / totalDupes) * 100;
            const pGraphic = ((cb.GRAPHIC || 0) / totalDupes) * 100;
            const pFile = Math.max(0, 100 - (pPhoto + pScreens + pDoc + pGraphic));

            document.getElementById('segPhoto').style.width = pPhoto + '%';
            document.getElementById('segScreenshot').style.width = pScreens + '%';
            document.getElementById('segDocument').style.width = pDoc + '%';
            document.getElementById('segGraphic').style.width = pGraphic + '%';
            document.getElementById('segFile').style.width = pFile + '%';

            document.getElementById('legendPhoto').innerText = `${{cb.PHOTO || 0}} files`;
            document.getElementById('legendScreenshot').innerText = `${{cb.SCREENSHOT || 0}} files`;
            document.getElementById('legendDocument').innerText = `${{cb.DOCUMENT || 0}} files`;
            document.getElementById('legendGraphic').innerText = `${{cb.GRAPHIC || 0}} files`;
            document.getElementById('legendFile').innerText = `${{cb.FILE || 0}} files`;
        }}

        function renderModalityTabCounts(summary) {{
            const cb = summary.category_breakdown || {{}};
            const total = summary.total_duplicate_groups || allClusters.length;
            document.getElementById('tabCount_ALL').innerText = total.toLocaleString();
            document.getElementById('tabCount_PHOTO').innerText = (cb.PHOTO || 0).toLocaleString();
            document.getElementById('tabCount_SCREENSHOT').innerText = (cb.SCREENSHOT || 0).toLocaleString();
            document.getElementById('tabCount_DOCUMENT').innerText = (cb.DOCUMENT || 0).toLocaleString();
            document.getElementById('tabCount_GRAPHIC').innerText = (cb.GRAPHIC || 0).toLocaleString();
            document.getElementById('tabCount_FILE').innerText = (cb.FILE || 0).toLocaleString();
        }}

        function setModalityTab(tab) {{
            activeModality = tab;
            document.querySelectorAll('.modality-tab').forEach(el => {{
                el.className = "modality-tab px-4 py-2 rounded-xl text-xs font-semibold bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition flex items-center gap-2";
            }});
            const activeBtn = document.getElementById('tab_' + tab);
            if (activeBtn) {{
                activeBtn.className = "modality-tab px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 text-white shadow-md shadow-indigo-600/20 transition flex items-center gap-2";
            }}
            currentPage = 1;
            applyFiltersAndSort();
        }}

        function onMatchTypeChange(val) {{
            activeMatchType = val;
            currentPage = 1;
            applyFiltersAndSort();
        }}

        function onSortOrderChange(val) {{
            activeSortOrder = val;
            currentPage = 1;
            applyFiltersAndSort();
        }}

        function onSearchInput(query) {{
            searchQuery = query.trim().toLowerCase();
            document.getElementById('clearSearchBtn').classList.toggle('hidden', searchQuery === '');
            currentPage = 1;
            applyFiltersAndSort();
        }}

        function clearSearch() {{
            document.getElementById('searchInput').value = '';
            onSearchInput('');
        }}

        function onPerPageChange(val) {{
            perPage = val;
            currentPage = 1;
            renderCurrentPage();
        }}

        function applyFiltersAndSort() {{
            filteredClusters = allClusters.filter(c => {{
                // Modality filter
                if (activeModality !== 'ALL') {{
                    const matchesCategory = c.items.some(i => i.category === activeModality);
                    if (!matchesCategory) return false;
                }}
                // Match type filter
                if (activeMatchType !== 'ALL') {{
                    if (c.match_type !== activeMatchType) return false;
                }}
                // Search query filter
                if (searchQuery) {{
                    const matchesSearch = c.items.some(i => i.path.toLowerCase().includes(searchQuery));
                    if (!matchesSearch) return false;
                }}
                return true;
            }});

            // Sorting
            filteredClusters.sort((a, b) => {{
                if (activeSortOrder === 'SIZE_DESC') {{
                    return b.totalWastedBytes - a.totalWastedBytes;
                }} else if (activeSortOrder === 'DUPES_DESC') {{
                    return b.duplicates.length - a.duplicates.length;
                }} else if (activeSortOrder === 'SIMILARITY_DESC') {{
                    const simA = a.duplicates.length > 0 ? (a.duplicates[0].similarity_score || 0) : 0;
                    const simB = b.duplicates.length > 0 ? (b.duplicates[0].similarity_score || 0) : 0;
                    return simB - simA;
                }} else {{
                    return a.group_id - b.group_id;
                }}
            }});

            renderCurrentPage();
        }}

        function renderCurrentPage() {{
            const total = filteredClusters.length;
            const totalPages = Math.max(1, Math.ceil(total / perPage));
            if (currentPage > totalPages) currentPage = totalPages;
            if (currentPage < 1) currentPage = 1;

            const startIdx = (currentPage - 1) * perPage;
            const endIdx = Math.min(startIdx + perPage, total);
            const pageClusters = filteredClusters.slice(startIdx, endIdx);

            document.getElementById('paginationSummary').innerText =
                total > 0 ? `Showing clusters ${{startIdx + 1}}–${{endIdx}} of ${{total.toLocaleString()}}` : 'No matching clusters';
            document.getElementById('pageIndicator').innerText = `Page ${{currentPage}} of ${{totalPages}}`;
            document.getElementById('prevPageBtn').disabled = (currentPage <= 1);
            document.getElementById('nextPageBtn').disabled = (currentPage >= totalPages);

            const gallery = document.getElementById('clustersGallery');
            if (pageClusters.length === 0) {{
                gallery.innerHTML = `
                    <div class="text-center py-24 glass-panel rounded-3xl text-slate-500 font-mono">
                        <span class="text-3xl block mb-2">🔍</span>
                        No duplicate clusters match the active search and filter criteria.
                    </div>
                `;
                return;
            }}

            gallery.innerHTML = '';
            for (const c of pageClusters) {{
                gallery.appendChild(createClusterCard(c));
            }}
        }}

        function changePage(newPage) {{
            currentPage = newPage;
            renderCurrentPage();
            window.scrollTo({{ top: document.getElementById('clustersGallery').offsetTop - 90, behavior: 'smooth' }});
        }}

        function createClusterCard(cluster) {{
            const card = document.createElement('div');
            card.className = "glass-panel rounded-3xl p-5 sm:p-6 shadow-xl border border-slate-800 transition-all hover:border-slate-700/80";

            // Match type badge
            let badgeClass = "bg-amber-500/20 text-amber-400 border border-amber-500/30";
            let badgeText = "Exact Hash (100%)";
            if (cluster.match_type === 'VISUAL_AI_NEAR_DUPLICATE') {{
                badgeClass = "bg-indigo-500/20 text-indigo-400 border border-indigo-500/30";
                const score = cluster.duplicates[0] && cluster.duplicates[0].similarity_score ? Math.round(cluster.duplicates[0].similarity_score * 100) : 95;
                badgeText = `Vision AI Match (${{score}}%)`;
            }} else if (cluster.match_type === 'CONTENT_NEAR_DUPLICATE') {{
                badgeClass = "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30";
                badgeText = "Content / Tabular Match";
            }}

            const wastedMb = (cluster.totalWastedBytes / (1024 * 1024)).toFixed(2);

            card.innerHTML = `
                <div class="flex flex-wrap justify-between items-center pb-4 mb-5 border-b border-slate-800/80 gap-3">
                    <div class="flex items-center gap-3">
                        <span class="font-extrabold text-white text-base">Cluster #${{cluster.group_id}}</span>
                        <span class="text-xs px-2.5 py-1 rounded-full font-medium font-mono ${{badgeClass}}">${{badgeText}}</span>
                        <span class="text-xs px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 font-mono">Wasted: ${{wastedMb}} MB</span>
                        <span class="text-xs text-slate-500 font-mono">${{cluster.items.length}} items</span>
                    </div>
                    <div>
                        <button onclick="openComparisonLightbox(${{cluster.group_id}})" class="text-xs bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/40 text-indigo-300 px-3.5 py-1.5 rounded-xl font-medium transition flex items-center gap-1.5 shadow-sm">
                            <span>🔍</span> <span>Side-by-Side Diff</span>
                        </button>
                    </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    ${{cluster.items.map(item => createItemCardHtml(cluster.group_id, item)).join('')}}
                </div>
            `;
            return card;
        }}

        function isImageFile(path) {{
            const exts = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.heic', '.psd'];
            return exts.some(e => path.toLowerCase().endsWith(e));
        }}

        function createItemCardHtml(groupId, item) {{
            const isKeeper = (item.action === 'KEEP');
            const isExcluded = excludedPaths.has(item.path);

            const borderClass = isKeeper ?
                "border-2 border-emerald-500/70 bg-emerald-950/15 glow-emerald" :
                (isExcluded ? "border border-slate-800 opacity-60 bg-slate-900/40" : "border border-slate-800 bg-slate-900/80 hover:border-slate-700");

            const fname = item.path.split('/').pop();
            const parentDir = item.path.substring(0, item.path.lastIndexOf('/'));
            const sizeStr = `${{(item.size_mb || 0).toFixed(2)}} MB`;
            const dimStr = item.dimensions ? `${{item.dimensions[0]}}x${{item.dimensions[1]}}` : "";

            return `
                <div class="rounded-2xl p-3.5 flex flex-col justify-between transition-all ${{borderClass}}">
                    <div>
                        <!-- Header Status Badge -->
                        <div class="flex justify-between items-center mb-2.5">
                            ${{isKeeper ? `
                                <span class="text-[11px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 px-2 py-0.5 rounded-full flex items-center gap-1">
                                    <span>★</span> KEEPER (Best Quality)
                                </span>
                            ` : `
                                <label class="flex items-center gap-2 cursor-pointer">
                                    <input type="checkbox" onchange="toggleItemQuarantine('${{encodeURIComponent(item.path)}}', this.checked)" ${{!isExcluded ? 'checked' : ''}}
                                           class="w-3.5 h-3.5 rounded accent-rose-500 cursor-pointer">
                                    <span class="text-[11px] font-semibold text-rose-400 bg-rose-500/10 border border-rose-500/30 px-2 py-0.5 rounded-full">
                                        ⌧ DUPLICATE
                                    </span>
                                </label>
                            `}}
                            <span class="text-[10px] font-mono text-slate-500 uppercase">${{item.category || 'FILE'}}</span>
                        </div>

                        <!-- Media Preview & Meta Details -->
                        <div class="flex gap-3 items-center mb-3">
                            <div class="w-16 h-16 rounded-xl bg-slate-950 flex items-center justify-center overflow-hidden flex-shrink-0 border border-slate-800">
                                ${{isImageFile(item.path) ? `
                                    <img src="/api/thumbnail?path=${{encodeURIComponent(item.path)}}" class="w-full h-full object-cover" loading="lazy" alt="preview"
                                         onerror="this.parentElement.innerHTML='<span class=\\'text-xs text-slate-600\\'>IMG</span>'">
                                ` : `
                                    <span class="text-xs font-mono text-slate-500 uppercase">${{fname.split('.').pop() || 'FILE'}}</span>
                                `}}
                            </div>
                            <div class="min-w-0 flex-1 text-xs">
                                <div class="font-bold text-white truncate" title="${{fname}}">${{fname}}</div>
                                <div class="text-[10px] text-slate-500 font-mono truncate" title="${{parentDir}}">${{parentDir}}</div>
                                <div class="flex items-center gap-2 text-[11px] text-slate-400 font-mono mt-1">
                                    <span class="font-bold text-slate-200">${{sizeStr}}</span>
                                    ${{dimStr ? `<span class="text-slate-500">•</span> <span>${{dimStr}}</span>` : ''}}
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Card Footer Actions -->
                    <div class="pt-2 border-t border-slate-800/80 flex justify-between items-center text-xs">
                        ${{isKeeper ? `
                            <span class="text-[11px] text-emerald-400/80 font-mono flex items-center gap-1">
                                <span>✓</span> Preserved on disk
                            </span>
                        ` : `
                            <button onclick="setKeeperOverride(${{groupId}}, '${{encodeURIComponent(item.path)}}')"
                                    class="text-[11px] text-indigo-400 hover:text-indigo-300 font-semibold flex items-center gap-1 hover:underline">
                                <span>★</span> Make Keeper
                            </button>
                            <span class="text-[10px] font-mono text-slate-500">${{item.similarity || '100%'}}</span>
                        `}}
                    </div>
                </div>
            `;
        }}

        async function setKeeperOverride(groupId, encodedPath) {{
            const path = decodeURIComponent(encodedPath);
            try {{
                const res = await fetch('/api/clusters/override-keeper', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ group_id: groupId, new_keeper_path: path }})
                }});
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || "Override failed");

                // Update in memory
                for (const item of currentSummary.groups) {{
                    if (item.group_id === groupId) {{
                        item.action = (item.path === path) ? 'KEEP' : 'DUPLICATE';
                    }}
                }}
                allClusters = groupRecordsIntoClusters(currentSummary.groups);
                applyFiltersAndSort();
                updateDockMetrics();
            }} catch (e) {{
                alert("Error setting keeper: " + e.message);
            }}
        }}

        function toggleItemQuarantine(encodedPath, isChecked) {{
            const path = decodeURIComponent(encodedPath);
            if (isChecked) {{
                excludedPaths.delete(path);
            }} else {{
                excludedPaths.add(path);
            }}
            applyFiltersAndSort();
            updateDockMetrics();
        }}

        function applySelectionRule(rule) {{
            if (!currentSummary) return;
            if (rule === 'NONE') {{
                for (const item of currentSummary.groups) {{
                    if (item.action === 'DUPLICATE') excludedPaths.add(item.path);
                }}
            }} else if (rule === 'ALL' || rule === 'AUTO') {{
                excludedPaths.clear();
            }}
            applyFiltersAndSort();
            updateDockMetrics();
        }}

        function updateDockMetrics() {{
            if (!currentSummary) return;
            let stagedBytes = 0;
            let stagedCount = 0;

            for (const item of currentSummary.groups) {{
                if (item.action === 'DUPLICATE' && !excludedPaths.has(item.path)) {{
                    stagedCount++;
                    stagedBytes += Math.round((item.size_mb || 0) * 1024 * 1024);
                }}
            }}

            const mb = (stagedBytes / (1024 * 1024)).toFixed(1);
            const gb = (stagedBytes / (1024 * 1024 * 1024)).toFixed(3);
            document.getElementById('dockSelectedSpace').innerText = `${{gb}} GB (${{mb}} MB)`;
            document.getElementById('dockSelectedCount').innerText = `${{stagedCount.toLocaleString()}} duplicate files staged for quarantine`;
        }}

        // Side-by-Side Comparison Lightbox Logic
        function openComparisonLightbox(groupId) {{
            const cluster = allClusters.find(c => c.group_id === groupId);
            if (!cluster || !cluster.keeper || cluster.duplicates.length === 0) return;

            modalActiveCluster = cluster;
            modalActiveDupe = cluster.duplicates[0];

            document.getElementById('modalClusterTitle').innerText = `Cluster #${{cluster.group_id}} Side-by-Side Diff`;
            document.getElementById('modalClusterSubtitle').innerText = `${{cluster.items.length}} candidate files matching with ${{cluster.match_type}}`;

            // Populate Keeper
            const keeper = cluster.keeper;
            document.getElementById('modalKeeperName').innerText = keeper.path.split('/').pop();
            document.getElementById('modalKeeperPath').innerText = keeper.path;
            document.getElementById('modalKeeperCategory').innerText = keeper.category || 'FILE';
            document.getElementById('modalKeeperDim').innerText = keeper.dimensions ? `${{keeper.dimensions[0]}}x${{keeper.dimensions[1]}}` : 'N/A';
            document.getElementById('modalKeeperSize').innerText = `${{(keeper.size_mb || 0).toFixed(2)}} MB`;

            const keeperPreview = document.getElementById('modalKeeperPreview');
            if (isImageFile(keeper.path)) {{
                keeperPreview.innerHTML = `<img src="/api/thumbnail?path=${{encodeURIComponent(keeper.path)}}" class="w-full h-full object-contain" alt="keeper">`;
            }} else {{
                keeperPreview.innerHTML = `<span class="text-xs font-mono text-slate-500 uppercase">${{keeper.path.split('.').pop()}} DOCUMENT</span>`;
            }}

            // Populate Duplicate
            const dupe = modalActiveDupe;
            document.getElementById('modalDupeName').innerText = dupe.path.split('/').pop();
            document.getElementById('modalDupePath').innerText = dupe.path;
            document.getElementById('modalDupeSimilarity').innerText = dupe.similarity || '100% Match';
            document.getElementById('modalDupeDim').innerText = dupe.dimensions ? `${{dupe.dimensions[0]}}x${{dupe.dimensions[1]}}` : 'N/A';
            document.getElementById('modalDupeSize').innerText = `${{(dupe.size_mb || 0).toFixed(2)}} MB`;

            const dupePreview = document.getElementById('modalDupePreview');
            if (isImageFile(dupe.path)) {{
                dupePreview.innerHTML = `<img src="/api/thumbnail?path=${{encodeURIComponent(dupe.path)}}" class="w-full h-full object-contain" alt="duplicate">`;
            }} else {{
                dupePreview.innerHTML = `<span class="text-xs font-mono text-slate-500 uppercase">${{dupe.path.split('.').pop()}} DOCUMENT</span>`;
            }}

            document.getElementById('comparisonModal').classList.remove('hidden');
        }}

        function closeComparisonModal() {{
            document.getElementById('comparisonModal').classList.add('hidden');
            modalActiveCluster = null;
            modalActiveDupe = null;
        }}

        async function swapKeeperInModal() {{
            if (!modalActiveCluster || !modalActiveDupe) return;
            await setKeeperOverride(modalActiveCluster.group_id, encodeURIComponent(modalActiveDupe.path));
            closeComparisonModal();
        }}

        // Quarantine Modal Controls
        function openQuarantineModal() {{
            if (!currentSummary) return;
            document.getElementById('quarantineModal').classList.remove('hidden');
        }}

        function closeQuarantineModal() {{
            document.getElementById('quarantineModal').classList.add('hidden');
        }}

        async function executeConfirmedQuarantine() {{
            closeQuarantineModal();
            const btn = document.getElementById('dockQuarantineBtn');
            btn.disabled = true;
            btn.innerText = "Quarantining Duplicates...";

            try {{
                const res = await fetch('/api/quarantine/execute', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        summary_file: currentSummary.summary_json,
                        base_dir: currentSummary.scanned_paths || currentSummary.scanned_dir
                    }})
                }});
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || "Quarantine execution failed");
                alert(`[✓] Successfully quarantined ${{data.total_files_moved}} duplicate files (${{(data.total_bytes_moved / (1024*1024)).toFixed(2)}} MB).`);
                updateStatus("completed", `Quarantine completed: ${{data.total_files_moved}} duplicates isolated safely.`);
            }} catch (e) {{
                alert("Quarantine error: " + e.message);
                updateStatus("failed", "Quarantine error: " + e.message);
            }} finally {{
                btn.disabled = false;
                btn.innerText = "⚡ Move Duplicates to Quarantine";
            }}
        }}

        async function triggerScan() {{
            const rawInput = document.getElementById('dirInput').value;
            const threshold = parseFloat(document.getElementById('thresholdInput').value) / 100.0;
            const paths = rawInput.replace(/\\r/g, '\\n').replace(/,/g, '\\n').split('\\n').map(p => p.trim()).filter(p => p.length > 0);

            if (paths.length === 0) {{
                alert("Please provide at least one directory path to scan.");
                return;
            }}

            const btn = document.getElementById('scanBtn');
            btn.disabled = true;
            toggleScanDrawer();
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
            }}
        }}

        async function pollScanStatus() {{
            try {{
                const res = await fetch('/api/status');
                const state = await res.json();
                if (state.status === "running") {{
                    updateStatus("running", state.message || "Scanning files, classifying images, and computing DINOv2 embeddings...");
                }} else if (state.status === "completed") {{
                    clearInterval(pollTimer);
                    pollTimer = null;
                    document.getElementById('scanBtn').disabled = false;
                    loadSummaryState(state.summary, state.message);
                }} else if (state.status === "failed") {{
                    clearInterval(pollTimer);
                    pollTimer = null;
                    document.getElementById('scanBtn').disabled = false;
                    updateStatus("failed", state.message);
                }}
            }} catch (e) {{
                console.error("Polling error:", e);
            }}
        }}
    </script>
</body>
</html>
"""
