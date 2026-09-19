"""
Clairvoy Web UI Component
Google Material Design 3 (M3) Storage Optimization & Photos Deduplication Studio.
Inspired by Google Photos, Google Drive, Google Files, and Google One.
100% offline, zero-dependency, ultra-minimal code with fluid Photos Grid, Drive List,
morphing Top Selection Bar, persistent Left-Bottom Storage Manager, Small/Medium/Large thumbnail controls,
real-time video keyframe previews, and native HTML5 video side-by-side playback.
"""

from clairvoy.core.config import VERSION


def get_index_html() -> str:
    """Renders the comprehensive Google Material Design 3 single-page dashboard."""
    return f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Clairvoy Photos | Google Storage & Multimodal Deduplication</title>
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
            padding: 7px 18px;
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
            padding: 7px 16px;
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
            padding: 7px 16px;
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

        /* Google Photos Circular Checkmark */
        .gp-check-circle {{
            width: 24px;
            height: 24px;
            border-radius: 50%;
            border: 2px solid rgba(255, 255, 255, 0.7);
            background: rgba(0, 0, 0, 0.45);
            backdrop-filter: blur(4px);
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
            cursor: pointer;
            user-select: none;
        }}
        .gp-check-circle:hover {{
            border-color: #ffffff;
            transform: scale(1.08);
        }}
        .gp-check-circle.checked {{
            background-color: #8ab4f8;
            border-color: #8ab4f8;
            opacity: 1 !important;
        }}
        .gp-check-circle svg {{
            opacity: 0;
            color: #131314;
            transition: opacity 0.1s ease;
        }}
        .gp-check-circle.checked svg {{
            opacity: 1;
        }}
    </style>
</head>
<body class="min-h-screen custom-scrollbar bg-[#131314] text-[#e3e3e3]">

    <!-- Google Photos Top App Bar (Morphs into Selection Bar when items are selected) -->
    <header id="topAppBar" class="sticky top-0 z-40 bg-[#1e1f20]/95 backdrop-blur-md border-b border-[#28292a] px-4 lg:px-8 py-2.5 transition-all">

        <!-- Default Header (Shown when 0 items selected) -->
        <div id="defaultHeader" class="max-w-7xl mx-auto flex items-center justify-between gap-3">
            <!-- Google Photos Logo & Brand -->
            <div class="flex items-center gap-3 flex-shrink-0">
                <!-- Google 4-Color Pinwheel -->
                <div class="relative w-7 h-7 flex items-center justify-center">
                    <svg class="w-7 h-7" viewBox="0 0 48 48" fill="none">
                        <path d="M24 12V24H12C12 17.37 17.37 12 24 12Z" fill="#4285F4"/>
                        <path d="M36 24H24V12C30.63 12 36 17.37 36 24Z" fill="#EA4335"/>
                        <path d="M24 36V24H36C36 30.63 30.63 36 24 36Z" fill="#FBBC05"/>
                        <path d="M12 24H24V36C17.37 36 12 30.63 12 24Z" fill="#34A853"/>
                    </svg>
                </div>
                <div class="flex items-baseline gap-2">
                    <span class="text-lg font-bold tracking-tight text-white flex items-center gap-1.5">
                        Clairvoy
                        <span class="text-xs font-semibold text-[#8ab4f8] bg-[#1a3860] px-2 py-0.5 rounded-full">Photos</span>
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
                           placeholder="Search duplicate photos, documents, filenames..."
                           class="w-full bg-transparent text-sm text-[#e3e3e3] placeholder-[#8e918f] focus:outline-none">
                    <button id="clearSearchBtn" onclick="clearSearch()" class="hidden text-[#8e918f] hover:text-white ml-2 text-sm">✕</button>
                </div>
            </div>

            <!-- Runs Selector & Scan Trigger -->
            <div class="flex items-center gap-2 flex-shrink-0">
                <!-- Past Runs Dropdown -->
                <div class="hidden sm:flex items-center bg-[#28292a] border border-[#3c4043] rounded-full px-3 py-1.5 text-xs text-[#c4c7c5]">
                    <span class="mr-1.5">📂</span>
                    <select id="runsDropdown" onchange="onRunSelected(this.value)" class="bg-transparent text-xs text-[#e3e3e3] focus:outline-none cursor-pointer max-w-[180px] truncate">
                        <option value="">Loading runs...</option>
                    </select>
                </div>

                <button onclick="toggleScanDrawer()" class="m3-button-secondary text-xs !py-1.5 !px-3">
                    <span>⚡</span> <span>Scan</span>
                </button>

                <button onclick="toggleShortcutsModal()" class="hidden md:inline-flex m3-button-secondary text-xs !py-1.5 !px-3 text-[#c4c7c5] hover:text-white" title="Keyboard Shortcuts (?)">
                    <span>⌨️</span> <span class="hidden lg:inline">Shortcuts</span>
                </button>

                <div class="w-2.5 h-2.5 rounded-full bg-[#81c995] animate-pulse" title="100% Offline & Local"></div>
            </div>
        </div>

        <!-- Google Photos Top Selection Bar (Morphs into view when >=1 item selected) -->
        <div id="selectionHeader" class="hidden max-w-7xl mx-auto flex items-center justify-between gap-4">
            <!-- Left: Deselect ✕ & Selected Counter -->
            <div class="flex items-center gap-4">
                <button onclick="applySelectionRule('NONE')" class="w-9 h-9 rounded-full hover:bg-white/10 flex items-center justify-center text-lg text-white font-bold transition" title="Clear selection">
                    ✕
                </button>
                <div class="flex items-baseline gap-2">
                    <span id="topSelectedCount" class="text-base font-bold text-white">0 selected</span>
                    <span id="topSelectedSpace" class="text-xs text-[#8ab4f8] font-mono">(0.000 GB)</span>
                </div>
            </div>

            <!-- Right: Bulk Action Buttons -->
            <div class="flex items-center gap-2 overflow-x-auto py-0.5">
                <button onclick="applySelectionRule('ALL')" class="m3-button-secondary !py-1.5 !px-3 text-xs">Select All</button>
                <button onclick="applySelectionRule('NONE')" class="m3-button-secondary !py-1.5 !px-3 text-xs">Clear</button>

                <button onclick="openTrashDialog()" class="m3-button-secondary !py-1.5 !px-3.5 text-xs text-[#8ab4f8] border-[#8ab4f8]/40 hover:bg-[#8ab4f8]/10" title="Safely move duplicates to .clairvoy_trash/">
                    <span>🗑️ Move to Trash</span>
                </button>

                <button onclick="openPermanentDeleteDialog()" class="m3-button-danger !py-1.5 !px-3.5 text-xs" title="Permanently unlink duplicate files">
                    <span>⚠️ Delete Permanently</span>
                </button>

                <button onclick="openQuarantineModal()" class="m3-button-secondary !py-1.5 !px-3.5 text-xs text-[#fdd663] border-[#fdd663]/40 hover:bg-[#fdd663]/10" title="Move to quarantine directory">
                    <span>📦 Quarantine</span>
                </button>

                <a id="downloadCsvBtn" href="/api/reports/csv" download class="m3-button-secondary !py-1.5 !px-3 text-xs" title="Export CSV Report">
                    <span>📄 CSV</span>
                </a>
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

    <!-- Main Google Photos Layout (Nav Rail + Fluid Workspace) -->
    <div class="max-w-7xl mx-auto px-4 lg:px-8 pt-6 pb-12 flex flex-col md:flex-row gap-6">

        <!-- Google Navigation Rail (Left Sidebar with Bottom Storage Card) -->
        <aside class="w-full md:w-64 flex-shrink-0 flex md:flex-col justify-between gap-5 pb-2 md:pb-0 md:sticky md:top-16 md:h-[calc(100vh-5.5rem)] overflow-y-auto pr-1">

            <!-- Left Navigation & Categories -->
            <div class="flex md:flex-col gap-1 w-full overflow-x-auto md:overflow-x-visible pb-1 md:pb-0">

                <!-- Section: Categories Header -->
                <div class="hidden md:flex items-center justify-between px-3 pt-1 pb-1.5 text-[11px] font-bold text-[#8e918f] uppercase tracking-wider">
                    <span>Categories</span>
                    <button id="sidebarClearAllBtn" onclick="setModalityCategory('ALL')" class="hidden text-[10px] text-[#8ab4f8] hover:underline font-mono" title="Clear category filter">
                        Clear ✕
                    </button>
                </div>

                <!-- Category 1: Photos -->
                <button onclick="setModalityCategory('PHOTO')" id="catBtn_PHOTO"
                        class="nav-rail-btn w-full flex items-center justify-between px-3.5 py-2.5 rounded-full text-xs font-semibold transition bg-[#1a3860] text-[#8ab4f8] group">
                    <div class="flex items-center gap-2.5 min-w-0">
                        <span class="text-base">🖼️</span>
                        <span class="truncate">Photos</span>
                    </div>
                    <div class="flex items-center gap-1.5 flex-shrink-0">
                        <span id="tabCount_PHOTO" class="text-[11px] font-mono px-2 py-0.5 rounded-full bg-black/40 text-[#c4c7c5]">0</span>
                        <span id="catCross_PHOTO" onclick="event.stopPropagation(); setModalityCategory('ALL');"
                              class="hidden text-xs font-bold text-[#8ab4f8] hover:text-white px-1 hover:bg-white/20 rounded-full" title="Clear filter">✕</span>
                    </div>
                </button>

                <!-- Category 2: Videos -->
                <button onclick="setModalityCategory('VIDEO')" id="catBtn_VIDEO"
                        class="nav-rail-btn w-full flex items-center justify-between px-3.5 py-2.5 rounded-full text-xs font-semibold transition hover:bg-[#28292a] text-[#c4c7c5] group">
                    <div class="flex items-center gap-2.5 min-w-0">
                        <span class="text-base">🎥</span>
                        <span class="truncate">Videos</span>
                    </div>
                    <div class="flex items-center gap-1.5 flex-shrink-0">
                        <span id="tabCount_VIDEO" class="text-[11px] font-mono px-2 py-0.5 rounded-full bg-black/40 text-[#c4c7c5]">0</span>
                        <span id="catCross_VIDEO" onclick="event.stopPropagation(); setModalityCategory('ALL');"
                              class="hidden text-xs font-bold text-[#8ab4f8] hover:text-white px-1 hover:bg-white/20 rounded-full" title="Clear filter">✕</span>
                    </div>
                </button>

                <!-- Category 3: Screenshots -->
                <button onclick="setModalityCategory('SCREENSHOT')" id="catBtn_SCREENSHOT"
                        class="nav-rail-btn w-full flex items-center justify-between px-3.5 py-2.5 rounded-full text-xs font-semibold transition hover:bg-[#28292a] text-[#c4c7c5] group">
                    <div class="flex items-center gap-2.5 min-w-0">
                        <span class="text-base">📸</span>
                        <span class="truncate">Screenshots</span>
                    </div>
                    <div class="flex items-center gap-1.5 flex-shrink-0">
                        <span id="tabCount_SCREENSHOT" class="text-[11px] font-mono px-2 py-0.5 rounded-full bg-black/40 text-[#c4c7c5]">0</span>
                        <span id="catCross_SCREENSHOT" onclick="event.stopPropagation(); setModalityCategory('ALL');"
                              class="hidden text-xs font-bold text-[#8ab4f8] hover:text-white px-1 hover:bg-white/20 rounded-full" title="Clear filter">✕</span>
                    </div>
                </button>

                <!-- Category 4: Documents -->
                <button onclick="setModalityCategory('DOCUMENT')" id="catBtn_DOCUMENT"
                        class="nav-rail-btn w-full flex items-center justify-between px-3.5 py-2.5 rounded-full text-xs font-semibold transition hover:bg-[#28292a] text-[#c4c7c5] group">
                    <div class="flex items-center gap-2.5 min-w-0">
                        <span class="text-base">📄</span>
                        <span class="truncate">Documents</span>
                    </div>
                    <div class="flex items-center gap-1.5 flex-shrink-0">
                        <span id="tabCount_DOCUMENT" class="text-[11px] font-mono px-2 py-0.5 rounded-full bg-black/40 text-[#c4c7c5]">0</span>
                        <span id="catCross_DOCUMENT" onclick="event.stopPropagation(); setModalityCategory('ALL');"
                              class="hidden text-xs font-bold text-[#8ab4f8] hover:text-white px-1 hover:bg-white/20 rounded-full" title="Clear filter">✕</span>
                    </div>
                </button>

                <!-- Category 5: Other Files -->
                <button onclick="setModalityCategory('FILE')" id="catBtn_FILE"
                        class="nav-rail-btn w-full flex items-center justify-between px-3.5 py-2.5 rounded-full text-xs font-semibold transition hover:bg-[#28292a] text-[#c4c7c5] group">
                    <div class="flex items-center gap-2.5 min-w-0">
                        <span class="text-base">📦</span>
                        <span class="truncate">Other Files</span>
                    </div>
                    <div class="flex items-center gap-1.5 flex-shrink-0">
                        <span id="tabCount_FILE" class="text-[11px] font-mono px-2 py-0.5 rounded-full bg-black/40 text-[#c4c7c5]">0</span>
                        <span id="catCross_FILE" onclick="event.stopPropagation(); setModalityCategory('ALL');"
                              class="hidden text-xs font-bold text-[#8ab4f8] hover:text-white px-1 hover:bg-white/20 rounded-full" title="Clear filter">✕</span>
                    </div>
                </button>

                <!-- Category 6: All Duplicates -->
                <button onclick="setModalityCategory('ALL')" id="catBtn_ALL"
                        class="nav-rail-btn w-full flex items-center justify-between px-3.5 py-2.5 rounded-full text-xs font-semibold transition hover:bg-[#28292a] text-[#c4c7c5] group">
                    <div class="flex items-center gap-2.5 min-w-0">
                        <span class="text-base">🌐</span>
                        <span class="truncate">All Duplicates</span>
                    </div>
                    <div class="flex items-center gap-1.5 flex-shrink-0">
                        <span id="tabCount_ALL" class="text-[11px] font-mono px-2 py-0.5 rounded-full bg-black/40 text-[#c4c7c5]">0</span>
                    </div>
                </button>

                <!-- Divider -->
                <div class="hidden md:block my-2 border-t border-[#28292a]"></div>

                <!-- Section: Tools & Views -->
                <div class="hidden md:block px-3 pt-1 pb-1 text-[11px] font-bold text-[#8e918f] uppercase tracking-wider">
                    Tools & Views
                </div>

                <button onclick="switchNavSection('DRIVE')" id="navBtn_DRIVE"
                        class="nav-rail-btn w-full flex items-center gap-3 px-3.5 py-2.5 rounded-full text-xs font-semibold transition hover:bg-[#28292a] text-[#c4c7c5]">
                    <span class="text-base">📁</span>
                    <span>Drive List</span>
                </button>
                <button onclick="switchNavSection('CLEANUP')" id="navBtn_CLEANUP"
                        class="nav-rail-btn w-full flex items-center gap-3 px-3.5 py-2.5 rounded-full text-xs font-semibold transition hover:bg-[#28292a] text-[#c4c7c5]">
                    <span class="text-base">🧹</span>
                    <span>Clean up space</span>
                </button>
                <button onclick="switchNavSection('TRASH')" id="navBtn_TRASH"
                        class="nav-rail-btn w-full flex items-center gap-3 px-3.5 py-2.5 rounded-full text-xs font-semibold transition hover:bg-[#28292a] text-[#c4c7c5]">
                    <span class="text-base">🗑️</span>
                    <span>Trash & Audit</span>
                </button>
            </div>

            <!-- Google Photos / Google Drive Storage Section (Bottom Left) -->
            <div class="m3-card p-4 border border-[#3c4043]/60 bg-[#1e1f20] w-full hidden md:block mt-auto shadow-lg">
                <div class="flex items-center justify-between mb-2">
                    <div class="flex items-center gap-2">
                        <span class="text-base">☁️</span>
                        <span class="text-xs font-bold text-white uppercase tracking-wider">Storage</span>
                    </div>
                    <span id="sideClusterCount" class="text-[10px] text-[#8e918f] font-mono">0 clusters</span>
                </div>

                <!-- Multi-Colored Storage Meter -->
                <div class="w-full bg-[#131314] rounded-full h-2 overflow-hidden flex border border-[#3c4043] mb-2.5">
                    <div id="sideSegPhoto" class="bg-[#8ab4f8] h-full transition-all duration-500" style="width: 0%;" title="Photos"></div>
                    <div id="sideSegScreenshot" class="bg-[#fdd663] h-full transition-all duration-500" style="width: 0%;" title="Screenshots"></div>
                    <div id="sideSegDocument" class="bg-[#81c995] h-full transition-all duration-500" style="width: 0%;" title="Documents"></div>
                    <div id="sideSegFile" class="bg-[#f28b82] h-full transition-all duration-500" style="width: 0%;" title="Large / Other Files"></div>
                </div>

                <!-- Recoverable Space Numbers -->
                <div class="text-xs text-white font-semibold flex items-baseline justify-between mb-0.5">
                    <span><span id="sideWastedGb" class="text-[#8ab4f8] text-sm font-bold">0.000</span> GB</span>
                    <span class="text-[10px] text-[#8e918f] font-mono">recoverable</span>
                </div>
                <div id="sideWastedMb" class="text-[10px] text-[#8e918f] font-mono truncate mb-3">0 MB wasted across duplicates</div>

                <!-- Category Mini-Breakdown -->
                <div class="space-y-1.5 text-[11px] text-[#c4c7c5] font-mono mb-3 pb-2.5 border-b border-[#28292a]">
                    <div class="flex justify-between items-center">
                        <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-[#8ab4f8]"></span> Photos & Videos</span>
                        <strong id="sideLegendPhoto" class="text-white">0</strong>
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-[#fdd663]"></span> Screenshots</span>
                        <strong id="sideLegendScreenshot" class="text-white">0</strong>
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-[#81c995]"></span> Documents</span>
                        <strong id="sideLegendDocument" class="text-white">0</strong>
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-[#f28b82]"></span> Other Files</span>
                        <strong id="sideLegendFile" class="text-white">0</strong>
                    </div>
                </div>

                <!-- Clean Up Space Button -->
                <button onclick="switchNavSection('CLEANUP')" class="w-full m3-button-secondary justify-center text-xs !py-1.5 hover:bg-[#303134]">
                    <span>🧹 Clean up space</span>
                </button>
            </div>
        </aside>

        <!-- Main Workspace -->
        <main class="flex-1 min-w-0">

            <!-- Google One Dedicated Clean-Up Section (Shown ONLY when Clean up tab is active) -->
            <section id="cleanupHeroCard" class="hidden m3-card p-6 mb-6 relative overflow-hidden">
                <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-5">
                    <div>
                        <div class="flex items-center gap-2 text-xs font-bold text-[#8ab4f8] uppercase tracking-wider mb-1">
                            <span>Google Storage Manager</span>
                        </div>
                        <h2 class="text-2xl md:text-3xl font-bold text-white tracking-tight flex items-baseline gap-2">
                            Clean up <span id="heroWastedGb" class="text-[#8ab4f8]">0.000</span> GB
                        </h2>
                        <p id="heroWastedMb" class="text-xs text-[#8e918f] font-mono mt-0.5">0 MB recoverable across duplicates</p>
                    </div>
                    <div class="text-right text-xs text-[#8e918f] font-mono">
                        <div id="heroClusterCount" class="font-bold text-[#e3e3e3]">0 duplicate clusters</div>
                        <div id="heroFileCount">0 files analyzed</div>
                    </div>
                </div>

                <!-- Google Multi-Colored Storage Meter -->
                <div class="w-full bg-[#131314] rounded-full h-3 overflow-hidden flex border border-[#3c4043] mb-4">
                    <div id="segPhoto" class="bg-[#8ab4f8] h-full transition-all duration-500" style="width: 0%;" title="Photos & Videos"></div>
                    <div id="segScreenshot" class="bg-[#fdd663] h-full transition-all duration-500" style="width: 0%;" title="Screenshots"></div>
                    <div id="segDocument" class="bg-[#81c995] h-full transition-all duration-500" style="width: 0%;" title="Documents"></div>
                    <div id="segFile" class="bg-[#f28b82] h-full transition-all duration-500" style="width: 0%;" title="Large / Other Files"></div>
                </div>

                <!-- Storage Legend -->
                <div class="flex flex-wrap gap-4 text-xs font-medium text-[#c4c7c5]">
                    <div class="flex items-center gap-1.5">
                        <span class="w-2.5 h-2.5 rounded-full bg-[#8ab4f8]"></span>
                        <span>Photos & Videos: <strong id="legendPhoto" class="text-white font-mono">0</strong></span>
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

            <!-- Smart Clean Recommendation Hero Banner (CleanMyMac / Gemini 2 Parity) -->
            <section id="smartCleanHero" class="hidden m3-card p-5 mb-5 bg-gradient-to-r from-[#1a3860]/40 via-[#1e1f20] to-[#1e1f20] border border-[#8ab4f8]/30 relative overflow-hidden shadow-xl">
                <div class="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
                    <div class="flex items-start gap-3.5">
                        <div class="w-11 h-11 rounded-2xl bg-[#1a3860] border border-[#8ab4f8]/30 flex items-center justify-center text-2xl flex-shrink-0 shadow-md">
                            ✨
                        </div>
                        <div>
                            <div class="flex items-center gap-2">
                                <span class="text-xs font-bold uppercase tracking-wider text-[#8ab4f8]">Smart Clean Recommendation</span>
                                <span id="smartCleanBadge" class="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#81c995]/20 text-[#81c995] font-bold">100% Safe</span>
                            </div>
                            <h3 class="text-lg md:text-xl font-bold text-white mt-0.5 flex items-baseline gap-2">
                                Reclaim <span id="smartCleanGb" class="text-[#8ab4f8]">0.00</span> GB of storage
                            </h3>
                            <p class="text-xs text-[#c4c7c5] mt-0.5 max-w-2xl leading-relaxed">
                                Best copy in each duplicate set is automatically kept. Safely clean redundant copies or customize selection rules.
                            </p>
                        </div>
                    </div>

                    <div class="flex flex-wrap items-center gap-2 flex-shrink-0 w-full lg:w-auto justify-end">
                        <select id="selectionRuleSelect" onchange="applySelectionPreset(this.value)" class="bg-[#202124] border border-[#3c4043] rounded-full px-3 py-1.5 text-xs text-[#c4c7c5] focus:outline-none cursor-pointer">
                            <option value="AUTO">Rule: Keep Best Copy (Auto)</option>
                            <option value="OLDEST">Rule: Keep Oldest File</option>
                            <option value="NEWEST">Rule: Keep Newest File</option>
                            <option value="SHORTEST_PATH">Rule: Keep Shortest Path</option>
                            <option value="ALL">Select All Duplicates</option>
                            <option value="NONE">Clear All Selections</option>
                        </select>

                        <button onclick="openTrashDialog()" class="m3-button-primary !py-1.5 !px-3.5 text-xs font-semibold shadow-md shadow-[#8ab4f8]/20 flex items-center gap-1.5">
                            <span>🗑️ Move to Trash</span>
                        </button>

                        <button onclick="openQuarantineModal()" class="m3-button-secondary !py-1.5 !px-3 text-xs text-[#fdd663] border-[#fdd663]/40 hover:bg-[#fdd663]/10">
                            <span>📦 Quarantine</span>
                        </button>
                    </div>
                </div>
            </section>

            <!-- Active Category Header & Gallery Controls -->
            <section class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-5 pb-1">
                <!-- Left: Active Category Breadcrumb & Filter Reset Cross Chip -->
                <div class="flex items-center gap-3">
                    <div class="flex items-center gap-2">
                        <span id="activeCategoryIcon" class="text-xl">🖼️</span>
                        <h2 id="activeCategoryTitle" class="text-base md:text-lg font-bold text-white tracking-tight">Photos</h2>
                        <span id="activeCategoryCount" class="text-xs text-[#8e918f] font-mono">(0 sets)</span>
                    </div>

                    <!-- Clear Filter Cross Chip (Shown when filtered to a specific category) -->
                    <button id="clearCategoryFilterChip" onclick="setModalityCategory('ALL')"
                            class="hidden items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-[#1a3860] text-[#8ab4f8] border border-[#8ab4f8]/30 hover:bg-[#8ab4f8]/20 transition cursor-pointer"
                            title="Reset filter to All Duplicates">
                        <span>Clear Filter</span>
                        <span class="font-bold text-xs leading-none">✕</span>
                    </button>
                </div>

                <!-- Right View Controls: Sort, Thumbnail/Icon Size, Mode Toggle -->
                <div class="flex items-center gap-2 self-end sm:self-auto flex-wrap">
                    <!-- Sort Dropdown -->
                    <select onchange="onSortOrderChange(this.value)"
                            class="bg-[#202124] border border-[#3c4043] rounded-full px-3 py-1.5 text-xs text-[#c4c7c5] focus:outline-none cursor-pointer">
                        <option value="SIZE_DESC">Largest Wasted</option>
                        <option value="DUPES_DESC">Most Duplicates</option>
                        <option value="SIMILARITY_DESC">Similarity Score</option>
                    </select>

                    <!-- Thumbnail / Icon Size Toggle (Small / Medium / Large) -->
                    <div class="flex items-center bg-[#202124] border border-[#3c4043] rounded-full p-0.5" title="Thumbnail / Icon Size">
                        <button onclick="setThumbnailSize('small')" id="sizeBtn_small"
                                class="px-2.5 py-1 rounded-full text-xs font-medium transition text-[#8e918f] hover:text-white"
                                title="Small Icons / Dense View">
                            Small
                        </button>
                        <button onclick="setThumbnailSize('medium')" id="sizeBtn_medium"
                                class="px-2.5 py-1 rounded-full text-xs font-medium transition bg-[#1a3860] text-[#8ab4f8]"
                                title="Medium Icons / Standard">
                            Medium
                        </button>
                        <button onclick="setThumbnailSize('large')" id="sizeBtn_large"
                                class="px-2.5 py-1 rounded-full text-xs font-medium transition text-[#8e918f] hover:text-white"
                                title="Large Icons / Big Previews">
                            Large
                        </button>
                    </div>

                    <!-- View Toggle Button (Photos Grid vs Drive List) -->
                    <div class="flex items-center bg-[#202124] border border-[#3c4043] rounded-full p-0.5">
                        <button onclick="setViewMode('grid')" id="viewModeGridBtn"
                                class="px-3 py-1 rounded-full text-xs font-medium transition bg-[#1a3860] text-[#8ab4f8]" title="Google Photos Grid View">
                            ▦ Photos
                        </button>
                        <button onclick="setViewMode('list')" id="viewModeListBtn"
                                class="px-3 py-1 rounded-full text-xs font-medium transition text-[#8e918f] hover:text-white" title="Google Drive List View">
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

            <!-- Dynamic Clusters Gallery (Google Photos Fluid Grid or Drive List) -->
            <div id="clustersGallery" class="space-y-8"></div>

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

    <!-- Google Photos Full-Screen Lightbox Viewer (Single Photo + Side-by-Side Diff) -->
    <div id="photoLightboxModal" class="hidden fixed inset-0 z-50 bg-black/95 backdrop-blur-xl flex flex-col">
        <!-- Top Lightbox Bar -->
        <div class="px-5 py-3 border-b border-white/10 flex items-center justify-between gap-4 bg-[#1e1f20]/80">
            <div class="flex items-center gap-3 min-w-0">
                <button onclick="closePhotoLightbox()" class="w-9 h-9 rounded-full hover:bg-white/10 flex items-center justify-center text-xl text-white transition" title="Back to gallery">
                    ←
                </button>
                <div class="min-w-0">
                    <div class="flex items-center gap-2">
                        <span id="lbClusterTitle" class="text-sm font-bold text-white">Cluster #1</span>
                        <span id="lbMatchType" class="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#1a3860] text-[#8ab4f8]">MATCH</span>
                    </div>
                    <p id="lbFileName" class="text-xs text-[#8e918f] font-mono truncate max-w-md">image.jpg</p>
                </div>
            </div>

            <div class="flex items-center gap-2 flex-shrink-0">
                <button id="lbMakeKeeperBtn" onclick="swapKeeperInLightbox()" class="m3-button-secondary text-xs !py-1.5 !px-3 text-[#8ab4f8]">
                    <span>★ Make Keeper</span>
                </button>
                <button onclick="toggleLightboxDiff()" id="lbDiffBtn" class="m3-button-secondary text-xs !py-1.5 !px-3">
                    <span>⇄ Side-by-Side</span>
                </button>
                <button onclick="toggleLightboxInfo()" id="lbInfoBtn" class="m3-button-secondary text-xs !py-1.5 !px-3" title="Toggle file details">
                    <span>ℹ️ Details</span>
                </button>
            </div>
        </div>

        <!-- Lightbox Content Area -->
        <div class="flex-1 min-h-0 flex overflow-hidden relative">
            <!-- Navigation Arrows -->
            <button onclick="navigateLightbox(-1)" id="lbPrevBtn"
                    class="absolute left-4 top-1/2 -translate-y-1/2 z-20 w-11 h-11 rounded-full bg-black/60 hover:bg-black/90 border border-white/20 text-white flex items-center justify-center text-2xl transition">
                ‹
            </button>
            <button onclick="navigateLightbox(1)" id="lbNextBtn"
                    class="absolute right-4 top-1/2 -translate-y-1/2 z-20 w-11 h-11 rounded-full bg-black/60 hover:bg-black/90 border border-white/20 text-white flex items-center justify-center text-2xl transition">
                ›
            </button>

            <!-- Single Photo / Video View -->
            <div id="lbSingleView" class="flex-1 flex items-center justify-center p-4 min-w-0">
                <div id="lbImageContainer" class="max-w-full max-h-[80vh] flex items-center justify-center w-full"></div>
            </div>

            <!-- Side-by-Side Diff View -->
            <div id="lbDiffView" class="hidden flex-1 grid grid-cols-1 md:grid-cols-2 gap-4 p-6 min-w-0 overflow-y-auto custom-scrollbar">
                <!-- Keeper Column -->
                <div class="bg-[#131314] rounded-2xl p-4 border border-[#81c995]/50 flex flex-col justify-between">
                    <div>
                        <div class="flex justify-between items-center mb-3">
                            <span class="text-xs font-bold bg-[#81c995]/20 text-[#81c995] px-2.5 py-1 rounded-full flex items-center gap-1">
                                <span>★</span> Designated Keeper (Preserved)
                            </span>
                            <span id="lbDiffKeeperCat" class="text-xs font-mono text-[#8e918f] uppercase">PHOTO</span>
                        </div>
                        <div id="lbDiffKeeperPreview" class="w-full h-72 rounded-xl bg-black flex items-center justify-center overflow-hidden mb-3 border border-[#28292a]"></div>
                        <div class="space-y-1.5 text-xs">
                            <div id="lbDiffKeeperName" class="font-bold text-white truncate">original.jpg</div>
                            <div id="lbDiffKeeperPath" class="text-[10px] text-[#8e918f] font-mono break-all">/path/to/original</div>
                            <div class="flex gap-4 font-mono text-[#c4c7c5] pt-1">
                                <span>Size: <strong id="lbDiffKeeperSize" class="text-white">0 MB</strong></span>
                                <span>Resolution: <strong id="lbDiffKeeperDim" class="text-white">N/A</strong></span>
                            </div>
                        </div>
                    </div>
                    <div class="mt-4 pt-3 border-t border-[#28292a]">
                        <span class="text-xs text-[#81c995] font-semibold flex items-center gap-1">✓ Safely preserved on disk</span>
                    </div>
                </div>

                <!-- Duplicate Candidate Column -->
                <div class="bg-[#131314] rounded-2xl p-4 border border-[#f28b82]/50 flex flex-col justify-between">
                    <div>
                        <div class="flex justify-between items-center mb-3">
                            <span class="text-xs font-bold bg-[#f28b82]/20 text-[#f28b82] px-2.5 py-1 rounded-full flex items-center gap-1">
                                <span>⌧</span> Redundant Duplicate
                            </span>
                            <span id="lbDiffDupeSim" class="text-xs font-mono text-[#fdd663]">100% Match</span>
                        </div>
                        <div id="lbDiffDupePreview" class="w-full h-72 rounded-xl bg-black flex items-center justify-center overflow-hidden mb-3 border border-[#28292a]"></div>
                        <div class="space-y-1.5 text-xs">
                            <div id="lbDiffDupeName" class="font-bold text-white truncate">duplicate.jpg</div>
                            <div id="lbDiffDupePath" class="text-[10px] text-[#8e918f] font-mono break-all">/path/to/dupe</div>
                            <div class="flex gap-4 font-mono text-[#c4c7c5] pt-1">
                                <span>Size: <strong id="lbDiffDupeSize" class="text-white">0 MB</strong></span>
                                <span>Resolution: <strong id="lbDiffDupeDim" class="text-white">N/A</strong></span>
                            </div>
                        </div>
                    </div>
                    <div class="mt-4 pt-3 border-t border-[#28292a] flex justify-between items-center">
                        <button onclick="swapKeeperInLightbox()" class="m3-button-secondary text-xs !py-1.5 !px-3 text-[#8ab4f8]">
                            <span>★ Promote to Keeper</span>
                        </button>
                    </div>
                </div>
            </div>

            <!-- Slide-in Details / Metadata Drawer -->
            <div id="lbInfoDrawer" class="hidden w-80 bg-[#1e1f20] border-l border-white/10 p-5 flex-shrink-0 overflow-y-auto custom-scrollbar">
                <div class="flex justify-between items-center mb-4">
                    <h4 class="text-sm font-bold text-white uppercase tracking-wider">File Details</h4>
                    <button onclick="toggleLightboxInfo()" class="text-sm text-[#8e918f] hover:text-white">✕</button>
                </div>
                <div class="space-y-4 text-xs font-mono">
                    <div>
                        <div class="text-[#8e918f] text-[10px] uppercase mb-0.5">Filename</div>
                        <div id="lbInfoName" class="text-white font-sans font-medium break-all">-</div>
                    </div>
                    <div>
                        <div class="text-[#8e918f] text-[10px] uppercase mb-0.5">Absolute Path</div>
                        <div id="lbInfoPath" class="text-[#c4c7c5] text-[11px] break-all">-</div>
                    </div>
                    <div class="grid grid-cols-2 gap-2">
                        <div>
                            <div class="text-[#8e918f] text-[10px] uppercase mb-0.5">File Size</div>
                            <div id="lbInfoSize" class="text-white">-</div>
                        </div>
                        <div>
                            <div class="text-[#8e918f] text-[10px] uppercase mb-0.5">Dimensions</div>
                            <div id="lbInfoDim" class="text-white">-</div>
                        </div>
                    </div>
                    <div class="grid grid-cols-2 gap-2">
                        <div>
                            <div class="text-[#8e918f] text-[10px] uppercase mb-0.5">Role</div>
                            <div id="lbInfoRole" class="text-[#81c995] font-semibold">-</div>
                        </div>
                        <div>
                            <div class="text-[#8e918f] text-[10px] uppercase mb-0.5">Similarity</div>
                            <div id="lbInfoSim" class="text-[#fdd663]">-</div>
                        </div>
                    </div>
                    <div>
                        <div class="text-[#8e918f] text-[10px] uppercase mb-0.5">Match Algorithm</div>
                        <div id="lbInfoAlgorithm" class="text-[#8ab4f8]">-</div>
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
                You can restore them back to their original locations at any time.
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

    <!-- Toast Notification Pill -->
    <div id="toastNotification"
         class="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-[#1e1f20]/95 text-white border border-white/20 backdrop-blur-xl px-5 py-2.5 rounded-full shadow-2xl text-xs font-semibold flex items-center gap-2.5 transition-all duration-300 pointer-events-none opacity-0 translate-y-4">
        <span>✓</span>
        <span>Notification message</span>
    </div>

    <!-- Keyboard Shortcuts Cheat Sheet Modal -->
    <div id="shortcutsModal" class="hidden fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
        <div class="bg-[#1e1f20] border border-[#3c4043] rounded-3xl max-w-md w-full p-6 shadow-2xl">
            <div class="flex items-center justify-between pb-3 mb-4 border-b border-[#28292a]">
                <div class="flex items-center gap-2">
                    <span class="text-lg">⌨️</span>
                    <h3 class="text-base font-bold text-white">Keyboard Shortcuts</h3>
                </div>
                <button onclick="toggleShortcutsModal()" class="text-[#8e918f] hover:text-white text-sm">✕</button>
            </div>
            <div class="space-y-3 text-xs">
                <div class="flex justify-between items-center py-1 border-b border-[#28292a]">
                    <span class="text-[#c4c7c5]">Open Lightbox / Compare</span>
                    <kbd class="px-2 py-1 bg-[#131314] rounded border border-white/10 font-mono text-white">Space / Enter</kbd>
                </div>
                <div class="flex justify-between items-center py-1 border-b border-[#28292a]">
                    <span class="text-[#c4c7c5]">Navigate Lightbox Items</span>
                    <kbd class="px-2 py-1 bg-[#131314] rounded border border-white/10 font-mono text-white">← / →</kbd>
                </div>
                <div class="flex justify-between items-center py-1 border-b border-[#28292a]">
                    <span class="text-[#c4c7c5]">Toggle Side-by-Side Diff</span>
                    <kbd class="px-2 py-1 bg-[#131314] rounded border border-white/10 font-mono text-white">Space / D</kbd>
                </div>
                <div class="flex justify-between items-center py-1 border-b border-[#28292a]">
                    <span class="text-[#c4c7c5]">Promote Current Item to Keeper</span>
                    <kbd class="px-2 py-1 bg-[#131314] rounded border border-white/10 font-mono text-[#81c995]">K</kbd>
                </div>
                <div class="flex justify-between items-center py-1 border-b border-[#28292a]">
                    <span class="text-[#c4c7c5]">Toggle Duplicate Selection</span>
                    <kbd class="px-2 py-1 bg-[#131314] rounded border border-white/10 font-mono text-[#8ab4f8]">X / Del</kbd>
                </div>
                <div class="flex justify-between items-center py-1 border-b border-[#28292a]">
                    <span class="text-[#c4c7c5]">Close Lightbox / Modals</span>
                    <kbd class="px-2 py-1 bg-[#131314] rounded border border-white/10 font-mono text-white">Esc</kbd>
                </div>
                <div class="flex justify-between items-center py-1">
                    <span class="text-[#c4c7c5]">Toggle Shortcuts Help</span>
                    <kbd class="px-2 py-1 bg-[#131314] rounded border border-white/10 font-mono text-white">?</kbd>
                </div>
            </div>
            <div class="mt-5 flex justify-end">
                <button onclick="toggleShortcutsModal()" class="m3-button-secondary text-xs">Close</button>
            </div>
        </div>
    </div>

    <!-- Client-Side JavaScript Engine -->
    <script>
        // State Management
        let currentSummary = null;
        let allClusters = [];
        let filteredClusters = [];
        let activeModality = 'PHOTO'; // Default to authentic Photos view
        let activeSortOrder = 'SIZE_DESC';
        let searchQuery = '';
        let currentPage = 1;
        let perPage = 25;
        let viewMode = 'grid'; // 'grid' (Photos) | 'list' (Drive)
        let thumbnailSize = 'medium'; // 'small' | 'medium' | 'large'
        let currentNav = 'PHOTOS'; // 'PHOTOS' | 'DRIVE' | 'CLEANUP' | 'TRASH'
        let pollTimer = null;

        // Tracks excluded file paths from batch actions (set of paths)
        let excludedPaths = new Set();

        // Lightbox state
        let lbCluster = null;
        let lbItemIndex = 0;
        let lbIsDiff = false;
        let lbIsInfoOpen = false;

        // Extension check helpers
        function isImageFile(path) {{
            const exts = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif', '.heic', '.psd'];
            return exts.some(e => path.toLowerCase().endsWith(e));
        }}

        function isVideoFile(path) {{
            const exts = ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.wmv', '.m4v', '.ts', '.mp'];
            return exts.some(e => path.toLowerCase().endsWith(e));
        }}

        function isMediaFile(path) {{
            return isImageFile(path) || isVideoFile(path);
        }}

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

            // Global keyboard navigation & shortcuts
            window.addEventListener('keydown', (e) => {{
                if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {{
                    return;
                }}

                const modal = document.getElementById('photoLightboxModal');
                const isLbOpen = modal && !modal.classList.contains('hidden');

                if (e.key === '?') {{
                    toggleShortcutsModal();
                    e.preventDefault();
                    return;
                }}

                if (isLbOpen) {{
                    if (e.key === 'Escape') {{
                        closePhotoLightbox();
                        e.preventDefault();
                    }} else if (e.key === 'ArrowLeft' || e.key === 'a' || e.key === 'A') {{
                        navigateLightbox(-1);
                        e.preventDefault();
                    }} else if (e.key === 'ArrowRight' || e.key === 'd' || e.key === 'D') {{
                        navigateLightbox(1);
                        e.preventDefault();
                    }} else if (e.key === ' ' || e.key === 'Spacebar') {{
                        toggleLightboxDiff();
                        e.preventDefault();
                    }} else if (e.key === 'k' || e.key === 'K') {{
                        swapKeeperInLightbox();
                        e.preventDefault();
                    }} else if (e.key === 'x' || e.key === 'X' || e.key === 'Delete') {{
                        if (lbCluster && lbCluster.items[lbItemIndex]) {{
                            const cur = lbCluster.items[lbItemIndex];
                            if (cur.action !== 'KEEP') {{
                                toggleItemSelection(encodeURIComponent(cur.path));
                                showToast(excludedPaths.has(cur.path) ? "Item excluded from cleaning." : "Item marked for cleaning.", "🗑️");
                            }}
                        }}
                        e.preventDefault();
                    }} else if (e.key === 'i' || e.key === 'I') {{
                        toggleLightboxInfo();
                        e.preventDefault();
                    }}
                }} else {{
                    if (e.key === 'Escape') {{
                        closeTrashDialog();
                        closePermanentDeleteDialog();
                        closeQuarantineModal();
                        const scModal = document.getElementById('shortcutsModal');
                        if (scModal && !scModal.classList.contains('hidden')) toggleShortcutsModal();
                        const scDrawer = document.getElementById('scanDrawer');
                        if (scDrawer && !scDrawer.classList.contains('hidden')) toggleScanDrawer();
                    }} else if (e.key === 'ArrowLeft') {{
                        if (currentPage > 1) changePage(currentPage - 1);
                    }} else if (e.key === 'ArrowRight') {{
                        const totalPages = Math.max(1, Math.ceil(filteredClusters.length / perPage));
                        if (currentPage < totalPages) changePage(currentPage + 1);
                    }}
                }}
            }});
        }});

        function showToast(msg, icon = '✓') {{
            const toast = document.getElementById('toastNotification');
            if (!toast) return;
            toast.innerHTML = `<span class="text-sm">${{icon}}</span> <span>${{msg}}</span>`;
            toast.classList.remove('opacity-0', 'translate-y-4');
            toast.classList.add('opacity-100', 'translate-y-0');
            if (window._toastTimer) clearTimeout(window._toastTimer);
            window._toastTimer = setTimeout(() => {{
                toast.classList.add('opacity-0', 'translate-y-4');
                toast.classList.remove('opacity-100', 'translate-y-0');
            }}, 2600);
        }}

        function toggleShortcutsModal() {{
            const m = document.getElementById('shortcutsModal');
            if (m) m.classList.toggle('hidden');
        }}

        function applySelectionPreset(rule) {{
            if (!currentSummary || !allClusters || allClusters.length === 0) return;

            if (rule === 'ALL') {{
                excludedPaths.clear();
                showToast("All duplicate copies selected for removal.", "🗑️");
            }} else if (rule === 'NONE') {{
                for (const c of allClusters) {{
                    for (const d of c.duplicates) {{
                        excludedPaths.add(d.path);
                    }}
                }}
                showToast("All selections cleared.", "✕");
            }} else if (rule === 'AUTO') {{
                excludedPaths.clear();
                showToast("Reset to Best Copy recommendation.", "✨");
            }} else if (rule === 'OLDEST' || rule === 'NEWEST' || rule === 'SHORTEST_PATH') {{
                for (const c of allClusters) {{
                    let best = c.items[0];
                    if (rule === 'SHORTEST_PATH') {{
                        best = [...c.items].sort((a, b) => a.path.length - b.path.length)[0];
                    }} else if (rule === 'OLDEST') {{
                        best = [...c.items].sort((a, b) => (a.mtime || 0) - (b.mtime || 0))[0];
                    }} else if (rule === 'NEWEST') {{
                        best = [...c.items].sort((a, b) => (b.mtime || 0) - (a.mtime || 0))[0];
                    }}
                    for (const it of c.items) {{
                        it.action = (it.path === best.path) ? 'KEEP' : 'DUPLICATE';
                    }}
                    c.keeper = best;
                    c.duplicates = c.items.filter(it => it.path !== best.path);
                }}
                excludedPaths.clear();
                const ruleName = rule === 'SHORTEST_PATH' ? 'Shortest Path' : (rule === 'OLDEST' ? 'Oldest Copy' : 'Newest Copy');
                showToast(`Auto-Rule applied: Keep ${{ruleName}}.`, "⚡");
            }}

            renderCurrentPage();
            updateTopSelectionBar();
        }}

        function toggleScanDrawer() {{
            document.getElementById('scanDrawer').classList.toggle('hidden');
        }}

        function setViewMode(mode) {{
            viewMode = mode;
            const gridBtn = document.getElementById('viewModeGridBtn');
            const listBtn = document.getElementById('viewModeListBtn');
            if (mode === 'grid') {{
                gridBtn.className = "px-3 py-1 rounded-full text-xs font-medium transition bg-[#1a3860] text-[#8ab4f8]";
                listBtn.className = "px-3 py-1 rounded-full text-xs font-medium transition text-[#8e918f] hover:text-white";
            }} else {{
                listBtn.className = "px-3 py-1 rounded-full text-xs font-medium transition bg-[#1a3860] text-[#8ab4f8]";
                gridBtn.className = "px-3 py-1 rounded-full text-xs font-medium transition text-[#8e918f] hover:text-white";
            }}
            renderCurrentPage();
        }}

        function setThumbnailSize(size) {{
            thumbnailSize = size;
            ['small', 'medium', 'large'].forEach(s => {{
                const btn = document.getElementById('sizeBtn_' + s);
                if (btn) {{
                    if (s === size) {{
                        btn.className = "px-2.5 py-1 rounded-full text-xs font-medium transition bg-[#1a3860] text-[#8ab4f8]";
                    }} else {{
                        btn.className = "px-2.5 py-1 rounded-full text-xs font-medium transition text-[#8e918f] hover:text-white";
                    }}
                }}
            }});
            renderCurrentPage();
        }}

        function switchNavSection(sec) {{
            currentNav = sec;
            const hero = document.getElementById('cleanupHeroCard');
            const gallery = document.getElementById('clustersGallery');

            // Unhighlight all category buttons and hide their crosses
            const categories = ['PHOTO', 'VIDEO', 'SCREENSHOT', 'DOCUMENT', 'FILE', 'ALL'];
            categories.forEach(c => {{
                const btn = document.getElementById('catBtn_' + c);
                const cross = document.getElementById('catCross_' + c);
                if (btn) btn.className = "nav-rail-btn w-full flex items-center justify-between px-3.5 py-2.5 rounded-full text-xs font-semibold transition hover:bg-[#28292a] text-[#c4c7c5] group";
                if (cross) cross.classList.add('hidden');
            }});

            const chipCross = document.getElementById('clearCategoryFilterChip');
            if (chipCross) {{
                chipCross.classList.add('hidden');
                chipCross.classList.remove('flex');
            }}
            const sideClearBtn = document.getElementById('sidebarClearAllBtn');
            if (sideClearBtn) sideClearBtn.classList.add('hidden');

            // Update tools buttons in sidebar
            ['DRIVE', 'CLEANUP', 'TRASH'].forEach(s => {{
                const btn = document.getElementById('navBtn_' + s);
                if (btn) {{
                    if (s === sec) {{
                        btn.className = "nav-rail-btn w-full flex items-center gap-3 px-3.5 py-2.5 rounded-full text-xs font-semibold transition bg-[#1a3860] text-[#8ab4f8]";
                    }} else {{
                        btn.className = "nav-rail-btn w-full flex items-center gap-3 px-3.5 py-2.5 rounded-full text-xs font-semibold transition hover:bg-[#28292a] text-[#c4c7c5]";
                    }}
                }}
            }});

            const smartHero = document.getElementById('smartCleanHero');
            if (sec === 'CLEANUP') {{
                if (hero) hero.classList.remove('hidden');
                if (smartHero && currentSummary && (currentSummary.wasted_gb || 0) > 0) smartHero.classList.remove('hidden');
                if (gallery) gallery.classList.remove('hidden');
                activeModality = 'ALL';
                currentPage = 1;
                applyFiltersAndSort();
            }} else if (sec === 'DRIVE') {{
                if (hero) hero.classList.add('hidden');
                if (smartHero && currentSummary && (currentSummary.wasted_gb || 0) > 0) smartHero.classList.remove('hidden');
                if (gallery) gallery.classList.remove('hidden');
                setViewMode('list');
            }} else if (sec === 'TRASH') {{
                if (hero) hero.classList.add('hidden');
                if (smartHero) smartHero.classList.add('hidden');
                renderTrashSection();
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

            // Enrich records with video categorization if marked as generic file
            for (const item of (summary.groups || [])) {{
                if (isVideoFile(item.path) && (!item.category || item.category === 'FILE')) {{
                    item.category = 'VIDEO';
                }}
            }}

            allClusters = groupRecordsIntoClusters(summary.groups || []);
            renderHeroStorageMeter(summary);
            renderModalityTabCounts(summary);

            // Default to PHOTO tab when in Photos view
            if (currentNav === 'PHOTOS') {{
                setModalityTab('PHOTO');
            }} else {{
                applyFiltersAndSort();
            }}
            updateTopSelectionBar();
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
            const wastedGbStr = (summary.wasted_gb || 0).toFixed(3);
            const wastedMbStr = `${{(summary.wasted_mb || 0).toLocaleString()}} MB recoverable across duplicates`;
            const fileCountStr = `${{(summary.total_files_scanned || 0).toLocaleString()}} files analyzed`;
            const clusterCountStr = `${{(summary.total_duplicate_groups || 0).toLocaleString()}} clusters`;

            // Update Top Clean-up Hero (when visible)
            const heroGb = document.getElementById('heroWastedGb');
            if (heroGb) heroGb.innerText = wastedGbStr;
            const heroMb = document.getElementById('heroWastedMb');
            if (heroMb) heroMb.innerText = wastedMbStr;
            const heroFiles = document.getElementById('heroFileCount');
            if (heroFiles) heroFiles.innerText = fileCountStr;
            const heroClusters = document.getElementById('heroClusterCount');
            if (heroClusters) heroClusters.innerText = clusterCountStr;

            // Update Left-Bottom Persistent Sidebar Storage Card (Google Photos / Drive style)
            const sideGb = document.getElementById('sideWastedGb');
            if (sideGb) sideGb.innerText = wastedGbStr;
            const sideMb = document.getElementById('sideWastedMb');
            if (sideMb) sideMb.innerText = wastedMbStr;
            const sideClusters = document.getElementById('sideClusterCount');
            if (sideClusters) sideClusters.innerText = clusterCountStr;

            // Update Smart Clean Recommendation Banner
            const smartHero = document.getElementById('smartCleanHero');
            if (smartHero) {{
                if ((summary.wasted_gb || 0) > 0 && currentNav !== 'TRASH') {{
                    smartHero.classList.remove('hidden');
                    const scGb = document.getElementById('smartCleanGb');
                    if (scGb) scGb.innerText = (summary.wasted_gb || 0).toFixed(2);
                }} else {{
                    smartHero.classList.add('hidden');
                }}
            }}

            const cb = summary.category_breakdown || {{}};
            const totalDupes = Math.max(1, (summary.groups ? summary.groups.filter(g => g.action === 'DUPLICATE').length : 1));
            const pPhoto = (((cb.PHOTO || 0) + (cb.VIDEO || 0)) / totalDupes) * 100;
            const pScreens = ((cb.SCREENSHOT || 0) / totalDupes) * 100;
            const pDoc = ((cb.DOCUMENT || 0) / totalDupes) * 100;
            const pFile = Math.max(0, 100 - (pPhoto + pScreens + pDoc));

            // Meters
            ['segPhoto', 'sideSegPhoto'].forEach(id => {{
                const el = document.getElementById(id);
                if (el) el.style.width = pPhoto + '%';
            }});
            ['segScreenshot', 'sideSegScreenshot'].forEach(id => {{
                const el = document.getElementById(id);
                if (el) el.style.width = pScreens + '%';
            }});
            ['segDocument', 'sideSegDocument'].forEach(id => {{
                const el = document.getElementById(id);
                if (el) el.style.width = pDoc + '%';
            }});
            ['segFile', 'sideSegFile'].forEach(id => {{
                const el = document.getElementById(id);
                if (el) el.style.width = pFile + '%';
            }});

            // Legend Numbers
            const photoCount = `${{((cb.PHOTO || 0) + (cb.VIDEO || 0)).toLocaleString()}} files`;
            const screenCount = `${{(cb.SCREENSHOT || 0).toLocaleString()}} files`;
            const docCount = `${{(cb.DOCUMENT || 0).toLocaleString()}} files`;
            const fileCount = `${{(cb.FILE || 0).toLocaleString()}} files`;

            ['legendPhoto', 'sideLegendPhoto'].forEach(id => {{
                const el = document.getElementById(id);
                if (el) el.innerText = photoCount;
            }});
            ['legendScreenshot', 'sideLegendScreenshot'].forEach(id => {{
                const el = document.getElementById(id);
                if (el) el.innerText = screenCount;
            }});
            ['legendDocument', 'sideLegendDocument'].forEach(id => {{
                const el = document.getElementById(id);
                if (el) el.innerText = docCount;
            }});
            ['legendFile', 'sideLegendFile'].forEach(id => {{
                const el = document.getElementById(id);
                if (el) el.innerText = fileCount;
            }});
        }}

        function renderModalityTabCounts(summary) {{
            const total = allClusters.length;
            let photoCount = 0;
            let videoCount = 0;
            let screenCount = 0;
            let docCount = 0;
            let fileCount = 0;

            for (const c of allClusters) {{
                const hasPhoto = c.items.some(i => i.category === 'PHOTO' || isImageFile(i.path));
                const hasVideo = c.items.some(i => i.category === 'VIDEO' || isVideoFile(i.path));
                const hasScreen = c.items.some(i => i.category === 'SCREENSHOT');
                const hasDoc = c.items.some(i => i.category === 'DOCUMENT');

                if (hasPhoto) photoCount++;
                if (hasVideo) videoCount++;
                if (hasScreen) screenCount++;
                if (hasDoc) docCount++;
                if (!hasPhoto && !hasVideo && !hasScreen && !hasDoc) fileCount++;
            }}

            document.getElementById('tabCount_ALL').innerText = total.toLocaleString();
            document.getElementById('tabCount_PHOTO').innerText = photoCount.toLocaleString();
            document.getElementById('tabCount_VIDEO').innerText = videoCount.toLocaleString();
            document.getElementById('tabCount_SCREENSHOT').innerText = screenCount.toLocaleString();
            document.getElementById('tabCount_DOCUMENT').innerText = docCount.toLocaleString();
            document.getElementById('tabCount_FILE').innerText = fileCount.toLocaleString();
        }}

        function setModalityCategory(cat) {{
            activeModality = cat;
            currentNav = 'PHOTOS';

            // Reset and update category buttons in left sidebar
            const categories = ['PHOTO', 'VIDEO', 'SCREENSHOT', 'DOCUMENT', 'FILE', 'ALL'];
            categories.forEach(c => {{
                const btn = document.getElementById('catBtn_' + c);
                const cross = document.getElementById('catCross_' + c);
                if (btn) {{
                    if (c === cat) {{
                        btn.className = "nav-rail-btn w-full flex items-center justify-between px-3.5 py-2.5 rounded-full text-xs font-semibold transition bg-[#1a3860] text-[#8ab4f8] group";
                    }} else {{
                        btn.className = "nav-rail-btn w-full flex items-center justify-between px-3.5 py-2.5 rounded-full text-xs font-semibold transition hover:bg-[#28292a] text-[#c4c7c5] group";
                    }}
                }}
                if (cross) {{
                    // Show cross ✕ on active category if not 'ALL'
                    if (c === cat && cat !== 'ALL') {{
                        cross.classList.remove('hidden');
                    }} else {{
                        cross.classList.add('hidden');
                    }}
                }}
            }});

            // Reset tools buttons in sidebar
            ['DRIVE', 'CLEANUP', 'TRASH'].forEach(s => {{
                const b = document.getElementById('navBtn_' + s);
                if (b) b.className = "nav-rail-btn w-full flex items-center gap-3 px-3.5 py-2.5 rounded-full text-xs font-semibold transition hover:bg-[#28292a] text-[#c4c7c5]";
            }});

            // Update top bar breadcrumb & filter cross chip
            const catMeta = {{
                'PHOTO': {{ icon: '🖼️', title: 'Photos' }},
                'VIDEO': {{ icon: '🎥', title: 'Videos' }},
                'SCREENSHOT': {{ icon: '📸', title: 'Screenshots' }},
                'DOCUMENT': {{ icon: '📄', title: 'Documents' }},
                'FILE': {{ icon: '📦', title: 'Other Files' }},
                'ALL': {{ icon: '🌐', title: 'All Duplicates' }}
            }};

            const meta = catMeta[cat] || catMeta['ALL'];
            const iconEl = document.getElementById('activeCategoryIcon');
            if (iconEl) iconEl.innerText = meta.icon;
            const titleEl = document.getElementById('activeCategoryTitle');
            if (titleEl) titleEl.innerText = meta.title;

            const chipCross = document.getElementById('clearCategoryFilterChip');
            if (chipCross) {{
                if (cat !== 'ALL') {{
                    chipCross.classList.remove('hidden');
                    chipCross.classList.add('flex');
                }} else {{
                    chipCross.classList.add('hidden');
                    chipCross.classList.remove('flex');
                }}
            }}

            const sideClearBtn = document.getElementById('sidebarClearAllBtn');
            if (sideClearBtn) {{
                if (cat !== 'ALL') {{
                    sideClearBtn.classList.remove('hidden');
                }} else {{
                    sideClearBtn.classList.add('hidden');
                }}
            }}

            // Restore gallery view if coming from cleanup or trash
            const hero = document.getElementById('cleanupHeroCard');
            if (hero) hero.classList.add('hidden');
            const gallery = document.getElementById('clustersGallery');
            if (gallery) gallery.classList.remove('hidden');

            currentPage = 1;
            applyFiltersAndSort();
        }}

        // Backward compatibility
        function setModalityTab(tab) {{
            setModalityCategory(tab);
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
                if (activeModality === 'PHOTO') {{
                    const matches = c.items.some(i => i.category === 'PHOTO' || isImageFile(i.path));
                    if (!matches) return false;
                }} else if (activeModality === 'VIDEO') {{
                    const matches = c.items.some(i => i.category === 'VIDEO' || isVideoFile(i.path));
                    if (!matches) return false;
                }} else if (activeModality !== 'ALL') {{
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

            const countEl = document.getElementById('activeCategoryCount');
            if (countEl) {{
                countEl.innerText = `(${{filteredClusters.length.toLocaleString()}} sets)`;
            }}

            renderCurrentPage();
        }}

        function renderCurrentPage() {{
            if (currentNav === 'TRASH') return;

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

        // Authentic Google Photos Duplicate Set Card (Cohesive M3 Card with Primary File, Path, Badges & 1-Click Clean)
        function createGooglePhotosCard(cluster) {{
            const card = document.createElement('div');
            card.className = "m3-card p-4 sm:p-5 border border-[#28292a] hover:border-[#3c4043] transition-all duration-200 bg-[#1e1f20]/90 shadow-md";

            const wastedMb = (cluster.totalWastedBytes / (1024 * 1024)).toFixed(2);
            const allDupesSelected = cluster.duplicates.length > 0 && cluster.duplicates.every(d => !excludedPaths.has(d.path));
            const representative = cluster.keeper || cluster.items[0];
            const primaryName = representative.path.split('/').pop();
            const parentDir = representative.path.substring(0, representative.path.lastIndexOf('/'));

            // Determine Grid Column classes based on thumbnailSize
            let gridColsClass = "grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3";
            if (thumbnailSize === 'small') {{
                gridColsClass = "grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 xl:grid-cols-10 gap-2";
            }} else if (thumbnailSize === 'large') {{
                gridColsClass = "grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-5";
            }}

            card.innerHTML = `
                <!-- Cluster Header: Primary filename, path context, badges, 1-click clean & diff -->
                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 mb-3 border-b border-[#28292a]">
                    <div class="flex items-center gap-3 min-w-0">
                        <div onclick="toggleClusterSelection(${{cluster.group_id}}, event)"
                             class="gp-check-circle ${{allDupesSelected ? 'checked' : ''}} flex-shrink-0"
                             title="${{allDupesSelected ? 'Deselect cluster' : 'Mark duplicates for cleaning and keep best copy'}}">
                            <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <div class="min-w-0">
                            <div class="flex items-center gap-2 flex-wrap">
                                <span class="text-sm font-bold text-white truncate max-w-sm sm:max-w-md" title="${{primaryName}}">${{primaryName}}</span>
                                <span class="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-[#1a3860] text-[#8ab4f8]">${{cluster.match_type}}</span>
                                <span class="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-[#81c995]/15 text-[#81c995]">${{wastedMb}} MB wasted</span>
                            </div>
                            <div class="text-[11px] text-[#8e918f] font-mono truncate mt-0.5" title="${{parentDir}}">
                                📁 ${{parentDir}} • ${{cluster.items.length}} copies (${{cluster.duplicates.length}} duplicate${{cluster.duplicates.length === 1 ? '' : 's'}})
                            </div>
                        </div>
                    </div>

                    <!-- Cluster Actions: 1-Click Clean & Compare -->
                    <div class="flex items-center gap-2 flex-shrink-0 self-end sm:self-auto">
                        <button onclick="toggleClusterSelection(${{cluster.group_id}}, event)"
                                class="m3-button-secondary text-xs !py-1 !px-3 ${{allDupesSelected ? 'text-[#8ab4f8] border-[#8ab4f8]/40' : ''}}"
                                title="${{allDupesSelected ? 'Deselect duplicates' : 'Keep designated best copy and mark duplicates for removal'}}">
                            <span>${{allDupesSelected ? '✓ Clean Ready' : '★ Keep Best & Clean Rest'}}</span>
                        </button>
                        <button onclick="openPhotoLightbox(${{cluster.group_id}}, '${{encodeURIComponent(cluster.items[0].path)}}')"
                                class="m3-button-secondary text-xs !py-1 !px-3 hover:text-[#8ab4f8]">
                            <span>⇄ Compare Diff</span>
                        </button>
                    </div>
                </div>

                <!-- Fluid Edge-to-Edge Photo Grid -->
                <div class="grid ${{gridColsClass}}">
                    ${{cluster.items.map((item, idx) => createPhotoTileHtml(cluster.group_id, item, idx)).join('')}}
                </div>
            `;
            return card;
        }}

        function createPhotoTileHtml(groupId, item, idx) {{
            const isKeeper = (item.action === 'KEEP');
            const isExcluded = excludedPaths.has(item.path);
            const isChecked = !isKeeper && !isExcluded;
            const isVideo = isVideoFile(item.path);
            const isMedia = isMediaFile(item.path);

            const fname = item.path.split('/').pop();
            const parentDir = item.path.substring(0, item.path.lastIndexOf('/'));
            const sizeStr = `${{(item.size_mb || 0).toFixed(2)}} MB`;
            const dimStr = item.dimensions ? `${{item.dimensions[0]}}×${{item.dimensions[1]}}` : '';

            // Render according to thumbnailSize: 'small' | 'medium' | 'large'
            if (thumbnailSize === 'small') {{
                // Small Icons: compact dense tiles
                return `
                    <div onclick="openPhotoLightbox(${{groupId}}, '${{encodeURIComponent(item.path)}}')"
                         class="group relative aspect-square rounded-xl overflow-hidden cursor-pointer bg-[#1e1f20] border ${{isKeeper ? 'border-[#81c995] shadow' : 'border-white/10'}} transition duration-200 hover:border-white/40">

                        ${{isMedia ? `
                            <img src="/api/thumbnail?path=${{encodeURIComponent(item.path)}}"
                                 class="w-full h-full object-cover transition-transform duration-200 group-hover:scale-105"
                                 loading="lazy" alt="${{fname}}"
                                 onerror="this.parentElement.querySelector('.fallback-thumb').classList.remove('hidden'); this.remove();">
                            <div class="fallback-thumb hidden w-full h-full flex items-center justify-center bg-[#131314] text-[#8e918f]">
                                <span class="text-xs">${{isVideo ? '🎥' : '🖼️'}}</span>
                            </div>
                        ` : `
                            <div class="w-full h-full flex flex-col items-center justify-center bg-[#131314] text-[#8e918f] p-1 text-center">
                                <span class="text-base mb-0.5">📄</span>
                                <span class="text-[9px] font-mono truncate max-w-full text-white">${{fname.split('.').pop() || 'DOC'}}</span>
                            </div>
                        `}}

                        <!-- Gradient -->
                        <div class="absolute inset-x-0 bottom-0 h-10 bg-gradient-to-t from-black/85 to-transparent pointer-events-none z-10"></div>

                        <!-- Top-Left Mini Checkmark -->
                        <div class="absolute top-1.5 left-1.5 z-20">
                            ${{isKeeper ? `
                                <span class="text-[9px] font-bold text-[#131314] bg-[#81c995] px-1.5 py-0.2 rounded-full shadow">★</span>
                            ` : `
                                <div onclick="toggleItemSelection('${{encodeURIComponent(item.path)}}', event)"
                                     class="gp-check-circle !w-4 !h-4 ${{isChecked ? 'checked' : 'opacity-0 group-hover:opacity-100'}}">
                                    <svg class="w-2.5 h-2.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                                        <polyline points="20 6 9 17 4 12"></polyline>
                                    </svg>
                                </div>
                            `}}
                        </div>

                        ${{isVideo ? `
                            <div class="absolute bottom-1 right-1 z-20">
                                <span class="text-[8px] bg-black/80 text-white px-1 rounded font-mono">▶</span>
                            </div>
                        ` : ''}}

                        <!-- Bottom Minimal Size -->
                        <div class="absolute bottom-1 inset-x-1.5 z-20 text-[9px] text-[#c4c7c5] font-mono truncate">
                            ${{sizeStr}}
                        </div>
                    </div>
                `;
            }}

            if (thumbnailSize === 'large') {{
                // Large Icons / Previews: spacious, rich high-res card with full details
                return `
                    <div onclick="openPhotoLightbox(${{groupId}}, '${{encodeURIComponent(item.path)}}')"
                         class="group relative aspect-square rounded-3xl overflow-hidden cursor-pointer bg-[#1e1f20] border-2 ${{isKeeper ? 'border-[#81c995] shadow-lg shadow-[#81c995]/15' : 'border-white/10'}} transition duration-300 hover:border-white/40">

                        ${{isMedia ? `
                            <img src="/api/thumbnail?path=${{encodeURIComponent(item.path)}}"
                                 class="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                                 loading="lazy" alt="${{fname}}"
                                 onerror="this.parentElement.querySelector('.fallback-thumb').classList.remove('hidden'); this.remove();">
                            <div class="fallback-thumb hidden w-full h-full flex flex-col items-center justify-center bg-[#131314] text-[#8e918f]">
                                <span class="text-4xl mb-2">${{isVideo ? '🎥' : '🖼️'}}</span>
                                <span class="text-xs font-mono uppercase">${{isVideo ? 'Video File' : 'Image File'}}</span>
                            </div>
                        ` : `
                            <div class="w-full h-full flex flex-col items-center justify-center bg-[#131314] text-[#8e918f] p-6 text-center">
                                <span class="text-5xl mb-3">📄</span>
                                <span class="text-sm font-bold text-white truncate max-w-full">${{fname}}</span>
                                <span class="text-xs text-[#8ab4f8] font-mono mt-1">${{sizeStr}}</span>
                            </div>
                        `}}

                        <!-- Gradient overlays -->
                        <div class="absolute inset-x-0 top-0 h-20 bg-gradient-to-b from-black/80 via-black/30 to-transparent pointer-events-none z-10"></div>
                        <div class="absolute inset-x-0 bottom-0 h-28 bg-gradient-to-t from-black/95 via-black/60 to-transparent pointer-events-none z-10"></div>

                        <!-- Top Bar: Checkmark & Badges -->
                        <div class="absolute top-3 inset-x-3 z-20 flex justify-between items-center">
                            <div>
                                ${{isKeeper ? `
                                    <span class="text-xs font-bold text-[#131314] bg-[#81c995] px-3 py-1 rounded-full flex items-center gap-1 shadow-md">
                                        <span>★</span> BEST COPY (KEEPER)
                                    </span>
                                ` : `
                                    <div onclick="toggleItemSelection('${{encodeURIComponent(item.path)}}', event)"
                                         class="gp-check-circle !w-7 !h-7 ${{isChecked ? 'checked' : 'opacity-0 group-hover:opacity-100'}}"
                                         title="${{isChecked ? 'Deselect from deletion' : 'Select for deletion'}}">
                                        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                                            <polyline points="20 6 9 17 4 12"></polyline>
                                        </svg>
                                    </div>
                                `}}
                            </div>
                            <div class="flex items-center gap-1.5">
                                ${{isVideo ? `
                                    <span class="text-xs font-mono bg-black/80 text-white px-2.5 py-1 rounded-full border border-white/20 flex items-center gap-1">
                                        <svg class="w-3 h-3 fill-white" viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                                        <span>VIDEO</span>
                                    </span>
                                ` : ''}}
                                ${{!isKeeper ? `
                                    <span class="text-xs font-mono text-[#8ab4f8] bg-black/70 backdrop-blur-md px-2.5 py-1 rounded-full border border-white/10 font-bold">
                                        ${{item.similarity || '100%'}} Match
                                    </span>
                                ` : ''}}
                            </div>
                        </div>

                        <!-- Bottom Detailed Overlay -->
                        <div class="absolute bottom-3 inset-x-3.5 z-20 flex flex-col justify-end space-y-1">
                            <div class="font-bold text-white text-sm truncate drop-shadow">${{fname}}</div>
                            <div class="text-[11px] text-[#8e918f] font-mono truncate" title="${{parentDir}}">${{parentDir}}</div>
                            <div class="flex items-center justify-between text-xs text-[#c4c7c5] font-mono pt-1">
                                <span>${{sizeStr}} ${{dimStr ? '• ' + dimStr : ''}}</span>
                                ${{!isKeeper ? `
                                    <button onclick="setKeeperOverride(${{groupId}}, '${{encodeURIComponent(item.path)}}', event)"
                                            class="m3-button-secondary !py-1 !px-3 text-xs text-[#8ab4f8] hover:text-white bg-black/80 backdrop-blur-md border-[#8ab4f8]/40 shadow"
                                            title="Make this file the designated keeper">
                                        ★ Keep This
                                    </button>
                                ` : `
                                    <span class="text-xs text-[#81c995] font-semibold flex items-center gap-1">✓ Preserved Original (Kept)</span>
                                `}}
                            </div>
                        </div>
                    </div>
                `;
            }}

            // Medium (Default Google Photos Tile)
            return `
                <div onclick="openPhotoLightbox(${{groupId}}, '${{encodeURIComponent(item.path)}}')"
                     class="group relative aspect-square rounded-2xl overflow-hidden cursor-pointer bg-[#1e1f20] border ${{isKeeper ? 'border-2 border-[#81c995] shadow-md shadow-[#81c995]/15 bg-[#81c995]/5' : 'border border-white/10 hover:border-white/30'}} transition duration-200">

                    <!-- High-Res Thumbnail Preview -->
                    ${{isMedia ? `
                        <img src="/api/thumbnail?path=${{encodeURIComponent(item.path)}}"
                             class="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                             loading="lazy" alt="${{fname}}"
                             onerror="this.parentElement.querySelector('.fallback-thumb').classList.remove('hidden'); this.remove();">
                        <div class="fallback-thumb hidden w-full h-full flex flex-col items-center justify-center bg-[#131314] text-[#8e918f]">
                            <span class="text-xl">${{isVideo ? '🎥' : '🖼️'}}</span>
                            <span class="text-[10px] font-mono mt-1">${{isVideo ? 'VIDEO' : 'PHOTO'}}</span>
                        </div>
                    ` : `
                        <div class="w-full h-full flex flex-col items-center justify-center bg-[#131314] text-[#8e918f] p-3 text-center">
                            <span class="text-2xl mb-1">📄</span>
                            <span class="text-xs font-semibold text-white truncate max-w-full">${{fname.split('.').pop() || 'DOC'}}</span>
                            <span class="text-[10px] text-[#8e918f] font-mono mt-0.5">${{sizeStr}}</span>
                        </div>
                    `}}

                    <!-- Dark Gradient Overlays for High Contrast Readability -->
                    <div class="absolute inset-x-0 top-0 h-14 bg-gradient-to-b from-black/70 via-black/20 to-transparent pointer-events-none z-10"></div>
                    <div class="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-black/85 via-black/40 to-transparent pointer-events-none z-10"></div>

                    <!-- Top Left: Google Photos Check Circle -->
                    <div class="absolute top-2.5 left-2.5 z-20">
                        ${{isKeeper ? `
                            <span class="text-[10px] font-bold text-[#131314] bg-[#81c995] px-2.5 py-0.5 rounded-full flex items-center gap-1 shadow-sm">
                                <span>★</span> BEST COPY
                            </span>
                        ` : `
                            <div onclick="toggleItemSelection('${{encodeURIComponent(item.path)}}', event)"
                                 class="gp-check-circle ${{isChecked ? 'checked' : 'opacity-0 group-hover:opacity-100'}}"
                                 title="${{isChecked ? 'Deselect from deletion' : 'Select for deletion'}}">
                                <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                                    <polyline points="20 6 9 17 4 12"></polyline>
                                </svg>
                            </div>
                        `}}
                    </div>

                    <!-- Top Right: Video play badge or similarity tag -->
                    <div class="absolute top-2.5 right-2.5 z-20 flex items-center gap-1">
                        ${{isVideo ? `
                            <span class="text-[10px] font-mono bg-black/70 text-white px-2 py-0.5 rounded-full border border-white/20 flex items-center gap-1">
                                <svg class="w-2.5 h-2.5 fill-white" viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                                <span>VIDEO</span>
                            </span>
                        ` : ''}}
                        ${{!isKeeper ? `
                            <span class="text-[10px] font-mono text-[#8ab4f8] bg-black/60 backdrop-blur-md px-2 py-0.5 rounded-full border border-white/10 font-bold">
                                ${{item.similarity || '100%'}}
                            </span>
                        ` : ''}}
                    </div>

                    <!-- Bottom Details Bar -->
                    <div class="absolute bottom-2 inset-x-2.5 z-20 flex flex-col justify-end">
                        <div class="font-medium text-white text-xs truncate drop-shadow">${{fname}}</div>
                        <div class="flex items-center justify-between text-[11px] text-[#c4c7c5] font-mono mt-0.5">
                            <span>${{sizeStr}}</span>
                            ${{!isKeeper ? `
                                <button onclick="setKeeperOverride(${{groupId}}, '${{encodeURIComponent(item.path)}}', event)"
                                        class="opacity-0 group-hover:opacity-100 transition text-[10px] text-[#8ab4f8] hover:text-white bg-black/80 backdrop-blur-md px-2 py-0.5 rounded-full border border-[#8ab4f8]/40 shadow"
                                        title="Make this file the designated keeper">
                                    ★ Keep This
                                </button>
                            ` : `
                                <span class="text-[10px] text-[#81c995] font-semibold flex items-center gap-0.5">✓ Original</span>
                            `}}
                        </div>
                    </div>
                </div>
            `;
        }}

        // Google Drive List View (Adapts to Thumbnail / Icon Size)
        function createGoogleDriveListCard(cluster) {{
            const card = document.createElement('div');
            card.className = "m3-card p-4 sm:p-5 shadow-lg border border-[#28292a] hover:border-[#3c4043] transition-all bg-[#1e1f20]/90";

            const wastedMb = (cluster.totalWastedBytes / (1024 * 1024)).toFixed(2);
            const allDupesSelected = cluster.duplicates.length > 0 && cluster.duplicates.every(d => !excludedPaths.has(d.path));
            const representative = cluster.keeper || cluster.items[0];
            const primaryName = representative.path.split('/').pop();
            const parentDir = representative.path.substring(0, representative.path.lastIndexOf('/'));

            card.innerHTML = `
                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 mb-3 border-b border-[#28292a]">
                    <div class="flex items-center gap-3 min-w-0">
                        <div onclick="toggleClusterSelection(${{cluster.group_id}}, event)"
                             class="gp-check-circle ${{allDupesSelected ? 'checked' : ''}} !w-5 !h-5 flex-shrink-0"
                             title="${{allDupesSelected ? 'Deselect cluster' : 'Mark duplicates for cleaning and keep best copy'}}">
                            <svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <div class="min-w-0">
                            <div class="flex items-center gap-2 flex-wrap">
                                <span class="font-bold text-white text-xs truncate max-w-sm" title="${{primaryName}}">${{primaryName}}</span>
                                <span class="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#1a3860] text-[#8ab4f8]">${{cluster.match_type}}</span>
                                <span class="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-[#81c995]/15 text-[#81c995]">${{wastedMb}} MB wasted</span>
                            </div>
                            <div class="text-[11px] text-[#8e918f] font-mono truncate mt-0.5" title="${{parentDir}}">
                                📁 ${{parentDir}} • ${{cluster.items.length}} copies
                            </div>
                        </div>
                    </div>
                    <div class="flex items-center gap-2 flex-shrink-0 self-end sm:self-auto">
                        <button onclick="toggleClusterSelection(${{cluster.group_id}}, event)"
                                class="m3-button-secondary text-xs !py-1 !px-3 ${{allDupesSelected ? 'text-[#8ab4f8] border-[#8ab4f8]/40' : ''}}"
                                title="${{allDupesSelected ? 'Deselect duplicates' : 'Keep designated best copy and mark duplicates for removal'}}">
                            <span>${{allDupesSelected ? '✓ Clean Ready' : '★ Keep Best & Clean Rest'}}</span>
                        </button>
                        <button onclick="openPhotoLightbox(${{cluster.group_id}}, '${{encodeURIComponent(cluster.items[0].path)}}')" class="m3-button-secondary text-xs !py-1 !px-3 hover:text-[#8ab4f8]">
                            <span>⇄ Compare Diff</span>
                        </button>
                    </div>
                </div>

                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs font-mono">
                        <thead>
                            <tr class="text-[#8e918f] border-b border-[#202124]">
                                <th class="py-1.5 px-2 w-8"></th>
                                ${{thumbnailSize === 'large' ? '<th class="py-1.5 px-2 w-16">Preview</th>' : ''}}
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
            const isMedia = isMediaFile(item.path);
            const fname = item.path.split('/').pop();
            const padClass = (thumbnailSize === 'small') ? 'py-1 px-2 text-[11px]' : 'py-2 px-2';

            return `
                <tr class="hover:bg-[#28292a]/50 transition cursor-pointer" onclick="openPhotoLightbox(${{groupId}}, '${{encodeURIComponent(item.path)}}')">
                    <td class="${{padClass}}" onclick="event.stopPropagation()">
                        ${{isKeeper ? `<span class="text-[#81c995]">★</span>` : `
                            <input type="checkbox" onchange="toggleItemSelection('${{encodeURIComponent(item.path)}}')"
                                   ${{isChecked ? 'checked' : ''}} class="rounded accent-[#8ab4f8] cursor-pointer">
                        `}}
                    </td>
                    ${{thumbnailSize === 'large' ? `
                        <td class="${{padClass}}">
                            <div class="w-12 h-12 rounded-lg bg-black overflow-hidden flex items-center justify-center border border-white/10">
                                ${{isMedia ? `
                                    <img src="/api/thumbnail?path=${{encodeURIComponent(item.path)}}" class="w-full h-full object-cover" loading="lazy">
                                ` : `
                                    <span class="text-xs">📄</span>
                                `}}
                            </div>
                        </td>
                    ` : ''}}
                    <td class="${{padClass}} font-medium text-white truncate max-w-[200px]" title="${{fname}}">${{fname}}</td>
                    <td class="${{padClass}}">
                        <span class="px-2 py-0.5 rounded-full text-[10px] ${{isKeeper ? 'bg-[#81c995]/15 text-[#81c995]' : 'bg-[#f28b82]/15 text-[#f28b82]'}}">
                            ${{item.action}}
                        </span>
                    </td>
                    <td class="${{padClass}} text-[#c4c7c5]">${{(item.size_mb || 0).toFixed(2)}} MB</td>
                    <td class="${{padClass}} text-[#8e918f] truncate max-w-[240px]" title="${{item.path}}">${{item.path}}</td>
                    <td class="${{padClass}} text-right" onclick="event.stopPropagation()">
                        ${{!isKeeper ? `
                            <button onclick="setKeeperOverride(${{groupId}}, '${{encodeURIComponent(item.path)}}', event)"
                                     class="text-[#8ab4f8] hover:underline text-[11px] font-sans font-medium mr-2">
                                Make Keeper
                            </button>
                        ` : '<span class="text-[#8e918f] text-[10px]">Keeper</span>'}}
                    </td>
                </tr>
            `;
        }}

        function toggleItemSelection(encodedPath, event) {{
            if (event) event.stopPropagation();
            const path = decodeURIComponent(encodedPath);
            if (excludedPaths.has(path)) {{
                excludedPaths.delete(path);
            }} else {{
                excludedPaths.add(path);
            }}
            renderCurrentPage();
            updateTopSelectionBar();
        }}

        function toggleClusterSelection(groupId, event) {{
            if (event) event.stopPropagation();
            const cluster = allClusters.find(c => c.group_id === groupId);
            if (!cluster) return;

            const allDupesSelected = cluster.duplicates.length > 0 && cluster.duplicates.every(d => !excludedPaths.has(d.path));
            if (allDupesSelected) {{
                for (const d of cluster.duplicates) {{
                    excludedPaths.add(d.path);
                }}
            }} else {{
                for (const d of cluster.duplicates) {{
                    excludedPaths.delete(d.path);
                }}
            }}
            renderCurrentPage();
            updateTopSelectionBar();
        }}

        async function setKeeperOverride(groupId, encodedPath, event) {{
            if (event) event.stopPropagation();
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
                updateTopSelectionBar();

                const fname = path.split('/').pop();
                showToast(`Promoted "${{fname}}" to Keeper in Cluster #${{groupId}}`, "★");

                // If lightbox is open, refresh it
                if (lbCluster && lbCluster.group_id === groupId) {{
                    openPhotoLightbox(groupId, encodeURIComponent(path));
                }}
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
                showToast("Cleared duplicate selection.", "✕");
            }} else if (rule === 'ALL') {{
                excludedPaths.clear();
                showToast("Selected all duplicate candidates.", "✓");
            }}
            renderCurrentPage();
            updateTopSelectionBar();
        }}

        // Updates Google Photos Top Selection Bar (Zero floating windows)
        function updateTopSelectionBar() {{
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

            const defHeader = document.getElementById('defaultHeader');
            const selHeader = document.getElementById('selectionHeader');

            if (stagedCount > 0) {{
                defHeader.classList.add('hidden');
                selHeader.classList.remove('hidden');
                selHeader.classList.add('flex');

                document.getElementById('topSelectedCount').innerText = `${{stagedCount.toLocaleString()}} selected`;
                document.getElementById('topSelectedSpace').innerText = `(${{gb}} GB • ${{mb}} MB)`;
            }} else {{
                selHeader.classList.add('hidden');
                selHeader.classList.remove('flex');
                defHeader.classList.remove('hidden');
            }}
        }}

        // Google Photos Full-Screen Lightbox
        function openPhotoLightbox(groupId, encodedPath) {{
            const cluster = allClusters.find(c => c.group_id === groupId);
            if (!cluster) return;

            const path = decodeURIComponent(encodedPath);
            let idx = cluster.items.findIndex(i => i.path === path);
            if (idx === -1) idx = 0;

            lbCluster = cluster;
            lbItemIndex = idx;
            lbIsDiff = false;

            renderLightboxView();
            document.getElementById('photoLightboxModal').classList.remove('hidden');
        }}

        function closePhotoLightbox() {{
            document.getElementById('photoLightboxModal').classList.add('hidden');
            lbCluster = null;
        }}

        function navigateLightbox(dir) {{
            if (!lbCluster || lbCluster.items.length <= 1) return;
            lbItemIndex = (lbItemIndex + dir + lbCluster.items.length) % lbCluster.items.length;
            renderLightboxView();
        }}

        function toggleLightboxDiff() {{
            lbIsDiff = !lbIsDiff;
            const diffBtn = document.getElementById('lbDiffBtn');
            if (lbIsDiff) {{
                diffBtn.classList.add('!bg-[#1a3860]', '!text-[#8ab4f8]');
            }} else {{
                diffBtn.classList.remove('!bg-[#1a3860]', '!text-[#8ab4f8]');
            }}
            renderLightboxView();
        }}

        function toggleLightboxInfo() {{
            lbIsInfoOpen = !lbIsInfoOpen;
            const drawer = document.getElementById('lbInfoDrawer');
            const infoBtn = document.getElementById('lbInfoBtn');
            if (lbIsInfoOpen) {{
                drawer.classList.remove('hidden');
                infoBtn.classList.add('!bg-[#1a3860]', '!text-[#8ab4f8]');
            }} else {{
                drawer.classList.add('hidden');
                infoBtn.classList.remove('!bg-[#1a3860]', '!text-[#8ab4f8]');
            }}
        }}

        function renderLightboxView() {{
            if (!lbCluster) return;
            const item = lbCluster.items[lbItemIndex];
            const keeper = lbCluster.keeper || lbCluster.items[0];
            const isKeeper = (item.action === 'KEEP');
            const fname = item.path.split('/').pop();
            const sizeStr = `${{(item.size_mb || 0).toFixed(2)}} MB`;

            document.getElementById('lbClusterTitle').innerText = `Cluster #${{lbCluster.group_id}} (${{lbItemIndex + 1}} of ${{lbCluster.items.length}})`;
            document.getElementById('lbMatchType').innerText = lbCluster.match_type;
            document.getElementById('lbFileName').innerText = fname;

            const makeKeeperBtn = document.getElementById('lbMakeKeeperBtn');
            if (isKeeper) {{
                makeKeeperBtn.classList.add('opacity-50', 'pointer-events-none');
                makeKeeperBtn.innerText = "★ Designated Keeper";
            }} else {{
                makeKeeperBtn.classList.remove('opacity-50', 'pointer-events-none');
                makeKeeperBtn.innerText = "★ Make Keeper";
            }}

            const singleView = document.getElementById('lbSingleView');
            const diffView = document.getElementById('lbDiffView');

            if (lbIsDiff) {{
                singleView.classList.add('hidden');
                diffView.classList.remove('hidden');

                // Keeper Diff Column
                document.getElementById('lbDiffKeeperName').innerText = keeper.path.split('/').pop();
                document.getElementById('lbDiffKeeperPath').innerText = keeper.path;
                document.getElementById('lbDiffKeeperSize').innerText = `${{(keeper.size_mb || 0).toFixed(2)}} MB`;
                document.getElementById('lbDiffKeeperDim').innerText = keeper.dimensions ? `${{keeper.dimensions[0]}}x${{keeper.dimensions[1]}}` : 'N/A';
                document.getElementById('lbDiffKeeperCat').innerText = keeper.category || 'MEDIA';
                const kpPreview = document.getElementById('lbDiffKeeperPreview');
                if (isVideoFile(keeper.path)) {{
                    kpPreview.innerHTML = `<video src="/api/media?path=${{encodeURIComponent(keeper.path)}}" controls class="w-full h-full object-contain bg-black"></video>`;
                }} else if (isImageFile(keeper.path)) {{
                    kpPreview.innerHTML = `<img src="/api/thumbnail?path=${{encodeURIComponent(keeper.path)}}" class="w-full h-full object-contain" alt="keeper">`;
                }} else {{
                    kpPreview.innerHTML = `<span class="text-xs font-mono text-[#8e918f] uppercase">${{keeper.path.split('.').pop()}} FILE</span>`;
                }}

                // Dupe Diff Column
                const dupeItem = isKeeper ? (lbCluster.duplicates[0] || item) : item;
                document.getElementById('lbDiffDupeName').innerText = dupeItem.path.split('/').pop();
                document.getElementById('lbDiffDupePath').innerText = dupeItem.path;
                document.getElementById('lbDiffDupeSize').innerText = `${{(dupeItem.size_mb || 0).toFixed(2)}} MB`;
                document.getElementById('lbDiffDupeDim').innerText = dupeItem.dimensions ? `${{dupeItem.dimensions[0]}}x${{dupeItem.dimensions[1]}}` : 'N/A';
                document.getElementById('lbDiffDupeSim').innerText = dupeItem.similarity || '100% Match';
                const dpPreview = document.getElementById('lbDiffDupePreview');
                if (isVideoFile(dupeItem.path)) {{
                    dpPreview.innerHTML = `<video src="/api/media?path=${{encodeURIComponent(dupeItem.path)}}" controls class="w-full h-full object-contain bg-black"></video>`;
                }} else if (isImageFile(dupeItem.path)) {{
                    dpPreview.innerHTML = `<img src="/api/thumbnail?path=${{encodeURIComponent(dupeItem.path)}}" class="w-full h-full object-contain" alt="dupe">`;
                }} else {{
                    dpPreview.innerHTML = `<span class="text-xs font-mono text-[#8e918f] uppercase">${{dupeItem.path.split('.').pop()}} FILE</span>`;
                }}
            }} else {{
                diffView.classList.add('hidden');
                singleView.classList.remove('hidden');

                const container = document.getElementById('lbImageContainer');
                if (isVideoFile(item.path)) {{
                    container.innerHTML = `
                        <div class="flex flex-col items-center justify-center max-w-full">
                            <video controls autoplay src="/api/media?path=${{encodeURIComponent(item.path)}}"
                                   class="max-h-[75vh] max-w-full rounded-2xl shadow-2xl bg-black border border-white/10">
                            </video>
                            <div class="text-xs text-[#8e918f] font-mono mt-2">${{fname}} (${{sizeStr}})</div>
                        </div>
                    `;
                }} else if (isImageFile(item.path)) {{
                    container.innerHTML = `<img src="/api/thumbnail?path=${{encodeURIComponent(item.path)}}" class="max-h-[80vh] max-w-full object-contain rounded-2xl shadow-2xl" alt="lightbox photo">`;
                }} else {{
                    container.innerHTML = `
                        <div class="text-center p-12 bg-[#1e1f20] rounded-3xl border border-[#3c4043] max-w-md">
                            <span class="text-6xl block mb-3">📄</span>
                            <div class="font-bold text-white text-base break-all">${{fname}}</div>
                            <div class="text-xs text-[#8e918f] font-mono mt-1">${{sizeStr}}</div>
                        </div>
                    `;
                }}
            }}

            // Populate Info Drawer
            document.getElementById('lbInfoName').innerText = item.path.split('/').pop();
            document.getElementById('lbInfoPath').innerText = item.path;
            document.getElementById('lbInfoSize').innerText = `${{(item.size_mb || 0).toFixed(2)}} MB`;
            document.getElementById('lbInfoDim').innerText = item.dimensions ? `${{item.dimensions[0]}}x${{item.dimensions[1]}}` : 'N/A';
            document.getElementById('lbInfoRole').innerText = isKeeper ? 'DESIGNATED KEEPER' : 'DUPLICATE CANDIDATE';
            document.getElementById('lbInfoRole').className = isKeeper ? 'text-[#81c995] font-semibold' : 'text-[#f28b82] font-semibold';
            document.getElementById('lbInfoSim').innerText = item.similarity || (isKeeper ? 'Original' : '100%');
            document.getElementById('lbInfoAlgorithm').innerText = lbCluster.match_type;
        }}

        async function swapKeeperInLightbox() {{
            if (!lbCluster) return;
            const item = lbCluster.items[lbItemIndex];
            await setKeeperOverride(lbCluster.group_id, encodeURIComponent(item.path));
        }}

        // Trash Section View
        function renderTrashSection() {{
            const gallery = document.getElementById('clustersGallery');
            gallery.innerHTML = `
                <div class="m3-card p-8">
                    <div class="flex items-center gap-3 mb-6">
                        <div class="w-12 h-12 rounded-full bg-[#1a3860] text-[#8ab4f8] flex items-center justify-center text-2xl">🗑️</div>
                        <div>
                            <h3 class="text-xl font-bold text-white">Safe Trash & Audit History</h3>
                            <p class="text-xs text-[#8e918f]">Restorable Soft Deletion & Audit Trail</p>
                        </div>
                    </div>

                    <div class="space-y-4 text-sm text-[#c4c7c5]">
                        <p>
                            Clairvoy moves deleted files into <code class="text-xs bg-[#131314] px-2 py-0.5 rounded text-[#8ab4f8]">.clairvoy_trash/</code> with an immutable JSON manifest.
                            Keeper files are mathematically protected by zero-clobber invariants.
                        </p>
                        <div class="bg-[#131314] rounded-2xl p-5 border border-[#3c4043] flex flex-wrap gap-4 items-center justify-between">
                            <div>
                                <div class="font-bold text-white text-xs">Hardened Deletion Scripts</div>
                                <div class="text-xs text-[#8e918f] font-mono">Download a shell script to review and execute offline at your leisure.</div>
                            </div>
                            <div class="flex gap-2">
                                <a href="/api/reports/delete-script?mode=trash" download class="m3-button-secondary text-xs">
                                    <span>Download Trash Script (.sh)</span>
                                </a>
                                <a href="/api/reports/delete-script?mode=permanent" download class="m3-button-danger text-xs">
                                    <span>Download Permanent Delete Script (.sh)</span>
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            `;
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
