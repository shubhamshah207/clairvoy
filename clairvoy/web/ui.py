"""
Clairvoy Web UI Component
Google Material Design 3 (M3) Storage Optimization Studio.
Inspired by Google Photos, Google Drive, Google Files, and Google One.
100% offline, zero-dependency, ultra-minimal code with Photos Grid, Drive List,
Google floating search bar, navigation rail, and Safe Trash/Permanent Deletion.
"""

from clairvoy.core.config import VERSION


def get_index_html() -> str:
    """Renders the comprehensive Google Material Design 3 single-page dashboard."""
    return f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Clairvoy | Google Storage & Photos Deduplication Studio</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {{
            darkMode: 'class',
            theme: {{
                extend: {{
                    colors: {{
                        google: {{
                            blue: '#8ab4f8',
                            blueDark: '#1a73e8',
                            blueContainer: '#1a3860',
                            red: '#f28b82',
                            redDark: '#d93025',
                            yellow: '#fdd663',
                            yellowDark: '#f9ab00',
                            green: '#81c995',
                            greenDark: '#1e8e3e',
                            surface: '#1e1f20',
                            surfaceVariant: '#28292a',
                            surfaceContainer: '#202124',
                            surfaceHigh: '#303134',
                            bg: '#131314',
                            textPrimary: '#e3e3e3',
                            textSecondary: '#c4c7c5',
                            textTertiary: '#8e918f',
                            outline: 'rgba(255, 255, 255, 0.10)'
                        }}
                    }}
                }}
            }}
        }}
    </script>
    <style>
        :root {{
            --md-sys-color-bg: #131314;
            --md-sys-color-surface: #1e1f20;
            --md-sys-color-surface-container: #202124;
            --md-sys-color-surface-high: #303134;
            --md-sys-color-primary: #8ab4f8;
            --md-sys-color-primary-container: #1a3860;
            --md-sys-color-success: #81c995;
            --md-sys-color-error: #f28b82;
            --md-sys-color-warning: #fdd663;
            --md-sys-color-outline: rgba(255, 255, 255, 0.10);
            --md-sys-color-text-primary: #e3e3e3;
            --md-sys-color-text-secondary: #c4c7c5;
        }}
        body {{
            background-color: var(--md-sys-color-bg);
            color: var(--md-sys-color-text-primary);
            font-family: 'Google Sans', system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            overflow-x: hidden;
            margin: 0;
            padding: 0;
        }}
        .custom-scrollbar::-webkit-scrollbar {{ width: 6px; height: 6px; }}
        .custom-scrollbar::-webkit-scrollbar-thumb {{ background: #3c4043; border-radius: 4px; }}
        .custom-scrollbar::-webkit-scrollbar-track {{ background: transparent; }}

        .m3-card {{
            background-color: var(--md-sys-color-surface);
            border: 1px solid var(--md-sys-color-outline);
            border-radius: 20px;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        .m3-card:hover {{
            border-color: rgba(255, 255, 255, 0.18);
            background-color: var(--md-sys-color-surface-high);
        }}
        .m3-chip {{
            border-radius: 9999px;
            border: 1px solid var(--md-sys-color-outline);
            background-color: var(--md-sys-color-surface-container);
            color: var(--md-sys-color-text-secondary);
            font-size: 12px;
            font-weight: 500;
            padding: 6px 14px;
            transition: all 0.15s ease;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            user-select: none;
        }}
        .m3-chip:hover {{
            background-color: var(--md-sys-color-surface-high);
            color: var(--md-sys-color-text-primary);
            border-color: rgba(255, 255, 255, 0.2);
        }}
        .m3-chip.active {{
            background-color: var(--md-sys-color-primary-container);
            color: var(--md-sys-color-primary);
            border-color: rgba(138, 180, 248, 0.4);
            font-weight: 600;
        }}
        .m3-button-primary {{
            background-color: var(--md-sys-color-primary);
            color: #131314;
            border-radius: 9999px;
            font-weight: 600;
            font-size: 13px;
            padding: 8px 18px;
            transition: all 0.15s ease;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            border: none;
            cursor: pointer;
        }}
        .m3-button-primary:hover {{
            background-color: #a8c7fa;
            box-shadow: 0 1px 3px rgba(0,0,0,0.3);
        }}
        .m3-button-secondary {{
            background-color: var(--md-sys-color-surface-container);
            color: var(--md-sys-color-text-primary);
            border: 1px solid var(--md-sys-color-outline);
            border-radius: 9999px;
            font-weight: 500;
            font-size: 13px;
            padding: 8px 16px;
            transition: all 0.15s ease;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            cursor: pointer;
        }}
        .m3-button-secondary:hover {{
            background-color: var(--md-sys-color-surface-high);
            border-color: rgba(255,255,255,0.2);
        }}
        .m3-button-danger {{
            background-color: rgba(242, 139, 130, 0.15);
            color: var(--md-sys-color-error);
            border: 1px solid rgba(242, 139, 130, 0.3);
            border-radius: 9999px;
            font-weight: 600;
            font-size: 13px;
            padding: 8px 16px;
            transition: all 0.15s ease;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            cursor: pointer;
        }}
        .m3-button-danger:hover {{
            background-color: rgba(242, 139, 130, 0.25);
            border-color: rgba(242, 139, 130, 0.5);
        }}
        /* Google Photos Checkbox Chip */
        .gp-check-circle {{
            width: 22px;
            height: 22px;
            border-radius: 50%;
            border: 2px solid rgba(255, 255, 255, 0.7);
            background: rgba(0, 0, 0, 0.35);
            backdrop-filter: blur(4px);
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
            cursor: pointer;
        }}
        .gp-check-circle.checked {{
            background-color: var(--md-sys-color-primary);
            border-color: var(--md-sys-color-primary);
        }}
        .gp-check-circle.checked svg {{
            opacity: 1;
        }}
        .gp-check-circle svg {{
            opacity: 0;
            color: #131314;
            transition: opacity 0.1s ease;
        }}
    </style>
</head>
<body class="min-h-screen pb-32 custom-scrollbar bg-[#131314] text-[#e3e3e3]">

    <!-- Google Material App Bar -->
    <header class="sticky top-0 z-40 bg-[#1e1f20]/95 backdrop-blur-md border-b border-[#28292a] px-4 lg:px-8 py-3">
        <div class="max-w-7xl mx-auto flex items-center justify-between gap-3">

            <!-- Logo & Brand (Google 4-Colors) -->
            <div class="flex items-center gap-3 flex-shrink-0">
                <div class="flex items-center gap-1.5">
                    <span class="w-2.5 h-2.5 rounded-full bg-[#4285F4]"></span>
                    <span class="w-2.5 h-2.5 rounded-full bg-[#EA4335]"></span>
                    <span class="w-2.5 h-2.5 rounded-full bg-[#FBBC05]"></span>
                    <span class="w-2.5 h-2.5 rounded-full bg-[#34A853]"></span>
                </div>
                <div class="flex items-baseline gap-2">
                    <span class="text-xl font-bold tracking-tight text-white flex items-center gap-1.5">
                        Clairvoy
                        <span class="text-xs font-semibold text-[#8ab4f8] bg-[#1a3860] px-2 py-0.5 rounded-full">Storage</span>
                    </span>
                    <span class="hidden md:inline text-[11px] font-mono text-[#8e918f]">v{VERSION}</span>
                </div>
            </div>

            <!-- Google Floating Search Bar -->
            <div class="flex-1 max-w-2xl mx-2">
                <div class="relative flex items-center bg-[#28292a] hover:bg-[#303134] focus-within:bg-[#303134] focus-within:ring-1 focus-within:ring-[#8ab4f8] border border-transparent focus-within:border-[#8ab4f8] rounded-full px-4 py-2 transition shadow-sm">
                    <svg class="w-4 h-4 text-[#8e918f] mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                    </svg>
                    <input type="text" id="searchInput" oninput="onSearchInput(this.value)"
                           placeholder="Search files, folders, duplicate formats..."
                           class="w-full bg-transparent text-sm text-[#e3e3e3] placeholder-[#8e918f] focus:outline-none">
                    <button id="clearSearchBtn" onclick="clearSearch()" class="hidden text-[#8e918f] hover:text-white ml-2 text-sm">
                        ✕
                    </button>
                </div>
            </div>

            <!-- Runs Selector & Scan Trigger -->
            <div class="flex items-center gap-2 flex-shrink-0">
                <!-- Google Account / Run Selector -->
                <div class="hidden sm:flex items-center bg-[#28292a] border border-[#3c4043] rounded-full px-3 py-1.5 text-xs text-[#c4c7c5]">
                    <span class="mr-1.5">📂</span>
                    <select id="runsDropdown" onchange="onRunSelected(this.value)" class="bg-transparent text-xs text-[#e3e3e3] focus:outline-none cursor-pointer max-w-[180px] truncate">
                        <option value="">Loading runs...</option>
                    </select>
                </div>

                <button onclick="toggleScanDrawer()" class="m3-button-secondary text-xs !py-1.5 !px-3">
                    <span>⚡</span> <span>Scan</span>
                </button>

                <div class="w-2.5 h-2.5 rounded-full bg-[#81c995] animate-pulse" title="100% Offline & Local"></div>
            </div>
        </div>
    </header>

    <!-- Collapsible New Scan Drawer -->
    <div id="scanDrawer" class="hidden bg-[#1e1f20] border-b border-[#28292a] px-6 py-5 shadow-2xl transition-all">
        <div class="max-w-4xl mx-auto">
            <div class="flex justify-between items-center mb-4">
                <div class="flex items-center gap-2">
                    <span class="text-lg">📁</span>
                    <h3 class="text-sm font-bold text-white uppercase tracking-wider">Start Storage Scan</h3>
                </div>
                <button onclick="toggleScanDrawer()" class="text-[#8e918f] hover:text-white text-sm">✕ Close</button>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div class="md:col-span-3">
                    <label class="block text-xs font-semibold text-[#c4c7c5] mb-1.5">Target Directories (one per line):</label>
                    <textarea id="dirInput" rows="2" placeholder="/home/user/Photos&#10;/mnt/backup/Documents"
                              class="w-full bg-[#131314] border border-[#3c4043] rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-[#8ab4f8]"></textarea>
                </div>
                <div class="flex flex-col justify-between">
                    <div>
                        <label class="block text-xs font-semibold text-[#c4c7c5] mb-1.5">Similarity Threshold:</label>
                        <div class="flex items-center gap-2">
                            <input type="range" id="thresholdSlider" min="70" max="99" value="95"
                                   oninput="document.getElementById('thresholdInput').value=this.value" class="w-full accent-[#8ab4f8]">
                            <input type="number" id="thresholdInput" min="70" max="99" value="95"
                                   oninput="document.getElementById('thresholdSlider').value=this.value"
                                   class="w-14 bg-[#131314] border border-[#3c4043] rounded-lg px-2 py-1 text-xs text-center font-mono text-white">
                            <span class="text-xs text-[#8e918f]">%</span>
                        </div>
                    </div>
                    <button onclick="triggerScan()" id="scanBtn" class="m3-button-primary justify-center w-full mt-3">
                        <span>▶ Start Scan</span>
                    </button>
                </div>
            </div>
        </div>
    </div>

    <!-- Main Studio Layout (Nav Rail + Content Area) -->
    <div class="max-w-7xl mx-auto px-4 lg:px-8 pt-6 flex flex-col md:flex-row gap-6">

        <!-- Google Navigation Rail (Left Sidebar) -->
        <aside class="w-full md:w-56 flex-shrink-0 flex md:flex-col gap-1.5 overflow-x-auto pb-2 md:pb-0">
            <button onclick="switchNavSection('CLEANUP')" id="navBtn_CLEANUP"
                    class="nav-rail-btn w-full flex items-center gap-3 px-4 py-3 rounded-full text-xs font-semibold transition bg-[#1a3860] text-[#8ab4f8]">
                <span class="text-base">🧹</span>
                <span>Clean up</span>
            </button>
            <button onclick="switchNavSection('PHOTOS')" id="navBtn_PHOTOS"
                    class="nav-rail-btn w-full flex items-center gap-3 px-4 py-3 rounded-full text-xs font-semibold transition hover:bg-[#28292a] text-[#c4c7c5]">
                <span class="text-base">🖼️</span>
                <span>Photos View</span>
            </button>
            <button onclick="switchNavSection('DRIVE')" id="navBtn_DRIVE"
                    class="nav-rail-btn w-full flex items-center gap-3 px-4 py-3 rounded-full text-xs font-semibold transition hover:bg-[#28292a] text-[#c4c7c5]">
                <span class="text-base">📁</span>
                <span>Drive List</span>
            </button>
            <button onclick="switchNavSection('DUPLICATES')" id="navBtn_DUPLICATES"
                    class="nav-rail-btn w-full flex items-center gap-3 px-4 py-3 rounded-full text-xs font-semibold transition hover:bg-[#28292a] text-[#c4c7c5]">
                <span class="text-base">🗂️</span>
                <span>All Clusters</span>
            </button>
            <button onclick="switchNavSection('TRASH')" id="navBtn_TRASH"
                    class="nav-rail-btn w-full flex items-center gap-3 px-4 py-3 rounded-full text-xs font-semibold transition hover:bg-[#28292a] text-[#c4c7c5]">
                <span class="text-base">🗑️</span>
                <span>Trash & Audit</span>
            </button>
        </aside>

        <!-- Main Workspace -->
        <main class="flex-1 min-w-0">

            <!-- Google One Clean-Up Hero Card -->
            <section id="cleanupHeroCard" class="m3-card p-6 md:p-8 mb-6 relative overflow-hidden">
                <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
                    <div>
                        <div class="flex items-center gap-2 text-xs font-bold text-[#8ab4f8] uppercase tracking-wider mb-1">
                            <span>Google Storage Manager</span>
                        </div>
                        <h2 class="text-2xl md:text-3xl font-bold text-white tracking-tight flex items-baseline gap-2">
                            Clean up <span id="heroWastedGb" class="text-[#8ab4f8]">0.000</span> GB
                        </h2>
                        <p id="heroWastedMb" class="text-xs text-[#8e918f] font-mono mt-0.5">0 MB recoverable across duplicates</p>
                    </div>
                    <div class="flex items-center gap-2">
                        <div class="text-right text-xs text-[#8e918f] font-mono">
                            <div id="heroClusterCount" class="font-bold text-[#e3e3e3]">0 duplicate clusters</div>
                            <div id="heroFileCount">0 files analyzed</div>
                        </div>
                    </div>
                </div>

                <!-- Google Multi-Colored Storage Meter -->
                <div class="w-full bg-[#131314] rounded-full h-3 overflow-hidden flex border border-[#3c4043] mb-4">
                    <div id="segPhoto" class="bg-[#8ab4f8] h-full transition-all duration-500" style="width: 0%;" title="Photos"></div>
                    <div id="segScreenshot" class="bg-[#fdd663] h-full transition-all duration-500" style="width: 0%;" title="Screenshots"></div>
                    <div id="segDocument" class="bg-[#81c995] h-full transition-all duration-500" style="width: 0%;" title="Documents"></div>
                    <div id="segFile" class="bg-[#f28b82] h-full transition-all duration-500" style="width: 0%;" title="Large / Other Files"></div>
                </div>

                <!-- Storage Legend -->
                <div class="flex flex-wrap gap-4 text-xs font-medium text-[#c4c7c5]">
                    <div class="flex items-center gap-1.5">
                        <span class="w-2.5 h-2.5 rounded-full bg-[#8ab4f8]"></span>
                        <span>Photos: <strong id="legendPhoto" class="text-white font-mono">0</strong></span>
                    </div>
                    <div class="flex items-center gap-1.5">
                        <span class="w-2.5 h-2.5 rounded-full bg-[#fdd663]"></span>
                        <span>Screenshots: <strong id="legendScreenshot" class="text-white font-mono">0</strong></span>
                    </div>
                    <div class="flex items-center gap-1.5">
                        <span class="w-2.5 h-2.5 rounded-full bg-[#81c995]"></span>
                        <span>Documents: <strong id="legendDocument" class="text-white font-mono">0</strong></span>
                    </div>
                    <div class="flex items-center gap-1.5">
                        <span class="w-2.5 h-2.5 rounded-full bg-[#f28b82]"></span>
                        <span>Files: <strong id="legendFile" class="text-white font-mono">0</strong></span>
                    </div>
                </div>
            </section>

            <!-- Filter Chips Toolbar & View Mode Controls -->
            <section class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6 pb-2">
                <!-- Modality Filter Chips (Google Style) -->
                <div class="flex items-center gap-2 overflow-x-auto w-full sm:w-auto pb-1">
                    <button onclick="setModalityTab('ALL')" id="tab_ALL" class="m3-chip active">
                        All <span id="tabCount_ALL" class="text-[11px] font-mono opacity-80">0</span>
                    </button>
                    <button onclick="setModalityTab('PHOTO')" id="tab_PHOTO" class="m3-chip">
                        Photos <span id="tabCount_PHOTO" class="text-[11px] font-mono opacity-80">0</span>
                    </button>
                    <button onclick="setModalityTab('SCREENSHOT')" id="tab_SCREENSHOT" class="m3-chip">
                        Screenshots <span id="tabCount_SCREENSHOT" class="text-[11px] font-mono opacity-80">0</span>
                    </button>
                    <button onclick="setModalityTab('DOCUMENT')" id="tab_DOCUMENT" class="m3-chip">
                        Docs <span id="tabCount_DOCUMENT" class="text-[11px] font-mono opacity-80">0</span>
                    </button>
                    <button onclick="setModalityTab('FILE')" id="tab_FILE" class="m3-chip">
                        Files <span id="tabCount_FILE" class="text-[11px] font-mono opacity-80">0</span>
                    </button>
                </div>

                <!-- Right View Controls: Match Type, Sort, View Toggle -->
                <div class="flex items-center gap-2 self-end sm:self-auto">
                    <!-- Sort Dropdown -->
                    <select onchange="onSortOrderChange(this.value)"
                            class="bg-[#202124] border border-[#3c4043] rounded-full px-3 py-1.5 text-xs text-[#c4c7c5] focus:outline-none cursor-pointer">
                        <option value="SIZE_DESC">Largest Wasted</option>
                        <option value="DUPES_DESC">Most Duplicates</option>
                        <option value="SIMILARITY_DESC">Similarity Score</option>
                    </select>

                    <!-- View Toggle Button (Photos Grid vs Drive List) -->
                    <div class="flex items-center bg-[#202124] border border-[#3c4043] rounded-full p-0.5">
                        <button onclick="setViewMode('grid')" id="viewModeGridBtn"
                                class="px-2.5 py-1 rounded-full text-xs font-medium transition bg-[#1a3860] text-[#8ab4f8]" title="Google Photos Grid View">
                            ▦ Grid
                        </button>
                        <button onclick="setViewMode('list')" id="viewModeListBtn"
                                class="px-2.5 py-1 rounded-full text-xs font-medium transition text-[#8e918f] hover:text-white" title="Google Drive List View">
                            ☰ List
                        </button>
                    </div>
                </div>
            </section>

            <!-- Pagination Status & Page Limit Selector -->
            <div class="flex justify-between items-center text-xs text-[#8e918f] font-mono mb-4 px-1">
                <span id="paginationSummary">Showing clusters...</span>
                <div class="flex items-center gap-2">
                    <span>Per page:</span>
                    <select onchange="onPerPageChange(parseInt(this.value))"
                            class="bg-[#202124] border border-[#3c4043] rounded-lg px-2 py-1 text-xs text-[#c4c7c5] focus:outline-none cursor-pointer">
                        <option value="25">25</option>
                        <option value="50">50</option>
                        <option value="100">100</option>
                    </select>
                </div>
            </div>

            <!-- Dynamic Clusters Container (Google Photos Grid or Google Drive List) -->
            <div id="clustersGallery" class="space-y-6"></div>

            <!-- Pagination Navigation Bar -->
            <div class="flex justify-center items-center gap-4 mt-8 pt-4">
                <button id="prevPageBtn" onclick="changePage(currentPage - 1)"
                        class="m3-button-secondary text-xs disabled:opacity-30 disabled:cursor-not-allowed">
                    ← Previous
                </button>
                <span id="pageIndicator" class="text-xs text-[#c4c7c5] font-mono">Page 1 of 1</span>
                <button id="nextPageBtn" onclick="changePage(currentPage + 1)"
                        class="m3-button-secondary text-xs disabled:opacity-30 disabled:cursor-not-allowed">
                    Next →
                </button>
            </div>
        </main>
    </div>

    <!-- Google Contextual Selection Action Bar (Appears when items are selected) -->
    <div id="contextualActionBar"
         class="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 w-[94%] max-w-4xl bg-[#28292a]/95 backdrop-blur-xl border border-[#3c4043] rounded-full px-5 py-3 shadow-2xl flex flex-wrap items-center justify-between gap-4 transition-all duration-300">
        <div class="flex items-center gap-3">
            <span class="w-6 h-6 rounded-full bg-[#1a3860] text-[#8ab4f8] flex items-center justify-center font-bold text-xs">✓</span>
            <div>
                <div id="dockSelectedSpace" class="font-bold text-white text-sm">0.000 GB selected</div>
                <div id="dockSelectedCount" class="text-[11px] text-[#8e918f] font-mono">0 duplicate files selected</div>
            </div>
        </div>

        <div class="flex items-center gap-2">
            <!-- Quick Selection Presets -->
            <button onclick="applySelectionRule('ALL')" class="m3-button-secondary !py-1.5 !px-3 text-xs">Select All</button>
            <button onclick="applySelectionRule('NONE')" class="m3-button-secondary !py-1.5 !px-3 text-xs">Clear</button>

            <!-- Actions -->
            <button onclick="openTrashDialog()" id="dockTrashBtn" class="m3-button-secondary !py-1.5 !px-3.5 text-xs text-[#8ab4f8] border-[#8ab4f8]/30">
                <span>🗑️ Move to Trash</span>
            </button>
            <button onclick="openPermanentDeleteDialog()" id="dockDeleteBtn" class="m3-button-danger !py-1.5 !px-3.5 text-xs">
                <span>⚠️ Delete Permanently</span>
            </button>
            <button onclick="openQuarantineModal()" id="dockQuarantineBtn" class="m3-button-secondary !py-1.5 !px-3.5 text-xs text-[#fdd663] border-[#fdd663]/30">
                <span>📦 Quarantine</span>
            </button>

            <a id="downloadCsvBtn" href="/api/reports/csv" download class="m3-button-secondary !py-1.5 !px-3 text-xs" title="Export CSV Report">
                <span>📄 CSV</span>
            </a>
        </div>
    </div>

    <!-- Google Photos Side-by-Side Comparison Lightbox Modal -->
    <div id="comparisonModal" class="hidden fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
        <div class="bg-[#1e1f20] border border-[#3c4043] rounded-3xl max-w-5xl w-full max-h-[92vh] flex flex-col overflow-hidden shadow-2xl">
            <div class="px-6 py-4 border-b border-[#28292a] flex justify-between items-center">
                <div>
                    <h3 id="modalClusterTitle" class="text-base font-bold text-white">Side-by-Side Comparison</h3>
                    <p id="modalClusterSubtitle" class="text-xs text-[#8e918f] font-mono">Compare Keeper against Candidate Duplicate</p>
                </div>
                <button onclick="closeComparisonModal()" class="text-[#8e918f] hover:text-white text-lg px-2">✕</button>
            </div>

            <div class="p-6 overflow-y-auto flex-1 grid grid-cols-1 md:grid-cols-2 gap-6 custom-scrollbar">
                <!-- Keeper Column -->
                <div class="bg-[#131314] rounded-2xl p-4 border border-[#81c995]/40 flex flex-col justify-between">
                    <div>
                        <div class="flex justify-between items-center mb-3">
                            <span class="text-xs font-bold bg-[#81c995]/20 text-[#81c995] px-2.5 py-1 rounded-full flex items-center gap-1">
                                <span>★</span> Designated Keeper
                            </span>
                            <span id="modalKeeperCategory" class="text-xs font-mono text-[#8e918f] uppercase">PHOTO</span>
                        </div>
                        <div id="modalKeeperPreview" class="w-full h-64 rounded-xl bg-black flex items-center justify-center overflow-hidden mb-3 border border-[#28292a]"></div>
                        <div class="space-y-1.5 text-xs">
                            <div id="modalKeeperName" class="font-bold text-white truncate">filename.jpg</div>
                            <div id="modalKeeperPath" class="text-[10px] text-[#8e918f] font-mono break-all">/path/to/file</div>
                            <div class="flex gap-4 font-mono text-[#c4c7c5] pt-1">
                                <span>Size: <strong id="modalKeeperSize" class="text-white">0 MB</strong></span>
                                <span>Resolution: <strong id="modalKeeperDim" class="text-white">N/A</strong></span>
                            </div>
                        </div>
                    </div>
                    <div class="mt-4 pt-3 border-t border-[#28292a]">
                        <span class="text-xs text-[#81c995] font-semibold flex items-center gap-1">✓ Safely preserved on disk</span>
                    </div>
                </div>

                <!-- Duplicate Column -->
                <div class="bg-[#131314] rounded-2xl p-4 border border-[#f28b82]/40 flex flex-col justify-between">
                    <div>
                        <div class="flex justify-between items-center mb-3">
                            <span class="text-xs font-bold bg-[#f28b82]/20 text-[#f28b82] px-2.5 py-1 rounded-full flex items-center gap-1">
                                <span>⌧</span> Redundant Duplicate
                            </span>
                            <span id="modalDupeSimilarity" class="text-xs font-mono text-[#fdd663]">100% Match</span>
                        </div>
                        <div id="modalDupePreview" class="w-full h-64 rounded-xl bg-black flex items-center justify-center overflow-hidden mb-3 border border-[#28292a]"></div>
                        <div class="space-y-1.5 text-xs">
                            <div id="modalDupeName" class="font-bold text-white truncate">filename_copy.jpg</div>
                            <div id="modalDupePath" class="text-[10px] text-[#8e918f] font-mono break-all">/path/to/copy</div>
                            <div class="flex gap-4 font-mono text-[#c4c7c5] pt-1">
                                <span>Size: <strong id="modalDupeSize" class="text-white">0 MB</strong></span>
                                <span>Resolution: <strong id="modalDupeDim" class="text-white">N/A</strong></span>
                            </div>
                        </div>
                    </div>
                    <div class="mt-4 pt-3 border-t border-[#28292a] flex justify-between items-center">
                        <button onclick="swapKeeperInModal()" class="m3-button-secondary text-xs !py-1.5 !px-3 text-[#8ab4f8]">
                            <span>★ Make This The Keeper</span>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Google Move to Trash Confirmation Dialog -->
    <div id="trashDialog" class="hidden fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
        <div class="bg-[#1e1f20] border border-[#3c4043] rounded-3xl max-w-md w-full p-6 shadow-2xl">
            <div class="flex items-center gap-3 mb-4">
                <div class="w-10 h-10 rounded-full bg-[#1a3860] text-[#8ab4f8] flex items-center justify-center text-lg">🗑️</div>
                <div>
                    <h3 class="text-lg font-bold text-white">Move to Trash?</h3>
                    <p class="text-xs text-[#8e918f]">Reversible Soft Delete</p>
                </div>
            </div>
            <p class="text-sm text-[#c4c7c5] leading-relaxed mb-5">
                Selected duplicate files will be safely moved into <code class="text-xs bg-[#131314] px-2 py-0.5 rounded text-[#8ab4f8]">.clairvoy_trash/</code>.
                You can restore them back to their original locations at any time from the Trash tab.
            </p>
            <div class="flex justify-end gap-3">
                <button onclick="closeTrashDialog()" class="m3-button-secondary text-xs">Cancel</button>
                <button onclick="executeConfirmedDelete('trash')" id="confirmTrashBtn" class="m3-button-primary text-xs">
                    Move to Trash
                </button>
            </div>
        </div>
    </div>

    <!-- Google Permanent Delete Confirmation Dialog -->
    <div id="permanentDeleteDialog" class="hidden fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
        <div class="bg-[#1e1f20] border border-[#f28b82]/40 rounded-3xl max-w-md w-full p-6 shadow-2xl">
            <div class="flex items-center gap-3 mb-4">
                <div class="w-10 h-10 rounded-full bg-[#f28b82]/20 text-[#f28b82] flex items-center justify-center text-lg">⚠️</div>
                <div>
                    <h3 class="text-lg font-bold text-white">Delete Permanently?</h3>
                    <p class="text-xs text-[#f28b82]">Irreversible Disk Free</p>
                </div>
            </div>
            <p class="text-sm text-[#c4c7c5] leading-relaxed mb-4">
                This action <strong class="text-white font-semibold">cannot be undone</strong>. All selected duplicate copies will be permanently unlinked from storage.
            </p>
            <div class="bg-[#131314] rounded-xl p-3 border border-[#3c4043] text-xs font-mono text-[#8e918f] mb-5">
                • Designated Keeper files are strictly protected and never touched.<br>
                • An immutable audit log will be saved to <span class="text-white">_dedupe_reports/</span>.
            </div>
            <div class="flex justify-end gap-3">
                <button onclick="closePermanentDeleteDialog()" class="m3-button-secondary text-xs">Cancel</button>
                <button onclick="executeConfirmedDelete('permanent')" id="confirmPermanentDeleteBtn" class="m3-button-danger text-xs">
                    Delete Permanently
                </button>
            </div>
        </div>
    </div>

    <!-- Quarantine Modal -->
    <div id="quarantineModal" class="hidden fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
        <div class="bg-[#1e1f20] border border-[#fdd663]/40 rounded-3xl max-w-md w-full p-6 shadow-2xl">
            <div class="flex items-center gap-3 mb-4">
                <div class="w-10 h-10 rounded-full bg-[#fdd663]/20 text-[#fdd663] flex items-center justify-center text-lg">📦</div>
                <div>
                    <h3 class="text-lg font-bold text-white">Isolate to Quarantine?</h3>
                    <p class="text-xs text-[#fdd663]">Non-Destructive Staging</p>
                </div>
            </div>
            <p class="text-sm text-[#c4c7c5] leading-relaxed mb-5">
                Duplicates will be moved into <code class="text-xs bg-[#131314] px-2 py-0.5 rounded text-[#fdd663]">_duplicate_quarantine/</code> preserving directory trees, with a complete rollback manifest.
            </p>
            <div class="flex justify-end gap-3">
                <button onclick="closeQuarantineModal()" class="m3-button-secondary text-xs">Cancel</button>
                <button onclick="executeConfirmedQuarantine()" id="confirmQuarantineBtn" class="m3-button-primary text-xs !bg-[#fdd663] !text-[#131314]">
                    Isolate Files
                </button>
            </div>
        </div>
    </div>

    <!-- Client-Side JavaScript Engine -->
    <script>
        // State Management
        let currentSummary = null;
        let allClusters = [];
        let filteredClusters = [];
        let activeModality = 'ALL';
        let activeSortOrder = 'SIZE_DESC';
        let searchQuery = '';
        let currentPage = 1;
        let perPage = 25;
        let viewMode = 'grid'; // 'grid' (Photos) | 'list' (Drive)
        let currentNav = 'CLEANUP'; // 'CLEANUP' | 'PHOTOS' | 'DRIVE' | 'DUPLICATES' | 'TRASH'
        let pollTimer = null;

        // Tracks excluded file paths from batch actions (set of paths)
        let excludedPaths = new Set();

        // Comparison modal active references
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
                }}
            }} catch (e) {{
                console.error("Initial status error:", e);
            }}
        }});

        function toggleScanDrawer() {{
            document.getElementById('scanDrawer').classList.toggle('hidden');
        }}

        function setViewMode(mode) {{
            viewMode = mode;
            const gridBtn = document.getElementById('viewModeGridBtn');
            const listBtn = document.getElementById('viewModeListBtn');
            if (mode === 'grid') {{
                gridBtn.className = "px-2.5 py-1 rounded-full text-xs font-medium transition bg-[#1a3860] text-[#8ab4f8]";
                listBtn.className = "px-2.5 py-1 rounded-full text-xs font-medium transition text-[#8e918f] hover:text-white";
            }} else {{
                listBtn.className = "px-2.5 py-1 rounded-full text-xs font-medium transition bg-[#1a3860] text-[#8ab4f8]";
                gridBtn.className = "px-2.5 py-1 rounded-full text-xs font-medium transition text-[#8e918f] hover:text-white";
            }}
            renderCurrentPage();
        }}

        function switchNavSection(sec) {{
            currentNav = sec;
            document.querySelectorAll('.nav-rail-btn').forEach(btn => {{
                btn.className = "nav-rail-btn w-full flex items-center gap-3 px-4 py-3 rounded-full text-xs font-semibold transition hover:bg-[#28292a] text-[#c4c7c5]";
            }});
            const active = document.getElementById('navBtn_' + sec);
            if (active) {{
                active.className = "nav-rail-btn w-full flex items-center gap-3 px-4 py-3 rounded-full text-xs font-semibold transition bg-[#1a3860] text-[#8ab4f8]";
            }}

            if (sec === 'PHOTOS') {{
                setModalityTab('PHOTO');
                setViewMode('grid');
            }} else if (sec === 'DRIVE') {{
                setViewMode('list');
            }} else if (sec === 'CLEANUP' || sec === 'DUPLICATES') {{
                setModalityTab('ALL');
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
                        opt.className = "bg-[#1e1f20] text-[#e3e3e3]";
                        const target = r.scanned_paths && r.scanned_paths.length > 0 ? r.scanned_paths[0] : "Scan";
                        const shortTarget = target.length > 18 ? target.slice(0, 16) + ".." : target;
                        opt.innerText = `${{shortTarget}} • ${{r.wasted_gb.toFixed(2)}} GB`;
                        dropdown.appendChild(opt);
                    }}
                }}
                const customOpt = document.createElement('option');
                customOpt.value = "__custom__";
                customOpt.className = "bg-[#1e1f20] text-[#8ab4f8] font-bold";
                customOpt.innerText = "➕ Load report path...";
                dropdown.appendChild(customOpt);

                if (selectedRunId) dropdown.value = selectedRunId;
            }} catch (e) {{
                console.error("Runs load error:", e);
            }}
        }}

        async function onRunSelected(val) {{
            if (!val) return;
            if (val === "__custom__") {{
                const path = prompt("Enter absolute path to clairvoy_summary.json:");
                if (!path) return;
                await loadRunReport({{ path: path.trim() }});
            }} else {{
                await loadRunReport({{ run_id: val }});
            }}
        }}

        async function loadRunReport(payload) {{
            try {{
                const res = await fetch('/api/runs/load', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(payload)
                }});
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || "Load failed");
                loadSummaryState(data.summary, "Report loaded.");
                await loadPastRunsList(payload.run_id);
            }} catch (e) {{
                alert("Error: " + e.message);
            }}
        }}

        function loadSummaryState(summary, msg) {{
            currentSummary = summary;
            excludedPaths.clear();

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
            document.getElementById('heroWastedMb').innerText = `${{(summary.wasted_mb || 0).toLocaleString()}} MB recoverable across duplicates`;
            document.getElementById('heroFileCount').innerText = `${{(summary.total_files_scanned || 0).toLocaleString()}} files analyzed`;
            document.getElementById('heroClusterCount').innerText = `${{(summary.total_duplicate_groups || 0).toLocaleString()}} clusters`;

            const cb = summary.category_breakdown || {{}};
            const totalDupes = Math.max(1, (summary.groups ? summary.groups.filter(g => g.action === 'DUPLICATE').length : 1));
            const pPhoto = ((cb.PHOTO || 0) / totalDupes) * 100;
            const pScreens = ((cb.SCREENSHOT || 0) / totalDupes) * 100;
            const pDoc = ((cb.DOCUMENT || 0) / totalDupes) * 100;
            const pFile = Math.max(0, 100 - (pPhoto + pScreens + pDoc));

            document.getElementById('segPhoto').style.width = pPhoto + '%';
            document.getElementById('segScreenshot').style.width = pScreens + '%';
            document.getElementById('segDocument').style.width = pDoc + '%';
            document.getElementById('segFile').style.width = pFile + '%';

            document.getElementById('legendPhoto').innerText = `${{cb.PHOTO || 0}} files`;
            document.getElementById('legendScreenshot').innerText = `${{cb.SCREENSHOT || 0}} files`;
            document.getElementById('legendDocument').innerText = `${{cb.DOCUMENT || 0}} files`;
            document.getElementById('legendFile').innerText = `${{cb.FILE || 0}} files`;
        }}

        function renderModalityTabCounts(summary) {{
            const cb = summary.category_breakdown || {{}};
            const total = summary.total_duplicate_groups || allClusters.length;
            document.getElementById('tabCount_ALL').innerText = total.toLocaleString();
            document.getElementById('tabCount_PHOTO').innerText = (cb.PHOTO || 0).toLocaleString();
            document.getElementById('tabCount_SCREENSHOT').innerText = (cb.SCREENSHOT || 0).toLocaleString();
            document.getElementById('tabCount_DOCUMENT').innerText = (cb.DOCUMENT || 0).toLocaleString();
            document.getElementById('tabCount_FILE').innerText = (cb.FILE || 0).toLocaleString();
        }}

        function setModalityTab(tab) {{
            activeModality = tab;
            document.querySelectorAll('.m3-chip').forEach(el => el.classList.remove('active'));
            const btn = document.getElementById('tab_' + tab);
            if (btn) btn.classList.add('active');
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
                if (activeModality !== 'ALL') {{
                    const matchesCategory = c.items.some(i => i.category === activeModality);
                    if (!matchesCategory) return false;
                }}
                if (searchQuery) {{
                    const matches = c.items.some(i => i.path.toLowerCase().includes(searchQuery));
                    if (!matches) return false;
                }}
                return true;
            }});

            filteredClusters.sort((a, b) => {{
                if (activeSortOrder === 'SIZE_DESC') {{
                    return b.totalWastedBytes - a.totalWastedBytes;
                }} else if (activeSortOrder === 'DUPES_DESC') {{
                    return b.duplicates.length - a.duplicates.length;
                }} else {{
                    const simA = a.duplicates.length > 0 ? (a.duplicates[0].similarity_score || 0) : 0;
                    const simB = b.duplicates.length > 0 ? (b.duplicates[0].similarity_score || 0) : 0;
                    return simB - simA;
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
                    <div class="text-center py-20 m3-card text-[#8e918f]">
                        <span class="text-3xl block mb-2">🔍</span>
                        No duplicate clusters match the current filters.
                    </div>
                `;
                return;
            }}

            gallery.innerHTML = '';
            for (const c of pageClusters) {{
                if (viewMode === 'grid') {{
                    gallery.appendChild(createGooglePhotosCard(c));
                }} else {{
                    gallery.appendChild(createGoogleDriveListCard(c));
                }}
            }}
        }}

        function changePage(newPage) {{
            currentPage = newPage;
            renderCurrentPage();
            window.scrollTo({{ top: document.getElementById('clustersGallery').offsetTop - 90, behavior: 'smooth' }});
        }}

        function isImageFile(path) {{
            const exts = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.heic', '.psd'];
            return exts.some(e => path.toLowerCase().endsWith(e));
        }}

        // Google Photos Grid Card
        function createGooglePhotosCard(cluster) {{
            const card = document.createElement('div');
            card.className = "m3-card p-5 shadow-lg";

            const wastedMb = (cluster.totalWastedBytes / (1024 * 1024)).toFixed(2);

            card.innerHTML = `
                <div class="flex flex-wrap justify-between items-center pb-3 mb-4 border-b border-[#28292a] gap-2">
                    <div class="flex items-center gap-2.5">
                        <span class="font-bold text-white text-sm">Cluster #${{cluster.group_id}}</span>
                        <span class="text-[11px] font-mono px-2 py-0.5 rounded-full bg-[#1a3860] text-[#8ab4f8]">${{cluster.match_type}}</span>
                        <span class="text-[11px] font-mono text-[#8e918f]">Wasted: ${{wastedMb}} MB</span>
                    </div>
                    <div>
                        <button onclick="openComparisonLightbox(${{cluster.group_id}})" class="m3-button-secondary text-xs !py-1 !px-3">
                            <span>🔍 Compare</span>
                        </button>
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    ${{cluster.items.map(item => createPhotoTileHtml(cluster.group_id, item)).join('')}}
                </div>
            `;
            return card;
        }}

        function createPhotoTileHtml(groupId, item) {{
            const isKeeper = (item.action === 'KEEP');
            const isExcluded = excludedPaths.has(item.path);
            const isChecked = !isKeeper && !isExcluded;

            const fname = item.path.split('/').pop();
            const parentDir = item.path.substring(0, item.path.lastIndexOf('/'));
            const sizeStr = `${{(item.size_mb || 0).toFixed(2)}} MB`;

            return `
                <div class="relative group rounded-2xl bg-[#131314] border ${{isKeeper ? 'border-[#81c995] shadow-md shadow-[#81c995]/10' : 'border-[#28292a]'}} p-3 flex flex-col justify-between overflow-hidden transition-all hover:border-[#3c4043]">

                    <!-- Top Bar: Checkbox or Keeper Star -->
                    <div class="flex justify-between items-center mb-2 z-10">
                        ${{isKeeper ? `
                            <span class="text-[10px] font-bold text-[#81c995] bg-[#81c995]/15 px-2 py-0.5 rounded-full flex items-center gap-1">
                                <span>★</span> Keeper
                            </span>
                        ` : `
                            <div onclick="toggleItemSelection('${{encodeURIComponent(item.path)}}')"
                                 class="gp-check-circle ${{isChecked ? 'checked' : ''}}" title="Toggle for deletion/quarantine">
                                <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                                    <polyline points="20 6 9 17 4 12"></polyline>
                                </svg>
                            </div>
                        `}}
                        <span class="text-[10px] font-mono text-[#8e918f] uppercase">${{item.category || 'FILE'}}</span>
                    </div>

                    <!-- Thumbnail & Info -->
                    <div class="flex gap-3 items-center mb-3">
                        <div class="w-16 h-16 rounded-xl bg-black flex items-center justify-center overflow-hidden flex-shrink-0 border border-[#28292a]">
                            ${{isImageFile(item.path) ? `
                                <img src="/api/thumbnail?path=${{encodeURIComponent(item.path)}}" class="w-full h-full object-cover" loading="lazy" alt="preview"
                                     onerror="this.parentElement.innerHTML='<span class=\\'text-xs text-[#8e918f]\\'>IMG</span>'">
                            ` : `
                                <span class="text-xs font-mono text-[#8e918f] uppercase">${{fname.split('.').pop() || 'DOC'}}</span>
                            `}}
                        </div>
                        <div class="min-w-0 flex-1 text-xs">
                            <div class="font-medium text-white truncate" title="${{fname}}">${{fname}}</div>
                            <div class="text-[10px] text-[#8e918f] font-mono truncate" title="${{parentDir}}">${{parentDir}}</div>
                            <div class="text-[11px] text-[#c4c7c5] font-mono mt-1 font-semibold">${{sizeStr}}</div>
                        </div>
                    </div>

                    <!-- Card Actions -->
                    <div class="pt-2 border-t border-[#202124] flex justify-between items-center text-xs">
                        ${{isKeeper ? `
                            <span class="text-[10px] text-[#81c995] font-mono">Original retained</span>
                        ` : `
                            <button onclick="setKeeperOverride(${{groupId}}, '${{encodeURIComponent(item.path)}}')"
                                    class="text-[11px] text-[#8ab4f8] hover:underline font-medium">
                                ★ Make Keeper
                            </button>
                            <span class="text-[10px] font-mono text-[#8e918f]">${{item.similarity || '100%'}}</span>
                        `}}
                    </div>
                </div>
            `;
        }}

        // Google Drive List Card
        function createGoogleDriveListCard(cluster) {{
            const card = document.createElement('div');
            card.className = "m3-card p-4 shadow-lg";

            const wastedMb = (cluster.totalWastedBytes / (1024 * 1024)).toFixed(2);

            card.innerHTML = `
                <div class="flex justify-between items-center pb-2.5 mb-3 border-b border-[#28292a]">
                    <div class="flex items-center gap-2">
                        <span class="font-bold text-white text-xs">Cluster #${{cluster.group_id}}</span>
                        <span class="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#1a3860] text-[#8ab4f8]">${{cluster.match_type}}</span>
                        <span class="text-[10px] font-mono text-[#8e918f]">Wasted: ${{wastedMb}} MB</span>
                    </div>
                    <button onclick="openComparisonLightbox(${{cluster.group_id}})" class="text-xs text-[#8ab4f8] hover:underline">
                        Compare Diff
                    </button>
                </div>

                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs font-mono">
                        <thead>
                            <tr class="text-[#8e918f] border-b border-[#202124]">
                                <th class="py-1.5 px-2 w-8"></th>
                                <th class="py-1.5 px-2">Name</th>
                                <th class="py-1.5 px-2">Role</th>
                                <th class="py-1.5 px-2">Size</th>
                                <th class="py-1.5 px-2">Path</th>
                                <th class="py-1.5 px-2 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-[#202124]">
                            ${{cluster.items.map(item => createDriveRowHtml(cluster.group_id, item)).join('')}}
                        </tbody>
                    </table>
                </div>
            `;
            return card;
        }}

        function createDriveRowHtml(groupId, item) {{
            const isKeeper = (item.action === 'KEEP');
            const isExcluded = excludedPaths.has(item.path);
            const isChecked = !isKeeper && !isExcluded;
            const fname = item.path.split('/').pop();

            return `
                <tr class="hover:bg-[#28292a]/50 transition">
                    <td class="py-2 px-2">
                        ${{isKeeper ? `<span class="text-[#81c995]">★</span>` : `
                            <input type="checkbox" onchange="toggleItemQuarantine('${{encodeURIComponent(item.path)}}', this.checked)"
                                   ${{isChecked ? 'checked' : ''}} class="rounded accent-[#8ab4f8] cursor-pointer">
                        `}}
                    </td>
                    <td class="py-2 px-2 font-medium text-white truncate max-w-[200px]" title="${{fname}}">${{fname}}</td>
                    <td class="py-2 px-2">
                        <span class="px-2 py-0.5 rounded-full text-[10px] ${{isKeeper ? 'bg-[#81c995]/15 text-[#81c995]' : 'bg-[#f28b82]/15 text-[#f28b82]'}}">
                            ${{item.action}}
                        </span>
                    </td>
                    <td class="py-2 px-2 text-[#c4c7c5]">${{(item.size_mb || 0).toFixed(2)}} MB</td>
                    <td class="py-2 px-2 text-[#8e918f] truncate max-w-[240px]" title="${{item.path}}">${{item.path}}</td>
                    <td class="py-2 px-2 text-right">
                        ${{!isKeeper ? `
                            <button onclick="setKeeperOverride(${{groupId}}, '${{encodeURIComponent(item.path)}}')"
                                    class="text-[#8ab4f8] hover:underline text-[11px] font-sans font-medium mr-2">
                                Make Keeper
                            </button>
                        ` : '<span class="text-[#8e918f] text-[10px]">Keeper</span>'}}
                    </td>
                </tr>
            `;
        }}

        function toggleItemSelection(encodedPath) {{
            const path = decodeURIComponent(encodedPath);
            if (excludedPaths.has(path)) {{
                excludedPaths.delete(path);
            }} else {{
                excludedPaths.add(path);
            }}
            renderCurrentPage();
            updateDockMetrics();
        }}

        function toggleItemQuarantine(encodedPath, isChecked) {{
            const path = decodeURIComponent(encodedPath);
            if (isChecked) {{
                excludedPaths.delete(path);
            }} else {{
                excludedPaths.add(path);
            }}
            updateDockMetrics();
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

        function applySelectionRule(rule) {{
            if (!currentSummary) return;
            if (rule === 'NONE') {{
                for (const item of currentSummary.groups) {{
                    if (item.action === 'DUPLICATE') excludedPaths.add(item.path);
                }}
            }} else if (rule === 'ALL') {{
                excludedPaths.clear();
            }}
            renderCurrentPage();
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
            document.getElementById('dockSelectedCount').innerText = `${{stagedCount.toLocaleString()}} duplicate files selected`;

            // Dim or elevate contextual bar
            const bar = document.getElementById('contextualActionBar');
            if (stagedCount === 0) {{
                bar.style.opacity = "0.7";
            }} else {{
                bar.style.opacity = "1";
            }}
        }}

        // Dialog Functions
        function openTrashDialog() {{
            document.getElementById('trashDialog').classList.remove('hidden');
        }}
        function closeTrashDialog() {{
            document.getElementById('trashDialog').classList.add('hidden');
        }}

        function openPermanentDeleteDialog() {{
            document.getElementById('permanentDeleteDialog').classList.remove('hidden');
        }}
        function closePermanentDeleteDialog() {{
            document.getElementById('permanentDeleteDialog').classList.add('hidden');
        }}

        function openQuarantineModal() {{
            document.getElementById('quarantineModal').classList.remove('hidden');
        }}
        function closeQuarantineModal() {{
            document.getElementById('quarantineModal').classList.add('hidden');
        }}

        async function executeConfirmedDelete(mode) {{
            if (mode === 'trash') closeTrashDialog();
            else closePermanentDeleteDialog();

            const selectedPaths = [];
            for (const item of currentSummary.groups) {{
                if (item.action === 'DUPLICATE' && !excludedPaths.has(item.path)) {{
                    selectedPaths.push(item.path);
                }}
            }}

            if (selectedPaths.length === 0) {{
                alert("No duplicate files are currently selected.");
                return;
            }}

            try {{
                const res = await fetch('/api/delete/execute', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        paths: selectedPaths,
                        mode: mode,
                        base_dir: currentSummary.scanned_paths || currentSummary.scanned_dir
                    }})
                }});
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || "Deletion failed");

                const freedMb = (data.total_bytes_freed / (1024 * 1024)).toFixed(2);
                alert(`[✓] Successfully processed ${{data.total_files_deleted}} files in ${{mode.toUpperCase()}} mode (${{freedMb}} MB freed).`);

                // Remove deleted items from currentSummary
                const deletedSet = new Set(data.items.map(it => it.original_path));
                currentSummary.groups = currentSummary.groups.filter(g => !deletedSet.has(g.path));
                currentSummary.wasted_bytes = Math.max(0, (currentSummary.wasted_bytes || 0) - data.total_bytes_freed);
                currentSummary.wasted_gb = currentSummary.wasted_bytes / (1024 * 1024 * 1024);

                loadSummaryState(currentSummary, `Deleted ${{data.total_files_deleted}} files (${{mode}}).`);
            }} catch (e) {{
                alert("Deletion error: " + e.message);
            }}
        }}

        async function executeConfirmedQuarantine() {{
            closeQuarantineModal();
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
                if (!res.ok) throw new Error(data.detail || "Quarantine failed");
                alert(`[✓] Successfully quarantined ${{data.total_files_moved}} files (${{(data.total_bytes_moved / (1024*1024)).toFixed(2)}} MB).`);
            }} catch (e) {{
                alert("Quarantine error: " + e.message);
            }}
        }}

        // Side-by-Side Comparison Modal
        function openComparisonLightbox(groupId) {{
            const cluster = allClusters.find(c => c.group_id === groupId);
            if (!cluster || !cluster.keeper || cluster.duplicates.length === 0) return;

            modalActiveCluster = cluster;
            modalActiveDupe = cluster.duplicates[0];

            document.getElementById('modalClusterTitle').innerText = `Cluster #${{cluster.group_id}} Side-by-Side Diff`;
            document.getElementById('modalClusterSubtitle').innerText = `${{cluster.items.length}} candidate files matching with ${{cluster.match_type}}`;

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
                keeperPreview.innerHTML = `<span class="text-xs font-mono text-[#8e918f] uppercase">${{keeper.path.split('.').pop()}} DOCUMENT</span>`;
            }}

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
                dupePreview.innerHTML = `<span class="text-xs font-mono text-[#8e918f] uppercase">${{dupe.path.split('.').pop()}} DOCUMENT</span>`;
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

            try {{
                const res = await fetch('/api/scan', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ paths: paths, enable_ml: true, threshold: threshold }})
                }});
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || "Scan failed");

                if (pollTimer) clearInterval(pollTimer);
                pollTimer = setInterval(pollScanStatus, 1000);
            }} catch (e) {{
                alert("Error: " + e.message);
                btn.disabled = false;
            }}
        }}

        async function pollScanStatus() {{
            try {{
                const res = await fetch('/api/status');
                const state = await res.json();
                if (state.status === "completed") {{
                    clearInterval(pollTimer);
                    pollTimer = null;
                    document.getElementById('scanBtn').disabled = false;
                    loadSummaryState(state.summary, state.message);
                }} else if (state.status === "failed") {{
                    clearInterval(pollTimer);
                    pollTimer = null;
                    document.getElementById('scanBtn').disabled = false;
                    alert("Scan failed: " + state.message);
                }}
            }} catch (e) {{
                console.error("Poll error:", e);
            }}
        }}
    </script>
</body>
</html>
"""
