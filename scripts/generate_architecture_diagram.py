#!/usr/bin/env python3
"""
Clairvoy Rich Architecture Diagram Generator
Generates a modern, dark-mode, animated vector SVG diagram for documentation and GitHub display.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "docs" / "assets" / "diagrams"
OUTPUT_SVG = OUTPUT_DIR / "architecture.svg"


def generate_architecture_svg() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    svg_content = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 780" width="100%" height="100%">
  <defs>
    <!-- Background & Card Gradients -->
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#090d16" />
      <stop offset="50%" stop-color="#0f172a" />
      <stop offset="100%" stop-color="#090d16" />
    </linearGradient>
    <linearGradient id="cardGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#1e293b" stop-opacity="0.8" />
      <stop offset="100%" stop-color="#0f172a" stop-opacity="0.9" />
    </linearGradient>
    <linearGradient id="indigoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#6366f1" />
      <stop offset="100%" stop-color="#4f46e5" />
    </linearGradient>
    <linearGradient id="emeraldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#10b981" />
      <stop offset="100%" stop-color="#059669" />
    </linearGradient>
    <linearGradient id="purpleGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#a855f7" />
      <stop offset="100%" stop-color="#7c3aed" />
    </linearGradient>
    <linearGradient id="amberGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#f59e0b" />
      <stop offset="100%" stop-color="#d97706" />
    </linearGradient>
    <linearGradient id="cyanGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#06b6d4" />
      <stop offset="100%" stop-color="#0891b2" />
    </linearGradient>

    <!-- Filters for Glow & Shadows -->
    <filter id="dropShadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="8" stdDeviation="12" flood-color="#000000" flood-opacity="0.5" />
    </filter>
    <filter id="emeraldGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="0" stdDeviation="6" flood-color="#10b981" flood-opacity="0.4" />
    </filter>
    <filter id="indigoGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="0" stdDeviation="6" flood-color="#6366f1" flood-opacity="0.4" />
    </filter>

    <!-- Arrow Marker -->
    <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 8 5 L 0 9 z" fill="#64748b" />
    </marker>
    <marker id="arrow-emerald" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 8 5 L 0 9 z" fill="#10b981" />
    </marker>
    <marker id="arrow-indigo" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 8 5 L 0 9 z" fill="#6366f1" />
    </marker>

    <!-- Animation Style -->
    <style>
      @keyframes pulseFlow {
        0% { stroke-dashoffset: 40; }
        100% { stroke-dashoffset: 0; }
      }
      .flow-line {
        stroke-dasharray: 8 6;
        animation: pulseFlow 2s linear infinite;
      }
      text {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      }
      .title { font-weight: 800; fill: #ffffff; letter-spacing: -0.5px; }
      .subtitle { font-size: 13px; fill: #94a3b8; }
      .badge-text { font-size: 11px; font-weight: 700; fill: #ffffff; }
      .card-title { font-size: 15px; font-weight: 700; fill: #f8fafc; }
      .card-desc { font-size: 12px; fill: #94a3b8; line-height: 1.4; }
      .tag { font-size: 10px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
    </style>
  </defs>

  <!-- Background -->
  <rect width="100%" height="100%" fill="url(#bgGrad)" rx="20" />
  <rect width="100%" height="100%" fill="none" stroke="#1e293b" stroke-width="2" rx="20" />

  <!-- Grid Accent Background Lines -->
  <g opacity="0.08" stroke="#ffffff" stroke-width="1">
    <path d="M 0 130 L 1200 130 M 0 260 L 1200 260 M 0 390 L 1200 390 M 0 520 L 1200 520 M 0 650 L 1200 650" />
    <path d="M 240 0 L 240 780 M 480 0 L 480 780 M 720 0 L 720 780 M 960 0 L 960 780" />
  </g>

  <!-- TOP HEADER -->
  <g transform="translate(60, 40)">
    <circle cx="16" cy="16" r="14" fill="url(#indigoGrad)" filter="url(#indigoGlow)" />
    <text x="11" y="21" font-size="16" fill="#ffffff">👁️</text>
    <text x="45" y="22" font-size="22" class="title">Clairvoy Pluggable Deduplication Pipeline</text>
    <text x="45" y="42" class="subtitle">Tiered Cost-Ascending Matcher Chain • Candidate Pruning • Composite Keeper Scoring • Safe Inode Resolution</text>
  </g>

  <!-- PLUGIN REGISTRY BADGE -->
  <g transform="translate(850, 40)" filter="url(#dropShadow)">
    <rect width="290" height="50" rx="12" fill="#1e293b" stroke="#334155" stroke-width="1.5" />
    <circle cx="25" cy="25" r="8" fill="#10b981" />
    <text x="45" y="24" font-size="12" font-weight="700" fill="#f8fafc">Dynamic PluginRegistry</text>
    <text x="45" y="38" font-size="10" fill="#94a3b8" class="tag">~/.clairvoy/plugins/*.py + entry_points</text>
  </g>

  <!-- INPUT DISCOVERY CARD -->
  <g transform="translate(60, 110)" filter="url(#dropShadow)">
    <rect width="1080" height="70" rx="14" fill="url(#cardGrad)" stroke="#334155" stroke-width="1.5" />
    <rect x="15" y="15" width="40" height="40" rx="8" fill="#334155" />
    <text x="26" y="41" font-size="18">📁</text>
    <text x="70" y="34" class="card-title">Multi-Root Filesystem Ingestion &amp; Discovery</text>
    <text x="70" y="52" class="card-desc">High-throughput recursive scanning with concurrent os.scandir threads across local drives and cloud mounts.</text>
    <rect x="940" y="22" width="120" height="26" rx="6" fill="#0f172a" stroke="#475569" />
    <text x="955" y="39" class="tag" fill="#38bdf8">Candidate Stream</text>
  </g>

  <!-- MAIN CONNECTOR LINE DOWN TO MATCHERS -->
  <path d="M 600 180 L 600 220" stroke="#6366f1" stroke-width="2.5" class="flow-line" marker-end="url(#arrow-indigo)" />

  <!-- PIPELINE CHAIN CONTAINER -->
  <rect x="60" y="220" width="1080" height="340" rx="18" fill="#0f172a" fill-opacity="0.6" stroke="#334155" stroke-width="1.5" stroke-dasharray="4 4" />
  <text x="85" y="246" font-size="13" font-weight="700" fill="#64748b" letter-spacing="1">TIERED MATCHER PIPELINE (CHAIN OF RESPONSIBILITY)</text>

  <!-- MATCHER 1: EXACT HASH -->
  <g transform="translate(85, 270)" filter="url(#dropShadow)">
    <rect width="240" height="260" rx="14" fill="url(#cardGrad)" stroke="#4f46e5" stroke-width="2" />
    <!-- Priority Badge -->
    <rect x="15" y="15" width="85" height="24" rx="6" fill="url(#indigoGrad)" />
    <text x="23" y="31" class="badge-text">Priority 10</text>
    <text x="195" y="32" font-size="18">⚡</text>
    <text x="15" y="68" class="card-title">Exact Hash</text>
    <text x="15" y="85" font-size="11" fill="#818cf8" font-weight="600">ExactHashMatcherPlugin</text>
    <text x="15" y="112" class="card-desc">Two-stage byte validation:</text>
    <text x="25" y="132" class="card-desc">1. 128KB QuickHash</text>
    <text x="25" y="150" class="card-desc">2. 64KB/1MB Stream SHA-256</text>
    <rect x="15" y="175" width="210" height="65" rx="8" fill="#090d16" stroke="#334155" />
    <text x="25" y="195" class="tag" fill="#10b981">✓ 100% Byte Identical</text>
    <text x="25" y="213" class="tag" fill="#94a3b8">Filters 80-90% duplicates</text>
    <text x="25" y="228" class="tag" fill="#94a3b8">before expensive AI stages</text>
  </g>

  <!-- CONNECTOR 1 -> 2 (WITH PRUNING CALLOUT) -->
  <path d="M 325 380 L 360 380" stroke="#6366f1" stroke-width="2" marker-end="url(#arrow-indigo)" class="flow-line" />

  <!-- MATCHER 2: PHOTO VISION -->
  <g transform="translate(360, 270)" filter="url(#dropShadow)">
    <rect width="240" height="260" rx="14" fill="url(#cardGrad)" stroke="#06b6d4" stroke-width="1.5" />
    <!-- Priority Badge -->
    <rect x="15" y="15" width="85" height="24" rx="6" fill="url(#cyanGrad)" />
    <text x="23" y="31" class="badge-text">Priority 20</text>
    <text x="195" y="32" font-size="18">🧠</text>
    <text x="15" y="68" class="card-title">Photo Vision AI</text>
    <text x="15" y="85" font-size="11" fill="#38bdf8" font-weight="600">PhotoVisionMatcherPlugin</text>
    <text x="15" y="112" class="card-desc">Visual similarity engine:</text>
    <text x="25" y="132" class="card-desc">• Local Meta DINOv2 ONNX</text>
    <text x="25" y="150" class="card-desc">• 2048-chunk Cosine Dots</text>
    <rect x="15" y="175" width="210" height="65" rx="8" fill="#090d16" stroke="#334155" />
    <text x="25" y="195" class="tag" fill="#38bdf8">✓ Near-Duplicate Photos</text>
    <text x="25" y="213" class="tag" fill="#94a3b8">Burst shots, crops, edits</text>
    <text x="25" y="228" class="tag" fill="#94a3b8">Disjoint Set Union (DSU)</text>
  </g>

  <!-- CONNECTOR 2 -> 3 -->
  <path d="M 600 380 L 635 380" stroke="#06b6d4" stroke-width="2" marker-end="url(#arrow)" class="flow-line" />

  <!-- MATCHER 3: VIDEO KEYFRAME -->
  <g transform="translate(635, 270)" filter="url(#dropShadow)">
    <rect width="240" height="260" rx="14" fill="url(#cardGrad)" stroke="#a855f7" stroke-width="1.5" />
    <!-- Priority Badge -->
    <rect x="15" y="15" width="85" height="24" rx="6" fill="url(#purpleGrad)" />
    <text x="23" y="31" class="badge-text">Priority 30</text>
    <text x="195" y="32" font-size="18">🎬</text>
    <text x="15" y="68" class="card-title">Video Keyframe</text>
    <text x="15" y="85" font-size="11" fill="#c084fc" font-weight="600">VideoKeyframeMatcherPlugin</text>
    <text x="15" y="112" class="card-desc">Transcode duplicate match:</text>
    <text x="25" y="132" class="card-desc">• Duration match (±1.5%)</text>
    <text x="25" y="150" class="card-desc">• 10%, 50%, 90% Keyframe</text>
    <rect x="15" y="175" width="210" height="65" rx="8" fill="#090d16" stroke="#334155" />
    <text x="25" y="195" class="tag" fill="#c084fc">✓ 4K vs 720p Transcodes</text>
    <text x="25" y="213" class="tag" fill="#94a3b8">Perceptual dHash matching</text>
    <text x="25" y="228" class="tag" fill="#94a3b8">ffprobe / ffmpeg / cv2</text>
  </g>

  <!-- CONNECTOR 3 -> 4 -->
  <path d="M 875 380 L 905 380" stroke="#a855f7" stroke-width="2" marker-end="url(#arrow)" class="flow-line" />

  <!-- MATCHER 4: ARCHIVE PEEK -->
  <g transform="translate(905, 270)" filter="url(#dropShadow)">
    <rect width="210" height="260" rx="14" fill="url(#cardGrad)" stroke="#f59e0b" stroke-width="1.5" />
    <!-- Priority Badge -->
    <rect x="15" y="15" width="85" height="24" rx="6" fill="url(#amberGrad)" />
    <text x="23" y="31" class="badge-text">Priority 40</text>
    <text x="165" y="32" font-size="18">📦</text>
    <text x="15" y="68" class="card-title">Archive Peek</text>
    <text x="15" y="85" font-size="11" fill="#fcd34d" font-weight="600">ArchiveInspectorMatcher</text>
    <text x="15" y="112" class="card-desc">Zero extraction peek:</text>
    <text x="25" y="132" class="card-desc">• ZIP Central Directory</text>
    <text x="25" y="150" class="card-desc">• In-memory CRC32</text>
    <rect x="15" y="175" width="180" height="65" rx="8" fill="#090d16" stroke="#334155" />
    <text x="22" y="195" class="tag" fill="#fcd34d">✓ Disk vs Archive</text>
    <text x="22" y="213" class="tag" fill="#94a3b8">Catches extracted files</text>
    <text x="22" y="228" class="tag" fill="#94a3b8">trapped inside backups</text>
  </g>

  <!-- SHORT CIRCUIT PRUNING FEEDBACK LOOP -->
  <path d="M 205 530 L 205 545 L 800 545" fill="none" stroke="#10b981" stroke-width="1.5" stroke-dasharray="4 4" />
  <text x="410" y="556" font-size="10" fill="#10b981" font-weight="600">⚡ Short-Circuit Candidate Pruning: Matched items are bypassed from downstream compute</text>

  <!-- CONNECTOR DOWN TO KEEPER & RESOLUTION -->
  <path d="M 600 560 L 600 595" stroke="#10b981" stroke-width="2.5" class="flow-line" marker-end="url(#arrow-emerald)" />

  <!-- BOTTOM RESOLUTION LAYER -->
  <g transform="translate(60, 595)" filter="url(#dropShadow)">
    <rect width="1080" height="145" rx="16" fill="url(#cardGrad)" stroke="#10b981" stroke-width="2" filter="url(#emeraldGlow)" />

    <!-- Keeper Scoring Strategy -->
    <g transform="translate(25, 20)">
      <rect width="400" height="105" rx="10" fill="#090d16" stroke="#334155" />
      <text x="15" y="26" class="card-title">CompositeKeeperStrategy</text>
      <text x="15" y="45" class="card-desc">Deterministic multi-signal keeper scoring:</text>
      <text x="25" y="65" class="tag" fill="#ef4444">- Penalize copy tags: (1), -copy, thumb (-50)</text>
      <text x="25" y="80" class="tag" fill="#ef4444">- Penalize trash/recycle directories (-500)</text>
      <text x="25" y="95" class="tag" fill="#10b981">+ Reward directory seniority &amp; 4K resolution (+50)</text>
    </g>

    <!-- Arrow between keeper and actions -->
    <path d="M 435 72 L 465 72" stroke="#64748b" stroke-width="2" marker-end="url(#arrow)" />

    <!-- Action 1: Hardlink -->
    <g transform="translate(475, 20)">
      <rect width="280" height="105" rx="10" fill="#090d16" stroke="#059669" />
      <rect x="15" y="12" width="75" height="20" rx="4" fill="#065f46" />
      <text x="20" y="26" font-size="10" font-weight="700" fill="#34d399">--action hardlink</text>
      <text x="15" y="52" class="card-title">Native Inode Unification</text>
      <text x="15" y="70" class="card-desc">• NTFS &amp; POSIX zero-space links</text>
      <text x="15" y="86" class="card-desc">• 100% space reclaimed instantly</text>
      <text x="15" y="101" class="tag" fill="#34d399">✓ Zero broken application paths</text>
    </g>

    <!-- Action 2: Quarantine -->
    <g transform="translate(775, 20)">
      <rect width="280" height="105" rx="10" fill="#090d16" stroke="#334155" />
      <rect x="15" y="12" width="90" height="20" rx="4" fill="#881337" />
      <text x="20" y="26" font-size="10" font-weight="700" fill="#fda4af">--action quarantine</text>
      <text x="15" y="52" class="card-title">Safe Reversible Isolation</text>
      <text x="15" y="70" class="card-desc">• Non-clobbering move (_1, _2)</text>
      <text x="15" y="86" class="card-desc">• quarantine_manifest.json</text>
      <text x="15" y="101" class="tag" fill="#fda4af">✓ 1-Click Rollback / Restore</text>
    </g>
  </g>
</svg>
"""
    OUTPUT_SVG.write_text(svg_content, encoding="utf-8")
    print(f"[✓] Generated architecture SVG at: {OUTPUT_SVG.relative_to(REPO_ROOT)} ({len(svg_content)} bytes)")
    return OUTPUT_SVG


if __name__ == "__main__":
    generate_architecture_svg()
