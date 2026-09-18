# Clairvoy Premier UX Design System & Architecture Spec
**Date:** 2026-09-18  
**Topic:** CleanMyMac / Immich / Gemini Photos Inspired Storage Deduplication Interface  
**Status:** Approved for Autonomous Implementation  

---

## 1. Executive Summary & Design Philosophy

Clairvoy's web interface is being transformed from a simple single-page list into a premier, world-class storage optimization dashboard inspired by the finest design patterns of **MacPaw CleanMyMac X / CleanMy®Phone**, **Immich**, and **Google Photos duplicate detection**.

The user interface balances **aesthetic polish** (modern dark mode, smooth glassmorphism, category distribution meters) with **deep engineering utility** (sub-millisecond instant search, fast pagination over 10,000+ clusters, interactive keeper swapping, side-by-side photo diff lightbox, and reversible quarantine staging).

---

## 2. Multi-Disciplinary Panel Debate & Key Decisions

A simulated expert design & engineering panel deliberated on the optimal UX architecture:

### Panelists:
- **Elena Vance** (VP of Product Design, Ex-MacPaw): Champions emotional satisfaction of space reclamation, clear "Keeper vs Duplicate" visual hierarchy, side-by-side comparison studio, and clean category breakdown meters.
- **Marcus Chen** (Principal Frontend Systems Architect, Ex-Immich): Champions client-side performance, instant filtering over 10,000+ clusters, lazy-loaded thumbnails, clean DOM pagination, and 100% offline self-containment.
- **Dr. Aris Thorne** (Security & Safety Invariants Architect): Champions the Zero-Clobber principle, manual keeper override capability, selective file exclusion checkboxes, and transparent shell script / manifest export.

### Consensus & Decisions:
1. **App Shell & Layout**:
   - Clean dark-mode aesthetic (`#0b0f19` canvas, `#111827` cards, indigo/violet focus accents, emerald keeper highlights, rose duplicate badges).
   - Prominent Top Bar featuring Run Selector (`📂 Runs:`), live status ticker, new scan trigger button, and storage overview.
2. **Hero Storage Reclamation Meter**:
   - Visual progress-style bar displaying wasted gigabytes segmented by category (Photos, Screenshots, Documents, Graphics, Files).
   - Clear KPI cards: Total Space Reclaimable, Scanned Files, Exact Duplicates, AI Near-Duplicates.
3. **Cluster Card Design & Interactive Keeper Swapping**:
   - Distinct visual separation between the `KEEP` file (highlighted in emerald border with star badge) and `DUPLICATE` files (checkbox for quarantine inclusion).
   - "Make Keeper" button on duplicate items allowing users to effortlessly change which file is preserved.
4. **Side-by-Side Comparison Lightbox Modal**:
   - Full-screen modal comparing Keeper vs Duplicate side-by-side with high-res thumbnails and metadata diff (dimensions, size, mtime, path).
5. **High-Performance Pagination & Multi-Facet Filtering**:
   - Instant search by filename or parent folder path.
   - Filter by Modality: `All`, `Photos`, `Screenshots`, `Documents`, `Graphics`, `Other`.
   - Filter by Match Type: `All`, `Exact Hash`, `Vision AI`, `Content Near-Duplicate`.
   - Sort by: `Wasted Space (Desc)`, `Duplicate Count (Desc)`, `Similarity Score`.
   - Paginated display (25, 50, 100 per page) ensuring snappy 60fps rendering even with 10,463 clusters.
6. **Bottom Action Dock**:
   - Sticky floating footer showing exact count and bytes currently selected for quarantine.
   - Buttons to download CSV report, view quarantine bash script, or execute safe reversible quarantine.

---

## 3. High-Level ASCII UI Architecture

```
+----------------------------------------------------------------------------------------------------------------+
|  👁️ CLAIRVOY                                📂 Run: [/mnt/e • 68.22 GB • 10,463 clusters] [v]    [+ New Scan] |
+----------------------------------------------------------------------------------------------------------------+
|                                                                                                                |
|  HERO STORAGE METER                                                                                            |
|  +----------------------------------------------------------------------------------------------------------+  |
|  | 68.216 GB RECLAIMABLE STORAGE                                                    43,086 Files Analyzed   |  |
|  | [======================== PHOTOS 65% ========================][== DOCS ==][== SCREENSHOTS ==][== FILES =]|  |
|  +----------------------------------------------------------------------------------------------------------+  |
|                                                                                                                |
|  MODALITY TABS:                                                                                                |
|  [All Duplicates: 10,463]  [📷 Photos: 6,678]  [📱 Screenshots: 786]  [📄 Documents: 355]  [🎨 Graphics: 86]     |
|                                                                                                                |
|  TOOLBAR:                                                                                                      |
|  [ 🔍 Search filename or path...           ]  [ Match Type: All [v] ]  [ Sort: Wasted Size [v] ]  [Select All]|
|                                                                                                                |
|  CLUSTER GALLERY (Paginated):                                                                                  |
|  +----------------------------------------------------------------------------------------------------------+  |
|  | Cluster #7876  •  Vision AI Match (98.4%)  •  Wasted: 14.8 MB  •  2 Items            [🔍 Compare Side-by-Side] |
|  |  +----------------------------------------+    +----------------------------------------+                 |  |
|  |  | [★ KEEPER - BEST QUALITY]              |    | [⌧ DUPLICATE - RECLAIMABLE]            |                 |  |
|  |  | [ Image Thumbnail Preview            ] |    | [ Image Thumbnail Preview            ] |                 |  |
|  |  | IMG_20220814.jpg (4032x3024 • 7.4 MB)  |    | IMG_20220814_copy.jpg (4032x3024)     |                 |  |
|  |  | /mnt/e/Photos/2022/IMG_20220814.jpg    |    | /mnt/e/Backups/Phone/IMG_...           |                 |  |
|  |  +----------------------------------------+    | [ Make Keeper ]                        |                 |  |
|  |                                                +----------------------------------------+                 |  |
|  +----------------------------------------------------------------------------------------------------------+  |
|                                                                                                                |
|  PAGINATION CONTROLS:                                                                                          |
|  [ << Prev ]  Page 1 of 419 (Showing 1-25 of 10,463 clusters)  [ Next >> ]   [ Per page: 25 [v] ]               |
|                                                                                                                |
|  STICKY ACTION DOCK:                                                                                           |
|  +----------------------------------------------------------------------------------------------------------+  |
|  | Selected for Quarantine: 10,463 files (68.216 GB)    [📄 CSV Report] [📜 Script] [⚡ Quarantine Selected] |  |
|  +----------------------------------------------------------------------------------------------------------+  |
+----------------------------------------------------------------------------------------------------------------+
```

---

## 4. API Endpoints Contract

- `GET /api/status`: Returns current server status and active summary.
- `GET /api/runs`: Lists past scan runs with metadata, newest first.
- `POST /api/runs/load`: Loads past run by `run_id` or `path`.
- `GET /api/thumbnail`: Streams secure, cached image thumbnail for valid image extensions.
- `POST /api/clusters/override-keeper`:
  - Body: `{"group_id": int, "new_keeper_path": str}`
  - Updates active summary in memory so the chosen file becomes `KEEP` and former keeper becomes `DUPLICATE`.
- `POST /api/quarantine/execute`: Moves designated duplicate files into `_duplicate_quarantine`.
- `POST /api/quarantine/restore`: Restores quarantined files from a manifest.
