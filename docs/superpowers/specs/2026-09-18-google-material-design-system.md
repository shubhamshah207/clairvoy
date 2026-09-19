# Specification: Google Material Design 3 UX & Safe Deletion Engine

**Status:** Approved  
**Author:** AI Pair Architecture Team (Design: Elena Vance [M3 Specialist], Systems: Marcus Chen, Security: Dr. Aris Thorne)  
**Date:** 2026-09-18  

---

## 1. Executive Summary & Vision

Clairvoy is evolving its user experience to match the world's most intuitive and recognizable consumer and enterprise storage interfaces: **Google Photos**, **Google Drive**, **Google Files**, and **Google One Storage Manager**.

The new experience combines:
1. **Google Material Design 3 (M3) Design System**: An ultra-clean, minimal, 100% offline design system utilizing Google's signature aesthetic:
   - Elevated pill search bar with integrated filtering and account/dataset status.
   - Left Navigation Rail (Desktop) with Google-style icons (*Storage Clean Up*, *Photos*, *Drive Files*, *Duplicates*, *Trash*).
   - Google Photos-style photo tiles with circular hover checkmarks for effortless multi-selection.
   - Google Drive-style dual view modes (Grid View for visual media, Compact List/Table View for dense tabular/document review).
   - Google Photos-style floating Contextual Selection Action Bar (`"X items selected"` with bulk actions).
2. **First-Class Safe Deletion Engine (`DeleteEngine`)**:
   - Giving users direct control to **Delete** duplicates in addition to **Quarantine**.
   - **Mode A: Soft Delete / Move to Trash** (`.clairvoy_trash/` or system trash) with full rollback manifest for instant 1-click restoration.
   - **Mode B: Permanent Deletion** with mandatory zero-clobber keeper protection, strict root path isolation, and an immutable JSON audit log.
   - Hardened Shell Script Generation (`GET /api/reports/delete-script`) for dry-run inspection before execution.

---

## 2. Multidisciplinary Panel Debate & Technical Decisions

### Debate 1: Material Design System — Heavy Framework vs. Minimal Offline Tokens
- **Elena Vance (UX/Design):** "Google Photos and Drive have an instantly recognizable rhythm: pill-shaped floating search bars, 24px rounded chips, circular selection checkmarks in the top corner of photos, and floating contextual top bars. We should not import bloated external npm packages or runtime CDNs that fail offline. We can define clean Material Design 3 tokens and utility classes directly on top of our existing Tailwind setup."
- **Marcus Chen (Performance):** "Agreed. Pure offline HTML5 + CSS3 + Vanilla JS means zero network calls, sub-millisecond DOM render times, and zero bundle bloat. By keeping the design system minimal and declarative, the entire frontend remains under 45KB."
- **Dr. Aris Thorne (Security):** "Zero external CDNs is an absolute security requirement. All styling, SVG icons, and typography must render offline in completely air-gapped environments."
- **Decision:** Build a custom, minimal Material Design 3 token system in `clairvoy/web/ui.py` using offline CSS custom properties, M3 color tokens, rounded geometries (`rounded-full`, `rounded-2xl`, `rounded-3xl`), and inline SVG icons matching Google Material symbols.

### Debate 2: Deletion Safety vs. Direct Curation
- **Dr. Aris Thorne (Security):** "Direct deletion is dangerous if unconstrained. We must guarantee:
  1. The designated Keeper file can NEVER be deleted under any circumstances (hard assertion in backend).
  2. Deleted files must never escape the authorized scanned roots.
  3. Every deletion must produce an audit trail (`deletion_audit.json`).
  4. Users must be offered a default **Move to Trash** (reversible) option, alongside an explicit **Delete Permanently** modal that requires active confirmation."
- **Marcus Chen (Performance):** "For large clusters (Drive E has 10,463 clusters with 68 GB), batch deletions must run concurrently using `ThreadPoolExecutor` bounded to 4-8 workers to avoid I/O bottlenecks."
- **Decision:** Implement `DeleteEngine` in `clairvoy/engines/delete_engine.py` supporting both `trash` (reversible) and `permanent` deletion, with `POST /api/delete/execute` and `GET /api/reports/delete-script`.

### Debate 3: View Modes — Google Photos vs. Google Drive
- **Elena Vance (UX):** "Users reviewing photos want an image-first visual masonry grid like Google Photos. Users reviewing documents, PDFs, and code repositories want a detailed file list like Google Drive. We must offer a seamless toggle:
  - **Photos View (Google Photos)**: Large visual cards, circular selection chips, keeper badge, and side-by-side comparison.
  - **Files View (Google Drive)**: Dense metadata table with columns (File Name, Size, Duplicate Type, Last Modified, Actions)."
- **Decision:** Support instant client-side toggling between **Grid View** (Google Photos) and **List View** (Google Drive) with persistent state.

---

## 3. Architecture & Data Flow Diagram

```
+-----------------------------------------------------------------------------------------+
|                                CLAIRVOY GOOGLE M3 STUDIO                                |
+-----------------------------------------------------------------------------------------+
|                                                                                         |
|  [Google App Bar]   Clairvoy Storage   |   [ 🔍 Search in storage... ]   |  Dataset Chip|
|                                                                                         |
|  +--------------------+  +-----------------------------------------------------------+  |
|  | GOOGLE NAV RAIL    |  | GOOGLE ONE CLEAN-UP HERO                                  |  |
|  |                    |  | Clean up space: 68.22 GB used by duplicates               |  |
|  | [🧹 Clean up]     |  | [=== Photos: 52GB ===][== Videos ==][= Docs =][= Files =] |  |
|  | [🖼️ Photos]       |  +-----------------------------------------------------------+  |
|  | [📁 Drive Files]   |                                                              |  |
|  | [🗂️ All Duplicates]|  +-----------------------------------------------------------+  |
|  | [🗑️ Trash / Audit] |  | FILTER CHIPS & VIEW TOGGLE: [ ▦ Grid ] [ ☰ List ]          |  |
|  |                    |  +-----------------------------------------------------------+  |
|  |                    |                                                              |  |
|  |                    |  +-----------------------------------------------------------+  |
|  |                    |  | CONTEXTUAL ACTION BAR (Visible when items selected)       |  |
|  |                    |  | [✕] 18 items selected (1.4 GB) | [Select All]             |  |
|  |                    |  | Actions: [ 🗑️ Move to Trash ] [ ⚠️ Delete ] [ 📦 Quarantine]|  |
|  |                    |  +-----------------------------------------------------------+  |
|  +--------------------+  +-----------------------------------------------------------+  |
+-----------------------------------------------------------------------------------------+
                                        |
                 +----------------------+----------------------+
                 v                                             v
       [Quarantine Engine]                               [Delete Engine]
       clairvoy/engines/quarantine.py                    clairvoy/engines/delete_engine.py
                 |                                             |
                 +---> _duplicate_quarantine/                  +---> .clairvoy_trash/ (Soft)
                 +---> quarantine_manifest.json                +---> os.unlink() (Permanent)
                                                               +---> deletion_audit.json
```

---

## 4. Design System Tokens (Material Design 3)

| Token Name | Hex Value | Purpose |
|---|---|---|
| `--md-sys-color-background` | `#131314` | Deep Google dark surface background |
| `--md-sys-color-surface` | `#1e1f20` | Elevated container surface (cards, rail) |
| `--md-sys-color-surface-variant`| `#28292a` | Higher elevation surface (modals, search bar) |
| `--md-sys-color-primary` | `#8ab4f8` | Google Blue (active tabs, primary buttons) |
| `--md-sys-color-primary-container`| `#1a3860` | Subtle blue tint for selection backgrounds |
| `--md-sys-color-success` | `#81c995` | Google Green (Keeper badge, completed states) |
| `--md-sys-color-error` | `#f28b82` | Google Red (Delete action, high risk) |
| `--md-sys-color-warning` | `#fdd663` | Google Yellow (Quarantine, warning chips) |
| `--md-sys-color-outline` | `rgba(255, 255, 255, 0.12)` | Subtle hair-line borders |
| `--md-sys-shape-corner-full`| `9999px` | Pill chips, search bar, floating action buttons |
| `--md-sys-shape-corner-large`| `24px` | Hero cards, dialog containers |
| `--md-sys-shape-corner-medium`| `16px` | Duplicate cluster cards, photo tiles |

---

## 5. API Endpoints

### 1. `POST /api/delete/execute`
- **Request Body:**
  ```json
  {
    "paths": ["/path/to/dupe1.jpg", "/path/to/dupe2.png"],
    "mode": "trash",  // "trash" | "permanent"
    "base_dir": "/mnt/e"
  }
  ```
- **Response:**
  ```json
  {
    "status": "completed",
    "mode": "trash",
    "total_files_deleted": 2,
    "total_bytes_freed": 1458200,
    "manifest_file": "/mnt/e/.clairvoy_trash/trash_manifest_20260918_203000.json"
  }
  ```

### 2. `POST /api/delete/restore`
- **Request Body:**
  ```json
  {
    "manifest_file": "/mnt/e/.clairvoy_trash/trash_manifest_20260918_203000.json"
  }
  ```
- **Response:**
  ```json
  {
    "status": "restored",
    "restored_files_count": 2
  }
  ```

### 3. `GET /api/reports/delete-script`
- Streams an audit-ready `delete_duplicates.sh` script containing hardened posix-quoted `rm -f --` commands.
